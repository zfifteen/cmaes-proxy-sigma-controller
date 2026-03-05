from __future__ import annotations

from typing import Any

from .types import ControllerState, RunTelemetrySummary


PROXY_SCHEMA_VERSION = 1


def build_run_summary(state: ControllerState, planned_generations: int) -> RunTelemetrySummary:
    if planned_generations < 1:
        raise ValueError("planned_generations must be >= 1")

    first_floor = state.first_floor_gen if state.first_floor_gen is not None else planned_generations
    fraction = state.n_floor_gens / float(planned_generations)

    return RunTelemetrySummary(
        proxy_schema_version=PROXY_SCHEMA_VERSION,
        proxy_sigma_factor_last=float(state.last_factor_applied),
        proxy_ema_snr_last=float(state.ema_snr),
        proxy_time_to_first_floor_gen=int(first_floor),
        proxy_fraction_at_floor=float(fraction),
        proxy_n_floor_entries=int(state.n_floor_entries),
        proxy_n_floor_exits=int(state.n_floor_exits),
        proxy_n_down_steps=int(state.n_down_steps),
        proxy_n_up_steps=int(state.n_up_steps),
        proxy_n_neutral_steps=int(state.n_neutral_steps),
        proxy_sigma_min_seen=float(state.sigma_min_seen),
        proxy_sigma_max_seen=float(state.sigma_max_seen),
        proxy_trace_written=bool(state.trace_written),
        proxy_trace_relpath=state.trace_relpath,
    )


def empty_proxy_row() -> dict[str, Any]:
    return {
        "proxy_schema_version": None,
        "proxy_sigma_factor_last": None,
        "proxy_ema_snr_last": None,
        "proxy_time_to_first_floor_gen": None,
        "proxy_fraction_at_floor": None,
        "proxy_n_floor_entries": None,
        "proxy_n_floor_exits": None,
        "proxy_n_down_steps": None,
        "proxy_n_up_steps": None,
        "proxy_n_neutral_steps": None,
        "proxy_sigma_min_seen": None,
        "proxy_sigma_max_seen": None,
        "proxy_trace_written": None,
        "proxy_trace_relpath": None,
    }
