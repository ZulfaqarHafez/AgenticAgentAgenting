from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class StoreBackend(str, Enum):
    MEMORY = "memory"
    POSTGRES_REDIS = "postgres_redis"


@dataclass(frozen=True)
class AppSettings:
    store_backend: StoreBackend
    database_url: str
    redis_url: str
    redis_run_ttl_seconds: int


def load_settings() -> AppSettings:
    backend = os.getenv("HIVE_STORE_BACKEND", StoreBackend.MEMORY.value).strip().lower()
    if backend not in {member.value for member in StoreBackend}:
        backend = StoreBackend.MEMORY.value

    return AppSettings(
        store_backend=StoreBackend(backend),
        database_url=os.getenv(
            "HIVE_DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/hive_agent",
        ),
        redis_url=os.getenv("HIVE_REDIS_URL", "redis://localhost:6379/0"),
        redis_run_ttl_seconds=int(os.getenv("HIVE_REDIS_RUN_TTL_SECONDS", "900")),
    )

