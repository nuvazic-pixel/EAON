# Architecture Map

## EAON Core

Responsible for:
- receiving task
- selecting skill
- loading skill context
- calling local model or tool
- returning structured answer

## Skills

Skills contain:
- skill.md for instructions
- tool.py for local operations

## Memory

Memory contains compressed project state and decisions.
