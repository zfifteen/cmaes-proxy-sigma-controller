#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from experiments.descent_geometry import generate_descent_geometry_metrics  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute descent-geometry metrics from runs_long and proxy traces."
    )
    parser.add_argument("--runs", required=True, help="Path to runs_long.csv")
    parser.add_argument("--config", required=True, help="Path to experiment YAML config")
    parser.add_argument("--outdir", required=True, help="Directory for descent metric artifacts")
    args = parser.parse_args()

    outputs = generate_descent_geometry_metrics(
        runs_csv=args.runs,
        config_path=args.config,
        outdir=args.outdir,
    )
    print(json.dumps(outputs, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

