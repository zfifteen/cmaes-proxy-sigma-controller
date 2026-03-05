from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .config import canonicalize_function_name
from .types import TraceMode


TARGET_TRACE_CELLS = {
    ("sphere", 10),
    ("sphere", 20),
    ("rosenbrock", 10),
    ("rosenbrock", 20),
}


TRACE_FIELDNAMES = [
    "proxy_schema_version",
    "generation",
    "sigma_before",
    "sigma_after",
    "at_floor",
    "was_clamped",
    "proxy_sigma_factor",
    "proxy_ema_snr",
    "proxy_signal",
    "proxy_noise",
    "proxy_snr",
    "proxy_current_best",
    "proxy_best_so_far",
    "phase_before",
    "phase_after",
]


def should_trace_proxy_run(function_name: str, dimension: int, seed: int, mode: TraceMode | str) -> bool:
    mode_value = TraceMode(mode)
    if mode_value is TraceMode.OFF:
        return False
    if mode_value is TraceMode.FULL:
        return True

    fn = canonicalize_function_name(function_name)
    return (fn, int(dimension)) in TARGET_TRACE_CELLS or int(seed) % 10 == 0


def write_trace_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=TRACE_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
