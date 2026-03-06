#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CONFIG_PATH="experiments/config/high_rigor.yaml"
RUN_ID="${RUN_ID:-}"

if [[ -z "$RUN_ID" ]]; then
  RUN_ID="$(python3 - <<'PY'
from experiments.io import load_yaml_config, make_run_id, stable_config_hash
cfg = load_yaml_config('experiments/config/high_rigor.yaml')
print(make_run_id(stable_config_hash(cfg)))
PY
)"
fi

RUN_ROOT="artifacts/runs/high-rigor/${RUN_ID}"
RESULTS_DIR="${RUN_ROOT}/results"
FIG_DIR="${RUN_ROOT}/figures"

if [[ -e "$RUN_ROOT" ]]; then
  echo "[high-rigor] ERROR: run root already exists: $RUN_ROOT" >&2
  exit 1
fi

mkdir -p "$RESULTS_DIR" "$FIG_DIR"

python3 -m experiments.run \
  --config "$CONFIG_PATH" \
  --outdir "$RESULTS_DIR" \
  --workers 1 \
  --run-id "$RUN_ID"

python3 -m experiments.analyze \
  --runs "$RESULTS_DIR/runs_long.csv" \
  --outdir "$RESULTS_DIR" \
  --figdir "$FIG_DIR" \
  --manifest-json "$RESULTS_DIR/manifest.json"

PAIRWISE_A="$(python3 - <<'PY'
from experiments.io import load_yaml_config
cfg = load_yaml_config('experiments/config/high_rigor.yaml')
print(cfg.get('analysis', {}).get('default_pairwise', {}).get('method_a', ''))
PY
)"
PAIRWISE_B="$(python3 - <<'PY'
from experiments.io import load_yaml_config
cfg = load_yaml_config('experiments/config/high_rigor.yaml')
print(cfg.get('analysis', {}).get('default_pairwise', {}).get('method_b', ''))
PY
)"

if [[ -n "$PAIRWISE_A" && -n "$PAIRWISE_B" ]]; then
  python3 -m experiments.pairwise \
    --runs "$RESULTS_DIR/runs_long.csv" \
    --method-a "$PAIRWISE_A" \
    --method-b "$PAIRWISE_B" \
    --outdir "$RESULTS_DIR" \
    --manifest-json "$RESULTS_DIR/manifest.json" \
    --analysis-manifest "$RESULTS_DIR/analysis_manifest.json"
fi

python3 -m experiments.hypotheses \
  --runs "$RESULTS_DIR/runs_long.csv" \
  --cell-stats "$RESULTS_DIR/cell_stats.csv" \
  --method-aggregate "$RESULTS_DIR/method_aggregate.csv" \
  --behavior-aggregate "$RESULTS_DIR/behavior_aggregate.csv" \
  --config "$CONFIG_PATH" \
  --outdir "$RESULTS_DIR"

python3 -m experiments.findings \
  --results-dir "$RESULTS_DIR" \
  --figdir "$FIG_DIR"

python3 scripts/verify_experiment_artifacts.py \
  --results-dir "$RESULTS_DIR" \
  --figdir "$FIG_DIR" \
  --config "$CONFIG_PATH" \
  --require-pairwise

echo "[high-rigor] run_id=$RUN_ID"
echo "[high-rigor] run_root=$RUN_ROOT"
