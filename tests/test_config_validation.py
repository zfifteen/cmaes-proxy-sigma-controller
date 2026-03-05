from __future__ import annotations

import pytest

from cmaes_proxy_sigma_controller.config import config_from_dict, validate_config, validate_input
from cmaes_proxy_sigma_controller.errors import ConfigValidationError, InputValidationError
from cmaes_proxy_sigma_controller.types import ControllerConfig, ControllerInput


def test_valid_default_config() -> None:
    validate_config(ControllerConfig())


def test_invalid_threshold_ordering() -> None:
    with pytest.raises(ConfigValidationError):
        validate_config(ControllerConfig(snr_down_threshold=0.2, snr_up_threshold=0.2))


def test_invalid_noise_floor_abs_zero() -> None:
    with pytest.raises(ConfigValidationError):
        validate_config(ControllerConfig(noise_floor_abs=0.0))


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"ema_alpha": 0.0}, "ema_alpha"),
        ({"snr_down_threshold": 0.0}, "snr_down_threshold"),
        ({"sigma_down_factor": 1.0}, "sigma_down_factor"),
        ({"sigma_up_factor": 1.0}, "sigma_up_factor"),
        ({"sigma_min_ratio": 0.0}, "sigma_min_ratio"),
        ({"sigma_max_ratio": 0.5}, "sigma_max_ratio"),
        ({"sigma_min_ratio": 0.9, "sigma_max_ratio": 0.8}, "sigma_max_ratio"),
        ({"warmup_generations": -1}, "warmup_generations"),
        ({"recovery_min_streak": 0}, "recovery_min_streak"),
        ({"recovery_boost_factor": 0.5}, "recovery_boost_factor"),
        ({"recovery_cooldown_generations": -1}, "recovery_cooldown_generations"),
        ({"noise_floor_rel": -1e-4}, "noise_floor_rel"),
        ({"at_floor_atol": -1e-4}, "at_floor_atol"),
        ({"at_floor_rtol": -1e-4}, "at_floor_rtol"),
    ],
)
def test_config_rejects_invalid_ranges(override: dict[str, float], expected: str) -> None:
    kwargs = dict(override)
    with pytest.raises(ConfigValidationError, match=expected):
        validate_config(ControllerConfig(**kwargs))


def test_config_from_dict_enums() -> None:
    cfg = config_from_dict({"trace_mode": "full", "ema_init_mode": "zero", "failure_policy": "fail_open"})
    assert cfg.trace_mode.value == "full"
    assert cfg.ema_init_mode.value == "zero"
    assert cfg.failure_policy.value == "fail_open"


def test_input_requires_canonical_function_name() -> None:
    controller_input = ControllerInput(
        generation=1,
        fitness=(1.0, 2.0),
        current_sigma=0.5,
        initial_sigma=0.5,
        planned_generations=10,
        seed=0,
        function_name="Sphere",
        dimension=10,
        noise_sigma=0.0,
    )
    with pytest.raises(InputValidationError):
        validate_input(controller_input)


def test_input_requires_non_negative_seed() -> None:
    controller_input = ControllerInput(
        generation=1,
        fitness=(1.0, 2.0),
        current_sigma=0.5,
        initial_sigma=0.5,
        planned_generations=10,
        seed=-1,
        function_name="sphere",
        dimension=10,
        noise_sigma=0.0,
    )
    with pytest.raises(InputValidationError):
        validate_input(controller_input)


def test_input_rejects_bad_generation_bounds_and_non_finite_fitness() -> None:
    bad_generation = ControllerInput(
        generation=11,
        fitness=(1.0, 2.0),
        current_sigma=0.5,
        initial_sigma=0.5,
        planned_generations=10,
        seed=0,
        function_name="sphere",
        dimension=10,
        noise_sigma=0.0,
    )
    with pytest.raises(InputValidationError, match="planned_generations"):
        validate_input(bad_generation)

    bad_fitness = ControllerInput(
        generation=1,
        fitness=(1.0, float("nan")),
        current_sigma=0.5,
        initial_sigma=0.5,
        planned_generations=10,
        seed=0,
        function_name="sphere",
        dimension=10,
        noise_sigma=0.0,
    )
    with pytest.raises(InputValidationError, match="finite"):
        validate_input(bad_fitness)
