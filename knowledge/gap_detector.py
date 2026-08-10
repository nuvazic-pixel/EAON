from __future__ import annotations

import hashlib
from collections import defaultdict

from .models import Claim, Evidence, Gap, GapType, Relation, RelationType


class GapDetector:
    """Deterministic first-pass detector for structural knowledge gaps.

    This intentionally starts rule-based. LLM agents can propose relations later,
    but every surfaced gap should remain inspectable and reproducible.
    """

    def __init__(
        self,
        claims: list[Claim],
        relations: list[Relation],
        evidence: list[Evidence] | None = None,
    ) -> None:
        self.claims = {c.id: c for c in claims}
        self.relations = relations
        self.evidence = {e.id: e for e in (evidence or [])}
        self.outgoing: dict[str, list[Relation]] = defaultdict(list)
        self.incoming: dict[str, list[Relation]] = defaultdict(list)
        for relation in relations:
            self.outgoing[relation.source_claim_id].append(relation)
            self.incoming[relation.target_claim_id].append(relation)

    def detect(self) -> list[Gap]:
        gaps: list[Gap] = []
        gaps.extend(self._detect_explicit_contradictions())
        gaps.extend(self._detect_unsupported_assumptions())
        gaps.extend(self._detect_missing_bridges())
        gaps.extend(self._detect_cross_domain_disconnects())
        gaps.extend(self._detect_temporal_inconsistencies())
        return sorted(gaps, key=lambda gap: gap.priority_score, reverse=True)

    def _detect_explicit_contradictions(self) -> list[Gap]:
        gaps: list[Gap] = []
        for rel in self.relations:
            if rel.relation_type != RelationType.CONTRADICTS:
                continue
            a = self.claims.get(rel.source_claim_id)
            b = self.claims.get(rel.target_claim_id)
            if not a or not b:
                continue
            gaps.append(
                self._gap(
                    GapType.CONTRADICTION,
                    f"Contradiction: {a.id} ↔ {b.id}",
                    f"Two claims are explicitly marked as contradictory: '{a.text}' versus '{b.text}'.",
                    [a, b],
                    confidence=max(0.5, rel.confidence),
                    impact=0.75,
                    novelty=0.35,
                    testability=0.7,
                    rationale=[rel.rationale or "Explicit contradiction relation"],
                )
            )
        return gaps

    def _detect_unsupported_assumptions(self) -> list[Gap]:
        gaps: list[Gap] = []
        for claim in self.claims.values():
            if not claim.assumptions:
                continue
            if claim.evidence_ids:
                continue
            gaps.append(
                self._gap(
                    GapType.UNSUPPORTED_ASSUMPTION,
                    f"Unsupported assumptions behind {claim.id}",
                    f"Claim has stated assumptions but no attached evidence: '{claim.text}'.",
                    [claim],
                    confidence=0.85,
                    impact=0.65,
                    novelty=0.25,
                    testability=0.8 if claim.falsifiable else 0.45,
                    rationale=[f"Assumption: {a}" for a in claim.assumptions],
                )
            )
        return gaps

    def _detect_missing_bridges(self) -> list[Gap]:
        """Find A→B and B→C where A→C has no represented relation.

        This does not assert A→C is true. It only marks it as a candidate bridge
        worth testing or explaining.
        """
        gaps: list[Gap] = []
        existing_pairs = {
            (r.source_claim_id, r.target_claim_id) for r in self.relations
        }
        bridge_types = {
            RelationType.DEPENDS_ON,
            RelationType.CAUSES,
            RelationType.EXPLAINS,
            RelationType.SUPPORTS,
        }

        for first in self.relations:
            if first.relation_type not in bridge_types:
                continue
            for second in self.outgoing.get(first.target_claim_id, []):
                if second.relation_type not in bridge_types:
                    continue
                a_id = first.source_claim_id
                b_id = first.target_claim_id
                c_id = second.target_claim_id
                if a_id == c_id or (a_id, c_id) in existing_pairs:
                    continue
                a, b, c = self.claims.get(a_id), self.claims.get(b_id), self.claims.get(c_id)
                if not a or not b or not c:
                    continue
                conf = min(first.confidence, second.confidence) * 0.75
                gaps.append(
                    self._gap(
                        GapType.MISSING_BRIDGE,
                        f"Candidate bridge: {a.id} → {c.id}",
                        (
                            f"Knowledge graph contains {a.id} → {b.id} and {b.id} → {c.id}, "
                            f"but no represented relation between {a.id} and {c.id}."
                        ),
                        [a, b, c],
                        confidence=conf,
                        impact=0.7,
                        novelty=0.7,
                        testability=0.65,
                        rationale=[
                            f"{a.id} --{first.relation_type.value}→ {b.id}",
                            f"{b.id} --{second.relation_type.value}→ {c.id}",
                            "No direct represented relation closes the path.",
                        ],
                    )
                )
        return gaps

    def _detect_cross_domain_disconnects(self) -> list[Gap]:
        gaps: list[Gap] = []
        for rel in self.relations:
            a = self.claims.get(rel.source_claim_id)
            b = self.claims.get(rel.target_claim_id)
            if not a or not b or a.domain == b.domain:
                continue
            if rel.confidence >= 0.8 and not rel.evidence_ids:
                gaps.append(
                    self._gap(
                        GapType.CROSS_DOMAIN_DISCONNECT,
                        f"Cross-domain bridge lacks evidence: {a.domain} ↔ {b.domain}",
                        (
                            f"A high-confidence relation connects {a.domain} and {b.domain}, "
                            "but the relation has no direct evidence attached."
                        ),
                        [a, b],
                        confidence=0.8,
                        impact=0.8,
                        novelty=0.75,
                        testability=0.7,
                        rationale=[f"Relation type: {rel.relation_type.value}"],
                    )
                )
        return gaps

    def _detect_temporal_inconsistencies(self) -> list[Gap]:
        gaps: list[Gap] = []
        for claim in self.claims.values():
            if (
                claim.valid_from_year is not None
                and claim.valid_to_year is not None
                and claim.valid_from_year > claim.valid_to_year
            ):
                gaps.append(
                    self._gap(
                        GapType.TEMPORAL_INCONSISTENCY,
                        f"Invalid temporal range in {claim.id}",
                        f"Claim '{claim.text}' begins after its declared end date.",
                        [claim],
                        confidence=1.0,
                        impact=0.4,
                        novelty=0.1,
                        testability=1.0,
                        rationale=[
                            f"valid_from_year={claim.valid_from_year}",
                            f"valid_to_year={claim.valid_to_year}",
                        ],
                    )
                )
        return gaps

    def _gap(
        self,
        gap_type: GapType,
        title: str,
        description: str,
        claims: list[Claim],
        confidence: float,
        impact: float,
        novelty: float,
        testability: float,
        rationale: list[str],
    ) -> Gap:
        key = "|".join([gap_type.value] + sorted(c.id for c in claims))
        gap_id = "gap_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
        return Gap(
            id=gap_id,
            gap_type=gap_type,
            title=title,
            description=description,
            claim_ids=[c.id for c in claims],
            domains=sorted({c.domain for c in claims}),
            confidence=round(max(0.0, min(1.0, confidence)), 4),
            impact=impact,
            novelty=novelty,
            testability=testability,
            rationale=rationale,
        )
