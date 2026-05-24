# Genomic Investigation Status

## Current Status
- State: Complete and healthy
- Latest pipeline: `genomic_investigation_auto_pipeline`
- Last completed run: `2026-05-24 10:53:46 UTC`
- Tasks completed: `6`
- Tasks failed: `0`
- Tasks skipped: `0`

## What Just Ran
- Inputs processed:
  - `data/dummy_dataset_a.csv`
  - `data/dummy_dataset_b.csv`
- Pipeline steps finished successfully:
  - Profile Dataset A
  - Profile Dataset B
  - Broad scan on Dataset A
  - Broad scan on Dataset B
  - Joint validation across both scans
  - Team report publishing

## Key Outputs Available
- Intermediate profiles/scans:
  - `output/intermediate/Dataset_01_dummy_dataset_a_profile.json`
  - `output/intermediate/Dataset_01_dummy_dataset_a_scan.json`
  - `output/intermediate/Dataset_02_dummy_dataset_b_profile.json`
  - `output/intermediate/Dataset_02_dummy_dataset_b_scan.json`
  - `output/intermediate/joint_analysis_validated.json`
- Final reports:
  - `results/joint_analysis_report.md`
  - `results/joint_analysis_report.html`
- Run summary:
  - `output/orchestration_summaries/orchestration_summary_20260524_105346.json`
- Per-task logs:
  - `output/orchestration_logs/`

## Highlight From Current Findings
- `10` candidates passed validation (`min-score = 1.0`).
- Highest-scoring repeated signal across datasets: `age`.
- Additional strong signals include genes/features such as `KRAS`, `BRCA1`, `EGFR`, `PTEN`, `MYC`, `BRAF`, and `TP53`.

## If You Want To Continue
- Open `results/joint_analysis_report.md` for a quick narrative summary.
- Open `results/joint_analysis_report.html` for a shareable browser view.
- Re-run the pipeline when new datasets are added to `data/`.
