"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  applyTurn,
  createGoal,
  getDecisionLedger,
  getApiBase,
  getRunReport,
  listGoals,
  startRun,
} from "@/lib/api";
import {
  DecisionLedgerEntry,
  Goal,
  Run,
  RunReport,
  SpecialistRole,
} from "@/types/hive";

type ChatSpeaker = "user" | "system" | "agent";

interface ChatMessage {
  id: string;
  speaker: ChatSpeaker;
  label: string;
  text: string;
  timestamp: string;
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
  planner: "#f59e0b",
  research: "#0ea5e9",
  verifier: "#10b981",
  executor: "#ef4444",
  critic: "#6366f1",
};

function ts() {
  return new Date().toLocaleTimeString();
}

function starterMessage(): ChatMessage {
  return {
    id: "start",
    speaker: "system",
    label: "Hive Circle",
    text: "Define a goal in the composer. The system will create a goal, start a run, and route turns by specialty.",
    timestamp: ts(),
  };
}

export function HiveShell() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([starterMessage()]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [selectedGoalId, setSelectedGoalId] = useState<string | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [report, setReport] = useState<RunReport | null>(null);
  const [ledger, setLedger] = useState<DecisionLedgerEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedGoal = useMemo(
    () => goals.find((goal) => goal.goal_id === selectedGoalId) ?? null,
    [goals, selectedGoalId]
  );

  const ringStyle = useMemo(() => {
    if (!run || run.active_roles.length === 0) {
      return "conic-gradient(#d4d4d8 0 360deg)";
    }
    const slice = 360 / run.active_roles.length;
    const segments: string[] = [];
    run.active_roles.forEach((role, index) => {
      const from = Math.round(index * slice);
      const to = Math.round((index + 1) * slice);
      segments.push(`${RING_COLORS[role]} ${from}deg ${to}deg`);
    });
    return `conic-gradient(${segments.join(", ")})`;
  }, [run]);

  const refreshGoals = useCallback(async () => {
    try {
      const goalList = await listGoals();
      setGoals(goalList);
      if (!selectedGoalId && goalList.length > 0) {
        setSelectedGoalId(goalList[goalList.length - 1].goal_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load goals");
    }
  }, [selectedGoalId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshGoals();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [refreshGoals]);

  async function ensureGoalAndRun(userInput: string) {
    let resolvedGoal = selectedGoal;
    if (!resolvedGoal) {
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
    }

    if (!resolvedGoal) {
      throw new Error("Unable to resolve a goal for the run.");
    }

    if (!run || run.goal_id !== resolvedGoal.goal_id) {
      const newRun = await startRun(resolvedGoal.goal_id, ROLE_ROTATION);
      setRun(newRun);
      const [newReport, newLedger] = await Promise.all([
        getRunReport(newRun.run_id),
        getDecisionLedger(newRun.run_id),
      ]);
      setReport(newReport);
      setLedger(newLedger);
      return { goal: resolvedGoal, activeRun: newRun };
    }

    return { goal: resolvedGoal, activeRun: run };
  }

  async function submitTurnFromPrompt(prompt: string) {
    const { activeRun } = await ensureGoalAndRun(prompt);
    const actingRole = activeRun.current_role;
    const updatedRun = await applyTurn(activeRun.run_id, {
      role: actingRole,
      contribution: prompt,
      confidence: 0.82,
      usefulness_score: 0.76,
      pass_turn: false,
      evidence_refs: [],
    });
    setRun(updatedRun);

    const [updatedReport, updatedLedger] = await Promise.all([
      getRunReport(updatedRun.run_id),
      getDecisionLedger(updatedRun.run_id),
    ]);
    setReport(updatedReport);
    setLedger(updatedLedger);

    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        speaker: "agent",
        label: ROLE_LABELS[actingRole],
        text: `Turn accepted. Next role is ${ROLE_LABELS[updatedRun.current_role]}. Round ${updatedRun.round_number}, turn ${updatedRun.turn_number}.`,
        timestamp: ts(),
      },
    ]);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || busy) return;

    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        speaker: "user",
        label: "You",
        text: trimmed,
        timestamp: ts(),
      },
    ]);
    setDraft("");
    setBusy(true);
    setError(null);

    try {
      await submitTurnFromPrompt(trimmed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit turn");
    } finally {
      setBusy(false);
    }
  }

  async function handlePassTurn() {
    if (!run || busy) return;
    setBusy(true);
    setError(null);
    try {
      const updatedRun = await applyTurn(run.run_id, {
        role: run.current_role,
        confidence: 0.2,
        usefulness_score: 0.0,
        pass_turn: true,
      });
      setRun(updatedRun);
      const [updatedReport, updatedLedger] = await Promise.all([
        getRunReport(updatedRun.run_id),
        getDecisionLedger(updatedRun.run_id),
      ]);
      setReport(updatedReport);
      setLedger(updatedLedger);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          speaker: "agent",
          label: ROLE_LABELS[updatedRun.turn_history[updatedRun.turn_history.length - 1].role],
          text: "Passed this turn due to low confidence. Baton moved forward.",
          timestamp: ts(),
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to pass turn");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="hive-page">
      <div className="hive-gradient" />
      <header className="hive-header">
        <div>
          <p className="kicker">Agentic Agent</p>
          <h1>Hive Circle Console</h1>
        </div>
        <div className="api-pill">
          <span>API</span>
          <code>{getApiBase()}</code>
        </div>
      </header>

      <div className="hive-grid">
        <section className="chat-panel">
          <div className="chat-log">
            {messages.map((message) => (
              <article key={message.id} className={`bubble bubble-${message.speaker}`}>
                <div className="bubble-meta">
                  <strong>{message.label}</strong>
                  <span>{message.timestamp}</span>
                </div>
                <p>{message.text}</p>
              </article>
            ))}
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Describe the goal or next instruction..."
              rows={3}
            />
            <div className="composer-row">
              <button type="submit" disabled={busy}>
                {busy ? "Routing..." : "Send to Hive"}
              </button>
              <button type="button" disabled={busy || !run} onClick={handlePassTurn}>
                Pass Turn
              </button>
            </div>
          </form>
          {error ? <p className="error-text">{error}</p> : null}
        </section>

        <aside className="artifact-panel">
          <article className="artifact-card">
            <h2>Goal Card</h2>
            {selectedGoal ? (
              <>
                <p className="goal-title">{selectedGoal.title}</p>
                <p className="muted">
                  Priority: <strong>{selectedGoal.priority}</strong>
                </p>
                <ul>
                  {selectedGoal.success_criteria.map((criterion) => (
                    <li key={criterion}>{criterion}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="muted">No goal yet. Send the first prompt to create one.</p>
            )}
          </article>

          <article className="artifact-card">
            <h2>Ring Radar</h2>
            <div className="ring-wrap">
              <div className="ring" style={{ backgroundImage: ringStyle }}>
                <div className="ring-core">
                  <span>Next</span>
                  <strong>{run ? ROLE_LABELS[run.current_role] : "None"}</strong>
                </div>
              </div>
            </div>
            <ul className="role-list">
              {(run?.active_roles ?? ROLE_ROTATION).map((role) => (
                <li key={role}>
                  <span className="swatch" style={{ backgroundColor: RING_COLORS[role] }} />
                  <span>{ROLE_LABELS[role]}</span>
                  {run?.paused_roles.includes(role) ? <em>Paused</em> : null}
                  {run?.current_role === role ? <strong>Current</strong> : null}
                </li>
              ))}
            </ul>
          </article>

          <article className="artifact-card">
            <h2>Decision Ledger</h2>
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
              <p className="muted">
                Decision events appear after turns are processed.
              </p>
            )}
          </article>

          <article className="artifact-card">
            <h2>Run Report</h2>
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
