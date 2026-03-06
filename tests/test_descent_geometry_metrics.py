from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from experiments.descent_geometry import _build_proxy_param_lookup, generate_descent_geometry_metrics


def test_proxy_param_lookup_resolves_sweep_and_explicit_variants() -> None:
    config = {
        "experiment_name": "lookup",
        "matrix": {"functions": ["sphere"], "dimensions": [4], "noise_sigmas": [0.0]},
        "methods": ["vanilla_cma", "proxy_sigma_controller"],
        "reference_method": "vanilla_cma",
        "budget": {"evals_per_run": 40},
        "cma": {"initial_sigma": 0.5, "base_popsize": 4, "verbose": -9},
        "proxy_defaults": {"sigma_down_factor": 0.95, "sigma_min_ratio": 0.2},
        "variants": [
            {
                "variant_id": "anchor_k090_r005",
                "method": "proxy_sigma_controller",
                "proxy_overrides": {"sigma_down_factor": 0.9, "sigma_min_ratio": 0.05},
            }
        ],
        "sweeps": [
            {
                "sweep_id": "geom",
                "method": "proxy_sigma_controller",
                "constants": {},
                "grid": {"sigma_down_factor": [0.9], "sigma_min_ratio": [0.1]},
            }
        ],
        "telemetry": {"proxy_trace_mode": "off"},
        "seeds": {"eval": [1]},
        "runtime": {"parallel_workers": 1},
        "analysis": {"default_pairwise": {"method_a": "vanilla_cma", "method_b": "proxy_sigma_controller"}},
        "hypotheses": {"checks": []},
    }
    _, lookup = _build_proxy_param_lookup(config)
    assert lookup["anchor_k090_r005"]["sigma_down_factor"] == 0.9
    assert lookup["anchor_k090_r005"]["sigma_min_ratio"] == 0.05
    assert lookup["geom__sigma_down_factor_0p9__sigma_min_ratio_0p1"]["sigma_down_factor"] == 0.9
    assert lookup["geom__sigma_down_factor_0p9__sigma_min_ratio_0p1"]["sigma_min_ratio"] == 0.1


def test_descent_geometry_metrics_trace_and_missing_trace(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    runs_path = tmp_path / "runs_long.csv"
    outdir = tmp_path / "results"

    config_path.write_text(
        """
experiment_name: dg_metric_test
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
  sigma_down_factor: 0.95
  sigma_min_ratio: 0.20
variants:
  - variant_id: anchor_k090_r005
    method: proxy_sigma_controller
    proxy_overrides:
      sigma_down_factor: 0.90
      sigma_min_ratio: 0.05
sweeps:
  - sweep_id: geom
    method: proxy_sigma_controller
    constants: {}
    grid:
      sigma_down_factor: [0.90]
      sigma_min_ratio: [0.10]
telemetry:
  proxy_trace_mode: off
seeds:
  eval: [1]
runtime:
  parallel_workers: 1
analysis:
  default_pairwise:
    method_a: vanilla_cma
    method_b: proxy_sigma_controller:geom__sigma_down_factor_0p9__sigma_min_ratio_0p1
hypotheses:
  checks: []
""".strip()
        + "\n",
        encoding="utf-8",
    )

    pd.DataFrame(
        [
            {
                "phase": "eval",
                "status": "ok",
                "method": "proxy_sigma_controller",
                "variant_id": "geom__sigma_down_factor_0p9__sigma_min_ratio_0p1",
                "method_instance": "proxy_sigma_controller:geom__sigma_down_factor_0p9__sigma_min_ratio_0p1",
                "function": "sphere",
                "dimension": 4,
                "noise_sigma": 0.0,
                "seed": 1,
                "generations": 5,
                "final_best": 0.5,
                "proxy_trace_written": True,
                "proxy_trace_relpath": "proxy_traces/trace_present.csv",
            },
            {
                "phase": "eval",
                "status": "ok",
                "method": "proxy_sigma_controller",
                "variant_id": "anchor_k090_r005",
                "method_instance": "proxy_sigma_controller:anchor_k090_r005",
                "function": "sphere",
                "dimension": 4,
                "noise_sigma": 0.0,
                "seed": 2,
                "generations": 5,
                "final_best": 0.6,
                "proxy_trace_written": True,
                "proxy_trace_relpath": "proxy_traces/trace_missing.csv",
            },
        ]
    ).to_csv(runs_path, index=False)

    trace_dir = tmp_path / "proxy_traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"generation": 1, "sigma_before": 1.10, "sigma_after": 1.00, "at_floor": False},
            {"generation": 2, "sigma_before": 1.00, "sigma_after": 0.90, "at_floor": False},
            {"generation": 3, "sigma_before": 0.90, "sigma_after": 0.80, "at_floor": False},
            {"generation": 4, "sigma_before": 0.80, "sigma_after": 0.70, "at_floor": True},
            {"generation": 5, "sigma_before": 0.70, "sigma_after": 0.70, "at_floor": True},
        ]
    ).to_csv(trace_dir / "trace_present.csv", index=False)

    outputs = generate_descent_geometry_metrics(
        runs_csv=runs_path,
        config_path=config_path,
        outdir=outdir,
    )

    run_metrics = pd.read_csv(outputs["descent_run_metrics_csv"])
    assert len(run_metrics) == 2

    present = run_metrics.loc[
        run_metrics["method_instance"]
        == "proxy_sigma_controller:geom__sigma_down_factor_0p9__sigma_min_ratio_0p1"
    ].iloc[0]
    assert bool(present["trace_available"])
    assert present["k"] == 0.9
    assert present["r"] == 0.1
    assert present["first_floor_gen_trace"] == 4
    assert present["floor_gens_trace"] == 2
    assert present["descent_gens_trace"] == 3
    assert np.isclose(present["sigma_volume_total"], 4.1)
    assert np.isclose(present["sigma_volume_floor"], 1.4)
    assert np.isclose(present["sigma_volume_descent"], 2.7)
    assert np.isclose(present["descent_volume_fraction"], 2.7 / 4.1)

    missing = run_metrics.loc[run_metrics["method_instance"] == "proxy_sigma_controller:anchor_k090_r005"].iloc[0]
    assert not bool(missing["trace_available"])
    assert np.isnan(missing["first_floor_gen_trace"])

    assert Path(outputs["descent_cell_metrics_csv"]).is_file()
    assert Path(outputs["descent_variant_metrics_csv"]).is_file()
    assert Path(outputs["descent_geometry_summary_json"]).is_file()

