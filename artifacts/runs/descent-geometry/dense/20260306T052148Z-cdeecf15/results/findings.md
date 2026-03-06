# Run Findings

## Run Identity
- Run ID: `20260306T052148Z-cdeecf15`
- Scope: `descent_geom_dense_hybrid`
- Created (UTC): `2026-03-06T06:58:31.777912+00:00`
- Config: `experiments/config/descent_geom_dense_hybrid.yaml`
- Config Hash: `cdeecf158298fc977a4d29ec7074b9365b952ec74c7f53ece3746aad75b7b887`

## Execution
- Total runs: `117000`
- OK runs: `117000`
- Failed runs: `0`
- Status by phase:
  - `eval` / `ok`: `117000`

## Performance Summary
- Compared method rows: `64`
- Cell rows: `2304`
- Significant cells (q < 0.05): `1586`
- Ranking (lower median delta is better):
  - `proxy_sigma_controller:geomdense__sigma_down_factor_0p93__sigma_min_ratio_0p02`: median delta `-52.10163337160182`, win-rate `0.645`, q<0.05 cells `24`
  - `proxy_sigma_controller:geomdense__sigma_down_factor_0p93__sigma_min_ratio_0p03`: median delta `-50.908420764234535`, win-rate `0.6333333333333333`, q<0.05 cells `25`
  - `proxy_sigma_controller:geomdense__sigma_down_factor_0p9__sigma_min_ratio_0p02`: median delta `-49.45473244500412`, win-rate `0.6661111111111111`, q<0.05 cells `25`
  - `proxy_sigma_controller:geomdense__sigma_down_factor_0p88__sigma_min_ratio_0p02`: median delta `-49.07200739267913`, win-rate `0.6461111111111112`, q<0.05 cells `23`
  - `proxy_sigma_controller:geomdense__sigma_down_factor_0p9__sigma_min_ratio_0p03`: median delta `-47.68829804886346`, win-rate `0.6533333333333334`, q<0.05 cells `25`
  - `proxy_sigma_controller:geomdense__sigma_down_factor_0p88__sigma_min_ratio_0p03`: median delta `-47.52133602705296`, win-rate `0.6377777777777778`, q<0.05 cells `23`
  - `proxy_sigma_controller:geomdense__sigma_down_factor_0p95__sigma_min_ratio_0p02`: median delta `-47.248645516394745`, win-rate `0.6133333333333333`, q<0.05 cells `22`
  - `proxy_sigma_controller:geomdense__sigma_down_factor_0p95__sigma_min_ratio_0p03`: median delta `-47.19171740569036`, win-rate `0.6116666666666666`, q<0.05 cells `22`
  - `proxy_sigma_controller:geomdense__sigma_down_factor_0p86__sigma_min_ratio_0p02`: median delta `-47.071629031839215`, win-rate `0.6572222222222222`, q<0.05 cells `25`
  - `proxy_sigma_controller:geomdense__sigma_down_factor_0p93__sigma_min_ratio_0p05`: median delta `-45.820589916410654`, win-rate `0.6061111111111112`, q<0.05 cells `27`

## Behavior Summary
- Behavior rows: `115200`
- Methods with behavior telemetry: `64`

## Hypothesis Checks
- Total checks: `3`
- Passed: `3`
- Failed: `0`
- Errors: `0`

## Warnings

## Artifact Links
- `analysis_manifest_json`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/analysis_manifest.json`
- `behavior_aggregate_csv`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/behavior_aggregate.csv`
- `cell_stats_csv`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/cell_stats.csv`
- `figure_behavior_floor`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/figures/behavior_fraction_at_floor_bar.png`
- `figure_behavior_ttf`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/figures/behavior_time_to_first_floor_bar.png`
- `figure_method_delta`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/figures/method_median_delta_bar.png`
- `figure_method_win_rate`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/figures/method_win_rate_bar.png`
- `hypothesis_checks_json`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/hypothesis_checks.json`
- `manifest_json`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/manifest.json`
- `method_aggregate_csv`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/method_aggregate.csv`
- `pairwise_json_pairwise_proxy_sigma_controller_geomdense__sigma_down_factor_0p9__sigma_min_ratio_0p1_vs_vanilla_cma`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/pairwise_proxy_sigma_controller_geomdense__sigma_down_factor_0p9__sigma_min_ratio_0p1_vs_vanilla_cma.json`
- `runs_long_csv`: `artifacts/runs/descent-geometry/dense/20260306T052148Z-cdeecf15/results/runs_long.csv`
