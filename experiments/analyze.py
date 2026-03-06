from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .io import ensure_dir, load_json, parse_analyze_args, save_csv, save_json
from .plots import (
    plot_behavior_fraction_at_floor,
    plot_behavior_time_to_first_floor,
    plot_method_median_delta,
    plot_method_win_rate,
)
from .stats import compute_behavior_aggregate, compute_cell_stats, compute_method_aggregate


def analyze_runs(
    runs_csv: str | Path,
    outdir: str | Path,
    *,
    figdir: str | Path | None = None,
    reference_method: str | None = None,
    manifest_json: str | Path | None = None,
) -> dict[str, str]:
    runs_path = Path(runs_csv)
    out_path = ensure_dir(outdir)
    fig_path = ensure_dir(figdir if figdir is not None else out_path)

    manifest: dict[str, Any] | None = load_json(manifest_json) if manifest_json else None
    if reference_method is None and manifest is not None:
        reference_method = manifest.get("reference_method")

    runs_df = pd.read_csv(runs_path)

    cell_stats, resolved_reference = compute_cell_stats(runs_df, reference_method)
    method_agg = compute_method_aggregate(cell_stats)
    behavior_agg = compute_behavior_aggregate(runs_df)

    cell_stats_path = out_path / "cell_stats.csv"
    method_agg_path = out_path / "method_aggregate.csv"
    behavior_agg_path = out_path / "behavior_aggregate.csv"
    analysis_manifest_path = out_path / "analysis_manifest.json"

    save_csv(cell_stats_path, cell_stats)
    save_csv(method_agg_path, method_agg)
    save_csv(behavior_agg_path, behavior_agg)

    fig_delta = fig_path / "method_median_delta_bar.png"
    fig_win = fig_path / "method_win_rate_bar.png"
    fig_floor = fig_path / "behavior_fraction_at_floor_bar.png"
    fig_ttf = fig_path / "behavior_time_to_first_floor_bar.png"

    plot_method_median_delta(method_agg, fig_delta)
    plot_method_win_rate(method_agg, fig_win)
    plot_behavior_fraction_at_floor(behavior_agg, fig_floor)
    plot_behavior_time_to_first_floor(behavior_agg, fig_ttf)

    analysis_manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_csv": str(runs_path),
        "run_id": manifest.get("run_id") if manifest else None,
        "manifest_json": str(manifest_json) if manifest_json else None,
        "reference_method_instance": resolved_reference,
        "files": {
            "cell_stats_csv": str(cell_stats_path),
            "method_aggregate_csv": str(method_agg_path),
            "behavior_aggregate_csv": str(behavior_agg_path),
            "figure_method_delta": str(fig_delta),
            "figure_method_win_rate": str(fig_win),
            "figure_behavior_floor": str(fig_floor),
            "figure_behavior_ttf": str(fig_ttf),
        },
        "summary": {
            "n_eval_rows": int(len(runs_df[(runs_df["phase"] == "eval") & (runs_df["status"] == "ok")])),
            "n_cell_rows": int(len(cell_stats)),
            "n_methods": int(method_agg["method_instance"].nunique()) if not method_agg.empty else 0,
            "n_behavior_rows": int(len(behavior_agg)),
            "n_significant_q_lt_005": int((cell_stats["bh_fdr_q_value"] < 0.05).sum()) if not cell_stats.empty else 0,
        },
    }
    save_json(analysis_manifest_path, analysis_manifest)

    return {
        "cell_stats_csv": str(cell_stats_path),
        "method_aggregate_csv": str(method_agg_path),
        "behavior_aggregate_csv": str(behavior_agg_path),
        "analysis_manifest_json": str(analysis_manifest_path),
        "figure_method_delta": str(fig_delta),
        "figure_method_win_rate": str(fig_win),
        "figure_behavior_floor": str(fig_floor),
        "figure_behavior_ttf": str(fig_ttf),
    }


def main() -> None:
    args = parse_analyze_args()
    outputs = analyze_runs(
        runs_csv=args.runs,
        outdir=args.outdir,
        figdir=args.figdir,
        reference_method=args.reference_method,
        manifest_json=args.manifest_json,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
