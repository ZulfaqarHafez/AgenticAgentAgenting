import {
  DecisionLedgerEntry,
  Goal,
  Run,
  RunReport,
  SpecialistRole,
} from "@/types/hive";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${response.status}: ${text}`);
  }
  return response.json() as Promise<T>;
}

export function getApiBase(): string {
  return API_BASE;
}

export function listGoals(): Promise<Goal[]> {
  return request<Goal[]>("/goals", { method: "GET", cache: "no-store" });
}

export function createGoal(input: {
  title: string;
  success_criteria: string[];
  constraints: string[];
  priority: "low" | "medium" | "high" | "critical";
}): Promise<Goal> {
  return request<Goal>("/goals", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function startRun(goalId: string, roles: SpecialistRole[]): Promise<Run> {
  return request<Run>(`/goals/${goalId}/runs`, {
    method: "POST",
    body: JSON.stringify({
      active_roles: roles,
      min_usefulness: 0.35,
      max_low_value_streak: 2,
      enable_priority_preemption: true,
    }),
  });
}

export function applyTurn(
  runId: string,
  input: {
    role: SpecialistRole;
    contribution?: string;
    confidence: number;
    evidence_refs?: string[];
    usefulness_score: number;
    pass_turn: boolean;
    priority_override?: boolean;
    requested_next_role?: SpecialistRole | null;
  }
): Promise<Run> {
  return request<Run>(`/runs/${runId}/turns`, {
    method: "POST",
    body: JSON.stringify({
      contribution: "",
      evidence_refs: [],
      priority_override: false,
      requested_next_role: null,
      ...input,
    }),
  });
}

export function getRunReport(runId: string): Promise<RunReport> {
  return request<RunReport>(`/runs/${runId}/report`, {
    method: "GET",
    cache: "no-store",
  });
}

export function getDecisionLedger(runId: string): Promise<DecisionLedgerEntry[]> {
  return request<DecisionLedgerEntry[]>(`/runs/${runId}/ledger`, {
    method: "GET",
    cache: "no-store",
  });
}
