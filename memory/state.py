from typing import TypedDict, Annotated, List, Optional, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class WorkingMemory(TypedDict):
    """Structured facts extracted and persisted across turns in a session."""
    customer_id: Optional[str]
    active_order_id: Optional[str]
    active_policy_id: Optional[str]
    last_intent: Optional[str]
    pending_approval: Optional[Dict[str, Any]]  # Holds high-value refund awaiting human sign-off
    is_human_approved: bool


class AgentState(TypedDict):
    """Master LangGraph state combining session message history + structured working memory."""
    messages: Annotated[List[BaseMessage], add_messages]
    session_id: str
    trace_id: str
    working_memory: WorkingMemory
    next_agent: Optional[str]
    security_blocked: bool
    security_reason: Optional[str]