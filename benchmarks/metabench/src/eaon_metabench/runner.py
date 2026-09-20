from __future__ import annotations

from collections.abc import Callable

from eaon_metabench.adapters.base import ModelAdapter
from eaon_metabench.models import BenchmarkCase, CaseResult
from eaon_metabench.parsing import parse_model_answer
from eaon_metabench.scoring import build_case_result


ProgressCallback = Callable[[int, int, CaseResult], None]


def run_suite(
    adapter: ModelAdapter,
    cases: list[BenchmarkCase],
    progress: ProgressCallback | None = None,
) -> list[CaseResult]:
    results: list[CaseResult] = []

    for index, case in enumerate(cases, start=1):
        try:
            response = adapter.generate(case)
            parsed, parse_error = parse_model_answer(response.text)
            result = build_case_result(
                case=case,
                parsed_answer=parsed,
                raw_response=response.text,
                latency_ms=response.latency_ms,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                error=parse_error,
            )
        except Exception as exc:  # The run must survive one provider failure.
            result = build_case_result(
                case=case,
                parsed_answer=None,
                raw_response="",
                latency_ms=0.0,
                error=f"{type(exc).__name__}: {exc}",
            )

        results.append(result)
        if progress:
            progress(index, len(cases), result)

    return results
