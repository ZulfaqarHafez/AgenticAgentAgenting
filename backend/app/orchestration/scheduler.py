from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import HTTPException

from app.models import (
    Run,
    RunReport,
    RunStartRequest,
    RunStatus,
    SpecialistRole,
    TurnInput,
    TurnOutcome,
    TurnRecord,
    utc_now,
)


class CircleJunctionScheduler:
    def initialize_run(self, goal_id: str, request: RunStartRequest) -> Run:
        current_role = request.active_roles[0]
        low_value_streaks = {role: 0 for role in request.active_roles}
        return Run(
            goal_id=goal_id,
            active_roles=request.active_roles,
            current_role=current_role,
            low_value_streaks=low_value_streaks,
            min_usefulness=request.min_usefulness,
            max_low_value_streak=request.max_low_value_streak,
            enable_priority_preemption=request.enable_priority_preemption,
        )

    def apply_turn(self, run: Run, turn: TurnInput) -> Run:
        if run.status != RunStatus.ACTIVE:
            raise HTTPException(status_code=409, detail="run is not active")

        expected_role = run.current_role
        was_preempted = False

        if (
            turn.priority_override
            and run.enable_priority_preemption
            and turn.role == SpecialistRole.VERIFIER
            and turn.role in run.active_roles
            and run.current_role != SpecialistRole.VERIFIER
        ):
            run.current_index = run.active_roles.index(SpecialistRole.VERIFIER)
            expected_role = SpecialistRole.VERIFIER
            run.current_role = SpecialistRole.VERIFIER
            was_preempted = True

        if turn.role != expected_role:
            raise HTTPException(
                status_code=409,
                detail=f"expected role '{expected_role.value}' but got '{turn.role.value}'",
            )

        run.turn_number += 1
        role = turn.role
        reason = "normal turn"
        outcome = TurnOutcome.CONTRIBUTED

        if turn.pass_turn:
            outcome = TurnOutcome.PASSED
            reason = "role passed due to low confidence or no new value"
            self._mark_pass(run, role)
        else:
            if turn.usefulness_score < run.min_usefulness:
                run.low_value_streaks[role] = run.low_value_streaks.get(role, 0) + 1
            else:
                run.low_value_streaks[role] = 0
            if run.low_value_streaks[role] >= run.max_low_value_streak:
                self._pause_role(run, role)
                outcome = TurnOutcome.AUTO_SKIPPED
                reason = "role paused after consecutive low-value turns"

        if was_preempted and outcome != TurnOutcome.PASSED:
            outcome = TurnOutcome.PRIORITY_PREEMPTED
            reason = "verifier preempted this turn on priority lane"

        next_index, next_role = self._pick_next_role(run, turn)
        previous_index = run.current_index
        run.current_index = next_index
        run.current_role = next_role

        if self._crossed_round_boundary(previous_index, next_index):
            run.round_number += 1
            run.round_passes = []

        record = TurnRecord(
            turn_number=run.turn_number,
            round_number=run.round_number,
            role=role,
            outcome=outcome,
            confidence=turn.confidence,
            usefulness_score=turn.usefulness_score,
            evidence_refs=turn.evidence_refs,
            contribution=turn.contribution,
            requested_next_role=turn.requested_next_role,
            next_role=next_role,
            reason=reason,
        )
        run.turn_history.append(record)
        run.updated_at = utc_now()
        return run

    def build_report(self, run: Run) -> RunReport:
        turn_counts: Counter[SpecialistRole] = Counter()
        pass_counts: Counter[SpecialistRole] = Counter()
        usefulness_sum: defaultdict[SpecialistRole, float] = defaultdict(float)
        usefulness_count: Counter[SpecialistRole] = Counter()

        for record in run.turn_history:
            turn_counts[record.role] += 1
            if record.outcome == TurnOutcome.PASSED:
                pass_counts[record.role] += 1
            usefulness_sum[record.role] += record.usefulness_score
            usefulness_count[record.role] += 1

        avg_usefulness: dict[SpecialistRole, float] = {}
        for role in run.active_roles:
            if usefulness_count[role] == 0:
                avg_usefulness[role] = 0.0
            else:
                avg_usefulness[role] = round(
                    usefulness_sum[role] / usefulness_count[role], 3
                )

        return RunReport(
            run_id=run.run_id,
            goal_id=run.goal_id,
            status=run.status,
            turns=run.turn_number,
            rounds=run.round_number,
            activated_roles=run.active_roles,
            role_turn_counts={role: turn_counts[role] for role in run.active_roles},
            role_pass_counts={role: pass_counts[role] for role in run.active_roles},
            role_avg_usefulness=avg_usefulness,
            paused_roles=run.paused_roles,
            fallback_layer=self._fallback_layer(run),
        )

    def _fallback_layer(self, run: Run) -> str:
        if run.status == RunStatus.HALTED:
            return "layer_3_safe_baseline"
        if run.turn_history and any(
            turn.outcome == TurnOutcome.PRIORITY_PREEMPTED for turn in run.turn_history
        ):
            return "layer_2_verifier_guard"
        return "layer_1_circle_junction"

    def _mark_pass(self, run: Run, role: SpecialistRole) -> None:
        if role not in run.round_passes:
            run.round_passes.append(role)

    def _pause_role(self, run: Run, role: SpecialistRole) -> None:
        if role not in run.paused_roles:
            run.paused_roles.append(role)

    def _is_role_active(self, run: Run, role: SpecialistRole) -> bool:
        return role in run.active_roles and role not in run.paused_roles

    def _pick_next_role(self, run: Run, turn: TurnInput) -> tuple[int, SpecialistRole]:
        active_count = len([r for r in run.active_roles if self._is_role_active(run, r)])
        if active_count == 0:
            run.status = RunStatus.HALTED
            return run.current_index, run.current_role

        if (
            turn.requested_next_role
            and self._is_role_active(run, turn.requested_next_role)
            and turn.requested_next_role != run.current_role
        ):
            requested_index = run.active_roles.index(turn.requested_next_role)
            return requested_index, turn.requested_next_role

        if (
            turn.requested_next_role == run.current_role
            and self._same_role_repeat_allowed(run, run.current_role)
        ):
            return run.current_index, run.current_role

        total_roles = len(run.active_roles)
        for offset in range(1, total_roles + 1):
            idx = (run.current_index + offset) % total_roles
            candidate = run.active_roles[idx]
            if self._is_role_active(run, candidate):
                return idx, candidate

        run.status = RunStatus.HALTED
        return run.current_index, run.current_role

    def _same_role_repeat_allowed(self, run: Run, role: SpecialistRole) -> bool:
        other_active = [
            candidate
            for candidate in run.active_roles
            if candidate != role and self._is_role_active(run, candidate)
        ]
        if not other_active:
            return True
        return all(candidate in run.round_passes for candidate in other_active)

    def _crossed_round_boundary(self, previous_index: int, next_index: int) -> bool:
        return next_index <= previous_index

