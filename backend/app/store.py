from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from app.models import Goal, Run


@dataclass
class InMemoryState:
    goals: dict[str, Goal] = field(default_factory=dict)
    runs: dict[str, Run] = field(default_factory=dict)


class InMemoryStore:
    """Simple in-memory store for MVP development."""

    def __init__(self) -> None:
        self._state = InMemoryState()
        self._lock = Lock()

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

