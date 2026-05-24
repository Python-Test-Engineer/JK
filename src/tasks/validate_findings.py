"""Validation task that merges scan outputs into a prioritized summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and merge scan findings.")
    parser.add_argument("--dataset", required=True, help="Logical dataset label.")
    parser.add_argument(
        "--inputs",
        nargs="+",
        default=None,
        help="One or more scan JSON paths.",
    )
    parser.add_argument(
        "--input-a",
        default=None,
        help="Backward-compatible first scan JSON path.",
    )
    parser.add_argument(
        "--input-b",
        default=None,
        help="Backward-compatible second scan JSON path.",
    )
    parser.add_argument("--min-score", type=float, default=1.0, help="Score threshold.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    raw_inputs: list[str] = []
    if args.inputs:
        raw_inputs.extend(args.inputs)
    if args.input_a:
        raw_inputs.append(args.input_a)
    if args.input_b:
        raw_inputs.append(args.input_b)
    if len(raw_inputs) < 1:
        raise SystemExit("No scan inputs provided. Use --inputs <path1> [path2 ...].")

    input_paths = [Path(path) for path in raw_inputs]
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    merged = []
    for idx, input_path in enumerate(input_paths, start=1):
        source = f"S{idx:02d}"
        data = load_json(input_path)
        for cand in data.get("top_candidates", []):
            row = dict(cand)
            row["source_dataset"] = source
            row["source_path"] = str(input_path)
            merged.append(row)

    merged.sort(key=lambda x: abs(float(x.get("signal_score", 0.0))), reverse=True)
    accepted = [
        row for row in merged if abs(float(row.get("signal_score", 0.0))) >= args.min_score
    ]

    summary = {
        "dataset": args.dataset,
        "inputs": [str(path) for path in input_paths],
        "threshold": args.min_score,
        "total_candidates_reviewed": len(merged),
        "accepted_candidates": accepted,
        "accepted_count": len(accepted),
    }
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
