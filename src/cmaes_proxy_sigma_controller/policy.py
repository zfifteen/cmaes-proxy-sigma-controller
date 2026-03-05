from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from .config import validate_config, validate_input, validate_state
from .errors import StepExecutionError
from .stats import floor_tolerance, noise_floor, robust_spread
from .telemetry import build_run_summary
from .types import (
    ControllerConfig,
    ControllerDecision,
    ControllerInput,
    ControllerState,
    FailurePolicy,
    Phase,
    RunTelemetrySummary,
)


def initialize(config: ControllerConfig, initial_sigma: float) -> ControllerState:
    validate_config(config)
    if initial_sigma <= 0.0:
        raise ValueError("initial_sigma must be > 0")

    initial_phase = Phase.WARMUP if config.warmup_generations > 0 else Phase.ACTIVE
    ema = 0.0

    return ControllerState(
        best_so_far=None,
        ema_snr=ema,
        phase=initial_phase,
        floor_streak=0,
        prev_at_floor=False,
        cooldown_remaining=0,
        n_floor_entries=0,
        n_floor_exits=0,
        n_down_steps=0,
        n_up_steps=0,
        n_neutral_steps=0,
        n_floor_gens=0,
        first_floor_gen=None,
        sigma_min_seen=float(initial_sigma),
        sigma_max_seen=float(initial_sigma),
        trace_written=False,
        trace_relpath=None,
        last_factor_applied=1.0,
    )


def _step_impl(
    controller_input: ControllerInput,
    state: ControllerState,
    config: ControllerConfig,
) -> tuple[ControllerDecision, ControllerState]:
    validate_input(controller_input)
    validate_state(state)

    fitness = np.asarray(controller_input.fitness, dtype=float)
    generation = int(controller_input.generation)

    cooldown_t = max(int(state.cooldown_remaining) - 1, 0)

    current_best = float(np.min(fitness))
    prev_best = current_best if state.best_so_far is None else float(state.best_so_far)

    signal_t = max(prev_best - current_best, 0.0)
    noise_floor_t = noise_floor(fitness, config.noise_floor_abs, config.noise_floor_rel)
    noise_t = robust_spread(fitness) + noise_floor_t
    snr_t = signal_t / noise_t

    if state.best_so_far is None and config.ema_init_mode.value == "first_observation":
        ema_t = snr_t
    else:
        ema_t = config.ema_alpha * snr_t + (1.0 - config.ema_alpha) * float(state.ema_snr)

    if ema_t < config.snr_down_threshold:
        factor_base = float(config.sigma_down_factor)
    elif ema_t > config.snr_up_threshold:
        factor_base = float(config.sigma_up_factor)
    else:
        factor_base = 1.0

    recovery_fire = bool(
        state.phase is Phase.CONSTRAINED
        and config.recovery_enabled
        and state.prev_at_floor
        and state.floor_streak >= config.recovery_min_streak
        and cooldown_t == 0
    )

    if recovery_fire:
        boosted = factor_base * float(config.recovery_boost_factor)
        boosted_cap = float(config.sigma_up_factor) * float(config.recovery_boost_factor)
        factor_applied = max(1.0, min(boosted, boosted_cap))
    else:
        factor_applied = factor_base

    floor_sigma = float(controller_input.initial_sigma) * float(config.sigma_min_ratio)
    ceiling_sigma = float(controller_input.initial_sigma) * float(config.sigma_max_ratio)

    floor_tol = floor_tolerance(floor_sigma, config.at_floor_atol, config.at_floor_rtol)
    ceiling_tol = floor_tolerance(ceiling_sigma, config.at_floor_atol, config.at_floor_rtol)

    unclamped = float(controller_input.current_sigma) * float(factor_applied)
    next_sigma = float(np.clip(unclamped, floor_sigma, ceiling_sigma))
    was_clamped = bool(next_sigma != unclamped)
    at_floor = abs(next_sigma - floor_sigma) <= floor_tol

    floor_streak_t = int(state.floor_streak + 1 if at_floor else 0)

    if generation <= int(config.warmup_generations):
        phase_after = Phase.WARMUP
    elif recovery_fire:
        phase_after = Phase.RECOVERY
    elif at_floor and floor_streak_t >= int(config.recovery_min_streak):
        phase_after = Phase.CONSTRAINED
    else:
        phase_after = Phase.ACTIVE

    n_down_steps = int(state.n_down_steps + (1 if factor_applied < 1.0 else 0))
    n_up_steps = int(state.n_up_steps + (1 if factor_applied > 1.0 else 0))
    n_neutral_steps = int(state.n_neutral_steps + (1 if factor_applied == 1.0 else 0))

    n_floor_gens = int(state.n_floor_gens + (1 if at_floor else 0))

    n_floor_entries = int(state.n_floor_entries)
    n_floor_exits = int(state.n_floor_exits)
    if at_floor and not state.prev_at_floor:
        n_floor_entries += 1
    if (not at_floor) and state.prev_at_floor:
        n_floor_exits += 1

    first_floor_gen = state.first_floor_gen
    if first_floor_gen is None and at_floor:
        first_floor_gen = generation

    cooldown_next = int(config.recovery_cooldown_generations if recovery_fire else cooldown_t)

    next_state = replace(
        state,
        best_so_far=min(prev_best, current_best),
        ema_snr=float(ema_t),
        phase=phase_after,
        floor_streak=floor_streak_t,
        prev_at_floor=bool(at_floor),
        cooldown_remaining=cooldown_next,
        n_floor_entries=n_floor_entries,
        n_floor_exits=n_floor_exits,
        n_down_steps=n_down_steps,
        n_up_steps=n_up_steps,
        n_neutral_steps=n_neutral_steps,
        n_floor_gens=n_floor_gens,
        first_floor_gen=first_floor_gen,
        sigma_min_seen=min(float(state.sigma_min_seen), next_sigma),
        sigma_max_seen=max(float(state.sigma_max_seen), next_sigma),
        last_factor_applied=float(factor_applied),
    )

    diagnostics: dict[str, Any] = {
        "proxy_signal": float(signal_t),
        "proxy_noise": float(noise_t),
        "proxy_snr": float(snr_t),
        "proxy_ema_snr": float(ema_t),
        "proxy_sigma_factor": float(factor_applied),
        "proxy_sigma": float(next_sigma),
        "proxy_current_best": float(current_best),
        "proxy_best_so_far": float(prev_best),
        "phase_before": state.phase.value,
        "phase_after": phase_after.value,
        "recovery_fire": bool(recovery_fire),
        "proxy_floor_tolerance": float(floor_tol),
        "proxy_ceiling_tolerance": float(ceiling_tol),
        "proxy_floor_sigma": float(floor_sigma),
        "proxy_ceiling_sigma": float(ceiling_sigma),
    }

    decision = ControllerDecision(
        next_sigma=float(next_sigma),
        factor_applied=float(factor_applied),
        was_clamped=was_clamped,
        phase_after=phase_after,
        diagnostics=diagnostics,
    )
    return decision, next_state


def step(
    controller_input: ControllerInput,
    state: ControllerState,
    config: ControllerConfig,
) -> tuple[ControllerDecision, ControllerState]:
    try:
        return _step_impl(controller_input, state, config)
    except Exception as exc:
        if config.failure_policy is FailurePolicy.FAIL_OPEN:
            diagnostics: dict[str, Any] = {
                "proxy_failure_policy": "fail_open",
                "proxy_failure_reason": str(exc),
                "proxy_failure_generation": int(controller_input.generation),
                "phase_before": state.phase.value,
                "phase_after": state.phase.value,
            }
            decision = ControllerDecision(
                next_sigma=float(controller_input.current_sigma),
                factor_applied=1.0,
                was_clamped=False,
                phase_after=state.phase,
                diagnostics=diagnostics,
            )
            return decision, state
        raise StepExecutionError(str(exc)) from exc


def finalize(state: ControllerState, planned_generations: int) -> RunTelemetrySummary:
    validate_state(state)
    return build_run_summary(state, planned_generations)
