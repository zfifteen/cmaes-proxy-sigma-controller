# Run Findings

## Run Identity
- Run ID: `20260306T065954Z-09aac718`
- Scope: `descent_geom_interaction_hybrid`
- Created (UTC): `2026-03-06T07:25:34.185134+00:00`
- Config: `experiments/config/descent_geom_interaction_hybrid.yaml`
- Config Hash: `09aac718cb04f20f441ba7e16420c04fcf76a2817eec38d74b3aa63442efacb4`

## Execution
- Total runs: `30600`
- OK runs: `30600`
- Failed runs: `0`
- Status by phase:
  - `eval` / `ok`: `30600`

## Performance Summary
- Compared method rows: `16`
- Cell rows: `576`
- Significant cells (q < 0.05): `412`
- Ranking (lower median delta is better):
  - `proxy_sigma_controller:int_k097_r005_t016_035`: median delta `-44.11347173779706`, win-rate `0.6611111111111112`, q<0.05 cells `22`
  - `proxy_sigma_controller:int_k097_r005_t012_030`: median delta `-43.73202210927683`, win-rate `0.6211111111111111`, q<0.05 cells `22`
  - `proxy_sigma_controller:int_k090_r005_t008_025`: median delta `-43.074250626580145`, win-rate `0.6211111111111111`, q<0.05 cells `28`
  - `proxy_sigma_controller:int_k090_r005_t012_030`: median delta `-39.5939178990476`, win-rate `0.66`, q<0.05 cells `25`
  - `proxy_sigma_controller:int_k090_r005_t016_035`: median delta `-39.200767630733175`, win-rate `0.7166666666666667`, q<0.05 cells `27`
  - `proxy_sigma_controller:int_k090_r005_t005_020`: median delta `-21.613462169781812`, win-rate `0.5866666666666667`, q<0.05 cells `26`
  - `proxy_sigma_controller:int_k090_r010_t008_025`: median delta `-18.764699262529696`, win-rate `0.5172222222222222`, q<0.05 cells `29`
  - `proxy_sigma_controller:int_k093_r010_t016_035`: median delta `-18.572381182748313`, win-rate `0.5477777777777777`, q<0.05 cells `25`
  - `proxy_sigma_controller:int_k093_r010_t012_030`: median delta `-17.98205677515892`, win-rate `0.5494444444444444`, q<0.05 cells `31`
  - `proxy_sigma_controller:int_k093_r010_t008_025`: median delta `-16.096919322182792`, win-rate `0.5094444444444445`, q<0.05 cells `29`

## Behavior Summary
- Behavior rows: `28800`
- Methods with behavior telemetry: `16`

## Hypothesis Checks
- Total checks: `3`
- Passed: `3`
- Failed: `0`
- Errors: `0`

## Warnings

## Artifact Links
- `analysis_manifest_json`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/analysis_manifest.json`
- `behavior_aggregate_csv`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/behavior_aggregate.csv`
- `cell_stats_csv`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/cell_stats.csv`
- `figure_behavior_floor`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/figures/behavior_fraction_at_floor_bar.png`
- `figure_behavior_ttf`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/figures/behavior_time_to_first_floor_bar.png`
- `figure_method_delta`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/figures/method_median_delta_bar.png`
- `figure_method_win_rate`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/figures/method_win_rate_bar.png`
- `hypothesis_checks_json`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/hypothesis_checks.json`
- `manifest_json`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/manifest.json`
- `method_aggregate_csv`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/method_aggregate.csv`
- `pairwise_json_pairwise_proxy_sigma_controller_int_k090_r010_t008_025_vs_vanilla_cma`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/pairwise_proxy_sigma_controller_int_k090_r010_t008_025_vs_vanilla_cma.json`
- `runs_long_csv`: `artifacts/runs/descent-geometry/interaction/20260306T065954Z-09aac718/results/runs_long.csv`
