# Audit of EAON Paper Integration v2.1

## Material issues found

- `ToolRegistry` returned hard-coded mock strings, so orchestration never performed real work.
- The no-LLM fallback created generic claims and fake author/year metadata not grounded in a source.
- Remote URLs were fetched without a local-first boundary, allowlist, size limit, or content validation.
- Planning depended on an obsolete hard-coded cloud model and silently degraded on errors.
- `save_learning_record()` was called but not implemented.
- Dependencies between plan steps were declared but never enforced.
- Retry fields existed but no retry loop used them.
- The summarizer received the literal string `"search results"`, not prior-step output.
- The benchmark always ran both modes and counted baseline success even when asked for one mode.
- Success meant “a mock tool returned,” not “the answer was correct or evidence-grounded.”
- Insight usage was not tracked, so ablation reports could not measure insight impact.
- JSON file writes were non-atomic and session filenames were insufficiently constrained.

## Decision

The prototype was rebuilt around a smaller truthful core. The new version stores exact
evidence, exposes its route, fails closed when evidence is absent, keeps all persistent
state local, and labels Reality Debugger scores as coverage rather than truth.

## Explicitly deferred

- semantic embeddings and vector search;
- OCR for scanned papers;
- claim/entity resolution across sources;
- temporal knowledge graph and cognitive evolution;
- real hypothesis ablation with historical holdouts;
- browser UI, Whisper, and event bus.

These belong after the local evidence contract is stable and testable.
