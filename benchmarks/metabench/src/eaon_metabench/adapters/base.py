from __future__ import annotations

from abc import ABC, abstractmethod

from eaon_metabench.models import AdapterResponse, BenchmarkCase


class ModelAdapter(ABC):
    @abstractmethod
    def generate(self, case: BenchmarkCase) -> AdapterResponse:
        """Generate one response for a benchmark case."""
        raise NotImplementedError
