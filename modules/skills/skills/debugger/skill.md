# Skill: debugger

## Purpose

Use this skill when the user provides an error, traceback, failing command, broken import, crashing server, or unexpected output.

## Required context

- exact error message
- command that produced the error
- relevant file
- relevant import section
- environment details, if available

## Do not do

- do not rewrite the whole project
- do not guess hidden files
- do not load unrelated modules
- do not change architecture before identifying the root cause

## Output format

1. Root cause
2. Minimal fix
3. Corrected code or command
4. Validation command
5. Risk / side effects
