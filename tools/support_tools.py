import uuid
from langchain_core.tools import tool
from tools.mock_db import MOCK_ORDERS, MOCK_INSURANCE, PROCESSED_REFUNDS
from tools.schemas import (
    OrderLookupInput,
    RefundRequestInput,
    InsuranceClaimInput,
    PolicyLookupInput,
)


@tool(args_schema=OrderLookupInput)
def get_order_status(order_id: str) -> dict:
    """Retrieve order details, shipping carrier, tracking number, and delivery status."""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return {"success": False, "error": f"Order '{order_id}' not found in system."}
    return {"success": True, "order": order}


@tool(args_schema=RefundRequestInput)
def process_refund(order_id: str, reason: str, amount: float) -> dict:
    """
    Process a customer refund for an eligible order.
    Note: Refunds over $500 require human supervisor approval before execution.
    """
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return {"success": False, "error": f"Order '{order_id}' not found."}

    if order_id in PROCESSED_REFUNDS:
        return {"success": False, "error": f"Refund already processed for {order_id}."}

    if not order["refundable"]:
        return {
            "success": False,
            "error": f"Order '{order_id}' ({order['item']}) is marked non-refundable (Final Sale).",
        }

    if order["delivered_days_ago"] is not None and order["delivered_days_ago"] > 30:
        return {
            "success": False,
            "error": f"Return window expired. Order was delivered {order['delivered_days_ago']} days ago (limit: 30 days).",
        }

    if amount > order["amount"]:
        return {
            "success": False,
            "error": f"Requested amount (${amount}) exceeds order total (${order['amount']}).",
        }

    refund_id = f"REF-{uuid.uuid4().hex[:6].upper()}"
    record = {
        "refund_id": refund_id,
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "status": "APPROVED_AND_PROCESSED",
    }
    PROCESSED_REFUNDS[order_id] = record
    return {"success": True, "refund": record}


@tool(args_schema=InsuranceClaimInput)
def file_insurance_claim(policy_id: str, incident_description: str, claim_amount: float) -> dict:
    """Check policy coverage and file an insurance claim for damaged or lost shipments."""
    policy = MOCK_INSURANCE.get(policy_id)
    if not policy:
        return {"success": False, "error": f"Insurance policy '{policy_id}' not found."}

    if policy["status"] != "ACTIVE":
        return {"success": False, "error": f"Policy '{policy_id}' is not active."}

    if claim_amount > policy["max_coverage"]:
        return {
            "success": False,
            "error": f"Claim amount (${claim_amount}) exceeds maximum coverage (${policy['max_coverage']}).",
        }

    claim_id = f"CLM-{uuid.uuid4().hex[:6].upper()}"
    claim_record = {
        "claim_id": claim_id,
        "policy_id": policy_id,
        "amount": claim_amount,
        "description": incident_description,
        "status": "SUBMITTED",
    }
    policy["claims_filed"].append(claim_record)
    return {"success": True, "claim": claim_record}


@tool(args_schema=PolicyLookupInput)
def get_insurance_policy(policy_id: str) -> dict:
    """Retrieve shipping insurance policy coverage limit, active status, and linked order ID."""
    policy = MOCK_INSURANCE.get(policy_id)
    if not policy:
        return {"success": False, "error": f"Insurance policy '{policy_id}' was not found."}
    return {"success": True, "policy": policy}