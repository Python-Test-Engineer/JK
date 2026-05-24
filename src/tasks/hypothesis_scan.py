"""Exploratory scan task for simple candidate genomic signals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run exploratory signal scan.")
    parser.add_argument("--input", required=True, help="Input CSV path.")
    parser.add_argument("--dataset", required=True, help="Dataset name.")
    parser.add_argument("--mode", default="broad", help="Scan mode label.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    numeric = df.select_dtypes(include=["number"]).copy()
    if "sample_id" in numeric.columns:
        numeric = numeric.drop(columns=["sample_id"])

    candidate_scores = []
    for col in numeric.columns:
        series = numeric[col].dropna()
        if series.empty:
            continue
        score = float(series.mean() / (series.std(ddof=0) + 1e-9))
        candidate_scores.append(
            {
                "feature": col,
                "mean": float(series.mean()),
                "std": float(series.std(ddof=0)),
                "signal_score": score,
            }
        )

    candidate_scores.sort(key=lambda x: abs(x["signal_score"]), reverse=True)
    top_candidates = candidate_scores[:5]
    findings = {
        "dataset": args.dataset,
        "mode": args.mode,
        "input_path": str(input_path),
        "candidate_count": len(candidate_scores),
        "top_candidates": top_candidates,
    }
    output_path.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(json.dumps(findings, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
