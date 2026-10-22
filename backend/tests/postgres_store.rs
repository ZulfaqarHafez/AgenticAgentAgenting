//! Exercises the Postgres + Redis store. Skipped unless both of these are set:
//!
//! ```sh
//! HIVE_TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hive_agent_test \
//! HIVE_TEST_REDIS_URL=redis://localhost:6379/15 cargo test --test postgres_store
//! ```

use hive_agent_backend::models::{
    Goal, GoalCreateRequest, GoalPriority, RunStartRequest, SpecialistRole, TurnInput,
};
use hive_agent_backend::scheduler;
use hive_agent_backend::settings::{AppSettings, StoreBackend};
use hive_agent_backend::store::Store;

async fn connect() -> Option<Store> {
    let (Ok(database_url), Ok(redis_url)) = (
        std::env::var("HIVE_TEST_DATABASE_URL"),
        std::env::var("HIVE_TEST_REDIS_URL"),
    ) else {
        eprintln!("skipping: HIVE_TEST_DATABASE_URL / HIVE_TEST_REDIS_URL not set");
        return None;
    };
    let settings = AppSettings {
        store_backend: StoreBackend::PostgresRedis,
        database_url,
        redis_url,
        redis_run_ttl_seconds: 300,
        ..AppSettings::default()
    };
    Some(
        Store::connect(&settings)
            .await
            .expect("connect to Postgres and Redis"),
    )
}

#[tokio::test]
async fn persists_goal_and_run() {
    let Some(store) = connect().await else { return };

    let goal = store
        .create_goal(Goal::from(GoalCreateRequest {
            title: "Persistent goal".into(),
            success_criteria: vec!["Keep data".into(), "Load data".into()],
            constraints: vec![],
            priority: GoalPriority::High,
            subgoals: vec![],
        }))
        .await
        .unwrap();
    let fetched = store
        .get_goal(&goal.goal_id)
        .await
        .unwrap()
        .expect("goal saved");
    assert_eq!(fetched.title, "Persistent goal");
    assert!(
        store
            .list_goals()
            .await
            .unwrap()
            .iter()
            .any(|g| g.goal_id == goal.goal_id)
    );

    let request = RunStartRequest {
        active_roles: Some(vec![SpecialistRole::Planner, SpecialistRole::Research]),
        ..RunStartRequest::default()
    };
    let mut run = scheduler::initialize_run(&goal.goal_id, &request).unwrap();
    run = store.create_run(run).await.unwrap();
    let fetched = store
        .get_run(&run.run_id)
        .await
        .unwrap()
        .expect("run saved");
    assert_eq!(fetched.goal_id, goal.goal_id);
    assert_eq!(fetched.current_role, SpecialistRole::Planner);

    // Updates must reach both Postgres and the Redis cache.
    scheduler::apply_turn(
        &mut run,
        TurnInput::contribution(SpecialistRole::Planner, "Plan", 0.8, 0.8),
    )
    .unwrap();
    store.update_run(run.clone()).await.unwrap();
    let fetched = store.get_run(&run.run_id).await.unwrap().unwrap();
    assert_eq!(fetched.turn_history.len(), 1);
    assert_eq!(fetched.current_role, SpecialistRole::Research);

    let listed = store.list_runs().await.unwrap();
    let listed = listed
        .iter()
        .find(|r| r.run_id == run.run_id)
        .expect("run listed");
    assert_eq!(listed.turn_history.len(), 1);

    assert!(store.get_run("R-does-not-exist").await.unwrap().is_none());
}
