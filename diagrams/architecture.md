# System Architecture Diagrams

## 1. Multi-Agent Orchestration & Guardrail Flow

```mermaid
flowchart TD
    User([Customer Input]) --> Guardrail[Input Security Guardrail\nsecurity/guardrails.py]
    Guardrail -->|Blocked: Injection / XSS / Length| AuditBlock[(audit.log)]
    AuditBlock --> Reject([Safe Rejection Response])

    Guardrail -->|Validated| Router[Supervisor / Router Agent\nagents/router.py]
    Router <--> Memory[(SQLite Working Memory &\nSession Checkpointer)]

    Router -->|Tracking Intent| Tracking[Tracking Specialist\nTool: get_order_status]
    Router -->|Refund Intent| Refund[Refund Specialist\nTools: get_order_status, process_refund]
    Router -->|Insurance Intent| Insurance[Insurance Specialist\nTools: get_order_status, file_insurance_claim]
    Router -->|General / Greeting| General[General Support Agent\nNo Tools]

    Refund -->|Amount > $500| HumanGate{Human Supervisor\nApproval Gate}
    HumanGate -->|Approved| ExecuteTool[Execute Typed Pydantic Tool]
    HumanGate -->|Declined| DeclineMsg([Refund Declined])

    Tracking --> ExecuteTool
    Insurance --> ExecuteTool
    ExecuteTool <--> MockDB[(Simulated Backend DB\ntools/mock_db.py)]
    ExecuteTool --> AuditLog[(audit.log & Structlog JSON)]
    AuditLog --> FinalReply([Customer Response])
    General --> FinalReply