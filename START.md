# START

Use this checklist at the start of each new Codex session.

## 1) Environment

1. Activate the project virtual environment.
2. Install or sync dependencies from `requirements.txt`.
3. If required, authenticate using `codex_login.md`.

## 2) Context

1. Read `AGENTS.md` for repository rules.
2. Read `_goal/goal.md` to confirm the current objective.
3. Read `_planning/plan.md` to confirm the approved plan.
4. Read `MEMORY.md` for what has already been done.

## 3) Execution

1. Keep intermediate outputs in `output/`.
2. Keep final reports in `results/` (`.md` and `.html`).
3. Update `output/status.md` with plain-English progress and timestamps.

## 4) Agent Assets

Use these folders when needed:

- `agents/` for primary agent definitions.
- `subagents/` for narrow helper agents.
- `skills/` for reusable workflows/instructions.
- `commands/` for reproducible command snippets.
