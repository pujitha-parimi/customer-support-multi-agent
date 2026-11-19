import re
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from agents.llm_factory import get_llm
from memory.state import AgentState
from memory.store import save_working_memory


class RouteDecision(BaseModel):
    destination: Literal["tracking_agent", "refund_agent", "insurance_agent", "general_agent"] = Field(
        ...,
        description="The specialist agent best suited to handle the user's latest request.",
    )
    reasoning: str = Field(..., description="Brief explanation for why this specialist was chosen.")


ROUTER_SYSTEM_PROMPT = """You are the Customer Support Orchestrator (Router).
Your ONLY job is to analyze the customer's message and conversation context, then route the request to the right specialist:

1. 'tracking_agent': Questions about order status, shipping carrier, tracking numbers, or delivery estimates.
2. 'refund_agent': Requests to return an item, cancel for a refund, or check refund eligibility.
3. 'insurance_agent': Questions about shipping insurance coverage, damaged packages, lost items, or filing an insurance claim.
4. 'general_agent': Greetings, general policy questions, or unclear requests where no specialist is needed yet.

Use the active working memory context if the user refers to 'it' or 'my order' from an earlier turn."""


def _clean_dialogue_history(messages: list) -> list:
    """Keep only clean Human/AI text turns (strip internal tool-call messages that break Gemini turn order)."""
    cleaned = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            cleaned.append(msg)
        elif isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            text = msg.content
            if isinstance(text, list):
                text = " ".join(b.get("text", "") for b in text if isinstance(b, dict))
            if text:
                cleaned.append(AIMessage(content=str(text)))
    return cleaned[-4:]


def route_request(state: AgentState) -> dict:
    """Extract entity IDs into working memory and classify which specialist agent should handle the turn."""
    messages = state["messages"]
    latest_text = messages[-1].content if messages else ""
    working_mem = dict(state["working_memory"])

    # Deterministic entity extraction into structured working memory
    order_match = re.search(r"\bORD-\d{4}\b", latest_text.upper())
    if order_match:
        working_mem["active_order_id"] = order_match.group(0)

    policy_match = re.search(r"\bINS-\d{3}\b", latest_text.upper())
    if policy_match:
        working_mem["active_policy_id"] = policy_match.group(0)

    llm = get_llm(temperature=0.0).with_structured_output(RouteDecision)
    context_note = (
        f"Current Working Memory: active_order_id={working_mem.get('active_order_id')}, "
        f"active_policy_id={working_mem.get('active_policy_id')}, "
        f"last_intent={working_mem.get('last_intent')}"
    )

    dialogue = _clean_dialogue_history(messages)
    decision: RouteDecision = llm.invoke(
        [SystemMessage(content=f"{ROUTER_SYSTEM_PROMPT}\n\n{context_note}")] + dialogue
    )

    working_mem["last_intent"] = decision.destination
    save_working_memory(state["session_id"], working_mem)

    return {
        "next_agent": decision.destination,
        "working_memory": working_mem,
    }