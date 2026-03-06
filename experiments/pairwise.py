from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .io import ensure_dir, load_json, parse_pairwise_args, sanitize_token, save_csv, save_json
from .stats import compute_pairwise_cell_stats


def _quantiles(series: pd.Series) -> dict[str, float]:
    if series.empty:
        return {}
    values = series.quantile([0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0])
    return {f"{k:.2f}": float(v) for k, v in values.items()}


def _build_prefix(method_a: str, method_b: str) -> str:
    return f"pairwise_{sanitize_token(method_b)}_vs_{sanitize_token(method_a)}"


def _top_rows(pairwise_df: pd.DataFrame, *, ascending: bool, n: int = 5) -> list[dict[str, Any]]:
    if pairwise_df.empty:
        return []
    cols = [
        "function",
        "dimension",
        "noise_sigma",
        "median_delta_b_minus_a",
        "wilcoxon_p_two_sided",
        "bh_fdr_q_value",
    ]
    ranked = pairwise_df.sort_values("median_delta_b_minus_a", ascending=ascending).head(n)
    return ranked[cols].to_dict(orient="records")


def generate_pairwise_artifacts(
    runs_csv: str | Path,
    *,
    method_a: str,
    method_b: str,
    outdir: str | Path,
    output_prefix: str | None = None,
    manifest_json_path: str | Path | None = None,
    analysis_manifest_path: str | Path | None = None,
) -> dict[str, str]:
    out_path = ensure_dir(outdir)
    runs_df = pd.read_csv(runs_csv)

    pairwise_df = compute_pairwise_cell_stats(runs_df, method_a=method_a, method_b=method_b)
    if output_prefix is None:
        output_prefix = _build_prefix(method_a, method_b)

    csv_path = out_path / f"{output_prefix}.csv"
    json_path = out_path / f"{output_prefix}.json"

    save_csv(csv_path, pairwise_df)

    run_id = "unknown"
    if manifest_json_path:
        manifest = load_json(manifest_json_path)
        run_id = str(manifest.get("run_id", "unknown"))

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "method_a": method_a,
        "method_b": method_b,
        "n_cells": int(len(pairwise_df)),
        "n_q_lt_0_05": int((pairwise_df["bh_fdr_q_value"] < 0.05).sum()) if not pairwise_df.empty else 0,
        "n_p_lt_0_05": int((pairwise_df["wilcoxon_p_two_sided"] < 0.05).sum()) if not pairwise_df.empty else 0,
        "n_b_better": int((pairwise_df["median_delta_b_minus_a"] < 0.0).sum()) if not pairwise_df.empty else 0,
        "n_a_better": int((pairwise_df["median_delta_b_minus_a"] > 0.0).sum()) if not pairwise_df.empty else 0,
        "median_of_cell_median_delta_b_minus_a": (
            float(pairwise_df["median_delta_b_minus_a"].median()) if not pairwise_df.empty else float("nan")
        ),
        "delta_quantiles_b_minus_a": _quantiles(pairwise_df["median_delta_b_minus_a"]) if not pairwise_df.empty else {},
        "top_b_better_cells": _top_rows(pairwise_df, ascending=True),
        "top_a_better_cells": _top_rows(pairwise_df, ascending=False),
        "pairwise_csv": str(csv_path),
        "pairwise_json": str(json_path),
    }
    save_json(json_path, summary)

    if analysis_manifest_path:
        analysis_manifest = load_json(analysis_manifest_path)
        files = dict(analysis_manifest.get("files", {}))
        files[f"{output_prefix}_csv"] = str(csv_path)
        files[f"{output_prefix}_json"] = str(json_path)
        analysis_manifest["files"] = files
        analysis_manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(analysis_manifest_path, analysis_manifest)

    return {
        "pairwise_csv": str(csv_path),
        "pairwise_json": str(json_path),
    }


def main() -> None:
    args = parse_pairwise_args()
    outputs = generate_pairwise_artifacts(
        runs_csv=args.runs,
        method_a=args.method_a,
        method_b=args.method_b,
        outdir=args.outdir,
        output_prefix=args.output_prefix,
        manifest_json_path=args.manifest_json,
        analysis_manifest_path=args.analysis_manifest,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
