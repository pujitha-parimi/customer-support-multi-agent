from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


class OrderLookupInput(BaseModel):
    order_id: str = Field(
        ...,
        description="The unique order identifier, formatted as ORD-XXXX (e.g., ORD-1001).",
    )

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^ORD-\d{4}$", v):
            raise ValueError("Invalid order_id format. Must match 'ORD-XXXX' (e.g., ORD-1001).")
        return v


class RefundRequestInput(BaseModel):
    order_id: str = Field(..., description="Order ID to refund (format: ORD-XXXX).")
    reason: str = Field(..., min_length=5, max_length=200, description="Clear reason for the refund.")
    amount: float = Field(..., gt=0, description="Refund amount in USD.")

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^ORD-\d{4}$", v):
            raise ValueError("Invalid order_id format. Must match 'ORD-XXXX'.")
        return v


class InsuranceClaimInput(BaseModel):
    policy_id: str = Field(..., description="Insurance policy ID (format: INS-XXX).")
    incident_description: str = Field(
        ..., min_length=10, max_length=500, description="Description of the damage or loss."
    )
    claim_amount: float = Field(..., gt=0, description="Requested claim payout in USD.")

    @field_validator("policy_id")
    @classmethod
    def validate_policy_id(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^INS-\d{3}$", v):
            raise ValueError("Invalid policy_id format. Must match 'INS-XXX' (e.g., INS-501).")
        return v


class PolicyLookupInput(BaseModel):
    policy_id: str = Field(..., description="Shipping insurance policy ID in format INS-XXX (e.g., INS-502).")

    @field_validator("policy_id")
    @classmethod
    def validate_policy_id(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not re.match(r"^INS-\d{3}$", cleaned):
            raise ValueError("Invalid policy_id format. Must match 'INS-XXX' (e.g., INS-502).")
        return cleaned