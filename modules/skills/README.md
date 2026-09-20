# EAON Skills v0.1

**EAON Skills** is a local-first dynamic context system for AI agents.

Instead of dumping an entire repository into a prompt, EAON loads only the skill, files, memory, and rules needed for the current task.

## Core idea

Do not maximize context.
Maximize relevant context.

## Structure

```text
eaon_skills_v01/
├── eaon/
│   ├── context_router.py
│   ├── skill_registry.py
│   └── types.py
├── skills/
│   ├── repo_reader/
│   ├── debugger/
│   ├── architect/
│   ├── digital_twin/
│   └── memory_summarizer/
├── memory/
│   ├── project_summary.md
│   ├── decisions.md
│   └── architecture_map.md
└── examples/
    └── run_router.py
```

## Skills included

| Skill | Purpose |
|---|---|
| repo_reader | Inspect repository structure and relevant files |
| debugger | Analyze errors, tracebacks, failing imports |
| architect | Propose architecture without modifying code |
| digital_twin | Handle GIS, IFC, FTTH, infrastructure twin concepts |
| memory_summarizer | Compress old project decisions into small context |

## Run demo

```bash
python examples/run_router.py
```

## Next step

Connect this router to your local LLM stack, for example:

- Ollama
- Open WebUI
- local CLI assistant
- EAON server
- FastAPI endpoint
