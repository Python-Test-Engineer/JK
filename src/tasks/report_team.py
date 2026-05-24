"""Create team-facing markdown and HTML reports from validated findings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate team-ready reports.")
    parser.add_argument("--validated-input", required=True, help="Validated findings JSON path.")
    parser.add_argument("--report-base", required=True, help="Report filename base.")
    parser.add_argument("--results-dir", default="results", help="Directory for report outputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validated_path = Path(args.validated_input)
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(validated_path.read_text(encoding="utf-8"))
    accepted = data.get("accepted_candidates", [])
    report_base = args.report_base
    md_path = results_dir / f"{report_base}.md"
    html_path = results_dir / f"{report_base}.html"

    md_lines = [
        f"# Team Report: {data.get('dataset', 'Unknown Dataset')}",
        "",
        "## Summary",
        f"- Threshold: `{data.get('threshold')}`",
        f"- Candidates reviewed: `{data.get('total_candidates_reviewed')}`",
        f"- Candidates accepted: `{data.get('accepted_count')}`",
        "",
        "## Accepted Candidates",
    ]
    if accepted:
        for item in accepted:
            md_lines.append(
                f"- `{item.get('feature')}` | score={item.get('signal_score'):.3f} | "
                f"source={item.get('source_dataset')}"
            )
    else:
        md_lines.append("- No candidates met the threshold.")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    html_rows = ""
    for item in accepted:
        html_rows += (
            "<tr>"
            f"<td>{item.get('feature')}</td>"
            f"<td>{item.get('signal_score'):.3f}</td>"
            f"<td>{item.get('source_dataset')}</td>"
            "</tr>"
        )
    if not html_rows:
        html_rows = "<tr><td colspan='3'>No candidates met the threshold.</td></tr>"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Team Report - {data.get('dataset', 'Unknown Dataset')}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
    h1 {{ margin-bottom: 8px; }}
    .meta {{ margin-bottom: 16px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background: #f0f0f0; }}
  </style>
</head>
<body>
  <h1>Team Report: {data.get('dataset', 'Unknown Dataset')}</h1>
  <div class="meta">
    <div><strong>Threshold:</strong> {data.get('threshold')}</div>
    <div><strong>Candidates reviewed:</strong> {data.get('total_candidates_reviewed')}</div>
    <div><strong>Candidates accepted:</strong> {data.get('accepted_count')}</div>
  </div>
  <h2>Accepted Candidates</h2>
  <table>
    <thead><tr><th>Feature</th><th>Signal Score</th><th>Source Dataset</th></tr></thead>
    <tbody>{html_rows}</tbody>
  </table>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")
    print(f"Wrote report files: {md_path} and {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
