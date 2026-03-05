# Technical Design Specification

## Document Status
This specification is canonical for implementation of the `cmaes-proxy-sigma-controller` baseline controller (version `v0.1-r3`). This revision resolves peer-review blocking ambiguities before coding begins.

## 1. Purpose
`cmaes-proxy-sigma-controller` is an external step-size controller for CMA-ES that modifies only `sigma` through a bounded, observable policy loop. It is designed to improve decision quality under noisy optimization by explicitly tracking run-time regime occupancy and preventing early clamp-dominant behavior.

## 2. Scope
In scope for `v0.1`:
- Deterministic proxy controller core.
- Host adapter contract for post-`tell` sigma updates.
- Structured telemetry (run-level always on, per-generation trace optional/hybrid).
- Mechanism-aware state machine with bounded recovery behavior.
- Reproducible configuration contract.

Out of scope for `v0.1`:
- Modifying CMA-ES covariance, recombination, or evolution path internals.
- Restart policy orchestration or restart-like control paths.
- Auto-tuning across tasks.
- Claims of universal superiority.

## 3. Design Constraints
- Proxy-only: controller must not require privileged optimizer internal state.
- One control output: next sigma value and applied multiplicative factor.
- Safety first: all sigma outputs must respect clamp bounds relative to initial sigma.
- Deterministic decisions given identical observations and config.
- Full auditability: each decision must be explainable from recorded inputs and state.
- Integration sequencing must prevent any hidden sigma mutation outside the defined adapter step.

## 4. Operating Model
The host optimizer calls the controller exactly once per generation, after objective evaluation and completion of the host update (`tell`). The controller:
- consumes generation observations,
- updates internal controller state,
- computes a sigma action,
- returns action plus diagnostics.

Host then applies action by setting optimizer sigma to returned value. No other sigma mutation may occur between this assignment and the next generation's `tell` completion.

## 5. Terminology
- `sigma`: CMA-ES sampling step-size.
- `signal`: observed positive best-improvement per generation.
- `noise`: robust spread estimate from generation fitness values plus configured floor.
- `snr`: `signal / noise`.
- `ema_snr`: exponentially smoothed SNR.
- `floor`: lower sigma clamp (`initial_sigma * sigma_min_ratio`).
- `ceiling`: upper sigma clamp (`initial_sigma * sigma_max_ratio`).
- `at_floor`: generation where post-action sigma is at floor under mixed tolerance.
- `regime occupancy`: temporal share and transitions of constrained behavior.
- `recovery_fire`: one-generation bounded recovery boost event.

## 6. Public Interfaces

### 6.1 Core Types (language-agnostic)

`ControllerConfig`
- `ema_alpha: float` in `(0, 1]`
- `ema_init_mode: enum("first_observation", "zero")` default `"first_observation"`
- `snr_down_threshold: float` in `(0, +inf)`
- `snr_up_threshold: float` in `(0, +inf)`, must satisfy `snr_up_threshold > snr_down_threshold`
- `sigma_down_factor: float` in `(0, 1)`
- `sigma_up_factor: float` in `(1, +inf)`
- `sigma_min_ratio: float` in `(0, 1]`
- `sigma_max_ratio: float` in `[1, +inf)`
- `warmup_generations: int` in `[0, +inf)`
- `recovery_enabled: bool`
- `recovery_min_streak: int` in `[1, +inf)`
- `recovery_boost_factor: float` in `[1, +inf)`
- `recovery_cooldown_generations: int` in `[0, +inf)`
- `noise_floor_abs: float` in `(0, +inf)` default `1e-12`
- `noise_floor_rel: float` in `[0, +inf)` default `1e-12`
- `at_floor_atol: float` in `[0, +inf)` default `1e-12`
- `at_floor_rtol: float` in `[0, +inf)` default `1e-9`
- `trace_mode: enum("off", "hybrid", "full")`
- `failure_policy: enum("fail_fast", "fail_open")` default `"fail_fast"`

`ControllerInput`
- `generation: int` (1-based)
- `fitness: array<float>` (non-empty)
- `current_sigma: float` (`> 0`)
- `initial_sigma: float` (`> 0`)
- `planned_generations: int` (`> 0`)
- `seed: int` (`>= 0`)
- `function_name: string` (canonical lower-case token)
- `dimension: int` (`> 0`)
- `noise_sigma: float` (`>= 0`)

`ControllerState`
- `best_so_far: float | null`
- `ema_snr: float`
- `phase: enum("WARMUP", "ACTIVE", "CONSTRAINED", "RECOVERY")`
- `floor_streak: int`
- `prev_at_floor: bool`
- `cooldown_remaining: int`
- `n_floor_entries: int`
- `n_floor_exits: int`
- `n_down_steps: int`
- `n_up_steps: int`
- `n_neutral_steps: int`
- `n_floor_gens: int`
- `first_floor_gen: int | null`
- `sigma_min_seen: float`
- `sigma_max_seen: float`
- `trace_written: bool`
- `trace_relpath: string | null`

`ControllerDecision`
- `next_sigma: float`
- `factor_applied: float`
- `was_clamped: bool`
- `phase_after: enum("WARMUP", "ACTIVE", "CONSTRAINED", "RECOVERY")`
- `diagnostics: map<string, scalar>`

`RunTelemetrySummary`
- Required run-level fields in Section 8.1, including `proxy_schema_version`.

### 6.2 API Methods

`initialize(config, initial_sigma) -> ControllerState`
- validates config and initializes state.
- initializes `ema_snr` as `0.0` when `ema_init_mode == "zero"`; otherwise `ema_snr` is initialized from first observation as defined in Section 7.1.

`step(input, state, config) -> (decision, next_state)`
- computes and returns single-generation action.

`finalize(state, planned_generations) -> RunTelemetrySummary`
- returns run-level telemetry summary for persistence.

## 7. Control Policy

### 7.1 Signal, Noise, and EMA Initialization
For minimization:
- `current_best = min(fitness_t)`
- `prev_best = best_so_far if set else current_best`
- `signal_t = max(prev_best - current_best, 0)`
- `noise_floor_t = max(noise_floor_abs, noise_floor_rel * max(1.0, abs(median(fitness_t))))`
- `noise_t = 1.4826 * MAD(fitness_t) + noise_floor_t`
- `snr_t = signal_t / noise_t`

EMA update:
- if `best_so_far is null` and `ema_init_mode == "first_observation"`, set `ema_t = snr_t`
- else use `ema_t = ema_alpha * snr_t + (1 - ema_alpha) * ema_{t-1}`

### 7.2 Base Action (non-recovery)
- If `ema_t < snr_down_threshold`, select `factor_base = sigma_down_factor`
- Else if `ema_t > snr_up_threshold`, select `factor_base = sigma_up_factor`
- Else select `factor_base = 1.0`

### 7.3 Clamp, Tolerance, and `was_clamped`
- `floor_sigma = initial_sigma * sigma_min_ratio`
- `ceiling_sigma = initial_sigma * sigma_max_ratio`
- `floor_tol = max(at_floor_atol, at_floor_rtol * max(1.0, abs(floor_sigma)))`
- `ceiling_tol = max(at_floor_atol, at_floor_rtol * max(1.0, abs(ceiling_sigma)))`
- `unclamped = current_sigma * factor_applied`
- `next_sigma = clip(unclamped, floor_sigma, ceiling_sigma)`
- `was_clamped = (next_sigma != unclamped)`
- `at_floor = abs(next_sigma - floor_sigma) <= floor_tol`

`was_clamped` reports whether clipping changed the proposed sigma value. This intentionally counts near-boundary changes where clipping occurs within tolerance.

### 7.4 Transition Ordering and State Machine
Per-generation normative order:
1. Validate input.
2. Decrement cooldown: `cooldown_t = max(cooldown_remaining - 1, 0)`.
3. Compute SNR/EMA and `factor_base`.
4. Determine `recovery_fire` from prior state:
   - `phase_prev == CONSTRAINED`
   - `recovery_enabled == true`
   - `prev_at_floor == true`
   - `floor_streak >= recovery_min_streak`
   - `cooldown_t == 0`
5. If `recovery_fire`, set `factor_applied = max(1.0, min(factor_base * recovery_boost_factor, sigma_up_factor * recovery_boost_factor))`; else `factor_applied = factor_base`.
6. Apply clamp and compute `at_floor`.
7. Update floor streak: `floor_streak_t = floor_streak + 1 if at_floor else 0`.
8. Compute `phase_after` using precedence table below.
9. Update counters and extrema.
10. Set cooldown for next state:
   - if `recovery_fire`, `cooldown_next = recovery_cooldown_generations`
   - else `cooldown_next = cooldown_t`.

Transition table (ordered by precedence):

| Rule | Condition | `phase_after` |
|---|---|---|
| T1 | `generation <= warmup_generations` | `WARMUP` |
| T2 | `generation > warmup_generations` and `recovery_fire` | `RECOVERY` |
| T3 | `generation > warmup_generations` and `at_floor` and `floor_streak_t >= recovery_min_streak` | `CONSTRAINED` |
| T4 | otherwise | `ACTIVE` |

Implications:
- No sink state exists when `recovery_enabled=false`; constrained runs return to `ACTIVE` as soon as `at_floor` becomes false.
- `RECOVERY` is transient by construction and cannot repeat without re-entering `CONSTRAINED`.
- `WARMUP` suppresses recovery transitions only; base sigma actions and floor-streak accumulation still occur during warmup.

State invariants:
- `WARMUP` may only occur when `generation <= warmup_generations`.
- No transition from `ACTIVE` or `CONSTRAINED` back to `WARMUP`.
- `first_floor_gen` is write-once.
- `n_floor_entries - n_floor_exits` is always `0` or `1`.

### 7.5 Counters and Occupancy
Per generation, update:
- step counters (`n_down_steps`, `n_up_steps`, `n_neutral_steps`) from `factor_applied`.
- floor occupancy (`n_floor_gens`, `first_floor_gen`).
- entry/exit counts using `prev_at_floor` and current `at_floor`.
- sigma extrema (`sigma_min_seen`, `sigma_max_seen`).
- `prev_at_floor <- at_floor` for next step.

Derived at finalize:
- `fraction_at_floor = n_floor_gens / planned_generations`
- `time_to_first_floor_gen = first_floor_gen if set else planned_generations`

## 8. Telemetry Contract

### 8.1 Required Run-Level Columns (proxy runs)
- `proxy_schema_version` (integer, required; `1` for `v0.1-r3`)
- `proxy_sigma_factor_last`
- `proxy_ema_snr_last`
- `proxy_time_to_first_floor_gen`
- `proxy_fraction_at_floor`
- `proxy_n_floor_entries`
- `proxy_n_floor_exits`
- `proxy_n_down_steps`
- `proxy_n_up_steps`
- `proxy_n_neutral_steps`
- `proxy_sigma_min_seen`
- `proxy_sigma_max_seen`
- `proxy_trace_written`
- `proxy_trace_relpath`

For non-proxy methods, these fields must be null/NaN except optional global schema metadata maintained by the host.

### 8.2 Optional Per-Generation Trace Schema
- `proxy_schema_version`
- `generation`
- `sigma_before`
- `sigma_after`
- `at_floor`
- `was_clamped`
- `proxy_sigma_factor`
- `proxy_ema_snr`
- `proxy_signal`
- `proxy_noise`
- `proxy_snr`
- `proxy_current_best`
- `proxy_best_so_far`
- `phase_before`
- `phase_after`

### 8.3 Hybrid Trace Selector (deterministic and portable)
Normalization and selector rules are normative:
- `function_name` must be canonicalized before selector checks: `strip().lower()`.
- Supported canonical names for target-cell tracing: `sphere`, `rosenbrock`.
- `seed` must be non-negative.
- Trace when method is proxy and either:
  - `(function_name, dimension)` in `{(sphere,10), (sphere,20), (rosenbrock,10), (rosenbrock,20)}`, or
  - `seed % 10 == 0`.

`trace_mode` behavior:
- `off`: no per-generation traces.
- `hybrid`: deterministic selector above.
- `full`: all proxy runs traced.

## 9. Configuration Contract

### 9.1 YAML Example
```yaml
controller:
  name: cmaes_proxy_sigma_controller
  ema_alpha: 0.2
  ema_init_mode: first_observation
  snr_down_threshold: 0.08
  snr_up_threshold: 0.25
  sigma_down_factor: 0.90
  sigma_up_factor: 1.03
  sigma_min_ratio: 0.05
  sigma_max_ratio: 10.0
  warmup_generations: 5
  recovery_enabled: true
  recovery_min_streak: 6
  recovery_boost_factor: 1.05
  recovery_cooldown_generations: 8
  noise_floor_abs: 1e-12
  noise_floor_rel: 1e-12
  at_floor_atol: 1e-12
  at_floor_rtol: 1e-9
  trace_mode: hybrid
  failure_policy: fail_fast
```

### 9.2 Validation Rules
Reject config at initialization if:
- threshold ordering invalid,
- factors outside ranges,
- `sigma_min_ratio > sigma_max_ratio`,
- generation/count parameters negative,
- unsupported `trace_mode`,
- unsupported `failure_policy`,
- negative tolerance or noise-floor values.

Reject input at step time if:
- `seed < 0`,
- `function_name` is not canonical lower-case token.

## 10. Integration Contract with CMA-ES Host
Normative generation sequence:
1. `ask` candidates.
2. evaluate objective.
3. call host `tell` and allow full internal CMA-ES update completion.
4. read `current_sigma` from host after `tell` completes.
5. call controller `step` with that `current_sigma`.
6. assign `es.sigma = decision.next_sigma`.
7. do not mutate `es.sigma` again before next generation `tell` completion.

Additional adapter requirements:
- Adapter must expose a sigma-drift assertion mode that raises if host mutates sigma between steps.
- Adapter must include `phase_before` and `phase_after` in trace rows.

## 11. Failure Handling
Hard failure conditions:
- empty fitness vector,
- non-finite fitness values where robust spread cannot be computed,
- non-positive sigma inputs,
- invalid/corrupt controller state.

`failure_policy` behavior:
- `fail_fast`: raise a typed exception with generation/seed context.
- `fail_open`: return no-op action (`next_sigma = current_sigma`, `factor_applied = 1.0`) and emit diagnostics keys:
  - `proxy_failure_policy`,
  - `proxy_failure_reason`,
  - `proxy_failure_generation`.

`failure_policy` is controller-level configuration only and must not be overridden per call.

## 12. Determinism and Reproducibility
Two deterministic replay tiers are defined:

Tier A (same-runtime bitwise replay):
- Same OS, CPU architecture, Python version, dependency versions, and controller build.
- Identical input sequence and config must produce bit-identical serialized controller outputs.
- This tier is the required acceptance gate for `v0.1`.

Tier B (cross-runtime tolerance replay):
- Across different but supported runtimes/platforms, outputs must satisfy tolerance checks:
  - `abs(x_ref - x_test) <= max(1e-12, 1e-9 * max(1.0, abs(x_ref)))` for float outputs.
- This tier is required for compatibility reporting but is not a release blocker for `v0.1`.

Trace files must include run identity and config hash metadata.

## 13. Performance Requirements
- Per-step controller overhead target: under 100 microseconds on commodity CPU for population sizes up to 64.
- Telemetry memory overhead in `hybrid` mode must remain bounded by streaming writes.
- Hybrid tracing must include a storage budget check in CI-sized sweeps.

## 14. Acceptance Criteria

### 14.1 Implementation Accepted (release gate)
`v0.1` implementation is accepted only when all are true, in order:
1. Config and type validation tests pass.
2. Policy invariants pass (clamp, tolerance, counters, transition table behavior).
3. Adapter integration tests pass (timing, schema, no hidden sigma mutations).
4. Hybrid selector determinism tests pass.
5. Tier A replay determinism passes.
6. End-to-end smoke run (`vanilla` + `proxy`) completes with required telemetry fields.

### 14.2 Mechanism Validated (research gate, separate)
Mechanism claims are validated only via a separate pre-registered evaluation protocol. Passing implementation tests does not imply mechanism validation.

## 15. Test Plan

### 15.1 Unit Tests
- robust spread and noise-floor numeric correctness on known vectors.
- SNR/EMA update correctness for both `ema_init_mode` options.
- clamp behavior at floor/ceiling boundaries with mixed tolerance.
- phase transition table correctness and cooldown behavior.
- occupancy counter correctness (entries/exits/time-to-first/fraction).
- config validation rejects invalid settings.

### 15.2 Integration Tests
- two-method run (`vanilla`, `proxy`) with small seed set verifies schema and adapter sequencing.
- hybrid tracing writes traces only for selected runs.
- non-proxy rows preserve backward compatibility with null proxy fields.
- sigma-drift assertion detects unauthorized post-step sigma mutation.

### 15.3 Statistical/Mechanism Evaluation Hooks (non-normative)
- export artifacts needed by external analysis protocol.
- provide endpoint and occupancy telemetry for downstream models.
- this section defines data availability only; no directional hypothesis pass/fail criteria are normative in this implementation spec.

## 16. Versioning and Compatibility
- This specification defines `v0.1-r3` baseline behavior.
- `proxy_schema_version` is mandatory in run-level and trace outputs.
- `proxy_schema_version` is a major schema integer only and increments on breaking changes.
- Additive optional telemetry fields are minor changes and do not increment `proxy_schema_version`; they are tracked in release notes and spec revision tags.
- Required-field additions, field rename/removal, type change, or semantic reinterpretation are breaking and must increment `proxy_schema_version`.
- Any change to state machine semantics or recovery trigger logic: major controller version bump.

## 17. Security and Safety Posture
- No external network dependencies in controller core.
- No execution of untrusted configuration expressions.
- Telemetry paths must be sanitized by host adapter to avoid path traversal.
- Trace file creation must fail safely under invalid paths according to `failure_policy`.

## 18. Open Issues for Next Spec Revision
- task-conditioned default profiles,
- optional adaptive floor policy with proof obligations,
- fixed-effects analysis integration as first-class report artifact,
- optional cross-language reference implementation for selector parity.

## 19. Implementation Checklist (Normative)
- Implement core types and config validator (including `failure_policy`, tolerance, and noise floor fields).
- Implement deterministic policy core with ordered transition evaluation and mixed tolerance logic.
- Implement host adapter contract with strict post-`tell` timing.
- Implement run-level telemetry summary persistence with `proxy_schema_version`.
- Implement optional trace writer with canonicalized hybrid selector.
- Implement unit and integration test suite, including Tier A replay gate.
- Publish separate mechanism-evaluation protocol document before making mechanism claims.
