from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from threading import Lock
from typing import Protocol

import redis
from sqlalchemy import DateTime, JSON, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.models import Goal, Run, utc_now
from app.settings import AppSettings, StoreBackend


class Store(Protocol):
    def initialize(self) -> None:
        """Prepare storage dependencies."""

    def close(self) -> None:
        """Release storage dependencies."""

    def create_goal(self, goal: Goal) -> Goal:
        ...

    def list_goals(self) -> list[Goal]:
        ...

    def get_goal(self, goal_id: str) -> Goal | None:
        ...

    def update_goal(self, goal: Goal) -> Goal:
        ...

    def create_run(self, run: Run) -> Run:
        ...

    def get_run(self, run_id: str) -> Run | None:
        ...

    def update_run(self, run: Run) -> Run:
        ...


@dataclass
class InMemoryState:
    goals: dict[str, Goal] = field(default_factory=dict)
    runs: dict[str, Run] = field(default_factory=dict)


class InMemoryStore:
    """Simple in-memory store for MVP development."""

    def __init__(self) -> None:
        self._state = InMemoryState()
        self._lock = Lock()

    def initialize(self) -> None:
        return None

    def close(self) -> None:
        return None

    def create_goal(self, goal: Goal) -> Goal:
        with self._lock:
            self._state.goals[goal.goal_id] = goal
        return goal

    def list_goals(self) -> list[Goal]:
        with self._lock:
            return list(self._state.goals.values())

    def get_goal(self, goal_id: str) -> Goal | None:
        with self._lock:
            return self._state.goals.get(goal_id)

    def update_goal(self, goal: Goal) -> Goal:
        with self._lock:
            self._state.goals[goal.goal_id] = goal
        return goal

    def create_run(self, run: Run) -> Run:
        with self._lock:
            self._state.runs[run.run_id] = run
        return run

    def get_run(self, run_id: str) -> Run | None:
        with self._lock:
            return self._state.runs.get(run_id)

    def update_run(self, run: Run) -> Run:
        with self._lock:
            self._state.runs[run.run_id] = run
        return run


class SqlBase(DeclarativeBase):
    pass


class GoalRecord(SqlBase):
    __tablename__ = "goals"
    goal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RunRecord(SqlBase):
    __tablename__ = "runs"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    goal_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PostgresRedisStore:
    def __init__(
        self,
        database_url: str,
        redis_url: str,
        run_ttl_seconds: int = 900,
        redis_client: redis.Redis | None = None,
    ) -> None:
        self._engine = create_engine(database_url, future=True, pool_pre_ping=True)
        self._sessions = sessionmaker(bind=self._engine, class_=Session, expire_on_commit=False)
        self._redis = redis_client or redis.from_url(redis_url, decode_responses=True)
        self._run_ttl_seconds = run_ttl_seconds

    def initialize(self) -> None:
        SqlBase.metadata.create_all(self._engine)
        self._redis.ping()

    def close(self) -> None:
        self._engine.dispose()
        self._redis.close()

    def create_goal(self, goal: Goal) -> Goal:
        return self._upsert_goal(goal)

    def list_goals(self) -> list[Goal]:
        with self._sessions() as session:
            rows = session.scalars(select(GoalRecord).order_by(GoalRecord.updated_at.desc()))
            return [Goal.model_validate(row.payload) for row in rows]

    def get_goal(self, goal_id: str) -> Goal | None:
        with self._sessions() as session:
            row = session.get(GoalRecord, goal_id)
            if not row:
                return None
            return Goal.model_validate(row.payload)

    def update_goal(self, goal: Goal) -> Goal:
        goal.updated_at = utc_now()
        return self._upsert_goal(goal)

    def create_run(self, run: Run) -> Run:
        return self._upsert_run(run)

    def get_run(self, run_id: str) -> Run | None:
        cache_key = self._run_cache_key(run_id)
        cached = self._redis.get(cache_key)
        if cached:
            return Run.model_validate(json.loads(cached))

        with self._sessions() as session:
            row = session.get(RunRecord, run_id)
            if not row:
                return None
            run = Run.model_validate(row.payload)
            self._cache_run(run)
            return run

    def update_run(self, run: Run) -> Run:
        run.updated_at = utc_now()
        return self._upsert_run(run)

    def _upsert_goal(self, goal: Goal) -> Goal:
        payload = goal.model_dump(mode="json")
        with self._sessions() as session:
            row = session.get(GoalRecord, goal.goal_id)
            if row:
                row.payload = payload
                row.updated_at = goal.updated_at
            else:
                row = GoalRecord(
                    goal_id=goal.goal_id,
                    payload=payload,
                    updated_at=goal.updated_at,
                )
                session.add(row)
            session.commit()
        return goal

    def _upsert_run(self, run: Run) -> Run:
        payload = run.model_dump(mode="json")
        with self._sessions() as session:
            row = session.get(RunRecord, run.run_id)
            if row:
                row.payload = payload
                row.updated_at = run.updated_at
                row.goal_id = run.goal_id
            else:
                row = RunRecord(
                    run_id=run.run_id,
                    goal_id=run.goal_id,
                    payload=payload,
                    updated_at=run.updated_at,
                )
                session.add(row)
            session.commit()
        self._cache_run(run)
        return run

    def _cache_run(self, run: Run) -> None:
        self._redis.set(
            self._run_cache_key(run.run_id),
            json.dumps(run.model_dump(mode="json")),
            ex=self._run_ttl_seconds,
        )

    @staticmethod
    def _run_cache_key(run_id: str) -> str:
        return f"hive:run:{run_id}"


def build_store(settings: AppSettings) -> Store:
    if settings.store_backend == StoreBackend.POSTGRES_REDIS:
        return PostgresRedisStore(
            database_url=settings.database_url,
            redis_url=settings.redis_url,
            run_ttl_seconds=settings.redis_run_ttl_seconds,
        )
    return InMemoryStore()
