from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_yaml_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {config_path}")
    return data


def load_json(path: str | Path) -> dict[str, Any]:
    in_path = Path(path)
    with in_path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON must decode to object: {in_path}")
    return payload


def save_json(path: str | Path, payload: dict[str, Any]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)


def save_csv(path: str | Path, df: pd.DataFrame) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)


def ensure_dir(path: str | Path) -> Path:
    out_path = Path(path)
    out_path.mkdir(parents=True, exist_ok=True)
    return out_path


def stable_config_hash(config: dict[str, Any]) -> str:
    serialized = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def make_run_id(config_hash: str, now_utc: dt.datetime | None = None) -> str:
    ts = (now_utc or dt.datetime.now(dt.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}-{config_hash[:8]}"


def sanitize_token(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text)


def parse_run_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repo-local CMA-ES experiment pipeline.")
    parser.add_argument("--config", required=True, help="Path to YAML config")
    parser.add_argument("--outdir", required=True, help="Directory for run artifacts")
    parser.add_argument("--workers", type=int, default=None, help="Optional worker override (v1 must be 1)")
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional explicit run identifier (default: UTC timestamp + config hash)",
    )
    return parser.parse_args()


def parse_analyze_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze experiment runs and emit tables/figures.")
    parser.add_argument("--runs", required=True, help="Path to runs_long.csv")
    parser.add_argument("--outdir", required=True, help="Directory for analysis artifacts")
    parser.add_argument("--figdir", default=None, help="Directory for figures (defaults to outdir)")
    parser.add_argument(
        "--reference-method",
        default=None,
        help="Optional reference method_instance override (default from runs_long if present)",
    )
    parser.add_argument(
        "--manifest-json",
        default=None,
        help="Optional run manifest path for metadata propagation",
    )
    return parser.parse_args()


def parse_pairwise_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute pairwise method comparison artifacts.")
    parser.add_argument("--runs", required=True, help="Path to runs_long.csv")
    parser.add_argument("--method-a", required=True, help="Method instance A (reference)")
    parser.add_argument("--method-b", required=True, help="Method instance B (compared)")
    parser.add_argument("--outdir", required=True, help="Directory for pairwise outputs")
    parser.add_argument(
        "--output-prefix",
        default=None,
        help="Optional explicit output prefix; default is derived from methods",
    )
    parser.add_argument(
        "--manifest-json",
        default=None,
        help="Optional run manifest path for run metadata",
    )
    parser.add_argument(
        "--analysis-manifest",
        default=None,
        help="Optional analysis manifest path to update with pairwise artifact links",
    )
    return parser.parse_args()


def parse_hypotheses_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate configured hypothesis checks against analysis artifacts.")
    parser.add_argument("--runs", required=True, help="Path to runs_long.csv")
    parser.add_argument("--cell-stats", required=True, help="Path to cell_stats.csv")
    parser.add_argument("--method-aggregate", required=True, help="Path to method_aggregate.csv")
    parser.add_argument(
        "--behavior-aggregate",
        default=None,
        help="Optional behavior_aggregate.csv path",
    )
    parser.add_argument("--config", required=True, help="Path to YAML config (for hypotheses.checks)")
    parser.add_argument("--outdir", required=True, help="Directory for hypothesis outputs")
    return parser.parse_args()


def parse_findings_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate findings summary artifacts for a run output directory.")
    parser.add_argument("--results-dir", required=True, help="Directory containing run + analysis artifacts")
    parser.add_argument("--figdir", required=True, help="Directory containing analysis plots")
    return parser.parse_args()
