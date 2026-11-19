# Production Multi-Agent Customer Support System

A production-grade multi-agent AI customer support system built with **Python 3.12**, **LangGraph**, **Pydantic v2**, **SQLite**, and **Google Gemini**, engineered with deterministic routing, typed tool execution, persistent working memory, defense-in-depth security guardrails, human-in-the-loop approval gates, structured observability, and a 22-case automated evaluation benchmark.

---

## 1. Problem Statement
Customer support operations require resolving high-stakes requests—order tracking, refund eligibility, and shipping insurance claims—without hallucinating policies, leaking sensitive system details, or executing unauthorized financial payouts. Single-prompt chatbots lack strict tool permission boundaries and human oversight. This system solves that challenge using a supervised multi-agent architecture with deterministic validation and audit trails.

---

## 2. System Architecture & Technology Stack

### High-Level Flow
1. **Input Security Guardrail (`security/guardrails.py`)**: Validates every incoming message before any LLM call—blocking prompt-injection overrides, SQL/XSS payloads, and oversized inputs while recording tamper-evident events in `audit.log`.
2. **Supervisor / Router (`agents/router.py`)**: Extracts order/policy entities (`ORD-XXXX`, `INS-XXX`) into persistent SQLite working memory and routes the request via structured output (`RouteDecision`) to the appropriate specialist[cite: 1].
3. **Specialist Agents (`agents/specialists.py`)**:
   - **Tracking Specialist**: Handles shipment status and carrier tracking (`get_order_status`)[cite: 1].
   - **Refund Specialist**: Verifies return windows (30-day limit) and processes eligible refunds (`get_order_status`, `process_refund`), pausing for human supervisor sign-off on payouts exceeding **$500**[cite: 1].
   - **Insurance Specialist**: Verifies active coverage and files transit/damage claims (`get_order_status`, `file_insurance_claim`)[cite: 1].
   - **General Support Assistant**: Handles greetings and general policy inquiries[cite: 1].
4. **Typed Tool Layer (`tools/`)**: Enforces strict Pydantic v2 input schemas (`OrderLookupInput`, `RefundRequestInput`, `InsuranceClaimInput`) against simulated backend databases (`tools/mock_db.py`)[cite: 1].

*(Detailed Mermaid flowcharts and sequence diagrams are available in [`diagrams/architecture.md`](diagrams/architecture.md)[cite: 1].)*

---

## 3. Repository Structure
```text
customer-support-multi-agent/
├── agents/                  # Router orchestrator, specialist agents, LangGraph StateGraph, LLM factory
├── tools/                   # Pydantic schemas, typed @tool functions, simulated backend DB
├── memory/                  # AgentState schema & SQLite working memory + session checkpointer
├── security/                # Pre-LLM input guardrails, RBAC permissions, audit logger, threat model
├── eval/                    # 22-case benchmark dataset & accuracy/latency/cost evaluation runner
├── ops/                     # Structured JSON logger & production deployment/scaling runbook
├── diagrams/                # Mermaid architecture & memory lifecycle diagrams
├── main.py                  # Interactive CLI runner with human-in-the-loop supervisor gate
├── Dockerfile               # Container image specification
├── docker-compose.yml       # Container orchestration configuration
├── .env.example             # Template for required environment variables
└── requirements.txt         # Pinned Python dependencies