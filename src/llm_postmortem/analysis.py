"""Deterministic, explainable failure analysis for LLM call logs."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable


FAILURE_ORDER = [
    "tool_failure",
    "format_error",
    "refusal",
    "hallucination",
    "retrieval_failure",
    "timeout",
    "unknown_failure",
]


@dataclass
class Finding:
    kind: str
    count: int
    share: float
    examples: list[dict[str, Any]] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class Report:
    total_calls: int
    failed_calls: int
    findings: list[Finding]
    model_stats: dict[str, dict[str, float]]
    input_errors: list[str]


def _text(record: dict[str, Any]) -> str:
    """Combine the common log fields without requiring a fixed vendor schema."""
    fields = ("prompt", "input", "response", "output", "error", "feedback", "expected")
    return " ".join(str(record.get(field, "")) for field in fields).lower()


def is_failure(record: dict[str, Any]) -> bool:
    status = str(record.get("status", "")).lower()
    score = record.get("score")
    passed = record.get("passed")
    if status in {"error", "failed", "failure", "timeout"} or passed is False:
        return True
    if isinstance(score, (int, float)) and score < 0.5:
        return True
    return bool(record.get("error"))


def classify(record: dict[str, Any]) -> str:
    text = _text(record)
    status = str(record.get("status", "")).lower()
    if any(word in text for word in ("tool_call", "tool call", "function call", "traceback", "exception")):
        return "tool_failure"
    if any(word in text for word in ("json", "schema", "parse", "format", "validation")):
        return "format_error"
    if any(word in text for word in ("retrieval", "no documents", "no context", "not found in source", "citation")):
        return "retrieval_failure"
    if any(word in text for word in ("i can't", "i cannot", "i'm sorry", "cannot help", "refuse")):
        return "refusal"
    if any(word in text for word in ("hallucinat", "made up", "fabricat", "incorrect fact", "not in context")):
        return "hallucination"
    if status == "timeout" or "timeout" in text or "timed out" in text:
        return "timeout"
    return "unknown_failure"


RECOMMENDATIONS = {
    "tool_failure": "Validate tool arguments against a schema, return recoverable tool errors, and add a retry prompt containing the exact error.",
    "format_error": "Use structured outputs or JSON schema validation, then retry once with the validation error included.",
    "refusal": "Separate policy-sensitive requests from normal flows and test whether the system prompt is over-constraining the model.",
    "hallucination": "Require grounded citations for factual answers and add an explicit 'insufficient evidence' path.",
    "retrieval_failure": "Inspect recall before changing the prompt: tune chunking, top-k, reranking, and metadata filters.",
    "timeout": "Set per-step time budgets, stream where possible, and fall back to a faster model or shorter context.",
    "unknown_failure": "Add a human label for these examples; recurring labels are the best signal for the next classifier rule.",
}


def analyze(records: Iterable[dict[str, Any]], errors: list[str] | None = None) -> Report:
    records = list(records)
    failures = [record for record in records if is_failure(record)]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in failures:
        groups[classify(record)].append(record)

    findings = [
        Finding(
            kind=kind,
            count=len(group),
            share=len(group) / len(failures) if failures else 0,
            examples=group[:3],
            recommendation=RECOMMENDATIONS[kind],
        )
        for kind, group in groups.items()
    ]
    findings.sort(key=lambda item: (-item.count, FAILURE_ORDER.index(item.kind)))

    per_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        per_model[str(record.get("model", "unknown"))].append(record)
    model_stats = {}
    for model, entries in sorted(per_model.items()):
        model_stats[model] = {
            "calls": len(entries),
            "failures": sum(is_failure(entry) for entry in entries),
            "avg_latency_ms": round(sum(float(entry.get("latency_ms", 0) or 0) for entry in entries) / len(entries), 1),
            "avg_cost_usd": round(sum(float(entry.get("cost_usd", 0) or 0) for entry in entries) / len(entries), 5),
        }
    return Report(len(records), len(failures), findings, model_stats, errors or [])


def top_keywords(records: Iterable[dict[str, Any]], limit: int = 5) -> list[str]:
    words = Counter()
    for record in records:
        for word in _text(record).split():
            cleaned = word.strip(".,!?;:()[]{}\"'")
            if len(cleaned) >= 5:
                words[cleaned] += 1
    return [word for word, _ in words.most_common(limit)]
