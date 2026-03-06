from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import expand_method_variants, validate_and_normalize_config
from .io import ensure_dir, load_yaml_config, save_csv, save_json
from .methods import build_default_registry

PROXY_METHOD = "proxy_sigma_controller"

RUN_COLUMNS = [
    "method",
    "variant_id",
    "method_instance",
    "function",
    "dimension",
    "noise_sigma",
    "seed",
    "generations",
    "final_best",
    "k",
    "r",
    "descent_sharpness",
    "proxy_trace_written",
    "trace_available",
    "trace_path",
    "trace_rows",
    "first_floor_gen_trace",
    "floor_gens_trace",
    "descent_gens_trace",
    "sigma_volume_total",
    "sigma_volume_descent",
    "sigma_volume_floor",
    "descent_volume_fraction",
    "mean_log_contraction_descent",
    "std_log_contraction_descent",
]

CELL_COLUMNS = [
    "method",
    "variant_id",
    "method_instance",
    "function",
    "dimension",
    "noise_sigma",
    "k",
    "r",
    "descent_sharpness",
    "n_runs",
    "n_trace_available",
    "trace_coverage",
    "final_best_mean",
    "final_best_median",
    "first_floor_gen_trace_mean",
    "floor_gens_trace_mean",
    "descent_gens_trace_mean",
    "sigma_volume_total_mean",
    "sigma_volume_descent_mean",
    "sigma_volume_floor_mean",
    "descent_volume_fraction_mean",
    "mean_log_contraction_descent_mean",
    "std_log_contraction_descent_mean",
]

VARIANT_COLUMNS = [
    "method",
    "variant_id",
    "method_instance",
    "k",
    "r",
    "descent_sharpness",
    "n_runs",
    "n_cells_observed",
    "n_trace_available",
    "trace_coverage",
    "final_best_mean",
    "final_best_median",
    "first_floor_gen_trace_mean",
    "floor_gens_trace_mean",
    "descent_gens_trace_mean",
    "sigma_volume_total_mean",
    "sigma_volume_descent_mean",
    "sigma_volume_floor_mean",
    "descent_volume_fraction_mean",
    "mean_log_contraction_descent_mean",
    "std_log_contraction_descent_mean",
]


def _normalize_variant_id(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y"}


def _to_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.map(_to_bool)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def _build_proxy_param_lookup(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str | None, dict[str, Any]]]:
    registry = build_default_registry()
    normalized = validate_and_normalize_config(config, known_methods=registry.method_ids())
    variants_by_method = expand_method_variants(normalized)

    defaults = dict(normalized.get("proxy_defaults", {}))
    lookup: dict[str | None, dict[str, Any]] = {}
    for variant in variants_by_method.get(PROXY_METHOD, []):
        variant_id = _normalize_variant_id(variant.get("variant_id"))
        merged = dict(defaults)
        merged.update(dict(variant.get("proxy_overrides", {})))
        lookup[variant_id] = merged

    if None not in lookup:
        lookup[None] = defaults

    return normalized, lookup


def _k_r_from_overrides(overrides: dict[str, Any]) -> tuple[float, float, float]:
    k = _safe_float(overrides.get("sigma_down_factor"))
    r = _safe_float(overrides.get("sigma_min_ratio"))
    if k <= 0.0 or np.isnan(k) or r <= 0.0 or np.isnan(r):
        return k, r, float("nan")
    return k, r, float(abs(np.log(k)) / r)


def _resolve_trace_path(results_dir: Path, trace_relpath: Any) -> Path | None:
    if pd.isna(trace_relpath):
        return None
    rel = str(trace_relpath).strip()
    if not rel:
        return None
    path = Path(rel)
    if not path.is_absolute():
        path = results_dir / path
    return path


def _trace_metrics(trace_df: pd.DataFrame, generations: int) -> dict[str, float]:
    required = {"generation", "sigma_before", "sigma_after", "at_floor"}
    missing = sorted(required.difference(trace_df.columns))
    if missing:
        raise ValueError(f"trace missing required columns: {missing}")

    ordered = trace_df.copy()
    ordered["generation"] = pd.to_numeric(ordered["generation"], errors="coerce")
    ordered["sigma_before"] = pd.to_numeric(ordered["sigma_before"], errors="coerce")
    ordered["sigma_after"] = pd.to_numeric(ordered["sigma_after"], errors="coerce")
    ordered["at_floor"] = _to_bool_series(ordered["at_floor"])
    ordered = ordered.dropna(subset=["generation"])
    ordered = ordered.sort_values("generation").reset_index(drop=True)

    if ordered.empty:
        return {
            "trace_rows": 0.0,
            "first_floor_gen_trace": float(generations),
            "floor_gens_trace": 0.0,
            "descent_gens_trace": float(generations),
            "sigma_volume_total": float("nan"),
            "sigma_volume_descent": float("nan"),
            "sigma_volume_floor": float("nan"),
            "descent_volume_fraction": float("nan"),
            "mean_log_contraction_descent": float("nan"),
            "std_log_contraction_descent": float("nan"),
        }

    floor_mask = ordered["at_floor"]
    if bool(floor_mask.any()):
        first_floor = int(ordered.loc[floor_mask, "generation"].min())
        descent_mask = ordered["generation"] < first_floor
    else:
        first_floor = int(generations)
        descent_mask = pd.Series(True, index=ordered.index)

    sigma_after = ordered["sigma_after"]
    sigma_total = float(sigma_after.sum(skipna=True))
    sigma_floor = float(sigma_after.where(floor_mask).sum(skipna=True))
    sigma_descent = float(sigma_total - sigma_floor)
    descent_fraction = float(sigma_descent / sigma_total) if sigma_total > 0.0 else float("nan")

    contraction_base = ordered.loc[descent_mask, "sigma_before"]
    contraction_next = ordered.loc[descent_mask, "sigma_after"]
    valid = (contraction_base > 0.0) & (contraction_next > 0.0)
    log_contraction = np.log((contraction_base[valid] / contraction_next[valid]).to_numpy(dtype=float))

    if log_contraction.size == 0:
        mean_log_contraction = float("nan")
        std_log_contraction = float("nan")
    else:
        mean_log_contraction = float(np.mean(log_contraction))
        std_log_contraction = float(np.std(log_contraction, ddof=0))

    return {
        "trace_rows": float(len(ordered)),
        "first_floor_gen_trace": float(first_floor),
        "floor_gens_trace": float(int(floor_mask.sum())),
        "descent_gens_trace": float(int(descent_mask.sum())),
        "sigma_volume_total": sigma_total,
        "sigma_volume_descent": sigma_descent,
        "sigma_volume_floor": sigma_floor,
        "descent_volume_fraction": descent_fraction,
        "mean_log_contraction_descent": mean_log_contraction,
        "std_log_contraction_descent": std_log_contraction,
    }


def _empty_trace_metrics(generations: int) -> dict[str, float]:
    return {
        "trace_rows": 0.0,
        "first_floor_gen_trace": float("nan"),
        "floor_gens_trace": float("nan"),
        "descent_gens_trace": float("nan"),
        "sigma_volume_total": float("nan"),
        "sigma_volume_descent": float("nan"),
        "sigma_volume_floor": float("nan"),
        "descent_volume_fraction": float("nan"),
        "mean_log_contraction_descent": float("nan"),
        "std_log_contraction_descent": float("nan"),
    }


def _aggregate_cell_metrics(run_metrics: pd.DataFrame) -> pd.DataFrame:
    if run_metrics.empty:
        return pd.DataFrame(columns=CELL_COLUMNS)

    group_cols = [
        "method",
        "variant_id",
        "method_instance",
        "function",
        "dimension",
        "noise_sigma",
        "k",
        "r",
        "descent_sharpness",
    ]
    rows: list[dict[str, Any]] = []
    for keys, group in run_metrics.groupby(group_cols, dropna=False):
        key_vals = dict(zip(group_cols, keys, strict=True))
        rows.append(
            {
                **key_vals,
                "n_runs": int(len(group)),
                "n_trace_available": int(group["trace_available"].sum()),
                "trace_coverage": float(group["trace_available"].mean()),
                "final_best_mean": float(group["final_best"].mean()),
                "final_best_median": float(group["final_best"].median()),
                "first_floor_gen_trace_mean": float(group["first_floor_gen_trace"].mean()),
                "floor_gens_trace_mean": float(group["floor_gens_trace"].mean()),
                "descent_gens_trace_mean": float(group["descent_gens_trace"].mean()),
                "sigma_volume_total_mean": float(group["sigma_volume_total"].mean()),
                "sigma_volume_descent_mean": float(group["sigma_volume_descent"].mean()),
                "sigma_volume_floor_mean": float(group["sigma_volume_floor"].mean()),
                "descent_volume_fraction_mean": float(group["descent_volume_fraction"].mean()),
                "mean_log_contraction_descent_mean": float(group["mean_log_contraction_descent"].mean()),
                "std_log_contraction_descent_mean": float(group["std_log_contraction_descent"].mean()),
            }
        )

    return pd.DataFrame(rows, columns=CELL_COLUMNS).sort_values(
        ["method_instance", "function", "dimension", "noise_sigma"]
    )


def _aggregate_variant_metrics(run_metrics: pd.DataFrame) -> pd.DataFrame:
    if run_metrics.empty:
        return pd.DataFrame(columns=VARIANT_COLUMNS)

    grouped = run_metrics.copy()
    grouped["cell_key"] = (
        grouped["function"].astype(str)
        + "::"
        + grouped["dimension"].astype(str)
        + "::"
        + grouped["noise_sigma"].astype(str)
    )

    group_cols = ["method", "variant_id", "method_instance", "k", "r", "descent_sharpness"]
    rows: list[dict[str, Any]] = []
    for keys, group in grouped.groupby(group_cols, dropna=False):
        key_vals = dict(zip(group_cols, keys, strict=True))
        rows.append(
            {
                **key_vals,
                "n_runs": int(len(group)),
                "n_cells_observed": int(group["cell_key"].nunique()),
                "n_trace_available": int(group["trace_available"].sum()),
                "trace_coverage": float(group["trace_available"].mean()),
                "final_best_mean": float(group["final_best"].mean()),
                "final_best_median": float(group["final_best"].median()),
                "first_floor_gen_trace_mean": float(group["first_floor_gen_trace"].mean()),
                "floor_gens_trace_mean": float(group["floor_gens_trace"].mean()),
                "descent_gens_trace_mean": float(group["descent_gens_trace"].mean()),
                "sigma_volume_total_mean": float(group["sigma_volume_total"].mean()),
                "sigma_volume_descent_mean": float(group["sigma_volume_descent"].mean()),
                "sigma_volume_floor_mean": float(group["sigma_volume_floor"].mean()),
                "descent_volume_fraction_mean": float(group["descent_volume_fraction"].mean()),
                "mean_log_contraction_descent_mean": float(group["mean_log_contraction_descent"].mean()),
                "std_log_contraction_descent_mean": float(group["std_log_contraction_descent"].mean()),
            }
        )

    return pd.DataFrame(rows, columns=VARIANT_COLUMNS).sort_values(["method_instance"])


def generate_descent_geometry_metrics(
    *,
    runs_csv: str | Path,
    config_path: str | Path,
    outdir: str | Path,
) -> dict[str, str]:
    runs_path = Path(runs_csv)
    runs_df = pd.read_csv(runs_path)
    results_dir = runs_path.parent

    config_raw = load_yaml_config(config_path)
    normalized, lookup = _build_proxy_param_lookup(config_raw)
    defaults = dict(normalized.get("proxy_defaults", {}))

    eval_proxy = runs_df[
        (runs_df["phase"] == "eval") & (runs_df["status"] == "ok") & (runs_df["method"] == PROXY_METHOD)
    ].copy()

    run_rows: list[dict[str, Any]] = []
    for _, row in eval_proxy.iterrows():
        variant_id = _normalize_variant_id(row.get("variant_id"))
        method_instance = str(row.get("method_instance"))
        overrides = dict(lookup.get(variant_id) or lookup.get(None) or defaults)
        k, r, sharpness = _k_r_from_overrides(overrides)

        generations = int(_safe_float(row.get("generations")))
        proxy_trace_written = _to_bool(row.get("proxy_trace_written"))
        trace_path = _resolve_trace_path(results_dir, row.get("proxy_trace_relpath"))

        trace_available = bool(proxy_trace_written and trace_path is not None and trace_path.is_file())
        trace_metrics = _empty_trace_metrics(generations)
        if trace_available:
            try:
                trace_df = pd.read_csv(trace_path)
                trace_metrics = _trace_metrics(trace_df, generations)
            except Exception:
                trace_available = False

        run_rows.append(
            {
                "method": str(row.get("method")),
                "variant_id": variant_id,
                "method_instance": method_instance,
                "function": str(row.get("function")),
                "dimension": int(row.get("dimension")),
                "noise_sigma": float(row.get("noise_sigma")),
                "seed": int(row.get("seed")),
                "generations": generations,
                "final_best": float(row.get("final_best")),
                "k": k,
                "r": r,
                "descent_sharpness": sharpness,
                "proxy_trace_written": proxy_trace_written,
                "trace_available": trace_available,
                "trace_path": str(trace_path) if trace_path is not None else "",
                **trace_metrics,
            }
        )

    run_metrics = pd.DataFrame(run_rows, columns=RUN_COLUMNS)
    cell_metrics = _aggregate_cell_metrics(run_metrics)
    variant_metrics = _aggregate_variant_metrics(run_metrics)

    output_dir = ensure_dir(outdir)
    run_csv = output_dir / "descent_run_metrics.csv"
    cell_csv = output_dir / "descent_cell_metrics.csv"
    variant_csv = output_dir / "descent_variant_metrics.csv"
    summary_json = output_dir / "descent_geometry_summary.json"

    save_csv(run_csv, run_metrics)
    save_csv(cell_csv, cell_metrics)
    save_csv(variant_csv, variant_metrics)

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_csv": str(runs_path),
        "config_path": str(config_path),
        "counts": {
            "n_eval_proxy_runs": int(len(run_metrics)),
            "n_trace_available_runs": int(run_metrics["trace_available"].sum()) if not run_metrics.empty else 0,
            "trace_coverage": float(run_metrics["trace_available"].mean()) if not run_metrics.empty else 0.0,
            "n_variants": int(variant_metrics["method_instance"].nunique()) if not variant_metrics.empty else 0,
            "n_cells": int(cell_metrics[["function", "dimension", "noise_sigma"]].drop_duplicates().shape[0])
            if not cell_metrics.empty
            else 0,
        },
        "files": {
            "descent_run_metrics_csv": str(run_csv),
            "descent_cell_metrics_csv": str(cell_csv),
            "descent_variant_metrics_csv": str(variant_csv),
            "descent_geometry_summary_json": str(summary_json),
        },
    }
    save_json(summary_json, summary)

    return {
        "descent_run_metrics_csv": str(run_csv),
        "descent_cell_metrics_csv": str(cell_csv),
        "descent_variant_metrics_csv": str(variant_csv),
        "descent_geometry_summary_json": str(summary_json),
    }

