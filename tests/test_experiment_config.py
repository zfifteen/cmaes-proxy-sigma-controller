from __future__ import annotations

import pytest

from experiments.config import ConfigError, expand_method_variants, validate_and_normalize_config


KNOWN_METHODS = {"vanilla_cma", "proxy_sigma_controller"}


def _base_config() -> dict:
    return {
        "experiment_name": "test",
        "matrix": {
            "functions": ["sphere"],
            "dimensions": [4],
            "noise_sigmas": [0.0],
        },
        "methods": ["vanilla_cma", "proxy_sigma_controller"],
        "reference_method": "vanilla_cma",
        "budget": {"evals_per_run": 40},
        "cma": {"initial_sigma": 0.5, "base_popsize": 4, "verbose": -9},
        "proxy_defaults": {"sigma_down_factor": 0.9, "sigma_min_ratio": 0.1},
        "variants": [],
        "sweeps": [],
        "telemetry": {"proxy_trace_mode": "off"},
        "seeds": {"eval": [0, 1]},
        "runtime": {"parallel_workers": 1},
        "analysis": {"default_pairwise": {"method_a": "vanilla_cma", "method_b": "proxy_sigma_controller"}},
        "hypotheses": {"checks": []},
    }


def test_config_rejects_unknown_method() -> None:
    cfg = _base_config()
    cfg["methods"] = ["vanilla_cma", "unknown"]
    with pytest.raises(ConfigError, match="Unknown methods"):
        validate_and_normalize_config(cfg, KNOWN_METHODS)


def test_expand_variants_is_deterministic() -> None:
    cfg = _base_config()
    cfg["variants"] = [
        {
            "variant_id": "manual_baseline",
            "method": "proxy_sigma_controller",
            "proxy_overrides": {"sigma_down_factor": 0.9, "sigma_min_ratio": 0.1},
        }
    ]
    cfg["sweeps"] = [
        {
            "sweep_id": "geom",
            "method": "proxy_sigma_controller",
            "constants": {},
            "grid": {
                "sigma_down_factor": [0.90, 0.95],
                "sigma_min_ratio": [0.10, 0.20],
            },
        }
    ]

    normalized = validate_and_normalize_config(cfg, KNOWN_METHODS)
    by_method = expand_method_variants(normalized)

    vanilla = by_method["vanilla_cma"]
    assert len(vanilla) == 1
    assert vanilla[0]["variant_id"] is None

    proxy_ids = [item["variant_id"] for item in by_method["proxy_sigma_controller"]]
    assert proxy_ids == [
        "manual_baseline",
        "geom__sigma_down_factor_0p9__sigma_min_ratio_0p1",
        "geom__sigma_down_factor_0p9__sigma_min_ratio_0p2",
        "geom__sigma_down_factor_0p95__sigma_min_ratio_0p1",
        "geom__sigma_down_factor_0p95__sigma_min_ratio_0p2",
    ]


def test_config_rejects_non_sequential_workers() -> None:
    cfg = _base_config()
    cfg["runtime"] = {"parallel_workers": 2}
    with pytest.raises(ConfigError, match="must be 1"):
        validate_and_normalize_config(cfg, KNOWN_METHODS)
