from __future__ import annotations

from dataclasses import dataclass

from app.models import (
    SkillRecommendation,
    SkillRecommendationRequest,
    SpecialistRole,
)


@dataclass(frozen=True)
class SkillProfile:
    expected_utility: float
    cost_penalty: float
    latency_penalty: float
    base_risk_reduction: float
    keywords: tuple[str, ...]


SKILL_PROFILES: dict[SpecialistRole, SkillProfile] = {
    SpecialistRole.PLANNER: SkillProfile(
        expected_utility=0.68,
        cost_penalty=0.19,
        latency_penalty=0.13,
        base_risk_reduction=0.22,
        keywords=("plan", "milestone", "roadmap", "sequence", "decompose"),
    ),
    SpecialistRole.RESEARCH: SkillProfile(
        expected_utility=0.66,
        cost_penalty=0.22,
        latency_penalty=0.18,
        base_risk_reduction=0.19,
        keywords=("research", "evidence", "source", "benchmark", "compare", "web"),
    ),
    SpecialistRole.VERIFIER: SkillProfile(
        expected_utility=0.62,
        cost_penalty=0.18,
        latency_penalty=0.12,
        base_risk_reduction=0.33,
        keywords=("verify", "risk", "safe", "accuracy", "audit", "validate"),
    ),
    SpecialistRole.EXECUTOR: SkillProfile(
        expected_utility=0.6,
        cost_penalty=0.24,
        latency_penalty=0.2,
        base_risk_reduction=0.17,
        keywords=("implement", "build", "execute", "deploy", "run"),
    ),
    SpecialistRole.CRITIC: SkillProfile(
        expected_utility=0.58,
        cost_penalty=0.2,
        latency_penalty=0.16,
        base_risk_reduction=0.28,
        keywords=("critique", "failure", "edge case", "tradeoff", "counter"),
    ),
}


def recommend_skills(request: SkillRecommendationRequest) -> list[SkillRecommendation]:
    text = " ".join(
        [request.goal_title, *request.success_criteria, *request.constraints]
    ).lower()
    roles = request.include_roles or list(SpecialistRole)

    recommendations: list[SkillRecommendation] = []
    for role in roles:
        profile = SKILL_PROFILES[role]
        keyword_hits = sum(1 for keyword in profile.keywords if keyword in text)
        keyword_boost = min(keyword_hits * 0.05, 0.2)
        utility = min(profile.expected_utility + keyword_boost, 1.0)
        risk_reduction = min(profile.base_risk_reduction + keyword_boost * 0.5, 1.0)

        activation_score = (
            utility - profile.cost_penalty - profile.latency_penalty + risk_reduction
        )
        rationale = (
            f"{keyword_hits} keyword hits; utility {utility:.2f}, risk {risk_reduction:.2f}"
        )
        recommendations.append(
            SkillRecommendation(
                role=role,
                activation_score=round(activation_score, 3),
                expected_utility=round(utility, 3),
                cost_penalty=profile.cost_penalty,
                latency_penalty=profile.latency_penalty,
                risk_reduction=round(risk_reduction, 3),
                rationale=rationale,
            )
        )

    recommendations.sort(key=lambda item: item.activation_score, reverse=True)
    return recommendations[: request.limit]

