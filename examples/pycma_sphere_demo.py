from __future__ import annotations

from cmaes_proxy_sigma_controller.reference_runner import run_reference
from cmaes_proxy_sigma_controller.types import ControllerConfig


def main() -> None:
    vanilla = run_reference(
        method="vanilla",
        function_name="sphere",
        dimension=10,
        seed=0,
        noise_sigma=0.1,
        initial_sigma=0.5,
        popsize=10,
        planned_generations=10,
    )
    proxy = run_reference(
        method="proxy",
        function_name="sphere",
        dimension=10,
        seed=0,
        noise_sigma=0.1,
        initial_sigma=0.5,
        popsize=10,
        planned_generations=10,
        controller_config=ControllerConfig(),
    )
    print("vanilla:", vanilla["final_best"])
    print("proxy:", proxy["final_best"], "schema", proxy["proxy_schema_version"])


if __name__ == "__main__":
    main()
