from fastapi import HTTPException
import pytest

from app.models import Run, RunStartRequest, SpecialistRole, TurnInput, TurnOutcome
from app.orchestration.scheduler import CircleJunctionScheduler


def _build_run() -> tuple[CircleJunctionScheduler, Run]:
    scheduler = CircleJunctionScheduler()
    run = scheduler.initialize_run(
        goal_id="G-1",
        request=RunStartRequest(
            active_roles=[
                SpecialistRole.PLANNER,
                SpecialistRole.RESEARCH,
                SpecialistRole.VERIFIER,
            ],
            min_usefulness=0.4,
            max_low_value_streak=2,
        ),
    )
    return scheduler, run


def test_rotation_advances_in_circle() -> None:
    scheduler, run = _build_run()
    run = scheduler.apply_turn(
        run,
        TurnInput(
            role=SpecialistRole.PLANNER,
            contribution="Plan draft",
            confidence=0.8,
            usefulness_score=0.7,
        ),
    )
    assert run.current_role == SpecialistRole.RESEARCH
    run = scheduler.apply_turn(
        run,
        TurnInput(
            role=SpecialistRole.RESEARCH,
            contribution="Evidence lookup",
            confidence=0.7,
            usefulness_score=0.8,
        ),
    )
    assert run.current_role == SpecialistRole.VERIFIER


def test_same_role_repeat_requires_other_passes() -> None:
    scheduler, run = _build_run()
    run = scheduler.apply_turn(
        run,
        TurnInput(
            role=SpecialistRole.PLANNER,
            contribution="First pass",
            confidence=0.8,
            usefulness_score=0.8,
            requested_next_role=SpecialistRole.PLANNER,
        ),
    )
    assert run.current_role == SpecialistRole.RESEARCH


def test_low_value_streak_pauses_role() -> None:
    scheduler, run = _build_run()
    run = scheduler.apply_turn(
        run,
        TurnInput(
            role=SpecialistRole.PLANNER,
            contribution="Weak planning",
            confidence=0.5,
            usefulness_score=0.1,
        ),
    )
    assert SpecialistRole.PLANNER not in run.paused_roles

    run = scheduler.apply_turn(
        run,
        TurnInput(
            role=SpecialistRole.RESEARCH,
            contribution="Strong evidence",
            confidence=0.9,
            usefulness_score=0.8,
        ),
    )
    run = scheduler.apply_turn(
        run,
        TurnInput(
            role=SpecialistRole.VERIFIER,
            contribution="Check pass",
            confidence=0.9,
            usefulness_score=0.8,
        ),
    )
    run = scheduler.apply_turn(
        run,
        TurnInput(
            role=SpecialistRole.PLANNER,
            contribution="Weak planning again",
            confidence=0.4,
            usefulness_score=0.2,
        ),
    )
    assert SpecialistRole.PLANNER in run.paused_roles
    assert run.turn_history[-1].outcome == TurnOutcome.AUTO_SKIPPED


def test_priority_preemption_allows_verifier_interrupt() -> None:
    scheduler, run = _build_run()
    run = scheduler.apply_turn(
        run,
        TurnInput(
            role=SpecialistRole.VERIFIER,
            contribution="Urgent contradiction found",
            confidence=0.95,
            usefulness_score=0.9,
            priority_override=True,
        ),
    )
    assert run.turn_history[-1].outcome == TurnOutcome.PRIORITY_PREEMPTED
    ledger = scheduler.build_decision_ledger(run)
    assert any(event.event_type.value == "fallback_transition" for event in ledger)


def test_wrong_role_raises_conflict() -> None:
    scheduler, run = _build_run()
    with pytest.raises(HTTPException):
        scheduler.apply_turn(
            run,
            TurnInput(
                role=SpecialistRole.RESEARCH,
                contribution="Out of turn",
                confidence=0.7,
                usefulness_score=0.7,
            ),
        )
