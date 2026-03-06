# Differences Report: Claude Revised Hypothesis vs Codex Deep-Mapping Report

Date: 2026-03-06
Scope: Compare these two documents without modifying either original.

1. `docs/Descent_Geometry_Revised_Hypothesis_2026_03_06.docx`
2. `docs/mechanism_analysis/descent_geometry_deep_mapping_suite_report_2026-03-06.md`

## Executive Summary

The two reports are strongly aligned on core mechanism conclusions:

1. Descent geometry is primary, with `r_min` as the dominant control axis.
2. Landscape-specific tolerance is the right framing (not one universal boundary).
3. Sphere does not show net recovery in this suite.
4. High-`r` geometry degrades outcomes, including for strong beneficiary classes.
5. Threshold tuning has real interaction effects within fixed geometry.

Most differences are not conceptual contradictions; they are scope, wording, or numerical precision differences. A small number of material numeric inconsistencies are present in the `.docx` and are documented below.

## Areas of Strong Agreement

1. `corr(r, mean_win_rate)` magnitude is consistently strong and negative across stages.
2. `descent_volume_fraction` is a top behavioral predictor of outcomes.
3. Sphere non-recovery is a robust class finding, not a single-config failure.
4. Ellipsoid is best overall but not immune to high-`r` degradation.
5. Rosenbrock is fragile and sensitive to both geometry and thresholds.
6. The `k=0.97, r=0.05` interaction block exhibits a large threshold-driven performance swing.

## Material Differences and Corrections

| Topic | `.docx` claim | Artifact-backed value | Notes |
|---|---|---|---|
| Suite run volume | "108,000+ runs" | `155,520` total eval rows (`151,200` proxy + `4,320` vanilla) | Numerical inconsistency in `.docx` scope statement. |
| Fixed-geometry threshold table (`k=0.97,r=0.05`) | Shows `t008_025=-15.28`, `t012_030=-23.80` | Actual variant values: `t008_025=-2.999`, `t012_030=-43.732` | `.docx` appears to mix fixed-geometry numbers with threshold-band aggregate numbers. |
| `r=0.20` anchor interpretation | "all r=0.20 anchor configurations remained net-negative across all landscape classes" | Anchors have one `r=0.20` variant (`anchor_k093_r020`), and function medians are mixed: ellipsoid negative, rastrigin/rosenbrock/sphere positive | Overstated in `.docx`; true only at overall aggregate level for that variant (`+4.407` median-of-cell-medians, i.e. net worse). |
| Rosenbrock interaction status | `.docx` marks cell-level breakdown pending | Codex report includes cell-level decomposition (`25/36` cells improved for `t016_035` vs `t005_020`, with function-level swing decomposition) | Difference is completeness/timing, not conflict. |

## Emphasis Differences (Non-Contradictory)

1. `.docx` includes a broader research-program narrative (supersession framing, practical decision rules, open questions).
2. Codex report is more artifact-anchored to this specific suite and includes explicit sphere forensics plus post-hoc cell-level interaction decomposition.
3. `.docx` adds stronger practitioner guidance language (landscape-first tuning workflow), while Codex report focuses on validated suite evidence and quantitative boundaries.

## Naming and Context Drift

1. `.docx` repeatedly references `lr_adapt_proxy` naming in prose.
2. Codex report is repo-native to `cmaes-proxy-sigma-controller` method IDs and artifact schema.

This is mostly editorial/context drift, but it can confuse readers about implementation identity if the two documents are read side-by-side.

## Net Assessment

1. Core scientific interpretation is consistent between documents.
2. The `.docx` contains several numeric/wording inaccuracies that should be treated as editorial errors, not mechanism disagreements.
3. Codex report currently holds the more precise artifact-level numeric account for this suite.
4. The `.docx` adds useful strategic framing and next-step hypotheses not fully elaborated in the Codex report.

## Verification Sources Used

Primary run artifacts:

1. `artifacts/runs/descent-geometry/suite_manifest.json`
2. `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/method_aggregate.csv`
3. `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/cell_stats.csv`
4. `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/method_aggregate.csv`
5. `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/cell_stats.csv`
6. `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/cell_stats.csv`
7. `artifacts/runs/descent-geometry/*/*/results/runs_long.csv`

Documents compared:

1. `docs/Descent_Geometry_Revised_Hypothesis_2026_03_06.docx`
2. `docs/mechanism_analysis/descent_geometry_deep_mapping_suite_report_2026-03-06.md`
