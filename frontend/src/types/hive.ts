export type GoalPriority = "low" | "medium" | "high" | "critical";
export type GoalStatus = "active" | "completed" | "blocked";
export type RunStatus = "active" | "completed" | "halted";
export type RunMode = "lite" | "balanced" | "power";
export type ProofGateState = "ready" | "blocked";
export type SpecialistRole =
  | "research"
  | "planner"
  | "executor"
  | "critic"
  | "verifier";
export type DecisionEventType =
  | "role_activation"
  | "fallback_transition"
  | "confidence_shift";

export interface Goal {
  goal_id: string;
  title: string;
  success_criteria: string[];
  constraints: string[];
  priority: GoalPriority;
  status: GoalStatus;
}

export interface TurnRecord {
  turn_number: number;
  round_number: number;
  role: SpecialistRole;
  user_prompt: string;
  outcome: string;
  confidence: number;
  confidence_delta_from_previous_turn: number;
  usefulness_score: number;
  evidence_refs: string[];
  contribution: string;
  specialist_output?: SpecialistOutput | null;
  role_activation_reason: string;
  requested_next_role?: SpecialistRole | null;
  next_role: SpecialistRole;
  next_role_activation_reason: string;
  reason: string;
  fallback_layer_before: string;
  fallback_layer_after: string;
  fallback_transitioned: boolean;
  created_at: string;
}

export interface SpecialistOutput {
  role: SpecialistRole;
  provider: string;
  prompt_title: string;
  system_prompt: string;
  message: string;
  checklist: string[];
  evidence_notes: string[];
  suggested_next_role?: SpecialistRole | null;
}

export interface ProofGateStatus {
  state: ProofGateState;
  ready_to_complete: boolean;
  min_turns_required: number;
  turns_observed: number;
  evidence_refs_required: number;
  evidence_refs_observed: number;
  verifier_turn_required: boolean;
  verifier_turn_observed: boolean;
  minimum_average_confidence: number;
  observed_average_confidence: number;
  blockers: string[];
  cleared_checks: string[];
  last_evaluated_at: string;
}

export interface Run {
  run_id: string;
  goal_id: string;
  run_mode: RunMode;
  active_roles: SpecialistRole[];
  activation_strategy: string;
  activation_recommendations: SkillRecommendation[];
  current_role_activation_reason: string;
  current_role: SpecialistRole;
  current_index: number;
  round_number: number;
  turn_number: number;
  round_passes: SpecialistRole[];
  paused_roles: SpecialistRole[];
  status: RunStatus;
  turn_history: TurnRecord[];
  proof_gate_status: ProofGateStatus;
}

export interface RunReport {
  run_id: string;
  goal_id: string;
  status: RunStatus;
  turns: number;
  rounds: number;
  activated_roles: SpecialistRole[];
  role_turn_counts: Record<SpecialistRole, number>;
  role_pass_counts: Record<SpecialistRole, number>;
  role_avg_usefulness: Record<SpecialistRole, number>;
  paused_roles: SpecialistRole[];
  fallback_layer: string;
  proof_gate_status: ProofGateStatus;
}

export interface DecisionLedgerEntry {
  event_id: string;
  run_id: string;
  turn_number: number;
  round_number: number;
  event_type: DecisionEventType;
  role?: SpecialistRole | null;
  activated_role?: SpecialistRole | null;
  reason: string;
  confidence_before?: number | null;
  confidence_after?: number | null;
  confidence_delta?: number | null;
  fallback_from?: string | null;
  fallback_to?: string | null;
  created_at: string;
}

export interface RuntimeStatus {
  status: string;
  service: string;
  api_version: string;
  contract_version: string;
  recommended_roles_supported: boolean;
  decision_ledger_supported: boolean;
  store_backend: string;
  server_started_at: string;
  server_now: string;
  uptime_seconds: number;
  total_runs: number;
  active_runs: number;
}

export interface SkillRecommendation {
  role: SpecialistRole;
  activation_score: number;
  expected_utility: number;
  cost_penalty: number;
  latency_penalty: number;
  risk_reduction: number;
  rationale: string;
}
