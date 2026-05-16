export type GoalPriority = "low" | "medium" | "high" | "critical";
export type GoalStatus = "active" | "completed" | "blocked";
export type RunStatus = "active" | "completed" | "halted";
export type SpecialistRole =
  | "research"
  | "planner"
  | "executor"
  | "critic"
  | "verifier";

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
  outcome: string;
  confidence: number;
  usefulness_score: number;
  evidence_refs: string[];
  contribution: string;
  requested_next_role?: SpecialistRole | null;
  next_role: SpecialistRole;
  reason: string;
  created_at: string;
}

export interface Run {
  run_id: string;
  goal_id: string;
  active_roles: SpecialistRole[];
  current_role: SpecialistRole;
  current_index: number;
  round_number: number;
  turn_number: number;
  round_passes: SpecialistRole[];
  paused_roles: SpecialistRole[];
  status: RunStatus;
  turn_history: TurnRecord[];
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
}
