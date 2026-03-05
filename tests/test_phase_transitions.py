from __future__ import annotations

from cmaes_proxy_sigma_controller.policy import initialize, step
from cmaes_proxy_sigma_controller.types import ControllerConfig, ControllerInput, Phase


def _mk_input(gen: int, sigma: float, planned: int = 10) -> ControllerInput:
    return ControllerInput(
        generation=gen,
        fitness=(1.0, 2.0),
        current_sigma=sigma,
        initial_sigma=1.0,
        planned_generations=planned,
        seed=0,
        function_name="sphere",
        dimension=10,
        noise_sigma=0.0,
    )


def test_enters_constrained_after_floor_streak() -> None:
    cfg = ControllerConfig(warmup_generations=0, recovery_enabled=False, recovery_min_streak=2, sigma_min_ratio=0.5)
    state = initialize(cfg, 1.0)

    _, state = step(_mk_input(1, 0.5), state, cfg)
    assert state.phase is Phase.ACTIVE

    _, state = step(_mk_input(2, 0.5), state, cfg)
    assert state.phase is Phase.CONSTRAINED


def test_constrained_returns_active_when_leaving_floor_with_recovery_off() -> None:
    cfg = ControllerConfig(warmup_generations=0, recovery_enabled=False, recovery_min_streak=1, sigma_min_ratio=0.5)
    state = initialize(cfg, 1.0)

    _, state = step(_mk_input(1, 0.5), state, cfg)
    assert state.phase is Phase.CONSTRAINED

    _, state = step(_mk_input(2, 0.8), state, cfg)
    assert state.phase is Phase.ACTIVE
