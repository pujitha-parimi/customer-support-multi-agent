import json
import time
import uuid
from pathlib import Path
from langchain_core.messages import HumanMessage
from agents.graph import build_support_graph
from memory.store import default_working_memory

DATASET_PATH = Path(__file__).parent / "dataset.json"
OUTPUT_PATH = Path(__file__).parent / "results_latest.json"

# Estimated pricing per 1M tokens for Gemini Flash-Lite tier (USD)
EST_INPUT_COST_PER_1M = 0.075
EST_OUTPUT_COST_PER_1M = 0.30


def extract_text(content) -> str:
    if isinstance(content, list):
        return "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        ).strip()
    return str(content).strip()


def run_benchmark():
    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    graph = build_support_graph()

    results = []
    passed_count = 0
    total_latency_ms = 0.0
    total_est_cost_usd = 0.0

    print(f"\nRunning Evaluation Benchmark ({len(cases)} cases)...\n")

    for idx, case in enumerate(cases):
        session_id = f"eval-{uuid.uuid4().hex[:8]}"
        trace_id = f"tr-{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": session_id}}

        start = time.perf_counter()
        output = graph.invoke(
            {
                "messages": [HumanMessage(content=case["query"])],
                "session_id": session_id,
                "trace_id": trace_id,
                "working_memory": default_working_memory(),
                "next_agent": None,
                "security_blocked": False,
                "security_reason": None,
            },
            config=config,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        total_latency_ms += latency_ms

        actual_agent = output.get("next_agent")
        actual_blocked = bool(output.get("security_blocked"))
        reply_text = extract_text(output["messages"][-1].content)

        # Estimate token usage & cost (~4 chars per token)
        est_in_tokens = max(120, len(case["query"]) // 4 + 250)
        est_out_tokens = max(30, len(reply_text) // 4)
        case_cost = (est_in_tokens / 1_000_000) * EST_INPUT_COST_PER_1M + (
            est_out_tokens / 1_000_000
        ) * EST_OUTPUT_COST_PER_1M
        total_est_cost_usd += case_cost

        route_ok = (actual_agent == case["expected_agent"]) and (actual_blocked == case["expected_blocked"])
        keyword_ok = any(kw.lower() in reply_text.lower() for kw in case["expected_keywords"])
        case_passed = route_ok and keyword_ok

        if case_passed:
            passed_count += 1

        status_icon = "PASS" if case_passed else "FAIL"
        print(
            f"[{status_icon}] {case['id']} ({case['category']}) | "
            f"Agent={actual_agent} | Blocked={actual_blocked} | {latency_ms}ms"
        )

        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "passed": case_passed,
                "route_ok": route_ok,
                "keyword_ok": keyword_ok,
                "expected_agent": case["expected_agent"],
                "actual_agent": actual_agent,
                "expected_blocked": case["expected_blocked"],
                "actual_blocked": actual_blocked,
                "latency_ms": latency_ms,
                "est_cost_usd": round(case_cost, 6),
                "reply_preview": reply_text[:140],
            }
        )

        # Pace requests for Free Tier 15 RPM limit on LLM-backed cases
        if not actual_blocked and idx < len(cases) - 1:
            time.sleep(13)

    accuracy = round((passed_count / len(cases)) * 100, 2)
    avg_latency = round(total_latency_ms / len(cases), 2)

    summary = {
        "total_cases": len(cases),
        "passed_cases": passed_count,
        "accuracy_percent": accuracy,
        "avg_latency_ms": avg_latency,
        "total_estimated_cost_usd": round(total_est_cost_usd, 6),
        "results": results,
    }

    OUTPUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n====================================================")
    print(f"  Benchmark Accuracy : {accuracy}% ({passed_count}/{len(cases)})")
    print(f"  Average Latency    : {avg_latency} ms")
    print(f"  Est. Total Cost    : ${summary['total_estimated_cost_usd']:.6f}")
    print(f"  Report saved to    : {OUTPUT_PATH}")
    print("====================================================\n")


if __name__ == "__main__":
    run_benchmark()