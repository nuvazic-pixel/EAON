from pathlib import Path

from eaon.types import Skill


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / 'skills'


def load_skill_registry() -> list[Skill]:
    """
    Loads available skills from the local skills directory.

    Each skill should contain:
    - skill.md
    - tool.py
    """

    skills = [
        Skill(
            name='repo_reader',
            path=SKILLS_DIR / 'repo_reader',
            description='Inspect repository structure, README files, dependencies and relevant source files.',
            triggers=[
                'repo',
                'repository',
                'files',
                'folder',
                'structure',
                'readme',
                'imports',
                'dependencies',
            ],
        ),
        Skill(
            name='debugger',
            path=SKILLS_DIR / 'debugger',
            description='Analyze tracebacks, runtime errors, import errors and failing code.',
            triggers=[
                'error',
                'traceback',
                'bug',
                'exception',
                'fix',
                'crash',
                'failed',
                'not found',
            ],
        ),
        Skill(
            name='architect',
            path=SKILLS_DIR / 'architect',
            description='Create architecture plans, module boundaries and implementation strategies.',
            triggers=[
                'architecture',
                'design',
                'plan',
                'module',
                'system',
                'roadmap',
                'refactor',
            ],
        ),
        Skill(
            name='digital_twin',
            path=SKILLS_DIR / 'digital_twin',
            description='Handle GIS, IFC, BIM, FTTH, infrastructure, telemetry and digital twin tasks.',
            triggers=[
                'digital twin',
                'gis',
                'ifc',
                'bim',
                'ftth',
                'qgis',
                'infrastructure',
                'telemetry',
                'map',
            ],
        ),
        Skill(
            name='memory_summarizer',
            path=SKILLS_DIR / 'memory_summarizer',
            description='Summarize project memory, decisions, logs and long histories into compact context.',
            triggers=[
                'memory',
                'summary',
                'summarize',
                'decisions',
                'history',
                'compress',
                'recap',
            ],
        ),
    ]

    return skills
