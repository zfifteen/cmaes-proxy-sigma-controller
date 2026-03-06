from __future__ import annotations

from typing import Callable

import numpy as np


SUPPORTED_FUNCTIONS = {
    "sphere",
    "rosenbrock",
    "rastrigin",
    "ellipsoid_cond1e6",
}


def _sphere(x: np.ndarray) -> float:
    return float(np.sum(x * x))


def _rosenbrock(x: np.ndarray) -> float:
    return float(np.sum(100.0 * (x[1:] - x[:-1] ** 2) ** 2 + (1.0 - x[:-1]) ** 2))


def _rastrigin(x: np.ndarray) -> float:
    n = x.shape[0]
    return float(10.0 * n + np.sum(x * x - 10.0 * np.cos(2.0 * np.pi * x)))


def _ellipsoid_cond1e6(x: np.ndarray) -> float:
    n = x.shape[0]
    if n == 1:
        weights = np.ones(1, dtype=float)
    else:
        weights = np.power(1e6, np.arange(n, dtype=float) / float(n - 1))
    return float(np.sum(weights * (x * x)))


_OBJECTIVE_MAP: dict[str, Callable[[np.ndarray], float]] = {
    "sphere": _sphere,
    "rosenbrock": _rosenbrock,
    "rastrigin": _rastrigin,
    "ellipsoid_cond1e6": _ellipsoid_cond1e6,
}


def evaluate_objective(function_name: str, x: np.ndarray) -> float:
    fn = function_name.strip().lower()
    objective = _OBJECTIVE_MAP.get(fn)
    if objective is None:
        raise ValueError(f"Unsupported function_name: {function_name}")
    return objective(x)


def noisy_objective(function_name: str, x: np.ndarray, noise_sigma: float, rng: np.random.Generator) -> float:
    base = evaluate_objective(function_name, x)
    if noise_sigma <= 0.0:
        return base
    return float(base + rng.normal(0.0, float(noise_sigma)))
