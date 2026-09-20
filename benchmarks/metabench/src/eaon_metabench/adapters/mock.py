from __future__ import annotations

import json

from eaon_metabench.adapters.base import ModelAdapter
from eaon_metabench.models import AdapterResponse, BenchmarkCase


class PerfectMockAdapter(ModelAdapter):
    """Offline adapter used to verify the harness and scoring pipeline."""

    def generate(self, case: BenchmarkCase) -> AdapterResponse:
        decision = case.expected_decision
        answer = case.accepted_answers[0] if decision == "answer" and case.accepted_answers else ""
        payload = {
            "decision": decision,
            "answer": answer,
            "confidence": 0.99,
            "reason": "Mock response generated from the test oracle.",
        }
        return AdapterResponse(text=json.dumps(payload), latency_ms=1.0)
