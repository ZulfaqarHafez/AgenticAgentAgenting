from typing import TypedDict

from langgraph.graph import END, StateGraph


class BootstrapState(TypedDict):
    message: str
    stage: str


def _mark_bootstrapped(state: BootstrapState) -> BootstrapState:
    return {"message": state["message"], "stage": "bootstrapped"}


def build_bootstrap_graph():
    graph = StateGraph(BootstrapState)
    graph.add_node("bootstrap", _mark_bootstrapped)
    graph.set_entry_point("bootstrap")
    graph.add_edge("bootstrap", END)
    return graph.compile()

