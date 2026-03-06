#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PACKAGE_VERSION = "0.1.0"
RELEASE_DIR_NAME = f"v{PACKAGE_VERSION}"
REFERENCE_FUNCTIONS = ("sphere", "rosenbrock")
REFERENCE_DIMENSIONS = (10,)
REFERENCE_NOISES = (0.0, 0.1)
# pycma treats seed=0 as time-based randomness; use strictly positive, non-zero
# seeds to preserve deterministic replay across script invocations.
REFERENCE_SEEDS = (101, 102)
REFERENCE_METHODS = ("vanilla", "proxy")
REFERENCE_INITIAL_SIGMA = 0.5
REFERENCE_POPSIZE = 10
REFERENCE_PLANNED_GENERATIONS = 12


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(repo_root: Path, *args: str) -> str:
    proc = _run(["git", *args], repo_root)
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.strip() or "unknown"


def _parse_pytest_summary(raw_output: str) -> tuple[int, int, str, str]:
    tests_passed = 0
    tests_skipped = 0
    coverage_total = "unknown"
    coverage_required = "unknown"

    passed_match = re.search(r"(\d+)\s+passed(?:,\s+(\d+)\s+skipped)?", raw_output)
    if passed_match:
        tests_passed = int(passed_match.group(1))
        tests_skipped = int(passed_match.group(2) or 0)

    total_cov_match = re.search(r"Total coverage:\s*([0-9.]+)%", raw_output)
    if total_cov_match:
        coverage_total = total_cov_match.group(1)

    required_cov_match = re.search(r"Required test coverage of\s*([0-9.]+)%", raw_output)
    if required_cov_match:
        coverage_required = required_cov_match.group(1)

    return tests_passed, tests_skipped, coverage_total, coverage_required


def _build_reference_rows() -> list[dict[str, Any]]:
    from cmaes_proxy_sigma_controller.reference_runner import run_reference
    from cmaes_proxy_sigma_controller.types import ControllerConfig, TraceMode

    rows: list[dict[str, Any]] = []
    controller_config = ControllerConfig()

    for function_name in REFERENCE_FUNCTIONS:
        for dimension in REFERENCE_DIMENSIONS:
            for noise_sigma in REFERENCE_NOISES:
                for seed in REFERENCE_SEEDS:
                    for method in REFERENCE_METHODS:
                        row = run_reference(
                            method=method,
                            function_name=function_name,
                            dimension=dimension,
                            seed=seed,
                            noise_sigma=noise_sigma,
                            initial_sigma=REFERENCE_INITIAL_SIGMA,
                            popsize=REFERENCE_POPSIZE,
                            planned_generations=REFERENCE_PLANNED_GENERATIONS,
                            controller_config=(controller_config if method == "proxy" else None),
                            trace_mode=TraceMode.OFF,
                        )
                        rows.append(row)

    rows.sort(
        key=lambda r: (
            str(r["function"]),
            int(r["dimension"]),
            float(r["noise_sigma"]),
            int(r["seed"]),
            str(r["method"]),
        )
    )
    return rows


def _write_reference_runs(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError("No reference rows generated")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_test_summary(
    path: Path,
    *,
    pytest_return_code: int,
    tests_passed: int,
    tests_skipped: int,
    coverage_total: str,
    coverage_required: str,
    git_commit: str,
    git_commit_date: str,
) -> None:
    lines = [
        "command=python -m pytest",
        f"exit_code={pytest_return_code}",
        f"tests_passed={tests_passed}",
        f"tests_skipped={tests_skipped}",
        f"coverage_total_percent={coverage_total}",
        f"coverage_required_percent={coverage_required}",
        f"python_version={platform.python_version()}",
        f"platform={platform.platform()}",
        f"git_commit={git_commit}",
        f"git_commit_date_utc={git_commit_date}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest(
    path: Path,
    *,
    repo_root: Path,
    output_files: list[Path],
    git_commit: str,
    git_commit_short: str,
    git_commit_date: str,
    git_dirty: bool,
    rows_count: int,
) -> None:
    outputs = []
    for file_path in output_files:
        rel = file_path.relative_to(repo_root)
        item: dict[str, Any] = {
            "path": str(rel),
            "sha256": _sha256(file_path),
        }
        if file_path.name == "reference_runs.csv":
            item["rows"] = rows_count
        outputs.append(item)

    payload = {
        "schema_version": 1,
        "package_version": PACKAGE_VERSION,
        "timestamp_utc": git_commit_date,
        "generator": "scripts/build_publication_evidence.py",
        "git": {
            "commit": git_commit,
            "commit_short": git_commit_short,
            "commit_date_utc": git_commit_date,
            "dirty_worktree": git_dirty,
        },
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "commands": {
            "pytest": "python -m pytest",
            "reference_runs": "python scripts/build_publication_evidence.py",
        },
        "outputs": outputs,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    src_root = repo_root / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

    release_dir = repo_root / "release-assets" / RELEASE_DIR_NAME

    reference_runs_path = release_dir / "reference_runs.csv"
    test_summary_path = release_dir / "test_gate_summary.txt"
    manifest_path = release_dir / "evidence_manifest.json"

    git_commit = _git_value(repo_root, "rev-parse", "HEAD")
    git_commit_short = _git_value(repo_root, "rev-parse", "--short", "HEAD")
    git_commit_date = _git_value(repo_root, "show", "-s", "--format=%cI", "HEAD")
    git_status = _git_value(repo_root, "status", "--porcelain")
    git_dirty = bool(git_status and git_status != "unknown")

    pytest_proc = _run([sys.executable, "-m", "pytest"], repo_root)
    pytest_output = (pytest_proc.stdout or "") + "\n" + (pytest_proc.stderr or "")
    tests_passed, tests_skipped, coverage_total, coverage_required = _parse_pytest_summary(pytest_output)
    _write_test_summary(
        test_summary_path,
        pytest_return_code=pytest_proc.returncode,
        tests_passed=tests_passed,
        tests_skipped=tests_skipped,
        coverage_total=coverage_total,
        coverage_required=coverage_required,
        git_commit=git_commit,
        git_commit_date=git_commit_date,
    )
    if pytest_proc.returncode != 0:
        raise RuntimeError("pytest failed during evidence build; see test_gate_summary.txt")

    rows = _build_reference_rows()
    _write_reference_runs(reference_runs_path, rows)

    _write_manifest(
        manifest_path,
        repo_root=repo_root,
        output_files=[reference_runs_path, test_summary_path],
        git_commit=git_commit,
        git_commit_short=git_commit_short,
        git_commit_date=git_commit_date,
        git_dirty=git_dirty,
        rows_count=len(rows),
    )

    print(str(reference_runs_path.relative_to(repo_root)))
    print(str(test_summary_path.relative_to(repo_root)))
    print(str(manifest_path.relative_to(repo_root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
