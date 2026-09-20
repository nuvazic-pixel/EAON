# EAON-Red source recovery

`attack.py` is the recovered 2026-06-13 source for the deterministic, sandboxed
"AI Agent Security – Multi-Step Tool Attacks" benchmark. It contains trace-aware
mutation templates, a Go-Explore archive, snapshot/restore search and replayable
candidate message chains.

This is a separate research artifact. It is not connected to EAON's production
tools. The original `aicomp_sdk` environment and benchmark fixtures are not in
this repository. Its import fallback exists for source inspection and is not
evidence that the real SDK contract or competition evaluation passes.

Recovery validation is limited to syntax and import inspection. No attack search
or external tool execution was run during consolidation. Use it only with the
intended authorized offline benchmark environment.
