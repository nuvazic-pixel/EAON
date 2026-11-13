"""Separate speculative ASR text from explicitly committed local input.

These objects are conversation-input state, never tool authorization. The
activation signal is supplied by the trusted UI/wake harness, not by ASR text.
A serialized record cannot recreate the process-local admission seal.
"""
from dataclasses import dataclass
from hashlib import sha256
import hmac
import json

MAX_TRANSCRIPT_CHARS = 4000
_ADMISSION_SEAL = object()
_ORIGINS = frozenset({"explicit_submit", "verified_wake"})


class VoiceStateError(ValueError):
    """Stable codes without transcript contents or other private data."""


def _text(value):
    if type(value) is not str or not 0 < len(value.strip()) <= MAX_TRANSCRIPT_CHARS:
        raise VoiceStateError("voice_invalid_transcript")
    normalized = value.strip()
    try:
        normalized.encode("utf-8")
    except UnicodeError:
        raise VoiceStateError("voice_invalid_transcript") from None
    return normalized


def _revision(value):
    if type(value) is not int or value < 0:
        raise VoiceStateError("voice_invalid_revision")
    return value


def _digest(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _commit_digest(*, text, revision, source_digest, origin, user_confirmed, arguments_stable, final):
    payload = {"schema": "eaon.committed-transcript.v1", "text": text, "revision": revision,
               "source_digest": source_digest, "origin": origin, "user_confirmed": user_confirmed,
               "arguments_stable": arguments_stable, "final": final}
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return _digest(body)


@dataclass(frozen=True)
class TranscriptDraft:
    text: str
    revision: int
    final: bool = False

    def __post_init__(self):
        object.__setattr__(self, "text", _text(self.text))
        _revision(self.revision)
        if type(self.final) is not bool:
            raise VoiceStateError("voice_invalid_final_flag")

    @property
    def prefetch_query(self):
        """Read-only query text; it carries no submission or execution capability."""
        return self.text


@dataclass(frozen=True, init=False)
class CommittedTranscript:
    text: str
    revision: int
    source_digest: str
    commit_digest: str
    origin: str
    user_confirmed: bool
    arguments_stable: bool
    final: bool

    def __init__(self, *args, **kwargs):
        raise VoiceStateError("voice_commit_requires_confirmation")

    @property
    def activation(self):
        return self.origin

    def validate(self, prompt=None):
        """Validate a factory-issued object and optional exact submitted-text binding.

        Hashes identify this input snapshot; the admission seal is a local
        harness boundary, not an identity signature or authorization for tools.
        """
        try:
            if getattr(self, "_admission_seal", None) is not _ADMISSION_SEAL:
                raise VoiceStateError("voice_invalid_commit")
            if _text(self.text) != self.text or _text(self._source_text) != self._source_text:
                raise VoiceStateError("voice_invalid_commit")
            _revision(self.revision)
            if (self.final is not True or self.user_confirmed is not True or self.arguments_stable is not True
                    or type(self.origin) is not str or self.origin not in _ORIGINS):
                raise VoiceStateError("voice_invalid_commit")
            if type(self.source_digest) is not str or not hmac.compare_digest(self.source_digest, _digest(self._source_text)):
                raise VoiceStateError("voice_invalid_commit")
            expected = _commit_digest(text=self.text, revision=self.revision, source_digest=self.source_digest,
                        origin=self.origin, user_confirmed=self.user_confirmed,
                        arguments_stable=self.arguments_stable, final=self.final)
            if type(self.commit_digest) is not str or not hmac.compare_digest(self.commit_digest, expected):
                raise VoiceStateError("voice_invalid_commit")
            if prompt is not None and (type(prompt) is not str or prompt != self.text):
                raise VoiceStateError("voice_prompt_mismatch")
        except (AttributeError, TypeError, UnicodeError):
            raise VoiceStateError("voice_invalid_commit") from None
        return True


def commit_transcript(draft, reviewed_text=None, *, user_confirmed, activation, arguments_stable):
    if type(draft) is not TranscriptDraft:
        raise VoiceStateError("voice_final_transcript_required")
    # Recheck frozen source fields so object.__setattr__/deserialization cannot
    # turn a malformed source into an admitted input.
    source_text = _text(draft.text)
    revision = _revision(draft.revision)
    if draft.final is not True:
        raise VoiceStateError("voice_final_transcript_required")
    if user_confirmed is not True:
        raise VoiceStateError("voice_user_confirmation_required")
    if type(activation) is not str or activation not in _ORIGINS:
        raise VoiceStateError("voice_activation_required")
    if arguments_stable is not True:
        raise VoiceStateError("voice_stable_arguments_required")
    text = source_text if reviewed_text is None else _text(reviewed_text)
    source_digest = _digest(source_text)
    fields = {"text": text, "revision": revision, "source_digest": source_digest,
              "origin": activation, "user_confirmed": True, "arguments_stable": True, "final": True}
    committed = object.__new__(CommittedTranscript)
    for key, value in fields.items():
        object.__setattr__(committed, key, value)
    object.__setattr__(committed, "commit_digest", _commit_digest(**fields))
    object.__setattr__(committed, "_source_text", source_text)
    object.__setattr__(committed, "_admission_seal", _ADMISSION_SEAL)
    committed.validate(text)
    return committed
