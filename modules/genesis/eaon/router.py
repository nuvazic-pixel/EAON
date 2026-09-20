from __future__ import annotations

from dataclasses import dataclass

from eaon.models import RouteResult


@dataclass(frozen=True)
class RouteRule:
    label: str
    keywords: tuple[str, ...]


class Router:
    RULES = (
        RouteRule("decision", ("decid", "aleg", "choice", "choose", "hotar", "optiune")),
        RouteRule("risk", ("risk", "risc", "problem", "blocker", "pericol", "gresit", "fail")),
        RouteRule("research", ("cauta", "verifica", "research", "source", "stire", "real", "fake")),
        RouteRule("action", ("fa", "build", "construi", "implementeaza", "ruleaza", "trimite")),
        RouteRule("idea", ("idee", "concept", "vision", "arhitectura", "orchestr", "eaon")),
        RouteRule("question", ("?", "cum", "de ce", "what", "why", "how")),
        RouteRule("reflection", ("simt", "cred", "ma gandesc", "vreau", "imi place")),
    )

    def classify(self, text: str) -> RouteResult:
        normalized = text.lower()
        scores: dict[str, int] = {}
        reasons: dict[str, list[str]] = {}

        for rule in self.RULES:
            for keyword in rule.keywords:
                if keyword in normalized:
                    scores[rule.label] = scores.get(rule.label, 0) + 1
                    reasons.setdefault(rule.label, []).append(keyword)

        if not scores:
            return RouteResult("reflection", 0.35, ["default: no strong route markers"])

        label, raw_score = max(scores.items(), key=lambda item: item[1])
        score = min(0.95, 0.45 + raw_score * 0.18)
        return RouteResult(label, score, [f"matched: {', '.join(reasons[label])}"])
