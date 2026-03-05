# cmaes-proxy-sigma-controller

`cmaes-proxy-sigma-controller` is a Python-first, mechanism-aware proxy layer for external sigma control in CMA-ES.

It is designed to remain outside optimizer internals while providing deterministic policy decisions, strict clamp safety, and telemetry for occupancy-driven diagnostics.

## Install

```bash
python -m pip install -e .
python -m pip install -e '.[dev,pycma]'
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

See [TECHNICAL_DESIGN_SPEC.md](/Users/velocityworks/IdeaProjects/cmaes-proxy-sigma-controller/TECHNICAL_DESIGN_SPEC.md) and [docs/RUNBOOK.md](/Users/velocityworks/IdeaProjects/cmaes-proxy-sigma-controller/docs/RUNBOOK.md).
