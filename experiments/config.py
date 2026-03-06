from __future__ import annotations

import itertools
import re
from dataclasses import fields
from typing import Any

from cmaes_proxy_sigma_controller.types import ControllerConfig

_VARIANT_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
_ALLOWED_TRACE_MODES = {"off", "hybrid", "full"}
_PROXY_FIELD_NAMES = {f.name for f in fields(ControllerConfig)}


class ConfigError(ValueError):
    """Raised when experiment config is invalid."""


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a mapping")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigError(f"{name} must be a list")
    if not value:
        raise ConfigError(f"{name} must be non-empty")
    return value


def _require_scalar_list(value: Any, name: str, cast: type, *, min_value: float | None = None) -> list[Any]:
    items = _require_list(value, name)
    out: list[Any] = []
    for raw in items:
        try:
            item = cast(raw)
        except Exception as exc:  # pragma: no cover - defensive
            raise ConfigError(f"{name} contains non-{cast.__name__} value: {raw!r}") from exc
        if min_value is not None and item < min_value:
            raise ConfigError(f"{name} values must be >= {min_value}")
        out.append(item)
    return out


def _sanitize_variant_id(variant_id: str) -> str:
    if not _VARIANT_ID_RE.fullmatch(variant_id):
        raise ConfigError(f"variant_id must match {_VARIANT_ID_RE.pattern}: {variant_id!r}")
    return variant_id


def _validate_proxy_overrides(overrides: dict[str, Any], where: str) -> None:
    for key in overrides:
        if key not in _PROXY_FIELD_NAMES:
            raise ConfigError(f"{where}: unknown proxy parameter {key!r}")


def _normalized_variant(raw: dict[str, Any], methods: set[str], *, where: str) -> dict[str, Any]:
    variant_id = _sanitize_variant_id(str(raw.get("variant_id", "")))
    method = str(raw.get("method", "proxy_sigma_controller"))
    if method not in methods:
        raise ConfigError(f"{where}: method {method!r} is not declared in methods list")
    proxy_overrides = raw.get("proxy_overrides", {})
    if proxy_overrides is None:
        proxy_overrides = {}
    proxy_overrides = _require_mapping(proxy_overrides, f"{where}.proxy_overrides")
    _validate_proxy_overrides(proxy_overrides, where)
    return {
        "variant_id": variant_id,
        "method": method,
        "proxy_overrides": dict(proxy_overrides),
    }


def validate_and_normalize_config(raw: dict[str, Any], known_methods: set[str]) -> dict[str, Any]:
    config = dict(raw)

    experiment_name = str(config.get("experiment_name", "experiment"))

    matrix = _require_mapping(config.get("matrix"), "matrix")
    functions = [str(x).strip().lower() for x in _require_list(matrix.get("functions"), "matrix.functions")]
    if any(not x for x in functions):
        raise ConfigError("matrix.functions may not contain empty names")
    dimensions = _require_scalar_list(matrix.get("dimensions"), "matrix.dimensions", int, min_value=1)
    noise_sigmas = _require_scalar_list(matrix.get("noise_sigmas"), "matrix.noise_sigmas", float, min_value=0.0)

    methods = [str(x) for x in _require_list(config.get("methods"), "methods")]
    if len(set(methods)) != len(methods):
        raise ConfigError("methods must not contain duplicates")
    unknown_methods = sorted(set(methods).difference(known_methods))
    if unknown_methods:
        raise ConfigError(f"Unknown methods declared: {unknown_methods}")

    reference_method = str(config.get("reference_method", ""))
    if reference_method not in methods:
        raise ConfigError("reference_method must be present in methods")

    budget = _require_mapping(config.get("budget"), "budget")
    evals_per_run = int(budget.get("evals_per_run", 0))
    if evals_per_run < 1:
        raise ConfigError("budget.evals_per_run must be >= 1")

    cma = _require_mapping(config.get("cma"), "cma")
    initial_sigma = float(cma.get("initial_sigma", 0.0))
    if initial_sigma <= 0.0:
        raise ConfigError("cma.initial_sigma must be > 0")
    base_popsize = int(cma.get("base_popsize", 0))
    if base_popsize < 1:
        raise ConfigError("cma.base_popsize must be >= 1")
    verbose = int(cma.get("verbose", -9))

    proxy_defaults = _require_mapping(config.get("proxy_defaults", {}), "proxy_defaults")
    _validate_proxy_overrides(proxy_defaults, "proxy_defaults")

    telemetry = _require_mapping(config.get("telemetry", {}), "telemetry")
    trace_mode_raw = telemetry.get("proxy_trace_mode", "off")
    if isinstance(trace_mode_raw, bool):
        trace_mode = "off" if trace_mode_raw is False else "full"
    else:
        trace_mode = str(trace_mode_raw).strip().lower()
    if trace_mode not in _ALLOWED_TRACE_MODES:
        raise ConfigError(f"telemetry.proxy_trace_mode must be one of {_ALLOWED_TRACE_MODES}")

    seeds = _require_mapping(config.get("seeds"), "seeds")
    eval_seeds = _require_scalar_list(seeds.get("eval"), "seeds.eval", int, min_value=0)

    runtime = _require_mapping(config.get("runtime", {}), "runtime")
    parallel_workers = int(runtime.get("parallel_workers", 1))
    if parallel_workers != 1:
        raise ConfigError("runtime.parallel_workers must be 1 in v1")

    analysis = _require_mapping(config.get("analysis", {}), "analysis")
    default_pairwise = _require_mapping(config.get("analysis", {}).get("default_pairwise", {}), "analysis.default_pairwise")
    if default_pairwise:
        method_a = str(default_pairwise.get("method_a", ""))
        method_b = str(default_pairwise.get("method_b", ""))
        if not method_a or not method_b:
            raise ConfigError("analysis.default_pairwise requires method_a and method_b")

    hypotheses = _require_mapping(config.get("hypotheses", {}), "hypotheses")
    checks = hypotheses.get("checks", [])
    if checks is None:
        checks = []
    if not isinstance(checks, list):
        raise ConfigError("hypotheses.checks must be a list")

    normalized_variants: list[dict[str, Any]] = []
    for idx, raw_variant in enumerate(config.get("variants", []) or []):
        raw_variant = _require_mapping(raw_variant, f"variants[{idx}]")
        normalized_variants.append(
            _normalized_variant(raw_variant, set(methods), where=f"variants[{idx}]")
        )

    normalized_sweeps: list[dict[str, Any]] = []
    for idx, raw_sweep in enumerate(config.get("sweeps", []) or []):
        raw_sweep = _require_mapping(raw_sweep, f"sweeps[{idx}]")
        sweep_id = _sanitize_variant_id(str(raw_sweep.get("sweep_id", "")))
        method = str(raw_sweep.get("method", "proxy_sigma_controller"))
        if method not in methods:
            raise ConfigError(f"sweeps[{idx}]: method {method!r} is not declared in methods")
        grid = _require_mapping(raw_sweep.get("grid"), f"sweeps[{idx}].grid")
        if not grid:
            raise ConfigError(f"sweeps[{idx}].grid must not be empty")
        for key, values in grid.items():
            if key not in _PROXY_FIELD_NAMES:
                raise ConfigError(f"sweeps[{idx}].grid has unknown proxy parameter {key!r}")
            vals = _require_list(values, f"sweeps[{idx}].grid.{key}")
            if not vals:
                raise ConfigError(f"sweeps[{idx}].grid.{key} must be non-empty")
        constants = _require_mapping(raw_sweep.get("constants", {}), f"sweeps[{idx}].constants")
        _validate_proxy_overrides(constants, f"sweeps[{idx}].constants")
        normalized_sweeps.append(
            {
                "sweep_id": sweep_id,
                "method": method,
                "grid": grid,
                "constants": constants,
            }
        )

    normalized = {
        "experiment_name": experiment_name,
        "matrix": {
            "functions": functions,
            "dimensions": dimensions,
            "noise_sigmas": noise_sigmas,
        },
        "methods": methods,
        "reference_method": reference_method,
        "budget": {"evals_per_run": evals_per_run},
        "cma": {
            "initial_sigma": initial_sigma,
            "base_popsize": base_popsize,
            "verbose": verbose,
        },
        "proxy_defaults": proxy_defaults,
        "variants": normalized_variants,
        "sweeps": normalized_sweeps,
        "telemetry": {
            "proxy_trace_mode": trace_mode,
        },
        "seeds": {
            "eval": eval_seeds,
        },
        "runtime": {
            "parallel_workers": parallel_workers,
        },
        "analysis": analysis,
        "hypotheses": {
            "checks": checks,
        },
    }

    return normalized


def _variant_from_sweep(
    *,
    sweep_id: str,
    method: str,
    key_order: list[str],
    values: tuple[Any, ...],
    constants: dict[str, Any],
) -> dict[str, Any]:
    parts: list[str] = [sweep_id]
    overrides = dict(constants)
    for key, value in zip(key_order, values, strict=True):
        overrides[key] = value
        value_token = str(value).replace(".", "p").replace("-", "m")
        parts.append(f"{key}_{value_token}")
    variant_id = _sanitize_variant_id("__".join(parts))
    return {
        "variant_id": variant_id,
        "method": method,
        "proxy_overrides": overrides,
    }


def expand_method_variants(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    methods = list(config["methods"])
    by_method: dict[str, list[dict[str, Any]]] = {method: [] for method in methods}

    seen_ids: set[str] = set()

    for variant in config.get("variants", []):
        variant_id = variant["variant_id"]
        if variant_id in seen_ids:
            raise ConfigError(f"Duplicate variant_id: {variant_id}")
        seen_ids.add(variant_id)
        by_method[variant["method"]].append(variant)

    for sweep in config.get("sweeps", []):
        grid: dict[str, list[Any]] = sweep["grid"]
        key_order = list(grid.keys())
        value_lists = [list(grid[key]) for key in key_order]
        for combo in itertools.product(*value_lists):
            variant = _variant_from_sweep(
                sweep_id=sweep["sweep_id"],
                method=sweep["method"],
                key_order=key_order,
                values=combo,
                constants=sweep["constants"],
            )
            variant_id = variant["variant_id"]
            if variant_id in seen_ids:
                raise ConfigError(f"Duplicate variant_id: {variant_id}")
            seen_ids.add(variant_id)
            by_method[variant["method"]].append(variant)

    for method in by_method:
        if not by_method[method]:
            by_method[method] = [
                {
                    "variant_id": None,
                    "method": method,
                    "proxy_overrides": {},
                }
            ]

    return by_method


def build_cells(matrix: dict[str, list[Any]]) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for function_name in matrix["functions"]:
        for dimension in matrix["dimensions"]:
            for noise_sigma in matrix["noise_sigmas"]:
                cells.append(
                    {
                        "function": str(function_name),
                        "dimension": int(dimension),
                        "noise_sigma": float(noise_sigma),
                    }
                )
    return cells
