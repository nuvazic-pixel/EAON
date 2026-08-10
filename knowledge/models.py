from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RelationType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DEPENDS_ON = "depends_on"
    CAUSES = "causes"
    CORRELATES_WITH = "correlates_with"
    GENERALIZES = "generalizes"
    SPECIALIZES = "specializes"
    PRECEDES = "precedes"
    EXPLAINS = "explains"
    MEASURES = "measures"


class GapType(str, Enum):
    MISSING_BRIDGE = "missing_bridge"
    CONTRADICTION = "contradiction"
    UNSUPPORTED_ASSUMPTION = "unsupported_assumption"
    UNTESTED_PREDICTION = "untested_prediction"
    CROSS_DOMAIN_DISCONNECT = "cross_domain_disconnect"
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"
    SOURCE_COVERAGE = "source_coverage"


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    source_type: str
    uri: str = ""
    authors: tuple[str, ...] = ()
    published_year: Optional[int] = None
    accessed_at: Optional[str] = None
    domain: str = "general"
    language: str = "unknown"
    retracted: bool = False


@dataclass(frozen=True)
class Evidence:
    id: str
    source_id: str
    quote_or_summary: str
    method: str = "unknown"
    strength: float = 0.5
    direct: bool = True
    location: str = ""


@dataclass
class Claim:
    id: str
    text: str
    domain: str
    subject: str = ""
    predicate: str = ""
    object: str = ""
    confidence: float = 0.5
    evidence_ids: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    discovered_year: Optional[int] = None
    valid_from_year: Optional[int] = None
    valid_to_year: Optional[int] = None
    falsifiable: bool = False
    status: str = "candidate"


@dataclass(frozen=True)
class Relation:
    source_claim_id: str
    target_claim_id: str
    relation_type: RelationType
    confidence: float = 0.5
    evidence_ids: tuple[str, ...] = ()
    rationale: str = ""


@dataclass
class Gap:
    id: str
    gap_type: GapType
    title: str
    description: str
    claim_ids: list[str]
    domains: list[str]
    confidence: float
    impact: float = 0.5
    novelty: float = 0.5
    testability: float = 0.5
    rationale: list[str] = field(default_factory=list)
    proposed_tests: list[str] = field(default_factory=list)

    @property
    def priority_score(self) -> float:
        """Rank gaps without pretending confidence alone equals importance."""
        return round(
            0.35 * self.confidence
            + 0.25 * self.impact
            + 0.20 * self.novelty
            + 0.20 * self.testability,
            4,
        )
