"""
src/graph.py
============
This module builds the LangGraph StateGraph that orchestrates the agents.

WHAT IS A STATEGRAPH?
  Think of it as a flowchart where each box is a Python function (a "node")
  and the arrows are rules that decide which box to run next.
  The graph passes a shared dictionary (AgentState) from node to node.

OUR FLOW:
  ┌─────────────┐
  │  architect  │  <-- entry point (Kimi plans the task)
  └──────┬──────┘
         │
         ▼
    ┌────────┐
    │ route  │  <-- conditional: "complexa" or "simple" ?
    └───┬────┘
        │
   ┌────┴────┐
   ▼         ▼
┌──────┐  ┌────────┐
│claude│  │opencode│  <-- one coder runs, depending on complexity
└──┬───┘  └───┬────┘
   │          │
   └────┬─────┘
        ▼
   ┌─────────┐
   │finalize │  <-- ALWAYS runs last (saves memory for next time)
   └────┬────┘
        ▼
       END
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from src.agents import (
    AgentState,
    architect_node,
    claude_coder_node,
    opencode_coder_node,
    finalize_node,
)


def route_task(state: AgentState) -> Literal["claude", "opencode"]:
    """
    ROUTER FUNCTION  --  The "traffic cop" of the graph.
    ================================================
    This function runs AFTER architect_node. It looks at the
    'complexity' field that the Architect wrote and decides which
    coder should handle the task.

    Returns:
        "claude"    -> if complexity contains the word "complexa"
        "opencode"  -> for everything else (assumes "simple")

    The returned string MUST match one of the keys in the
    add_conditional_edges() dictionary inside build_graph().
    """
    if "complexa" in state.get("complexity", ""):
        return "claude"
    return "opencode"


def build_graph():
    """
    FACTORY FUNCTION  --  Builds and compiles the StateGraph.
    ==========================================================
    Call this once at startup (see main.py). It returns a compiled
    graph object that you can invoke with an initial AgentState.
    """
    # Create a new graph that uses AgentState as its shared data schema.
    workflow = StateGraph(AgentState)

    # -------------------------------------------------------------------------
    # REGISTER NODES
    # -------------------------------------------------------------------------
    # Every node is just a Python function. The string name is how we
    # reference it when wiring up edges.
    # -------------------------------------------------------------------------
    workflow.add_node("architect", architect_node)
    workflow.add_node("claude", claude_coder_node)
    workflow.add_node("opencode", opencode_coder_node)
    workflow.add_node("finalize", finalize_node)

    # -------------------------------------------------------------------------
    # SET ENTRY POINT
    # -------------------------------------------------------------------------
    # Every graph invocation starts here.
    # -------------------------------------------------------------------------
    workflow.set_entry_point("architect")

    # -------------------------------------------------------------------------
    # CONDITIONAL EDGE: architect -> (claude OR opencode)
    # -------------------------------------------------------------------------
    # After the architect node finishes, LangGraph calls route_task() and
    # looks at the returned string. The dictionary below maps that string
    # to the name of the next node to run.
    # -------------------------------------------------------------------------
    workflow.add_conditional_edges(
        "architect",          # source node
        route_task,           # routing function
        {
            "claude": "claude",      # if route_task returns "claude", go here
            "opencode": "opencode"   # if route_task returns "opencode", go here
        }
    )

    # -------------------------------------------------------------------------
    # SEQUENTIAL EDGES: coders -> finalize -> END
    # -------------------------------------------------------------------------
    # Both coders MUST pass through finalize before the graph ends.
    # This guarantees that EVERY run produces a memory snapshot,
    # even if the coder crashes or returns garbage.
    # -------------------------------------------------------------------------
    workflow.add_edge("claude", "finalize")
    workflow.add_edge("opencode", "finalize")
    workflow.add_edge("finalize", END)

    # Compile the graph into an executable object.
    # This validates the topology (no dead ends, no orphan nodes, etc.)
    return workflow.compile()
