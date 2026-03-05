from __future__ import annotations

import pytest

from cmaes_proxy_sigma_controller.errors import StepExecutionError
from cmaes_proxy_sigma_controller.policy import initialize, step
from cmaes_proxy_sigma_controller.types import ControllerConfig, ControllerInput, EmaInitMode, FailurePolicy, Phase


def _input(
    *,
    generation: int,
    fitness: tuple[float, ...],
    current_sigma: float = 1.0,
    planned_generations: int = 20,
) -> ControllerInput:
    return ControllerInput(
        generation=generation,
        fitness=fitness,
        current_sigma=current_sigma,
        initial_sigma=1.0,
        planned_generations=planned_generations,
        seed=0,
        function_name="sphere",
        dimension=10,
        noise_sigma=0.0,
    )


def test_ema_init_zero_mode_starts_zero_then_updates() -> None:
    cfg = ControllerConfig(ema_init_mode=EmaInitMode.ZERO, warmup_generations=0)
    state = initialize(cfg, 1.0)
    assert state.ema_snr == 0.0
    decision, state = step(_input(generation=1, fitness=(1.0, 2.0)), state, cfg)
    assert decision.factor_applied == cfg.sigma_down_factor


def test_was_clamped_true_when_clip_changes_value() -> None:
    cfg = ControllerConfig(warmup_generations=0, sigma_min_ratio=0.5, sigma_down_factor=0.9)
    state = initialize(cfg, 1.0)
    decision, _ = step(_input(generation=1, fitness=(1.0, 2.0), current_sigma=0.51), state, cfg)
    assert decision.was_clamped is True


def test_warmup_keeps_phase_but_allows_base_actions() -> None:
    cfg = ControllerConfig(warmup_generations=3)
    state = initialize(cfg, 1.0)
    decision, state = step(_input(generation=1, fitness=(1.0, 2.0)), state, cfg)
    assert decision.phase_after is Phase.WARMUP
    assert decision.factor_applied == cfg.sigma_down_factor


def test_recovery_is_non_downward() -> None:
    cfg = ControllerConfig(warmup_generations=0, recovery_enabled=True, recovery_min_streak=1)
    state = initialize(cfg, 1.0)
    state.phase = Phase.CONSTRAINED
    state.prev_at_floor = True
    state.floor_streak = 2
    decision, _ = step(_input(generation=2, fitness=(1.0, 2.0), current_sigma=0.05), state, cfg)
    assert decision.factor_applied >= 1.0


def test_fail_open_returns_noop_decision() -> None:
    cfg = ControllerConfig(warmup_generations=0, failure_policy=FailurePolicy.FAIL_OPEN)
    state = initialize(cfg, 1.0)
    state.floor_streak = -1  # invalid state triggers fail-open branch
    decision, next_state = step(_input(generation=1, fitness=(1.0, 2.0), current_sigma=0.8), state, cfg)
    assert decision.next_sigma == 0.8
    assert decision.factor_applied == 1.0
    assert decision.diagnostics["proxy_failure_policy"] == "fail_open"
    assert next_state is state


def test_fail_fast_raises_on_invalid_state() -> None:
    cfg = ControllerConfig(warmup_generations=0, failure_policy=FailurePolicy.FAIL_FAST)
    state = initialize(cfg, 1.0)
    state.floor_streak = -1
    with pytest.raises(StepExecutionError):
        step(_input(generation=1, fitness=(1.0, 2.0)), state, cfg)
