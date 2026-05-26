from __future__ import annotations

import logging
import os

import anthropic

from app.models import (
    AutoTurnRequest,
    Goal,
    Run,
    SpecialistOutput,
    SpecialistRole,
    TurnInput,
)

logger = logging.getLogger(__name__)

_SUBMIT_TOOL: dict = {
    "name": "submit_specialist_turn",
    "description": (
        "Submit your structured contribution for this specialist turn in the multi-agent "
        "traffic circle. Call this exactly once."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "contribution": {
                "type": "string",
                "description": (
                    "Your substantive specialist contribution. Be concrete, actionable, "
                    "and mission-specific. Minimum 40 words. Empty string only when pass_turn is true."
                ),
            },
            "confidence": {
                "type": "number",
                "description": "Your confidence in this contribution, 0.0 (very uncertain) to 1.0 (certain).",
            },
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "1-3 short references supporting your contribution. "
                    "Format prior turns as 'turn:N:role', cite patterns as 'pattern:topic', "
                    "flag constraints as 'constraint:name'."
                ),
            },
            "suggested_next_role": {
                "type": "string",
                "enum": ["planner", "research", "executor", "critic", "verifier"],
                "description": "Which specialist should receive the baton next and why.",
            },
            "usefulness_score": {
                "type": "number",
                "description": "How useful this turn was to mission progress, 0.0 to 1.0.",
            },
            "pass_turn": {
                "type": "boolean",
                "description": (
                    "Set true ONLY if you genuinely have nothing new to add this turn. "
                    "Contribution must be empty string when true."
                ),
            },
        },
        "required": [
            "contribution",
            "confidence",
            "evidence_refs",
            "suggested_next_role",
            "usefulness_score",
            "pass_turn",
        ],
    },
}


def _build_context_message(goal: Goal, run: Run, user_prompt: str, role: SpecialistRole) -> str:
    lines: list[str] = []
    lines.append(f"GOAL: {goal.title}")
    lines.append(f"  Priority: {goal.priority.value}")
    if goal.success_criteria:
        lines.append("  Success criteria:")
        for c in goal.success_criteria:
            lines.append(f"    - {c}")
    if goal.constraints:
        lines.append("  Constraints:")
        for c in goal.constraints:
            lines.append(f"    - {c}")
    if goal.subgoals:
        lines.append(f"  Subgoals: {len(goal.subgoals)} tracked")

    lines.append("")
    lines.append("CURRENT RUN STATE:")
    lines.append(f"  Mode: {run.run_mode.value} | Round: {run.round_number} | Turn: {run.turn_number}")
    lines.append(f"  Active roles: {', '.join(r.value for r in run.active_roles)}")
    if run.paused_roles:
        lines.append(f"  Paused roles: {', '.join(r.value for r in run.paused_roles)}")

    recent = run.turn_history[-5:]
    if recent:
        lines.append("")
        lines.append(f"RECENT HISTORY ({len(recent)} of {len(run.turn_history)} turns):")
        for t in recent:
            preview = t.contribution[:300] + "..." if len(t.contribution) > 300 else t.contribution
            lines.append(f"  Turn {t.turn_number} [{t.role.value}] conf={t.confidence:.2f}:")
            lines.append(f"    {preview}")

    lines.append("")
    lines.append("USER MISSION PROMPT:")
    lines.append(user_prompt)
    lines.append("")
    lines.append(
        f"YOUR TURN: You are the {role.value} specialist. "
        f"Round {run.round_number}, turn {run.turn_number + 1}. "
        "Use the submit_specialist_turn tool to deliver your structured contribution."
    )
    return "\n".join(lines)


from dataclasses import dataclass


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

    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self._client: anthropic.AsyncAnthropic | None = (
            anthropic.AsyncAnthropic(api_key=api_key) if api_key else None
        )
        if self._client is None:
            logger.warning(
                "ANTHROPIC_API_KEY not set — SpecialistEngine will use template fallback mode. "
                "Set the env var to enable real LLM responses."
            )

    @property
    def provider_name(self) -> str:
        return "claude-opus-4-7" if self._client is not None else "template_fallback"

    async def build_turn(self, goal: Goal, run: Run, request: AutoTurnRequest) -> TurnInput:
        role = run.current_role
        profile = PROMPT_PROFILES[role]

        if self._client is not None:
            try:
                return await self._build_turn_via_claude(goal, run, request, role, profile)
            except Exception as exc:
                logger.warning(
                    "Claude API call failed for role=%s, falling back to template: %s",
                    role.value,
                    exc,
                )

        return self._build_turn_template(goal, run, request, role, profile)

    async def _build_turn_via_claude(
        self,
        goal: Goal,
        run: Run,
        request: AutoTurnRequest,
        role: SpecialistRole,
        profile: PromptProfile,
    ) -> TurnInput:
        assert self._client is not None
        context = _build_context_message(goal, run, request.user_prompt, role)

        response = await self._client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system=profile.system_prompt,
            messages=[{"role": "user", "content": context}],
            tools=[_SUBMIT_TOOL],
            tool_choice={"type": "tool", "name": "submit_specialist_turn"},
        )

        tool_input: dict | None = None
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_specialist_turn":
                tool_input = block.input  # type: ignore[assignment]
                break

        if tool_input is None:
            raise ValueError("Claude did not call submit_specialist_turn — unexpected response")

        pass_turn = bool(tool_input.get("pass_turn", False))
        contribution = str(tool_input.get("contribution", "")).strip()

        # Enforce TurnInput invariant: pass_turn XOR non-empty contribution
        if pass_turn and contribution:
            contribution = ""
        elif not pass_turn and not contribution:
            pass_turn = False
            contribution = "(specialist completed reasoning without a written contribution)"

        evidence_refs = [str(r) for r in tool_input.get("evidence_refs", [])][:3]
        confidence = float(max(0.0, min(1.0, tool_input.get("confidence", 0.7))))
        usefulness = float(max(0.0, min(1.0, tool_input.get("usefulness_score", 0.7))))

        suggested_next_role: SpecialistRole | None = None
        suggested_role_str = tool_input.get("suggested_next_role")
        if suggested_role_str:
            try:
                suggested_next_role = SpecialistRole(suggested_role_str)
            except ValueError:
                pass

        specialist_output = SpecialistOutput(
            role=role,
            provider=self.provider_name,
            prompt_title=profile.title,
            system_prompt=profile.system_prompt,
            message=contribution,
            checklist=self._build_checklist(goal, role),
            evidence_notes=self._build_evidence_notes(goal, run, role),
            suggested_next_role=suggested_next_role,
        )

        return TurnInput(
            role=role,
            user_prompt=request.user_prompt,
            contribution=contribution,
            confidence=confidence,
            evidence_refs=evidence_refs,
            usefulness_score=usefulness,
            pass_turn=pass_turn,
            requested_next_role=suggested_next_role,
            priority_override=request.priority_override,
            specialist_output=specialist_output,
        )

    def _build_turn_template(
        self,
        goal: Goal,
        run: Run,
        request: AutoTurnRequest,
        role: SpecialistRole,
        profile: PromptProfile,
    ) -> TurnInput:
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

    # ── template fallback helpers ──────────────────────────────────────────

    def _suggest_next_role(self, role: SpecialistRole, run: Run) -> SpecialistRole | None:
        def pick(preferred: list[SpecialistRole], fallback: SpecialistRole | None = None) -> SpecialistRole | None:
            for r in preferred:
                if r in run.active_roles and r not in run.paused_roles:
                    return r
            return fallback if fallback and fallback in run.active_roles else None

        if role == SpecialistRole.PLANNER:
            return pick([SpecialistRole.RESEARCH, SpecialistRole.EXECUTOR, SpecialistRole.VERIFIER], SpecialistRole.VERIFIER)
        if role == SpecialistRole.RESEARCH:
            return pick([SpecialistRole.VERIFIER, SpecialistRole.CRITIC, SpecialistRole.PLANNER], SpecialistRole.PLANNER)
        if role == SpecialistRole.VERIFIER:
            return pick([SpecialistRole.PLANNER, SpecialistRole.EXECUTOR, SpecialistRole.CRITIC], SpecialistRole.PLANNER)
        if role == SpecialistRole.EXECUTOR:
            return pick([SpecialistRole.VERIFIER, SpecialistRole.CRITIC, SpecialistRole.PLANNER], SpecialistRole.VERIFIER)
        return pick([SpecialistRole.PLANNER, SpecialistRole.VERIFIER, SpecialistRole.RESEARCH], SpecialistRole.PLANNER)

    def _build_evidence_refs(self, goal: Goal, run: Run, role: SpecialistRole) -> list[str]:
        import re
        def slugify(v: str) -> str:
            return re.sub(r"[^a-z0-9]+", "-", v.lower()).strip("-") or "untitled"

        refs: list[str] = []
        if goal.success_criteria:
            refs.append(f"criterion://{slugify(goal.success_criteria[0])}")
        if goal.constraints:
            refs.append(f"constraint://{slugify(goal.constraints[0])}")
        if run.turn_history:
            refs.append(f"turn://{run.turn_history[-1].turn_number}")
        role_refs = {
            SpecialistRole.RESEARCH: f"pattern://{slugify(goal.title)}",
            SpecialistRole.VERIFIER: f"verification://round-{run.round_number}",
            SpecialistRole.EXECUTOR: f"handoff://{run.current_role.value}",
            SpecialistRole.CRITIC: f"counterpoint://{slugify(goal.title)}",
        }
        if role in role_refs:
            refs.append(role_refs[role])
        return refs[:3]

    def _build_checklist(self, goal: Goal, role: SpecialistRole) -> list[str]:
        base = [
            "Keep the mission aligned with the user goal.",
            "Respect current constraints and fallback rules.",
        ]
        extras = {
            SpecialistRole.PLANNER: "Sequence the next baton handoff deliberately.",
            SpecialistRole.RESEARCH: "Surface evidence markers before making strong claims.",
            SpecialistRole.VERIFIER: "Block completion if proof quality is not high enough.",
            SpecialistRole.EXECUTOR: "Name the next concrete implementation move.",
            SpecialistRole.CRITIC: "Pressure-test hidden assumptions and edge cases.",
        }
        base.append(extras[role])
        if goal.subgoals:
            base.append(f"Account for {len(goal.subgoals)} tracked subgoals.")
        return base

    def _build_evidence_notes(self, goal: Goal, run: Run, role: SpecialistRole) -> list[str]:
        notes = [
            f"Mission priority is {goal.priority.value}.",
            f"Current fallback lane is derived from {len(run.turn_history)} prior turns.",
        ]
        if goal.constraints:
            notes.append(f"Primary constraint: {goal.constraints[0]}")
        if role == SpecialistRole.VERIFIER:
            notes.append("Verifier is checking whether completion can be safely unlocked.")
        return notes

    def _estimate_confidence(self, role: SpecialistRole, run: Run, evidence_refs: list[str]) -> float:
        base = {
            SpecialistRole.PLANNER: 0.74,
            SpecialistRole.RESEARCH: 0.80,
            SpecialistRole.VERIFIER: 0.84,
            SpecialistRole.EXECUTOR: 0.77,
            SpecialistRole.CRITIC: 0.72,
        }[role]
        return round(min(0.95, max(0.42, base + min(len(evidence_refs), 3) * 0.02 - (0.03 if role in run.paused_roles else 0.0))), 3)

    def _estimate_usefulness(self, role: SpecialistRole, run: Run) -> float:
        base = {
            SpecialistRole.PLANNER: 0.78,
            SpecialistRole.RESEARCH: 0.82,
            SpecialistRole.VERIFIER: 0.80,
            SpecialistRole.EXECUTOR: 0.79,
            SpecialistRole.CRITIC: 0.76,
        }[role]
        return round(max(0.35, base - (0.04 if len(run.paused_roles) > 1 else 0.0)), 3)

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
        next_label = suggested_next_role.value if suggested_next_role else "next-available"
        criteria = ", ".join(goal.success_criteria[:2]) or "no explicit criteria yet"
        evidence = ", ".join(evidence_refs)
        recent = ", ".join(recent_roles) if recent_roles else "fresh run"
        constraint = goal.constraints[0] if goal.constraints else "the current system constraints"

        if role == SpecialistRole.PLANNER:
            return (
                f"Mission frame: {user_prompt}\n"
                f"Execution lanes: center the goal '{goal.title}' around {criteria} while preserving {constraint}.\n"
                f"Routing decision: hand the baton to {next_label} after decomposition because recent traffic was {recent}.\n"
                f"Evidence markers: {evidence}."
            )
        if role == SpecialistRole.RESEARCH:
            return (
                f"Signals: the mission '{goal.title}' maps to {criteria} and needs stronger proof around '{user_prompt}'.\n"
                f"Useful evidence: {evidence}.\n"
                f"Open gap: the next role should be {next_label} to verify whether these signals are sufficient.\n"
                f"Research notes: {evidence_notes[-1]}."
            )
        if role == SpecialistRole.VERIFIER:
            return (
                f"Proof check: reviewing '{goal.title}' against {criteria}.\n"
                f"Release risks: verify evidence quality before completion and keep fallback visible if claims outrun proof.\n"
                f"Decision: baton should move to {next_label} after this audit.\n"
                f"Verifier evidence: {evidence}."
            )
        if role == SpecialistRole.EXECUTOR:
            return (
                f"Implementation move: translate '{user_prompt}' into the next concrete build step for '{goal.title}'.\n"
                f"Operational focus: keep the work aligned with {criteria}.\n"
                f"Delivery handoff: send the result to {next_label} once the move is framed.\n"
                f"Execution markers: {evidence}."
            )
        return (
            f"Contrarian read: the mission '{goal.title}' could fail if '{user_prompt}' is accepted without pressure testing.\n"
            f"Fragility points: recent traffic was {recent}, so hidden coupling may still be unchallenged.\n"
            f"Counter-move: push the baton to {next_label} with a tighter release bar.\n"
            f"Critic markers: {evidence}."
        )
