from __future__ import annotations

import numpy as np


def robust_spread(values: np.ndarray) -> float:
    """1.4826 * MAD for robust spread."""
    med = np.median(values)
    mad = np.median(np.abs(values - med))
    return float(1.4826 * mad)


def noise_floor(values: np.ndarray, noise_floor_abs: float, noise_floor_rel: float) -> float:
    med = float(np.median(values))
    return float(max(noise_floor_abs, noise_floor_rel * max(1.0, abs(med))))


def floor_tolerance(value: float, atol: float, rtol: float) -> float:
    return float(max(atol, rtol * max(1.0, abs(value))))
