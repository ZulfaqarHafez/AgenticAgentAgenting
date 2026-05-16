from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.models import Run, TurnInput
from app.orchestration.scheduler import CircleJunctionScheduler


class TurnGraphState(TypedDict):
    run: Run
    turn: TurnInput


def build_turn_graph(scheduler: CircleJunctionScheduler):
    def _advance(state: TurnGraphState) -> TurnGraphState:
        run = scheduler.apply_turn(state["run"], state["turn"])
        return {"run": run, "turn": state["turn"]}

    graph = StateGraph(TurnGraphState)
    graph.add_node("advance", _advance)
    graph.set_entry_point("advance")
    graph.add_edge("advance", END)
    return graph.compile()

