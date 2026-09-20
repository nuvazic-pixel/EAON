from pathlib import Path

from eaon.skill_registry import load_skill_registry
from eaon.types import RouteDecision


ROOT = Path(__file__).resolve().parents[1]


def score_skill(task: str, triggers: list[str]) -> int:
    task_lower = task.lower()
    return sum(1 for trigger in triggers if trigger in task_lower)


def route_task(task: str) -> RouteDecision:
    """
    Selects the best skill for a user task.

    This is intentionally simple for v0.1:
    - keyword scoring
    - one selected skill
    - conservative context budget
    """

    skills = load_skill_registry()
    scored = [(score_skill(task, skill.triggers), skill) for skill in skills]
    scored.sort(key=lambda item: item[0], reverse=True)

    best_score, best_skill = scored[0]

    if best_score == 0:
        best_skill = next(skill for skill in skills if skill.name == 'architect')
        reason = 'No direct trigger matched. Defaulting to architect for high-level planning.'
    else:
        reason = f'Matched {best_score} trigger(s) for skill: {best_skill.name}.'

    context_budget = estimate_context_budget(best_skill.name)

    return RouteDecision(
        task=task,
        selected_skill=best_skill.name,
        reason=reason,
        context_budget=context_budget,
        files_to_load=[
            str(best_skill.path / 'skill.md'),
            str(best_skill.path / 'tool.py'),
        ],
    )


def estimate_context_budget(skill_name: str) -> int:
    budgets = {
        'repo_reader': 8000,
        'debugger': 6000,
        'architect': 5000,
        'digital_twin': 7000,
        'memory_summarizer': 4000,
    }
    return budgets.get(skill_name, 5000)


def load_skill_context(decision: RouteDecision) -> str:
    """
    Loads only the selected skill context.

    This prevents context rot by avoiding full-repo prompt dumping.
    """

    chunks = []

    for file_path in decision.files_to_load:
        path = Path(file_path)
        if path.exists():
            chunks.append(f'\n--- FILE: {path} ---\n')
            chunks.append(path.read_text(encoding='utf-8'))

    return '\n'.join(chunks)
