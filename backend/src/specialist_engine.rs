//! Builds specialist turns automatically from templates.
//!
//! No language model is called: each role's message, evidence refs, confidence and
//! usefulness come from fixed rules over the goal and run state.

use crate::models::{
    AutoTurnRequest, Goal, Run, SpecialistOutput, SpecialistRole, TurnInput, round3,
};
use crate::scheduler::is_role_active;

pub const PROVIDER_NAME: &str = "prompted_local_engine";

/// Lowercases and joins runs of ASCII letters/digits with `-`.
fn slugify(value: &str) -> String {
    let lowered = value.to_lowercase();
    let mut slug = String::with_capacity(lowered.len());
    let mut pending_dash = false;
    for ch in lowered.chars() {
        if ch.is_ascii_lowercase() || ch.is_ascii_digit() {
            if pending_dash && !slug.is_empty() {
                slug.push('-');
            }
            pending_dash = false;
            slug.push(ch);
        } else {
            pending_dash = true;
        }
    }
    if slug.is_empty() {
        "untitled".to_string()
    } else {
        slug
    }
}

fn next_available_role(
    run: &Run,
    preferred: [SpecialistRole; 3],
    fallback: SpecialistRole,
) -> Option<SpecialistRole> {
    preferred
        .into_iter()
        .find(|role| is_role_active(run, *role))
        .or_else(|| run.active_roles.contains(&fallback).then_some(fallback))
}

struct PromptProfile {
    title: &'static str,
    system_prompt: &'static str,
}

fn prompt_profile(role: SpecialistRole) -> PromptProfile {
    match role {
        SpecialistRole::Planner => PromptProfile {
            title: "Planner mission decomposition",
            system_prompt: "You are the planner specialist in a multi-agent traffic circle. Break the mission \
                into execution lanes, preserve the user's intent, and hand the baton toward the \
                specialist that can validate the next highest-risk unknown.",
        },
        SpecialistRole::Research => PromptProfile {
            title: "Research evidence sweep",
            system_prompt: "You are the research specialist. Surface comparable patterns, useful evidence \
                markers, and unresolved unknowns. Favor concise, source-shaped findings that can \
                be verified by the verifier role.",
        },
        SpecialistRole::Verifier => PromptProfile {
            title: "Verifier proof gate review",
            system_prompt: "You are the verifier specialist. Audit claims, check whether evidence is adequate, \
                and decide if the current plan is safe to ship or should fall back to stricter review.",
        },
        SpecialistRole::Executor => PromptProfile {
            title: "Executor implementation move",
            system_prompt: "You are the executor specialist. Convert the mission into concrete implementation \
                moves, name the next change, and surface operational risk before handoff.",
        },
        SpecialistRole::Critic => PromptProfile {
            title: "Critic adversarial pressure test",
            system_prompt: "You are the critic specialist. Find blind spots, hidden coupling, and weak assumptions. \
                Offer a tighter counter-move instead of generic negativity.",
        },
    }
}

pub fn build_turn(goal: &Goal, run: &Run, request: &AutoTurnRequest) -> TurnInput {
    let role = run.current_role;
    let profile = prompt_profile(role);
    let recent_roles: Vec<&str> = run
        .turn_history
        .iter()
        .rev()
        .take(3)
        .rev()
        .map(|record| record.role.as_str())
        .collect();
    let suggested_next_role = suggest_next_role(role, run);
    let evidence_refs = build_evidence_refs(goal, run, role);
    let checklist = build_checklist(goal, role);
    let evidence_notes = build_evidence_notes(goal, run, role);
    let confidence = estimate_confidence(role, run, &evidence_refs);
    let usefulness = estimate_usefulness(role, run);
    let message = render_message(&MessageContext {
        goal,
        role,
        user_prompt: &request.user_prompt,
        suggested_next_role,
        recent_roles: &recent_roles,
        evidence_refs: &evidence_refs,
        evidence_notes: &evidence_notes,
    });

    TurnInput {
        role,
        user_prompt: request.user_prompt.clone(),
        contribution: message.clone(),
        confidence,
        evidence_refs,
        usefulness_score: usefulness,
        pass_turn: false,
        requested_next_role: suggested_next_role,
        priority_override: request.priority_override,
        specialist_output: Some(SpecialistOutput {
            role,
            provider: PROVIDER_NAME.to_string(),
            prompt_title: profile.title.to_string(),
            system_prompt: profile.system_prompt.to_string(),
            message,
            checklist,
            evidence_notes,
            suggested_next_role,
        }),
    }
}

fn suggest_next_role(role: SpecialistRole, run: &Run) -> Option<SpecialistRole> {
    use SpecialistRole::*;
    let (preferred, fallback) = match role {
        Planner => ([Research, Executor, Verifier], Verifier),
        Research => ([Verifier, Critic, Planner], Planner),
        Verifier => ([Planner, Executor, Critic], Planner),
        Executor => ([Verifier, Critic, Planner], Verifier),
        Critic => ([Planner, Verifier, Research], Planner),
    };
    next_available_role(run, preferred, fallback)
}

fn build_evidence_refs(goal: &Goal, run: &Run, role: SpecialistRole) -> Vec<String> {
    let mut refs = Vec::new();
    if let Some(criterion) = goal.success_criteria.first() {
        refs.push(format!("criterion://{}", slugify(criterion)));
    }
    if let Some(constraint) = goal.constraints.first() {
        refs.push(format!("constraint://{}", slugify(constraint)));
    }
    if let Some(last) = run.turn_history.last() {
        refs.push(format!("turn://{}", last.turn_number));
    }
    match role {
        SpecialistRole::Research => refs.push(format!("pattern://{}", slugify(&goal.title))),
        SpecialistRole::Verifier => refs.push(format!("verification://round-{}", run.round_number)),
        SpecialistRole::Executor => refs.push(format!("handoff://{}", run.current_role.as_str())),
        SpecialistRole::Critic => refs.push(format!("counterpoint://{}", slugify(&goal.title))),
        SpecialistRole::Planner => {}
    }
    refs.truncate(3);
    refs
}

fn build_checklist(goal: &Goal, role: SpecialistRole) -> Vec<String> {
    let mut checklist = vec![
        "Keep the mission aligned with the user goal.".to_string(),
        "Respect current constraints and fallback rules.".to_string(),
    ];
    checklist.push(
        match role {
            SpecialistRole::Planner => "Sequence the next baton handoff deliberately.",
            SpecialistRole::Research => "Surface evidence markers before making strong claims.",
            SpecialistRole::Verifier => "Block completion if proof quality is not high enough.",
            SpecialistRole::Executor => "Name the next concrete implementation move.",
            SpecialistRole::Critic => "Pressure-test hidden assumptions and edge cases.",
        }
        .to_string(),
    );
    if !goal.subgoals.is_empty() {
        checklist.push(format!(
            "Account for {} tracked subgoals.",
            goal.subgoals.len()
        ));
    }
    checklist
}

fn build_evidence_notes(goal: &Goal, run: &Run, role: SpecialistRole) -> Vec<String> {
    let mut notes = vec![
        format!("Mission priority is {}.", goal.priority.as_str()),
        format!(
            "Current fallback lane is derived from {} prior turns.",
            run.turn_history.len()
        ),
    ];
    if let Some(constraint) = goal.constraints.first() {
        notes.push(format!("Primary constraint: {constraint}"));
    }
    if role == SpecialistRole::Verifier {
        notes.push("Verifier is checking whether completion can be safely unlocked.".to_string());
    }
    notes
}

fn estimate_confidence(role: SpecialistRole, run: &Run, evidence_refs: &[String]) -> f64 {
    let base: f64 = match role {
        SpecialistRole::Planner => 0.74,
        SpecialistRole::Research => 0.8,
        SpecialistRole::Verifier => 0.84,
        SpecialistRole::Executor => 0.77,
        SpecialistRole::Critic => 0.72,
    };
    let evidence_bonus = evidence_refs.len().min(3) as f64 * 0.02;
    let history_penalty = if run.paused_roles.contains(&role) {
        0.03
    } else {
        0.0
    };
    round3((base + evidence_bonus - history_penalty).clamp(0.42, 0.95))
}

fn estimate_usefulness(role: SpecialistRole, run: &Run) -> f64 {
    let base: f64 = match role {
        SpecialistRole::Planner => 0.78,
        SpecialistRole::Research => 0.82,
        SpecialistRole::Verifier => 0.8,
        SpecialistRole::Executor => 0.79,
        SpecialistRole::Critic => 0.76,
    };
    let congestion_penalty = if run.paused_roles.len() > 1 {
        0.04
    } else {
        0.0
    };
    round3((base - congestion_penalty).max(0.35))
}

struct MessageContext<'a> {
    goal: &'a Goal,
    role: SpecialistRole,
    user_prompt: &'a str,
    suggested_next_role: Option<SpecialistRole>,
    recent_roles: &'a [&'a str],
    evidence_refs: &'a [String],
    evidence_notes: &'a [String],
}

fn render_message(ctx: &MessageContext) -> String {
    let goal = ctx.goal;
    let title = &goal.title;
    let user_prompt = ctx.user_prompt;
    let next_role = ctx
        .suggested_next_role
        .map_or("next-available", SpecialistRole::as_str);
    let criteria = if goal.success_criteria.is_empty() {
        "no explicit criteria yet".to_string()
    } else {
        goal.success_criteria
            .iter()
            .take(2)
            .cloned()
            .collect::<Vec<_>>()
            .join(", ")
    };
    let evidence = ctx.evidence_refs.join(", ");
    let recent = if ctx.recent_roles.is_empty() {
        "fresh run".to_string()
    } else {
        ctx.recent_roles.join(", ")
    };

    match ctx.role {
        SpecialistRole::Planner => {
            let constraint = goal
                .constraints
                .first()
                .map_or("the current system constraints", String::as_str);
            format!(
                "Mission frame: {user_prompt}\n\
                 Execution lanes: center the goal '{title}' around {criteria} while preserving {constraint}.\n\
                 Routing decision: hand the baton to {next_role} after decomposition because recent traffic was {recent}.\n\
                 Evidence markers: {evidence}."
            )
        }
        SpecialistRole::Research => {
            let last_note = ctx.evidence_notes.last().map_or("", String::as_str);
            format!(
                "Signals: the mission '{title}' maps to {criteria} and needs stronger proof around '{user_prompt}'.\n\
                 Useful evidence: {evidence}.\n\
                 Open gap: the next role should be {next_role} to verify whether these signals are sufficient.\n\
                 Research notes: {last_note}."
            )
        }
        SpecialistRole::Verifier => format!(
            "Proof check: reviewing '{title}' against {criteria}.\n\
             Release risks: verify evidence quality before completion and keep fallback visible if claims outrun proof.\n\
             Decision: baton should move to {next_role} after this audit.\n\
             Verifier evidence: {evidence}."
        ),
        SpecialistRole::Executor => format!(
            "Implementation move: translate '{user_prompt}' into the next concrete build step for '{title}'.\n\
             Operational focus: keep the work aligned with {criteria}.\n\
             Delivery handoff: send the result to {next_role} once the move is framed.\n\
             Execution markers: {evidence}."
        ),
        SpecialistRole::Critic => format!(
            "Contrarian read: the mission '{title}' could fail if '{user_prompt}' is accepted without pressure testing.\n\
             Fragility points: recent traffic was {recent}, so hidden coupling may still be unchallenged.\n\
             Counter-move: push the baton to {next_role} with a tighter release bar.\n\
             Critic markers: {evidence}."
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slugify_matches_python_behaviour() {
        assert_eq!(slugify("Latency under 15s!"), "latency-under-15s");
        assert_eq!(slugify("  --Hello__World--  "), "hello-world");
        assert_eq!(slugify("Café déjà"), "caf-d-j");
        assert_eq!(slugify("!!!"), "untitled");
    }
}
