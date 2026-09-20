from __future__ import annotations

from eaon.models import CouncilResponse, DebugReport, MemoryRecord, RouteResult


class Council:
    """Deterministic local council. LLM adapters can replace this later."""

    def respond(
        self,
        *,
        user_input: str,
        route: RouteResult,
        debug_report: DebugReport,
        memories: list[MemoryRecord],
    ) -> CouncilResponse:
        memory_hint = self._memory_hint(memories)
        architect = self._architect(user_input, route, memory_hint)
        skeptic = self._skeptic(debug_report)
        implementer = self._implementer(route)
        next_step = self._next_step(route, debug_report)
        judge = (
            f"Route '{route.label}' is usable. Keep the output small, save the "
            "decision trail, and do the next step before expanding the system."
        )
        return CouncilResponse(
            architect=architect,
            skeptic=skeptic,
            implementer=implementer,
            judge=judge,
            next_step=next_step,
        )

    def _memory_hint(self, memories: list[MemoryRecord]) -> str:
        if not memories:
            return "No relevant memory found yet."
        top = memories[0]
        return f"Relevant memory: [{top.kind}] {top.text[:180]}"

    def _architect(self, user_input: str, route: RouteResult, memory_hint: str) -> str:
        return (
            f"Interpret this as a '{route.label}' input. Build around the core loop: "
            f"classify, debug reality, retrieve memory, synthesize, and store. {memory_hint}"
        )

    def _skeptic(self, debug_report: DebugReport) -> str:
        assumptions = debug_report.by_kind("ASSUMPTION")
        risks = debug_report.by_kind("RISK")
        if assumptions or risks:
            parts = []
            if assumptions:
                parts.append(f"{len(assumptions)} assumption(s) need checking")
            if risks:
                parts.append(f"{len(risks)} risk item(s) need mitigation")
            return "; ".join(parts) + "."
        return "No explicit risk was detected, but keep one verification step."

    def _implementer(self, route: RouteResult) -> str:
        if route.label == "decision":
            return "Write options, pick criteria, decide, and log why."
        if route.label == "research":
            return "Verify source, extract claims, save evidence, then decide."
        if route.label == "risk":
            return "Name the risk, define the smallest test, and set a stop rule."
        if route.label == "action":
            return "Create the smallest runnable version and test it immediately."
        if route.label == "idea":
            return "Turn the idea into one module, one input, one output, one test."
        return "Capture the thought, tag it, and define the next concrete action."

    def _next_step(self, route: RouteResult, debug_report: DebugReport) -> str:
        tests = debug_report.by_kind("TEST")
        if tests:
            return tests[0].text
        if route.label == "idea":
            return "Write the idea as a one-screen module spec."
        if route.label == "action":
            return "Run the smallest possible command or prototype."
        return "Add one fact, one assumption, and one test."
