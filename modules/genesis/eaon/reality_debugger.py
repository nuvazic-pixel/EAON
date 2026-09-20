from __future__ import annotations

import re

from eaon.models import DebugItem, DebugReport


SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]?", re.UNICODE)


class RealityDebugger:
    """Separates a thought into facts, assumptions, risks, and tests."""

    MARKERS = {
        "FACT": (
            "am vazut",
            "este",
            "sunt",
            "a fost",
            "exista",
            "i saw",
            "it is",
            "there is",
        ),
        "ASSUMPTION": (
            "cred",
            "pare",
            "probabil",
            "poate",
            "presupun",
            "maybe",
            "probably",
            "i think",
        ),
        "RISK": (
            "risc",
            "problema",
            "blocker",
            "pericol",
            "nu stiu",
            "worried",
            "risk",
            "fail",
        ),
        "TEST": (
            "verific",
            "test",
            "masor",
            "intreb",
            "cauta",
            "verify",
            "check",
            "measure",
        ),
    }

    def analyze(self, text: str) -> DebugReport:
        sentences = [match.group(0).strip() for match in SENTENCE_RE.finditer(text)]
        sentences = [sentence for sentence in sentences if sentence]
        items: list[DebugItem] = []

        for sentence in sentences or [text.strip()]:
            normalized = sentence.lower()
            matched_any = False
            for kind, markers in self.MARKERS.items():
                hits = [marker for marker in markers if marker in normalized]
                if hits:
                    confidence = min(0.95, 0.55 + 0.1 * len(hits))
                    items.append(DebugItem(kind=kind, text=sentence, confidence=confidence))
                    matched_any = True

            if not matched_any:
                items.append(DebugItem(kind="OBSERVATION", text=sentence, confidence=0.4))

        if not any(item.kind == "TEST" for item in items):
            items.append(
                DebugItem(
                    kind="TEST",
                    text="Define one small verification step before acting.",
                    confidence=0.5,
                )
            )

        return DebugReport(items=items)
