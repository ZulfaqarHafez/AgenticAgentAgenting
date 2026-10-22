//! The circle-junction scheduler: passes the baton between specialists, tracks
//! low-value streaks, handles verifier preemption, and evaluates the proof gate.

use std::collections::HashSet;

use indexmap::IndexMap;

use crate::error::{ApiError, ApiResult};
use crate::models::{
    DecisionEventType, DecisionLedgerEntry, FallbackLayer, ProofGateState, ProofGateStatus, Run,
    RunMode, RunReport, RunStartRequest, RunStatus, SpecialistRole, TurnInput, TurnOutcome,
    TurnRecord, new_event_id, round3, utc_now,
};

/// Minimum turns, distinct evidence refs, and average confidence a run needs to complete.
struct ProofGatePolicy {
    min_turns: u32,
    min_evidence: u32,
    min_confidence: f64,
}

fn proof_gate_policy(run_mode: RunMode) -> ProofGatePolicy {
    let (min_turns, min_evidence, min_confidence) = match run_mode {
        RunMode::Lite => (2, 1, 0.58),
        RunMode::Balanced => (3, 2, 0.68),
        RunMode::Power => (4, 3, 0.74),
    };
    ProofGatePolicy {
        min_turns,
        min_evidence,
        min_confidence,
    }
}

pub fn initialize_run(goal_id: &str, request: &RunStartRequest) -> ApiResult<Run> {
    let active_roles = match &request.active_roles {
        Some(roles) if !roles.is_empty() => roles.clone(),
        _ => return Err(ApiError::unprocessable("active_roles must not be empty")),
    };
    let mut run = Run::new(goal_id, request, active_roles);
    run.proof_gate_status = evaluate_proof_gate(&run);
    Ok(run)
}

/// Applies one specialist turn to the run. On error the run may be partly modified,
/// so callers should work on a copy and only keep it on success.
pub fn apply_turn(run: &mut Run, turn: TurnInput) -> ApiResult<()> {
    if run.status != RunStatus::Active {
        return Err(ApiError::conflict("run is not active"));
    }

    let fallback_before = fallback_layer(run);
    let previous_confidence = run
        .turn_history
        .last()
        .map_or(turn.confidence, |record| record.confidence);
    let mut expected_role = run.current_role;
    let mut role_activation_reason = run.current_role_activation_reason.clone();
    let mut was_preempted = false;

    if turn.priority_override
        && run.enable_priority_preemption
        && turn.role == SpecialistRole::Verifier
        && run.current_role != SpecialistRole::Verifier
        && let Some(verifier_index) = index_of(run, SpecialistRole::Verifier)
    {
        run.current_index = verifier_index;
        run.current_role = SpecialistRole::Verifier;
        expected_role = SpecialistRole::Verifier;
        role_activation_reason = "priority lane override triggered verifier preemption".into();
        was_preempted = true;
    }

    if turn.role != expected_role {
        return Err(ApiError::conflict(format!(
            "expected role '{}' but got '{}'",
            expected_role.as_str(),
            turn.role.as_str()
        )));
    }

    run.turn_number += 1;
    let role = turn.role;
    let mut reason = "normal turn";
    let mut outcome = TurnOutcome::Contributed;

    if turn.pass_turn {
        outcome = TurnOutcome::Passed;
        reason = "role passed due to low confidence or no new value";
        push_unique(&mut run.round_passes, role);
    } else {
        let streak = run.low_value_streaks.entry(role).or_insert(0);
        if turn.usefulness_score < run.min_usefulness {
            *streak += 1;
        } else {
            *streak = 0;
        }
        if *streak >= run.max_low_value_streak {
            push_unique(&mut run.paused_roles, role);
            outcome = TurnOutcome::AutoSkipped;
            reason = "role paused after consecutive low-value turns";
        }
    }

    if was_preempted && outcome != TurnOutcome::Passed {
        outcome = TurnOutcome::PriorityPreempted;
        reason = "verifier preempted this turn on priority lane";
    }

    let (next_index, next_role, next_role_activation_reason) = pick_next_role(run, &turn);
    let previous_index = run.current_index;
    run.current_index = next_index;
    run.current_role = next_role;
    run.current_role_activation_reason = next_role_activation_reason.clone();

    // Wrapping back to the same or an earlier seat means the baton went all the way round.
    if next_index <= previous_index {
        run.round_number += 1;
        run.round_passes.clear();
    }

    let fallback_after = fallback_layer_after_turn(run, fallback_before, outcome);
    run.turn_history.push(TurnRecord {
        turn_number: run.turn_number,
        round_number: run.round_number,
        role,
        user_prompt: turn.user_prompt,
        outcome,
        confidence: turn.confidence,
        confidence_delta_from_previous_turn: round3(turn.confidence - previous_confidence),
        usefulness_score: turn.usefulness_score,
        evidence_refs: turn.evidence_refs,
        contribution: turn.contribution,
        specialist_output: turn.specialist_output,
        role_activation_reason,
        requested_next_role: turn.requested_next_role,
        next_role,
        next_role_activation_reason,
        reason: reason.to_string(),
        fallback_layer_before: fallback_before,
        fallback_layer_after: fallback_after,
        fallback_transitioned: fallback_before != fallback_after,
        created_at: utc_now(),
    });
    run.proof_gate_status = evaluate_proof_gate(run);
    run.updated_at = utc_now();
    Ok(())
}

pub fn build_report(run: &Run) -> RunReport {
    let mut turn_counts: IndexMap<_, u32> = run.active_roles.iter().map(|r| (*r, 0)).collect();
    let mut pass_counts: IndexMap<_, u32> = turn_counts.clone();
    let mut usefulness: IndexMap<_, (f64, u32)> =
        run.active_roles.iter().map(|r| (*r, (0.0, 0))).collect();

    for record in &run.turn_history {
        if let Some(count) = turn_counts.get_mut(&record.role) {
            *count += 1;
        }
        if record.outcome == TurnOutcome::Passed
            && let Some(count) = pass_counts.get_mut(&record.role)
        {
            *count += 1;
        }
        if let Some((sum, count)) = usefulness.get_mut(&record.role) {
            *sum += record.usefulness_score;
            *count += 1;
        }
    }

    let role_avg_usefulness = usefulness
        .into_iter()
        .map(|(role, (sum, count))| {
            let average = if count == 0 {
                0.0
            } else {
                round3(sum / f64::from(count))
            };
            (role, average)
        })
        .collect();

    RunReport {
        run_id: run.run_id.clone(),
        goal_id: run.goal_id.clone(),
        status: run.status,
        turns: run.turn_number,
        rounds: run.round_number,
        activated_roles: run.active_roles.clone(),
        role_turn_counts: turn_counts,
        role_pass_counts: pass_counts,
        role_avg_usefulness,
        paused_roles: run.paused_roles.clone(),
        fallback_layer: fallback_layer(run),
        proof_gate_status: run.proof_gate_status.clone(),
    }
}

pub fn evaluate_proof_gate(run: &Run) -> ProofGateStatus {
    let policy = proof_gate_policy(run.run_mode);
    let turns_observed = run.turn_history.len() as u32;
    let evidence_refs: HashSet<&str> = run
        .turn_history
        .iter()
        .flat_map(|record| record.evidence_refs.iter())
        .filter(|reference| !reference.trim().is_empty())
        .map(String::as_str)
        .collect();
    let evidence_observed = evidence_refs.len() as u32;
    let verifier_turn_observed = run
        .turn_history
        .iter()
        .any(|record| record.role == SpecialistRole::Verifier);
    let observed_average_confidence = if turns_observed == 0 {
        0.0
    } else {
        let total: f64 = run
            .turn_history
            .iter()
            .map(|record| record.confidence)
            .sum();
        round3(total / f64::from(turns_observed))
    };

    let mut blockers = Vec::new();
    let mut cleared_checks = Vec::new();

    if turns_observed < policy.min_turns {
        blockers.push(format!(
            "Need at least {} specialist turns before completion.",
            policy.min_turns
        ));
    } else {
        cleared_checks.push(format!(
            "Minimum turn depth reached ({turns_observed}/{}).",
            policy.min_turns
        ));
    }

    if evidence_observed < policy.min_evidence {
        blockers.push(format!(
            "Need at least {} evidence markers before completion.",
            policy.min_evidence
        ));
    } else {
        cleared_checks.push(format!(
            "Evidence threshold cleared ({evidence_observed}/{}).",
            policy.min_evidence
        ));
    }

    if verifier_turn_observed {
        cleared_checks.push("Verifier review recorded.".to_string());
    } else {
        blockers.push("Verifier review must occur before completion.".to_string());
    }

    if observed_average_confidence < policy.min_confidence {
        blockers.push(format!(
            "Average confidence must reach {:.2} before completion.",
            policy.min_confidence
        ));
    } else {
        cleared_checks.push(format!(
            "Average confidence cleared ({observed_average_confidence:.2}/{:.2}).",
            policy.min_confidence
        ));
    }

    let ready = blockers.is_empty();
    ProofGateStatus {
        state: if ready {
            ProofGateState::Ready
        } else {
            ProofGateState::Blocked
        },
        ready_to_complete: ready,
        min_turns_required: policy.min_turns,
        turns_observed,
        evidence_refs_required: policy.min_evidence,
        evidence_refs_observed: evidence_observed,
        verifier_turn_required: true,
        verifier_turn_observed,
        minimum_average_confidence: policy.min_confidence,
        observed_average_confidence,
        blockers,
        cleared_checks,
        last_evaluated_at: utc_now(),
    }
}

/// Expands the turn history into role-activation, confidence-shift and fallback events.
pub fn build_decision_ledger(run: &Run) -> Vec<DecisionLedgerEntry> {
    let mut entries = Vec::new();
    for record in &run.turn_history {
        let base = DecisionLedgerEntry {
            event_id: new_event_id(),
            run_id: run.run_id.clone(),
            turn_number: record.turn_number,
            round_number: record.round_number,
            event_type: DecisionEventType::RoleActivation,
            role: Some(record.role),
            activated_role: Some(record.role),
            reason: record.role_activation_reason.clone(),
            confidence_before: None,
            confidence_after: None,
            confidence_delta: None,
            fallback_from: None,
            fallback_to: None,
            created_at: record.created_at,
        };
        entries.push(base.clone());

        entries.push(DecisionLedgerEntry {
            event_id: new_event_id(),
            event_type: DecisionEventType::ConfidenceShift,
            activated_role: None,
            reason: "confidence updated after specialist turn".to_string(),
            confidence_before: Some(round3(
                record.confidence - record.confidence_delta_from_previous_turn,
            )),
            confidence_after: Some(record.confidence),
            confidence_delta: Some(record.confidence_delta_from_previous_turn),
            ..base.clone()
        });

        if record.fallback_transitioned {
            let reason = if record.fallback_layer_after == FallbackLayer::VerifierGuard {
                "fallback layer changed due to verifier intervention"
            } else {
                "fallback layer changed due to run halt safeguard"
            };
            entries.push(DecisionLedgerEntry {
                event_id: new_event_id(),
                event_type: DecisionEventType::FallbackTransition,
                activated_role: None,
                reason: reason.to_string(),
                fallback_from: Some(record.fallback_layer_before),
                fallback_to: Some(record.fallback_layer_after),
                ..base
            });
        }
    }
    entries
}

pub fn fallback_layer(run: &Run) -> FallbackLayer {
    if run.status == RunStatus::Halted {
        FallbackLayer::SafeBaseline
    } else if run
        .turn_history
        .iter()
        .any(|record| record.outcome == TurnOutcome::PriorityPreempted)
    {
        FallbackLayer::VerifierGuard
    } else {
        FallbackLayer::CircleJunction
    }
}

fn fallback_layer_after_turn(
    run: &Run,
    fallback_before: FallbackLayer,
    outcome: TurnOutcome,
) -> FallbackLayer {
    if run.status == RunStatus::Halted {
        FallbackLayer::SafeBaseline
    } else if fallback_before == FallbackLayer::VerifierGuard
        || outcome == TurnOutcome::PriorityPreempted
    {
        FallbackLayer::VerifierGuard
    } else {
        FallbackLayer::CircleJunction
    }
}

fn push_unique(roles: &mut Vec<SpecialistRole>, role: SpecialistRole) {
    if !roles.contains(&role) {
        roles.push(role);
    }
}

fn index_of(run: &Run, role: SpecialistRole) -> Option<usize> {
    run.active_roles
        .iter()
        .position(|candidate| *candidate == role)
}

pub fn is_role_active(run: &Run, role: SpecialistRole) -> bool {
    run.active_roles.contains(&role) && !run.paused_roles.contains(&role)
}

fn pick_next_role(run: &mut Run, turn: &TurnInput) -> (usize, SpecialistRole, String) {
    let halt = |run: &mut Run, reason: &str| {
        run.status = RunStatus::Halted;
        (run.current_index, run.current_role, reason.to_string())
    };

    if !run
        .active_roles
        .iter()
        .any(|role| is_role_active(run, *role))
    {
        return halt(
            run,
            "no active specialists remain; run halted to safe baseline",
        );
    }

    if let Some(requested) = turn.requested_next_role {
        if requested != run.current_role
            && is_role_active(run, requested)
            && let Some(index) = index_of(run, requested)
        {
            return (
                index,
                requested,
                format!("explicit handoff requested by {}", turn.role.as_str()),
            );
        }
        if requested == run.current_role && same_role_repeat_allowed(run, requested) {
            return (
                run.current_index,
                run.current_role,
                "repeat turn allowed because all other active specialists passed".to_string(),
            );
        }
    }

    let total = run.active_roles.len();
    for offset in 1..=total {
        let index = (run.current_index + offset) % total;
        let candidate = run.active_roles[index];
        if is_role_active(run, candidate) {
            let reason = if offset == 1 {
                "standard round-robin baton advance"
            } else {
                "round-robin advance skipped paused specialists"
            };
            return (index, candidate, reason.to_string());
        }
    }

    halt(
        run,
        "no eligible specialist found; run halted to safe baseline",
    )
}

fn same_role_repeat_allowed(run: &Run, role: SpecialistRole) -> bool {
    run.active_roles
        .iter()
        .filter(|candidate| **candidate != role && is_role_active(run, **candidate))
        .all(|candidate| run.round_passes.contains(candidate))
}

#[cfg(test)]
mod tests {
    use super::*;
    use SpecialistRole::{Planner, Research, Verifier};

    fn build_run() -> Run {
        initialize_run(
            "G-1",
            &RunStartRequest {
                active_roles: Some(vec![Planner, Research, Verifier]),
                min_usefulness: 0.4,
                max_low_value_streak: 2,
                ..RunStartRequest::default()
            },
        )
        .unwrap()
    }

    #[test]
    fn rotation_advances_in_circle() {
        let mut run = build_run();
        apply_turn(
            &mut run,
            TurnInput::contribution(Planner, "Plan draft", 0.8, 0.7),
        )
        .unwrap();
        assert_eq!(run.current_role, Research);
        apply_turn(
            &mut run,
            TurnInput::contribution(Research, "Evidence lookup", 0.7, 0.8),
        )
        .unwrap();
        assert_eq!(run.current_role, Verifier);
        apply_turn(
            &mut run,
            TurnInput::contribution(Verifier, "Checked", 0.9, 0.8),
        )
        .unwrap();
        assert_eq!(run.current_role, Planner);
        assert_eq!(run.round_number, 2);
    }

    #[test]
    fn same_role_repeat_requires_other_passes() {
        let mut run = build_run();
        let turn = TurnInput {
            requested_next_role: Some(Planner),
            ..TurnInput::contribution(Planner, "First pass", 0.8, 0.8)
        };
        apply_turn(&mut run, turn).unwrap();
        assert_eq!(run.current_role, Research);
    }

    #[test]
    fn explicit_handoff_jumps_to_requested_role() {
        let mut run = build_run();
        let turn = TurnInput {
            requested_next_role: Some(Verifier),
            ..TurnInput::contribution(Planner, "Skip ahead", 0.8, 0.8)
        };
        apply_turn(&mut run, turn).unwrap();
        assert_eq!(run.current_role, Verifier);
        assert_eq!(
            run.current_role_activation_reason,
            "explicit handoff requested by planner"
        );
    }

    #[test]
    fn low_value_streak_pauses_role() {
        let mut run = build_run();
        apply_turn(
            &mut run,
            TurnInput::contribution(Planner, "Weak planning", 0.5, 0.1),
        )
        .unwrap();
        assert!(!run.paused_roles.contains(&Planner));
        apply_turn(
            &mut run,
            TurnInput::contribution(Research, "Strong evidence", 0.9, 0.8),
        )
        .unwrap();
        apply_turn(
            &mut run,
            TurnInput::contribution(Verifier, "Check pass", 0.9, 0.8),
        )
        .unwrap();
        apply_turn(
            &mut run,
            TurnInput::contribution(Planner, "Weak again", 0.4, 0.2),
        )
        .unwrap();
        assert!(run.paused_roles.contains(&Planner));
        assert_eq!(
            run.turn_history.last().unwrap().outcome,
            TurnOutcome::AutoSkipped
        );
        // The paused planner is skipped from now on.
        assert_eq!(run.current_role, Research);
    }

    #[test]
    fn priority_preemption_allows_verifier_interrupt() {
        let mut run = build_run();
        let turn = TurnInput {
            priority_override: true,
            ..TurnInput::contribution(Verifier, "Urgent contradiction found", 0.95, 0.9)
        };
        apply_turn(&mut run, turn).unwrap();
        assert_eq!(
            run.turn_history.last().unwrap().outcome,
            TurnOutcome::PriorityPreempted
        );
        let ledger = build_decision_ledger(&run);
        assert!(
            ledger
                .iter()
                .any(|e| e.event_type == DecisionEventType::FallbackTransition)
        );
        let order: Vec<_> = ledger.iter().map(|e| e.event_type).collect();
        assert_eq!(
            order,
            [
                DecisionEventType::RoleActivation,
                DecisionEventType::ConfidenceShift,
                DecisionEventType::FallbackTransition
            ]
        );
        assert_eq!(fallback_layer(&run), FallbackLayer::VerifierGuard);
    }

    #[test]
    fn wrong_role_is_a_conflict() {
        let mut run = build_run();
        let error = apply_turn(
            &mut run,
            TurnInput::contribution(Research, "Out of turn", 0.7, 0.7),
        )
        .unwrap_err();
        assert_eq!(error.status, axum::http::StatusCode::CONFLICT);
    }

    #[test]
    fn empty_roles_are_rejected() {
        let request = RunStartRequest {
            active_roles: Some(vec![]),
            ..RunStartRequest::default()
        };
        assert!(initialize_run("G-1", &request).is_err());
    }

    #[test]
    fn pausing_every_role_halts_run() {
        let mut run = initialize_run(
            "G-1",
            &RunStartRequest {
                active_roles: Some(vec![Planner]),
                max_low_value_streak: 1,
                ..RunStartRequest::default()
            },
        )
        .unwrap();
        apply_turn(
            &mut run,
            TurnInput::contribution(Planner, "Useless", 0.5, 0.0),
        )
        .unwrap();
        assert_eq!(run.status, RunStatus::Halted);
        assert_eq!(
            run.turn_history[0].fallback_layer_after,
            FallbackLayer::SafeBaseline
        );
        assert!(apply_turn(&mut run, TurnInput::contribution(Planner, "More", 0.5, 0.9)).is_err());
    }

    #[test]
    fn proof_gate_unlocks_after_enough_evidence() {
        let mut run = build_run();
        assert!(!run.proof_gate_status.ready_to_complete);
        for (role, reference) in [(Planner, "a"), (Research, "b"), (Verifier, "c")] {
            let turn = TurnInput {
                evidence_refs: vec![reference.to_string()],
                ..TurnInput::contribution(role, "work", 0.8, 0.8)
            };
            apply_turn(&mut run, turn).unwrap();
        }
        assert!(run.proof_gate_status.ready_to_complete);
        assert_eq!(run.proof_gate_status.state, ProofGateState::Ready);
        assert!(run.proof_gate_status.blockers.is_empty());
    }

    #[test]
    fn report_averages_usefulness_per_role() {
        let mut run = build_run();
        apply_turn(&mut run, TurnInput::contribution(Planner, "one", 0.8, 0.5)).unwrap();
        let report = build_report(&run);
        assert_eq!(report.role_turn_counts[&Planner], 1);
        assert_eq!(report.role_avg_usefulness[&Planner], 0.5);
        assert_eq!(report.role_avg_usefulness[&Verifier], 0.0);
    }
}
