from pathlib import Path
from tempfile import TemporaryDirectory

from app.models import Goal, GoalPriority, RunStartRequest, SpecialistRole
from app.orchestration.scheduler import CircleJunctionScheduler
from app.settings import AppSettings, StoreBackend
from app.store import InMemoryStore, PostgresRedisStore, build_store


class FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def get(self, key: str):
        return self._kv.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._kv[key] = value
        return True

    def close(self) -> None:
        return None


def test_build_store_memory_backend() -> None:
    settings = AppSettings(
        store_backend=StoreBackend.MEMORY,
        database_url="postgresql+psycopg://postgres:postgres@localhost:5432/hive_agent",
        redis_url="redis://localhost:6379/0",
        redis_run_ttl_seconds=900,
    )
    store = build_store(settings)
    assert isinstance(store, InMemoryStore)


def test_postgres_redis_store_persists_goal_and_run() -> None:
    scheduler = CircleJunctionScheduler()
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "hive.db"
        store = PostgresRedisStore(
            database_url=f"sqlite+pysqlite:///{db_path}",
            redis_url="redis://unused",
            run_ttl_seconds=300,
            redis_client=FakeRedis(),
        )
        store.initialize()

        goal = Goal(
            title="Persistent goal",
            success_criteria=["Keep data", "Load data"],
            constraints=[],
            priority=GoalPriority.HIGH,
        )
        store.create_goal(goal)
        fetched_goal = store.get_goal(goal.goal_id)
        assert fetched_goal is not None
        assert fetched_goal.title == "Persistent goal"

        run = scheduler.initialize_run(
            goal_id=goal.goal_id,
            request=RunStartRequest(active_roles=[SpecialistRole.PLANNER, SpecialistRole.RESEARCH]),
        )
        store.create_run(run)
        fetched_run = store.get_run(run.run_id)
        assert fetched_run is not None
        assert fetched_run.goal_id == goal.goal_id
        assert fetched_run.current_role == SpecialistRole.PLANNER

        store.close()
