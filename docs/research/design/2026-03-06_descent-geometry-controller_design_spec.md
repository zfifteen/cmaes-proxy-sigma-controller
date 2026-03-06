# Descent Geometry Controller (DGC)
## Data-Driven Design Specification (New Dedicated Repository)

Document version: `v1.0-draft`  
Date: `2026-03-06`  
Status: `Implementation-ready design spec`  
Primary evidence source: `docs/research/reports/descent-geometry/2026-03-06_deep-mapping-report.md`

---

## Part I: Accessible Narrative (Why This Design Exists)

### 1. The practical problem this controller is solving

CMA-ES already adapts step size internally. That is a strength, not a weakness. An external controller is only justified if it can improve outcomes in regimes where internal adaptation tends to get trapped in unproductive behavior, and only if it does that without damaging regimes where vanilla CMA-ES is already well tuned.

The new descent-geometry suite was run specifically to test whether we can identify a robust mechanism for when external control helps versus hurts. The suite result is clear: the key mechanism is not “any adaptive wrapper helps,” and it is not “AWF thresholds alone drive outcome.” The dominant mechanism is **descent geometry**, especially the lower-floor geometry set by `r_min`.

### 2. What the data says in plain language

Across three stages (dense map, interaction map, and full-trace anchors), the strongest and most stable control variable is `r_min`.

- Correlation between `r` and win-rate is strongly negative in every stage (`-0.949`, `-0.946`, `-0.989`).
- Behavior metrics confirm mechanism, not just scoreboard shifts:
  - `descent_volume_fraction` tracks win-rate strongly (`0.918`, `0.851`, `0.949`).
  - Hitting floor later is good; spending many generations at floor is bad.

In practical terms: when floor geometry is too permissive in the wrong direction (high `r_min`), the run spends too much time in constrained behavior. That reduces useful search dynamics.

### 3. The most important corrected finding: no universal threshold

A previous interpretation framed `r_min=0.05` as a universal boundary. The new data rejects that framing.

What exists is a **landscape-specific tolerance curve**, not a single universal transition value.

Empirical hierarchy from dense sweep:

1. `ellipsoid_cond1e6` (strongest beneficiary)
2. `rastrigin`
3. `rosenbrock` (fragile)
4. `sphere` (no net recovery)

Dense function-level improvement counts (64 geometry variants):

- `ellipsoid_cond1e6`: `57/64` improved
- `rastrigin`: `45/64` improved
- `rosenbrock`: `14/64` improved
- `sphere`: `0/64` improved

This means a production controller cannot be “one geometry for all landscapes.”

### 4. Why sphere changes the design philosophy

Sphere is decisive because it never shows net function-level recovery in this suite, even under the most aggressive tested geometry (`k=0.86`, `r=0.02`, sharpness `7.54`).

That is not a tiny detail. It means the external controller can be intrinsically counterproductive on smooth isotropic landscapes where vanilla CMA-ES is already near-optimal. The design response is straightforward:

- The controller must have explicit **harm-minimizing behavior** for sphere-like workloads.
- “Always-on aggressive adaptation” is the wrong default.

### 5. Why thresholds still matter (but as secondary controls)

Thresholds are still real and useful, but their role is secondary to geometry.

In fixed geometry `k=0.97, r=0.05`, threshold changes move overall median delta from `-6.011` to `-44.113`. That swing is not Rosenbrock-only; ellipsoid contributes most magnitude, with additional directional improvement on rastrigin and rosenbrock.

So the design principle is:

- Geometry is primary policy surface.
- Threshold controls are secondary modulation for amplification + harm reduction.

### 6. Design consequence

The new controller should be **geometry-prioritized and profile-driven**:

1. Geometry envelope (especially `r_min`) defines safe/unsafe regime.
2. Explicit landscape profiles choose defaults and guardrails.
3. Threshold logic modulates within profile constraints.
4. Telemetry must remain rich enough to verify mechanism claims, not only endpoints.

That is what this specification defines.

---

## Part II: Technical Implementation Specification

## 7. Scope, goals, and non-goals

### 7.1 Goals

1. Build a dedicated repository implementing a deterministic external sigma controller with geometry-first policy.
2. Enforce profile-specific geometry guardrails to prevent known harmful regimes.
3. Preserve mechanism observability (descent/floor occupancy and sigma-volume metrics).
4. Provide reproducible comparative evaluation against vanilla CMA-ES.

### 7.2 Non-goals (v1)

1. No mutation of CMA-ES covariance/evolution-path internals.
2. No automatic online landscape inference in v1.
3. No claim of universal superiority across all landscapes.
4. No requirement for backward compatibility with current repo schemas (clean-break design).

## 8. Repository architecture (new repo)

Recommended package layout:

- `dgc/core/policy.py`  
Geometry-prioritized decision policy.
- `dgc/core/state.py`  
Controller state model and state transitions.
- `dgc/profiles/catalog.py`  
Landscape profile definitions and defaults.
- `dgc/adapter/pycma.py`  
Reference host adapter (post-`tell` sigma apply).
- `dgc/telemetry/schema.py`  
Run summary and trace schemas.
- `dgc/evaluation/`  
Benchmark orchestration and analysis helpers.
- `dgc/config/schema.py`  
Config parsing + validation (strict).

## 9. Public interfaces

### 9.1 `ControllerConfig`

```yaml
profile_id: sphere | rosenbrock | rosenbrock_active_tight | rastrigin | ellipsoid | unknown
mode: active | pass_through
initial_sigma: float > 0

geometry:
  k_down: float (0,1)
  r_min: float (0,1)
  sigma_max_ratio: float >= 1

thresholds:
  snr_down: float > 0
  snr_up: float > snr_down
  ema_alpha: float (0,1]
  ema_init_mode: first_snr | zero

actions:
  k_up: float > 1
  warmup_generations: int >= 0

occupancy:
  floor_streak_constrained: int >= 1
  recovery_boost: float >= 1
  recovery_cooldown_gens: int >= 0

safety:
  atol: float >= 0
  rtol: float >= 0
  noise_floor_abs: float > 0
  noise_floor_rel: float >= 0
  fail_policy: fail_fast | fail_open
  allow_high_r_override: bool
  allow_active_sphere_profile: bool

telemetry:
  trace_mode: off | hybrid | full
  trace_cells: optional explicit list
```

Validation rules (hard):

1. `snr_up > snr_down`.
2. `k_down < 1 < k_up`.
3. `r_min <= 0.20` unless `allow_high_r_override=true`.
4. `profile_id=sphere` with `mode=active` requires `allow_active_sphere_profile=true` (prevent accidental harm mode).
5. `mode=pass_through` ignores adaptive action outputs and emits `factor_applied=1.0` each generation.
6. `warmup_generations < planned_generations` for every run; violation is handled by `fail_policy`.

### 9.2 `StepInput`

```yaml
generation: int >= 1
fitness: non-empty array[float]
current_sigma: float > 0
initial_sigma: float > 0
planned_generations: int >= 1
seed: int >= 0
function_name: string
dimension: int >= 1
noise_sigma: float >= 0
```

### 9.3 `StepOutput`

```yaml
next_sigma: float > 0
factor_applied: float > 0
phase_after: warmup | active | constrained | recovery | pass_through
was_clamped: bool
at_floor: bool
recovery_fired: bool
diagnostics:
  snr
  ema_snr
  signal
  noise
  floor_sigma
  ceiling_sigma
  descent_sharpness
  floor_streak
  error_code|null
```

### 9.4 `RunSummary` (required)

```yaml
schema_version: int
profile_id: string
mode: string
k_down: float
r_min: float
descent_sharpness: float
n_generations: int
n_floor_gens: int
fraction_at_floor: float
time_to_first_floor_gen: int
n_floor_entries: int
n_floor_exits: int
sigma_min_seen: float
sigma_max_seen: float
dgc_trace_written: bool
dgc_trace_relpath: string|null
n_fail_open_events: int
```

### 9.5 Optional trace row schema

Required fields per traced generation:

- `generation`, `sigma_before`, `sigma_after`, `at_floor`, `factor_applied`
- `snr`, `ema_snr`, `signal`, `noise`
- `phase_before`, `phase_after`, `recovery_fired`

### 9.6 Trace mode contract (fully specified)

1. `off`: write no per-generation traces.
2. `full`: write per-generation traces for every run.
3. `hybrid`:
   - if `trace_cells` is provided, trace only those `(function_name, dimension)` cells;
   - else trace default sentinel cells:
     - `(sphere,10)`, `(sphere,20)`, `(rosenbrock,10)`, `(rosenbrock,20)`;
   - plus all runs where `seed % 10 == 0`.

## 10. Control model and equations

### 10.0 Normative per-generation execution order

1. Validate input and config-runtime constraints:
   - all numeric inputs finite,
   - `1 <= generation <= planned_generations`,
   - `warmup_generations < planned_generations`.
2. Compute read-only diagnostics: `floor_sigma`, `ceiling_sigma`, `descent_sharpness`.
3. If `mode=pass_through`, return immediately:
   - `next_sigma = current_sigma`
   - `factor_applied = 1.0`
   - `phase_after = pass_through`
   - `was_clamped = false`
   - `at_floor = false`
   - `recovery_fired = false`
   - no clamp path is executed in this mode.
4. Compute signal/noise/SNR and EMA.
5. Compute base factor from threshold rules.
6. Compute `recovery_fired_t` from pre-step state and cooldown.
7. Apply recovery modulation to get `factor_mod`.
8. Apply clamp path and compute `at_floor_t`.
9. Update occupancy counters, cooldown, and phase transitions.
10. On any step error, apply `fail_policy` (Section 10.5).

### 10.1 Core derived values

Given generation `t`:

1. `current_best_t = min(fitness_t)`
2. `signal_t = max(prev_best - current_best_t, 0)`
3. `noise_floor_t = max(noise_floor_abs, noise_floor_rel * max(1.0, abs(median(fitness_t))))`
4. `noise_t = 1.4826 * MAD(fitness_t) + noise_floor_t`
5. `snr_t = signal_t / noise_t`
6. EMA bootstrap:
   - if `generation==1` and `ema_init_mode=first_snr`, `ema_1 = snr_1`
   - if `generation==1` and `ema_init_mode=zero`, `ema_1 = 0.0`
   - else `ema_t = ema_alpha * snr_t + (1-ema_alpha) * ema_{t-1}`
7. `floor_sigma = initial_sigma * r_min`
8. `ceiling_sigma = initial_sigma * sigma_max_ratio`
9. `descent_sharpness = abs(ln(k_down)) / r_min`
10. `progress_t = generation / planned_generations`

`descent_sharpness` is telemetry/analysis-only in v1. It is not used directly in control branching.

### 10.2 Base action selection

1. If `ema_t < snr_down`: `factor_base = k_down`.
2. Else if `ema_t > snr_up`: `factor_base = k_up`.
3. Else: `factor_base = 1.0`.

### 10.3 Occupancy-aware modulation

Recovery uses pre-step state (`*_prev`) so causality is explicit:

`recovery_fired_t = true` iff all conditions hold:

1. `phase_prev == constrained`
2. `prev_at_floor == true`
3. `floor_streak_prev >= floor_streak_constrained`
4. `cooldown_prev == 0`
5. `generation > warmup_generations`
6. `progress_t <= 0.90` (no late-budget expansion)

If `recovery_fired_t`, apply one-step boost:

- `factor_mod = max(1.0, min(k_up, factor_base * recovery_boost))`

Else:

- `factor_mod = factor_base`

### 10.4 Safety clamp

1. `unclamped = current_sigma * factor_mod`
2. `next_sigma = clip(unclamped, floor_sigma, ceiling_sigma)`
3. `was_clamped = (next_sigma != unclamped)`
4. `at_floor = abs(next_sigma - floor_sigma) <= max(atol, rtol * max(1, abs(floor_sigma)))`

### 10.5 Failure policy behavior

Failures include:

1. invalid numeric inputs (NaN/inf),
2. invalid runtime constraints (`generation` bounds, `warmup_generations` violation),
3. non-finite intermediate values from policy equations.

Policies:

1. `fail_fast`: raise step error and stop run.
2. `fail_open`: emit neutral action for this generation:
   - `next_sigma = current_sigma`
   - `factor_applied = 1.0`
   - `was_clamped = false`
   - `recovery_fired = false`
   - `phase_after = active`
   - `diagnostics.error_code` populated
   - increment `n_fail_open_events`.

## 11. State machine

States:

1. `warmup`
2. `active`
3. `constrained`
4. `recovery`
5. `pass_through`

Transition precedence:

1. `mode=pass_through` -> `pass_through`.
2. `generation <= warmup_generations` -> `warmup`.
3. `recovery_fired_t=true` -> `recovery`.
4. `at_floor=true` and `floor_streak >= floor_streak_constrained` -> `constrained`.
5. Else -> `active`.

Invariants:

1. `pass_through` never emits non-neutral factor.
2. `first_floor_gen` is write-once.
3. `n_floor_entries - n_floor_exits` must be `0` or `1`.
4. `recovery` cannot repeat without cooldown expiration and renewed constrained condition.

## 12. Landscape profiles and defaults

### 12.1 Global defaults (all profiles unless overridden)

| Field | Default |
|---|---|
| `sigma_max_ratio` | `10.0` |
| `k_up` | `1.03` |
| `ema_alpha` | `0.20` |
| `ema_init_mode` | `first_snr` |
| `warmup_generations` | `5` |
| `floor_streak_constrained` | `3` |
| `recovery_boost` | `1.10` |
| `recovery_cooldown_gens` | `10` |
| `noise_floor_abs` | `1e-12` |
| `noise_floor_rel` | `1e-12` |
| `atol` | `1e-12` |
| `rtol` | `1e-9` |
| `fail_policy` | `fail_fast` |
| `trace_mode` | `hybrid` |

Global-default policy note:

1. These defaults are conservative initialization values for v1.
2. Profile-specific tuning may adjust `sigma_max_ratio` and/or `k_up` during acceptance testing when empirical behavior indicates ceiling-dominated dynamics.

### 12.2 Profile defaults (numeric, implementation-locked)

| `profile_id` | `mode` | `k_down` | `r_min` | `snr_down` | `snr_up` | `warmup_generations` | `floor_streak_constrained` | `recovery_boost` | `recovery_cooldown_gens` |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `sphere` | `pass_through` | 0.99 | 0.15 | 0.08 | 0.25 | 0 | 3 | 1.00 | 0 |
| `rosenbrock` | `pass_through` | 0.99 | 0.05 | 0.16 | 0.35 | 0 | 3 | 1.00 | 0 |
| `rosenbrock_active_tight` | `active` | 0.97 | 0.05 | 0.16 | 0.35 | 10 | 3 | 1.05 | 20 |
| `rastrigin` | `active` | 0.93 | 0.05 | 0.12 | 0.30 | 5 | 3 | 1.08 | 10 |
| `ellipsoid` | `active` | 0.90 | 0.03 | 0.08 | 0.25 | 5 | 3 | 1.10 | 10 |
| `unknown` | `pass_through` | 0.99 | 0.10 | 0.12 | 0.30 | 0 | 3 | 1.00 | 0 |

Profile constraints:

1. `sphere` and `rosenbrock` defaults are non-invasive (`pass_through`) to avoid known harm regimes.
   - Rationale: sphere is `0/64` improved in dense sweep; rosenbrock is fragile (`14/64`) and showed broad harm in high-rigor baseline cells.
2. `rosenbrock_active_tight` is explicitly experimental and must be selected intentionally.
3. `ellipsoid` and `rastrigin` are active defaults because dense-sweep evidence supports beneficial regimes under low-mid `r`.
4. `unknown` defaults to `pass_through`; active mode requires explicit override with declared risk.

## 13. Failure modes and mitigations

1. **Premature floor dominance**  
Mitigation: constrained-state detection + bounded recovery boost + cooldown.

2. **Oscillatory sigma actions**  
Mitigation: EMA smoothing + bounded `k_down/k_up` envelope + cooldown on recovery events.

3. **False neutrality from pass-through misuse**  
Mitigation: explicit profile-mode logging and audit fields (`mode`, `profile_id`, action counters).

4. **Profile mismatch to workload**  
Mitigation: required profile declaration + post-run profile fitness diagnostics + unknown fallback.

5. **High-`r` unsafe overrides**  
Mitigation: explicit `allow_high_r_override` gate and warning-level telemetry flag.

## 14. Evaluation protocol and acceptance criteria

### 14.1 Evaluation protocol

For each profile:

1. Compare against vanilla CMA-ES on 36-cell matrix.
2. Produce both endpoint and behavior diagnostics.
3. Run seed-robustness check (multiple seed blocks).
4. Report results at both aggregate level and per-function level; aggregate-only reporting is non-compliant.

Required outputs:

- `runs_long.csv`
- `method_aggregate.csv`
- `cell_stats.csv`
- `behavior_aggregate.csv`
- `pairwise_*.csv/json`
- `descent_*_metrics.csv`

### 14.2 Acceptance criteria (v1)

1. **Determinism**  
Same config + seed -> row-stable deterministic controller fields.

2. **Sphere harm constraint**  
With `sphere` default profile (`pass_through`), require functional parity with vanilla on matched seeds:
- for paired eval rows, `abs(final_best_dgc - final_best_vanilla) <= 1e-8` for 100% of pairs,
- sphere-only `median_delta_vs_reference` in `cell_stats.csv` must satisfy `abs(value) <= 1e-8` for all 9 sphere cells.

3. **High-`r` safeguard effectiveness**  
Default profiles cannot run with unsafe high `r_min` unless explicit override.

4. **Mechanism observability**  
Run summaries + traces must be sufficient to compute:
- floor occupancy,
- first-floor timing,
- descent/floor sigma-volume split,
- descent contraction statistics.

5. **Profile behavior sanity**
- `sphere` resolves to `mode=pass_through` and emits `factor_applied=1.0` for every generation.
- `ellipsoid` default config enforces `r_min <= 0.15`.
- `rosenbrock` default resolves to `mode=pass_through`; `rosenbrock_active_tight` is opt-in.
- `unknown` default resolves to `mode=pass_through`.

6. **Acceptance coverage for sphere parity**
- Automated hypothesis validation must include criterion #2 (`pass_through` sphere parity), or the run must emit a documented manual verification artifact proving criterion #2 was checked and passed.

## 15. Implementation checklist (decision-complete)

1. Create typed config schema with hard validation.
2. Implement deterministic policy core and state machine exactly as defined.
3. Implement profile catalog with immutable defaults.
4. Implement adapter contract (post-`tell` sigma apply only).
5. Implement telemetry writer for run summary + optional trace rows.
6. Implement evaluation harness and acceptance checks.
7. Add tests:
   - schema validation,
   - transition ordering,
   - determinism,
   - pass-through parity versus vanilla,
   - fail_fast/fail_open behavior,
   - profile defaults,
   - occupancy metric correctness,
   - safety clamp behavior.

---

## Appendix A: Evidence-to-Design Traceability Matrix

| Design rule | Evidence pattern | Source artifact |
|---|---|---|
| `r_min` is primary policy axis | `corr(r, mean_win_rate)` strongly negative across stages (`-0.949`, `-0.946`, `-0.989`) | `.../dense|interaction|anchors.../method_aggregate.csv` + derived analysis |
| Prioritize occupancy observability | `descent_volume_fraction` strongly tracks win-rate (`0.918`, `0.851`, `0.949`) | `.../descent_variant_metrics.csv` |
| Sphere default should be non-invasive | sphere `0/64` function-level improvements; anchors also net positive deltas | dense + anchors `cell_stats.csv` |
| High-`r` guardrails are mandatory | ellipsoid degrades at `r=0.20`; typical crossover to net loss at `r=0.25` | dense `cell_stats.csv` |
| Thresholds are secondary modulators | fixed `k=0.97,r=0.05` moves from `-6.011` to `-44.113` by thresholds | interaction `method_aggregate.csv` |
| Include class profiles | tolerance differs by class: `Ellipsoid > Rastrigin > Rosenbrock > Sphere` | dense aggregated function analysis |

## Appendix B: What This Design Does Not Claim

1. It does not claim universal improvement over vanilla CMA-ES.
2. It does not claim a universal `r_min` phase boundary.
3. It does not claim profile auto-detection in v1.
4. It does not claim that thresholds can compensate for unsafe geometry in all cases.
5. It does not replace rigorous comparative evaluation; it formalizes it.
