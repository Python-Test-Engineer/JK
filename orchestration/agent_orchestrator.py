"""Dependency-aware agent orchestration with automatic dataset discovery.

Drop CSV files into `data/` and run this module. The orchestrator builds a
default pipeline from discovered datasets and executes dependent tasks in
parallel while writing progress updates and task logs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, Future, wait
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    description: str
    command_template: str
    cwd: str | None = None
    env: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    agent: str
    args: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    retries: int = 0
    timeout_sec: int | None = None


@dataclass(frozen=True)
class PipelineSpec:
    name: str
    max_workers: int
    fail_fast: bool
    tasks: list[TaskSpec]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def append_status(status_path: Path, lines: list[str]) -> None:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with status_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip()).strip("_")
    if not slug:
        slug = "dataset"
    if slug[0].isdigit():
        slug = f"dataset_{slug}"
    return slug.lower()


def list_csv_files(data_dir: Path) -> list[Path]:
    return sorted(path for path in data_dir.glob("*.csv") if path.is_file())


def read_plan_excerpt(plan_path: Path, max_lines: int = 8) -> str:
    if not plan_path.exists():
        return "(plan file missing)"
    lines = plan_path.read_text(encoding="utf-8").splitlines()
    non_empty = [line.strip() for line in lines if line.strip()]
    return " | ".join(non_empty[:max_lines]) if non_empty else "(plan file is empty)"


def default_agents() -> dict[str, AgentDefinition]:
    return {
        "dataset_profile_agent": AgentDefinition(
            name="dataset_profile_agent",
            description="Profiles genomic datasets and emits shape/schema/QC hints.",
            command_template=(
                'python -m orchestration.tasks.profile_dataset --input "{input_path}" '
                '--dataset "{dataset_name}" --output "{output_path}"'
            ),
        ),
        "hypothesis_scan_agent": AgentDefinition(
            name="hypothesis_scan_agent",
            description="Runs exploratory scans and candidate signal extraction.",
            command_template=(
                'python -m orchestration.tasks.hypothesis_scan --input "{input_path}" '
                '--dataset "{dataset_name}" --mode "{mode}" --output "{output_path}"'
            ),
        ),
        "validation_agent": AgentDefinition(
            name="validation_agent",
            description="Validates candidate findings across all dataset scans.",
            command_template=(
                'python -m orchestration.tasks.validate_findings --dataset "{dataset_name}" '
                '--inputs {inputs_clause} --min-score {min_score} --output "{output_path}"'
            ),
        ),
        "team_report_agent": AgentDefinition(
            name="team_report_agent",
            description="Generates team-facing markdown and HTML reports in results.",
            command_template=(
                'python -m orchestration.tasks.report_team --validated-input "{validated_input}" '
                '--report-base "{report_base}" --results-dir "{results_dir}"'
            ),
        ),
    }


def build_default_pipeline(
    csv_files: list[Path],
    min_score: float,
    max_workers: int,
    fail_fast: bool,
    report_base: str,
) -> PipelineSpec:
    tasks: list[TaskSpec] = []
    scan_task_ids: list[str] = []
    scan_outputs: list[Path] = []
    seen_names: dict[str, int] = {}

    for index, csv_path in enumerate(csv_files, start=1):
        base = slugify(csv_path.stem)
        seen_names[base] = seen_names.get(base, 0) + 1
        suffix = seen_names[base]
        unique = f"{base}_{suffix}" if suffix > 1 else base
        dataset_name = f"Dataset_{index:02d}_{unique}"

        profile_task_id = f"profile_{unique}"
        scan_task_id = f"scan_{unique}"
        profile_output = Path("output/intermediate") / f"{dataset_name}_profile.json"
        scan_output = Path("output/intermediate") / f"{dataset_name}_scan.json"

        tasks.append(
            TaskSpec(
                task_id=profile_task_id,
                agent="dataset_profile_agent",
                args={
                    "input_path": str(csv_path.as_posix()),
                    "dataset_name": dataset_name,
                    "output_path": str(profile_output.as_posix()),
                },
                retries=1,
            )
        )
        tasks.append(
            TaskSpec(
                task_id=scan_task_id,
                agent="hypothesis_scan_agent",
                args={
                    "input_path": str(csv_path.as_posix()),
                    "dataset_name": dataset_name,
                    "mode": "broad",
                    "output_path": str(scan_output.as_posix()),
                },
                depends_on=[profile_task_id],
            )
        )
        scan_task_ids.append(scan_task_id)
        scan_outputs.append(scan_output)

    inputs_clause = " ".join(f'"{path.as_posix()}"' for path in scan_outputs)
    validated_output = Path("output/intermediate/joint_analysis_validated.json")
    tasks.append(
        TaskSpec(
            task_id="validate_joint_findings",
            agent="validation_agent",
            args={
                "dataset_name": "joint_analysis",
                "inputs_clause": inputs_clause,
                "min_score": min_score,
                "output_path": str(validated_output.as_posix()),
            },
            depends_on=scan_task_ids,
        )
    )
    tasks.append(
        TaskSpec(
            task_id="publish_team_report",
            agent="team_report_agent",
            args={
                "validated_input": str(validated_output.as_posix()),
                "report_base": report_base,
                "results_dir": "results",
            },
            depends_on=["validate_joint_findings"],
        )
    )

    return PipelineSpec(
        name="genomic_investigation_auto_pipeline",
        max_workers=max(1, max_workers),
        fail_fast=fail_fast,
        tasks=tasks,
    )


def validate_pipeline(pipeline: PipelineSpec, agents: dict[str, AgentDefinition]) -> None:
    task_ids = set()
    for task in pipeline.tasks:
        if task.task_id in task_ids:
            raise ValueError(f"Duplicate task id: {task.task_id}")
        task_ids.add(task.task_id)
        if task.agent not in agents:
            raise ValueError(f"Task {task.task_id} references unknown agent: {task.agent}")
    for task in pipeline.tasks:
        for dep in task.depends_on:
            if dep not in task_ids:
                raise ValueError(f"Task {task.task_id} depends on missing task: {dep}")
            if dep == task.task_id:
                raise ValueError(f"Task {task.task_id} cannot depend on itself.")


def render_command(agent: AgentDefinition, args: dict[str, Any]) -> str:
    try:
        return agent.command_template.format(**args)
    except KeyError as error:
        missing = str(error).strip("'")
        raise ValueError(
            f"Missing command argument '{missing}' for agent '{agent.name}'."
        ) from error


def run_task(
    task: TaskSpec,
    agent: AgentDefinition,
    repo_root: Path,
    logs_dir: Path,
    attempt: int,
) -> dict[str, Any]:
    command = render_command(agent, task.args)
    start = time.time()
    started_at = utc_now()
    task_cwd = repo_root / agent.cwd if agent.cwd else repo_root
    env = os.environ.copy()
    env.update(agent.env)
    process = subprocess.run(
        command,
        shell=True,
        cwd=str(task_cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=task.timeout_sec,
    )
    ended_at = utc_now()
    duration_sec = round(time.time() - start, 2)
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{task.task_id}.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] Attempt {attempt}\n")
        handle.write(f"Command: {command}\n")
        handle.write(f"CWD: {task_cwd}\n")
        handle.write("--- STDOUT ---\n")
        handle.write(process.stdout or "")
        handle.write("\n--- STDERR ---\n")
        handle.write(process.stderr or "")
        handle.write(f"\nExit code: {process.returncode}\n\n")
    return {
        "task_id": task.task_id,
        "command": command,
        "attempt": attempt,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_sec": duration_sec,
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "log_path": str(log_path),
    }


def orchestrate(
    agents: dict[str, AgentDefinition],
    pipeline: PipelineSpec,
    repo_root: Path,
    status_path: Path,
    logs_dir: Path,
    summary_dir: Path,
    dry_run: bool,
    plan_path: Path,
    plan_excerpt: str,
    data_files: list[Path],
) -> int:
    task_map = {task.task_id: task for task in pipeline.tasks}
    pending = set(task_map)
    completed: set[str] = set()
    failed: set[str] = set()
    skipped: set[str] = set()
    attempts = {task_id: 0 for task_id in task_map}
    running: dict[Future[dict[str, Any]], str] = {}
    results: list[dict[str, Any]] = []

    append_status(
        status_path,
        [
            f"## [{utc_now()}] Pipeline Start: {pipeline.name}",
            f"- Max workers: {pipeline.max_workers}",
            f"- Fail fast: {pipeline.fail_fast}",
            f"- Dry run: {dry_run}",
            f"- Plan file: `{plan_path.as_posix()}`",
            f"- Plan excerpt: {plan_excerpt}",
            f"- Input CSV files: {', '.join(path.name for path in data_files)}",
        ],
    )

    if dry_run:
        for task in pipeline.tasks:
            agent = agents[task.agent]
            command = render_command(agent, task.args)
            append_status(
                status_path,
                [
                    f"### [{utc_now()}] DRY RUN: {task.task_id}",
                    f"- Agent: {task.agent}",
                    f"- Depends on: {', '.join(task.depends_on) or '(none)'}",
                    f"- Command: `{command}`",
                ],
            )
        return 0

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=pipeline.max_workers) as executor:
        while pending or running:
            if failed and pipeline.fail_fast:
                for task_id in sorted(pending):
                    skipped.add(task_id)
                pending.clear()
                break

            ready = sorted(
                task_id
                for task_id in pending
                if all(dep in completed for dep in task_map[task_id].depends_on)
            )
            for task_id in ready:
                if len(running) >= pipeline.max_workers:
                    break
                task = task_map[task_id]
                pending.remove(task_id)
                attempts[task_id] += 1
                agent = agents[task.agent]
                append_status(
                    status_path,
                    [
                        f"### [{utc_now()}] STARTED: {task_id}",
                        f"- Agent: {task.agent}",
                        f"- Attempt: {attempts[task_id]}",
                        f"- Depends on: {', '.join(task.depends_on) or '(none)'}",
                    ],
                )
                future = executor.submit(
                    run_task,
                    task,
                    agent,
                    repo_root,
                    logs_dir,
                    attempts[task_id],
                )
                running[future] = task_id

            if not running:
                unresolved = sorted(pending)
                if unresolved:
                    append_status(
                        status_path,
                        [
                            f"### [{utc_now()}] BLOCKED",
                            f"- Unresolved tasks: {', '.join(unresolved)}",
                            "- Cause: dependencies not satisfied (likely due to earlier failures).",
                        ],
                    )
                    skipped.update(unresolved)
                break

            done, _ = wait(running.keys(), return_when=FIRST_COMPLETED)
            for future in done:
                task_id = running.pop(future)
                task = task_map[task_id]
                result = future.result()
                results.append(result)
                if result["returncode"] == 0:
                    completed.add(task_id)
                    append_status(
                        status_path,
                        [
                            f"### [{utc_now()}] COMPLETED: {task_id}",
                            f"- Duration (sec): {result['duration_sec']}",
                            f"- Log: `{result['log_path']}`",
                        ],
                    )
                    continue

                if attempts[task_id] <= task.retries:
                    pending.add(task_id)
                    append_status(
                        status_path,
                        [
                            f"### [{utc_now()}] RETRYING: {task_id}",
                            f"- Attempt: {attempts[task_id]} failed (exit {result['returncode']})",
                            f"- Max retries: {task.retries}",
                        ],
                    )
                else:
                    failed.add(task_id)
                    append_status(
                        status_path,
                        [
                            f"### [{utc_now()}] FAILED: {task_id}",
                            f"- Exit code: {result['returncode']}",
                            f"- Log: `{result['log_path']}`",
                        ],
                    )

    summary_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    summary_path = summary_dir / f"orchestration_summary_{timestamp}.json"
    summary = {
        "pipeline": pipeline.name,
        "generated_at": utc_now(),
        "max_workers": pipeline.max_workers,
        "fail_fast": pipeline.fail_fast,
        "plan_path": str(plan_path.as_posix()),
        "input_files": [str(path.as_posix()) for path in data_files],
        "completed": sorted(completed),
        "failed": sorted(failed),
        "skipped": sorted(skipped),
        "results": results,
    }
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    append_status(
        status_path,
        [
            f"## [{utc_now()}] Pipeline End: {pipeline.name}",
            f"- Completed: {len(completed)}",
            f"- Failed: {len(failed)}",
            f"- Skipped: {len(skipped)}",
            f"- Summary: `{summary_path}`",
        ],
    )
    return 0 if not failed else 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parallel genomic orchestrator with automatic CSV discovery."
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing input CSV datasets.",
    )
    parser.add_argument(
        "--plan",
        default="_planning/plan.md",
        help="Plan markdown file used to provide run context.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=1.0,
        help="Minimum absolute signal score used during validation.",
    )
    parser.add_argument(
        "--report-base",
        default="joint_analysis_report",
        help="Base filename for report outputs in results/.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=min(4, os.cpu_count() or 4),
        help="Maximum parallel workers.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop scheduling pending tasks after the first unrecoverable failure.",
    )
    parser.add_argument(
        "--status",
        default="output/status.md",
        help="Path to status markdown output.",
    )
    parser.add_argument(
        "--logs-dir",
        default="output/orchestration_logs",
        help="Directory for per-task logs.",
    )
    parser.add_argument(
        "--summary-dir",
        default="output/orchestration_summaries",
        help="Directory for summary JSON output.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the execution plan without running commands.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    repo_root = Path.cwd()
    data_dir = repo_root / args.data_dir
    plan_path = repo_root / args.plan
    status_path = repo_root / args.status
    logs_dir = repo_root / args.logs_dir
    summary_dir = repo_root / args.summary_dir

    csv_files = list_csv_files(data_dir)
    if not csv_files:
        append_status(
            status_path,
            [
                f"## [{utc_now()}] Pipeline Aborted: no CSV files found",
                f"- Data directory checked: `{data_dir.as_posix()}`",
                "- Add one or more `.csv` files and rerun the command.",
            ],
        )
        print(f"No CSV files found in {data_dir}. Add data files and rerun.")
        return 2

    agents = default_agents()
    pipeline = build_default_pipeline(
        csv_files=csv_files,
        min_score=args.min_score,
        max_workers=args.max_workers,
        fail_fast=args.fail_fast,
        report_base=args.report_base,
    )
    validate_pipeline(pipeline, agents)

    plan_excerpt = read_plan_excerpt(plan_path)
    return orchestrate(
        agents=agents,
        pipeline=pipeline,
        repo_root=repo_root,
        status_path=status_path,
        logs_dir=logs_dir,
        summary_dir=summary_dir,
        dry_run=args.dry_run,
        plan_path=plan_path,
        plan_excerpt=plan_excerpt,
        data_files=csv_files,
    )


if __name__ == "__main__":
    raise SystemExit(main())
