"""Deterministic baseline claim extractor for EAON."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Iterable
from .openalex import OpenAlexWork

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_CLAIM_CUES = ("show","demonstrat","indicat","suggest","associated","correlat","increase","decrease","cause","result","predict","support","inhibit","promot")

@dataclass
class ExtractedClaim:
    claim_id: str
    text: str
    source_id: str
    source_title: str
    publication_year: int | None
    evidence_text: str
    topics: list[str] = field(default_factory=list)
    extractor: str = "heuristic-v0.1"
    confidence: float = 0.5

class ClaimExtractor:
    def extract(self, work: OpenAlexWork) -> list[ExtractedClaim]:
        if not work.abstract.strip():
            return []
        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(work.abstract.strip()) if len(s.strip()) >= 30]
        candidates = [s for s in sentences if any(cue in s.lower() for cue in _CLAIM_CUES)]
        if not candidates and sentences:
            candidates = [max(sentences, key=len)]
        stable_source = work.id.rsplit("/", 1)[-1] or "unknown"
        return [ExtractedClaim(
            claim_id=f"{stable_source}:claim:{i}",
            text=sentence,
            source_id=work.id,
            source_title=work.title,
            publication_year=work.publication_year,
            evidence_text=sentence,
            topics=list(work.topics),
            confidence=0.55 if len(candidates) > 1 else 0.50,
        ) for i, sentence in enumerate(candidates, start=1)]

    def extract_many(self, works: Iterable[OpenAlexWork]) -> list[ExtractedClaim]:
        claims: list[ExtractedClaim] = []
        for work in works:
            claims.extend(self.extract(work))
        return claims
