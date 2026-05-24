"""Dependency-aware agent orchestration with parallel task execution.

This runner executes a pipeline of agent tasks in parallel when dependencies
allow it, writes per-task logs, and maintains a status markdown for visibility.
"""

from __future__ import annotations

import argparse
import json
import os
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


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_agents(path: Path) -> dict[str, AgentDefinition]:
    raw = load_json(path)
    agents: dict[str, AgentDefinition] = {}
    for item in raw.get("agents", []):
        name = item["name"]
        agents[name] = AgentDefinition(
            name=name,
            description=item.get("description", ""),
            command_template=item["command_template"],
            cwd=item.get("cwd"),
            env=item.get("env", {}),
        )
    return agents


def load_pipeline(path: Path) -> PipelineSpec:
    raw = load_json(path)
    tasks = [
        TaskSpec(
            task_id=item["id"],
            agent=item["agent"],
            args=item.get("args", {}),
            depends_on=item.get("depends_on", []),
            retries=int(item.get("retries", 0)),
            timeout_sec=item.get("timeout_sec"),
        )
        for item in raw.get("tasks", [])
    ]
    max_workers = int(raw.get("max_workers", os.cpu_count() or 4))
    return PipelineSpec(
        name=raw.get("name", "unnamed_pipeline"),
        max_workers=max(1, max_workers),
        fail_fast=bool(raw.get("fail_fast", True)),
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


def append_status(status_path: Path, lines: list[str]) -> None:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with status_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


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
        description="Parallel, dependency-aware agent orchestrator."
    )
    parser.add_argument(
        "--agents",
        default="_planning/agents.example.json",
        help="Path to agent definition JSON.",
    )
    parser.add_argument(
        "--pipeline",
        default="_planning/pipeline.example.json",
        help="Path to pipeline definition JSON.",
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
    agents_path = repo_root / args.agents
    pipeline_path = repo_root / args.pipeline
    status_path = repo_root / args.status
    logs_dir = repo_root / args.logs_dir
    summary_dir = repo_root / args.summary_dir

    agents = load_agents(agents_path)
    pipeline = load_pipeline(pipeline_path)
    validate_pipeline(pipeline, agents)

    return orchestrate(
        agents=agents,
        pipeline=pipeline,
        repo_root=repo_root,
        status_path=status_path,
        logs_dir=logs_dir,
        summary_dir=summary_dir,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
