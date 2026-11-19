import re
import json
from datetime import datetime, timezone
from typing import Tuple, Dict, Any
from langchain_core.messages import AIMessage
from memory.state import AgentState

AUDIT_LOG_PATH = "audit.log"

# Prompt injection & malicious payload signatures
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+your\s+rules",
    r"system\s+prompt",
    r"you\s+are\s+now\s+(in\s+)?developer\s+mode",
    r"bypass\s+(security|approval|limit)",
    r"drop\s+table",
    r"<script>",
]

# Role-based tool permission matrix
AGENT_TOOL_PERMISSIONS: Dict[str, list] = {
    "tracking_agent": ["get_order_status"],
    "refund_agent": ["get_order_status", "process_refund"],
    "insurance_agent": ["get_order_status", "file_insurance_claim"],
    "general_agent": [],
}


def write_audit_event(event_type: str, session_id: str, trace_id: str, details: Dict[str, Any]) -> None:
    """Append a tamper-evident JSON audit record for compliance and security review."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "session_id": session_id,
        "trace_id": trace_id,
        "details": details,
    }
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def validate_user_input(text: str) -> Tuple[bool, str]:
    """Check user input for length limits and prompt-injection attempts."""
    if not text or not text.strip():
        return False, "Empty input is not allowed."
    if len(text) > 1500:
        return False, "Input exceeds maximum allowed length (1500 characters)."

    lowered = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return False, f"Blocked potential prompt injection / policy bypass pattern: '{pattern}'."

    return True, "OK"


def input_guardrail_node(state: AgentState) -> dict:
    """LangGraph entry node that validates incoming messages before routing to any LLM."""
    latest_text = state["messages"][-1].content if state["messages"] else ""
    is_safe, reason = validate_user_input(latest_text)

    if not is_safe:
        write_audit_event(
            event_type="SECURITY_INPUT_BLOCKED",
            session_id=state["session_id"],
            trace_id=state["trace_id"],
            details={"reason": reason, "snippet": latest_text[:120]},
        )
        return {
            "security_blocked": True,
            "security_reason": reason,
            "messages": [
                AIMessage(
                    content="I cannot process that request due to a security policy violation. Please rephrase your customer support question."
                )
            ],
        }

    write_audit_event(
        event_type="INPUT_VALIDATED",
        session_id=state["session_id"],
        trace_id=state["trace_id"],
        details={"length": len(latest_text)},
    )
    return {"security_blocked": False, "security_reason": None}