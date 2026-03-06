from __future__ import annotations

import pytest

from experiments.methods import MethodDefinition, MethodRegistry, build_default_registry, method_instance_name


def test_default_registry_methods() -> None:
    registry = build_default_registry()
    assert registry.method_ids() == {"vanilla_cma", "proxy_sigma_controller"}
    assert registry.get("vanilla_cma").uses_proxy is False
    assert registry.get("proxy_sigma_controller").uses_proxy is True


def test_registry_duplicate_registration_rejected() -> None:
    registry = MethodRegistry()
    registry.register(MethodDefinition("a", "A"))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(MethodDefinition("a", "A again"))


def test_registry_unknown_method_rejected() -> None:
    registry = build_default_registry()
    with pytest.raises(ValueError, match="Unknown method"):
        registry.get("not_a_method")


def test_method_instance_name() -> None:
    assert method_instance_name("vanilla_cma", None) == "vanilla_cma"
    assert method_instance_name("proxy_sigma_controller", "geom_k090_r010") == "proxy_sigma_controller:geom_k090_r010"
