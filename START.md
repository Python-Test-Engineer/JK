# START: Parallel Genomic Investigation Workflow

This file is the fast-start runbook for testing and then operating the orchestration workflow.

## 1. What Is Already In Place

- Parallel orchestrator: `src/agent_orchestrator.py`
- Task executables:
  - `src/tasks/profile_dataset.py`
  - `src/tasks/hypothesis_scan.py`
  - `src/tasks/validate_findings.py`
- Plan file: `_planning/plan.md`
- Dummy test datasets:
  - `data/dummy_dataset_a.csv`
  - `data/dummy_dataset_b.csv`

## 2. Environment Setup

Use your preferred Python environment, then install minimum dependencies:

```powershell
pip install pandas
```

## 3. Run a Dry Plan Check

This validates DAG dependencies and prints the planned commands without executing tasks:

```powershell
python src/agent_orchestrator.py --dry-run
```

## 4. Run End-to-End Test (Dummy Data)

```powershell
python src/agent_orchestrator.py
```

## 5. Where Outputs Appear

- Progress timeline: `output/status.md`
- Per-task logs: `output/orchestration_logs/*.log`
- Intermediate artifacts:
  - `output/intermediate/Dataset_A_profile.json`
  - `output/intermediate/Dataset_B_profile.json`
  - `output/intermediate/Dataset_A_scan.json`
  - `output/intermediate/Dataset_B_scan.json`
- Final validation:
  - `output/intermediate/joint_analysis_validated.json`
  - `output/orchestration_summaries/orchestration_summary_*.json`
- Team-facing reports in `results/`:
  - `results/joint_analysis_report.md`
  - `results/joint_analysis_report.html`

## 6. How To Switch From Dummy To Real Data

1. Place real CSVs in `data/`.
2. Re-run:

```powershell
python src/agent_orchestrator.py
```

Optional tuning:

```powershell
python src/agent_orchestrator.py --min-score 1.2 --max-workers 4
```

## 7. What You (Lead Researcher) Need To Provide Next

1. Priority research questions/hypotheses.
2. Required statistical/QC thresholds.
3. Dataset metadata and field definitions.
4. Criteria for promoting findings to `results/`.
