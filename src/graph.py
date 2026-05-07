from typing import Literal
from langgraph.graph import StateGraph, END
from src.agents import AgentState, architect_node, claude_coder_node, opencode_coder_node, finalize_node

def route_task(state: AgentState) -> Literal["claude", "opencode"]:
    if "complexa" in state.get("complexity", ""):
        return "claude"
    return "opencode"

def build_graph():
    workflow = StateGraph(AgentState)

    # Afegim nodes
    workflow.add_node("architect", architect_node)
    workflow.add_node("claude", claude_coder_node)
    workflow.add_node("opencode", opencode_coder_node)
    workflow.add_node("finalize", finalize_node)

    # Definim el flux
    workflow.set_entry_point("architect")

    # Aresta condicional
    workflow.add_conditional_edges(
        "architect",
        route_task,
        {
            "claude": "claude",
            "opencode": "opencode"
        }
    )

    # Finalitzacio: coders -> finalize -> END
    workflow.add_edge("claude", "finalize")
    workflow.add_edge("opencode", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()
