# Investigative Genomic Research Workspace

## For: Javed Khan (Lead Researcher)

This repository is set up as an AI-assisted workspace for exploratory genomic investigation.

Current intent:
- Load genomic datasets into `data/`.
- Use AI to explore those datasets from multiple scientific angles, including non-obvious patterns and hypotheses.
- Track interim progress and decisions in `output/`.
- Store finalized analysis outputs and conclusions in `results/`.

## Repository Structure

- `data/`: input genomic datasets (raw or prepared).
- `output/`: working files, logs, status updates, and intermediate findings.
- `results/`: finalized deliverables, validated summaries, and decision-ready outputs.
- `_planning/plan.md`: high-level investigation process and operating approach.

## Investigation Workflow

1. Intake and profile datasets from `data/`.
2. Build/update a concrete analysis plan (questions, methods, priorities).
3. Run iterative exploratory analysis across many perspectives.
4. Update `output/status.md` with timestamped progress and blockers.
5. Refine based on researcher feedback.
6. Promote validated outcomes to `results/`.

## What Is Needed From You

To make this scientifically useful and operationally efficient, please provide:

1. Research objectives:
- Primary biological/clinical questions to answer.
- Priority hypotheses to test.

2. Dataset context:
- Description of each dataset (cohort, assay type, source, preprocessing).
- Data dictionary/column definitions.
- Sample metadata and identifier conventions.

3. Scientific constraints:
- Required statistical thresholds and QC rules.
- Known confounders or batch effects to account for.
- Methods or analyses that are preferred or prohibited.

4. Success criteria:
- What constitutes a meaningful finding.
- Required evidence level before moving outputs to `results/`.

5. Reporting expectations:
- Preferred output format (tables, figures, narrative, ranked candidate genes/pathways).
- Audience (internal research, publication prep, clinical translation discussion).

6. Governance and compliance:
- Any privacy, consent, IRB, or data-sharing boundaries that must be respected.

## Immediate Next Step

Please place the first datasets in `data/` and provide the six input categories above.  
Once provided, the analysis cycle can start and `output/status.md` will be maintained with timestamped updates.

## Agent Orchestration (Parallel Execution)

A dependency-aware parallel orchestrator is now included at:
- `orchestration/agent_orchestrator.py`

The orchestrator now auto-builds its task graph directly from CSV files in `data/`.
No agent or pipeline JSON setup is required.

Run a dry run (plan validation only):

```powershell
python orchestration/agent_orchestrator.py --dry-run
```

Run the pipeline:

```powershell
python orchestration/agent_orchestrator.py
```

This one command:
- Reads context from `_planning/plan.md`
- Discovers all `data/*.csv` files
- Profiles and scans each dataset in parallel
- Validates merged findings
- Writes reports into `results/`

Execution artifacts:
- `output/status.md`: timestamped task lifecycle updates.
- `output/orchestration_logs/*.log`: per-task stdout/stderr and command details.
- `output/orchestration_summaries/orchestration_summary_*.json`: run summary (completed/failed/skipped tasks).
- `results/*.md` and `results/*.html`: team-facing report outputs only.

Quick-start instructions and dummy data test flow are in:
- `START.md`
