from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr, wilcoxon


def _bh_fdr(p_values: np.ndarray) -> np.ndarray:
    n = int(p_values.size)
    if n == 0:
        return np.array([], dtype=float)

    safe = np.asarray(p_values, dtype=float)
    safe = np.where(np.isfinite(safe), safe, 1.0)
    safe = np.clip(safe, 0.0, 1.0)

    order = np.argsort(safe)
    ranked = safe[order]
    q_ranked = np.empty(n, dtype=float)

    prev = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        value = ranked[i] * n / rank
        prev = min(prev, value)
        q_ranked[i] = min(prev, 1.0)

    q = np.empty(n, dtype=float)
    q[order] = q_ranked
    return q


def _wilcoxon_two_sided(deltas: np.ndarray) -> float:
    if deltas.size == 0:
        return float("nan")
    if np.allclose(deltas, 0.0):
        return 1.0
    try:
        return float(wilcoxon(deltas, alternative="two-sided", zero_method="pratt").pvalue)
    except ValueError:
        return 1.0


def resolve_reference_method_instance(runs_df: pd.DataFrame, reference_method: str | None = None) -> str:
    method_instances = set(runs_df["method_instance"].dropna().astype(str).unique())
    methods = set(runs_df["method"].dropna().astype(str).unique())

    candidate = reference_method
    if candidate is None:
        if "reference_method" in runs_df.columns:
            vals = sorted({str(x) for x in runs_df["reference_method"].dropna().unique()})
            if len(vals) == 1:
                candidate = vals[0]
        if candidate is None and "vanilla_cma" in methods:
            candidate = "vanilla_cma"

    if candidate is None:
        raise ValueError("Could not infer reference method")

    if candidate in method_instances:
        return candidate

    if candidate in methods:
        matches = sorted({str(x) for x in runs_df.loc[runs_df["method"] == candidate, "method_instance"].unique()})
        if len(matches) == 1:
            return matches[0]
        raise ValueError(
            f"Reference method {candidate!r} maps to multiple method_instance values: {matches}. "
            "Specify --reference-method as an explicit method_instance."
        )

    raise ValueError(f"Reference method not present in runs data: {candidate!r}")


def _method_lookup(eval_df: pd.DataFrame) -> dict[str, tuple[str, str | None]]:
    lookup: dict[str, tuple[str, str | None]] = {}
    for method_instance, group in eval_df.groupby("method_instance"):
        method = str(group["method"].iloc[0])
        variant_raw = group["variant_id"].iloc[0]
        variant_id = None if pd.isna(variant_raw) else str(variant_raw)
        lookup[str(method_instance)] = (method, variant_id)
    return lookup


def compute_cell_stats(runs_df: pd.DataFrame, reference_method: str | None = None) -> tuple[pd.DataFrame, str]:
    out_columns = [
        "function",
        "dimension",
        "noise_sigma",
        "method",
        "variant_id",
        "method_instance",
        "reference_method_instance",
        "n_pairs",
        "reference_median",
        "method_median",
        "median_delta_vs_reference",
        "win_rate_vs_reference",
        "loss_rate_vs_reference",
        "wilcoxon_p_two_sided",
        "bh_fdr_q_value",
    ]

    eval_df = runs_df[(runs_df["phase"] == "eval") & (runs_df["status"] == "ok")].copy()
    if eval_df.empty:
        return pd.DataFrame(columns=out_columns), ""

    reference_instance = resolve_reference_method_instance(eval_df, reference_method)
    method_lookup = _method_lookup(eval_df)

    cells = (
        eval_df[["function", "dimension", "noise_sigma"]]
        .drop_duplicates()
        .sort_values(["function", "dimension", "noise_sigma"])
    )
    method_instances = sorted(eval_df["method_instance"].astype(str).unique())

    rows: list[dict[str, Any]] = []
    for _, cell in cells.iterrows():
        cell_df = eval_df[
            (eval_df["function"] == cell["function"])
            & (eval_df["dimension"] == cell["dimension"])
            & (eval_df["noise_sigma"] == cell["noise_sigma"])
        ]

        pivot = cell_df.pivot_table(index="seed", columns="method_instance", values="final_best", aggfunc="first")
        if reference_instance not in pivot.columns:
            continue

        for method_instance in method_instances:
            if method_instance == reference_instance or method_instance not in pivot.columns:
                continue
            paired = pivot[[reference_instance, method_instance]].dropna()
            n_pairs = int(len(paired))
            if n_pairs == 0:
                continue

            deltas = (paired[method_instance] - paired[reference_instance]).to_numpy(dtype=float)
            method, variant_id = method_lookup[method_instance]

            rows.append(
                {
                    "function": str(cell["function"]),
                    "dimension": int(cell["dimension"]),
                    "noise_sigma": float(cell["noise_sigma"]),
                    "method": method,
                    "variant_id": variant_id,
                    "method_instance": method_instance,
                    "reference_method_instance": reference_instance,
                    "n_pairs": n_pairs,
                    "reference_median": float(np.median(paired[reference_instance].to_numpy(dtype=float))),
                    "method_median": float(np.median(paired[method_instance].to_numpy(dtype=float))),
                    "median_delta_vs_reference": float(np.median(deltas)),
                    "win_rate_vs_reference": float(np.mean(deltas < 0.0)),
                    "loss_rate_vs_reference": float(np.mean(deltas > 0.0)),
                    "wilcoxon_p_two_sided": _wilcoxon_two_sided(deltas),
                }
            )

    cell_stats = pd.DataFrame(rows)
    if cell_stats.empty:
        return pd.DataFrame(columns=out_columns), reference_instance

    qvals = _bh_fdr(cell_stats["wilcoxon_p_two_sided"].to_numpy(dtype=float))
    cell_stats["bh_fdr_q_value"] = qvals

    return (
        cell_stats.sort_values(["function", "dimension", "noise_sigma", "method_instance"]).reset_index(drop=True),
        reference_instance,
    )


def compute_method_aggregate(cell_stats: pd.DataFrame) -> pd.DataFrame:
    columns = [
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
    ]
    if cell_stats.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, Any]] = []
    grouped = cell_stats.groupby(["method", "variant_id", "method_instance", "reference_method_instance"], dropna=False)
    for (method, variant_id, method_instance, reference_instance), group in grouped:
        rows.append(
            {
                "method": str(method),
                "variant_id": None if pd.isna(variant_id) else str(variant_id),
                "method_instance": str(method_instance),
                "reference_method_instance": str(reference_instance),
                "n_cells": int(len(group)),
                "median_of_cell_median_delta": float(np.median(group["median_delta_vs_reference"])),
                "mean_win_rate": float(np.mean(group["win_rate_vs_reference"])),
                "mean_loss_rate": float(np.mean(group["loss_rate_vs_reference"])),
                "fraction_cells_median_delta_lt0": float(np.mean(group["median_delta_vs_reference"] < 0.0)),
                "cells_q_lt_0_05": int(np.sum(group["bh_fdr_q_value"] < 0.05)),
                "best_q_value": float(np.min(group["bh_fdr_q_value"])),
            }
        )

    return pd.DataFrame(rows).sort_values(["method", "variant_id", "method_instance"]).reset_index(drop=True)


def compute_behavior_aggregate(runs_df: pd.DataFrame) -> pd.DataFrame:
    columns = [
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
    ]

    eval_df = runs_df[(runs_df["phase"] == "eval") & (runs_df["status"] == "ok")].copy()
    if eval_df.empty:
        return pd.DataFrame(columns=columns)

    metric_cols = [
        "proxy_fraction_at_floor",
        "proxy_time_to_first_floor_gen",
        "proxy_n_floor_entries",
        "proxy_n_floor_exits",
        "proxy_n_down_steps",
        "proxy_n_up_steps",
        "proxy_n_neutral_steps",
        "proxy_sigma_min_seen",
        "proxy_sigma_max_seen",
        "proxy_ema_snr_last",
    ]

    rows: list[dict[str, Any]] = []
    grouped = eval_df.groupby(["method", "variant_id", "method_instance"], dropna=False)
    for (method, variant_id, method_instance), group in grouped:
        behavior = group[metric_cols].dropna(how="all")
        if behavior.empty:
            rows.append(
                {
                    "method": str(method),
                    "variant_id": None if pd.isna(variant_id) else str(variant_id),
                    "method_instance": str(method_instance),
                    "n_runs": int(len(group)),
                    "n_behavior_rows": 0,
                    "proxy_fraction_at_floor_mean": float("nan"),
                    "proxy_fraction_at_floor_median": float("nan"),
                    "proxy_time_to_first_floor_gen_mean": float("nan"),
                    "proxy_n_floor_entries_mean": float("nan"),
                    "proxy_n_floor_exits_mean": float("nan"),
                    "proxy_n_down_steps_mean": float("nan"),
                    "proxy_n_up_steps_mean": float("nan"),
                    "proxy_n_neutral_steps_mean": float("nan"),
                    "proxy_sigma_min_seen_mean": float("nan"),
                    "proxy_sigma_max_seen_mean": float("nan"),
                    "proxy_ema_snr_last_mean": float("nan"),
                }
            )
            continue

        rows.append(
            {
                "method": str(method),
                "variant_id": None if pd.isna(variant_id) else str(variant_id),
                "method_instance": str(method_instance),
                "n_runs": int(len(group)),
                "n_behavior_rows": int(len(behavior)),
                "proxy_fraction_at_floor_mean": float(np.mean(behavior["proxy_fraction_at_floor"])),
                "proxy_fraction_at_floor_median": float(np.median(behavior["proxy_fraction_at_floor"])),
                "proxy_time_to_first_floor_gen_mean": float(np.mean(behavior["proxy_time_to_first_floor_gen"])),
                "proxy_n_floor_entries_mean": float(np.mean(behavior["proxy_n_floor_entries"])),
                "proxy_n_floor_exits_mean": float(np.mean(behavior["proxy_n_floor_exits"])),
                "proxy_n_down_steps_mean": float(np.mean(behavior["proxy_n_down_steps"])),
                "proxy_n_up_steps_mean": float(np.mean(behavior["proxy_n_up_steps"])),
                "proxy_n_neutral_steps_mean": float(np.mean(behavior["proxy_n_neutral_steps"])),
                "proxy_sigma_min_seen_mean": float(np.mean(behavior["proxy_sigma_min_seen"])),
                "proxy_sigma_max_seen_mean": float(np.mean(behavior["proxy_sigma_max_seen"])),
                "proxy_ema_snr_last_mean": float(np.mean(behavior["proxy_ema_snr_last"])),
            }
        )

    return pd.DataFrame(rows).sort_values(["method", "variant_id", "method_instance"]).reset_index(drop=True)


def compute_pairwise_cell_stats(
    runs_df: pd.DataFrame,
    *,
    method_a: str,
    method_b: str,
) -> pd.DataFrame:
    columns = [
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
    ]

    eval_df = runs_df[(runs_df["phase"] == "eval") & (runs_df["status"] == "ok")].copy()
    eval_df = eval_df[eval_df["method_instance"].isin([method_a, method_b])]
    if eval_df.empty:
        return pd.DataFrame(columns=columns)

    cells = (
        eval_df[["function", "dimension", "noise_sigma"]]
        .drop_duplicates()
        .sort_values(["function", "dimension", "noise_sigma"])
    )

    rows: list[dict[str, Any]] = []
    for _, cell in cells.iterrows():
        cell_df = eval_df[
            (eval_df["function"] == cell["function"])
            & (eval_df["dimension"] == cell["dimension"])
            & (eval_df["noise_sigma"] == cell["noise_sigma"])
        ]
        pivot = cell_df.pivot_table(index="seed", columns="method_instance", values="final_best", aggfunc="first")
        if method_a not in pivot.columns or method_b not in pivot.columns:
            continue

        paired = pivot[[method_a, method_b]].dropna()
        n_pairs = int(len(paired))
        if n_pairs == 0:
            continue
        deltas = (paired[method_b] - paired[method_a]).to_numpy(dtype=float)

        rows.append(
            {
                "function": str(cell["function"]),
                "dimension": int(cell["dimension"]),
                "noise_sigma": float(cell["noise_sigma"]),
                "method_a": method_a,
                "method_b": method_b,
                "n_pairs": n_pairs,
                "median_delta_b_minus_a": float(np.median(deltas)),
                "win_rate_b_vs_a": float(np.mean(deltas < 0.0)),
                "loss_rate_b_vs_a": float(np.mean(deltas > 0.0)),
                "wilcoxon_p_two_sided": _wilcoxon_two_sided(deltas),
            }
        )

    pairwise = pd.DataFrame(rows)
    if pairwise.empty:
        return pd.DataFrame(columns=columns)

    pairwise["bh_fdr_q_value"] = _bh_fdr(pairwise["wilcoxon_p_two_sided"].to_numpy(dtype=float))
    return pairwise.sort_values(["function", "dimension", "noise_sigma"]).reset_index(drop=True)


def compute_correlation(values_x: pd.Series, values_y: pd.Series, method: str = "pearson") -> float:
    x = values_x.to_numpy(dtype=float)
    y = values_y.to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if x.size < 2:
        return float("nan")

    if method == "pearson":
        corr, _ = pearsonr(x, y)
    elif method == "spearman":
        corr, _ = spearmanr(x, y)
    else:
        raise ValueError(f"Unknown correlation method: {method}")

    if math.isnan(corr):
        return float("nan")
    return float(corr)
