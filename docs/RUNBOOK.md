# RUNBOOK

## Environment

```bash
cd /Users/velocityworks/IdeaProjects/cmaes-proxy-sigma-controller
python -m pip install -e '.[dev,pycma,experiments]'
```

## Test Gates

Run full gate suite:

```bash
pytest
```

Coverage is enforced at `>= 90%` on `src/cmaes_proxy_sigma_controller`.

## Reference Smoke

```bash
python - <<'PY'
from cmaes_proxy_sigma_controller.reference_runner import run_reference
from cmaes_proxy_sigma_controller.types import ControllerConfig

row_v = run_reference(
    method="vanilla",
    function_name="sphere",
    dimension=10,
    seed=0,
    noise_sigma=0.1,
    initial_sigma=0.5,
    popsize=10,
    planned_generations=10,
)
row_p = run_reference(
    method="proxy",
    function_name="sphere",
    dimension=10,
    seed=0,
    noise_sigma=0.1,
    initial_sigma=0.5,
    popsize=10,
    planned_generations=10,
    controller_config=ControllerConfig(),
)
print(row_v["method"], row_v["final_best"])
print(row_p["method"], row_p["final_best"], row_p["proxy_schema_version"])
PY
```

## Reproducibility Tiers

- Tier A: same-runtime strict replay (required gate)
- Tier B: cross-runtime tolerance checks (reporting gate)

## Schema

- `proxy_schema_version` is major-only and currently `1`.
- additive optional telemetry changes do not bump schema integer.

## Experiment Pipeline

Run wrappers:

```bash
bash scripts/run_smoke_pipeline.sh
bash scripts/run_high_rigor_pipeline.sh
bash scripts/run_sensitivity_pipeline.sh
```

Manual entrypoints:

```bash
python -m experiments.run --config experiments/config/smoke.yaml --outdir artifacts/runs/smoke/<RUN_ID>/results --workers 1
python -m experiments.analyze --runs artifacts/runs/smoke/<RUN_ID>/results/runs_long.csv --outdir artifacts/runs/smoke/<RUN_ID>/results --figdir artifacts/runs/smoke/<RUN_ID>/figures
python -m experiments.pairwise --runs artifacts/runs/smoke/<RUN_ID>/results/runs_long.csv --method-a vanilla_cma --method-b proxy_sigma_controller --outdir artifacts/runs/smoke/<RUN_ID>/results
python -m experiments.hypotheses --runs artifacts/runs/smoke/<RUN_ID>/results/runs_long.csv --cell-stats artifacts/runs/smoke/<RUN_ID>/results/cell_stats.csv --method-aggregate artifacts/runs/smoke/<RUN_ID>/results/method_aggregate.csv --behavior-aggregate artifacts/runs/smoke/<RUN_ID>/results/behavior_aggregate.csv --config experiments/config/smoke.yaml --outdir artifacts/runs/smoke/<RUN_ID>/results
python -m experiments.findings --results-dir artifacts/runs/smoke/<RUN_ID>/results --figdir artifacts/runs/smoke/<RUN_ID>/figures
```

Verify output contracts:

```bash
python scripts/verify_experiment_artifacts.py \
  --results-dir artifacts/runs/smoke/<RUN_ID>/results \
  --figdir artifacts/runs/smoke/<RUN_ID>/figures \
  --config experiments/config/smoke.yaml \
  --require-pairwise
```
