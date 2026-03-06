from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd
import pytest

from experiments.analyze import analyze_runs
from experiments.findings import generate_findings
from experiments.hypotheses import run_hypothesis_checks
from experiments.pairwise import generate_pairwise_artifacts
from experiments.run import execute_pipeline

try:
    import cma  # noqa: F401

    HAS_CMA = True
except Exception:  # pragma: no cover
    HAS_CMA = False


@pytest.mark.skipif(not HAS_CMA, reason="pycma unavailable")
def test_end_to_end_smoke_pipeline_and_verifier(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
experiment_name: test_smoke
matrix:
  functions: [sphere]
  dimensions: [4]
  noise_sigmas: [0.0]
methods: [vanilla_cma, proxy_sigma_controller]
reference_method: vanilla_cma
budget:
  evals_per_run: 40
cma:
  initial_sigma: 0.5
  base_popsize: 4
  verbose: -9
proxy_defaults:
  sigma_down_factor: 0.90
  sigma_up_factor: 1.03
  sigma_min_ratio: 0.10
  sigma_max_ratio: 10.0
variants: []
sweeps: []
telemetry:
  proxy_trace_mode: off
seeds:
  eval: [7, 8]
runtime:
  parallel_workers: 1
analysis:
  default_pairwise:
    method_a: vanilla_cma
    method_b: proxy_sigma_controller
hypotheses:
  checks:
    - id: proxy_exists
      type: metric_threshold
      dataset: method_aggregate
      where:
        method_instance: proxy_sigma_controller
      metric: mean_win_rate
      aggregate: first
      op: ">="
      threshold: 0.0
""".strip()
        + "\n",
        encoding="utf-8",
    )

    results_dir = tmp_path / "results"
    figures_dir = tmp_path / "figures"

    run_outputs = execute_pipeline(config_path, results_dir, workers_override=1, explicit_run_id="run-a")

    analyze_runs(
        runs_csv=run_outputs["runs_long_csv"],
        outdir=results_dir,
        figdir=figures_dir,
        manifest_json=results_dir / "manifest.json",
    )

    generate_pairwise_artifacts(
        runs_csv=results_dir / "runs_long.csv",
        method_a="vanilla_cma",
        method_b="proxy_sigma_controller",
        outdir=results_dir,
        manifest_json_path=results_dir / "manifest.json",
        analysis_manifest_path=results_dir / "analysis_manifest.json",
    )

    run_hypothesis_checks(
        runs_csv=results_dir / "runs_long.csv",
        cell_stats_csv=results_dir / "cell_stats.csv",
        method_aggregate_csv=results_dir / "method_aggregate.csv",
        behavior_aggregate_csv=results_dir / "behavior_aggregate.csv",
        config_path=config_path,
        outdir=results_dir,
    )

    generate_findings(results_dir=results_dir, figdir=figures_dir)

    repo_root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [
            "python3",
            "scripts/verify_experiment_artifacts.py",
            "--results-dir",
            str(results_dir),
            "--figdir",
            str(figures_dir),
            "--config",
            str(config_path),
            "--require-pairwise",
        ],
        cwd=repo_root,
        check=True,
    )


@pytest.mark.skipif(not HAS_CMA, reason="pycma unavailable")
def test_runs_long_deterministic_for_fixed_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
experiment_name: deterministic_check
matrix:
  functions: [sphere]
  dimensions: [4]
  noise_sigmas: [0.0]
methods: [vanilla_cma, proxy_sigma_controller]
reference_method: vanilla_cma
budget:
  evals_per_run: 40
cma:
  initial_sigma: 0.5
  base_popsize: 4
  verbose: -9
proxy_defaults:
  sigma_down_factor: 0.90
  sigma_up_factor: 1.03
  sigma_min_ratio: 0.10
  sigma_max_ratio: 10.0
variants: []
sweeps: []
telemetry:
  proxy_trace_mode: off
seeds:
  eval: [1, 2]
runtime:
  parallel_workers: 1
analysis:
  default_pairwise:
    method_a: vanilla_cma
    method_b: proxy_sigma_controller
hypotheses:
  checks: []
""".strip()
        + "\n",
        encoding="utf-8",
    )

    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    execute_pipeline(config_path, out_a, workers_override=1, explicit_run_id="det-a")
    execute_pipeline(config_path, out_b, workers_override=1, explicit_run_id="det-b")

    runs_a = pd.read_csv(out_a / "runs_long.csv")
    runs_b = pd.read_csv(out_b / "runs_long.csv")

    compare_cols = [
        "phase",
        "method",
        "variant_id",
        "method_instance",
        "function",
        "dimension",
        "noise_sigma",
        "seed",
        "eval_budget",
        "popsize",
        "status",
        "final_best",
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
    ]

    a_sorted = runs_a.sort_values(["method_instance", "function", "dimension", "noise_sigma", "seed"]).reset_index(drop=True)
    b_sorted = runs_b.sort_values(["method_instance", "function", "dimension", "noise_sigma", "seed"]).reset_index(drop=True)

    pd.testing.assert_frame_equal(a_sorted[compare_cols], b_sorted[compare_cols], check_dtype=False)


@pytest.mark.skipif(not HAS_CMA, reason="pycma unavailable")
def test_verifier_fails_when_required_artifact_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
experiment_name: verify_fail
matrix:
  functions: [sphere]
  dimensions: [4]
  noise_sigmas: [0.0]
methods: [vanilla_cma, proxy_sigma_controller]
reference_method: vanilla_cma
budget:
  evals_per_run: 20
cma:
  initial_sigma: 0.5
  base_popsize: 4
  verbose: -9
proxy_defaults:
  sigma_down_factor: 0.90
  sigma_up_factor: 1.03
  sigma_min_ratio: 0.10
  sigma_max_ratio: 10.0
variants: []
sweeps: []
telemetry:
  proxy_trace_mode: off
seeds:
  eval: [3]
runtime:
  parallel_workers: 1
analysis:
  default_pairwise:
    method_a: vanilla_cma
    method_b: proxy_sigma_controller
hypotheses:
  checks: []
""".strip()
        + "\n",
        encoding="utf-8",
    )

    results_dir = tmp_path / "results"
    figures_dir = tmp_path / "figures"
    execute_pipeline(config_path, results_dir, workers_override=1, explicit_run_id="run-v")
    analyze_runs(
        runs_csv=results_dir / "runs_long.csv",
        outdir=results_dir,
        figdir=figures_dir,
        manifest_json=results_dir / "manifest.json",
    )
    generate_pairwise_artifacts(
        runs_csv=results_dir / "runs_long.csv",
        method_a="vanilla_cma",
        method_b="proxy_sigma_controller",
        outdir=results_dir,
        manifest_json_path=results_dir / "manifest.json",
        analysis_manifest_path=results_dir / "analysis_manifest.json",
    )
    run_hypothesis_checks(
        runs_csv=results_dir / "runs_long.csv",
        cell_stats_csv=results_dir / "cell_stats.csv",
        method_aggregate_csv=results_dir / "method_aggregate.csv",
        behavior_aggregate_csv=results_dir / "behavior_aggregate.csv",
        config_path=config_path,
        outdir=results_dir,
    )
    generate_findings(results_dir=results_dir, figdir=figures_dir)

    (results_dir / "method_aggregate.csv").unlink()

    repo_root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [
            "python3",
            "scripts/verify_experiment_artifacts.py",
            "--results-dir",
            str(results_dir),
            "--figdir",
            str(figures_dir),
            "--config",
            str(config_path),
            "--require-pairwise",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "Missing required result artifact" in proc.stderr
