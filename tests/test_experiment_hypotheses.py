from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.hypotheses import run_hypothesis_checks


def _write_csv(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)


def test_hypothesis_checks_cover_all_types(tmp_path: Path) -> None:
    runs_csv = tmp_path / "runs_long.csv"
    cell_csv = tmp_path / "cell_stats.csv"
    method_csv = tmp_path / "method_aggregate.csv"
    behavior_csv = tmp_path / "behavior_aggregate.csv"
    config_path = tmp_path / "config.yaml"

    _write_csv(
        runs_csv,
        [
            {"method_instance": "vanilla_cma", "final_best": 1.0},
            {"method_instance": "proxy_sigma_controller:a", "final_best": 0.8},
        ],
    )
    _write_csv(
        cell_csv,
        [
            {"method_instance": "proxy_sigma_controller:a", "median_delta_vs_reference": -0.2},
            {"method_instance": "proxy_sigma_controller:b", "median_delta_vs_reference": -0.1},
            {"method_instance": "proxy_sigma_controller:c", "median_delta_vs_reference": 0.1},
        ],
    )
    _write_csv(
        method_csv,
        [
            {
                "method": "proxy_sigma_controller",
                "method_instance": "proxy_sigma_controller:a",
                "mean_win_rate": 0.70,
                "median_of_cell_median_delta": -0.30,
            },
            {
                "method": "proxy_sigma_controller",
                "method_instance": "proxy_sigma_controller:b",
                "mean_win_rate": 0.60,
                "median_of_cell_median_delta": -0.10,
            },
            {
                "method": "proxy_sigma_controller",
                "method_instance": "proxy_sigma_controller:c",
                "mean_win_rate": 0.40,
                "median_of_cell_median_delta": 0.20,
            },
            {
                "method": "vanilla_cma",
                "method_instance": "vanilla_cma",
                "mean_win_rate": 0.50,
                "median_of_cell_median_delta": 0.0,
            },
        ],
    )
    _write_csv(
        behavior_csv,
        [
            {"method_instance": "proxy_sigma_controller:a", "n_behavior_rows": 10},
            {"method_instance": "vanilla_cma", "n_behavior_rows": 0},
        ],
    )

    config_path.write_text(
        """
hypotheses:
  checks:
    - id: metric
      type: metric_threshold
      dataset: method_aggregate
      where:
        method_instance: proxy_sigma_controller:a
      metric: median_of_cell_median_delta
      aggregate: first
      op: "<"
      threshold: 0.0

    - id: corr
      type: correlation_threshold
      dataset: method_aggregate
      where:
        method: proxy_sigma_controller
      x_metric: mean_win_rate
      y_metric: median_of_cell_median_delta
      method: pearson
      op: "<="
      threshold: -0.5

    - id: comp
      type: comparative_threshold
      dataset: behavior_aggregate
      metric: n_behavior_rows
      aggregate: first
      lhs_where:
        method_instance: proxy_sigma_controller:a
      rhs_where:
        method_instance: vanilla_cma
      op: ">"
      threshold: 0.0
""".strip()
        + "\n",
        encoding="utf-8",
    )

    outputs = run_hypothesis_checks(
        runs_csv=runs_csv,
        cell_stats_csv=cell_csv,
        method_aggregate_csv=method_csv,
        behavior_aggregate_csv=behavior_csv,
        config_path=config_path,
        outdir=tmp_path,
    )

    payload = json.loads(Path(outputs["hypothesis_checks_json"]).read_text(encoding="utf-8"))
    assert payload["summary"]["n_checks"] == 3
    assert payload["summary"]["n_passed"] == 3
    assert payload["summary"]["n_errors"] == 0


def test_hypothesis_check_errors_are_recorded(tmp_path: Path) -> None:
    runs_csv = tmp_path / "runs_long.csv"
    cell_csv = tmp_path / "cell_stats.csv"
    method_csv = tmp_path / "method_aggregate.csv"
    config_path = tmp_path / "config.yaml"

    _write_csv(runs_csv, [{"x": 1.0}])
    _write_csv(cell_csv, [{"x": 1.0}])
    _write_csv(method_csv, [{"x": 1.0}])

    config_path.write_text(
        """
hypotheses:
  checks:
    - id: bad
      type: metric_threshold
      dataset: method_aggregate
      metric: missing_col
      aggregate: first
      op: "<"
      threshold: 0.0
""".strip()
        + "\n",
        encoding="utf-8",
    )

    outputs = run_hypothesis_checks(
        runs_csv=runs_csv,
        cell_stats_csv=cell_csv,
        method_aggregate_csv=method_csv,
        behavior_aggregate_csv=None,
        config_path=config_path,
        outdir=tmp_path,
    )

    payload = json.loads(Path(outputs["hypothesis_checks_json"]).read_text(encoding="utf-8"))
    assert payload["summary"]["n_checks"] == 1
    assert payload["summary"]["n_errors"] == 1
    assert payload["checks"][0]["status"] == "error"
