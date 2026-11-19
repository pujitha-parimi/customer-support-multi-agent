from langgraph.graph import StateGraph, END
from memory.state import AgentState
from memory.store import get_session_checkpointer
from security.guardrails import input_guardrail_node
from agents.router import route_request
from agents.specialists import (
    tracking_agent_node,
    refund_agent_node,
    insurance_agent_node,
    general_agent_node,
)


def _after_guardrail(state: AgentState) -> str:
    """Stop immediately if input failed security validation; otherwise proceed to router."""
    if state.get("security_blocked"):
        return END
    return "router"


def _after_router(state: AgentState) -> str:
    """Route to the selected specialist agent."""
    return state.get("next_agent") or "general_agent"


def build_support_graph():
    """Compile the multi-agent customer support StateGraph with memory checkpointer."""
    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("input_guardrail", input_guardrail_node)
    workflow.add_node("router", route_request)
    workflow.add_node("tracking_agent", tracking_agent_node)
    workflow.add_node("refund_agent", refund_agent_node)
    workflow.add_node("insurance_agent", insurance_agent_node)
    workflow.add_node("general_agent", general_agent_node)

    # Define edges
    workflow.set_entry_point("input_guardrail")
    workflow.add_conditional_edges(
        "input_guardrail",
        _after_guardrail,
        {END: END, "router": "router"},
    )
    workflow.add_conditional_edges(
        "router",
        _after_router,
        {
            "tracking_agent": "tracking_agent",
            "refund_agent": "refund_agent",
            "insurance_agent": "insurance_agent",
            "general_agent": "general_agent",
        },
    )

    # All specialists conclude the turn after responding
    workflow.add_edge("tracking_agent", END)
    workflow.add_edge("refund_agent", END)
    workflow.add_edge("insurance_agent", END)
    workflow.add_edge("general_agent", END)

    checkpointer = get_session_checkpointer()
    return workflow.compile(checkpointer=checkpointer)