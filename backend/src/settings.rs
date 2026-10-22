//! Configuration from `HIVE_*` environment variables.

const DEFAULT_DATABASE_URL: &str = "postgresql://postgres:postgres@localhost:5432/hive_agent";
const DEFAULT_REDIS_URL: &str = "redis://localhost:6379/0";
const DEFAULT_CORS_ORIGINS: &str = "http://localhost:3000,http://127.0.0.1:3000,\
    http://localhost:3001,http://127.0.0.1:3001,http://localhost:3002,http://127.0.0.1:3002,\
    http://localhost:3003,http://127.0.0.1:3003,http://localhost:3004,http://127.0.0.1:3004,\
    http://localhost:3005,http://127.0.0.1:3005,http://localhost:3010,http://127.0.0.1:3010,\
    http://localhost:3011,http://127.0.0.1:3011";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StoreBackend {
    Memory,
    PostgresRedis,
}

impl StoreBackend {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Memory => "memory",
            Self::PostgresRedis => "postgres_redis",
        }
    }
}

#[derive(Debug, Clone)]
pub struct AppSettings {
    pub host: String,
    pub port: u16,
    pub store_backend: StoreBackend,
    pub database_url: String,
    pub redis_url: String,
    pub redis_run_ttl_seconds: u64,
    pub cors_origins: Vec<String>,
}

impl Default for AppSettings {
    fn default() -> Self {
        Self::from_lookup(|_| None)
    }
}

impl AppSettings {
    pub fn from_env() -> Self {
        Self::from_lookup(|key| std::env::var(key).ok())
    }

    /// Builds settings from any key lookup, so tests don't have to touch the real environment.
    pub fn from_lookup(lookup: impl Fn(&str) -> Option<String>) -> Self {
        let get = |key: &str, default: &str| lookup(key).unwrap_or_else(|| default.to_string());

        let store_backend = match get("HIVE_STORE_BACKEND", "memory")
            .trim()
            .to_lowercase()
            .as_str()
        {
            "postgres_redis" => StoreBackend::PostgresRedis,
            _ => StoreBackend::Memory,
        };

        Self {
            host: get("HIVE_HOST", "127.0.0.1"),
            port: parse_or("HIVE_PORT", &get("HIVE_PORT", "8000"), 8000),
            store_backend,
            database_url: normalize_database_url(&get("HIVE_DATABASE_URL", DEFAULT_DATABASE_URL)),
            redis_url: get("HIVE_REDIS_URL", DEFAULT_REDIS_URL),
            redis_run_ttl_seconds: parse_or(
                "HIVE_REDIS_RUN_TTL_SECONDS",
                &get("HIVE_REDIS_RUN_TTL_SECONDS", "900"),
                900,
            ),
            cors_origins: get("HIVE_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
                .split(',')
                .map(str::trim)
                .filter(|origin| !origin.is_empty())
                .map(str::to_string)
                .collect(),
        }
    }
}

fn parse_or<T: std::str::FromStr + Copy>(key: &str, raw: &str, default: T) -> T {
    raw.trim().parse().unwrap_or_else(|_| {
        tracing::warn!("{key}={raw:?} is not a valid number; using default");
        default
    })
}

/// Accepts the SQLAlchemy-style `postgresql+psycopg://` URLs the Python backend used.
fn normalize_database_url(url: &str) -> String {
    match url.split_once("://") {
        Some((scheme, rest))
            if scheme.starts_with("postgresql+") || scheme.starts_with("postgres+") =>
        {
            format!("postgresql://{rest}")
        }
        _ => url.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_use_memory_store() {
        let settings = AppSettings::default();
        assert_eq!(settings.store_backend, StoreBackend::Memory);
        assert_eq!(settings.port, 8000);
        assert!(
            settings
                .cors_origins
                .contains(&"http://127.0.0.1:3010".to_string())
        );
        assert_eq!(settings.cors_origins.len(), 16);
    }

    #[test]
    fn reads_overrides() {
        let settings = AppSettings::from_lookup(|key| match key {
            "HIVE_STORE_BACKEND" => Some(" Postgres_Redis ".into()),
            "HIVE_DATABASE_URL" => Some("postgresql+psycopg://u:p@db:5432/hive".into()),
            "HIVE_PORT" => Some("8010".into()),
            "HIVE_REDIS_RUN_TTL_SECONDS" => Some("not-a-number".into()),
            _ => None,
        });
        assert_eq!(settings.store_backend, StoreBackend::PostgresRedis);
        assert_eq!(settings.database_url, "postgresql://u:p@db:5432/hive");
        assert_eq!(settings.port, 8010);
        assert_eq!(settings.redis_run_ttl_seconds, 900);
    }

    #[test]
    fn unknown_backend_falls_back_to_memory() {
        let settings = AppSettings::from_lookup(|key| {
            (key == "HIVE_STORE_BACKEND").then(|| "mongo".to_string())
        });
        assert_eq!(settings.store_backend, StoreBackend::Memory);
    }
}
