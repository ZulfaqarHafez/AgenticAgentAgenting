from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class GoalPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class RunStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    HALTED = "halted"


class RunMode(str, Enum):
    LITE = "lite"
    BALANCED = "balanced"
    POWER = "power"


class SpecialistRole(str, Enum):
    RESEARCH = "research"
    PLANNER = "planner"
    EXECUTOR = "executor"
    CRITIC = "critic"
    VERIFIER = "verifier"


class TurnOutcome(str, Enum):
    CONTRIBUTED = "contributed"
    PASSED = "passed"
    AUTO_SKIPPED = "auto_skipped"
    PRIORITY_PREEMPTED = "priority_preempted"


class DecisionEventType(str, Enum):
    ROLE_ACTIVATION = "role_activation"
    FALLBACK_TRANSITION = "fallback_transition"
    CONFIDENCE_SHIFT = "confidence_shift"


class Subgoal(BaseModel):
    id: str = Field(default_factory=lambda: f"SG-{uuid4().hex[:8]}")
    title: str
    done: bool = False
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    evidence_count: int = 0
    blocking_reason: str | None = None


class GoalCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    success_criteria: list[str] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    priority: GoalPriority = GoalPriority.MEDIUM
    subgoals: list[Subgoal] = Field(default_factory=list)


class Goal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"G-{uuid4().hex[:10]}")
    title: str
    success_criteria: list[str]
    constraints: list[str]
    priority: GoalPriority
    status: GoalStatus = GoalStatus.ACTIVE
    subgoals: list[Subgoal] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RunStartRequest(BaseModel):
    run_mode: RunMode = RunMode.BALANCED
    active_roles: list[SpecialistRole] | None = None
    include_roles: list[SpecialistRole] | None = None
    auto_role_limit: int = Field(default=3, ge=1, le=5)
    min_usefulness: Annotated[float, Field(ge=0.0, le=1.0)] = 0.35
    max_low_value_streak: int = Field(ge=1, le=10, default=2)
    enable_priority_preemption: bool = True


class TurnInput(BaseModel):
    role: SpecialistRole
    contribution: str = ""
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    usefulness_score: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    pass_turn: bool = False
    requested_next_role: SpecialistRole | None = None
    priority_override: bool = False

    @model_validator(mode="after")
    def validate_turn_payload(self) -> "TurnInput":
        if not self.pass_turn and not self.contribution.strip():
            raise ValueError("contribution is required when pass_turn is false")
        if self.pass_turn and self.contribution.strip():
            raise ValueError("contribution must be empty when pass_turn is true")
        return self


class TurnRecord(BaseModel):
    turn_number: int
    round_number: int
    role: SpecialistRole
    outcome: TurnOutcome
    confidence: float
    confidence_delta_from_previous_turn: float
    usefulness_score: float
    evidence_refs: list[str]
    contribution: str
    role_activation_reason: str
    requested_next_role: SpecialistRole | None
    next_role: SpecialistRole
    next_role_activation_reason: str
    reason: str
    fallback_layer_before: str
    fallback_layer_after: str
    fallback_transitioned: bool
    created_at: datetime = Field(default_factory=utc_now)


class Run(BaseModel):
    run_id: str = Field(default_factory=lambda: f"R-{uuid4().hex[:10]}")
    goal_id: str
    run_mode: RunMode = RunMode.BALANCED
    active_roles: list[SpecialistRole]
    activation_strategy: str = "manual_active_roles"
    activation_recommendations: list["SkillRecommendation"] = Field(default_factory=list)
    current_index: int = 0
    current_role: SpecialistRole
    current_role_activation_reason: str = (
        "run started with first configured specialist in rotation"
    )
    round_number: int = 1
    turn_number: int = 0
    round_passes: list[SpecialistRole] = Field(default_factory=list)
    low_value_streaks: dict[SpecialistRole, int]
    paused_roles: list[SpecialistRole] = Field(default_factory=list)
    status: RunStatus = RunStatus.ACTIVE
    turn_history: list[TurnRecord] = Field(default_factory=list)
    min_usefulness: float
    max_low_value_streak: int
    enable_priority_preemption: bool
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class RunReport(BaseModel):
    run_id: str
    goal_id: str
    status: RunStatus
    turns: int
    rounds: int
    activated_roles: list[SpecialistRole]
    role_turn_counts: dict[SpecialistRole, int]
    role_pass_counts: dict[SpecialistRole, int]
    role_avg_usefulness: dict[SpecialistRole, float]
    paused_roles: list[SpecialistRole]
    fallback_layer: str


class DecisionLedgerEntry(BaseModel):
    event_id: str = Field(default_factory=lambda: f"E-{uuid4().hex[:10]}")
    run_id: str
    turn_number: int
    round_number: int
    event_type: DecisionEventType
    role: SpecialistRole | None = None
    activated_role: SpecialistRole | None = None
    reason: str
    confidence_before: float | None = None
    confidence_after: float | None = None
    confidence_delta: float | None = None
    fallback_from: str | None = None
    fallback_to: str | None = None
    created_at: datetime


class SkillRecommendationRequest(BaseModel):
    goal_title: str = Field(min_length=3, max_length=240)
    success_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    include_roles: list[SpecialistRole] | None = None
    limit: int = Field(default=5, ge=1, le=5)


class SkillRecommendation(BaseModel):
    role: SpecialistRole
    activation_score: float
    expected_utility: float
    cost_penalty: float
    latency_penalty: float
    risk_reduction: float
    rationale: str
