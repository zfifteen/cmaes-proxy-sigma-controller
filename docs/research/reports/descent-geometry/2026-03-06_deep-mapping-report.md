# Descent-Geometry Deep Mapping Suite: Formal Analysis Report

Date: 2026-03-06
Repository: `cmaes-proxy-sigma-controller`
Suite manifest: `artifacts/runs/descent-geometry/suite_manifest.json`

## Natural-Language Conclusions

The updated evidence supports a geometry-first mechanism with a landscape-specific tolerance curve, not a single global threshold. The dominant control axis remains descent geometry, especially `r = sigma_min_ratio`, but each landscape class tolerates different `r` ranges before degrading.

The most decisive clarification is sphere: there is no geometry configuration in this suite that yields net sphere recovery. In the dense sweep, sphere is `0/64` improved at function level, including aggressive configurations like `k=0.86, r=0.02` (sharpness `7.54`). In anchors-full (seeds `1000..1019`, full trace), `anchor_k086_r002` still remains net-positive on sphere (worse than vanilla on aggregate), with only localized small cell negatives.

Ellipsoid remains the strongest beneficiary class, but it is not immune to poor geometry. It is robust through lower `r`, weakens at `r=0.20`, and crosses to net loss around `r=0.25`. This demonstrates there is no landscape class that safely tolerates high-`r` geometry.

Threshold tuning is still materially useful, but as a secondary interaction layer over geometry. The large interaction-stage jump for `k=0.97, r=0.05` is not Rosenbrock-only: ellipsoid contributes most of the magnitude, while Rosenbrock and Rastrigin also improve directionally.

The prior AWF narrative should therefore be interpreted as partially correct but incomplete. The phase-transition idea is real, but the transition location is landscape-dependent rather than fixed globally (for example, not universally `r=0.05`).

## Detailed Technical Breakdown

## 1. Scope and Artifacts

The suite executed three sequential stages with `reference_method: vanilla_cma`:

1. `descent_geom_dense_hybrid.yaml`
2. `descent_geom_interaction_hybrid.yaml`
3. `descent_geom_anchors_full.yaml`

Run roots:

1. `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15`
2. `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718`
3. `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20`

All stages completed with verification pass and zero failed eval runs.

## 2. Completion and Quality Gates

| Stage | Run ID | Total eval rows | Proxy rows | Vanilla rows | Hypothesis checks |
|---|---|---:|---:|---:|---|
| Dense (hybrid) | `20260306T052148Z-cdeecf15` | 117,000 | 115,200 | 1,800 | 3/3 passed |
| Interaction (hybrid) | `20260306T065954Z-09aac718` | 30,600 | 28,800 | 1,800 | 3/3 passed |
| Anchors (full trace) | `20260306T072559Z-ff541e20` | 7,920 | 7,200 | 720 | 4/4 passed |

Trace coverage:

1. Dense hybrid: `0.4`
2. Interaction hybrid: `0.4`
3. Anchors full: `1.0`

## 3. Landscape Taxonomy (Updated)

The data now supports this class ordering:

1. `ellipsoid_cond1e6`: strongest and most frequent gains at low-mid `r`, but degrades at high `r` and can cross to loss.
2. `rastrigin`: generally positive under favorable geometry, degrades with high `r`.
3. `rosenbrock`: fragile and geometry-sensitive; recoverable in subsets.
4. `sphere`: no function-level recovery in this suite.

Dense function-level improvement counts over 64 variants (`median_delta < 0`):

| Function | Improved variants | Total variants |
|---|---:|---:|
| `ellipsoid_cond1e6` | 57 | 64 |
| `rastrigin` | 45 | 64 |
| `rosenbrock` | 14 | 64 |
| `sphere` | 0 | 64 |

## 4. Geometry as Primary Axis

Variant-level correlations (stage-level):

| Correlation | Dense | Interaction | Anchors |
|---|---:|---:|---:|
| `corr(descent_sharpness, mean_win_rate)` | `0.670` | `0.676` | `0.575` |
| `corr(descent_sharpness, median_delta)` | `-0.778` | `-0.645` | `-0.734` |
| `corr(r, mean_win_rate)` | `-0.949` | `-0.946` | `-0.989` |
| `corr(r, median_delta)` | `0.739` | `0.750` | `0.698` |

Dense grouped by `r` (mean across variants) shows a clear regime shift:

| `r` | Mean median-delta | Mean win-rate |
|---:|---:|---:|
| 0.02 | -32.66 | 0.611 |
| 0.03 | -31.79 | 0.604 |
| 0.05 | -28.67 | 0.576 |
| 0.07 | -23.75 | 0.542 |
| 0.10 | -9.27 | 0.478 |
| 0.15 | 1.65 | 0.360 |
| 0.20 | 5.92 | 0.287 |
| 0.25 | 9.52 | 0.245 |

Interpretation:

1. Lower `r` systematically improves comparative outcomes.
2. High `r` (`>= 0.15`) is broadly harmful.
3. Geometry remains the primary control axis across all stages.

## 5. Sphere Forensics (Definitive Clarification)

Dense sphere by `r` (function-level median delta per variant):

| `r` | Variants | Variants with sphere function median `< 0` | Best (smallest) sphere function median delta |
|---:|---:|---:|---:|
| 0.02 | 8 | 0 | `+0.00657` |
| 0.03 | 8 | 0 | `+0.01007` |
| 0.05 | 8 | 0 | `+0.05533` |
| 0.07 | 8 | 0 | `+0.13130` |
| 0.10 | 8 | 0 | `+0.30560` |
| 0.15 | 8 | 0 | `+0.68699` |
| 0.20 | 8 | 0 | `+1.12377` |
| 0.25 | 8 | 0 | `+1.72061` |

Additional nuance:

1. `18/64` variants have at least one individual sphere cell with negative delta.
2. None of those variants flips to net sphere recovery at function level.

Anchors-full targeted checks:

| Variant | Sphere cells with delta `< 0` | Sphere function median delta |
|---|---:|---:|
| `proxy_sigma_controller:anchor_k090_r005` | 0/9 | `+0.06671` |
| `proxy_sigma_controller:anchor_k086_r002` | 2/9 | `+0.01104` |

Conclusion: sphere non-recovery is robust in this suite, including the most aggressive tested geometry.

## 6. Ellipsoid High-r Degradation and Crossover

Dense ellipsoid by `r` (variant-level function medians):

| `r` | Variants improved (`<0`) | Variants total | Median of variant ellipsoid medians |
|---:|---:|---:|---:|
| 0.02 | 8 | 8 | `-27917.78` |
| 0.03 | 8 | 8 | `-28061.95` |
| 0.05 | 8 | 8 | `-29223.68` |
| 0.07 | 8 | 8 | `-27088.41` |
| 0.10 | 8 | 8 | `-25005.39` |
| 0.15 | 8 | 8 | `-18580.33` |
| 0.20 | 6 | 8 | `-9713.26` |
| 0.25 | 3 | 8 | `+460.57` |

Cell-level support (ellipsoid rows pooled by `r`):

1. Fraction of negative deltas declines from `1.00` at `r<=0.07` to `0.58` at `r=0.20` and `0.46` at `r=0.25`.
2. Median cell delta turns positive at `r=0.25`.

Conclusion: even the strongest beneficiary class eventually breaks under high-`r` geometry.

## 7. Threshold Interaction Decomposition (k=0.97, r=0.05)

Overall stage-level medians for threshold variants:

| Variant | Overall median-of-cell-medians | Mean win-rate |
|---|---:|---:|
| `int_k097_r005_t005_020` | `-6.011` | `0.528` |
| `int_k097_r005_t008_025` | `-2.999` | `0.573` |
| `int_k097_r005_t012_030` | `-43.732` | `0.621` |
| `int_k097_r005_t016_035` | `-44.113` | `0.661` |

Function-level medians (`t016_035` minus `t005_020`):

| Function | Delta swing |
|---|---:|
| `ellipsoid_cond1e6` | `-6051.39` |
| `rastrigin` | `-28.20` |
| `rosenbrock` | `-2.23` |
| `sphere` | `-0.0668` |

Cell-level comparison (`t016_035` vs `t005_020`):

1. `25/36` cells improve in median delta.
2. `25/36` cells improve in win-rate.
3. Largest absolute gains are ellipsoid high-dimension cells.

Conclusion: the interaction-stage swing is multi-landscape, dominated by ellipsoid magnitude, with additional directional contributions from Rastrigin and Rosenbrock.

## 8. Behavioral Telemetry Link

Variant-level telemetry correlations with `mean_win_rate`:

| Metric | Dense | Interaction | Anchors |
|---|---:|---:|---:|
| `descent_volume_fraction_mean` | `0.918` | `0.851` | `0.949` |
| `first_floor_gen_trace_mean` | `0.845` | `0.653` | `0.889` |
| `floor_gens_trace_mean` | `-0.854` | `-0.684` | `-0.887` |

This remains consistent with the mechanism interpretation:

1. Better variants preserve descent-volume share.
2. Better variants hit floor later.
3. Better variants spend less time at floor.

## 9. Pairwise Baseline Checks

Default pairwise target in each stage:

| Stage | Method B | Cells better (B) | Cells better (A) | q<0.05 cells | Median cell delta (B-A) |
|---|---|---:|---:|---:|---:|
| Dense | `proxy_sigma_controller:geomdense__sigma_down_factor_0p9__sigma_min_ratio_0p1` | 20 | 16 | 29 | `-18.76` |
| Interaction | `proxy_sigma_controller:int_k090_r010_t008_025` | 20 | 16 | 29 | `-18.76` |
| Anchors | `proxy_sigma_controller:anchor_k090_r010` | 20 | 16 | 23 | `-9.52` |

## 10. Robustness and Seed Sensitivity

Dense seed-block analysis (5 blocks x 10 seeds) indicates effect-size sensitivity:

1. Median-delta block-range mean: `23.69` (max `66.17`).
2. Win-rate block-range mean: `0.083` (max `0.125`).

Interpretation:

1. Directional rankings are fairly stable.
2. Effect-size magnitude can vary materially by seed composition.
3. Prior sphere "recovery" claims are consistent with seed-composition artifact rather than robust mechanism.

## 11. Final Synthesis

The complete evidence set supports:

1. Geometry-first control (`r` as dominant governing variable).
2. Landscape-specific tolerance thresholds rather than one universal phase boundary.
3. Secondary but real threshold interactions layered on geometry.
4. A clean four-class taxonomy for expected proxy behavior:

   - Ellipsoid: strong gains at low-mid `r`, degrades at high `r`, crossover near `r=0.25`.
   - Rastrigin: generally positive under favorable geometry, high-`r` degradation.
   - Rosenbrock: fragile and tune-sensitive.
   - Sphere: no net recovery observed in this suite.

## 12. Primary Source Files

Core suite:

1. `artifacts/runs/descent-geometry/suite_manifest.json`
2. `artifacts/runs/descent-geometry/suite.log`

Dense:

1. `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/method_aggregate.csv`
2. `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/cell_stats.csv`
3. `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/descent_variant_metrics.csv`
4. `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/hypothesis_checks.json`

Interaction:

1. `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/method_aggregate.csv`
2. `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/cell_stats.csv`
3. `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/descent_variant_metrics.csv`
4. `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/hypothesis_checks.json`

Anchors:

1. `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/method_aggregate.csv`
2. `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/cell_stats.csv`
3. `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/descent_variant_metrics.csv`
4. `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/hypothesis_checks.json`
