# Changelog

## v0.1.0

- Implemented `v0.1-r3` controller core per technical spec.
- Added deterministic policy API: `initialize`, `step`, `finalize`.
- Added strict config/input/state validation and typed error hierarchy.
- Added mechanism-aware phase logic with bounded recovery behavior.
- Added run-level telemetry contract with `proxy_schema_version=1`.
- Added deterministic hybrid trace selector and CSV trace writer.
- Added reference `PyCMAAdapter` with post-`tell` sigma mutation boundary.
- Added sigma-drift assertion mode for integration tests.
- Added reference runner for vanilla/proxy smoke comparisons.
- Added unit + integration + determinism test suites with coverage gating.
