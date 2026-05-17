"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";

import {
  applyTurn,
  completeRun,
  createGoal,
  getApiBase,
  getDecisionLedger,
  getProofGate,
  getRun,
  getRunReport,
  getRuntimeStatus,
  listGoals,
  listRuns,
  runAutoTurn,
  startRun,
} from "@/lib/api";
import {
  DecisionLedgerEntry,
  Goal,
  ProofGateStatus,
  Run,
  RunMode,
  RunReport,
  RuntimeStatus,
  SpecialistOutput,
  SpecialistRole,
} from "@/types/hive";

type ChatSpeaker = "user" | "system" | "agent";
type ActivityPhase =
  | "idle"
  | "creating_goal"
  | "starting_run"
  | "routing_turn"
  | "refreshing_panels"
  | "compatibility_fallback"
  | "loading_history"
  | "completing_run"
  | "ready"
  | "error";
type PartRuntimeState = "idle" | "running" | "ready" | "blocked" | "offline";

interface ChatMessage {
  id: string;
  speaker: ChatSpeaker;
  label: string;
  text: string;
  timestamp: string;
  role?: SpecialistRole;
  turnNumber?: number;
  confidence?: number;
  evidenceRefs?: string[];
  nextRole?: SpecialistRole | null;
  outcome?: string;
  specialistOutput?: SpecialistOutput | null;
}

interface ActivityState {
  phase: ActivityPhase;
  title: string;
  detail: string;
  updatedAt: string;
}

interface RuntimePartRow {
  id: string;
  label: string;
  state: PartRuntimeState;
  detail: string;
  stamp: string;
}

const ROLE_ROTATION: SpecialistRole[] = ["planner", "research", "verifier"];
const ROLE_LABELS: Record<SpecialistRole, string> = {
  planner: "Planner",
  research: "Research",
  verifier: "Verifier",
  executor: "Executor",
  critic: "Critic",
};
const RING_COLORS: Record<SpecialistRole, string> = {
  planner: "#d97706",
  research: "#0284c7",
  verifier: "#0f766e",
  executor: "#dc2626",
  critic: "#4f46e5",
};
const ROLE_ARTWORK: Record<SpecialistRole, string> = {
  planner: "/agents/planner.svg",
  research: "/agents/research.svg",
  verifier: "/agents/verifier.svg",
  executor: "/agents/executor.svg",
  critic: "/agents/critic.svg",
};
const STARTER_PROMPTS = [
  {
    title: "Design the control loop",
    detail: "Map the adaptable circle-junction runtime and fallback logic.",
    prompt:
      "Design an adaptable multi-agent traffic circle that activates specialists only when needed and reports why each one was selected.",
  },
  {
    title: "Stress-test reliability",
    detail: "Push the verifier and fallback paths under pressure.",
    prompt:
      "Stress-test the hive design for failure modes and propose fallback rules that keep output reliable when confidence drops.",
  },
  {
    title: "Plan product direction",
    detail: "Turn the system into a stronger product with visible proof.",
    prompt:
      "Turn this agentic system into a premium product with runtime transparency, decision proof, and stronger operator control.",
  },
];

function speakerArtwork(message: ChatMessage): string {
  if (message.speaker === "user") return "/agents/user.svg";
  if (message.speaker === "system") return "/agents/hive.svg";
  if (message.role) return ROLE_ARTWORK[message.role];
  return "/agents/hive.svg";
}

function timestamp() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatIsoTimestamp(value: string) {
  return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function starterMessage(): ChatMessage {
  return {
    id: "start",
    speaker: "system",
    label: "Hive Circle",
    text: "Set a mission and the circle will create a goal, choose specialists, then show the reasoning behind each handoff.",
    timestamp: "ready",
  };
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatUptime(seconds: number | undefined) {
  if (typeof seconds !== "number") return "n/a";
  if (seconds < 90) return `${Math.floor(seconds)}s`;
  if (seconds < 5400) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h`;
}

function formatRunModeLabel(mode: RunMode) {
  return mode.charAt(0).toUpperCase() + mode.slice(1);
}

function shortRunLabel(runId: string) {
  return runId.slice(-6).toUpperCase();
}

function buildMessagesFromRun(run: Run | null): ChatMessage[] {
  if (!run || run.turn_history.length === 0) {
    return [starterMessage()];
  }

  const messages: ChatMessage[] = [];
  run.turn_history.forEach((turn) => {
    if (turn.user_prompt.trim()) {
      messages.push({
        id: `${run.run_id}-u-${turn.turn_number}`,
        speaker: "user",
        label: "You",
        text: turn.user_prompt,
        timestamp: formatIsoTimestamp(turn.created_at),
      });
    }

    const agentText =
      turn.specialist_output?.message ??
      (turn.outcome === "passed"
        ? `${ROLE_LABELS[turn.role]} passed due to low confidence. Baton moved to ${ROLE_LABELS[turn.next_role]}.`
        : turn.contribution);

    messages.push({
      id: `${run.run_id}-a-${turn.turn_number}`,
      speaker: "agent",
      role: turn.role,
      label: ROLE_LABELS[turn.role],
      text: agentText,
      timestamp: formatIsoTimestamp(turn.created_at),
      turnNumber: turn.turn_number,
      confidence: turn.confidence,
      evidenceRefs: turn.evidence_refs,
      nextRole: turn.specialist_output?.suggested_next_role ?? turn.requested_next_role,
      outcome: turn.outcome,
      specialistOutput: turn.specialist_output,
    });
  });
  return messages;
}

export function HiveShell() {
  const [draft, setDraft] = useState("");
  const [pendingPrompt, setPendingPrompt] = useState("");
  const [goals, setGoals] = useState<Goal[]>([]);
  const [goalRuns, setGoalRuns] = useState<Run[]>([]);
  const [selectedGoalId, setSelectedGoalId] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<RunReport | null>(null);
  const [proofGate, setProofGate] = useState<ProofGateStatus | null>(null);
  const [ledger, setLedger] = useState<DecisionLedgerEntry[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [runtimeOnline, setRuntimeOnline] = useState(false);
  const [runtimeCheckedAt, setRuntimeCheckedAt] = useState("never");
  const [activationMode, setActivationMode] = useState<"auto" | "manual">("auto");
  const [runMode, setRunMode] = useState<RunMode>("balanced");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedGoalIdRef = useRef<string | null>(null);
  const selectedRunIdRef = useRef<string | null>(null);
  const freshMissionPinnedRef = useRef(false);
  const [activity, setActivity] = useState<ActivityState>({
    phase: "idle",
    title: "Ready",
    detail: "The hive is waiting for a mission.",
    updatedAt: "ready",
  });

  const selectedGoal = useMemo(
    () => goals.find((goal) => goal.goal_id === selectedGoalId) ?? null,
    [goals, selectedGoalId]
  );
  const visibleRoles = run?.active_roles ?? ROLE_ROTATION;
  const latestTurn = run?.turn_history[run.turn_history.length - 1] ?? null;
  const latestEvidenceCount = latestTurn?.evidence_refs.length ?? 0;
  const topRecommendations = run?.activation_recommendations?.slice(0, 3) ?? [];
  const runtimeContractHealthy =
    runtime?.contract_version === "run-start.v2" &&
    runtime?.recommended_roles_supported === true &&
    runtime?.decision_ledger_supported === true;
  const messages = useMemo(() => {
    const base = buildMessagesFromRun(run);
    if (!pendingPrompt.trim()) return base;
    const pendingMessage: ChatMessage = {
      id: "pending-user",
      speaker: "user",
      label: "You",
      text: pendingPrompt,
      timestamp: "sending...",
    };
    return [
      ...base,
      pendingMessage,
    ];
  }, [pendingPrompt, run]);

  const ringStyle = useMemo(() => {
    if (visibleRoles.length === 0) {
      return "conic-gradient(#d4d4d8 0 360deg)";
    }
    const slice = 360 / visibleRoles.length;
    const segments = visibleRoles.map((role, index) => {
      const from = Math.round(index * slice);
      const to = Math.round((index + 1) * slice);
      return `${RING_COLORS[role]} ${from}deg ${to}deg`;
    });
    return `conic-gradient(${segments.join(", ")})`;
  }, [visibleRoles]);

  const updateActivity = useCallback((phase: ActivityPhase, title: string, detail: string) => {
    setActivity({
      phase,
      title,
      detail,
      updatedAt: timestamp(),
    });
  }, []);

  const refreshRuntime = useCallback(async () => {
    try {
      const runtimeStatus = await getRuntimeStatus();
      setRuntime(runtimeStatus);
      setRuntimeOnline(true);
    } catch {
      setRuntimeOnline(false);
    } finally {
      setRuntimeCheckedAt(timestamp());
    }
  }, []);

  const syncRunView = useCallback(async (nextRun: Run) => {
    const [nextReport, nextLedger, nextProofGate] = await Promise.all([
      getRunReport(nextRun.run_id),
      getDecisionLedger(nextRun.run_id),
      getProofGate(nextRun.run_id),
    ]);
    setRun(nextRun);
    setSelectedRunId(nextRun.run_id);
    setReport(nextReport);
    setLedger(nextLedger);
    setProofGate(nextProofGate);
  }, []);

  const refreshRuns = useCallback(
    async (goalId: string | null, preferredRunId?: string | null) => {
      if (!goalId) {
        setGoalRuns([]);
        setRun(null);
        setSelectedRunId(null);
        setReport(null);
        setProofGate(null);
        setLedger([]);
        return;
      }

      const runList = await listRuns(goalId);
      if (selectedGoalIdRef.current !== goalId) {
        return;
      }
      setGoalRuns(runList);

      if (runList.length === 0) {
        setRun(null);
        setSelectedRunId(null);
        setReport(null);
        setProofGate(null);
        setLedger([]);
        return;
      }

      const chosenRun =
        runList.find((candidate) => candidate.run_id === preferredRunId) ??
        runList.find((candidate) => candidate.run_id === selectedRunIdRef.current) ??
        runList.find((candidate) => candidate.status === "active") ??
        runList[0];

      if (!chosenRun) return;
      const hydratedRun = await getRun(chosenRun.run_id);
      if (selectedGoalIdRef.current !== goalId) {
        return;
      }
      await syncRunView(hydratedRun);
    },
    [syncRunView]
  );

  const refreshGoals = useCallback(async () => {
    const goalList = await listGoals();
    setGoals(goalList);
    if (!selectedGoalIdRef.current && !freshMissionPinnedRef.current && goalList.length > 0) {
      setSelectedGoalId(goalList[0].goal_id);
    }
  }, []);

  useEffect(() => {
    selectedGoalIdRef.current = selectedGoalId;
  }, [selectedGoalId]);

  useEffect(() => {
    selectedRunIdRef.current = selectedRunId;
  }, [selectedRunId]);

  useEffect(() => {
    const bootstrap = window.setTimeout(() => {
      void refreshGoals().catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Failed to load goals";
        setError(message);
        updateActivity("error", "Goal load failed", "Unable to load saved missions.");
      });
      void refreshRuntime();
    }, 0);

    const intervalId = window.setInterval(() => {
      void refreshRuntime();
    }, 5000);

    return () => {
      window.clearTimeout(bootstrap);
      window.clearInterval(intervalId);
    };
  }, [refreshGoals, refreshRuntime, updateActivity]);

  useEffect(() => {
    if (!selectedGoalId) return;
    const timer = window.setTimeout(() => {
      void refreshRuns(selectedGoalId).catch((err: unknown) => {
        const message = err instanceof Error ? err.message : "Failed to load run history";
        setError(message);
        updateActivity("error", "History load failed", message);
      });
    }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshRuns, selectedGoalId, updateActivity]);

  async function ensureGoalAndRun(userInput: string) {
    let resolvedGoal = selectedGoal;

    if (!resolvedGoal) {
      freshMissionPinnedRef.current = false;
      updateActivity(
        "creating_goal",
        "Creating mission",
        "Turning your prompt into a tracked goal and success criteria."
      );

      resolvedGoal = await createGoal({
        title: userInput.slice(0, 90),
        success_criteria: [
          "Deliver a useful multi-agent response",
          "Keep fallback and confidence signals visible",
        ],
        constraints: ["Budget-aware orchestration"],
        priority: "high",
      });

      setGoals((prev) => [resolvedGoal!, ...prev]);
      setSelectedGoalId(resolvedGoal.goal_id);
    }

    if (!resolvedGoal) {
      throw new Error("Unable to resolve a goal for the run.");
    }

    if (!run || run.goal_id !== resolvedGoal.goal_id || run.status !== "active") {
      updateActivity(
        "starting_run",
        "Starting circle",
        `Selecting specialists in ${activationMode === "auto" ? "auto skill" : "manual circle"} mode with the ${runMode} depth profile.`
      );

      const startResult =
        activationMode === "manual"
          ? await startRun(resolvedGoal.goal_id, {
              roles: ROLE_ROTATION,
              runMode,
            })
          : await startRun(resolvedGoal.goal_id, {
              includeRoles: ROLE_ROTATION,
              autoRoleLimit: 3,
              runMode,
            });

      if (startResult.compatibilityFallbackUsed) {
        updateActivity(
          "compatibility_fallback",
          "Legacy backend detected",
          "Auto skill mode fell back to a safe manual rotation instead of failing."
        );
      }

      setGoalRuns((prev) => [
        startResult.run,
        ...prev.filter((candidate) => candidate.run_id !== startResult.run.run_id),
      ]);
      await syncRunView(startResult.run);
      return {
        goal: resolvedGoal,
        activeRun: startResult.run,
      };
    }

    return { goal: resolvedGoal, activeRun: run };
  }

  async function sendPrompt(prompt: string) {
    const trimmed = prompt.trim();
    if (!trimmed || busy) return;

    setBusy(true);
    setError(null);
    setPendingPrompt(trimmed);
    setDraft("");

    try {
      const { activeRun } = await ensureGoalAndRun(trimmed);
      updateActivity(
        "routing_turn",
        `Running ${ROLE_LABELS[activeRun.current_role]}`,
        activeRun.current_role_activation_reason
      );

      const updatedRun = await runAutoTurn(activeRun.run_id, {
        user_prompt: trimmed,
      });

      updateActivity(
        "refreshing_panels",
        "Refreshing mission state",
        "Updating radar, proof gate, ledger, and history."
      );
      await syncRunView(updatedRun);
      setGoalRuns((prev) =>
        prev.map((candidate) => (candidate.run_id === updatedRun.run_id ? updatedRun : candidate))
      );
      await refreshRuntime();
      updateActivity(
        "ready",
        "Turn complete",
        `${ROLE_LABELS[updatedRun.current_role]} now holds the baton for the next move.`
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit turn";
      setError(message);
      updateActivity("error", "Request failed", message);
    } finally {
      setPendingPrompt("");
      setBusy(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await sendPrompt(draft);
  }

  async function handlePassTurn() {
    if (!run || busy) return;

    setBusy(true);
    setError(null);
    updateActivity(
      "routing_turn",
      `Passing ${ROLE_LABELS[run.current_role]}`,
      "Low-confidence turn detected, advancing the baton."
    );

    try {
      const updatedRun = await applyTurn(run.run_id, {
        role: run.current_role,
        user_prompt: "",
        confidence: 0.2,
        usefulness_score: 0.0,
        pass_turn: true,
      });
      await syncRunView(updatedRun);
      setGoalRuns((prev) =>
        prev.map((candidate) => (candidate.run_id === updatedRun.run_id ? updatedRun : candidate))
      );
      await refreshRuntime();
      updateActivity(
        "ready",
        "Turn passed",
        `${ROLE_LABELS[updatedRun.current_role]} picked up the baton.`
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to pass turn";
      setError(message);
      updateActivity("error", "Pass turn failed", message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCompleteRun() {
    if (!run || busy) return;

    setBusy(true);
    setError(null);
    updateActivity(
      "completing_run",
      "Attempting completion",
      "Checking the proof gate before marking this run complete."
    );

    try {
      const completedRun = await completeRun(run.run_id);
      await syncRunView(completedRun);
      setGoalRuns((prev) =>
        prev.map((candidate) => (candidate.run_id === completedRun.run_id ? completedRun : candidate))
      );
      await refreshRuntime();
      updateActivity(
        "ready",
        "Run completed",
        "Proof gate cleared and the run has been marked complete."
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to complete run";
      setError(message);
      updateActivity("error", "Completion blocked", message);
    } finally {
      setBusy(false);
    }
  }

  async function handleGoalChange(goalId: string | null) {
    freshMissionPinnedRef.current = goalId === null;
    setSelectedGoalId(goalId);
    setSelectedRunId(null);
    setGoalRuns([]);
    setRun(null);
    setReport(null);
    setProofGate(null);
    setLedger([]);
  }

  function handleNewMission() {
    freshMissionPinnedRef.current = true;
    setSelectedGoalId(null);
    setSelectedRunId(null);
    setGoalRuns([]);
    setRun(null);
    setReport(null);
    setProofGate(null);
    setLedger([]);
    setPendingPrompt("");
    setDraft("");
    setError(null);
    updateActivity(
      "ready",
      "Fresh mission",
      "The console is cleared and ready to start a brand new circle."
    );
  }

  async function handleRunSelect(runId: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    updateActivity(
      "loading_history",
      "Loading replay",
      "Hydrating this run from persistent history."
    );

    try {
      const nextRun = await getRun(runId);
      await syncRunView(nextRun);
      updateActivity(
        "ready",
        "Replay loaded",
        `Loaded run ${shortRunLabel(runId)} for inspection.`
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load run replay";
      setError(message);
      updateActivity("error", "Replay load failed", message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRefreshPanels() {
    if (busy) return;

    setBusy(true);
    setError(null);
    updateActivity(
      "refreshing_panels",
      "Refreshing cockpit",
      "Rechecking runtime, replay, proof gate, and the active run state."
    );

    try {
      await refreshRuntime();
      await refreshGoals();
      if (selectedGoalId) {
        await refreshRuns(selectedGoalId, selectedRunId);
      }
      updateActivity("ready", "Console refreshed", "Runtime and mission state are up to date.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to refresh the console";
      setError(message);
      updateActivity("error", "Refresh failed", message);
    } finally {
      setBusy(false);
    }
  }

  const runtimeParts = useMemo<RuntimePartRow[]>(() => {
    const proofState: PartRuntimeState =
      !run || !proofGate ? "idle" : proofGate.ready_to_complete ? "ready" : "blocked";

    return [
      {
        id: "goal-engine",
        label: "Goal Engine",
        state: activity.phase === "creating_goal" ? "running" : selectedGoal ? "ready" : "idle",
        detail: selectedGoal ? `Tracking ${selectedGoal.title}` : "No active mission selected yet.",
        stamp: activity.updatedAt,
      },
      {
        id: "skill-router",
        label: "Skill Router",
        state: activity.phase === "starting_run" ? "running" : run ? "ready" : "idle",
        detail: run
          ? `${run.activation_strategy} using ${visibleRoles.length} active specialists.`
          : "Waiting for the first run to start.",
        stamp: activity.updatedAt,
      },
      {
        id: "specialist-engine",
        label: "Specialist Engine",
        state:
          activity.phase === "routing_turn"
            ? "running"
            : latestTurn?.specialist_output
              ? "ready"
              : "idle",
        detail: latestTurn?.specialist_output
          ? `${ROLE_LABELS[latestTurn.role]} produced a structured role output.`
          : "No specialist output has been generated yet.",
        stamp: latestTurn ? formatIsoTimestamp(latestTurn.created_at) : activity.updatedAt,
      },
      {
        id: "proof-gate",
        label: "Proof Gate",
        state: proofState,
        detail: proofGate
          ? proofGate.ready_to_complete
            ? "Completion is unlocked."
            : proofGate.blockers[0] ?? "Completion is still blocked."
          : "Proof gate has not been evaluated yet.",
        stamp: proofGate ? formatIsoTimestamp(proofGate.last_evaluated_at) : activity.updatedAt,
      },
      {
        id: "history-sync",
        label: "History Sync",
        state:
          activity.phase === "loading_history" || activity.phase === "refreshing_panels"
            ? "running"
            : goalRuns.length > 0
              ? "ready"
              : "idle",
        detail:
          goalRuns.length > 0
            ? `${goalRuns.length} persisted run${goalRuns.length === 1 ? "" : "s"} available for replay.`
            : "No run history has been loaded yet.",
        stamp: selectedRunId ? activity.updatedAt : runtimeCheckedAt,
      },
    ];
  }, [
    activity.phase,
    activity.updatedAt,
    goalRuns.length,
    latestTurn,
    proofGate,
    run,
    runtimeCheckedAt,
    selectedGoal,
    selectedRunId,
    visibleRoles.length,
  ]);

  const runtimePartsById = useMemo(
    () => Object.fromEntries(runtimeParts.map((part) => [part.id, part])),
    [runtimeParts]
  );

  const cockpitSignals = useMemo(
    () => [
      {
        id: "baton",
        label: "Baton",
        value: run ? ROLE_LABELS[run.current_role] : "Waiting",
        detail: run?.current_role_activation_reason ?? "No active handoff yet.",
        state: (busy ? "running" : run ? "ready" : "idle") as PartRuntimeState,
      },
      {
        id: "router",
        label: "Router",
        value:
          run?.activation_strategy === "recommended_roles"
            ? "Adaptive"
            : run?.activation_strategy === "manual_active_roles"
              ? "Manual"
              : "Standby",
        detail: run
          ? `${run.activation_strategy} across ${visibleRoles.length} specialists.`
          : "No live run yet.",
        state: (
          activity.phase === "starting_run"
            ? "running"
            : run
              ? "ready"
              : "idle"
        ) as PartRuntimeState,
      },
      {
        id: "proof",
        label: "Proof",
        value: proofGate?.state ?? "blocked",
        detail: proofGate?.ready_to_complete
          ? "Completion can be marked safely."
          : proofGate?.blockers[0] ?? "Proof gate waiting for evidence.",
        state: (!proofGate ? "idle" : proofGate.ready_to_complete ? "ready" : "blocked") as PartRuntimeState,
      },
      {
        id: "history",
        label: "Replay",
        value: selectedRunId ? shortRunLabel(selectedRunId) : "Empty",
        detail:
          goalRuns.length > 0
            ? `${goalRuns.length} saved run${goalRuns.length === 1 ? "" : "s"} ready to inspect.`
            : "No replayable runs loaded yet.",
        state: (
          activity.phase === "loading_history"
            ? "running"
            : goalRuns.length > 0
              ? "ready"
              : "idle"
        ) as PartRuntimeState,
      },
    ],
    [activity.phase, busy, goalRuns.length, proofGate, run, selectedRunId, visibleRoles.length]
  );

  function renderSectionRuntime(partId: RuntimePartRow["id"]) {
    const part = runtimePartsById[partId];
    if (!part) return null;
    return (
      <span className={`section-runtime section-runtime-${part.state}`}>
        <span className="section-runtime-dot" />
        {part.label} {part.state}
      </span>
    );
  }

  return (
    <div className="hive-page">
      <div className="hive-gradient" />

      <header className="hive-header">
        <div className="header-copy">
          <div className="header-orbit">
            <Image src="/art/orbit-map.svg" alt="" width={320} height={188} priority />
          </div>
          <p className="kicker">Agentic Agent</p>
          <h1>Hive Circle Console</h1>
          <p className="header-subtitle">
            A mission-control shell for adaptive specialists, visible fallback lanes,
            proof-gated completion, and persistent replay.
          </p>
        </div>

        <div className="header-badges">
          <div
            className={`status-pill ${
              runtimeOnline ? "status-pill-live" : "status-pill-offline"
            }`}
          >
            <span className="status-dot" />
            <strong>{runtimeOnline ? "Backend live" : "Backend offline"}</strong>
            <small>Checked {runtimeCheckedAt}</small>
          </div>
          <div
            className={`status-pill ${busy ? "status-pill-working" : "status-pill-neutral"}`}
          >
            <span className="status-dot" />
            <strong>{activity.title}</strong>
            <small>{activity.updatedAt}</small>
          </div>
          <div className="api-pill">
            <span>API</span>
            <code>{getApiBase()}</code>
          </div>
        </div>
      </header>

      <div className="hive-grid">
        <section className="chat-panel">
          <div className="mission-board">
            <div className="mission-copy">
              <p className="mission-eyebrow">Mission Control</p>
              <div className="mission-title-row">
                <h2>{selectedGoal?.title ?? "No mission active yet"}</h2>
                <div className="mission-controls">
                  <button
                    type="button"
                    className="mission-action mission-action-quiet"
                    onClick={handleNewMission}
                    disabled={busy}
                  >
                    New Mission
                  </button>
                  <select
                    className="goal-select"
                    value={selectedGoalId ?? ""}
                    onChange={(event) => {
                      void handleGoalChange(event.target.value || null);
                    }}
                    disabled={busy}
                  >
                    <option value="">Latest mission</option>
                    {goals.map((goal) => (
                      <option key={goal.goal_id} value={goal.goal_id}>
                        {goal.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <p className="mission-summary">
                {selectedGoal
                  ? selectedGoal.success_criteria[0]
                  : "Start with a concrete goal and the circle will turn it into a live run."}
              </p>

              <div className="signal-strip">
                {cockpitSignals.map((signal) => (
                  <article key={signal.id} className="signal-card">
                    <div className="signal-card-header">
                      <span>{signal.label}</span>
                      <span className={`state-chip state-chip-${signal.state}`}>
                        {signal.state}
                      </span>
                    </div>
                    <strong>{signal.value}</strong>
                    <p>{signal.detail}</p>
                  </article>
                ))}
              </div>

              <div className="mission-facts">
                <span className="fact-pill">
                  Mode{" "}
                  <strong>{activationMode === "auto" ? "Auto Skills" : "Manual Circle"}</strong>
                </span>
                <span className="fact-pill">
                  Depth <strong>{formatRunModeLabel(run?.run_mode ?? runMode)}</strong>
                </span>
                <span className="fact-pill">
                  Status <strong>{run?.status ?? "idle"}</strong>
                </span>
                <span className="fact-pill">
                  Run <strong>{selectedRunId ? shortRunLabel(selectedRunId) : "none"}</strong>
                </span>
                <span className="fact-pill">
                  Turns <strong>{run?.turn_number ?? 0}</strong>
                </span>
                <span className="fact-pill">
                  Evidence <strong>{latestEvidenceCount}</strong>
                </span>
              </div>
            </div>

            <div className="mission-side">
              <div className="mission-presence">
                <Image
                  src={run ? ROLE_ARTWORK[run.current_role] : "/agents/hive.svg"}
                  alt=""
                  width={52}
                  height={52}
                />
                <div>
                  <p className="mission-presence-label">
                    {busy ? "Currently working" : "Current baton holder"}
                  </p>
                  <strong>{run ? ROLE_LABELS[run.current_role] : "Hive Circle"}</strong>
                  <span>{activity.detail}</span>
                </div>
              </div>

              <div className="cast-row">
                {visibleRoles.map((role) => (
                  <div
                    key={role}
                    className={`cast-pill ${run?.current_role === role ? "cast-pill-active" : ""}`}
                  >
                    <Image src={ROLE_ARTWORK[role]} alt="" width={22} height={22} />
                    <span>{ROLE_LABELS[role]}</span>
                  </div>
                ))}
              </div>

              <div className="mission-illustration">
                <Image src="/art/mission-weave.svg" alt="" width={280} height={164} />
              </div>
            </div>
          </div>

          <div className="chat-log">
            {!selectedGoal && messages.length <= 1 ? (
              <div className="starter-grid">
                {STARTER_PROMPTS.map((starter) => (
                  <button
                    key={starter.title}
                    type="button"
                    className="starter-card"
                    onClick={() => {
                      setDraft(starter.prompt);
                    }}
                    disabled={busy}
                  >
                    <span className="starter-kicker">{starter.title}</span>
                    <strong>{starter.detail}</strong>
                    <span>{starter.prompt}</span>
                  </button>
                ))}
              </div>
            ) : null}

            {messages.map((message) => (
              <article key={message.id} className={`bubble bubble-${message.speaker}`}>
                <div className="bubble-meta">
                  <span className="bubble-agent-id">
                    <Image src={speakerArtwork(message)} alt="" width={24} height={24} />
                    <strong>{message.label}</strong>
                  </span>
                  <span>{message.timestamp}</span>
                </div>
                {message.speaker === "agent" ? (
                  <div className="bubble-runtime">
                    <span className="mini-badge mini-badge-neutral">
                      Turn {message.turnNumber ?? "-"}
                    </span>
                    <span className="mini-badge mini-badge-good">
                      {formatPercent(message.confidence ?? 0)}
                    </span>
                    <span className="mini-badge mini-badge-neutral">
                      {(message.evidenceRefs?.length ?? 0)} evidence
                    </span>
                    {message.nextRole ? (
                      <span className="mini-badge mini-badge-warn">
                        Next {ROLE_LABELS[message.nextRole]}
                      </span>
                    ) : null}
                  </div>
                ) : null}
                <p>{message.text}</p>
                {message.speaker === "agent" && message.specialistOutput ? (
                  <div className="bubble-artifact">
                    <div className="bubble-artifact-header">
                      <div>
                        <strong>{message.specialistOutput.prompt_title}</strong>
                        <span>{message.specialistOutput.provider}</span>
                      </div>
                      <span className="mini-badge mini-badge-neutral">
                        {message.outcome?.replaceAll("_", " ") ?? "contributed"}
                      </span>
                    </div>
                    <div className="bubble-artifact-grid">
                      <div>
                        <h3>Checklist</h3>
                        <ul>
                          {message.specialistOutput.checklist.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h3>Evidence notes</h3>
                        <ul>
                          {message.specialistOutput.evidence_notes.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                ) : null}
              </article>
            ))}
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <div className="composer-header">
              <div>
                <p className="composer-kicker">Compose</p>
                <strong>Send the next mission update into the circle</strong>
                <span className="composer-subcopy">
                  Start a fresh circle, steer the mode, or pressure-test the live baton holder.
                </span>
              </div>
              <div className="mode-row">
                <button
                  type="button"
                  className={activationMode === "auto" ? "mode-active" : ""}
                  onClick={() => setActivationMode("auto")}
                  disabled={busy}
                >
                  Auto Skills
                </button>
                <button
                  type="button"
                  className={activationMode === "manual" ? "mode-active" : ""}
                  onClick={() => setActivationMode("manual")}
                  disabled={busy}
                >
                  Manual Circle
                </button>
              </div>
            </div>

            <div className="mode-row mode-row-secondary">
              <button
                type="button"
                className={runMode === "lite" ? "mode-active" : ""}
                onClick={() => setRunMode("lite")}
                disabled={busy}
              >
                Lite
              </button>
              <button
                type="button"
                className={runMode === "balanced" ? "mode-active" : ""}
                onClick={() => setRunMode("balanced")}
                disabled={busy}
              >
                Balanced
              </button>
              <button
                type="button"
                className={runMode === "power" ? "mode-active" : ""}
                onClick={() => setRunMode("power")}
                disabled={busy}
              >
                Power
              </button>
            </div>

            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Describe the goal, ask for the next turn, or pressure-test the fallback behavior..."
              rows={4}
            />

            <div className="composer-status">
              <span
                className={`activity-pulse ${
                  busy
                    ? "activity-pulse-working"
                    : runtimeOnline
                      ? "activity-pulse-ready"
                      : "activity-pulse-offline"
                }`}
              />
              <div>
                <strong>{activity.title}</strong>
                <span>{activity.detail}</span>
              </div>
            </div>

            <div className="composer-row">
              <button type="submit" disabled={busy || draft.trim().length === 0}>
                {busy ? "Processing..." : "Send to Hive"}
              </button>
              <button type="button" disabled={busy} onClick={() => void handleRefreshPanels()}>
                Refresh View
              </button>
              <button type="button" disabled={busy || !run} onClick={handlePassTurn}>
                Pass Turn
              </button>
              <button
                type="button"
                disabled={busy || !run || !proofGate?.ready_to_complete}
                onClick={handleCompleteRun}
              >
                Complete Run
              </button>
            </div>
          </form>

          {error ? (
            <div className="error-banner">
              <strong>Request blocked</strong>
              <span>{error}</span>
            </div>
          ) : null}
        </section>

        <aside className="artifact-panel">
          <article className="artifact-card">
            <div className="artifact-card-header">
              <div className="card-title-block">
                <Image className="card-mark" src="/art/runtime-signal.svg" alt="" width={34} height={34} />
                <div>
                  <h2>Component Runtime</h2>
                  <p className="artifact-caption">
                    Live state for each subsystem so you can see what is actively running.
                  </p>
                </div>
              </div>
            </div>

            <div className="runtime-part-list">
              {runtimeParts.map((part) => (
                <div key={part.id} className="runtime-part">
                  <div className="runtime-part-header">
                    <strong>{part.label}</strong>
                    <span className={`state-chip state-chip-${part.state}`}>{part.state}</span>
                  </div>
                  <p>{part.detail}</p>
                  <small>{part.stamp}</small>
                </div>
              ))}
            </div>
          </article>

          <article className="artifact-card">
            <div className="artifact-card-header">
              <div className="card-title-block">
                <Image className="card-mark" src="/art/runtime-signal.svg" alt="" width={34} height={34} />
                <div>
                  <h2>Runtime</h2>
                  <p className="artifact-caption">
                    Live health, contract support, and execution state.
                  </p>
                </div>
              </div>
              <span
                className={`mini-badge ${
                  runtimeContractHealthy ? "mini-badge-good" : "mini-badge-warn"
                }`}
              >
                {runtimeContractHealthy ? "Current contract" : "Legacy contract"}
              </span>
            </div>

            <div className="runtime-grid">
              <p>
                <span>Backend</span>
                <strong className={runtimeOnline ? "runtime-live" : "runtime-down"}>
                  {runtimeOnline ? "Online" : "Offline"}
                </strong>
              </p>
              <p>
                <span>Checked</span>
                <strong>{runtimeCheckedAt}</strong>
              </p>
              <p>
                <span>API</span>
                <strong>{runtime?.api_version ?? "n/a"}</strong>
              </p>
              <p>
                <span>Contract</span>
                <strong>{runtime?.contract_version ?? "legacy"}</strong>
              </p>
              <p>
                <span>Store</span>
                <strong>{runtime?.store_backend ?? "n/a"}</strong>
              </p>
              <p>
                <span>Uptime</span>
                <strong>{formatUptime(runtime?.uptime_seconds)}</strong>
              </p>
              <p>
                <span>Total Runs</span>
                <strong>{runtime?.total_runs ?? 0}</strong>
              </p>
              <p>
                <span>Active Runs</span>
                <strong>{runtime?.active_runs ?? 0}</strong>
              </p>
            </div>
          </article>

          <article className="artifact-card">
            <div className="artifact-card-header">
              <div>
                <h2>Goal Card</h2>
                <p className="artifact-caption">
                  The active mission, strategy, and completion posture.
                </p>
              </div>
              <div className="card-runtime-stack">
                {renderSectionRuntime("goal-engine")}
                {selectedGoal ? (
                  <span className="mini-badge mini-badge-neutral">{selectedGoal.priority}</span>
                ) : null}
              </div>
            </div>

            {selectedGoal ? (
              <>
                <p className="goal-title">{selectedGoal.title}</p>
                <p className="muted">
                  Strategy: <strong>{run?.activation_strategy ?? "not started"}</strong>
                </p>
                <p className="muted">
                  Run mode: <strong>{formatRunModeLabel(run?.run_mode ?? runMode)}</strong>
                </p>
                <p className="muted">
                  Proof gate: <strong>{proofGate?.state ?? "blocked"}</strong>
                </p>
                <ul>
                  {selectedGoal.success_criteria.map((criterion) => (
                    <li key={criterion}>{criterion}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="muted">No mission yet. Choose a starter prompt or write your own.</p>
            )}
          </article>

          <article className="artifact-card">
            <div className="artifact-card-header">
              <div>
                <h2>Ring Radar</h2>
                <p className="artifact-caption">
                  Circle rotation, baton holder, and role recommendations.
                </p>
              </div>
              {renderSectionRuntime("skill-router")}
            </div>

            <div className="ring-wrap">
              <div className="ring-backdrop">
                <Image src="/art/baton-arc.svg" alt="" width={220} height={220} />
              </div>
              <div className={`ring ${busy ? "ring-live" : ""}`} style={{ backgroundImage: ringStyle }}>
                <div className="ring-core">
                  <Image
                    src={run ? ROLE_ARTWORK[run.current_role] : "/agents/hive.svg"}
                    alt=""
                    width={36}
                    height={36}
                  />
                  <span>Next</span>
                  <strong>{run ? ROLE_LABELS[run.current_role] : "None"}</strong>
                </div>
              </div>
            </div>

            {run?.current_role_activation_reason ? (
              <p className="muted">
                Why now: <strong>{run.current_role_activation_reason}</strong>
              </p>
            ) : null}

            <ul className="role-list">
              {visibleRoles.map((role) => (
                <li key={role}>
                  <Image
                    className="role-avatar"
                    src={ROLE_ARTWORK[role]}
                    alt=""
                    width={24}
                    height={24}
                  />
                  <span className="swatch" style={{ backgroundColor: RING_COLORS[role] }} />
                  <span>{ROLE_LABELS[role]}</span>
                  {run?.paused_roles.includes(role) ? <em>Paused</em> : null}
                  {run?.current_role === role ? <strong>Current</strong> : null}
                </li>
              ))}
            </ul>

            {topRecommendations.length > 0 ? (
              <div className="recommendation-list">
                {topRecommendations.map((recommendation) => (
                  <div key={recommendation.role} className="recommendation-item">
                    <span>{ROLE_LABELS[recommendation.role]}</span>
                    <strong>{recommendation.activation_score.toFixed(2)}</strong>
                  </div>
                ))}
              </div>
            ) : null}
          </article>

          <article className="artifact-card">
            <div className="artifact-card-header">
              <div className="card-title-block">
                <Image className="card-mark" src="/art/proof-seal.svg" alt="" width={34} height={34} />
                <div>
                  <h2>Proof Gate</h2>
                  <p className="artifact-caption">
                    Completion only unlocks after enough turns, evidence, confidence, and verifier review.
                  </p>
                </div>
              </div>
              <div className="card-runtime-stack">
                {renderSectionRuntime("proof-gate")}
                <span
                  className={`mini-badge ${
                    proofGate?.ready_to_complete ? "mini-badge-good" : "mini-badge-warn"
                  }`}
                >
                  {proofGate?.state ?? "blocked"}
                </span>
              </div>
            </div>

            {proofGate ? (
              <>
                <div className="proof-grid">
                  <p>
                    <span>Turns</span>
                    <strong>
                      {proofGate.turns_observed}/{proofGate.min_turns_required}
                    </strong>
                  </p>
                  <p>
                    <span>Evidence</span>
                    <strong>
                      {proofGate.evidence_refs_observed}/{proofGate.evidence_refs_required}
                    </strong>
                  </p>
                  <p>
                    <span>Verifier</span>
                    <strong>{proofGate.verifier_turn_observed ? "Done" : "Waiting"}</strong>
                  </p>
                  <p>
                    <span>Avg Confidence</span>
                    <strong>
                      {proofGate.observed_average_confidence.toFixed(2)}/
                      {proofGate.minimum_average_confidence.toFixed(2)}
                    </strong>
                  </p>
                </div>

                <div className="proof-section">
                  <strong>Cleared checks</strong>
                  <ul className="proof-list proof-list-good">
                    {proofGate.cleared_checks.length > 0 ? (
                      proofGate.cleared_checks.map((item) => <li key={item}>{item}</li>)
                    ) : (
                      <li>No checks cleared yet.</li>
                    )}
                  </ul>
                </div>

                <div className="proof-section">
                  <strong>Blockers</strong>
                  <ul className="proof-list">
                    {proofGate.blockers.length > 0 ? (
                      proofGate.blockers.map((item) => <li key={item}>{item}</li>)
                    ) : (
                      <li>None. Completion is unlocked.</li>
                    )}
                  </ul>
                </div>
              </>
            ) : (
              <p className="muted">Proof gate status appears after a run is active.</p>
            )}
          </article>

          <article className="artifact-card">
            <div className="artifact-card-header">
              <div>
                <h2>Decision Ledger</h2>
                <p className="artifact-caption">
                  The most recent activation, confidence, and fallback events.
                </p>
              </div>
              <div className="card-runtime-stack">
                {renderSectionRuntime("specialist-engine")}
                <span className="mini-badge mini-badge-neutral">{ledger.length} events</span>
              </div>
            </div>

            {ledger.length > 0 ? (
              <div className="ledger-list">
                {ledger
                  .slice(-8)
                  .reverse()
                  .map((entry) => (
                    <div key={entry.event_id} className="ledger-item">
                      <p className="ledger-meta">
                        <span>T{entry.turn_number}</span>
                        <strong>{entry.event_type.replaceAll("_", " ")}</strong>
                      </p>
                      <p className="ledger-reason">{entry.reason}</p>
                      {typeof entry.confidence_delta === "number" ? (
                        <p className="ledger-supplement">
                          Confidence {entry.confidence_before?.toFixed(2)} -&gt;{" "}
                          {entry.confidence_after?.toFixed(2)} (
                          {entry.confidence_delta >= 0 ? "+" : ""}
                          {entry.confidence_delta.toFixed(2)})
                        </p>
                      ) : null}
                      {entry.fallback_from && entry.fallback_to ? (
                        <p className="ledger-supplement">
                          Fallback {entry.fallback_from} -&gt; {entry.fallback_to}
                        </p>
                      ) : null}
                    </div>
                  ))}
              </div>
            ) : (
              <p className="muted">Decision events appear after the first processed turn.</p>
            )}
          </article>

          <article className="artifact-card">
            <div className="artifact-card-header">
              <div className="card-title-block">
                <Image className="card-mark" src="/art/history-ribbon.svg" alt="" width={34} height={34} />
                <div>
                  <h2>Run History</h2>
                  <p className="artifact-caption">
                    Persisted runs for the selected goal, ready for replay.
                  </p>
                </div>
              </div>
              <div className="card-runtime-stack">
                {renderSectionRuntime("history-sync")}
                <span className="mini-badge mini-badge-neutral">{goalRuns.length} runs</span>
              </div>
            </div>

            {goalRuns.length > 0 ? (
              <div className="history-list">
                {goalRuns.map((candidate) => (
                  <button
                    key={candidate.run_id}
                    type="button"
                    className={`history-button ${
                      selectedRunId === candidate.run_id ? "history-button-active" : ""
                    }`}
                    onClick={() => {
                      void handleRunSelect(candidate.run_id);
                    }}
                    disabled={busy}
                  >
                    <div className="history-button-header">
                      <strong>{shortRunLabel(candidate.run_id)}</strong>
                      <span>{candidate.status}</span>
                    </div>
                    <p>
                      {formatRunModeLabel(candidate.run_mode)} mode, {candidate.turn_number} turns,{" "}
                      {candidate.active_roles.length} specialists
                    </p>
                  </button>
                ))}
              </div>
            ) : (
              <p className="muted">No persisted runs yet for this goal.</p>
            )}
          </article>

          <article className="artifact-card">
            <div className="artifact-card-header">
              <div className="card-title-block">
                <Image className="card-mark" src="/art/history-ribbon.svg" alt="" width={34} height={34} />
                <div>
                  <h2>Replay Timeline</h2>
                  <p className="artifact-caption">
                    Review prior prompts, specialist outputs, and baton handoffs.
                  </p>
                </div>
              </div>
              {renderSectionRuntime("history-sync")}
            </div>

            {run?.turn_history.length ? (
              <div className="replay-list">
                {run.turn_history.map((turn) => (
                  <div key={`${run.run_id}-${turn.turn_number}`} className="replay-item">
                    <div className="replay-item-header">
                      <strong>
                        T{turn.turn_number} - {ROLE_LABELS[turn.role]}
                      </strong>
                      <span>{formatIsoTimestamp(turn.created_at)}</span>
                    </div>
                    <p className="replay-user">{turn.user_prompt || "Manual pass / replay event"}</p>
                    <p className="replay-agent">
                      {turn.specialist_output?.prompt_title ?? "Specialist response"}
                    </p>
                    <p>{turn.contribution}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">Replay becomes available after the first turn.</p>
            )}
          </article>

          <article className="artifact-card">
            <div className="artifact-card-header">
              <div>
                <h2>Run Report</h2>
                <p className="artifact-caption">
                  A compact readout of turns, rounds, fallback, and next focus.
                </p>
              </div>
              {renderSectionRuntime("specialist-engine")}
            </div>

            {report ? (
              <div className="report-grid">
                <p>
                  <span>Status</span>
                  <strong>{report.status}</strong>
                </p>
                <p>
                  <span>Rounds</span>
                  <strong>{report.rounds}</strong>
                </p>
                <p>
                  <span>Turns</span>
                  <strong>{report.turns}</strong>
                </p>
                <p>
                  <span>Fallback</span>
                  <strong>{report.fallback_layer}</strong>
                </p>
                <p>
                  <span>Last confidence</span>
                  <strong>{latestTurn ? formatPercent(latestTurn.confidence) : "n/a"}</strong>
                </p>
                <p>
                  <span>Proof gate</span>
                  <strong>{report.proof_gate_status.state}</strong>
                </p>
                {run?.activation_recommendations?.[0] ? (
                  <p>
                    <span>Top Skill</span>
                    <strong>
                      {ROLE_LABELS[run.activation_recommendations[0].role]} (
                      {run.activation_recommendations[0].activation_score.toFixed(2)})
                    </strong>
                  </p>
                ) : null}
              </div>
            ) : (
              <p className="muted">Run report will appear after the first turn.</p>
            )}
          </article>
        </aside>
      </div>
    </div>
  );
}
