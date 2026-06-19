"""Command-line entry point for CPS Sentinel."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from cps_sentinel.config import load_settings
from cps_sentinel.detection import (
    HybridDetector,
    aggregate_events,
    evaluate_detection,
    write_events,
)
from cps_sentinel.detection.plotting import write_detection_plot
from cps_sentinel.scenarios import load_scenario, summarize_scenario
from cps_sentinel.scenarios.plotting import write_scenario_plot
from cps_sentinel.simulation import run_simulation, summarize_simulation
from cps_sentinel.simulation.plotting import write_simulation_plot
from cps_sentinel.twin import run_digital_twin, summarize_twin
from cps_sentinel.twin.plotting import write_twin_plot


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

    twin = commands.add_parser("twin", help="Run the Phase 2 independent digital twin")
    twin.add_argument("--config", default="config/default.yaml", help="Path to YAML config")
    twin.add_argument("--input", help="Optional observed simulation CSV; generated if omitted")
    twin.add_argument(
        "--output",
        default="data/simulated/twin-baseline.csv",
        help="Destination CSV path",
    )
    twin.add_argument("--plot", help="Optional destination for an interactive HTML plot")

    scenario = commands.add_parser("scenario", help="Run a labeled Phase 3 attack or fault")
    scenario.add_argument("--config", default="config/default.yaml", help="Path to YAML config")
    scenario.add_argument("--scenario", required=True, help="Path to scenario YAML")
    scenario.add_argument(
        "--output",
        default="data/simulated/scenario.csv",
        help="Destination labeled CSV path",
    )
    scenario.add_argument("--plot", help="Optional destination for an interactive HTML plot")

    detect = commands.add_parser("detect", help="Run Phase 4 hybrid detection and diagnosis")
    detect.add_argument("--config", default="config/default.yaml", help="Path to YAML config")
    detect.add_argument("--scenario", required=True, help="Path to scenario YAML")
    detect.add_argument(
        "--output",
        default="data/simulated/detection.csv",
        help="Destination row-level detection CSV",
    )
    detect.add_argument(
        "--events",
        default="data/simulated/events.json",
        help="Destination aggregated event JSON",
    )
    detect.add_argument("--plot", help="Optional destination for an interactive HTML plot")
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
        simulation_summary = summarize_simulation(frame, settings.simulation.timestep_minutes)
        print(f"Simulation complete: {output}")
        print(f"Rows: {simulation_summary.rows}")
        print(
            f"SOC range: {simulation_summary.minimum_soc:.3f} "
            f"to {simulation_summary.maximum_soc:.3f}"
        )
        print(f"Grid import: {simulation_summary.imported_energy_kwh:.3f} kWh")
        print(f"Grid export: {simulation_summary.exported_energy_kwh:.3f} kWh")
        print(f"Maximum power-balance error: {simulation_summary.maximum_balance_error_kw:.3e} kW")
        return 0

    if args.command == "twin":
        observed = pd.read_csv(args.input) if args.input else run_simulation(settings)
        frame = run_digital_twin(settings, observed)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        if args.plot:
            plot_path = write_twin_plot(frame, args.plot)
            print(f"Interactive plot: {plot_path}")
        twin_summary = summarize_twin(frame)
        print(f"Digital twin complete: {output}")
        print(f"Rows: {twin_summary.rows}")
        print(f"PV MAE: {twin_summary.pv_mae_kw:.4f} kW")
        print(f"Load MAE: {twin_summary.load_mae_kw:.4f} kW")
        print(f"Battery-power MAE: {twin_summary.battery_power_mae_kw:.4f} kW")
        print(f"Grid-power MAE: {twin_summary.grid_power_mae_kw:.4f} kW")
        print(f"Battery-SOC MAE: {twin_summary.battery_soc_mae:.5f}")
        print(f"Controller agreement: {twin_summary.controller_action_agreement:.1%}")
        print(f"Maximum twin balance error: {twin_summary.maximum_twin_balance_error_kw:.3e} kW")
        return 0

    if args.command == "scenario":
        total_steps = (
            settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
        )
        scenario_spec = load_scenario(args.scenario, total_steps)
        observed = run_simulation(settings, scenario_spec)
        frame = run_digital_twin(settings, observed)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        if args.plot:
            plot_path = write_scenario_plot(frame, args.plot)
            print(f"Interactive plot: {plot_path}")
        scenario_summary = summarize_scenario(frame)
        print(f"Scenario complete: {scenario_spec.name}")
        print(f"Kind: {scenario_spec.kind.value} ({scenario_spec.ground_truth_label})")
        print(f"Target: {scenario_spec.target.value}")
        print(f"Active steps: {scenario_summary.active_steps}")
        print(f"Peak PV sensor error: {scenario_summary.peak_pv_sensor_error_kw:.4f} kW")
        print(f"Peak load sensor error: {scenario_summary.peak_load_sensor_error_kw:.4f} kW")
        print(f"Peak command deviation: {scenario_summary.peak_command_deviation_kw:.4f} kW")
        print(f"Peak grid residual: {scenario_summary.peak_grid_residual_kw:.4f} kW")
        print(f"Peak SOC residual: {scenario_summary.peak_soc_residual:.5f}")
        print(
            f"Active controller disagreement: "
            f"{scenario_summary.active_action_disagreement_rate:.1%}"
        )
        print(f"Labeled output: {output}")
        return 0

    if args.command == "detect":
        total_steps = (
            settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
        )
        scenario_spec = load_scenario(args.scenario, total_steps)
        normal_twin = run_digital_twin(settings, run_simulation(settings))
        scenario_twin = run_digital_twin(settings, run_simulation(settings, scenario_spec))
        detector = HybridDetector(settings.detection, settings.random_seed).fit(normal_twin)
        frame = detector.detect(scenario_twin)

        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        events = aggregate_events(frame)
        events_path = write_events(events, args.events)
        if args.plot:
            plot_path = write_detection_plot(frame, args.plot)
            print(f"Interactive plot: {plot_path}")
        evaluation = evaluate_detection(frame)
        print(f"Detection complete: {scenario_spec.name}")
        print(f"Precision: {evaluation.precision:.3f}")
        print(f"Recall: {evaluation.recall:.3f}")
        print(f"F1: {evaluation.f1:.3f}")
        print(f"False-positive rate: {evaluation.false_positive_rate:.3f}")
        print(f"Event detected: {evaluation.event_detected}")
        print(f"Detection delay: {evaluation.detection_delay_steps} steps")
        print(f"Aggregated events: {len(events)}")
        print(f"Row-level output: {output}")
        print(f"Event output: {events_path}")
        return 0

    steps = settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
    print(
        f"{settings.project_name}: configuration valid "
        f"({settings.simulation.duration_hours} h, {steps} steps)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
