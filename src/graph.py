"""
src/graph.py
============
Builds the LangGraph StateGraph that orchestrates multi-agent execution.

FLOW (with task loop):
  ┌───────────┐
  │ optimizer │  <-- entry: fast model structures raw user input
  └─────┬─────┘
        │
        ▼
  ┌──────────┐
  │ planner  │  <-- powerful model creates full plan.md with [COMPLEX]/[SIMPLE]
  └─────┬────┘
        │
        ▼
  ┌──────────┐
  │ executor │◄──────────────────────────┐
  └─────┬────┘                           │
        │                                │
        ▼                                │
   ┌─────────┐                           │
   │  route  │──► complex ───────────────┤
   │  next   │──► simple  ───────────────┘
   │         │──► finalize → END
   └─────────┘

DEPENDENCY INJECTION:
  build_graph() receives an AgentFactory, creates nodes with clients injected.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from src.agents import (
    AgentState,
    make_optimizer_node,
    make_planner_node,
    make_scaffolder_node,
    make_executor_node,
    make_complex_coder_node,
    make_simple_coder_node,
    make_finalize_node,
)
from src.clients import AgentFactory


def route_next(state: AgentState) -> Literal["complex", "simple", "finalize"]:
    """
    ROUTER FUNCTION -- Decides where the executor should go next.

    Runs AFTER executor_node. Checks:
      - If all tasks are done (task_index >= total_tasks) → finalize
      - If next task is complex → complex coder
      - Otherwise → simple coder
    """
    task_index = state.get("task_index", 0)
    total_tasks = state.get("total_tasks", 0)

    if task_index >= total_tasks:
        return "finalize"

    if "complexa" in state.get("complexity", ""):
        return "complex"
    return "simple"


def build_graph(factory: AgentFactory | None = None):
    """
    Builds and compiles the StateGraph with task-loop support.

    Args:
        factory: AgentFactory providing configured AgentClient per role.
    """
    if factory is None:
        factory = AgentFactory()

    # Create node functions with clients injected (DIP)
    optimizer = make_optimizer_node(factory.create_optimizer())
    planner = make_planner_node(factory.create_architect())
    scaffolder = make_scaffolder_node()
    executor = make_executor_node()
    complex_coder = make_complex_coder_node(factory.create_complex_coder())
    simple_coder = make_simple_coder_node(factory.create_simple_coder())
    finalize = make_finalize_node(factory.create_finalizer())

    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("optimizer", optimizer)
    workflow.add_node("planner", planner)
    workflow.add_node("scaffolder", scaffolder)
    workflow.add_node("executor", executor)
    workflow.add_node("complex", complex_coder)
    workflow.add_node("simple", simple_coder)
    workflow.add_node("finalize", finalize)

    # Entry point
    workflow.set_entry_point("optimizer")

    # optimizer → planner → scaffolder → executor (dispatches first task)
    workflow.add_edge("optimizer", "planner")
    workflow.add_edge("planner", "scaffolder")
    workflow.add_edge("scaffolder", "executor")

    # executor → complex | simple | finalize (conditional loop)
    workflow.add_conditional_edges(
        "executor",
        route_next,
        {
            "complex": "complex",
            "simple": "simple",
            "finalize": "finalize",
        }
    )

    # Coders loop back to executor (for next task)
    workflow.add_edge("complex", "executor")
    workflow.add_edge("simple", "executor")

    # finalize → END
    workflow.add_edge("finalize", END)

    return workflow.compile()
