from __future__ import annotations

import pytest

from cmaes_proxy_sigma_controller.adapters.pycma import PyCMAAdapter
from cmaes_proxy_sigma_controller.errors import SigmaDriftError
from cmaes_proxy_sigma_controller.types import ControllerConfig

try:
    import cma  # noqa: F401

    HAS_CMA = True
except Exception:  # pragma: no cover
    HAS_CMA = False


@pytest.mark.skipif(not HAS_CMA, reason="pycma unavailable")
def test_adapter_smoke_and_schema_fields() -> None:
    import cma
    import numpy as np

    es = cma.CMAEvolutionStrategy([3.0, 3.0], 0.5, {"seed": 0, "popsize": 4, "verbose": -9, "verb_disp": 0, "verb_log": 0})
    cfg = ControllerConfig(warmup_generations=0)
    adapter = PyCMAAdapter(cfg, initial_sigma=0.5)

    rng = np.random.default_rng(0)
    for gen in range(1, 4):
        xs = np.asarray(es.ask(), dtype=float)
        fitness = [float(np.sum(x * x) + rng.normal(0.0, 0.01)) for x in xs]
        es.tell(xs.tolist(), fitness)
        adapter.apply_post_tell(
            es,
            fitness=fitness,
            generation=gen,
            planned_generations=3,
            seed=0,
            function_name="sphere",
            dimension=2,
            noise_sigma=0.01,
        )

    summary = adapter.finalize(planned_generations=3).to_dict()
    assert summary["proxy_schema_version"] == 1
    assert "proxy_time_to_first_floor_gen" in summary


@pytest.mark.skipif(not HAS_CMA, reason="pycma unavailable")
def test_sigma_drift_assertion() -> None:
    import cma

    es = cma.CMAEvolutionStrategy([3.0, 3.0], 0.5, {"seed": 0, "popsize": 4, "verbose": -9, "verb_disp": 0, "verb_log": 0})
    cfg = ControllerConfig(warmup_generations=0)
    adapter = PyCMAAdapter(cfg, initial_sigma=0.5, assert_sigma_drift=True)

    xs = es.ask()
    fitness = [float(sum(xi * xi for xi in x)) for x in xs]
    es.tell(xs, fitness)
    adapter.apply_post_tell(
        es,
        fitness=fitness,
        generation=1,
        planned_generations=2,
        seed=0,
        function_name="sphere",
        dimension=2,
        noise_sigma=0.0,
    )

    es.sigma += 0.01
    xs = es.ask()
    fitness = [float(sum(xi * xi for xi in x)) for x in xs]
    es.tell(xs, fitness)
    with pytest.raises(SigmaDriftError):
        adapter.apply_post_tell(
            es,
            fitness=fitness,
            generation=2,
            planned_generations=2,
            seed=0,
            function_name="sphere",
            dimension=2,
            noise_sigma=0.0,
        )
