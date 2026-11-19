from langchain_core.messages import SystemMessage, ToolMessage, AIMessage
from agents.llm_factory import get_llm
from memory.state import AgentState
from memory.store import save_working_memory
from tools.support_tools import (
    get_order_status,
    process_refund,
    file_insurance_claim,
    get_insurance_policy,
)
from tools.mock_db import MOCK_ORDERS

TRACKING_PROMPT = """You are the Order Tracking Specialist.
- Help customers check order status, shipping carrier, and tracking numbers.
- Always call `get_order_status` using the order ID (from the user's message or working memory).
- Never invent tracking numbers. If no order ID is known, politely ask for it (format: ORD-XXXX)."""

REFUND_PROMPT = """You are the Refund & Returns Specialist.
- Help customers check eligibility and process refunds.
- First call `get_order_status` to verify the order amount, delivery window (30 days), and refundable flag.
- Only call `process_refund` if the item is eligible and the user explicitly wants a refund.
- Never promise a refund if the tool returns an error or policy violation."""

INSURANCE_PROMPT = """You are the Shipping Insurance & Claims Specialist.
- Help customers check insurance policy details and file claims for damaged or lost items.
- Whenever a policy ID (format: INS-XXX) is provided, ALWAYS call `get_insurance_policy` first to verify that the policy exists and is active before asking for claim details or filing a claim.
- If the user provides an order ID instead of a policy ID, call `get_order_status` first to find `insurance_policy_id`.
- Call `file_insurance_claim` with the policy ID, incident description, and claim amount."""

GENERAL_PROMPT = """You are a polite Frontline Customer Support Assistant.
- Greet the customer and explain how you can help (Order Tracking, Refunds, or Shipping Insurance Claims).
- Ask for their Order ID (e.g., ORD-1001) or Policy ID (e.g., INS-501) if they need account-specific help."""


def _run_agent_with_tools(state: AgentState, system_prompt: str, tools: list) -> dict:
    """Helper loop that invokes a specialist LLM, executes allowed tools, and enforces refund approval thresholds."""
    working_mem = dict(state["working_memory"])
    context_banner = (
        f"\n[Working Memory Context: active_order_id={working_mem.get('active_order_id')}, "
        f"active_policy_id={working_mem.get('active_policy_id')}]"
    )
    llm = get_llm(temperature=0.0).bind_tools(tools) if tools else get_llm(temperature=0.0)
    tool_map = {t.name: t for t in tools}

    conversation = [SystemMessage(content=system_prompt + context_banner)] + list(state["messages"])
    new_messages = []

    # Allow up to 3 tool-calling hops per turn
    for _ in range(3):
        response = llm.invoke(conversation)
        conversation.append(response)
        new_messages.append(response)

        if not getattr(response, "tool_calls", None):
            break

        for tool_call in response.tool_calls:
            t_name = tool_call["name"]
            t_args = tool_call["args"]

            # Human-in-the-Loop Gate: Block irreversible refunds > $500 unless approved
            if t_name == "process_refund":
                amount = float(t_args.get("amount", 0))
                order_id = t_args.get("order_id")
                order_amt = MOCK_ORDERS.get(order_id, {}).get("amount", amount)
                effective_amt = max(amount, order_amt)

                if effective_amt > 500.0 and not working_mem.get("is_human_approved", False):
                    working_mem["pending_approval"] = {
                        "action": "process_refund",
                        "args": t_args,
                        "amount": effective_amt,
                    }
                    save_working_memory(state["session_id"], working_mem)
                    pause_msg = AIMessage(
                        content=(
                            f"HUMAN APPROVAL REQUIRED: Refund for {order_id} (${effective_amt:.2f}) "
                            "exceeds the $500 automated limit. A supervisor must approve this action before execution."
                        )
                    )
                    return {
                        "messages": new_messages + [pause_msg],
                        "working_memory": working_mem,
                    }

            if t_name in tool_map:
                try:
                    result = tool_map[t_name].invoke(t_args)
                    # Update working memory if order lookup revealed a linked insurance policy
                    if t_name == "get_order_status" and isinstance(result, dict) and result.get("success"):
                        order_data = result["order"]
                        working_mem["active_order_id"] = order_data["order_id"]
                        working_mem["customer_id"] = order_data["customer_id"]
                        if order_data.get("insurance_policy_id"):
                            working_mem["active_policy_id"] = order_data["insurance_policy_id"]
                        save_working_memory(state["session_id"], working_mem)
                except Exception as e:
                    result = {"success": False, "error": f"Tool input validation error: {str(e)}"}
            else:
                result = {"success": False, "error": f"Permission denied: tool '{t_name}' not assigned to this agent."}

            tool_msg = ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            conversation.append(tool_msg)
            new_messages.append(tool_msg)

    return {"messages": new_messages, "working_memory": working_mem}


def tracking_agent_node(state: AgentState) -> dict:
    return _run_agent_with_tools(state, TRACKING_PROMPT, [get_order_status])


def refund_agent_node(state: AgentState) -> dict:
    return _run_agent_with_tools(state, REFUND_PROMPT, [get_order_status, process_refund])


def insurance_agent_node(state: AgentState) -> dict:
    return _run_agent_with_tools(
        state,
        INSURANCE_PROMPT,
        [get_order_status, get_insurance_policy, file_insurance_claim],
    )


def general_agent_node(state: AgentState) -> dict:
    return _run_agent_with_tools(state, GENERAL_PROMPT, [])