# AGENTS

## Purpose
This file defines how coding agents should work in this repository.

## Repository Layout
- `src/`: application/source code.
- `data/`: input datasets.
- `output/`: generated artifacts from runs.
- `results/`: analysis outputs and summaries.
- `_planning/`: planning notes and execution plans.
- `_goal/`: goal tracking artifacts.
- `requirements.txt`: Python dependencies.

## Working Rules
- Keep changes scoped to the user request.
- Prefer small, reviewable commits.
- Do not delete user data in `data/`, `output/`, or `results/` unless explicitly asked.
- Preserve existing file conventions and structure.
- If behavior changes, update related docs in the same change.
- **NEVER** delete files outside of this project.

## Python Environment
- Create/activate a virtual environment before running Python tasks.
- Install dependencies from `requirements.txt`.
- Prefer reproducible commands and pin new dependencies when added.

## Code Standards
- Favor clear, maintainable code over clever implementations.
- Add type hints for new Python code where practical.
- Write focused functions and avoid unnecessary abstraction.
- Keep comments concise and only where logic is non-obvious.

## Validation
- Run the smallest relevant checks first, then broader checks.
- For Python changes, run targeted tests before full-suite tests.
- If tests are unavailable, validate with a reproducible command and report it.

## Data and Outputs
- Treat `data/` as source inputs.
- Write generated files to `output/` or `results/`, not `src/`.
- Avoid committing large generated artifacts unless requested.

## Documentation
- When adding new scripts or modules, include a short usage note.
- Record important assumptions directly in PR/commit notes or `_planning/` docs.

## If Blocked
- Report the exact blocker and the command/file involved.
- Include one concrete next action the user can approve.
