import os
import time
import uuid
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from agents.graph import build_support_graph
from memory.store import load_working_memory, save_working_memory
from security.guardrails import write_audit_event
from ops.logger import configure_logging, get_logger

load_dotenv(override=True)
configure_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger("cli_runner")


def format_ai_content(content) -> str:
    """Normalize string or structured content blocks from Gemini into clean plain text."""
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
    return str(content).strip()


def run_cli():
    graph = build_support_graph()
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": session_id}}

    print("\n====================================================")
    print("  Production Multi-Agent Customer Support System")
    print(f"  Session ID: {session_id}")
    print("  Type 'exit' to quit | Type 'memory' to inspect state")
    print("====================================================\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        working_mem = load_working_memory(session_id)

        if user_input.lower() == "memory":
            print(f"\n[Working Memory]: {working_mem}\n")
            continue

        trace_id = f"tr-{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()

        state_input = {
            "messages": [HumanMessage(content=user_input)],
            "session_id": session_id,
            "trace_id": trace_id,
            "working_memory": working_mem,
            "next_agent": None,
            "security_blocked": False,
            "security_reason": None,
        }

        result = graph.invoke(state_input, config=config)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        ai_reply = format_ai_content(result["messages"][-1].content)
        updated_mem = result.get("working_memory", working_mem)

        logger.info(
            "request_completed",
            session_id=session_id,
            trace_id=trace_id,
            routed_agent=result.get("next_agent"),
            security_blocked=result.get("security_blocked"),
            latency_ms=latency_ms,
        )

        print(f"\nAgent ({result.get('next_agent') or 'guardrail'}): {ai_reply}\n")

        # Handle Human-in-the-Loop Supervisor Approval if triggered
        if updated_mem.get("pending_approval") and not updated_mem.get("is_human_approved"):
            choice = input("⚠️  [SUPERVISOR GATE] Approve high-value refund? (yes/no): ").strip().lower()
            if choice == "yes":
                updated_mem["is_human_approved"] = True
                save_working_memory(session_id, updated_mem)
                write_audit_event(
                    event_type="HUMAN_SUPERVISOR_APPROVED",
                    session_id=session_id,
                    trace_id=trace_id,
                    details=updated_mem["pending_approval"],
                )
                # Re-invoke turn with human approval granted
                resume_state = {
                    "messages": [HumanMessage(content="Supervisor approved. Please complete the refund now.")],
                    "session_id": session_id,
                    "trace_id": f"tr-{uuid.uuid4().hex[:8]}",
                    "working_memory": updated_mem,
                    "next_agent": None,
                    "security_blocked": False,
                    "security_reason": None,
                }
                resumed = graph.invoke(resume_state, config=config)
                resumed_mem = resumed.get("working_memory", updated_mem)
                resumed_mem["pending_approval"] = None
                resumed_mem["is_human_approved"] = False
                save_working_memory(session_id, resumed_mem)
                resumed_reply = format_ai_content(resumed["messages"][-1].content)
                print(f"\nAgent (refund_agent): {resumed_reply}\n")
            else:
                updated_mem["pending_approval"] = None
                save_working_memory(session_id, updated_mem)
                write_audit_event(
                    event_type="HUMAN_SUPERVISOR_REJECTED",
                    session_id=session_id,
                    trace_id=trace_id,
                    details={"reason": "Supervisor declined high-value payout"},
                )
                print("\nAgent: Refund request was declined by the supervisor.\n")


if __name__ == "__main__":
    run_cli()