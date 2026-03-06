from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from cmaes_proxy_sigma_controller import config_from_dict
from cmaes_proxy_sigma_controller.adapters.pycma import PyCMAAdapter
from cmaes_proxy_sigma_controller.telemetry import empty_proxy_row

from .io import sanitize_token
from .objectives import noisy_objective


@dataclass(frozen=True)
class MethodDefinition:
    method_id: str
    description: str
    popsize_multiplier: int = 1
    uses_proxy: bool = False


class MethodRegistry:
    def __init__(self) -> None:
        self._methods: dict[str, MethodDefinition] = {}

    def register(self, definition: MethodDefinition) -> None:
        if definition.method_id in self._methods:
            raise ValueError(f"Method already registered: {definition.method_id}")
        self._methods[definition.method_id] = definition

    def get(self, method_id: str) -> MethodDefinition:
        try:
            return self._methods[method_id]
        except KeyError as exc:
            raise ValueError(f"Unknown method: {method_id}") from exc

    def method_ids(self) -> set[str]:
        return set(self._methods)


def build_default_registry() -> MethodRegistry:
    registry = MethodRegistry()
    registry.register(
        MethodDefinition(
            method_id="vanilla_cma",
            description="Unmodified CMA-ES baseline",
            popsize_multiplier=1,
            uses_proxy=False,
        )
    )
    registry.register(
        MethodDefinition(
            method_id="proxy_sigma_controller",
            description="CMA-ES with external proxy sigma controller",
            popsize_multiplier=1,
            uses_proxy=True,
        )
    )
    return registry


def method_instance_name(method_id: str, variant_id: str | None) -> str:
    if variant_id:
        return f"{method_id}:{variant_id}"
    return method_id


def _stable_int(seed_text: str) -> int:
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _trace_file_name(
    *,
    phase: str,
    method_instance: str,
    function_name: str,
    dimension: int,
    noise_sigma: float,
    seed: int,
) -> str:
    method_token = sanitize_token(method_instance)
    fn_token = sanitize_token(function_name)
    noise_token = str(noise_sigma).replace(".", "p").replace("-", "m")
    return f"{phase}_{method_token}_{fn_token}_d{dimension}_n{noise_token}_seed{seed}.csv"


def run_experiment_job(job: dict[str, Any], registry: MethodRegistry, trace_root: Path | None = None) -> dict[str, Any]:
    started = time.time()

    phase = str(job["phase"])
    method_id = str(job["method_id"])
    method_def = registry.get(method_id)
    variant_id = job.get("variant_id")
    variant_id = str(variant_id) if variant_id is not None else None
    method_instance = method_instance_name(method_id, variant_id)

    function_name = str(job["function"])
    dimension = int(job["dimension"])
    noise_sigma = float(job["noise_sigma"])
    seed = int(job["seed"])

    eval_budget = int(job["eval_budget"])
    initial_sigma = float(job["initial_sigma"])
    base_popsize = int(job["base_popsize"])
    popsize = int(base_popsize * method_def.popsize_multiplier)
    cma_verbose = int(job.get("cma_verbose", -9))
    trace_mode = str(job.get("trace_mode", "off"))

    base_row = {
        "phase": phase,
        "method": method_id,
        "variant_id": variant_id,
        "method_instance": method_instance,
        "reference_method": str(job["reference_method"]),
        "function": function_name,
        "dimension": dimension,
        "noise_sigma": noise_sigma,
        "seed": seed,
        "eval_budget": eval_budget,
        "popsize": popsize,
        "initial_sigma": initial_sigma,
        "status": "ok",
        "error_message": "",
    }

    try:
        import cma  # noqa: PLC0415

        if eval_budget % popsize != 0:
            raise ValueError(
                "eval_budget must be divisible by method popsize for exact evaluation budgeting"
            )

        generations = eval_budget // popsize
        noise_seed = _stable_int(f"{function_name}|{dimension}|{noise_sigma:.12g}|{seed}")
        rng = np.random.default_rng(noise_seed)

        x0 = np.full(dimension, 3.0, dtype=float)
        es = cma.CMAEvolutionStrategy(
            x0.tolist(),
            initial_sigma,
            {
                "seed": seed,
                "popsize": popsize,
                "verbose": cma_verbose,
                "verb_disp": 0,
                "verb_log": 0,
                "maxiter": 10**9,
            },
        )

        adapter: PyCMAAdapter | None = None
        if method_def.uses_proxy:
            proxy_config = dict(job.get("proxy_config") or {})
            adapter = PyCMAAdapter(config_from_dict(proxy_config), initial_sigma=initial_sigma)

        eval_count = 0
        best_so_far = float("inf")

        for generation in range(1, generations + 1):
            candidates = np.asarray(es.ask(), dtype=float)
            fitness = [
                noisy_objective(function_name, point, noise_sigma, rng)
                for point in candidates
            ]
            es.tell(candidates.tolist(), fitness)
            best_so_far = min(best_so_far, float(np.min(np.asarray(fitness, dtype=float))))
            eval_count += popsize

            if adapter is not None:
                adapter.apply_post_tell(
                    es,
                    fitness=fitness,
                    generation=generation,
                    planned_generations=generations,
                    seed=seed,
                    function_name=function_name,
                    dimension=dimension,
                    noise_sigma=noise_sigma,
                    trace_mode=trace_mode,
                )

        row: dict[str, Any] = {
            **base_row,
            "n_evals": int(eval_count),
            "generations": int(generations),
            "final_best": float(best_so_far),
            "duration_sec": float(time.time() - started),
        }

        if adapter is not None:
            if trace_root is not None and adapter.trace_rows:
                trace_root.mkdir(parents=True, exist_ok=True)
                trace_path = trace_root / _trace_file_name(
                    phase=phase,
                    method_instance=method_instance,
                    function_name=function_name,
                    dimension=dimension,
                    noise_sigma=noise_sigma,
                    seed=seed,
                )
                adapter.write_trace(trace_path)

            summary = adapter.finalize(planned_generations=generations).to_dict()
            row.update(summary)
            relpath = row.get("proxy_trace_relpath")
            if relpath and trace_root is not None:
                try:
                    row["proxy_trace_relpath"] = str(Path(relpath).relative_to(trace_root.parent))
                except Exception:
                    row["proxy_trace_relpath"] = str(relpath)
        else:
            row.update(empty_proxy_row())

        return row
    except Exception as exc:  # pragma: no cover - defensive path
        return {
            **base_row,
            "status": "failed",
            "error_message": str(exc),
            "n_evals": 0,
            "generations": 0,
            "final_best": float("nan"),
            "duration_sec": float(time.time() - started),
            **empty_proxy_row(),
        }
