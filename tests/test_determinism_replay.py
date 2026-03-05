from __future__ import annotations

from cmaes_proxy_sigma_controller.policy import finalize, initialize, step
from cmaes_proxy_sigma_controller.types import ControllerConfig, ControllerInput


def _run_sequence() -> tuple[list[tuple[float, bool]], dict[str, object]]:
    cfg = ControllerConfig(warmup_generations=0)
    state = initialize(cfg, 1.0)

    decisions: list[tuple[float, bool]] = []
    seq = [
        (1, (1.0, 2.0, 3.0), 1.0),
        (2, (0.9, 1.8, 2.7), 0.9),
        (3, (0.8, 1.6, 2.4), 0.85),
        (4, (0.8, 1.5, 2.2), 0.8),
    ]
    for gen, fit, sigma in seq:
        controller_input = ControllerInput(
            generation=gen,
            fitness=fit,
            current_sigma=sigma,
            initial_sigma=1.0,
            planned_generations=4,
            seed=0,
            function_name="sphere",
            dimension=10,
            noise_sigma=0.0,
        )
        decision, state = step(controller_input, state, cfg)
        decisions.append((decision.next_sigma, decision.was_clamped))

    summary = finalize(state, 4).to_dict()
    return decisions, summary


def test_tier_a_replay_determinism() -> None:
    d1, s1 = _run_sequence()
    d2, s2 = _run_sequence()
    assert d1 == d2
    assert s1 == s2


def test_tier_b_tolerance_rule_for_float_fields() -> None:
    x_ref = 1.23456789
    x_test = 1.2345678905
    tol = max(1e-12, 1e-9 * max(1.0, abs(x_ref)))
    assert abs(x_ref - x_test) <= tol
