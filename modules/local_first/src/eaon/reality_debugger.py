from __future__ import annotations

import re

from .models import Claim, RealityCheck


NEGATIONS = {"not", "no", "never", "without", "nu", "nici", "fără"}


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in re.findall(r"\b[\w-]{3,}\b", text)}


class RealityDebugger:
    """Evidence gate. It flags gaps; it does not pretend to prove truth."""

    def inspect(self, goal: str, evidence: list[Claim]) -> RealityCheck:
        warnings: list[str] = []
        if not evidence:
            return RealityCheck("insufficient_evidence", 0.0, ["No matching local claims"])
        goal_terms = _tokens(goal)
        supporting, contradicting = [], []
        goal_negative = bool(goal_terms & NEGATIONS)
        for claim in evidence:
            claim_terms = _tokens(claim.text)
            overlap = len(goal_terms & claim_terms) / max(1, len(goal_terms))
            if overlap >= 0.15:
                claim_negative = bool(claim_terms & NEGATIONS)
                target = contradicting if claim_negative != goal_negative else supporting
                if claim.id is not None:
                    target.append(claim.id)
        if not supporting:
            warnings.append("Evidence is related but does not directly support the goal")
        if contradicting:
            warnings.append("Potentially contradictory local evidence exists")
        if len({claim.source_id for claim in evidence}) < 2:
            warnings.append("Single-source evidence; independent corroboration missing")
        score = sum(claim.confidence for claim in evidence[:5]) / min(5, len(evidence))
        if len({claim.source_id for claim in evidence}) < 2:
            score *= 0.75
        verdict = "contested" if contradicting else ("supported" if supporting else "uncertain")
        return RealityCheck(verdict, round(score, 3), warnings, supporting, contradicting)
