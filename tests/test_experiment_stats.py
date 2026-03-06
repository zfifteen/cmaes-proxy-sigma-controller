from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.stats import (
    compute_behavior_aggregate,
    compute_cell_stats,
    compute_method_aggregate,
    compute_pairwise_cell_stats,
    resolve_reference_method_instance,
)


def _runs_df() -> pd.DataFrame:
    rows = []
    for seed, vanilla_best, proxy_best in [(1, 10.0, 9.0), (2, 12.0, 10.5)]:
        rows.append(
            {
                "phase": "eval",
                "status": "ok",
                "method": "vanilla_cma",
                "variant_id": None,
                "method_instance": "vanilla_cma",
                "reference_method": "vanilla_cma",
                "function": "sphere",
                "dimension": 10,
                "noise_sigma": 0.1,
                "seed": seed,
                "final_best": vanilla_best,
                "proxy_fraction_at_floor": np.nan,
                "proxy_time_to_first_floor_gen": np.nan,
                "proxy_n_floor_entries": np.nan,
                "proxy_n_floor_exits": np.nan,
                "proxy_n_down_steps": np.nan,
                "proxy_n_up_steps": np.nan,
                "proxy_n_neutral_steps": np.nan,
                "proxy_sigma_min_seen": np.nan,
                "proxy_sigma_max_seen": np.nan,
                "proxy_ema_snr_last": np.nan,
            }
        )
        rows.append(
            {
                "phase": "eval",
                "status": "ok",
                "method": "proxy_sigma_controller",
                "variant_id": None,
                "method_instance": "proxy_sigma_controller",
                "reference_method": "vanilla_cma",
                "function": "sphere",
                "dimension": 10,
                "noise_sigma": 0.1,
                "seed": seed,
                "final_best": proxy_best,
                "proxy_fraction_at_floor": 0.2,
                "proxy_time_to_first_floor_gen": 8.0,
                "proxy_n_floor_entries": 1.0,
                "proxy_n_floor_exits": 0.0,
                "proxy_n_down_steps": 6.0,
                "proxy_n_up_steps": 2.0,
                "proxy_n_neutral_steps": 2.0,
                "proxy_sigma_min_seen": 0.1,
                "proxy_sigma_max_seen": 1.0,
                "proxy_ema_snr_last": 0.3,
            }
        )
    return pd.DataFrame(rows)


def test_resolve_reference_method_instance() -> None:
    df = _runs_df()
    resolved = resolve_reference_method_instance(df, None)
    assert resolved == "vanilla_cma"


def test_cell_and_method_aggregate() -> None:
    df = _runs_df()
    cell_stats, reference_instance = compute_cell_stats(df, reference_method="vanilla_cma")
    assert reference_instance == "vanilla_cma"
    assert len(cell_stats) == 1
    assert cell_stats.iloc[0]["method_instance"] == "proxy_sigma_controller"
    assert cell_stats.iloc[0]["median_delta_vs_reference"] < 0.0

    method_agg = compute_method_aggregate(cell_stats)
    assert len(method_agg) == 1
    assert method_agg.iloc[0]["method_instance"] == "proxy_sigma_controller"
    assert method_agg.iloc[0]["mean_win_rate"] > 0.0


def test_behavior_aggregate_handles_non_proxy_rows() -> None:
    df = _runs_df()
    behavior = compute_behavior_aggregate(df)
    assert set(behavior["method_instance"].tolist()) == {"vanilla_cma", "proxy_sigma_controller"}

    vanilla = behavior.loc[behavior["method_instance"] == "vanilla_cma"].iloc[0]
    assert int(vanilla["n_behavior_rows"]) == 0
    assert np.isnan(vanilla["proxy_fraction_at_floor_mean"])

    proxy = behavior.loc[behavior["method_instance"] == "proxy_sigma_controller"].iloc[0]
    assert int(proxy["n_behavior_rows"]) == 2
    assert proxy["proxy_fraction_at_floor_mean"] == 0.2


def test_pairwise_stats() -> None:
    df = _runs_df()
    pairwise = compute_pairwise_cell_stats(
        df,
        method_a="vanilla_cma",
        method_b="proxy_sigma_controller",
    )
    assert len(pairwise) == 1
    assert pairwise.iloc[0]["median_delta_b_minus_a"] < 0.0
