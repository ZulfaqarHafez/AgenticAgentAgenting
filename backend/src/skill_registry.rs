//! Scores which specialists are worth activating for a goal, based on keyword hits
//! against fixed utility/cost/latency/risk profiles.

use crate::models::{SkillRecommendation, SkillRecommendationRequest, SpecialistRole, round3};

struct SkillProfile {
    expected_utility: f64,
    cost_penalty: f64,
    latency_penalty: f64,
    base_risk_reduction: f64,
    keywords: &'static [&'static str],
}

fn profile(role: SpecialistRole) -> SkillProfile {
    match role {
        SpecialistRole::Planner => SkillProfile {
            expected_utility: 0.68,
            cost_penalty: 0.19,
            latency_penalty: 0.13,
            base_risk_reduction: 0.22,
            keywords: &["plan", "milestone", "roadmap", "sequence", "decompose"],
        },
        SpecialistRole::Research => SkillProfile {
            expected_utility: 0.66,
            cost_penalty: 0.22,
            latency_penalty: 0.18,
            base_risk_reduction: 0.19,
            keywords: &[
                "research",
                "evidence",
                "source",
                "benchmark",
                "compare",
                "web",
            ],
        },
        SpecialistRole::Verifier => SkillProfile {
            expected_utility: 0.62,
            cost_penalty: 0.18,
            latency_penalty: 0.12,
            base_risk_reduction: 0.33,
            keywords: &["verify", "risk", "safe", "accuracy", "audit", "validate"],
        },
        SpecialistRole::Executor => SkillProfile {
            expected_utility: 0.6,
            cost_penalty: 0.24,
            latency_penalty: 0.2,
            base_risk_reduction: 0.17,
            keywords: &["implement", "build", "execute", "deploy", "run"],
        },
        SpecialistRole::Critic => SkillProfile {
            expected_utility: 0.58,
            cost_penalty: 0.2,
            latency_penalty: 0.16,
            base_risk_reduction: 0.28,
            keywords: &["critique", "failure", "edge case", "tradeoff", "counter"],
        },
    }
}

/// Returns up to `request.limit` roles, best activation score first.
pub fn recommend_skills(request: &SkillRecommendationRequest) -> Vec<SkillRecommendation> {
    let text = std::iter::once(&request.goal_title)
        .chain(&request.success_criteria)
        .chain(&request.constraints)
        .map(String::as_str)
        .collect::<Vec<_>>()
        .join(" ")
        .to_lowercase();

    let roles: &[SpecialistRole] = match &request.include_roles {
        Some(roles) if !roles.is_empty() => roles,
        _ => &SpecialistRole::ALL,
    };

    let mut recommendations: Vec<SkillRecommendation> = roles
        .iter()
        .map(|role| {
            let profile = profile(*role);
            let keyword_hits = profile
                .keywords
                .iter()
                .filter(|kw| text.contains(**kw))
                .count();
            let keyword_boost = (keyword_hits as f64 * 0.05).min(0.2);
            let utility = (profile.expected_utility + keyword_boost).min(1.0);
            let risk_reduction = (profile.base_risk_reduction + keyword_boost * 0.5).min(1.0);
            let activation_score =
                utility - profile.cost_penalty - profile.latency_penalty + risk_reduction;

            SkillRecommendation {
                role: *role,
                activation_score: round3(activation_score),
                expected_utility: round3(utility),
                cost_penalty: profile.cost_penalty,
                latency_penalty: profile.latency_penalty,
                risk_reduction: round3(risk_reduction),
                rationale: format!(
                    "{keyword_hits} keyword hits; utility {utility:.2}, risk {risk_reduction:.2}"
                ),
            }
        })
        .collect();

    // Stable sort, so ties keep their input order.
    recommendations.sort_by(|a, b| b.activation_score.total_cmp(&a.activation_score));
    recommendations.truncate(request.limit);
    recommendations
}

#[cfg(test)]
mod tests {
    use super::*;

    fn request(title: &str) -> SkillRecommendationRequest {
        SkillRecommendationRequest {
            goal_title: title.to_string(),
            success_criteria: vec![],
            constraints: vec![],
            include_roles: None,
            limit: 5,
        }
    }

    #[test]
    fn keywords_boost_matching_roles() {
        let recs = recommend_skills(&request("Research evidence and benchmark sources"));
        assert_eq!(recs[0].role, SpecialistRole::Research);
        assert!(recs[0].rationale.starts_with("4 keyword hits"));
    }

    #[test]
    fn without_keywords_verifier_ranks_first() {
        let recs = recommend_skills(&request("Something neutral"));
        let roles: Vec<_> = recs.iter().map(|r| r.role).collect();
        assert_eq!(
            roles,
            [
                SpecialistRole::Verifier,
                SpecialistRole::Planner,
                SpecialistRole::Critic,
                SpecialistRole::Research,
                SpecialistRole::Executor
            ]
        );
        assert_eq!(recs[0].activation_score, 0.65);
    }
}
