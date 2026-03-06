#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.io import load_yaml_config, sanitize_token  # noqa: E402


REQUIRED_RESULTS = [
    "runs_long.csv",
    "manifest.json",
    "cell_stats.csv",
    "method_aggregate.csv",
    "behavior_aggregate.csv",
    "analysis_manifest.json",
    "hypothesis_checks.json",
    "findings.json",
    "findings.md",
]

REQUIRED_FIGURES = [
    "method_median_delta_bar.png",
    "method_win_rate_bar.png",
    "behavior_fraction_at_floor_bar.png",
    "behavior_time_to_first_floor_bar.png",
]

RUNS_COLS = {
    "phase",
    "method",
    "variant_id",
    "method_instance",
    "reference_method",
    "function",
    "dimension",
    "noise_sigma",
    "seed",
    "eval_budget",
    "popsize",
    "initial_sigma",
    "status",
    "error_message",
    "n_evals",
    "generations",
    "final_best",
    "duration_sec",
    "proxy_schema_version",
    "proxy_sigma_factor_last",
    "proxy_ema_snr_last",
    "proxy_time_to_first_floor_gen",
    "proxy_fraction_at_floor",
    "proxy_n_floor_entries",
    "proxy_n_floor_exits",
    "proxy_n_down_steps",
    "proxy_n_up_steps",
    "proxy_n_neutral_steps",
    "proxy_sigma_min_seen",
    "proxy_sigma_max_seen",
    "proxy_trace_written",
    "proxy_trace_relpath",
}

CELL_STATS_COLS = {
    "function",
    "dimension",
    "noise_sigma",
    "method",
    "variant_id",
    "method_instance",
    "reference_method_instance",
    "n_pairs",
    "median_delta_vs_reference",
    "win_rate_vs_reference",
    "loss_rate_vs_reference",
    "wilcoxon_p_two_sided",
    "bh_fdr_q_value",
}

METHOD_AGG_COLS = {
    "method",
    "variant_id",
    "method_instance",
    "reference_method_instance",
    "n_cells",
    "median_of_cell_median_delta",
    "mean_win_rate",
    "mean_loss_rate",
    "fraction_cells_median_delta_lt0",
    "cells_q_lt_0_05",
    "best_q_value",
}

BEHAVIOR_AGG_COLS = {
    "method",
    "variant_id",
    "method_instance",
    "n_runs",
    "n_behavior_rows",
    "proxy_fraction_at_floor_mean",
    "proxy_fraction_at_floor_median",
    "proxy_time_to_first_floor_gen_mean",
    "proxy_n_floor_entries_mean",
    "proxy_n_floor_exits_mean",
    "proxy_n_down_steps_mean",
    "proxy_n_up_steps_mean",
    "proxy_n_neutral_steps_mean",
    "proxy_sigma_min_seen_mean",
    "proxy_sigma_max_seen_mean",
    "proxy_ema_snr_last_mean",
}

PAIRWISE_COLS = {
    "function",
    "dimension",
    "noise_sigma",
    "method_a",
    "method_b",
    "n_pairs",
    "median_delta_b_minus_a",
    "win_rate_b_vs_a",
    "loss_rate_b_vs_a",
    "wilcoxon_p_two_sided",
    "bh_fdr_q_value",
}


def fail(message: str) -> None:
    print(f"[verify-experiment] FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def _check_columns(path: Path, required: set[str]) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = sorted(required.difference(df.columns))
    if missing:
        fail(f"{path.name} missing columns: {missing}")
    return df


def _to_existing_path(path_text: str, repo_root: Path) -> Path:
    candidate = Path(path_text)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--figdir", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--require-pairwise", action="store_true")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    figdir = Path(args.figdir)
    config = load_yaml_config(args.config)

    for rel in REQUIRED_RESULTS:
        path = results_dir / rel
        if not path.is_file():
            fail(f"Missing required result artifact: {path}")

    for rel in REQUIRED_FIGURES:
        path = figdir / rel
        if not path.is_file():
            fail(f"Missing required figure artifact: {path}")

    runs_df = _check_columns(results_dir / "runs_long.csv", RUNS_COLS)
    _check_columns(results_dir / "cell_stats.csv", CELL_STATS_COLS)
    _check_columns(results_dir / "method_aggregate.csv", METHOD_AGG_COLS)
    _check_columns(results_dir / "behavior_aggregate.csv", BEHAVIOR_AGG_COLS)

    if not set(runs_df["phase"].unique()).issubset({"eval"}):
        fail("runs_long.csv contains unsupported phase values")
    if not set(runs_df["status"].unique()).issubset({"ok", "failed"}):
        fail("runs_long.csv contains unsupported status values")

    findings_payload = json.loads((results_dir / "findings.json").read_text(encoding="utf-8"))
    required_findings_keys = {
        "run_id",
        "run_scope",
        "created_at_utc",
        "config_path",
        "config_hash",
        "manifest_json",
        "analysis_manifest_json",
        "execution",
        "statistics",
        "behavior",
        "warnings",
        "artifacts",
    }
    missing_findings = sorted(required_findings_keys.difference(findings_payload.keys()))
    if missing_findings:
        fail(f"findings.json missing keys: {missing_findings}")

    artifacts = findings_payload.get("artifacts", {})
    if not isinstance(artifacts, dict):
        fail("findings.json artifacts must be an object")
    for key, value in artifacts.items():
        path = _to_existing_path(str(value), REPO_ROOT)
        if not path.exists():
            fail(f"findings artifact path missing ({key}): {path}")

    hypothesis_payload = json.loads((results_dir / "hypothesis_checks.json").read_text(encoding="utf-8"))
    if "summary" not in hypothesis_payload or "checks" not in hypothesis_payload:
        fail("hypothesis_checks.json missing summary/checks")

    if args.require_pairwise:
        default_pairwise = config.get("analysis", {}).get("default_pairwise", {})
        method_a = str(default_pairwise.get("method_a", ""))
        method_b = str(default_pairwise.get("method_b", ""))
        if not method_a or not method_b:
            fail("--require-pairwise set but config has no analysis.default_pairwise")
        prefix = f"pairwise_{sanitize_token(method_b)}_vs_{sanitize_token(method_a)}"
        pairwise_csv = results_dir / f"{prefix}.csv"
        pairwise_json = results_dir / f"{prefix}.json"
        if not pairwise_csv.is_file() or not pairwise_json.is_file():
            fail(f"Missing pairwise artifacts for default pairwise config: {prefix}")
        _check_columns(pairwise_csv, PAIRWISE_COLS)

    print("[verify-experiment] PASS: artifacts, schemas, and findings links validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
