# Run Findings

## Run Identity
- Run ID: `20260306T024807Z-0fc7f2bf`
- Scope: `sensitivity_pipeline`
- Created (UTC): `2026-03-06T03:08:43.598409+00:00`
- Config: `experiments/config/sensitivity.yaml`
- Config Hash: `0fc7f2bf88450ffdae253be0c4c65a53c3db846658f0dc6d962423ec4a858650`

## Execution
- Total runs: `24480`
- OK runs: `24480`
- Failed runs: `0`
- Status by phase:
  - `eval` / `ok`: `24480`

## Performance Summary
- Compared method rows: `16`
- Cell rows: `576`
- Significant cells (q < 0.05): `401`
- Ranking (lower median delta is better):
  - `proxy_sigma_controller:geom__sigma_down_factor_0p93__sigma_min_ratio_0p05`: median delta `-43.20152853345416`, win-rate `0.6076388888888888`, q<0.05 cells `24`
  - `proxy_sigma_controller:geom__sigma_down_factor_0p95__sigma_min_ratio_0p05`: median delta `-42.85789888172104`, win-rate `0.5895833333333333`, q<0.05 cells `22`
  - `proxy_sigma_controller:geom__sigma_down_factor_0p9__sigma_min_ratio_0p05`: median delta `-41.87873485678836`, win-rate `0.6354166666666666`, q<0.05 cells `26`
  - `proxy_sigma_controller:geom__sigma_down_factor_0p93__sigma_min_ratio_0p1`: median delta `-21.35279998371651`, win-rate `0.5118055555555556`, q<0.05 cells `24`
  - `proxy_sigma_controller:thctl_005_020`: median delta `-20.475182328151593`, win-rate `0.5027777777777778`, q<0.05 cells `25`
  - `proxy_sigma_controller:geom__sigma_down_factor_0p9__sigma_min_ratio_0p1`: median delta `-17.221346309251942`, win-rate `0.5236111111111111`, q<0.05 cells `25`
  - `proxy_sigma_controller:geom_k090_r010`: median delta `-17.221346309251942`, win-rate `0.5236111111111111`, q<0.05 cells `25`
  - `proxy_sigma_controller:thctl_012_030`: median delta `-12.741034743210978`, win-rate `0.5472222222222222`, q<0.05 cells `30`
  - `proxy_sigma_controller:thctl_016_035`: median delta `-11.210255156388216`, win-rate `0.5361111111111112`, q<0.05 cells `19`
  - `proxy_sigma_controller:geom__sigma_down_factor_0p97__sigma_min_ratio_0p05`: median delta `-6.304632031020544`, win-rate `0.5770833333333334`, q<0.05 cells `22`

## Behavior Summary
- Behavior rows: `23040`
- Methods with behavior telemetry: `16`

## Hypothesis Checks
- Total checks: `3`
- Passed: `3`
- Failed: `0`
- Errors: `0`

## Warnings

## Artifact Links
- `analysis_manifest_json`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/results/analysis_manifest.json`
- `behavior_aggregate_csv`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/results/behavior_aggregate.csv`
- `cell_stats_csv`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/results/cell_stats.csv`
- `figure_behavior_floor`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/figures/behavior_fraction_at_floor_bar.png`
- `figure_behavior_ttf`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/figures/behavior_time_to_first_floor_bar.png`
- `figure_method_delta`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/figures/method_median_delta_bar.png`
- `figure_method_win_rate`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/figures/method_win_rate_bar.png`
- `hypothesis_checks_json`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/results/hypothesis_checks.json`
- `manifest_json`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/results/manifest.json`
- `method_aggregate_csv`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/results/method_aggregate.csv`
- `pairwise_json_pairwise_proxy_sigma_controller_geom_k090_r010_vs_vanilla_cma`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/results/pairwise_proxy_sigma_controller_geom_k090_r010_vs_vanilla_cma.json`
- `runs_long_csv`: `artifacts/runs/sensitivity/20260306T024807Z-0fc7f2bf/results/runs_long.csv`
