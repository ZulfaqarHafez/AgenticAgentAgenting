import {
  DecisionLedgerEntry,
  Goal,
  ProofGateStatus,
  RunMode,
  RuntimeStatus,
  Run,
  RunReport,
  SpecialistRole,
} from "@/types/hive";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  bodyText: string;
  bodyJson: unknown;

  constructor(status: number, bodyText: string, bodyJson: unknown) {
    super(`API ${status}: ${bodyText}`);
    this.status = status;
    this.bodyText = bodyText;
    this.bodyJson = bodyJson;
  }
}

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
    let bodyJson: unknown = null;
    try {
      bodyJson = JSON.parse(text);
    } catch {
      bodyJson = null;
    }
    throw new ApiError(response.status, text, bodyJson);
  }
  return response.json() as Promise<T>;
}

export function getApiBase(): string {
  return API_BASE;
}

export function listGoals(): Promise<Goal[]> {
  return request<Goal[]>("/goals", { method: "GET", cache: "no-store" });
}

export function listRuns(goalId?: string): Promise<Run[]> {
  if (goalId) {
    return request<Run[]>(`/goals/${goalId}/runs`, {
      method: "GET",
      cache: "no-store",
    });
  }
  return request<Run[]>("/runs", { method: "GET", cache: "no-store" });
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

export interface StartRunResult {
  run: Run;
  compatibilityFallbackUsed: boolean;
}

function isMissingActiveRolesError(error: unknown): boolean {
  if (!(error instanceof ApiError) || error.status !== 422) {
    return false;
  }

  const detail = (error.bodyJson as { detail?: Array<{ loc?: unknown[]; msg?: string }> } | null)
    ?.detail;

  return (
    Array.isArray(detail) &&
    detail.some(
      (issue) =>
        Array.isArray(issue.loc) &&
        issue.loc.includes("active_roles") &&
        typeof issue.msg === "string" &&
        issue.msg.toLowerCase().includes("required")
    )
  );
}

export function startRun(
  goalId: string,
  options?: {
    roles?: SpecialistRole[];
    includeRoles?: SpecialistRole[];
    autoRoleLimit?: number;
    runMode?: RunMode;
  }
): Promise<StartRunResult> {
  const payload = {
    run_mode: options?.runMode ?? "balanced",
    active_roles: options?.roles,
    include_roles: options?.includeRoles,
    auto_role_limit: options?.autoRoleLimit ?? 3,
    min_usefulness: 0.35,
    max_low_value_streak: 2,
    enable_priority_preemption: true,
  };

  return request<Run>(`/goals/${goalId}/runs`, {
    method: "POST",
    body: JSON.stringify(payload),
  })
    .then((run) => ({
      run,
      compatibilityFallbackUsed: false,
    }))
    .catch(async (error) => {
      if (options?.roles || !isMissingActiveRolesError(error)) {
        throw error;
      }

      const fallbackRun = await request<Run>(`/goals/${goalId}/runs`, {
        method: "POST",
        body: JSON.stringify({
          ...payload,
          active_roles: options?.includeRoles ?? ["planner", "research", "verifier"],
        }),
      });

      return {
        run: fallbackRun,
        compatibilityFallbackUsed: true,
      };
    });
}

export function applyTurn(
  runId: string,
  input: {
    role: SpecialistRole;
    user_prompt?: string;
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

export function runAutoTurn(
  runId: string,
  input: {
    user_prompt: string;
    priority_override?: boolean;
  }
): Promise<Run> {
  return request<Run>(`/runs/${runId}/auto-turn`, {
    method: "POST",
    body: JSON.stringify({
      priority_override: false,
      ...input,
    }),
  });
}

export function getRun(runId: string): Promise<Run> {
  return request<Run>(`/runs/${runId}`, {
    method: "GET",
    cache: "no-store",
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

export function getProofGate(runId: string): Promise<ProofGateStatus> {
  return request<ProofGateStatus>(`/runs/${runId}/proof-gate`, {
    method: "GET",
    cache: "no-store",
  });
}

export function completeRun(runId: string): Promise<Run> {
  return request<Run>(`/runs/${runId}/complete`, {
    method: "POST",
  });
}

export function getRuntimeStatus(): Promise<RuntimeStatus> {
  return request<RuntimeStatus>("/runtime/status", {
    method: "GET",
    cache: "no-store",
  });
}
