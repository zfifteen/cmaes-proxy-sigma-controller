from __future__ import annotations

import re
from dataclasses import fields
from typing import Any

import numpy as np

from .errors import ConfigValidationError, InputValidationError, StateValidationError
from .types import (
    ControllerConfig,
    ControllerInput,
    ControllerState,
    EmaInitMode,
    FailurePolicy,
    Phase,
    TraceMode,
)

_CANON_TOKEN_RE = re.compile(r"^[a-z0-9_]+$")


def canonicalize_function_name(name: str) -> str:
    return name.strip().lower()


def is_canonical_function_name(name: str) -> bool:
    return bool(_CANON_TOKEN_RE.fullmatch(name)) and name == canonicalize_function_name(name)


def config_from_dict(values: dict[str, Any]) -> ControllerConfig:
    kwargs: dict[str, Any] = {}
    for f in fields(ControllerConfig):
        if f.name not in values:
            continue
        raw = values[f.name]
        if f.name == "trace_mode":
            kwargs[f.name] = TraceMode(str(raw))
        elif f.name == "ema_init_mode":
            kwargs[f.name] = EmaInitMode(str(raw))
        elif f.name == "failure_policy":
            kwargs[f.name] = FailurePolicy(str(raw))
        else:
            kwargs[f.name] = raw
    config = ControllerConfig(**kwargs)
    validate_config(config)
    return config


def validate_config(config: ControllerConfig) -> None:
    if not (0.0 < config.ema_alpha <= 1.0):
        raise ConfigValidationError("ema_alpha must be in (0, 1]")
    if config.snr_down_threshold <= 0.0:
        raise ConfigValidationError("snr_down_threshold must be > 0")
    if config.snr_up_threshold <= config.snr_down_threshold:
        raise ConfigValidationError("snr_up_threshold must be > snr_down_threshold")
    if not (0.0 < config.sigma_down_factor < 1.0):
        raise ConfigValidationError("sigma_down_factor must be in (0, 1)")
    if config.sigma_up_factor <= 1.0:
        raise ConfigValidationError("sigma_up_factor must be > 1")
    if not (0.0 < config.sigma_min_ratio <= 1.0):
        raise ConfigValidationError("sigma_min_ratio must be in (0, 1]")
    if config.sigma_max_ratio < 1.0:
        raise ConfigValidationError("sigma_max_ratio must be >= 1")
    if config.sigma_min_ratio > config.sigma_max_ratio:
        raise ConfigValidationError("sigma_min_ratio must be <= sigma_max_ratio")
    if config.warmup_generations < 0:
        raise ConfigValidationError("warmup_generations must be >= 0")
    if config.recovery_min_streak < 1:
        raise ConfigValidationError("recovery_min_streak must be >= 1")
    if config.recovery_boost_factor < 1.0:
        raise ConfigValidationError("recovery_boost_factor must be >= 1")
    if config.recovery_cooldown_generations < 0:
        raise ConfigValidationError("recovery_cooldown_generations must be >= 0")
    if config.noise_floor_abs <= 0.0:
        raise ConfigValidationError("noise_floor_abs must be > 0")
    if config.noise_floor_rel < 0.0:
        raise ConfigValidationError("noise_floor_rel must be >= 0")
    if config.at_floor_atol < 0.0:
        raise ConfigValidationError("at_floor_atol must be >= 0")
    if config.at_floor_rtol < 0.0:
        raise ConfigValidationError("at_floor_rtol must be >= 0")


def validate_input(controller_input: ControllerInput) -> None:
    if controller_input.generation < 1:
        raise InputValidationError("generation must be >= 1")
    if controller_input.planned_generations < 1:
        raise InputValidationError("planned_generations must be >= 1")
    if controller_input.generation > controller_input.planned_generations:
        raise InputValidationError("generation must be <= planned_generations")
    if controller_input.seed < 0:
        raise InputValidationError("seed must be >= 0")
    if controller_input.dimension < 1:
        raise InputValidationError("dimension must be >= 1")
    if controller_input.noise_sigma < 0.0:
        raise InputValidationError("noise_sigma must be >= 0")
    if controller_input.current_sigma <= 0.0:
        raise InputValidationError("current_sigma must be > 0")
    if controller_input.initial_sigma <= 0.0:
        raise InputValidationError("initial_sigma must be > 0")
    if not is_canonical_function_name(controller_input.function_name):
        raise InputValidationError("function_name must be canonical lower-case token")

    arr = np.asarray(controller_input.fitness, dtype=float)
    if arr.size == 0:
        raise InputValidationError("fitness must be non-empty")
    if not np.all(np.isfinite(arr)):
        raise InputValidationError("fitness must contain finite values only")


def validate_state(state: ControllerState) -> None:
    if state.phase not in set(Phase):
        raise StateValidationError("phase is invalid")
    if state.floor_streak < 0:
        raise StateValidationError("floor_streak must be >= 0")
    if state.cooldown_remaining < 0:
        raise StateValidationError("cooldown_remaining must be >= 0")
    if state.n_floor_entries < 0 or state.n_floor_exits < 0:
        raise StateValidationError("floor counters must be >= 0")
    if state.n_down_steps < 0 or state.n_up_steps < 0 or state.n_neutral_steps < 0:
        raise StateValidationError("step counters must be >= 0")
    if state.n_floor_gens < 0:
        raise StateValidationError("n_floor_gens must be >= 0")
