# cmaes-proxy-sigma-controller

`cmaes-proxy-sigma-controller` is a Python-first, mechanism-aware proxy layer for external sigma control in CMA-ES.

It is designed to remain outside optimizer internals while providing deterministic policy decisions, strict clamp safety, and telemetry for occupancy-driven diagnostics.

## Install

```bash
python -m pip install -e .
python -m pip install -e '.[dev,pycma]'
python -m pip install -e '.[dev,pycma,experiments]'
```

## Core API

```python
from cmaes_proxy_sigma_controller import (
    ControllerConfig,
    ControllerInput,
    initialize,
    step,
    finalize,
)

config = ControllerConfig()
state = initialize(config, initial_sigma=0.5)

controller_input = ControllerInput(
    generation=1,
    fitness=(1.0, 1.2, 1.4),
    current_sigma=0.5,
    initial_sigma=0.5,
    planned_generations=100,
    seed=0,
    function_name="sphere",
    dimension=10,
    noise_sigma=0.0,
)

decision, state = step(controller_input, state, config)
summary = finalize(state, planned_generations=100)
```

## pycma Adapter

```python
from cmaes_proxy_sigma_controller.adapters import PyCMAAdapter
from cmaes_proxy_sigma_controller.types import ControllerConfig

adapter = PyCMAAdapter(ControllerConfig(), initial_sigma=0.5)
# after es.tell(...), call adapter.apply_post_tell(...)
```

## Telemetry Schema

Run-level proxy fields include:
- `proxy_schema_version`
- `proxy_sigma_factor_last`
- `proxy_ema_snr_last`
- `proxy_time_to_first_floor_gen`
- `proxy_fraction_at_floor`
- `proxy_n_floor_entries`
- `proxy_n_floor_exits`
- `proxy_n_down_steps`
- `proxy_n_up_steps`
- `proxy_n_neutral_steps`
- `proxy_sigma_min_seen`
- `proxy_sigma_max_seen`
- `proxy_trace_written`
- `proxy_trace_relpath`

See [docs/TECHNICAL_DESIGN_SPEC.md](docs/TECHNICAL_DESIGN_SPEC.md) and [docs/RUNBOOK.md](docs/RUNBOOK.md).

## Experiment Pipeline

Research pipeline entrypoints (outside CI):

```bash
python -m experiments.run --config experiments/config/smoke.yaml --outdir artifacts/runs/smoke/<RUN_ID>/results --workers 1
python -m experiments.analyze --runs artifacts/runs/smoke/<RUN_ID>/results/runs_long.csv --outdir artifacts/runs/smoke/<RUN_ID>/results --figdir artifacts/runs/smoke/<RUN_ID>/figures
python -m experiments.pairwise --runs artifacts/runs/smoke/<RUN_ID>/results/runs_long.csv --method-a vanilla_cma --method-b proxy_sigma_controller --outdir artifacts/runs/smoke/<RUN_ID>/results
python -m experiments.hypotheses --runs artifacts/runs/smoke/<RUN_ID>/results/runs_long.csv --cell-stats artifacts/runs/smoke/<RUN_ID>/results/cell_stats.csv --method-aggregate artifacts/runs/smoke/<RUN_ID>/results/method_aggregate.csv --behavior-aggregate artifacts/runs/smoke/<RUN_ID>/results/behavior_aggregate.csv --config experiments/config/smoke.yaml --outdir artifacts/runs/smoke/<RUN_ID>/results
python -m experiments.findings --results-dir artifacts/runs/smoke/<RUN_ID>/results --figdir artifacts/runs/smoke/<RUN_ID>/figures
```

Wrapper scripts:
- `scripts/run_smoke_pipeline.sh`
- `scripts/run_high_rigor_pipeline.sh`
- `scripts/run_sensitivity_pipeline.sh`

Contract reference:
- `docs/EXPERIMENT_PIPELINE.md`

Artifact verifier:
- `python scripts/verify_experiment_artifacts.py --results-dir ... --figdir ... --config ... --require-pairwise`

## Publication / Citation

- Mechanism-focused technical note: [docs/technical-note/technical_note.md](docs/technical-note/technical_note.md)
- Zenodo metadata: [.zenodo.json](.zenodo.json)
- Citation metadata: [CITATION.cff](CITATION.cff)
- License: [LICENSE](LICENSE)
- Deterministic evidence builder: [scripts/build_publication_evidence.py](scripts/build_publication_evidence.py)
- Evidence bundle manifest: [release-assets/v0.1.0/evidence_manifest.json](release-assets/v0.1.0/evidence_manifest.json)
