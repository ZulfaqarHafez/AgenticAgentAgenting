"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";

import {
  applyTurn,
  createGoal,
  getApiBase,
  getDecisionLedger,
  getRuntimeStatus,
  getRunReport,
  listGoals,
  startRun,
} from "@/lib/api";
import {
  DecisionLedgerEntry,
  Goal,
  RunMode,
  RuntimeStatus,
  Run,
  RunReport,
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
  | "ready"
  | "error";

interface ChatMessage {
  id: string;
  speaker: ChatSpeaker;
  label: string;
  text: string;
  timestamp: string;
  role?: SpecialistRole;
}

interface ActivityState {
  phase: ActivityPhase;
  title: string;
  detail: string;
  updatedAt: string;
}

const ROLE_ROTATION: SpecialistRole[] = ["planner", "research", "verifier"];

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

function speakerArtwork(message: ChatMessage): string {
  if (message.speaker === "user") return "/agents/user.svg";
  if (message.speaker === "system") return "/agents/hive.svg";
  if (message.role) return ROLE_ARTWORK[message.role];
  return "/agents/hive.svg";
}

function timestamp() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
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

function buildTurnSummary(run: Run, actingRole: SpecialistRole) {
  const latestTurn = run.turn_history[run.turn_history.length - 1];
  if (!latestTurn) {
    return `Turn recorded. ${ROLE_LABELS[run.current_role]} now holds the baton.`;
  }

  return [
    `${ROLE_LABELS[actingRole]} logged a turn at ${formatPercent(latestTurn.confidence)} confidence and ${formatPercent(latestTurn.usefulness_score)} usefulness.`,
    `Next up: ${ROLE_LABELS[run.current_role]}.`,
    latestTurn.next_role_activation_reason,
  ].join(" ");
}

function buildPassSummary(run: Run) {
  const latestTurn = run.turn_history[run.turn_history.length - 1];
  if (!latestTurn) {
    return `Turn passed. ${ROLE_LABELS[run.current_role]} now holds the baton.`;
  }

  return [
    `${ROLE_LABELS[latestTurn.role]} passed due to low confidence.`,
    `Fallback layer: ${latestTurn.fallback_layer_after}.`,
    `Next up: ${ROLE_LABELS[run.current_role]}.`,
    latestTurn.next_role_activation_reason,
  ].join(" ");
}

export function HiveShell() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([starterMessage()]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [selectedGoalId, setSelectedGoalId] = useState<string | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<RunReport | null>(null);
  const [ledger, setLedger] = useState<DecisionLedgerEntry[]>([]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  const [runtimeOnline, setRuntimeOnline] = useState(false);
  const [runtimeCheckedAt, setRuntimeCheckedAt] = useState("never");
  const [activationMode, setActivationMode] = useState<"auto" | "manual">("auto");
  const [runMode, setRunMode] = useState<RunMode>("balanced");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
  const topRecommendations = run?.activation_recommendations?.slice(0, 3) ?? [];
  const latestTurn = run?.turn_history[run.turn_history.length - 1] ?? null;
  const runtimeContractHealthy =
    runtime?.contract_version === "run-start.v2" &&
    runtime?.recommended_roles_supported === true &&
    runtime?.decision_ledger_supported === true;

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

  const appendMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const updateActivity = useCallback(
    (phase: ActivityPhase, title: string, detail: string) => {
      setActivity({
        phase,
        title,
        detail,
        updatedAt: timestamp(),
      });
    },
    []
  );

  const refreshGoals = useCallback(async () => {
    try {
      const goalList = await listGoals();
      setGoals(goalList);
      if (!selectedGoalId && goalList.length > 0) {
        setSelectedGoalId(goalList[goalList.length - 1].goal_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load goals");
      updateActivity("error", "Goal load failed", "Unable to load saved missions.");
    }
  }, [selectedGoalId, updateActivity]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshGoals();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshGoals]);

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

  useEffect(() => {
    const bootstrap = window.setTimeout(() => {
      void refreshRuntime();
    }, 0);
    const id = window.setInterval(() => {
      void refreshRuntime();
    }, 5000);
    return () => {
      window.clearTimeout(bootstrap);
      window.clearInterval(id);
    };
  }, [refreshRuntime]);

  async function ensureGoalAndRun(userInput: string) {
    let resolvedGoal = selectedGoal;

    if (!resolvedGoal) {
      updateActivity(
        "creating_goal",
        "Creating mission",
        "Turning your prompt into a goal card and success criteria."
      );
      const createdGoal = await createGoal({
        title: userInput.slice(0, 90),
        success_criteria: [
          "Deliver a useful multi-agent response",
          "Keep fallback and confidence signals visible",
        ],
        constraints: ["Budget-aware orchestration"],
        priority: "high",
      });

      setGoals((prev) => [...prev, createdGoal]);
      setSelectedGoalId(createdGoal.goal_id);
      resolvedGoal = createdGoal;
      appendMessage({
        id: crypto.randomUUID(),
        speaker: "system",
        label: "Mission Board",
        text: `Created goal "${createdGoal.title}" with a high-priority mission profile.`,
        timestamp: timestamp(),
      });
    }

    if (!resolvedGoal) {
      throw new Error("Unable to resolve a goal for the run.");
    }

    if (!run || run.goal_id !== resolvedGoal.goal_id) {
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

      const newRun = startResult.run;
      setRun(newRun);

      if (startResult.compatibilityFallbackUsed) {
        updateActivity(
          "compatibility_fallback",
          "Legacy backend detected",
          "Auto skill mode fell back to a safe manual rotation so the run could continue."
        );
        appendMessage({
          id: crypto.randomUUID(),
          speaker: "system",
          label: "Compatibility Guard",
          text: "The backend exposed an older run-start contract, so the client switched to a safe manual planner/research/verifier rotation instead of failing.",
          timestamp: timestamp(),
        });
      }

      updateActivity(
        "refreshing_panels",
        "Loading mission state",
        "Pulling the latest report, ledger, and radar context."
      );
      const [newReport, newLedger] = await Promise.all([
        getRunReport(newRun.run_id),
        getDecisionLedger(newRun.run_id),
      ]);
      setReport(newReport);
      setLedger(newLedger);

      return {
        goal: resolvedGoal,
        activeRun: newRun,
        compatibilityFallbackUsed: startResult.compatibilityFallbackUsed,
      };
    }

    return { goal: resolvedGoal, activeRun: run, compatibilityFallbackUsed: false };
  }

  async function submitTurnFromPrompt(prompt: string) {
    const { activeRun } = await ensureGoalAndRun(prompt);
    const actingRole = activeRun.current_role;

    updateActivity(
      "routing_turn",
      `Routing to ${ROLE_LABELS[actingRole]}`,
      activeRun.current_role_activation_reason
    );

    const updatedRun = await applyTurn(activeRun.run_id, {
      role: actingRole,
      contribution: prompt,
      confidence: 0.82,
      usefulness_score: 0.76,
      pass_turn: false,
      evidence_refs: [],
    });
    setRun(updatedRun);

    updateActivity(
      "refreshing_panels",
      "Refreshing circle state",
      "Updating radar, report, and decision ledger."
    );
    const [updatedReport, updatedLedger] = await Promise.all([
      getRunReport(updatedRun.run_id),
      getDecisionLedger(updatedRun.run_id),
    ]);
    setReport(updatedReport);
    setLedger(updatedLedger);

    appendMessage({
      id: crypto.randomUUID(),
      speaker: "agent",
      role: actingRole,
      label: ROLE_LABELS[actingRole],
      text: buildTurnSummary(updatedRun, actingRole),
      timestamp: timestamp(),
    });

    updateActivity(
      "ready",
      "Run updated",
      `${ROLE_LABELS[updatedRun.current_role]} now holds the baton for the next turn.`
    );
  }

  async function sendPrompt(prompt: string) {
    const trimmed = prompt.trim();
    if (!trimmed || busy) return;

    appendMessage({
      id: crypto.randomUUID(),
      speaker: "user",
      label: "You",
      text: trimmed,
      timestamp: timestamp(),
    });

    setBusy(true);
    setError(null);
    setDraft("");

    try {
      await submitTurnFromPrompt(trimmed);
      await refreshRuntime();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit turn";
      setError(message);
      updateActivity("error", "Request failed", message);
    } finally {
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
        confidence: 0.2,
        usefulness_score: 0.0,
        pass_turn: true,
      });

      setRun(updatedRun);
      updateActivity(
        "refreshing_panels",
        "Refreshing circle state",
        "Updating the run report and decision ledger after the pass."
      );

      const [updatedReport, updatedLedger] = await Promise.all([
        getRunReport(updatedRun.run_id),
        getDecisionLedger(updatedRun.run_id),
      ]);
      setReport(updatedReport);
      setLedger(updatedLedger);

      appendMessage({
        id: crypto.randomUUID(),
        speaker: "agent",
        role: updatedRun.turn_history[updatedRun.turn_history.length - 1].role,
        label: ROLE_LABELS[updatedRun.turn_history[updatedRun.turn_history.length - 1].role],
        text: buildPassSummary(updatedRun),
        timestamp: timestamp(),
      });

      updateActivity(
        "ready",
        "Turn passed",
        `${ROLE_LABELS[updatedRun.current_role]} picked up the baton.`
      );
      await refreshRuntime();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to pass turn";
      setError(message);
      updateActivity("error", "Pass turn failed", message);
    } finally {
      setBusy(false);
    }
  }

  function handleGoalChange(goalId: string | null) {
    setSelectedGoalId(goalId);
    if (run && goalId && run.goal_id !== goalId) {
      setRun(null);
      setReport(null);
      setLedger([]);
    }
  }

  return (
    <div className="hive-page">
      <div className="hive-gradient" />

      <header className="hive-header">
        <div className="header-copy">
          <p className="kicker">Agentic Agent</p>
          <h1>Hive Circle Console</h1>
          <p className="header-subtitle">
            A mission-control shell for adaptive specialists, visible fallback lanes,
            and goal-driven orchestration.
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
            className={`status-pill ${
              busy ? "status-pill-working" : "status-pill-neutral"
            }`}
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
                <select
                  className="goal-select"
                  value={selectedGoalId ?? ""}
                  onChange={(event) => handleGoalChange(event.target.value || null)}
                  disabled={busy || goals.length === 0}
                >
                  <option value="">Latest mission</option>
                  {goals.map((goal) => (
                    <option key={goal.goal_id} value={goal.goal_id}>
                      {goal.title}
                    </option>
                  ))}
                </select>
              </div>
              <p className="mission-summary">
                {selectedGoal
                  ? selectedGoal.success_criteria[0]
                  : "Start with a concrete goal and the circle will turn it into a live run."}
              </p>
              <div className="mission-facts">
                <span className="fact-pill">
                  Mode <strong>{activationMode === "auto" ? "Auto Skills" : "Manual Circle"}</strong>
                </span>
                <span className="fact-pill">
                  Depth <strong>{formatRunModeLabel(run?.run_mode ?? runMode)}</strong>
                </span>
                <span className="fact-pill">
                  Status <strong>{run?.status ?? "idle"}</strong>
                </span>
                <span className="fact-pill">
                  Round <strong>{run?.round_number ?? 0}</strong>
                </span>
                <span className="fact-pill">
                  Turn <strong>{run?.turn_number ?? 0}</strong>
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
                <p>{message.text}</p>
              </article>
            ))}
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <div className="composer-header">
              <div>
                <p className="composer-kicker">Compose</p>
                <strong>Send the next mission update into the circle</strong>
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
                  busy ? "activity-pulse-working" : runtimeOnline ? "activity-pulse-ready" : "activity-pulse-offline"
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
              <button type="button" disabled={busy || !run} onClick={handlePassTurn}>
                Pass Turn
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
              <div>
                <h2>Runtime</h2>
                <p className="artifact-caption">
                  Live health, contract support, and execution state.
                </p>
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
                  The active mission, success criteria, and chosen strategy.
                </p>
              </div>
              {selectedGoal ? (
                <span className="mini-badge mini-badge-neutral">{selectedGoal.priority}</span>
              ) : null}
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
            </div>

            <div className="ring-wrap">
              <div className="ring" style={{ backgroundImage: ringStyle }}>
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
              <div>
                <h2>Decision Ledger</h2>
                <p className="artifact-caption">
                  The most recent activation, confidence, and fallback events.
                </p>
              </div>
              <span className="mini-badge mini-badge-neutral">{ledger.length} events</span>
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
              <div>
                <h2>Run Report</h2>
                <p className="artifact-caption">
                  A compact readout of turns, rounds, fallback, and next focus.
                </p>
              </div>
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
