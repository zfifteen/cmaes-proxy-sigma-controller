from __future__ import annotations

import numpy as np

from cmaes_proxy_sigma_controller.stats import floor_tolerance, noise_floor, robust_spread


def test_robust_spread_known_vector() -> None:
    values = np.asarray([1.0, 2.0, 3.0, 4.0, 100.0], dtype=float)
    got = robust_spread(values)
    assert got > 0.0
    assert got < 3.0


def test_noise_floor_mixed_rule() -> None:
    values = np.asarray([1e-15, 2e-15, 3e-15], dtype=float)
    got = noise_floor(values, noise_floor_abs=1e-12, noise_floor_rel=1e-12)
    assert got == 1e-12


def test_floor_tolerance_mixed_rule() -> None:
    tol = floor_tolerance(5e-10, atol=1e-12, rtol=1e-9)
    assert tol >= 1e-12
