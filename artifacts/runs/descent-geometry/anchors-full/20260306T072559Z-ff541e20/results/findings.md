# Run Findings

## Run Identity
- Run ID: `20260306T072559Z-ff541e20`
- Scope: `descent_geom_anchors_full`
- Created (UTC): `2026-03-06T07:34:17.476812+00:00`
- Config: `experiments/config/descent_geom_anchors_full.yaml`
- Config Hash: `ff541e207980f69e4fa45a8a14d83a246393d29f89857082d33244a8ca19c1f2`

## Execution
- Total runs: `7920`
- OK runs: `7920`
- Failed runs: `0`
- Status by phase:
  - `eval` / `ok`: `7920`

## Performance Summary
- Compared method rows: `10`
- Cell rows: `360`
- Significant cells (q < 0.05): `221`
- Ranking (lower median delta is better):
  - `proxy_sigma_controller:anchor_k086_r002`: median delta `-46.5561588466064`, win-rate `0.6708333333333333`, q<0.05 cells `20`
  - `proxy_sigma_controller:anchor_k093_r005`: median delta `-44.306122586950245`, win-rate `0.6194444444444444`, q<0.05 cells `25`
  - `proxy_sigma_controller:anchor_k090_r005`: median delta `-38.26943809563931`, win-rate `0.6208333333333333`, q<0.05 cells `21`
  - `proxy_sigma_controller:anchor_k090_r010`: median delta `-9.5215689306378`, win-rate `0.5194444444444446`, q<0.05 cells `23`
  - `proxy_sigma_controller:anchor_k097_r005`: median delta `-4.156299974215191`, win-rate `0.5750000000000001`, q<0.05 cells `21`
  - `proxy_sigma_controller:anchor_k095_r005`: median delta `-3.529629107199681`, win-rate `0.5986111111111111`, q<0.05 cells `20`
  - `proxy_sigma_controller:anchor_k095_r010`: median delta `-1.856800051998006`, win-rate `0.4819444444444445`, q<0.05 cells `22`
  - `proxy_sigma_controller:anchor_k097_r010`: median delta `-1.6511046726136411`, win-rate `0.4861111111111112`, q<0.05 cells `22`
  - `proxy_sigma_controller:anchor_k093_r020`: median delta `4.407246170494582`, win-rate `0.3013888888888889`, q<0.05 cells `23`
  - `proxy_sigma_controller:anchor_k098_r025`: median delta `9.954657086494596`, win-rate `0.25`, q<0.05 cells `24`

## Behavior Summary
- Behavior rows: `7200`
- Methods with behavior telemetry: `10`

## Hypothesis Checks
- Total checks: `4`
- Passed: `4`
- Failed: `0`
- Errors: `0`

## Warnings

## Artifact Links
- `analysis_manifest_json`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/analysis_manifest.json`
- `behavior_aggregate_csv`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/behavior_aggregate.csv`
- `cell_stats_csv`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/cell_stats.csv`
- `figure_behavior_floor`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/figures/behavior_fraction_at_floor_bar.png`
- `figure_behavior_ttf`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/figures/behavior_time_to_first_floor_bar.png`
- `figure_method_delta`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/figures/method_median_delta_bar.png`
- `figure_method_win_rate`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/figures/method_win_rate_bar.png`
- `hypothesis_checks_json`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/hypothesis_checks.json`
- `manifest_json`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/manifest.json`
- `method_aggregate_csv`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/method_aggregate.csv`
- `pairwise_json_pairwise_proxy_sigma_controller_anchor_k090_r010_vs_vanilla_cma`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/pairwise_proxy_sigma_controller_anchor_k090_r010_vs_vanilla_cma.json`
- `runs_long_csv`: `artifacts/runs/descent-geometry/anchors-full/20260306T072559Z-ff541e20/results/runs_long.csv`
