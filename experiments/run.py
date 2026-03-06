from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .config import build_cells, expand_method_variants, validate_and_normalize_config
from .io import ensure_dir, load_yaml_config, make_run_id, parse_run_args, save_csv, save_json, stable_config_hash
from .methods import MethodRegistry, build_default_registry, run_experiment_job


def _git_commit_short() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _resolve_workers(config: dict[str, Any], workers_override: int | None) -> int:
    workers = int(workers_override if workers_override is not None else config["runtime"]["parallel_workers"])
    if workers != 1:
        raise ValueError("v1 pipeline is sequential-only; set workers to 1")
    return workers


def _build_jobs(config: dict[str, Any], registry: MethodRegistry) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    cells = build_cells(config["matrix"])
    seeds = list(config["seeds"]["eval"])
    variants_by_method = expand_method_variants(config)

    for method_id in config["methods"]:
        method_def = registry.get(method_id)
        for variant in variants_by_method[method_id]:
            variant_id = variant["variant_id"]
            proxy_config = dict(config["proxy_defaults"])
            if method_def.uses_proxy:
                proxy_config.update(variant["proxy_overrides"])
            for cell in cells:
                for seed in seeds:
                    jobs.append(
                        {
                            "phase": "eval",
                            "method_id": method_id,
                            "variant_id": variant_id,
                            "reference_method": config["reference_method"],
                            "function": cell["function"],
                            "dimension": int(cell["dimension"]),
                            "noise_sigma": float(cell["noise_sigma"]),
                            "seed": int(seed),
                            "eval_budget": int(config["budget"]["evals_per_run"]),
                            "initial_sigma": float(config["cma"]["initial_sigma"]),
                            "base_popsize": int(config["cma"]["base_popsize"]),
                            "cma_verbose": int(config["cma"].get("verbose", -9)),
                            "proxy_config": proxy_config,
                            "trace_mode": str(config["telemetry"]["proxy_trace_mode"]),
                        }
                    )
    return jobs


def execute_pipeline(
    config_path: str | Path,
    outdir: str | Path,
    workers_override: int | None = None,
    explicit_run_id: str | None = None,
) -> dict[str, str]:
    registry = build_default_registry()
    config_raw = load_yaml_config(config_path)
    config = validate_and_normalize_config(config_raw, known_methods=registry.method_ids())

    workers = _resolve_workers(config, workers_override)
    out_path = ensure_dir(outdir)
    created_at = datetime.now(timezone.utc)
    config_hash = stable_config_hash(config)
    run_id = explicit_run_id or make_run_id(config_hash, created_at)

    trace_root = out_path / "proxy_traces"
    jobs = _build_jobs(config, registry)

    rows = [run_experiment_job(job, registry=registry, trace_root=trace_root) for job in jobs]
    runs_df = pd.DataFrame(rows)
    runs_df.insert(0, "run_index", range(1, len(runs_df) + 1))

    runs_path = out_path / "runs_long.csv"
    manifest_path = out_path / "manifest.json"

    save_csv(runs_path, runs_df)

    status_by_phase = (
        runs_df.groupby(["phase", "status"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["phase", "status"])
        .to_dict(orient="records")
    )

    manifest = {
        "run_id": run_id,
        "run_scope": str(config.get("experiment_name", "experiment")),
        "created_at_utc": created_at.isoformat(),
        "config_path": str(Path(config_path)),
        "config_hash": config_hash,
        "git_commit": _git_commit_short(),
        "workers": workers,
        "reference_method": config["reference_method"],
        "methods": list(config["methods"]),
        "files": {
            "runs_long_csv": str(runs_path),
            "manifest_json": str(manifest_path),
        },
        "counts": {
            "total_runs": int(len(runs_df)),
            "status_by_phase": status_by_phase,
            "n_methods": int(len(config["methods"])),
            "n_cells": int(len(build_cells(config["matrix"]))),
            "n_eval_seeds": int(len(config["seeds"]["eval"])),
        },
        "notes": {
            "execution_mode": "sequential_only_v1",
            "fairness_mode": "equal_eval_budget",
        },
    }
    save_json(manifest_path, manifest)

    return {
        "run_id": run_id,
        "runs_long_csv": str(runs_path),
        "manifest_json": str(manifest_path),
    }


def main() -> None:
    args = parse_run_args()
    outputs = execute_pipeline(args.config, args.outdir, args.workers, args.run_id)
    print(json.dumps(outputs, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
