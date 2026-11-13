"""Predictive transcripts may prefetch; only reviewed final input may submit."""
from dataclasses import FrozenInstanceError, asdict
from hashlib import sha256
import pickle

import pytest

from core.voice_state import CommittedTranscript, TranscriptDraft, VoiceStateError, commit_transcript


def admitted(draft=None, **options):
    return commit_transcript(draft or TranscriptDraft("Salut", 0, final=True),
            user_confirmed=True, activation="explicit_submit", arguments_stable=True, **options)


def test_partial_transcript_exposes_only_readonly_prefetch_and_cannot_commit():
    draft = TranscriptDraft(" caută documentul ", revision=2)
    assert draft.prefetch_query == "caută documentul"
    assert not isinstance(draft.prefetch_query, CommittedTranscript)
    with pytest.raises(FrozenInstanceError):
        draft.text = "overwrite"
    with pytest.raises(VoiceStateError, match="voice_final_transcript_required"):
        admitted(draft)
    with pytest.raises(VoiceStateError, match="voice_final_transcript_required"):
        admitted(draft, reviewed_text="User reviewed text still cannot make partial ASR final")
    with pytest.raises(VoiceStateError, match="voice_final_transcript_required"):
        admitted(draft.prefetch_query)


def test_final_reviewed_input_has_bound_source_revision_and_new_commit_digest():
    draft = TranscriptDraft("caută documentul unu", 4, final=True)
    original = admitted(draft)
    corrected = admitted(draft, reviewed_text="caută documentul doi")
    assert original.validate(draft.text) is True
    assert corrected.validate("caută documentul doi") is True
    assert corrected.source_digest == original.source_digest == sha256(draft.text.encode()).hexdigest()
    assert corrected.commit_digest != original.commit_digest
    assert corrected.revision == 4 and corrected.origin == corrected.activation == "explicit_submit"
    with pytest.raises(VoiceStateError, match="voice_prompt_mismatch"):
        corrected.validate(draft.text)
    with pytest.raises(FrozenInstanceError):
        corrected.text = "changed"


@pytest.mark.parametrize("options,code", [
    ({"user_confirmed": False}, "voice_user_confirmation_required"),
    ({"user_confirmed": 1}, "voice_user_confirmation_required"),
    ({"user_confirmed": "true"}, "voice_user_confirmation_required"),
    ({"arguments_stable": False}, "voice_stable_arguments_required"),
    ({"arguments_stable": 1}, "voice_stable_arguments_required"),
    ({"activation": "partial_asr"}, "voice_activation_required"),
    ({"activation": None}, "voice_activation_required"),
])
def test_commit_requires_strict_confirmation_activation_and_stable_arguments(options, code):
    flags = {"user_confirmed": True, "activation": "explicit_submit", "arguments_stable": True, **options}
    with pytest.raises(VoiceStateError, match="^" + code + "$"):
        commit_transcript(TranscriptDraft("Salut", 1, final=True), **flags)


@pytest.mark.parametrize("fields", [
    {"text": ""}, {"text": " "}, {"text": None}, {"text": "x" * 4001}, {"text": "\ud800"},
    {"revision": -1}, {"revision": True}, {"revision": 1.5}, {"final": "true"},
])
def test_invalid_draft_text_boolean_or_revision_is_rejected(fields):
    with pytest.raises(VoiceStateError):
        TranscriptDraft(**{"text": "Salut", "revision": 0, "final": False, **fields})


@pytest.mark.parametrize("field,value", [
    ("text", "changed"), ("revision", 9), ("source_digest", "0" * 64), ("commit_digest", "0" * 64),
    ("final", False), ("user_confirmed", 1), ("arguments_stable", False), ("origin", "partial_asr"),
])
def test_tampered_factory_commit_cannot_validate(field, value):
    transcript = admitted()
    object.__setattr__(transcript, field, value)
    with pytest.raises(VoiceStateError):
        transcript.validate()


def test_fabricated_or_deserialized_commit_has_no_local_admission_seal():
    transcript = admitted()
    with pytest.raises(VoiceStateError, match="voice_commit_requires_confirmation"):
        CommittedTranscript(**asdict(transcript))
    fabricated = object.__new__(CommittedTranscript)
    for key, value in asdict(transcript).items():
        object.__setattr__(fabricated, key, value)
    with pytest.raises(VoiceStateError, match="voice_invalid_commit"):
        fabricated.validate()
    restored = pickle.loads(pickle.dumps(transcript))
    with pytest.raises(VoiceStateError, match="voice_invalid_commit"):
        restored.validate()


def test_verified_wake_still_requires_final_user_confirmation_and_stable_arguments():
    transcript = commit_transcript(TranscriptDraft("Salut", 3, final=True), user_confirmed=True,
                                  activation="verified_wake", arguments_stable=True)
    assert transcript.validate("Salut") and transcript.origin == "verified_wake"
    assert not hasattr(transcript, "execute") and not hasattr(transcript, "tool_call")


def test_malformed_frozen_draft_is_rechecked_at_commit_boundary():
    draft = TranscriptDraft("Salut", 1, final=True)
    object.__setattr__(draft, "revision", True)
    with pytest.raises(VoiceStateError, match="voice_invalid_revision"):
        admitted(draft)
