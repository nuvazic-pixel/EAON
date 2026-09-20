from __future__ import annotations

import math
import re
from collections import defaultdict
from statistics import mean, median
from typing import Any

from eaon_metabench.models import BenchmarkCase, CaseResult, ModelAnswer


def normalize_answer(value: str) -> str:
    value = value.strip().upper()
    value = re.sub(r"\s+", " ", value)
    value = value.rstrip(".")
    return value


def answer_is_correct(case: BenchmarkCase, answer: ModelAnswer) -> bool:
    if answer.decision != case.expected_decision:
        return False
    if case.expected_decision == "abstain":
        return True
    normalized = normalize_answer(answer.answer)
    accepted = {normalize_answer(item) for item in case.accepted_answers}
    return normalized in accepted


def confidence_calibration_score(confidence: float, correct: bool) -> float:
    target = 1.0 if correct else 0.0
    brier = (confidence - target) ** 2
    return max(0.0, 1.0 - brier)


def build_case_result(
    case: BenchmarkCase,
    parsed_answer: ModelAnswer | None,
    raw_response: str,
    latency_ms: float,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    error: str | None = None,
) -> CaseResult:
    correct = parsed_answer is not None and answer_is_correct(case, parsed_answer)
    confidence = parsed_answer.confidence if parsed_answer else 0.0
    calibration = confidence_calibration_score(confidence, correct)

    expected_abstain = case.expected_decision == "abstain"
    predicted_abstain = parsed_answer is not None and parsed_answer.decision == "abstain"

    return CaseResult(
        case=case,
        parsed_answer=parsed_answer,
        raw_response=raw_response,
        parse_ok=parsed_answer is not None,
        correct=correct,
        confidence_score=calibration,
        abstention_true_positive=expected_abstain and predicted_abstain,
        abstention_false_positive=(not expected_abstain) and predicted_abstain,
        abstention_false_negative=expected_abstain and (not predicted_abstain),
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        error=error,
    )


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def summarize(results: list[CaseResult]) -> dict[str, Any]:
    if not results:
        raise ValueError("Cannot summarize an empty result set.")

    total = len(results)
    correct = sum(result.correct for result in results)
    parse_rate = sum(result.parse_ok for result in results) / total
    accuracy = correct / total
    calibration = mean(result.confidence_score for result in results)

    tp = sum(result.abstention_true_positive for result in results)
    fp = sum(result.abstention_false_positive for result in results)
    fn = sum(result.abstention_false_negative for result in results)
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    abstention_f1 = _safe_div(2 * precision * recall, precision + recall)

    category_buckets: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        category_buckets[result.case.category].append(result)

    categories: dict[str, Any] = {}
    for category, bucket in sorted(category_buckets.items()):
        categories[category] = {
            "count": len(bucket),
            "accuracy": mean(item.correct for item in bucket),
            "calibration": mean(item.confidence_score for item in bucket),
            "median_latency_ms": median(item.latency_ms for item in bucket),
        }

    recovery_dimensions = [
        categories.get("rule_shift", {}).get("accuracy", 0.0),
        categories.get("error_repair", {}).get("accuracy", 0.0),
    ]
    recovery_score = mean(recovery_dimensions)

    overall = (
        0.45 * accuracy
        + 0.25 * calibration
        + 0.15 * abstention_f1
        + 0.15 * recovery_score
    )

    prompt_tokens = [item.prompt_tokens for item in results if item.prompt_tokens is not None]
    completion_tokens = [
        item.completion_tokens for item in results if item.completion_tokens is not None
    ]

    return {
        "total_cases": total,
        "overall_score": round(overall, 6),
        "accuracy": round(accuracy, 6),
        "calibration_score": round(calibration, 6),
        "abstention_precision": round(precision, 6),
        "abstention_recall": round(recall, 6),
        "abstention_f1": round(abstention_f1, 6),
        "recovery_adaptation_score": round(recovery_score, 6),
        "parse_rate": round(parse_rate, 6),
        "median_latency_ms": round(median(item.latency_ms for item in results), 3),
        "p95_latency_ms": round(_percentile([item.latency_ms for item in results], 0.95), 3),
        "total_prompt_tokens": sum(prompt_tokens) if prompt_tokens else None,
        "total_completion_tokens": sum(completion_tokens) if completion_tokens else None,
        "categories": categories,
    }


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction
