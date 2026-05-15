"""Evaluate retrieval quality with RAGAS when available, otherwise manual rubric."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
for path in (PROJECT_ROOT, BACKEND_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

EVALUATION_DIR = BACKEND_DIR / "evaluation"
GOLD_QUERIES_PATH = EVALUATION_DIR / "gold_queries.json"
RAW_RESULTS_PATH = EVALUATION_DIR / "raw_results.json"
RESULTS_MD_PATH = EVALUATION_DIR / "results.md"


@dataclass(frozen=True)
class EvalSummary:
    """Aggregated evaluation metrics."""

    total: int
    passed: int
    failed: int
    pass_rate: float
    strategy_accuracy: float
    language_accuracy: float
    citation_pass_rate: float
    data_availability_accuracy: float
    average_latency_ms: float
    ragas_available: bool


def load_gold_queries(path: Path = GOLD_QUERIES_PATH) -> list[dict[str, Any]]:
    """Load gold query specs."""
    return json.loads(path.read_text(encoding="utf-8"))


def ragas_available() -> bool:
    """Return whether RAGAS dependencies are installed."""
    try:
        import ragas  # noqa: F401
        import datasets  # noqa: F401
    except Exception:
        return False
    return True


def call_chat_api(question: str, api_url: str, timeout: int) -> tuple[dict[str, Any], float]:
    """Call running FastAPI backend."""
    started = time.perf_counter()
    response = requests.post(
        f"{api_url.rstrip('/')}/api/chat",
        json={"question": question},
        timeout=timeout,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    return response.json(), elapsed_ms


def call_chat_test_client(question: str) -> tuple[dict[str, Any], float]:
    """Fallback to in-process FastAPI TestClient."""
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    started = time.perf_counter()
    response = client.post("/api/chat", json={"question": question})
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.raise_for_status()
    return response.json(), elapsed_ms


def contains_any(answer: str, expected_terms: list[str]) -> bool:
    """Check if answer contains at least one expected term."""
    if not expected_terms:
        return True
    lowered = answer.lower()
    return any(term.lower() in lowered for term in expected_terms)


def contains_none(answer: str, forbidden_terms: list[str]) -> bool:
    """Check if answer contains no forbidden terms."""
    lowered = answer.lower()
    return not any(term.lower() in lowered for term in forbidden_terms)


def score_case(case: dict[str, Any], response: dict[str, Any], latency_ms: float) -> dict[str, Any]:
    """Score one query with deterministic rubric."""
    citations = response.get("citations") or []
    answer = str(response.get("answer") or "")
    checks = {
        "strategy": response.get("strategy_used") == case["expected_strategy"],
        "language": response.get("language") == case["expected_language"],
        "data_available": bool(response.get("data_available")) == bool(case["expected_data_available"]),
        "citations": (len(citations) > 0) if case.get("requires_citations") else len(citations) == 0,
        "must_contain_any": contains_any(answer, case.get("must_contain_any", [])),
        "must_not_contain": contains_none(answer, case.get("must_not_contain", [])),
    }
    passed = all(checks.values())
    return {
        "id": case["id"],
        "question": case["question"],
        "expected_strategy": case["expected_strategy"],
        "actual_strategy": response.get("strategy_used"),
        "expected_language": case["expected_language"],
        "actual_language": response.get("language"),
        "expected_data_available": case["expected_data_available"],
        "actual_data_available": response.get("data_available"),
        "citation_count": len(citations),
        "latency_ms": round(latency_ms, 2),
        "checks": checks,
        "passed": passed,
        "answer_preview": answer[:300],
        "fallback_signal": response.get("fallback_signal"),
    }


def evaluate_cases(
    cases: list[dict[str, Any]],
    api_url: str,
    timeout: int,
    prefer_http: bool,
) -> list[dict[str, Any]]:
    """Run all cases through backend."""
    results: list[dict[str, Any]] = []
    for case in cases:
        try:
            if prefer_http:
                response, latency_ms = call_chat_api(case["question"], api_url, timeout)
            else:
                response, latency_ms = call_chat_test_client(case["question"])
        except Exception as exc:
            if prefer_http:
                response, latency_ms = call_chat_test_client(case["question"])
                scored = score_case(case, response, latency_ms)
                scored["transport_fallback"] = f"http_failed: {exc}"
                results.append(scored)
                continue
            results.append(
                {
                    "id": case["id"],
                    "question": case["question"],
                    "passed": False,
                    "error": str(exc),
                    "checks": {},
                    "latency_ms": 0,
                }
            )
            continue
        results.append(score_case(case, response, latency_ms))
    return results


def summarize(results: list[dict[str, Any]], has_ragas: bool) -> EvalSummary:
    """Build aggregate metrics."""
    total = len(results)
    passed = sum(1 for item in results if item.get("passed"))
    failed = total - passed
    latencies = [float(item.get("latency_ms") or 0) for item in results]

    def rate(check_name: str) -> float:
        values = [bool(item.get("checks", {}).get(check_name)) for item in results if item.get("checks")]
        return sum(values) / len(values) if values else 0.0

    return EvalSummary(
        total=total,
        passed=passed,
        failed=failed,
        pass_rate=passed / total if total else 0.0,
        strategy_accuracy=rate("strategy"),
        language_accuracy=rate("language"),
        citation_pass_rate=rate("citations"),
        data_availability_accuracy=rate("data_available"),
        average_latency_ms=statistics.mean(latencies) if latencies else 0.0,
        ragas_available=has_ragas,
    )


def write_raw_results(results: list[dict[str, Any]], summary: EvalSummary) -> None:
    """Persist raw evaluation results."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary.__dict__,
        "results": results,
    }
    RAW_RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_markdown(results: list[dict[str, Any]], summary: EvalSummary) -> str:
    """Render evaluation report."""
    failed = [item for item in results if not item.get("passed")]
    passed = [item for item in results if item.get("passed")]
    lines = [
        "# Evaluation Results",
        "",
        f"Generated at: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Method",
        "",
        (
            "RAGAS dependencies were available, but this script still records the deterministic rubric output."
            if summary.ragas_available
            else "RAGAS package is not installed in the active Python environment, so fallback manual evaluation was used."
        ),
        "The fallback rubric checks strategy, language, data availability, citations, required terms, and forbidden terms.",
        "",
        "## Metrics",
        "",
        f"- Total queries: {summary.total}",
        f"- Passed: {summary.passed}",
        f"- Failed: {summary.failed}",
        f"- Pass rate: {summary.pass_rate:.2%}",
        f"- Strategy accuracy: {summary.strategy_accuracy:.2%}",
        f"- Language accuracy: {summary.language_accuracy:.2%}",
        f"- Citation pass rate: {summary.citation_pass_rate:.2%}",
        f"- Data availability accuracy: {summary.data_availability_accuracy:.2%}",
        f"- Average latency: {summary.average_latency_ms:.0f} ms",
        "",
        "## Passed Examples",
        "",
    ]
    for item in passed[:5]:
        lines.extend(
            [
                f"### {item['id']}",
                f"- Question: {item['question']}",
                f"- Strategy: {item.get('actual_strategy')}",
                f"- Citations: {item.get('citation_count')}",
                f"- Preview: {item.get('answer_preview')}",
                "",
            ]
        )
    lines.extend(["## Failure Cases", ""])
    if not failed:
        lines.append("No failed cases in this run.")
        lines.append("")
    else:
        for item in failed:
            failed_checks = [
                name for name, passed_check in item.get("checks", {}).items() if not passed_check
            ]
            lines.extend(
                [
                    f"### {item['id']}",
                    f"- Question: {item['question']}",
                    f"- Expected strategy: {item.get('expected_strategy')}",
                    f"- Actual strategy: {item.get('actual_strategy')}",
                    f"- Failed checks: {', '.join(failed_checks) or item.get('error', 'unknown')}",
                    f"- Preview: {item.get('answer_preview')}",
                    "",
                ]
            )
    lines.extend(
        [
            "## Recommendations",
            "",
            "- Keep answer synthesis constrained to retrieved rows and citations.",
            "- Treat UCL queries as unsupported negative cases.",
            "- Do not surface unavailable advanced stats such as xG or progressive actions unless real values exist in context.",
            "- Before demo, rerun this script after any prompt or router change.",
            "",
            "## Raw Results",
            "",
            "See `backend/evaluation/raw_results.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_results_md(results: list[dict[str, Any]], summary: EvalSummary) -> None:
    """Persist markdown evaluation report."""
    RESULTS_MD_PATH.write_text(build_markdown(results, summary), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Evaluate KG-RAG chat endpoint")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--no-http", action="store_true")
    return parser


def main() -> None:
    """Run evaluation."""
    args = build_arg_parser().parse_args()
    cases = load_gold_queries()
    has_ragas = ragas_available()
    results = evaluate_cases(
        cases,
        api_url=args.api_url,
        timeout=args.timeout,
        prefer_http=not args.no_http,
    )
    summary = summarize(results, has_ragas)
    write_raw_results(results, summary)
    write_results_md(results, summary)
    print(json.dumps(summary.__dict__, ensure_ascii=False, indent=2))
    if summary.failed:
        print("FAILED_CASES")
        for item in results:
            if not item.get("passed"):
                print(f"{item['id']}: {item.get('checks') or item.get('error')}")


if __name__ == "__main__":
    main()
