# Descent Geometry Controller Design Doc Plan (New Repo)

## Summary
Create one new, implementation-ready design document for a **new dedicated repo** named **Descent Geometry Controller**.  
The document will open with a long-form, accessible narrative explaining exactly how the experimental data drives the design, then transition into a precise engineering spec (clean-break contract, class-profile-driven control, deterministic behavior, and testable acceptance criteria).

Target output file:
- `docs/research/design/2026-03-06_descent-geometry-controller_design_spec.md`

## Key Changes (Document Content)
1. **Narrative Front Section (verbose, non-technical first)**
- Explain the research arc from AWF-centric interpretation to geometry-first interpretation.
- Explain landscape tolerance curve in plain language: `Ellipsoid > Rastrigin > Rosenbrock > Sphere`.
- Explain why `r_min` is primary and thresholds are secondary interaction controls.
- Explain decisive findings users can reason about:
  - Sphere non-recovery (`0/64` dense function-level improvements).
  - Ellipsoid high-`r` degradation and crossover near `r=0.25`.
  - Threshold interaction at fixed geometry (`k=0.97,r=0.05`) is multi-landscape, not Rosenbrock-only.
- Tie each major claim to explicit artifact-backed numeric anchors.

2. **Technical Specification Section (implementation-ready)**
- Define architecture for a **new repo** (clean break from existing contracts):
  - `core/policy`, `core/state`, `profiles`, `adapter`, `telemetry`, `evaluation`.
- Define v1 operating model:
  - Explicit **landscape-class profile selection** (no auto-inference in v1).
  - Deterministic per-generation decision loop.
  - Safety envelope and bounded sigma updates.
- Define control model and equations:
  - Geometry envelope (`k_down`, `r_min`), threshold gating, floor occupancy controls, recovery logic.
  - State machine with exact transitions and invariants.
- Define class profiles and defaults:
  - `sphere`: pass-through/near-pass-through profile.
  - `rosenbrock`: conservative low-`r`, strict thresholds, harm-minimization defaults.
  - `rastrigin`: moderate-`r` tolerated profile.
  - `ellipsoid`: low-mid `r` aggressive-benefit profile with high-`r` guardrails.
  - `unknown`: conservative fallback profile.
- Define failure modes and mitigations:
  - premature floor dominance, oscillation, false neutrality, profile mismatch.

3. **Concrete Interface Contracts**
- Add precise schema tables for:
  - `ControllerConfig` (clean-break fields; no backward compatibility constraints).
  - `StepInput` / `StepOutput`.
  - `RunSummary` and optional trace schema.
- Define required telemetry fields for mechanism validation:
  - descent-volume split, floor timing, occupancy, contraction diagnostics.
- Define validation rules and hard constraints (ranges, monotonic guards, incompatible combinations).

4. **Evaluation and Acceptance Section**
- Define benchmark/validation protocol that mirrors current evidence standards:
  - comparative evaluation vs vanilla CMA-ES.
  - class-wise performance and behavior diagnostics.
  - seed-robustness checks (effect size and win-rate stability).
- Define acceptance criteria for first implementation:
  - deterministic replay for fixed seed/config.
  - profile behavior matches stated guardrails.
  - sphere harm constraints and high-`r` safeguards verified.
  - artifact outputs sufficient to re-test the core hypotheses.

5. **Appendix**
- Include a compact “evidence-to-design traceability matrix”:
  - each design rule mapped to specific observed data pattern and source artifact file.
- Include “what this design does not claim” boundary section to prevent overreach.

## Test Plan (for document quality and decision completeness)
1. **Numerical consistency pass**
- Verify all quoted metrics in the doc against current source-of-truth artifact files.
- Flag and avoid mixed aggregate/fixed-geometry numbers.

2. **Contract completeness pass**
- Confirm every algorithmic section has matching interfaces, validation rules, and telemetry outputs.
- Confirm no unresolved implementation decisions remain.

3. **Implementer handoff pass**
- A separate engineer should be able to build v1 from the spec without making policy-level decisions.

## Assumptions and Defaults
1. Design target is a **new dedicated repository**.
2. Controller name is **Descent Geometry Controller**.
3. Compatibility mode is **clean break** from current repo contracts.
4. v1 control mode is **explicit landscape-class profile selection** (not auto-inferred).
5. The current deep-mapping markdown report remains the source of truth for numeric claims.
