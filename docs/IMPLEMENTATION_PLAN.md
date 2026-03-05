# v0.1 Implementation Plan for `cmaes-proxy-sigma-controller`

## Summary
Implement a production-ready Python library (`Python 3.11 + numpy + pytest`) that provides a deterministic proxy sigma controller and a reference pycma adapter. Delivery is phased: core policy engine, adapter and telemetry, then tests and hardening. The implementation will follow the existing `TECHNICAL_DESIGN_SPEC.md` contract exactly, including phase logic, run-level occupancy metrics, and hybrid trace sampling.

## Important Changes or Additions to Public APIs/Interfaces/Types
New package API (no existing code to preserve):
- `ControllerConfig`
- `ControllerInput`
- `ControllerState`
- `ControllerDecision`
- `RunTelemetrySummary`
- `initialize(config, initial_sigma) -> ControllerState`
- `step(input, state, config) -> (ControllerDecision, ControllerState)`
- `finalize(state, planned_generations) -> RunTelemetrySummary`
- `PyCMAAdapter.apply_post_tell(es, fitness, meta) -> dict`

Telemetry output contract:
- Run-level fields: `proxy_sigma_factor_last`, `proxy_ema_snr_last`, `proxy_time_to_first_floor_gen`, `proxy_fraction_at_floor`, `proxy_n_floor_entries`, `proxy_n_floor_exits`, `proxy_n_down_steps`, `proxy_n_up_steps`, `proxy_n_neutral_steps`, `proxy_sigma_min_seen`, `proxy_sigma_max_seen`, `proxy_trace_written`, `proxy_trace_relpath`.
- Optional per-generation trace schema per spec.

## Implementation Plan

### Milestone 0: Repository Bootstrap and Tooling
Create these files:
- `/Users/velocityworks/IdeaProjects/cmaes-proxy-sigma-controller/pyproject.toml`
- `/Users/velocityworks/IdeaProjects/cmaes-proxy-sigma-controller/src/cmaes_proxy_sigma_controller/__init__.py`
- `/Users/velocityworks/IdeaProjects/cmaes-proxy-sigma-controller/tests/__init__.py`

Decisions:
- Build backend: `hatchling`.
- Runtime deps: `numpy`.
- Optional dep group `pycma`: `cma`.
- Dev deps: `pytest`, `pytest-cov`.

Done criteria:
- `python -m pip install -e .` works.
- `pytest` discovers tests.

### Milestone 1: Core Domain Model and Validation
Create:
- `src/cmaes_proxy_sigma_controller/types.py`
- `src/cmaes_proxy_sigma_controller/config.py`
- `src/cmaes_proxy_sigma_controller/errors.py`

Implement:
- Dataclasses for all canonical types.
- Strict config validation with explicit errors.
- Enum types for `phase` and `trace_mode`.
- Utility parser `ControllerConfig.from_dict`.

Done criteria:
- Validation rejects all invalid ranges/orderings in spec.
- Type objects are immutable where appropriate (`frozen=True`).

### Milestone 2: Deterministic Policy Core
Create:
- `src/cmaes_proxy_sigma_controller/stats.py`
- `src/cmaes_proxy_sigma_controller/policy.py`
- `src/cmaes_proxy_sigma_controller/phases.py`

Implement:
- `robust_spread` (`1.4826 * MAD + 1e-12`).
- SNR and EMA update.
- Base factor decision (`down`, `up`, `neutral`).
- Clamp logic and `was_clamped`.
- Phase transitions (`WARMUP`, `ACTIVE`, `CONSTRAINED`, `RECOVERY`).
- Recovery override with cap and cooldown behavior.
- Counter updates for occupancy, entries/exits, step counts, sigma extrema.
- `initialize`, `step`, `finalize` functions as canonical entry points.

Done criteria:
- Clamp invariant holds for every call.
- State progression is deterministic and replay-stable.

### Milestone 3: Telemetry and Trace Writing
Create:
- `src/cmaes_proxy_sigma_controller/telemetry.py`
- `src/cmaes_proxy_sigma_controller/trace.py`

Implement:
- Run-level summary builder returning exact required fields.
- Trace row serializer with exact schema.
- Deterministic hybrid selector:
  - target cells `(sphere,10)`, `(sphere,20)`, `(rosenbrock,10)`, `(rosenbrock,20)`;
  - or `seed % 10 == 0`.
- Trace modes `off`, `hybrid`, `full`.
- Streaming CSV writes to avoid large in-memory accumulation.

Done criteria:
- Trace inclusion/exclusion is exact for selector test matrix.
- Trace metadata includes run identity and config hash.

### Milestone 4: pycma Adapter
Create:
- `src/cmaes_proxy_sigma_controller/adapters/__init__.py`
- `src/cmaes_proxy_sigma_controller/adapters/pycma.py`

Implement:
- `PyCMAAdapter` that:
  - accepts host context (`fitness`, generation, seed/function/dim/noise meta, planned generations);
  - calls policy `step`;
  - applies returned `next_sigma` to `es.sigma`;
  - returns diagnostics payload and optional trace write status.
- Enforce no hidden post-controller sigma scaling in adapter path.

Done criteria:
- Adapter operates post-`tell` with no direct mutation of CMA-ES internals beyond `es.sigma`.
- Non-finite/invalid inputs fail-fast by default, optional fail-open via config flag.

### Milestone 5: Reference Runner and Example
Create:
- `src/cmaes_proxy_sigma_controller/reference_runner.py`
- `examples/pycma_sphere_demo.py`

Implement:
- Lightweight reference loop to demonstrate wiring for `vanilla` vs `proxy`.
- Writes run-level CSV and optional trace files.
- Keeps scope intentionally small, not a benchmark platform replacement.

Done criteria:
- Example run succeeds locally with `cma` installed.
- Output rows include all required proxy fields.

### Milestone 6: Tests and Verification
Create:
- `tests/test_config_validation.py`
- `tests/test_stats.py`
- `tests/test_policy_core.py`
- `tests/test_phase_transitions.py`
- `tests/test_occupancy_metrics.py`
- `tests/test_trace_selector.py`
- `tests/test_pycma_adapter_smoke.py`
- `tests/test_determinism_replay.py`

Implement required coverage:
- Numeric correctness for MAD/SNR/EMA.
- Clamp boundaries and epsilon floor detection.
- Entry/exit counting correctness.
- Recovery and cooldown behavior.
- Hybrid trace selector exactness.
- Non-proxy null telemetry behavior in reference runner.
- Replay determinism with fixed synthetic observation sequence.

Done criteria:
- All tests pass.
- Coverage threshold: `>= 90%` on policy, phase, telemetry modules.

### Milestone 7: Documentation and Release Packaging
Create:
- `/Users/velocityworks/IdeaProjects/cmaes-proxy-sigma-controller/README.md`
- `/Users/velocityworks/IdeaProjects/cmaes-proxy-sigma-controller/CHANGELOG.md`
- `/Users/velocityworks/IdeaProjects/cmaes-proxy-sigma-controller/docs/RUNBOOK.md`

Document:
- Installation and extras (`.[pycma]`).
- Minimal integration snippet.
- Telemetry schema table.
- Determinism and failure mode notes.
- Version tag `v0.1.0`.

Done criteria:
- New user can run example and produce telemetry artifacts from docs only.

## Data Flow and I/O Contract
Input per generation:
- `fitness`, `generation`, `current_sigma`, `initial_sigma`, `planned_generations`, run metadata.

Policy output:
- `next_sigma`, `factor_applied`, `was_clamped`, `phase_after`, diagnostics map.

Persisted outputs:
- run-level summary row for every run;
- optional per-generation trace file according to `trace_mode`.

## Edge Cases and Failure Modes to Handle Explicitly
- Empty `fitness`.
- Non-finite values in `fitness`.
- `current_sigma <= 0` or `initial_sigma <= 0`.
- `snr_up_threshold <= snr_down_threshold`.
- Planned generations not positive.
- Clamp edge with float tolerance near floor.
- Recovery oscillation when at-floor toggles rapidly.

## Test Cases and Scenarios
- Scenario A: Stable noisy run with mostly neutral steps and no floor entry.
- Scenario B: Early floor dominance triggers constrained phase then recovery.
- Scenario C: High SNR regime with sustained controlled expansion.
- Scenario D: Hybrid trace selector across target and non-target cells.
- Scenario E: Replay determinism with identical observation stream.
- Scenario F: Invalid config/input failures with explicit error typing.

## Rollout and Monitoring
Phase rollout:
- Internal QA using synthetic sequences.
- Adapter smoke tests with pycma sphere objective.
- Controlled benchmark pilot with fixed seeds.
- Promotion to default use only after telemetry schema and determinism checks pass.

Monitoring metrics:
- distribution of `proxy_fraction_at_floor`,
- distribution of `proxy_time_to_first_floor_gen`,
- step-count mix (`down/up/neutral`),
- failure counts by validation/error type.

## Explicit Assumptions and Defaults
- Language: Python 3.11.
- Core dependency set: `numpy`; pycma integration via optional extra.
- Fail mode default: fail-fast.
- Trace mode default: `off`; `hybrid` used for mechanism studies.
- Objective direction supported in v0.1: minimization only.
- Repository remains standalone and does not import code from `/Users/velocityworks/IdeaProjects/lr-adapt-proxy`.
