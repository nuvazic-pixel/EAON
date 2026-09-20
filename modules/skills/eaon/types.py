from dataclasses import dataclass
from pathlib import Path


@dataclass
class Skill:
    name: str
    path: Path
    description: str
    triggers: list[str]


@dataclass
class RouteDecision:
    task: str
    selected_skill: str
    reason: str
    context_budget: int
    files_to_load: list[str]
