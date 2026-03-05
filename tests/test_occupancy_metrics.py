from __future__ import annotations

from cmaes_proxy_sigma_controller.policy import finalize, initialize, step
from cmaes_proxy_sigma_controller.types import ControllerConfig, ControllerInput


def _mk_input(gen: int, sigma: float, fitness: tuple[float, ...]) -> ControllerInput:
    return ControllerInput(
        generation=gen,
        fitness=fitness,
        current_sigma=sigma,
        initial_sigma=1.0,
        planned_generations=5,
        seed=0,
        function_name="sphere",
        dimension=10,
        noise_sigma=0.0,
    )


def test_floor_entry_exit_and_finalize_summary() -> None:
    cfg = ControllerConfig(
        warmup_generations=0,
        sigma_min_ratio=0.5,
        recovery_enabled=False,
        recovery_min_streak=2,
        ema_alpha=1.0,
    )
    state = initialize(cfg, 1.0)

    _, state = step(_mk_input(1, 0.5, (1.0, 2.0)), state, cfg)
    _, state = step(_mk_input(2, 0.9, (0.5, 1.0)), state, cfg)
    # No improvement -> down-step from near-floor sigma gets clipped back to floor (new entry).
    _, state = step(_mk_input(3, 0.51, (0.5, 1.0)), state, cfg)

    summary = finalize(state, planned_generations=5)
    assert summary.proxy_n_floor_entries >= 2
    assert summary.proxy_n_floor_exits >= 1
    assert summary.proxy_time_to_first_floor_gen == 1
    assert 0.0 <= summary.proxy_fraction_at_floor <= 1.0
