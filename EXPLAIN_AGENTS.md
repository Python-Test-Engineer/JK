# EXPLAIN_AGENTS

This project now includes a Codex-ready agent scaffolding layout.

## Created Folders

- `agents/`: Definitions for broad responsibilities (for example: planner, analyst, reporter).
- `subagents/`: Task-specific helpers spawned for focused investigations.
- `skills/`: Reusable instructions or SOP-style task guides.
- `commands/`: Repeatable command recipes to keep runs reproducible.

## Workflow

```text
Goal (_goal/goal.md)
  -> Plan (_planning/plan.md)
    -> Primary agent(s) in agents/
      -> Optional helper subagents in subagents/
        -> Reusable guidance from skills/
          -> Execute reproducible commands from commands/
            -> Progress logs in output/status.md
              -> Final reports in results/
```

## How To Use

1. Define or update objective in `_goal/goal.md`.
2. Confirm plan in `_planning/plan.md`.
3. Add or update agent role docs in `agents/`.
4. Add focused helpers in `subagents/` only when parallelization helps.
5. Store reusable methods in `skills/`.
6. Keep run commands in `commands/` so future sessions can reproduce output.
