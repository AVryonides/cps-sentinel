"""Command-line entry point for CPS Sentinel."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from cps_sentinel.config import load_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a CPS Sentinel configuration.")
    parser.add_argument("--config", default="config/default.yaml", help="Path to YAML config")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = load_settings(args.config)
    steps = settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
    print(
        f"{settings.project_name}: configuration valid "
        f"({settings.simulation.duration_hours} h, {steps} steps)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
