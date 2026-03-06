from __future__ import annotations

from pathlib import Path

from experiments.config import expand_method_variants, validate_and_normalize_config
from experiments.io import load_yaml_config
from experiments.methods import build_default_registry, method_instance_name


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_normalized(path: Path) -> dict:
    registry = build_default_registry()
    raw = load_yaml_config(path)
    return validate_and_normalize_config(raw, known_methods=registry.method_ids())


def _assert_pairwise_target_exists(config: dict) -> None:
    pairwise = config["analysis"]["default_pairwise"]
    method_b = pairwise["method_b"]
    variants = expand_method_variants(config)
    instances: set[str] = set()
    for method_id, items in variants.items():
        for item in items:
            instances.add(method_instance_name(method_id, item["variant_id"]))
    assert method_b in instances


def test_descent_geom_dense_config_variant_count_and_pairwise_target() -> None:
    config = _load_normalized(REPO_ROOT / "experiments/config/descent_geom_dense_hybrid.yaml")
    variants = expand_method_variants(config)
    assert len(variants["proxy_sigma_controller"]) == 64
    _assert_pairwise_target_exists(config)


def test_descent_geom_interaction_config_variant_count_and_pairwise_target() -> None:
    config = _load_normalized(REPO_ROOT / "experiments/config/descent_geom_interaction_hybrid.yaml")
    variants = expand_method_variants(config)
    assert len(variants["proxy_sigma_controller"]) == 16
    _assert_pairwise_target_exists(config)


def test_descent_geom_anchors_config_variant_count_and_pairwise_target() -> None:
    config = _load_normalized(REPO_ROOT / "experiments/config/descent_geom_anchors_full.yaml")
    variants = expand_method_variants(config)
    assert len(variants["proxy_sigma_controller"]) == 10
    _assert_pairwise_target_exists(config)
