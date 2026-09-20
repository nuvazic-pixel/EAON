# Skill: repo_reader

## Purpose

Use this skill when the task requires understanding a repository, folder structure, dependencies, imports, file relationships, or README documentation.

## Load only

- repository tree
- README files
- package files
- dependency files
- directly relevant source files
- recent logs, if the user provides an error

## Do not load

- virtual environments
- generated files
- build folders
- node_modules
- large datasets
- all source files by default

## Output format

1. Files inspected
2. What the repository appears to do
3. Relevant modules
4. Missing or risky parts
5. Suggested next action
