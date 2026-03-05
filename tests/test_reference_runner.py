from __future__ import annotations

from pathlib import Path

import pytest

from cmaes_proxy_sigma_controller.reference_runner import run_reference, write_runs_csv
from cmaes_proxy_sigma_controller.types import ControllerConfig

try:
    import cma  # noqa: F401

    HAS_CMA = True
except Exception:  # pragma: no cover
    HAS_CMA = False


@pytest.mark.skipif(not HAS_CMA, reason="pycma unavailable")
def test_reference_runner_vanilla_and_proxy(tmp_path: Path) -> None:
    vanilla = run_reference(
        method="vanilla",
        function_name="sphere",
        dimension=4,
        seed=0,
        noise_sigma=0.0,
        initial_sigma=0.5,
        popsize=6,
        planned_generations=4,
    )
    proxy = run_reference(
        method="proxy",
        function_name="sphere",
        dimension=4,
        seed=0,
        noise_sigma=0.0,
        initial_sigma=0.5,
        popsize=6,
        planned_generations=4,
        controller_config=ControllerConfig(warmup_generations=0),
    )

    assert vanilla["method"] == "vanilla"
    assert proxy["method"] == "proxy"
    assert proxy["proxy_schema_version"] == 1

    out = tmp_path / "runs.csv"
    write_runs_csv(out, [vanilla, proxy])
    assert out.exists()


def test_reference_runner_rejects_unknown_function() -> None:
    with pytest.raises(ValueError, match="Unsupported function_name"):
        run_reference(
            method="vanilla",
            function_name="unknown_fn",
            dimension=4,
            seed=0,
            noise_sigma=0.0,
            initial_sigma=0.5,
            popsize=6,
            planned_generations=1,
        )
