from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .io import load_json, parse_findings_args, save_json


def _status_by_phase(runs_df: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = (
        runs_df.groupby(["phase", "status"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["phase", "status"])
    )
    return grouped.to_dict(orient="records")


def _build_markdown(payload: dict[str, Any]) -> str:
    exec_info = payload["execution"]
    stats = payload["statistics"]
    behavior = payload["behavior"]
    hypotheses = payload.get("hypotheses")

    lines = [
        "# Run Findings",
        "",
        "## Run Identity",
        f"- Run ID: `{payload['run_id']}`",
        f"- Scope: `{payload['run_scope']}`",
        f"- Created (UTC): `{payload['created_at_utc']}`",
        f"- Config: `{payload['config_path']}`",
        f"- Config Hash: `{payload['config_hash']}`",
        "",
        "## Execution",
        f"- Total runs: `{exec_info['total_runs']}`",
        f"- OK runs: `{exec_info['ok_runs']}`",
        f"- Failed runs: `{exec_info['failed_runs']}`",
        "- Status by phase:",
    ]

    for row in exec_info["status_by_phase"]:
        lines.append(f"  - `{row['phase']}` / `{row['status']}`: `{row['count']}`")

    lines.extend(
        [
            "",
            "## Performance Summary",
            f"- Compared method rows: `{stats['n_methods']}`",
            f"- Cell rows: `{stats['n_cells']}`",
            f"- Significant cells (q < 0.05): `{stats['n_q_lt_0_05']}`",
            "- Ranking (lower median delta is better):",
        ]
    )

    for row in stats["ranking"]:
        lines.append(
            f"  - `{row['method_instance']}`: median delta `{row['median_of_cell_median_delta']}`, "
            f"win-rate `{row['mean_win_rate']}`, q<0.05 cells `{row['cells_q_lt_0_05']}`"
        )

    lines.extend(
        [
            "",
            "## Behavior Summary",
            f"- Behavior rows: `{behavior['n_behavior_rows']}`",
            f"- Methods with behavior telemetry: `{behavior['n_methods_with_behavior']}`",
        ]
    )

    if hypotheses is not None:
        lines.extend(
            [
                "",
                "## Hypothesis Checks",
                f"- Total checks: `{hypotheses['n_checks']}`",
                f"- Passed: `{hypotheses['n_passed']}`",
                f"- Failed: `{hypotheses['n_failed']}`",
                f"- Errors: `{hypotheses['n_errors']}`",
            ]
        )

    lines.extend(["", "## Warnings"])
    for warning in payload["warnings"]:
        lines.append(f"- {warning}")

    lines.extend(["", "## Artifact Links"])
    for key, value in sorted(payload["artifacts"].items()):
        lines.append(f"- `{key}`: `{value}`")

    return "\n".join(lines) + "\n"


def generate_findings(results_dir: str | Path, figdir: str | Path) -> dict[str, str]:
    results_path = Path(results_dir)
    fig_path = Path(figdir)

    manifest_path = results_path / "manifest.json"
    analysis_manifest_path = results_path / "analysis_manifest.json"
    runs_path = results_path / "runs_long.csv"
    cell_stats_path = results_path / "cell_stats.csv"
    method_agg_path = results_path / "method_aggregate.csv"
    behavior_agg_path = results_path / "behavior_aggregate.csv"
    hypothesis_path = results_path / "hypothesis_checks.json"

    manifest = load_json(manifest_path)
    analysis_manifest = load_json(analysis_manifest_path)

    runs_df = pd.read_csv(runs_path)
    cell_stats_df = pd.read_csv(cell_stats_path)
    method_agg_df = pd.read_csv(method_agg_path)
    behavior_agg_df = pd.read_csv(behavior_agg_path)

    warnings: list[str] = []
    failed_runs = int((runs_df["status"] != "ok").sum())
    if failed_runs > 0:
        warnings.append("Some runs failed; inspect runs_long.csv before interpreting outcomes.")
    if method_agg_df.empty:
        warnings.append("method_aggregate.csv is empty; no comparative outcomes were computed.")
    if behavior_agg_df["n_behavior_rows"].fillna(0).sum() == 0:
        warnings.append("No behavior telemetry rows were available in this run.")

    hypotheses_summary: dict[str, Any] | None = None
    if hypothesis_path.is_file():
        hypothesis_payload = load_json(hypothesis_path)
        hsum = hypothesis_payload.get("summary", {})
        hypotheses_summary = {
            "n_checks": int(hsum.get("n_checks", 0)),
            "n_passed": int(hsum.get("n_passed", 0)),
            "n_failed": int(hsum.get("n_failed", 0)),
            "n_errors": int(hsum.get("n_errors", 0)),
        }
        if hypotheses_summary["n_errors"] > 0:
            warnings.append("One or more hypothesis checks errored; inspect hypothesis_checks.json.")

    ranking = (
        method_agg_df.sort_values("median_of_cell_median_delta", ascending=True)
        .head(10)
        .to_dict(orient="records")
    )

    artifacts: dict[str, str] = {
        "runs_long_csv": str(runs_path),
        "manifest_json": str(manifest_path),
        "analysis_manifest_json": str(analysis_manifest_path),
        "cell_stats_csv": str(cell_stats_path),
        "method_aggregate_csv": str(method_agg_path),
        "behavior_aggregate_csv": str(behavior_agg_path),
    }
    if hypothesis_path.is_file():
        artifacts["hypothesis_checks_json"] = str(hypothesis_path)

    for key, rel_name in [
        ("figure_method_delta", "method_median_delta_bar.png"),
        ("figure_method_win_rate", "method_win_rate_bar.png"),
        ("figure_behavior_floor", "behavior_fraction_at_floor_bar.png"),
        ("figure_behavior_ttf", "behavior_time_to_first_floor_bar.png"),
    ]:
        candidate = fig_path / rel_name
        if candidate.is_file():
            artifacts[key] = str(candidate)

    for pairwise_file in sorted(results_path.glob("pairwise_*.json")):
        artifacts[f"pairwise_json_{pairwise_file.stem}"] = str(pairwise_file)

    payload = {
        "run_id": str(manifest.get("run_id", "unknown")),
        "run_scope": str(manifest.get("run_scope", "unknown")),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(manifest.get("config_path", "unknown")),
        "config_hash": str(manifest.get("config_hash", "unknown")),
        "manifest_json": str(manifest_path),
        "analysis_manifest_json": str(analysis_manifest_path),
        "execution": {
            "total_runs": int(len(runs_df)),
            "ok_runs": int((runs_df["status"] == "ok").sum()),
            "failed_runs": failed_runs,
            "status_by_phase": _status_by_phase(runs_df),
        },
        "statistics": {
            "n_cells": int(len(cell_stats_df)),
            "n_methods": int(method_agg_df["method_instance"].nunique()) if not method_agg_df.empty else 0,
            "n_q_lt_0_05": int((cell_stats_df["bh_fdr_q_value"] < 0.05).sum()) if not cell_stats_df.empty else 0,
            "ranking": ranking,
        },
        "behavior": {
            "n_behavior_rows": int(behavior_agg_df["n_behavior_rows"].fillna(0).sum()) if not behavior_agg_df.empty else 0,
            "n_methods_with_behavior": int((behavior_agg_df["n_behavior_rows"].fillna(0) > 0).sum())
            if not behavior_agg_df.empty
            else 0,
        },
        "hypotheses": hypotheses_summary,
        "warnings": warnings,
        "artifacts": artifacts,
        "analysis_manifest_files": analysis_manifest.get("files", {}),
    }

    findings_json = results_path / "findings.json"
    findings_md = results_path / "findings.md"
    save_json(findings_json, payload)
    findings_md.write_text(_build_markdown(payload), encoding="utf-8")

    return {
        "findings_json": str(findings_json),
        "findings_md": str(findings_md),
    }


def main() -> None:
    args = parse_findings_args()
    outputs = generate_findings(args.results_dir, args.figdir)
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
