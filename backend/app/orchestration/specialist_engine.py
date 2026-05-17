from __future__ import annotations

from dataclasses import dataclass
import re

from app.models import (
    AutoTurnRequest,
    Goal,
    Run,
    SpecialistOutput,
    SpecialistRole,
    TurnInput,
)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "untitled"


def _next_available_role(
    run: Run, preferred: list[SpecialistRole], fallback: SpecialistRole | None = None
) -> SpecialistRole | None:
    for role in preferred:
        if role in run.active_roles and role not in run.paused_roles:
            return role
    if fallback and fallback in run.active_roles:
        return fallback
    return None


@dataclass(frozen=True)
class PromptProfile:
    title: str
    system_prompt: str


PROMPT_PROFILES: dict[SpecialistRole, PromptProfile] = {
    SpecialistRole.PLANNER: PromptProfile(
        title="Planner mission decomposition",
        system_prompt=(
            "You are the planner specialist in a multi-agent traffic circle. Break the mission "
            "into execution lanes, preserve the user's intent, and hand the baton toward the "
            "specialist that can validate the next highest-risk unknown."
        ),
    ),
    SpecialistRole.RESEARCH: PromptProfile(
        title="Research evidence sweep",
        system_prompt=(
            "You are the research specialist. Surface comparable patterns, useful evidence "
            "markers, and unresolved unknowns. Favor concise, source-shaped findings that can "
            "be verified by the verifier role."
        ),
    ),
    SpecialistRole.VERIFIER: PromptProfile(
        title="Verifier proof gate review",
        system_prompt=(
            "You are the verifier specialist. Audit claims, check whether evidence is adequate, "
            "and decide if the current plan is safe to ship or should fall back to stricter review."
        ),
    ),
    SpecialistRole.EXECUTOR: PromptProfile(
        title="Executor implementation move",
        system_prompt=(
            "You are the executor specialist. Convert the mission into concrete implementation "
            "moves, name the next change, and surface operational risk before handoff."
        ),
    ),
    SpecialistRole.CRITIC: PromptProfile(
        title="Critic adversarial pressure test",
        system_prompt=(
            "You are the critic specialist. Find blind spots, hidden coupling, and weak assumptions. "
            "Offer a tighter counter-move instead of generic negativity."
        ),
    ),
}


class SpecialistEngine:
    provider_name = "prompted_local_engine"

    def build_turn(self, goal: Goal, run: Run, request: AutoTurnRequest) -> TurnInput:
        role = run.current_role
        profile = PROMPT_PROFILES[role]
        recent_roles = [record.role.value for record in run.turn_history[-3:]]
        suggested_next_role = self._suggest_next_role(role, run)
        evidence_refs = self._build_evidence_refs(goal, run, role)
        checklist = self._build_checklist(goal, role)
        evidence_notes = self._build_evidence_notes(goal, run, role)
        confidence = self._estimate_confidence(role, run, evidence_refs)
        usefulness = self._estimate_usefulness(role, run)
        message = self._render_message(
            goal=goal,
            run=run,
            role=role,
            user_prompt=request.user_prompt,
            suggested_next_role=suggested_next_role,
            recent_roles=recent_roles,
            evidence_refs=evidence_refs,
            evidence_notes=evidence_notes,
        )

        specialist_output = SpecialistOutput(
            role=role,
            provider=self.provider_name,
            prompt_title=profile.title,
            system_prompt=profile.system_prompt,
            message=message,
            checklist=checklist,
            evidence_notes=evidence_notes,
            suggested_next_role=suggested_next_role,
        )

        return TurnInput(
            role=role,
            user_prompt=request.user_prompt,
            contribution=message,
            confidence=confidence,
            evidence_refs=evidence_refs,
            usefulness_score=usefulness,
            pass_turn=False,
            requested_next_role=suggested_next_role,
            priority_override=request.priority_override,
            specialist_output=specialist_output,
        )

    def _suggest_next_role(self, role: SpecialistRole, run: Run) -> SpecialistRole | None:
        if role == SpecialistRole.PLANNER:
            return _next_available_role(
                run,
                [SpecialistRole.RESEARCH, SpecialistRole.EXECUTOR, SpecialistRole.VERIFIER],
                fallback=SpecialistRole.VERIFIER,
            )
        if role == SpecialistRole.RESEARCH:
            return _next_available_role(
                run,
                [SpecialistRole.VERIFIER, SpecialistRole.CRITIC, SpecialistRole.PLANNER],
                fallback=SpecialistRole.PLANNER,
            )
        if role == SpecialistRole.VERIFIER:
            return _next_available_role(
                run,
                [SpecialistRole.PLANNER, SpecialistRole.EXECUTOR, SpecialistRole.CRITIC],
                fallback=SpecialistRole.PLANNER,
            )
        if role == SpecialistRole.EXECUTOR:
            return _next_available_role(
                run,
                [SpecialistRole.VERIFIER, SpecialistRole.CRITIC, SpecialistRole.PLANNER],
                fallback=SpecialistRole.VERIFIER,
            )
        return _next_available_role(
            run,
            [SpecialistRole.PLANNER, SpecialistRole.VERIFIER, SpecialistRole.RESEARCH],
            fallback=SpecialistRole.PLANNER,
        )

    def _build_evidence_refs(
        self, goal: Goal, run: Run, role: SpecialistRole
    ) -> list[str]:
        refs: list[str] = []
        if goal.success_criteria:
            refs.append(f"criterion://{_slugify(goal.success_criteria[0])}")
        if goal.constraints:
            refs.append(f"constraint://{_slugify(goal.constraints[0])}")
        if run.turn_history:
            refs.append(f"turn://{run.turn_history[-1].turn_number}")
        if role == SpecialistRole.RESEARCH:
            refs.append(f"pattern://{_slugify(goal.title)}")
        if role == SpecialistRole.VERIFIER:
            refs.append(f"verification://round-{run.round_number}")
        if role == SpecialistRole.EXECUTOR:
            refs.append(f"handoff://{run.current_role.value}")
        if role == SpecialistRole.CRITIC:
            refs.append(f"counterpoint://{_slugify(goal.title)}")
        return refs[:3]

    def _build_checklist(self, goal: Goal, role: SpecialistRole) -> list[str]:
        base = [
            "Keep the mission aligned with the user goal.",
            "Respect current constraints and fallback rules.",
        ]
        if role == SpecialistRole.PLANNER:
            base.append("Sequence the next baton handoff deliberately.")
        elif role == SpecialistRole.RESEARCH:
            base.append("Surface evidence markers before making strong claims.")
        elif role == SpecialistRole.VERIFIER:
            base.append("Block completion if proof quality is not high enough.")
        elif role == SpecialistRole.EXECUTOR:
            base.append("Name the next concrete implementation move.")
        else:
            base.append("Pressure-test hidden assumptions and edge cases.")
        if goal.subgoals:
            base.append(f"Account for {len(goal.subgoals)} tracked subgoals.")
        return base

    def _build_evidence_notes(
        self, goal: Goal, run: Run, role: SpecialistRole
    ) -> list[str]:
        notes = [
            f"Mission priority is {goal.priority.value}.",
            f"Current fallback lane is derived from {len(run.turn_history)} prior turns.",
        ]
        if goal.constraints:
            notes.append(f"Primary constraint: {goal.constraints[0]}")
        if role == SpecialistRole.VERIFIER:
            notes.append("Verifier is checking whether completion can be safely unlocked.")
        return notes

    def _estimate_confidence(
        self, role: SpecialistRole, run: Run, evidence_refs: list[str]
    ) -> float:
        base = {
            SpecialistRole.PLANNER: 0.74,
            SpecialistRole.RESEARCH: 0.8,
            SpecialistRole.VERIFIER: 0.84,
            SpecialistRole.EXECUTOR: 0.77,
            SpecialistRole.CRITIC: 0.72,
        }[role]
        evidence_bonus = min(len(evidence_refs), 3) * 0.02
        history_penalty = 0.03 if role in run.paused_roles else 0.0
        return round(min(0.95, max(0.42, base + evidence_bonus - history_penalty)), 3)

    def _estimate_usefulness(self, role: SpecialistRole, run: Run) -> float:
        base = {
            SpecialistRole.PLANNER: 0.78,
            SpecialistRole.RESEARCH: 0.82,
            SpecialistRole.VERIFIER: 0.8,
            SpecialistRole.EXECUTOR: 0.79,
            SpecialistRole.CRITIC: 0.76,
        }[role]
        congestion_penalty = 0.04 if len(run.paused_roles) > 1 else 0.0
        return round(max(0.35, base - congestion_penalty), 3)

    def _render_message(
        self,
        goal: Goal,
        run: Run,
        role: SpecialistRole,
        user_prompt: str,
        suggested_next_role: SpecialistRole | None,
        recent_roles: list[str],
        evidence_refs: list[str],
        evidence_notes: list[str],
    ) -> str:
        next_role_label = suggested_next_role.value if suggested_next_role else "next-available"
        criteria_line = ", ".join(goal.success_criteria[:2]) or "no explicit criteria yet"
        evidence_line = ", ".join(evidence_refs)
        recent_line = ", ".join(recent_roles) if recent_roles else "fresh run"

        if role == SpecialistRole.PLANNER:
            return (
                f"Mission frame: {user_prompt}\n"
                f"Execution lanes: center the goal '{goal.title}' around {criteria_line} while preserving {goal.constraints[0] if goal.constraints else 'the current system constraints'}.\n"
                f"Routing decision: hand the baton to {next_role_label} after decomposition because recent traffic was {recent_line}.\n"
                f"Evidence markers: {evidence_line}."
            )
        if role == SpecialistRole.RESEARCH:
            return (
                f"Signals: the mission '{goal.title}' maps to {criteria_line} and needs stronger proof around '{user_prompt}'.\n"
                f"Useful evidence: {evidence_line}.\n"
                f"Open gap: the next role should be {next_role_label} to verify whether these signals are sufficient.\n"
                f"Research notes: {evidence_notes[-1]}."
            )
        if role == SpecialistRole.VERIFIER:
            return (
                f"Proof check: reviewing '{goal.title}' against {criteria_line}.\n"
                f"Release risks: verify evidence quality before completion and keep fallback visible if claims outrun proof.\n"
                f"Decision: baton should move to {next_role_label} after this audit.\n"
                f"Verifier evidence: {evidence_line}."
            )
        if role == SpecialistRole.EXECUTOR:
            return (
                f"Implementation move: translate '{user_prompt}' into the next concrete build step for '{goal.title}'.\n"
                f"Operational focus: keep the work aligned with {criteria_line}.\n"
                f"Delivery handoff: send the result to {next_role_label} once the move is framed.\n"
                f"Execution markers: {evidence_line}."
            )
        return (
            f"Contrarian read: the mission '{goal.title}' could fail if '{user_prompt}' is accepted without pressure testing.\n"
            f"Fragility points: recent traffic was {recent_line}, so hidden coupling may still be unchallenged.\n"
            f"Counter-move: push the baton to {next_role_label} with a tighter release bar.\n"
            f"Critic markers: {evidence_line}."
        )
