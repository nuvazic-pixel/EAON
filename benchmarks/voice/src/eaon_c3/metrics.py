from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict
from typing import Iterable


def normalize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"[^\W_]+", text, flags=re.UNICODE)


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    previous = list(range(len(hyp) + 1))
    for i, expected in enumerate(ref, 1):
        current = [i]
        for j, actual in enumerate(hyp, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (expected != actual)))
        previous = current
    return previous[-1] / len(ref)


def percentile(values: Iterable[float], q: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    pos = (len(ordered) - 1) * q
    low, high = math.floor(pos), math.ceil(pos)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def summarize(rows: list[dict]) -> dict:
    stages: dict[str, list[float]] = defaultdict(list)
    language_wer: dict[str, list[float]] = defaultdict(list)
    false_accepts = false_rejects = positives = negatives = 0
    for row in rows:
        language_wer[row["language"]].append(float(row["wer"]))
        for stage, value in row["latencies_ms"].items():
            stages[stage].append(float(value))
        expected, detected = row["wake_expected"], row["wake_detected"]
        positives += int(expected); negatives += int(not expected)
        false_accepts += int(not expected and detected)
        false_rejects += int(expected and not detected)
    return {
        "samples": len(rows),
        "wer_by_language": {k: round(sum(v) / len(v), 4) for k, v in sorted(language_wer.items())},
        "wake": {
            "false_accepts": false_accepts, "false_rejects": false_rejects,
            "false_accept_rate": round(false_accepts / negatives, 4) if negatives else None,
            "false_reject_rate": round(false_rejects / positives, 4) if positives else None,
        },
        "latency_ms": {stage: {"p50": round(percentile(vals, .5) or 0, 3),
                               "p95": round(percentile(vals, .95) or 0, 3)}
                       for stage, vals in sorted(stages.items())},
    }
