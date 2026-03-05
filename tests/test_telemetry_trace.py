from __future__ import annotations

from pathlib import Path

import pytest

from cmaes_proxy_sigma_controller.policy import initialize
from cmaes_proxy_sigma_controller.telemetry import build_run_summary, empty_proxy_row
from cmaes_proxy_sigma_controller.trace import TRACE_FIELDNAMES, write_trace_csv
from cmaes_proxy_sigma_controller.types import ControllerConfig


def test_build_run_summary_requires_positive_planned_generations() -> None:
    state = initialize(ControllerConfig(), 1.0)
    with pytest.raises(ValueError, match="planned_generations"):
        build_run_summary(state, 0)


def test_empty_proxy_row_uses_nulls() -> None:
    row = empty_proxy_row()
    assert row["proxy_schema_version"] is None
    assert row["proxy_trace_written"] is None


def test_write_trace_csv(tmp_path: Path) -> None:
    path = tmp_path / "trace.csv"
    rows = [
        {
            "proxy_schema_version": 1,
            "generation": 1,
            "sigma_before": 0.5,
            "sigma_after": 0.5,
            "at_floor": True,
            "was_clamped": False,
            "proxy_sigma_factor": 1.0,
            "proxy_ema_snr": 0.1,
            "proxy_signal": 0.0,
            "proxy_noise": 1.0,
            "proxy_snr": 0.0,
            "proxy_current_best": 1.0,
            "proxy_best_so_far": 1.0,
            "phase_before": "ACTIVE",
            "phase_after": "ACTIVE",
        }
    ]
    write_trace_csv(path, rows)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    for name in TRACE_FIELDNAMES:
        assert name in text
