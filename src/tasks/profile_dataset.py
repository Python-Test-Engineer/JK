"""Dataset profiling task for genomic CSV inputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile a genomic dataset CSV.")
    parser.add_argument("--input", required=True, help="Input CSV path.")
    parser.add_argument("--dataset", required=True, help="Dataset name.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_path)
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    missing_by_col = {col: int(df[col].isna().sum()) for col in df.columns}
    summary = {
        "dataset": args.dataset,
        "input_path": str(input_path),
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": df.columns.tolist(),
        "numeric_columns": numeric_cols,
        "missing_values_per_column": missing_by_col,
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
