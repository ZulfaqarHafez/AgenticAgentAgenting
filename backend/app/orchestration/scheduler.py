from __future__ import annotations

from collections import Counter, defaultdict

from fastapi import HTTPException

from app.models import (
    DecisionEventType,
    DecisionLedgerEntry,
    ProofGateState,
    ProofGateStatus,
    Run,
    RunReport,
    RunMode,
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
        if not request.active_roles:
            raise HTTPException(status_code=422, detail="active_roles must not be empty")
        current_role = request.active_roles[0]
        low_value_streaks = {role: 0 for role in request.active_roles}
        run = Run(
            goal_id=goal_id,
            run_mode=request.run_mode,
            active_roles=request.active_roles,
            current_role=current_role,
            low_value_streaks=low_value_streaks,
            min_usefulness=request.min_usefulness,
            max_low_value_streak=request.max_low_value_streak,
            enable_priority_preemption=request.enable_priority_preemption,
        )
        run.proof_gate_status = self.evaluate_proof_gate(run)
        return run

    def apply_turn(self, run: Run, turn: TurnInput) -> Run:
        if run.status != RunStatus.ACTIVE:
            raise HTTPException(status_code=409, detail="run is not active")

        fallback_before = self._fallback_layer(run)
        previous_confidence = (
            run.turn_history[-1].confidence if run.turn_history else turn.confidence
        )
        expected_role = run.current_role
        role_activation_reason = run.current_role_activation_reason
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
            role_activation_reason = "priority lane override triggered verifier preemption"
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

        next_index, next_role, next_role_activation_reason = self._pick_next_role(run, turn)
        previous_index = run.current_index
        run.current_index = next_index
        run.current_role = next_role
        run.current_role_activation_reason = next_role_activation_reason

        if self._crossed_round_boundary(previous_index, next_index):
            run.round_number += 1
            run.round_passes = []

        fallback_after = self._fallback_layer_after_turn(run, fallback_before, outcome)
        record = TurnRecord(
            turn_number=run.turn_number,
            round_number=run.round_number,
            role=role,
            user_prompt=turn.user_prompt,
            outcome=outcome,
            confidence=turn.confidence,
            confidence_delta_from_previous_turn=round(
                turn.confidence - previous_confidence, 3
            ),
            usefulness_score=turn.usefulness_score,
            evidence_refs=turn.evidence_refs,
            contribution=turn.contribution,
            specialist_output=turn.specialist_output,
            role_activation_reason=role_activation_reason,
            requested_next_role=turn.requested_next_role,
            next_role=next_role,
            next_role_activation_reason=next_role_activation_reason,
            reason=reason,
            fallback_layer_before=fallback_before,
            fallback_layer_after=fallback_after,
            fallback_transitioned=fallback_before != fallback_after,
        )
        run.turn_history.append(record)
        run.proof_gate_status = self.evaluate_proof_gate(run)
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
            proof_gate_status=run.proof_gate_status,
        )

    def evaluate_proof_gate(self, run: Run) -> ProofGateStatus:
        min_turns, min_evidence, min_confidence = self._proof_gate_policy(run.run_mode)
        turns_observed = len(run.turn_history)
        evidence_refs = {
            ref
            for record in run.turn_history
            for ref in record.evidence_refs
            if ref.strip()
        }
        verifier_turn_observed = any(
            record.role == SpecialistRole.VERIFIER for record in run.turn_history
        )
        observed_average_confidence = (
            round(
                sum(record.confidence for record in run.turn_history) / turns_observed,
                3,
            )
            if turns_observed
            else 0.0
        )

        blockers: list[str] = []
        cleared_checks: list[str] = []

        if turns_observed < min_turns:
            blockers.append(
                f"Need at least {min_turns} specialist turns before completion."
            )
        else:
            cleared_checks.append(f"Minimum turn depth reached ({turns_observed}/{min_turns}).")

        if len(evidence_refs) < min_evidence:
            blockers.append(
                f"Need at least {min_evidence} evidence markers before completion."
            )
        else:
            cleared_checks.append(
                f"Evidence threshold cleared ({len(evidence_refs)}/{min_evidence})."
            )

        if not verifier_turn_observed:
            blockers.append("Verifier review must occur before completion.")
        else:
            cleared_checks.append("Verifier review recorded.")

        if observed_average_confidence < min_confidence:
            blockers.append(
                f"Average confidence must reach {min_confidence:.2f} before completion."
            )
        else:
            cleared_checks.append(
                f"Average confidence cleared ({observed_average_confidence:.2f}/{min_confidence:.2f})."
            )

        ready = len(blockers) == 0
        return ProofGateStatus(
            state=ProofGateState.READY if ready else ProofGateState.BLOCKED,
            ready_to_complete=ready,
            min_turns_required=min_turns,
            turns_observed=turns_observed,
            evidence_refs_required=min_evidence,
            evidence_refs_observed=len(evidence_refs),
            verifier_turn_required=True,
            verifier_turn_observed=verifier_turn_observed,
            minimum_average_confidence=min_confidence,
            observed_average_confidence=observed_average_confidence,
            blockers=blockers,
            cleared_checks=cleared_checks,
            last_evaluated_at=utc_now(),
        )

    def _fallback_layer(self, run: Run) -> str:
        if run.status == RunStatus.HALTED:
            return "layer_3_safe_baseline"
        if run.turn_history and any(
            turn.outcome == TurnOutcome.PRIORITY_PREEMPTED for turn in run.turn_history
        ):
            return "layer_2_verifier_guard"
        return "layer_1_circle_junction"

    def _proof_gate_policy(self, run_mode: RunMode) -> tuple[int, int, float]:
        if run_mode == RunMode.LITE:
            return (2, 1, 0.58)
        if run_mode == RunMode.POWER:
            return (4, 3, 0.74)
        return (3, 2, 0.68)

    def build_decision_ledger(self, run: Run) -> list[DecisionLedgerEntry]:
        entries: list[DecisionLedgerEntry] = []
        for record in run.turn_history:
            entries.append(
                DecisionLedgerEntry(
                    run_id=run.run_id,
                    turn_number=record.turn_number,
                    round_number=record.round_number,
                    event_type=DecisionEventType.ROLE_ACTIVATION,
                    role=record.role,
                    activated_role=record.role,
                    reason=record.role_activation_reason,
                    created_at=record.created_at,
                )
            )
            confidence_before = round(
                record.confidence - record.confidence_delta_from_previous_turn, 3
            )
            entries.append(
                DecisionLedgerEntry(
                    run_id=run.run_id,
                    turn_number=record.turn_number,
                    round_number=record.round_number,
                    event_type=DecisionEventType.CONFIDENCE_SHIFT,
                    role=record.role,
                    reason="confidence updated after specialist turn",
                    confidence_before=confidence_before,
                    confidence_after=record.confidence,
                    confidence_delta=record.confidence_delta_from_previous_turn,
                    created_at=record.created_at,
                )
            )
            if record.fallback_transitioned:
                entries.append(
                    DecisionLedgerEntry(
                        run_id=run.run_id,
                        turn_number=record.turn_number,
                        round_number=record.round_number,
                        event_type=DecisionEventType.FALLBACK_TRANSITION,
                        role=record.role,
                        reason=(
                            "fallback layer changed due to verifier intervention"
                            if record.fallback_layer_after
                            == "layer_2_verifier_guard"
                            else "fallback layer changed due to run halt safeguard"
                        ),
                        fallback_from=record.fallback_layer_before,
                        fallback_to=record.fallback_layer_after,
                        created_at=record.created_at,
                    )
                )
        return entries

    def _fallback_layer_after_turn(
        self, run: Run, fallback_before: str, outcome: TurnOutcome
    ) -> str:
        if run.status == RunStatus.HALTED:
            return "layer_3_safe_baseline"
        if (
            fallback_before == "layer_2_verifier_guard"
            or outcome == TurnOutcome.PRIORITY_PREEMPTED
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

    def _pick_next_role(
        self, run: Run, turn: TurnInput
    ) -> tuple[int, SpecialistRole, str]:
        active_count = len([r for r in run.active_roles if self._is_role_active(run, r)])
        if active_count == 0:
            run.status = RunStatus.HALTED
            return (
                run.current_index,
                run.current_role,
                "no active specialists remain; run halted to safe baseline",
            )

        if (
            turn.requested_next_role
            and self._is_role_active(run, turn.requested_next_role)
            and turn.requested_next_role != run.current_role
        ):
            requested_index = run.active_roles.index(turn.requested_next_role)
            return (
                requested_index,
                turn.requested_next_role,
                f"explicit handoff requested by {turn.role.value}",
            )

        if (
            turn.requested_next_role == run.current_role
            and self._same_role_repeat_allowed(run, run.current_role)
        ):
            return (
                run.current_index,
                run.current_role,
                "repeat turn allowed because all other active specialists passed",
            )

        total_roles = len(run.active_roles)
        for offset in range(1, total_roles + 1):
            idx = (run.current_index + offset) % total_roles
            candidate = run.active_roles[idx]
            if self._is_role_active(run, candidate):
                if offset == 1:
                    reason = "standard round-robin baton advance"
                else:
                    reason = "round-robin advance skipped paused specialists"
                return idx, candidate, reason

        run.status = RunStatus.HALTED
        return (
            run.current_index,
            run.current_role,
            "no eligible specialist found; run halted to safe baseline",
        )

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
