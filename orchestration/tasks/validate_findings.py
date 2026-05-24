"""Validation task that merges scan outputs into a prioritized summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and merge scan findings.")
    parser.add_argument("--dataset", required=True, help="Logical dataset label.")
    parser.add_argument("--input-a", required=True, help="First scan JSON path.")
    parser.add_argument("--input-b", required=True, help="Second scan JSON path.")
    parser.add_argument("--min-score", type=float, default=1.0, help="Score threshold.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    input_a = Path(args.input_a)
    input_b = Path(args.input_b)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scan_a = load_json(input_a)
    scan_b = load_json(input_b)

    merged = []
    for source, data in [("A", scan_a), ("B", scan_b)]:
        for cand in data.get("top_candidates", []):
            row = dict(cand)
            row["source_dataset"] = source
            merged.append(row)

    merged.sort(key=lambda x: abs(float(x.get("signal_score", 0.0))), reverse=True)
    accepted = [
        row for row in merged if abs(float(row.get("signal_score", 0.0))) >= args.min_score
    ]

    summary = {
        "dataset": args.dataset,
        "inputs": [str(input_a), str(input_b)],
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
