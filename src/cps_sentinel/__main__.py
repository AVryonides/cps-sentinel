"""Command-line entry point for CPS Sentinel."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from cps_sentinel.config import load_settings
from cps_sentinel.demo import run_demo_workflow
from cps_sentinel.detection import (
    HybridDetector,
    aggregate_events,
    evaluate_detection,
    write_events,
)
from cps_sentinel.detection.plotting import write_detection_plot
from cps_sentinel.health import (
    analyze_battery_health,
    build_health_alerts,
    evaluate_rul,
    load_nasa_batteries,
    write_health_alerts,
)
from cps_sentinel.health.plotting import write_health_plot
from cps_sentinel.risk import assess_events, write_alerts
from cps_sentinel.risk.plotting import write_risk_plot
from cps_sentinel.scenarios import load_scenario, summarize_scenario
from cps_sentinel.scenarios.plotting import write_scenario_plot
from cps_sentinel.simulation import run_simulation, summarize_simulation
from cps_sentinel.simulation.plotting import write_simulation_plot
from cps_sentinel.swat import (
    SWAT_A4_A5_JUL_2019_ATTACK_WINDOWS,
    SwatDetector,
    aggregate_swat_events,
    evaluate_swat_detection,
    load_swat_file,
    load_swat_scheduled_file,
    write_swat_events,
)
from cps_sentinel.swat.plotting import write_swat_plot
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

    assess = commands.add_parser("assess", help="Run Phase 5 risk assessment and response guidance")
    assess.add_argument("--config", default="config/default.yaml", help="Path to YAML config")
    assess.add_argument("--scenario", required=True, help="Path to scenario YAML")
    assess.add_argument(
        "--output",
        default="data/simulated/assessment.csv",
        help="Destination row-level detection CSV",
    )
    assess.add_argument(
        "--alerts",
        default="data/simulated/alerts.json",
        help="Destination prioritized alert JSON",
    )
    assess.add_argument("--plot", help="Optional destination for an interactive HTML plot")

    health = commands.add_parser("health", help="Run Phase 7 NASA battery health validation")
    health.add_argument("--config", default="config/default.yaml", help="Path to YAML config")
    health.add_argument(
        "--input",
        default="data/raw/nasa/battery-aging-fy08q4",
        help="NASA B*.mat file or directory",
    )
    health.add_argument(
        "--output",
        default="data/processed/nasa-battery-health.csv",
        help="Destination cycle-level health CSV",
    )
    health.add_argument(
        "--alerts",
        default="data/processed/nasa-health-alerts.json",
        help="Destination latest battery health alerts",
    )
    health.add_argument("--plot", help="Optional destination for an interactive HTML plot")

    swat = commands.add_parser("swat", help="Run Phase 8 iTrust SWaT security validation")
    swat.add_argument("--config", default="config/default.yaml", help="Path to YAML config")
    swat.add_argument("--normal", help="Authorized normal historian CSV/XLSX")
    swat.add_argument("--attack", help="Authorized labeled attack historian CSV/XLSX")
    swat.add_argument(
        "--scheduled-run",
        help="Authorized single-run historian CSV/XLSX labelled from an official schedule",
    )
    swat.add_argument(
        "--schedule",
        choices=["swat-a4-a5-jul-2019"],
        help="Built-in official attack schedule used with --scheduled-run",
    )
    swat.add_argument(
        "--sample-stride",
        type=int,
        default=1,
        help="Keep every Nth row; default preserves the original one-second resolution",
    )
    swat.add_argument(
        "--output",
        default="data/processed/swat-security.csv",
        help="Destination row-level security CSV",
    )
    swat.add_argument(
        "--events",
        default="data/processed/swat-security-events.json",
        help="Destination aggregated event JSON",
    )
    swat.add_argument("--plot", help="Optional destination for an interactive HTML report")

    demo = commands.add_parser("demo", help="Run the Phase 11 reproducible local demo workflow")
    demo.add_argument("--config", default="config/default.yaml", help="Path to YAML config")
    demo.add_argument(
        "--scenario",
        default="config/scenarios/pv-false-data-injection.yaml",
        help="Flagship scenario YAML used for the nanogrid demo",
    )
    demo.add_argument(
        "--output-dir",
        default="reports/demo",
        help="Directory for local demo report, manifest, CSV, JSON, and HTML artifacts",
    )
    demo.add_argument(
        "--health-result",
        default="data/processed/nasa-battery-health.csv",
        help="Optional processed NASA health CSV to summarize if present",
    )
    demo.add_argument(
        "--swat-result",
        default="data/processed/swat-security.csv",
        help="Optional processed SWaT security CSV to summarize if present",
    )
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

    if args.command == "assess":
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
        alerts = assess_events(frame, aggregate_events(frame), settings)
        alerts_path = write_alerts(alerts, args.alerts)
        if args.plot:
            plot_path = write_risk_plot(frame, alerts, settings.simulation.battery, args.plot)
            print(f"Interactive risk report: {plot_path}")
        print(f"Risk assessment complete: {scenario_spec.name}")
        print(f"Prioritized alerts: {len(alerts)}")
        for alert in alerts:
            print(
                f"#{alert.priority} {alert.alert_id}: {alert.risk_level.upper()} "
                f"({alert.risk_score:.1f}/100) - {alert.likely_event}"
            )
            print(f"  Recommended first action: {alert.recommended_actions[0]}")
        print(f"Row-level output: {output}")
        print(f"Alert output: {alerts_path}")
        return 0

    if args.command == "health":
        raw = load_nasa_batteries(args.input)
        frame = analyze_battery_health(raw, settings.health)
        health_evaluation = evaluate_rul(frame)
        health_alerts = build_health_alerts(frame)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        alerts_path = write_health_alerts(health_alerts, args.alerts)
        if args.plot:
            plot_path = write_health_plot(frame, settings.health, args.plot)
            print(f"Interactive health report: {plot_path}")
        print("NASA battery health validation complete")
        print(f"Batteries: {frame['battery_id'].nunique()}")
        print(f"Discharge cycles: {len(frame)}")
        print(f"RUL predictions evaluated: {health_evaluation.evaluated_predictions}")
        print(f"RUL MAE: {health_evaluation.mae_cycles:.2f} cycles")
        print(f"RUL RMSE: {health_evaluation.rmse_cycles:.2f} cycles")
        for health_alert in health_alerts:
            print(
                f"{health_alert.battery_id}: {health_alert.health_status.upper()} - "
                f"SOH {health_alert.state_of_health:.1%}, "
                f"estimated RUL {health_alert.estimated_rul_cycles} cycles"
            )
        print(f"Cycle-level output: {output}")
        print(f"Health alert output: {alerts_path}")
        return 0

    if args.command == "swat":
        if args.scheduled_run:
            if args.schedule != "swat-a4-a5-jul-2019":
                raise SystemExit(
                    "--scheduled-run currently requires --schedule swat-a4-a5-jul-2019"
                )
            normal = load_swat_scheduled_file(
                args.scheduled_run,
                attack_windows=SWAT_A4_A5_JUL_2019_ATTACK_WINDOWS,
                start="2019-07-20T04:35:00Z",
                end="2019-07-20T07:08:45Z",
                sample_stride=args.sample_stride,
            )
            attack = load_swat_scheduled_file(
                args.scheduled_run,
                attack_windows=SWAT_A4_A5_JUL_2019_ATTACK_WINDOWS,
                start="2019-07-20T07:08:46Z",
                end="2019-07-20T08:16:18Z",
                sample_stride=args.sample_stride,
            )
        else:
            if args.normal is None or args.attack is None:
                raise SystemExit(
                    "Provide either --normal and --attack, or --scheduled-run with --schedule"
                )
            normal = load_swat_file(args.normal, sample_stride=args.sample_stride)
            attack = load_swat_file(
                args.attack,
                assume_attack=False,
                sample_stride=args.sample_stride,
            )
        swat_detector = SwatDetector(settings.swat, settings.random_seed).fit(normal)
        frame = swat_detector.detect(attack)
        swat_evaluation = evaluate_swat_detection(frame)
        swat_events = aggregate_swat_events(frame, settings.swat)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, index=False)
        events_path = write_swat_events(swat_events, args.events)
        if args.plot:
            plot_path = write_swat_plot(frame, swat_events, swat_evaluation, args.plot)
            print(f"Interactive SWaT report: {plot_path}")
        print("iTrust SWaT security validation complete")
        print(f"Historian rows evaluated: {swat_evaluation.rows}")
        print(f"Labeled attack rows: {swat_evaluation.attack_rows}")
        print(f"Point precision: {swat_evaluation.precision:.3f}")
        print(f"Point recall: {swat_evaluation.recall:.3f}")
        print(f"Point F1: {swat_evaluation.f1:.3f}")
        print(f"False-positive rate: {swat_evaluation.false_positive_rate:.3f}")
        print(
            f"Attack events detected: {swat_evaluation.detected_attack_events}/"
            f"{swat_evaluation.ground_truth_events}"
        )
        print(f"Aggregated detection events: {len(swat_events)}")
        print(f"Row-level output: {output}")
        print(f"Event output: {events_path}")
        return 0

    if args.command == "demo":
        demo_result = run_demo_workflow(
            root=Path.cwd(),
            settings=settings,
            scenario_path=Path(args.scenario),
            output_dir=Path(args.output_dir),
            health_result_path=Path(args.health_result),
            swat_result_path=Path(args.swat_result),
        )
        print("Reproducible demo complete")
        print(f"Output directory: {demo_result.output_dir}")
        print(f"Summary report: {demo_result.report_path}")
        print(f"Manifest: {demo_result.manifest_path}")
        for track in demo_result.tracks:
            print(f"{track.name}: {track.status}")
            if track.metrics:
                metrics = ", ".join(f"{key}={value}" for key, value in track.metrics.items())
                print(f"  {metrics}")
            if track.next_step:
                print(f"  Next step: {track.next_step}")
        return 0

    steps = settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
    print(
        f"{settings.project_name}: configuration valid "
        f"({settings.simulation.duration_hours} h, {steps} steps)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
