"""Command-line entry point for CPS Sentinel."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from cps_sentinel.config import load_settings
from cps_sentinel.simulation import run_simulation, summarize_simulation
from cps_sentinel.simulation.plotting import write_simulation_plot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CPS Sentinel command-line interface.")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="Validate a project configuration")
    validate.add_argument("--config", default="config/default.yaml", help="Path to YAML config")

    simulate = commands.add_parser("simulate", help="Run the Phase 1 nanogrid simulator")
    simulate.add_argument("--config", default="config/default.yaml", help="Path to YAML config")
    simulate.add_argument(
        "--output",
        default="data/simulated/baseline.csv",
        help="Destination CSV path",
    )
    simulate.add_argument("--plot", help="Optional destination for an interactive HTML plot")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if not arguments or arguments[0].startswith("-"):
        arguments.insert(0, "validate")
    args = build_parser().parse_args(arguments)
    settings = load_settings(args.config)

    if args.command == "simulate":
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        frame = run_simulation(settings)
        frame.to_csv(output, index=False)
        if args.plot:
            plot_path = write_simulation_plot(frame, settings.simulation.battery, args.plot)
            print(f"Interactive plot: {plot_path}")
        summary = summarize_simulation(frame, settings.simulation.timestep_minutes)
        print(f"Simulation complete: {output}")
        print(f"Rows: {summary.rows}")
        print(f"SOC range: {summary.minimum_soc:.3f} to {summary.maximum_soc:.3f}")
        print(f"Grid import: {summary.imported_energy_kwh:.3f} kWh")
        print(f"Grid export: {summary.exported_energy_kwh:.3f} kWh")
        print(f"Maximum power-balance error: {summary.maximum_balance_error_kw:.3e} kW")
        return 0

    steps = settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
    print(
        f"{settings.project_name}: configuration valid "
        f"({settings.simulation.duration_hours} h, {steps} steps)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
