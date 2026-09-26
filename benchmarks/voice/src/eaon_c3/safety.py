"""Mock-only voice tool path. This module does not launch an audio or tool process.

NetworkBoundary is supplied by the host environment. A fake boundary is suitable
for policy tests, but cannot establish OS-level isolation for a live voice test.
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol

from .journal import StateJournal, verify


class InterlockError(RuntimeError):
    """The dry-run is not permitted to start or continue."""


class NetworkBoundary(Protocol):
    def verify_isolated(self) -> bool:
        """Return True only while an external network boundary is in force."""


class UnverifiedNetworkBoundary:
    def verify_isolated(self) -> bool:
        return False


class EmergencyStop:
    def __init__(self) -> None:
        self._armed = True

    @property
    def armed(self) -> bool:
        return self._armed

    def trip(self) -> None:
        self._armed = False


class MockToolExecutor:
    """Returns data only; it has no connection to the real tool registry."""

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, requested_tool: str) -> dict[str, Any]:
        self.calls += 1
        return {
            "status": "SIMULATED",
            "requested_tool": requested_tool,
            "validated": True,
            "reason": "dry_run",
            "real_world_effect": False,
        }


@dataclass(frozen=True)
class VoiceToolAttempt:
    requested_tool: str
    arguments: Mapping[str, Any]
    model_id: str | None
    wake_valid: bool
    source: str  # human, tts, or unknown; supplied by a trusted audio-source gate
    intent_confidence: float
    raw_model_output: str = ""
    shadow_recommendation: str | None = None


class DryRunSession:
    """Fail-closed policy and trajectory journal for an in-process mock executor.

    The trusted caller must supply wake/source classification, argument validators,
    and a network boundary. No live Sherpa wrapper is connected by this class.
    """

    def __init__(
        self,
        *,
        dry_run: bool,
        executor: MockToolExecutor,
        real_tool_registry: object | None,
        network_boundary: NetworkBoundary | None,
        journal: StateJournal,
        emergency_stop: EmergencyStop,
        authorized_model_id: str | None,
        allowed_model_ids: frozenset[str],
        tool_validators: Mapping[str, Callable[[Mapping[str, Any]], bool]],
        minimum_confidence: float = 0.5,
    ) -> None:
        self.dry_run = dry_run
        self.executor = executor
        self.real_tool_registry = real_tool_registry
        self.network_boundary = network_boundary or UnverifiedNetworkBoundary()
        self.journal = journal
        self.emergency_stop = emergency_stop
        self.authorized_model_id = authorized_model_id
        self.allowed_model_ids = frozenset(allowed_model_ids)
        self.tool_validators = MappingProxyType(dict(tool_validators))
        self.minimum_confidence = minimum_confidence
        self.session_id = str(uuid.uuid4())
        self.started = False
        self.blocked_actions = 0
        self._journal_head: str | None = None

    def _check(self) -> None:
        if self.dry_run is not True:
            raise InterlockError("dry_run_required")
        if type(self.executor) is not MockToolExecutor:
            raise InterlockError("mock_executor_required")
        if self.real_tool_registry is not None:
            raise InterlockError("real_registry_must_be_disconnected")
        try:
            isolated = self.network_boundary.verify_isolated()
        except Exception as exc:
            raise InterlockError("network_boundary_unverified") from exc
        if isolated is not True:
            raise InterlockError("outbound_network_not_blocked")
        if self.emergency_stop.armed is not True:
            raise InterlockError("emergency_stop_disarmed")
        if (not self.authorized_model_id or
                self.authorized_model_id not in self.allowed_model_ids):
            raise InterlockError("unknown_authorized_model_id")
        if not 0 <= self.minimum_confidence <= 1 or not math.isfinite(self.minimum_confidence):
            raise InterlockError("invalid_confidence_threshold")
        if type(self.journal) is not StateJournal:
            raise InterlockError("state_journal_required")
        try:
            if not self.journal.path.exists():
                if self._journal_head is not None:
                    raise InterlockError("journal_missing_after_start")
            else:
                valid, _, _ = verify(self.journal.path, expected_head=self._journal_head)
                if not valid:
                    raise InterlockError("journal_integrity_error")
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise InterlockError("journal_unavailable") from exc

    def _record(self, turn_id: str, event: str, parent_span_id: str | None,
                **details: Any) -> str:
        span_id = str(uuid.uuid4())
        payload = {
            "schema": "eaon.trajectory/v1",
            "session_id": self.session_id,
            "turn_id": turn_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "event": event,
            **details,
        }
        try:
            record = self.journal.append("Observation", f"voice_session/{self.session_id}", payload)
        except Exception as exc:
            self.emergency_stop.trip()
            raise InterlockError("journal_write_failed") from exc
        self._journal_head = record["hash"]
        return span_id

    def start(self) -> None:
        if self.started:
            raise InterlockError("session_already_started")
        self._check()
        self._record("preflight", "preflight", None,
                     status="PASS", model_id=self.authorized_model_id)
        self.started = True

    def _reject_reason(self, attempt: VoiceToolAttempt, serializable: bool) -> str | None:
        if attempt.source != "human":
            return "source_not_verified_human"
        if attempt.wake_valid is not True:
            return "wake_not_authorized"
        if attempt.model_id != self.authorized_model_id:
            return "model_id_not_authorized"
        confidence = attempt.intent_confidence
        if (isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or
                not math.isfinite(confidence) or confidence < self.minimum_confidence or
                confidence > 1):
            return "intent_not_confident"
        if not serializable:
            return "arguments_not_serializable"
        if not isinstance(attempt.requested_tool, str) or not attempt.requested_tool:
            return "capability_not_allowed"
        validator = self.tool_validators.get(attempt.requested_tool)
        if validator is None:
            return "capability_not_allowed"
        try:
            if validator(attempt.arguments) is not True:
                return "arguments_invalid"
        except Exception:
            return "arguments_invalid"
        return None

    def attempt(self, attempt: VoiceToolAttempt) -> dict[str, Any]:
        if not self.started:
            raise InterlockError("session_not_started")
        self._check()  # Recheck mutable external conditions before every attempt.
        turn_id = str(uuid.uuid4())
        parent = self._record(turn_id, "wake", None,
                              wake_valid=attempt.wake_valid is True, source=attempt.source)
        raw_hash = (hashlib.sha256(attempt.raw_model_output.encode("utf-8")).hexdigest()
                    if isinstance(attempt.raw_model_output, str) else None)
        parent = self._record(turn_id, "raw_model_output", parent, sha256=raw_hash)
        try:
            arg_bytes = json.dumps(attempt.arguments, sort_keys=True, ensure_ascii=False,
                                   separators=(",", ":"), allow_nan=False).encode("utf-8")
            args_hash = hashlib.sha256(arg_bytes).hexdigest()
            serializable = True
        except (TypeError, ValueError):
            args_hash, serializable = None, False
        parent = self._record(turn_id, "parsed_call", parent,
                              requested_tool=attempt.requested_tool, arguments_sha256=args_hash,
                              model_id=attempt.model_id,
                              shadow_recommendation=attempt.shadow_recommendation)
        reason = self._reject_reason(attempt, serializable)
        parent = self._record(turn_id, "policy_decision", parent,
                              decision="BLOCK" if reason else "ALLOW", reason=reason)
        if reason:
            result = {"status": "blocked_dry_run", "requested_tool": attempt.requested_tool,
                      "validated": False, "reason": reason, "real_world_effect": False}
            self._record(turn_id, "tool_result", parent, status=result["status"], reason=reason)
            self.blocked_actions += 1
            return result

        self._check()  # A stop/network/journal change after policy cannot reach the executor.
        parent = self._record(turn_id, "simulated_call", parent,
                              requested_tool=attempt.requested_tool)
        self._check()
        try:
            result = self.executor.execute(attempt.requested_tool)
            if not isinstance(result, dict):
                raise ValueError("mock returned a non-object result")
        except Exception as exc:
            self.emergency_stop.trip()
            raise InterlockError("mock_execution_failed") from exc
        parent = self._record(turn_id, "tool_result", parent, status=result.get("status"))
        valid = (result.get("status") == "SIMULATED" and result.get("validated") is True
                 and result.get("real_world_effect") is False)
        self._record(turn_id, "postcondition", parent, valid=valid)
        if not valid:
            self.emergency_stop.trip()
            raise InterlockError("mock_postcondition_failed")
        return result
