# JK Research Workspace

This repository is set up for iterative dataset research with Codex-driven planning, execution, and reporting.

## Project Structure

- `src/`: Python source code and reusable analysis logic.
- `data/`: Input datasets and dataset metadata (`datasets_info.md`).
- `output/`: Working artifacts and progress logs generated during runs.
- `results/`: Final analysis reports and summaries.
- `_planning/`: Active plan files and planning notes.
- `_goal/`: Goal tracking and execution intent.
- `agents/`: Top-level agent role definitions.
- `subagents/`: Focused helper agents for parallel work.
- `skills/`: Reusable skill playbooks and task-specific instructions.
- `commands/`: Reproducible command snippets and runbooks.

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Authenticate Codex/OpenAI if needed:
   - See `codex_login.md`.
4. Confirm the active objective:
   - Review `_goal/goal.md`.
5. Confirm or update execution plan:
   - Review `_planning/plan.md`.
6. Run analysis scripts from `src/` and write:
   - Intermediate work to `output/`
   - Final reports to `results/` (`.md` and `.html` when applicable)

## Working Conventions

- Keep changes scoped and reviewable.
- Do not delete user data in `data/`, `output/`, or `results/` unless explicitly requested.
- Keep logs human-readable in `output/status.md`.
- Track session memory in `MEMORY.md`.

## Core Docs

- Agent instructions: `AGENTS.md`
- Startup checklist: `START.md`
- Agent system summary: `EXPLAIN_AGENTS.md`
- Session memory: `MEMORY.md`
