from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


Scalar = str | int | float | bool


class Phase(str, Enum):
    WARMUP = "WARMUP"
    ACTIVE = "ACTIVE"
    CONSTRAINED = "CONSTRAINED"
    RECOVERY = "RECOVERY"


class TraceMode(str, Enum):
    OFF = "off"
    HYBRID = "hybrid"
    FULL = "full"


class EmaInitMode(str, Enum):
    FIRST_OBSERVATION = "first_observation"
    ZERO = "zero"


class FailurePolicy(str, Enum):
    FAIL_FAST = "fail_fast"
    FAIL_OPEN = "fail_open"


@dataclass(frozen=True)
class ControllerConfig:
    ema_alpha: float = 0.2
    ema_init_mode: EmaInitMode = EmaInitMode.FIRST_OBSERVATION
    snr_down_threshold: float = 0.08
    snr_up_threshold: float = 0.25
    sigma_down_factor: float = 0.90
    sigma_up_factor: float = 1.03
    sigma_min_ratio: float = 0.05
    sigma_max_ratio: float = 10.0
    warmup_generations: int = 5
    recovery_enabled: bool = True
    recovery_min_streak: int = 6
    recovery_boost_factor: float = 1.05
    recovery_cooldown_generations: int = 8
    noise_floor_abs: float = 1e-12
    noise_floor_rel: float = 1e-12
    at_floor_atol: float = 1e-12
    at_floor_rtol: float = 1e-9
    trace_mode: TraceMode = TraceMode.HYBRID
    failure_policy: FailurePolicy = FailurePolicy.FAIL_FAST


@dataclass(frozen=True)
class ControllerInput:
    generation: int
    fitness: tuple[float, ...]
    current_sigma: float
    initial_sigma: float
    planned_generations: int
    seed: int
    function_name: str
    dimension: int
    noise_sigma: float


@dataclass
class ControllerState:
    best_so_far: float | None
    ema_snr: float
    phase: Phase
    floor_streak: int
    prev_at_floor: bool
    cooldown_remaining: int
    n_floor_entries: int
    n_floor_exits: int
    n_down_steps: int
    n_up_steps: int
    n_neutral_steps: int
    n_floor_gens: int
    first_floor_gen: int | None
    sigma_min_seen: float
    sigma_max_seen: float
    trace_written: bool
    trace_relpath: str | None
    last_factor_applied: float = 1.0


@dataclass(frozen=True)
class ControllerDecision:
    next_sigma: float
    factor_applied: float
    was_clamped: bool
    phase_after: Phase
    diagnostics: dict[str, Scalar] = field(default_factory=dict)


@dataclass(frozen=True)
class RunTelemetrySummary:
    proxy_schema_version: int
    proxy_sigma_factor_last: float
    proxy_ema_snr_last: float
    proxy_time_to_first_floor_gen: int
    proxy_fraction_at_floor: float
    proxy_n_floor_entries: int
    proxy_n_floor_exits: int
    proxy_n_down_steps: int
    proxy_n_up_steps: int
    proxy_n_neutral_steps: int
    proxy_sigma_min_seen: float
    proxy_sigma_max_seen: float
    proxy_trace_written: bool
    proxy_trace_relpath: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "proxy_schema_version": self.proxy_schema_version,
            "proxy_sigma_factor_last": self.proxy_sigma_factor_last,
            "proxy_ema_snr_last": self.proxy_ema_snr_last,
            "proxy_time_to_first_floor_gen": self.proxy_time_to_first_floor_gen,
            "proxy_fraction_at_floor": self.proxy_fraction_at_floor,
            "proxy_n_floor_entries": self.proxy_n_floor_entries,
            "proxy_n_floor_exits": self.proxy_n_floor_exits,
            "proxy_n_down_steps": self.proxy_n_down_steps,
            "proxy_n_up_steps": self.proxy_n_up_steps,
            "proxy_n_neutral_steps": self.proxy_n_neutral_steps,
            "proxy_sigma_min_seen": self.proxy_sigma_min_seen,
            "proxy_sigma_max_seen": self.proxy_sigma_max_seen,
            "proxy_trace_written": self.proxy_trace_written,
            "proxy_trace_relpath": self.proxy_trace_relpath,
        }
