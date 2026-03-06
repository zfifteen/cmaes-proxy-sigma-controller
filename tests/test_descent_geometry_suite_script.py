from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

try:
    import cma  # noqa: F401
    from scipy import stats  # noqa: F401

    HAS_EXPERIMENT_STACK = True
except Exception:  # pragma: no cover
    HAS_EXPERIMENT_STACK = False


REPO_ROOT = Path(__file__).resolve().parents[1]


def _fixture_config_text(variant_id: str, *, use_sweep: bool = False) -> str:
    if use_sweep:
        variant_block = """
variants: []
sweeps:
  - sweep_id: geomdense
    method: proxy_sigma_controller
    constants: {}
    grid:
      sigma_down_factor: [0.90]
      sigma_min_ratio: [0.10]
""".strip()
        method_b = "proxy_sigma_controller:geomdense__sigma_down_factor_0p9__sigma_min_ratio_0p1"
    else:
        variant_block = f"""
variants:
  - variant_id: {variant_id}
    method: proxy_sigma_controller
    proxy_overrides:
      sigma_down_factor: 0.90
      sigma_min_ratio: 0.10
sweeps: []
""".strip()
        method_b = f"proxy_sigma_controller:{variant_id}"

    return (
        f"""
experiment_name: fixture_stage
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
{variant_block}
telemetry:
  proxy_trace_mode: off
seeds:
  eval: [1]
runtime:
  parallel_workers: 1
analysis:
  default_pairwise:
    method_a: vanilla_cma
    method_b: {method_b}
hypotheses:
  checks:
    - id: fixture_exists
      type: metric_threshold
      dataset: method_aggregate
      where:
        method: proxy_sigma_controller
      metric: mean_win_rate
      aggregate: first
      op: ">="
      threshold: 0.0
""".strip()
        + "\n"
    )


@pytest.mark.skipif(not HAS_EXPERIMENT_STACK, reason="pycma/scipy unavailable")
def test_descent_geometry_suite_dry_run_stage_order(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["DESCENT_GEOM_RUN_BASE"] = str(tmp_path / "runs")

    proc = subprocess.run(
        ["bash", "scripts/run_descent_geometry_suite.sh", "--dry-run"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    output = proc.stdout
    assert "stage=dense" in output
    assert "stage=interaction" in output
    assert "stage=anchors_full" in output
    assert output.index("stage=dense") < output.index("stage=interaction") < output.index("stage=anchors_full")

    manifest = Path(env["DESCENT_GEOM_RUN_BASE"]) / "suite_manifest.json"
    assert manifest.is_file()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert [s["stage"] for s in payload["stages"]] == ["dense", "interaction", "anchors_full"]


@pytest.mark.skipif(not HAS_EXPERIMENT_STACK, reason="pycma/scipy unavailable")
def test_descent_geometry_suite_runs_with_reduced_fixture_configs(tmp_path: Path) -> None:
    dense_cfg = tmp_path / "dense.yaml"
    interaction_cfg = tmp_path / "interaction.yaml"
    anchors_cfg = tmp_path / "anchors.yaml"

    dense_cfg.write_text(_fixture_config_text("unused", use_sweep=True), encoding="utf-8")
    interaction_cfg.write_text(_fixture_config_text("int_k090_r010_t008_025"), encoding="utf-8")
    anchors_cfg.write_text(_fixture_config_text("anchor_k090_r010"), encoding="utf-8")

    run_base = tmp_path / "runs"
    env = os.environ.copy()
    env["DESCENT_GEOM_RUN_BASE"] = str(run_base)
    env["DESCENT_GEOM_DENSE_CONFIG"] = str(dense_cfg)
    env["DESCENT_GEOM_INTERACTION_CONFIG"] = str(interaction_cfg)
    env["DESCENT_GEOM_ANCHORS_CONFIG"] = str(anchors_cfg)
    env["DESCENT_GEOM_DENSE_RUN_ID"] = "fixture-dense"
    env["DESCENT_GEOM_INTERACTION_RUN_ID"] = "fixture-interaction"
    env["DESCENT_GEOM_ANCHORS_RUN_ID"] = "fixture-anchors"

    subprocess.run(
        ["bash", "scripts/run_descent_geometry_suite.sh"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )

    manifest_path = run_base / "suite_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["dry_run"] is False
    assert [s["status"] for s in payload["stages"]] == ["ok", "ok", "ok"]

    for stage in payload["stages"]:
        results_dir = Path(stage["results_dir"])
        assert (results_dir / "descent_run_metrics.csv").is_file()
        assert (results_dir / "descent_cell_metrics.csv").is_file()
        assert (results_dir / "descent_variant_metrics.csv").is_file()
        assert (results_dir / "descent_geometry_summary.json").is_file()

