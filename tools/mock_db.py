from datetime import datetime, timedelta

# Simulated Orders Database
MOCK_ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "customer_id": "CUST-01",
        "customer_email": "pujitha@example.com",
        "item": "Noise-Cancelling Headphones",
        "amount": 249.99,
        "status": "DELIVERED",
        "carrier": "BlueDart Express",
        "tracking_number": "BD987654321IN",
        "delivered_days_ago": 5,
        "refundable": True,
        "insured": True,
        "insurance_policy_id": "INS-501",
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "customer_id": "CUST-01",
        "customer_email": "pujitha@example.com",
        "item": "Mechanical Keyboard (Final Sale)",
        "amount": 129.00,
        "status": "DELIVERED",
        "carrier": "Delhivery",
        "tracking_number": "DL112233445IN",
        "delivered_days_ago": 45,  # Outside 30-day return window
        "refundable": False,
        "insured": False,
        "insurance_policy_id": None,
    },
    "ORD-1003": {
        "order_id": "ORD-1003",
        "customer_id": "CUST-02",
        "customer_email": "rahul@example.com",
        "item": "4K Ultra-Wide Monitor",
        "amount": 650.00,  # High-value refund (> $500 requires human approval!)
        "status": "IN_TRANSIT",
        "carrier": "DHL",
        "tracking_number": "DHL99887766",
        "delivered_days_ago": None,
        "refundable": True,
        "insured": True,
        "insurance_policy_id": "INS-502",
    },
}

# Simulated Insurance Policies Database
MOCK_INSURANCE = {
    "INS-501": {
        "policy_id": "INS-501",
        "order_id": "ORD-1001",
        "coverage_type": "Accidental Damage & Loss",
        "max_coverage": 300.00,
        "status": "ACTIVE",
        "claims_filed": [],
    },
    "INS-502": {
        "policy_id": "INS-502",
        "order_id": "ORD-1003",
        "coverage_type": "Full Transit & Damage Protection",
        "max_coverage": 700.00,
        "status": "ACTIVE",
        "claims_filed": [],
    },
}

# Store processed refunds in memory for session/audit tracking
PROCESSED_REFUNDS = {}