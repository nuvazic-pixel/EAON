"""Exact-model dispatch boundary for the original INTEL orchestrator."""

from __future__ import annotations

from types import MappingProxyType
from typing import Callable, Mapping


class ModelDispatchError(ValueError):
    """A model ID or its response failed gateway validation."""


class InferenceGateway:
    """Dispatch only IDs explicitly selected by the deterministic orchestrator.

    Model recommendations from observers must never be passed as the authorized
    model ID. There is no implicit default or retry on another model.
    """

    def __init__(self, handlers: Mapping[str, Callable[[str], str]]) -> None:
        self._handlers = MappingProxyType(dict(handlers))

    def dispatch(self, logical_model_id: str | None, prompt: str) -> str:
        if (not isinstance(logical_model_id, str) or not logical_model_id or
                logical_model_id not in self._handlers):
            raise ModelDispatchError("unknown_model_id")
        result = self._handlers[logical_model_id](prompt)
        if not isinstance(result, str) or not result.strip():
            raise ModelDispatchError("empty_model_response")
        return result
