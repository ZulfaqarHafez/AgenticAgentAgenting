from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class RuntimeStatusResponse(BaseModel):
    status: str
    service: str
    api_version: str
    contract_version: str
    recommended_roles_supported: bool
    decision_ledger_supported: bool
    store_backend: str
    server_started_at: datetime
    server_now: datetime
    uptime_seconds: float
    total_runs: int
    active_runs: int
