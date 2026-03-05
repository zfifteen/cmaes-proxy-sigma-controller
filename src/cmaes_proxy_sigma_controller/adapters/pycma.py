from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from ..config import canonicalize_function_name, validate_config
from ..errors import SigmaDriftError
from ..policy import finalize, initialize, step
from ..telemetry import PROXY_SCHEMA_VERSION
from ..trace import should_trace_proxy_run, write_trace_csv
from ..types import ControllerConfig, ControllerInput, ControllerState, RunTelemetrySummary, TraceMode


class PyCMAAdapter:
    """Reference pycma adapter that only mutates es.sigma post-tell."""

    def __init__(
        self,
        config: ControllerConfig,
        initial_sigma: float,
        *,
        assert_sigma_drift: bool = False,
    ) -> None:
        validate_config(config)
        self.config = config
        self.initial_sigma = float(initial_sigma)
        self.state: ControllerState = initialize(config, initial_sigma)
        self.assert_sigma_drift = bool(assert_sigma_drift)
        self._last_applied_sigma: float | None = None
        self._trace_rows: list[dict[str, Any]] = []

    def apply_post_tell(
        self,
        es: Any,
        *,
        fitness: list[float] | tuple[float, ...],
        generation: int,
        planned_generations: int,
        seed: int,
        function_name: str,
        dimension: int,
        noise_sigma: float,
        trace_mode: TraceMode | str | None = None,
    ) -> dict[str, Any]:
        sigma_before = float(es.sigma)
        if self.assert_sigma_drift and self._last_applied_sigma is not None:
            if sigma_before != self._last_applied_sigma:
                raise SigmaDriftError(
                    f"Host sigma drift detected: expected {self._last_applied_sigma}, observed {sigma_before}"
                )

        fn = canonicalize_function_name(function_name)
        controller_input = ControllerInput(
            generation=int(generation),
            fitness=tuple(float(v) for v in fitness),
            current_sigma=sigma_before,
            initial_sigma=self.initial_sigma,
            planned_generations=int(planned_generations),
            seed=int(seed),
            function_name=fn,
            dimension=int(dimension),
            noise_sigma=float(noise_sigma),
        )

        phase_before = self.state.phase
        decision, next_state = step(controller_input, self.state, self.config)
        self.state = next_state

        es.sigma = float(decision.next_sigma)
        self._last_applied_sigma = float(es.sigma)

        mode = trace_mode if trace_mode is not None else self.config.trace_mode
        if should_trace_proxy_run(fn, int(dimension), int(seed), mode):
            self.state = replace(self.state, trace_written=True)
            self._trace_rows.append(
                {
                    "proxy_schema_version": PROXY_SCHEMA_VERSION,
                    "generation": int(generation),
                    "sigma_before": float(sigma_before),
                    "sigma_after": float(es.sigma),
                    "at_floor": bool(self.state.prev_at_floor),
                    "was_clamped": bool(decision.was_clamped),
                    "proxy_sigma_factor": float(decision.factor_applied),
                    "proxy_ema_snr": float(decision.diagnostics.get("proxy_ema_snr", 0.0)),
                    "proxy_signal": float(decision.diagnostics.get("proxy_signal", 0.0)),
                    "proxy_noise": float(decision.diagnostics.get("proxy_noise", 0.0)),
                    "proxy_snr": float(decision.diagnostics.get("proxy_snr", 0.0)),
                    "proxy_current_best": float(decision.diagnostics.get("proxy_current_best", 0.0)),
                    "proxy_best_so_far": float(decision.diagnostics.get("proxy_best_so_far", 0.0)),
                    "phase_before": phase_before.value,
                    "phase_after": decision.phase_after.value,
                }
            )

        return dict(decision.diagnostics)

    def write_trace(self, path: Path) -> None:
        write_trace_csv(path, self._trace_rows)
        self.state = replace(self.state, trace_written=True, trace_relpath=str(path))

    def finalize(self, planned_generations: int) -> RunTelemetrySummary:
        return finalize(self.state, planned_generations)

    @property
    def trace_rows(self) -> list[dict[str, Any]]:
        return list(self._trace_rows)
