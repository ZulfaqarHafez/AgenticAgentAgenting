//! Goal and run storage: in-memory by default, or Postgres with a Redis run cache.

use std::sync::RwLock;

use anyhow::Context;
use indexmap::IndexMap;
use redis::AsyncCommands;
use redis::aio::ConnectionManager;
use sqlx::PgPool;
use sqlx::postgres::PgPoolOptions;

use crate::models::{Goal, Run, utc_now};
use crate::settings::{AppSettings, StoreBackend};

pub enum Store {
    Memory(MemoryStore),
    PostgresRedis(PostgresRedisStore),
}

impl Store {
    /// Connects to the configured backend and prepares its schema.
    pub async fn connect(settings: &AppSettings) -> anyhow::Result<Self> {
        match settings.store_backend {
            StoreBackend::Memory => Ok(Self::Memory(MemoryStore::default())),
            StoreBackend::PostgresRedis => {
                let store = PostgresRedisStore::connect(
                    &settings.database_url,
                    &settings.redis_url,
                    settings.redis_run_ttl_seconds,
                )
                .await?;
                store.initialize().await?;
                Ok(Self::PostgresRedis(store))
            }
        }
    }

    pub fn memory() -> Self {
        Self::Memory(MemoryStore::default())
    }

    pub async fn create_goal(&self, goal: Goal) -> anyhow::Result<Goal> {
        match self {
            Self::Memory(store) => Ok(store.put_goal(goal)),
            Self::PostgresRedis(store) => store.upsert_goal(goal).await,
        }
    }

    pub async fn list_goals(&self) -> anyhow::Result<Vec<Goal>> {
        match self {
            Self::Memory(store) => Ok(store.list_goals()),
            Self::PostgresRedis(store) => store.list_goals().await,
        }
    }

    pub async fn get_goal(&self, goal_id: &str) -> anyhow::Result<Option<Goal>> {
        match self {
            Self::Memory(store) => Ok(store.get_goal(goal_id)),
            Self::PostgresRedis(store) => store.get_goal(goal_id).await,
        }
    }

    pub async fn create_run(&self, run: Run) -> anyhow::Result<Run> {
        match self {
            Self::Memory(store) => Ok(store.put_run(run)),
            Self::PostgresRedis(store) => store.upsert_run(run).await,
        }
    }

    pub async fn update_run(&self, mut run: Run) -> anyhow::Result<Run> {
        run.updated_at = utc_now();
        self.create_run(run).await
    }

    pub async fn get_run(&self, run_id: &str) -> anyhow::Result<Option<Run>> {
        match self {
            Self::Memory(store) => Ok(store.get_run(run_id)),
            Self::PostgresRedis(store) => store.get_run(run_id).await,
        }
    }

    pub async fn list_runs(&self) -> anyhow::Result<Vec<Run>> {
        match self {
            Self::Memory(store) => Ok(store.list_runs()),
            Self::PostgresRedis(store) => store.list_runs().await,
        }
    }
}

/// Keeps everything in process memory, in insertion order. Lost on restart.
#[derive(Default)]
pub struct MemoryStore {
    goals: RwLock<IndexMap<String, Goal>>,
    runs: RwLock<IndexMap<String, Run>>,
}

impl MemoryStore {
    fn put_goal(&self, goal: Goal) -> Goal {
        self.goals
            .write()
            .unwrap()
            .insert(goal.goal_id.clone(), goal.clone());
        goal
    }

    fn list_goals(&self) -> Vec<Goal> {
        self.goals.read().unwrap().values().cloned().collect()
    }

    fn get_goal(&self, goal_id: &str) -> Option<Goal> {
        self.goals.read().unwrap().get(goal_id).cloned()
    }

    fn put_run(&self, run: Run) -> Run {
        self.runs
            .write()
            .unwrap()
            .insert(run.run_id.clone(), run.clone());
        run
    }

    fn get_run(&self, run_id: &str) -> Option<Run> {
        self.runs.read().unwrap().get(run_id).cloned()
    }

    fn list_runs(&self) -> Vec<Run> {
        self.runs.read().unwrap().values().cloned().collect()
    }
}

/// Stores goals and runs as JSON in Postgres, and caches runs in Redis.
///
/// Uses the same `goals` / `runs` tables the Python backend created, so existing data loads.
pub struct PostgresRedisStore {
    pool: PgPool,
    redis: ConnectionManager,
    run_ttl_seconds: u64,
}

impl PostgresRedisStore {
    pub async fn connect(
        database_url: &str,
        redis_url: &str,
        run_ttl_seconds: u64,
    ) -> anyhow::Result<Self> {
        let pool = PgPoolOptions::new()
            .max_connections(10)
            .connect(database_url)
            .await
            .context("connecting to Postgres")?;
        let redis = redis::Client::open(redis_url)
            .context("parsing Redis URL")?
            .get_connection_manager()
            .await
            .context("connecting to Redis")?;
        Ok(Self {
            pool,
            redis,
            run_ttl_seconds,
        })
    }

    pub async fn initialize(&self) -> anyhow::Result<()> {
        for statement in [
            "CREATE TABLE IF NOT EXISTS goals (
                goal_id VARCHAR(64) PRIMARY KEY,
                payload JSON NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )",
            "CREATE TABLE IF NOT EXISTS runs (
                run_id VARCHAR(64) PRIMARY KEY,
                goal_id VARCHAR(64) NOT NULL,
                payload JSON NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )",
            "CREATE INDEX IF NOT EXISTS ix_runs_goal_id ON runs (goal_id)",
        ] {
            sqlx::query(statement)
                .execute(&self.pool)
                .await
                .context("creating tables")?;
        }
        let _: String = redis::cmd("PING")
            .query_async(&mut self.redis.clone())
            .await
            .context("pinging Redis")?;
        Ok(())
    }

    async fn upsert_goal(&self, goal: Goal) -> anyhow::Result<Goal> {
        sqlx::query(
            "INSERT INTO goals (goal_id, payload, updated_at) VALUES ($1, $2::json, $3)
             ON CONFLICT (goal_id) DO UPDATE
             SET payload = EXCLUDED.payload, updated_at = EXCLUDED.updated_at",
        )
        .bind(&goal.goal_id)
        .bind(serde_json::to_string(&goal)?)
        .bind(goal.updated_at)
        .execute(&self.pool)
        .await
        .context("saving goal")?;
        Ok(goal)
    }

    async fn list_goals(&self) -> anyhow::Result<Vec<Goal>> {
        let rows: Vec<(String,)> =
            sqlx::query_as("SELECT payload::text FROM goals ORDER BY updated_at DESC")
                .fetch_all(&self.pool)
                .await
                .context("listing goals")?;
        rows.iter()
            .map(|(json,)| Ok(serde_json::from_str(json)?))
            .collect()
    }

    async fn get_goal(&self, goal_id: &str) -> anyhow::Result<Option<Goal>> {
        let row: Option<(String,)> =
            sqlx::query_as("SELECT payload::text FROM goals WHERE goal_id = $1")
                .bind(goal_id)
                .fetch_optional(&self.pool)
                .await
                .context("loading goal")?;
        row.map(|(json,)| Ok(serde_json::from_str(&json)?))
            .transpose()
    }

    async fn upsert_run(&self, run: Run) -> anyhow::Result<Run> {
        let payload = serde_json::to_string(&run)?;
        sqlx::query(
            "INSERT INTO runs (run_id, goal_id, payload, updated_at) VALUES ($1, $2, $3::json, $4)
             ON CONFLICT (run_id) DO UPDATE
             SET goal_id = EXCLUDED.goal_id, payload = EXCLUDED.payload,
                 updated_at = EXCLUDED.updated_at",
        )
        .bind(&run.run_id)
        .bind(&run.goal_id)
        .bind(&payload)
        .bind(run.updated_at)
        .execute(&self.pool)
        .await
        .context("saving run")?;
        self.cache_run(&run.run_id, &payload).await;
        Ok(run)
    }

    async fn get_run(&self, run_id: &str) -> anyhow::Result<Option<Run>> {
        let cached: Option<String> = self
            .redis
            .clone()
            .get(cache_key(run_id))
            .await
            .inspect_err(|error| tracing::warn!(%error, "Redis read failed; using Postgres"))
            .ok()
            .flatten();
        if let Some(json) = cached {
            return Ok(Some(serde_json::from_str(&json)?));
        }

        let row: Option<(String,)> =
            sqlx::query_as("SELECT payload::text FROM runs WHERE run_id = $1")
                .bind(run_id)
                .fetch_optional(&self.pool)
                .await
                .context("loading run")?;
        let Some((json,)) = row else { return Ok(None) };
        self.cache_run(run_id, &json).await;
        Ok(Some(serde_json::from_str(&json)?))
    }

    async fn list_runs(&self) -> anyhow::Result<Vec<Run>> {
        let rows: Vec<(String,)> =
            sqlx::query_as("SELECT payload::text FROM runs ORDER BY updated_at DESC")
                .fetch_all(&self.pool)
                .await
                .context("listing runs")?;
        rows.iter()
            .map(|(json,)| Ok(serde_json::from_str(json)?))
            .collect()
    }

    /// Best effort: Postgres is the source of truth, so a cache failure is only logged.
    async fn cache_run(&self, run_id: &str, payload: &str) {
        let result: redis::RedisResult<()> = self
            .redis
            .clone()
            .set_ex(cache_key(run_id), payload, self.run_ttl_seconds)
            .await;
        if let Err(error) = result {
            tracing::warn!(%error, "Redis write failed");
        }
    }
}

fn cache_key(run_id: &str) -> String {
    format!("hive:run:{run_id}")
}
