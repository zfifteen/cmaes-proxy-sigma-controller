#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi
if [[ "$#" -ne 0 ]]; then
  echo "[suite] ERROR: unsupported arguments: $*" >&2
  echo "[suite] Usage: bash scripts/run_descent_geometry_suite.sh [--dry-run]" >&2
  exit 1
fi

RUN_BASE="${DESCENT_GEOM_RUN_BASE:-artifacts/runs/descent-geometry}"

DENSE_CONFIG="${DESCENT_GEOM_DENSE_CONFIG:-experiments/config/descent_geom_dense_hybrid.yaml}"
INTERACTION_CONFIG="${DESCENT_GEOM_INTERACTION_CONFIG:-experiments/config/descent_geom_interaction_hybrid.yaml}"
ANCHORS_CONFIG="${DESCENT_GEOM_ANCHORS_CONFIG:-experiments/config/descent_geom_anchors_full.yaml}"

DENSE_RUN_ID="${DESCENT_GEOM_DENSE_RUN_ID:-}"
INTERACTION_RUN_ID="${DESCENT_GEOM_INTERACTION_RUN_ID:-}"
ANCHORS_RUN_ID="${DESCENT_GEOM_ANCHORS_RUN_ID:-}"

RECORDS_FILE="$(mktemp)"
cleanup() {
  rm -f "$RECORDS_FILE"
}
trap cleanup EXIT

resolve_run_id() {
  local config_path="$1"
  python3 - <<PY
from experiments.io import load_yaml_config, make_run_id, stable_config_hash
cfg = load_yaml_config("$config_path")
print(make_run_id(stable_config_hash(cfg)))
PY
}

append_record() {
  local stage="$1"
  local config_path="$2"
  local run_id="$3"
  local run_root="$4"
  local results_dir="$5"
  local fig_dir="$6"
  local status="$7"
  python3 - <<PY >> "$RECORDS_FILE"
import json
print(json.dumps({
    "stage": "$stage",
    "config_path": "$config_path",
    "run_id": "$run_id",
    "run_root": "$run_root",
    "results_dir": "$results_dir",
    "figures_dir": "$fig_dir",
    "status": "$status",
}))
PY
}

run_or_echo() {
  local stage="$1"
  shift
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[suite][dry-run][%s] ' "$stage"
    printf '%q ' "$@"
    echo
  else
    "$@"
  fi
}

run_stage() {
  local stage="$1"
  local stage_dir="$2"
  local config_path="$3"
  local run_id_override="$4"

  if [[ ! -f "$config_path" ]]; then
    echo "[suite] ERROR: missing config for stage=$stage: $config_path" >&2
    exit 1
  fi

  local run_id="$run_id_override"
  if [[ -z "$run_id" ]]; then
    run_id="$(resolve_run_id "$config_path")"
  fi

  local run_root="${RUN_BASE}/${stage_dir}/${run_id}"
  local results_dir="${run_root}/results"
  local fig_dir="${run_root}/figures"

  echo "[suite] stage=${stage} config=${config_path}"
  echo "[suite] stage=${stage} run_id=${run_id}"
  echo "[suite] stage=${stage} run_root=${run_root}"

  if [[ "$DRY_RUN" -eq 0 && -e "$run_root" ]]; then
    echo "[suite] ERROR: run root already exists for stage=${stage}: ${run_root}" >&2
    exit 1
  fi

  if [[ "$DRY_RUN" -eq 0 ]]; then
    mkdir -p "$results_dir" "$fig_dir"
  fi

  run_or_echo "$stage" python3 -m experiments.run \
    --config "$config_path" \
    --outdir "$results_dir" \
    --workers 1 \
    --run-id "$run_id"

  run_or_echo "$stage" python3 -m experiments.analyze \
    --runs "$results_dir/runs_long.csv" \
    --outdir "$results_dir" \
    --figdir "$fig_dir" \
    --manifest-json "$results_dir/manifest.json"

  local pairwise_a
  local pairwise_b
  pairwise_a="$(python3 - <<PY
from experiments.io import load_yaml_config
cfg = load_yaml_config("$config_path")
print(cfg.get("analysis", {}).get("default_pairwise", {}).get("method_a", ""))
PY
)"
  pairwise_b="$(python3 - <<PY
from experiments.io import load_yaml_config
cfg = load_yaml_config("$config_path")
print(cfg.get("analysis", {}).get("default_pairwise", {}).get("method_b", ""))
PY
)"
  if [[ -n "$pairwise_a" && -n "$pairwise_b" ]]; then
    run_or_echo "$stage" python3 -m experiments.pairwise \
      --runs "$results_dir/runs_long.csv" \
      --method-a "$pairwise_a" \
      --method-b "$pairwise_b" \
      --outdir "$results_dir" \
      --manifest-json "$results_dir/manifest.json" \
      --analysis-manifest "$results_dir/analysis_manifest.json"
  fi

  run_or_echo "$stage" python3 -m experiments.hypotheses \
    --runs "$results_dir/runs_long.csv" \
    --cell-stats "$results_dir/cell_stats.csv" \
    --method-aggregate "$results_dir/method_aggregate.csv" \
    --behavior-aggregate "$results_dir/behavior_aggregate.csv" \
    --config "$config_path" \
    --outdir "$results_dir"

  run_or_echo "$stage" python3 -m experiments.findings \
    --results-dir "$results_dir" \
    --figdir "$fig_dir"

  run_or_echo "$stage" python3 scripts/analyze_descent_geometry_metrics.py \
    --runs "$results_dir/runs_long.csv" \
    --config "$config_path" \
    --outdir "$results_dir"

  run_or_echo "$stage" python3 scripts/verify_experiment_artifacts.py \
    --results-dir "$results_dir" \
    --figdir "$fig_dir" \
    --config "$config_path" \
    --require-pairwise

  if [[ "$DRY_RUN" -eq 0 && ! -f "$results_dir/descent_variant_metrics.csv" ]]; then
    echo "[suite] ERROR: missing descent_variant_metrics.csv for stage=${stage}" >&2
    exit 1
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    append_record "$stage" "$config_path" "$run_id" "$run_root" "$results_dir" "$fig_dir" "dry_run"
  else
    append_record "$stage" "$config_path" "$run_id" "$run_root" "$results_dir" "$fig_dir" "ok"
  fi
}

run_stage "dense" "dense" "$DENSE_CONFIG" "$DENSE_RUN_ID"
run_stage "interaction" "interaction" "$INTERACTION_CONFIG" "$INTERACTION_RUN_ID"
run_stage "anchors_full" "anchors-full" "$ANCHORS_CONFIG" "$ANCHORS_RUN_ID"

mkdir -p "$RUN_BASE"
MANIFEST_PATH="${RUN_BASE}/suite_manifest.json"
python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

records_path = Path("$RECORDS_FILE")
records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
payload = {
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "dry_run": bool($DRY_RUN),
    "run_base": "$RUN_BASE",
    "stages": records,
}
Path("$MANIFEST_PATH").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
print(json.dumps({"suite_manifest_json": "$MANIFEST_PATH"}, indent=2, sort_keys=True))
PY

echo "[suite] completed"

