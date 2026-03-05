from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

from .adapters.pycma import PyCMAAdapter
from .telemetry import empty_proxy_row
from .types import ControllerConfig, TraceMode


def _sphere(x: np.ndarray) -> float:
    return float(np.sum(x * x))


def _rosenbrock(x: np.ndarray) -> float:
    return float(np.sum(100.0 * (x[1:] - x[:-1] ** 2) ** 2 + (1.0 - x[:-1]) ** 2))


def _objective(function_name: str, x: np.ndarray) -> float:
    if function_name == "sphere":
        return _sphere(x)
    if function_name == "rosenbrock":
        return _rosenbrock(x)
    raise ValueError(f"Unsupported function_name: {function_name}")


def run_reference(
    *,
    method: str,
    function_name: str,
    dimension: int,
    seed: int,
    noise_sigma: float,
    initial_sigma: float,
    popsize: int,
    planned_generations: int,
    controller_config: ControllerConfig | None = None,
    trace_mode: TraceMode | str = TraceMode.OFF,
) -> dict[str, Any]:
    try:
        import cma  # noqa: PLC0415
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pycma is required for reference runner") from exc

    rng = np.random.default_rng(seed)
    x0 = np.full(dimension, 3.0, dtype=float)
    es = cma.CMAEvolutionStrategy(
        x0.tolist(),
        float(initial_sigma),
        {"seed": int(seed), "popsize": int(popsize), "verbose": -9, "verb_disp": 0, "verb_log": 0},
    )

    adapter: PyCMAAdapter | None = None
    if method == "proxy":
        if controller_config is None:
            controller_config = ControllerConfig()
        adapter = PyCMAAdapter(controller_config, initial_sigma)

    best = float("inf")
    for gen in range(1, planned_generations + 1):
        candidates = np.asarray(es.ask(), dtype=float)
        fitness = []
        for point in candidates:
            base = _objective(function_name, point)
            val = float(base + rng.normal(0.0, float(noise_sigma)))
            fitness.append(val)
        es.tell(candidates.tolist(), fitness)
        best = min(best, float(np.min(fitness)))

        if adapter is not None:
            adapter.apply_post_tell(
                es,
                fitness=fitness,
                generation=gen,
                planned_generations=planned_generations,
                seed=seed,
                function_name=function_name,
                dimension=dimension,
                noise_sigma=noise_sigma,
                trace_mode=trace_mode,
            )

    row: dict[str, Any] = {
        "method": method,
        "function": function_name,
        "dimension": int(dimension),
        "seed": int(seed),
        "noise_sigma": float(noise_sigma),
        "planned_generations": int(planned_generations),
        "final_best": float(best),
    }

    if adapter is not None:
        row.update(adapter.finalize(planned_generations).to_dict())
    else:
        row.update(empty_proxy_row())

    return row


def write_runs_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
