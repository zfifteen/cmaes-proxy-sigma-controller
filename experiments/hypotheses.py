from __future__ import annotations

import json
import operator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from .io import ensure_dir, load_yaml_config, parse_hypotheses_args, save_json
from .stats import compute_correlation


_OPS: dict[str, Callable[[float, float], bool]] = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}


def _apply_where(df: pd.DataFrame, where: dict[str, Any] | None) -> pd.DataFrame:
    if not where:
        return df
    filtered = df
    for key, value in where.items():
        if key not in filtered.columns:
            raise ValueError(f"where filter references unknown column: {key}")
        if isinstance(value, list):
            filtered = filtered[filtered[key].isin(value)]
        else:
            filtered = filtered[filtered[key] == value]
    return filtered


def _aggregate(series: pd.Series, agg: str) -> float:
    values = series.dropna()
    if values.empty:
        raise ValueError("No rows available after filtering")
    if agg == "mean":
        return float(values.mean())
    if agg == "median":
        return float(values.median())
    if agg == "min":
        return float(values.min())
    if agg == "max":
        return float(values.max())
    if agg == "first":
        return float(values.iloc[0])
    raise ValueError(f"Unsupported aggregate: {agg}")


def _evaluate_metric_threshold(check: dict[str, Any], datasets: dict[str, pd.DataFrame]) -> dict[str, Any]:
    dataset_name = str(check["dataset"])
    metric = str(check["metric"])
    agg = str(check.get("aggregate", "mean"))
    op_name = str(check["op"])
    threshold = float(check["threshold"])

    if dataset_name not in datasets:
        raise ValueError(f"Unknown dataset: {dataset_name}")
    df = _apply_where(datasets[dataset_name], check.get("where"))
    if metric not in df.columns:
        raise ValueError(f"Metric not found in dataset {dataset_name}: {metric}")

    value = _aggregate(pd.to_numeric(df[metric], errors="coerce"), agg)
    comparator = _OPS.get(op_name)
    if comparator is None:
        raise ValueError(f"Unsupported operator: {op_name}")
    passed = bool(comparator(value, threshold))

    return {
        "value": value,
        "threshold": threshold,
        "op": op_name,
        "aggregate": agg,
        "n_rows": int(len(df)),
        "passed": passed,
    }


def _evaluate_correlation_threshold(check: dict[str, Any], datasets: dict[str, pd.DataFrame]) -> dict[str, Any]:
    dataset_name = str(check["dataset"])
    x_metric = str(check.get("x_metric", check.get("x")))
    y_metric = str(check.get("y_metric", check.get("y")))
    corr_method = str(check.get("method", "pearson"))
    op_name = str(check["op"])
    threshold = float(check["threshold"])
    min_samples = int(check.get("min_samples", 3))

    if dataset_name not in datasets:
        raise ValueError(f"Unknown dataset: {dataset_name}")
    df = _apply_where(datasets[dataset_name], check.get("where"))

    if x_metric not in df.columns or y_metric not in df.columns:
        raise ValueError(f"Correlation metrics not found: {x_metric}, {y_metric}")

    x = pd.to_numeric(df[x_metric], errors="coerce")
    y = pd.to_numeric(df[y_metric], errors="coerce")
    valid = x.notna() & y.notna()
    n_samples = int(valid.sum())
    if n_samples < min_samples:
        raise ValueError(
            f"Not enough samples for correlation check: n={n_samples}, min_samples={min_samples}"
        )

    corr = compute_correlation(x[valid], y[valid], method=corr_method)
    comparator = _OPS.get(op_name)
    if comparator is None:
        raise ValueError(f"Unsupported operator: {op_name}")
    passed = bool(comparator(corr, threshold))

    return {
        "value": corr,
        "threshold": threshold,
        "op": op_name,
        "method": corr_method,
        "n_rows": int(len(df)),
        "n_samples": n_samples,
        "passed": passed,
    }


def _evaluate_comparative_threshold(check: dict[str, Any], datasets: dict[str, pd.DataFrame]) -> dict[str, Any]:
    dataset_name = str(check["dataset"])
    metric = str(check["metric"])
    agg = str(check.get("aggregate", "mean"))
    op_name = str(check["op"])
    threshold = float(check["threshold"])

    if dataset_name not in datasets:
        raise ValueError(f"Unknown dataset: {dataset_name}")
    df = datasets[dataset_name]

    lhs_where = check.get("lhs_where")
    rhs_where = check.get("rhs_where")
    if not isinstance(lhs_where, dict) or not isinstance(rhs_where, dict):
        raise ValueError("comparative_threshold requires lhs_where and rhs_where mappings")

    lhs = _apply_where(df, lhs_where)
    rhs = _apply_where(df, rhs_where)
    if metric not in lhs.columns or metric not in rhs.columns:
        raise ValueError(f"Metric not found in dataset {dataset_name}: {metric}")

    lhs_value = _aggregate(pd.to_numeric(lhs[metric], errors="coerce"), agg)
    rhs_value = _aggregate(pd.to_numeric(rhs[metric], errors="coerce"), agg)
    value = lhs_value - rhs_value

    comparator = _OPS.get(op_name)
    if comparator is None:
        raise ValueError(f"Unsupported operator: {op_name}")
    passed = bool(comparator(value, threshold))

    return {
        "value": value,
        "lhs_value": lhs_value,
        "rhs_value": rhs_value,
        "threshold": threshold,
        "op": op_name,
        "aggregate": agg,
        "lhs_n_rows": int(len(lhs)),
        "rhs_n_rows": int(len(rhs)),
        "passed": passed,
    }


def run_hypothesis_checks(
    *,
    runs_csv: str | Path,
    cell_stats_csv: str | Path,
    method_aggregate_csv: str | Path,
    config_path: str | Path,
    outdir: str | Path,
    behavior_aggregate_csv: str | Path | None = None,
) -> dict[str, str]:
    config = load_yaml_config(config_path)
    checks = list(config.get("hypotheses", {}).get("checks", []))

    datasets = {
        "runs_long": pd.read_csv(runs_csv),
        "cell_stats": pd.read_csv(cell_stats_csv),
        "method_aggregate": pd.read_csv(method_aggregate_csv),
    }
    if behavior_aggregate_csv:
        datasets["behavior_aggregate"] = pd.read_csv(behavior_aggregate_csv)

    results: list[dict[str, Any]] = []
    for idx, check in enumerate(checks):
        check_id = str(check.get("id", f"check_{idx + 1}"))
        check_type = str(check.get("type", ""))
        base = {
            "id": check_id,
            "type": check_type,
        }

        try:
            if check_type == "metric_threshold":
                outcome = _evaluate_metric_threshold(check, datasets)
            elif check_type == "correlation_threshold":
                outcome = _evaluate_correlation_threshold(check, datasets)
            elif check_type == "comparative_threshold":
                outcome = _evaluate_comparative_threshold(check, datasets)
            else:
                raise ValueError(f"Unsupported hypothesis check type: {check_type}")
            results.append(
                {
                    **base,
                    "status": "ok",
                    **outcome,
                }
            )
        except Exception as exc:
            results.append(
                {
                    **base,
                    "status": "error",
                    "passed": False,
                    "error": str(exc),
                }
            )

    n_checks = len(results)
    n_passed = int(sum(1 for item in results if item.get("status") == "ok" and bool(item.get("passed"))))
    n_failed = int(sum(1 for item in results if item.get("status") == "ok" and not bool(item.get("passed"))))
    n_errors = int(sum(1 for item in results if item.get("status") == "error"))

    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path),
        "summary": {
            "n_checks": n_checks,
            "n_passed": n_passed,
            "n_failed": n_failed,
            "n_errors": n_errors,
        },
        "checks": results,
    }

    out_path = ensure_dir(outdir)
    result_path = out_path / "hypothesis_checks.json"
    save_json(result_path, payload)

    return {
        "hypothesis_checks_json": str(result_path),
    }


def main() -> None:
    args = parse_hypotheses_args()
    outputs = run_hypothesis_checks(
        runs_csv=args.runs,
        cell_stats_csv=args.cell_stats,
        method_aggregate_csv=args.method_aggregate,
        behavior_aggregate_csv=args.behavior_aggregate,
        config_path=args.config,
        outdir=args.outdir,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
