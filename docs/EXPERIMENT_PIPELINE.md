# Experiment Pipeline Contract

## Config Schema (v1)

Top-level keys:
- `experiment_name`
- `matrix.functions`, `matrix.dimensions`, `matrix.noise_sigmas`
- `methods`
- `reference_method`
- `budget.evals_per_run`
- `cma.initial_sigma`, `cma.base_popsize`, `cma.verbose`
- `proxy_defaults`
- `variants` (explicit named variants)
- `sweeps` (cartesian proxy-parameter grids)
- `telemetry.proxy_trace_mode`
- `seeds.eval`
- `runtime.parallel_workers` (must be `1` in v1)
- `analysis.default_pairwise`
- `hypotheses.checks`

## CLI Entry Points

- `python -m experiments.run --config ... --outdir ... --workers 1 [--run-id ...]`
- `python -m experiments.analyze --runs ... --outdir ... [--figdir ...] [--manifest-json ...]`
- `python -m experiments.pairwise --runs ... --method-a ... --method-b ... --outdir ...`
- `python -m experiments.hypotheses --runs ... --cell-stats ... --method-aggregate ... --behavior-aggregate ... --config ... --outdir ...`
- `python -m experiments.findings --results-dir ... --figdir ...`

## Artifact Contract

`run` outputs:
- `runs_long.csv`
- `manifest.json`
- `proxy_traces/*.csv` (when trace mode selects rows)

`analyze` outputs:
- `cell_stats.csv`
- `method_aggregate.csv`
- `behavior_aggregate.csv`
- `analysis_manifest.json`
- `method_median_delta_bar.png`
- `method_win_rate_bar.png`
- `behavior_fraction_at_floor_bar.png`
- `behavior_time_to_first_floor_bar.png`

`pairwise` outputs:
- `pairwise_<method_b>_vs_<method_a>.csv`
- `pairwise_<method_b>_vs_<method_a>.json`

`hypotheses` outputs:
- `hypothesis_checks.json`

`findings` outputs:
- `findings.json`
- `findings.md`

Verifier:
- `python scripts/verify_experiment_artifacts.py --results-dir ... --figdir ... --config ... --require-pairwise`

## Sequential-Only Runtime

v1 intentionally enforces sequential execution. `--workers` is accepted for forward compatibility but must resolve to `1`.
