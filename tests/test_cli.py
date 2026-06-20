from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import savemat

from cps_sentinel.__main__ import main

ROOT = Path(__file__).resolve().parents[1]


def _write_battery_mat(path: Path, capacities: list[float]) -> None:
    cycles: list[dict[str, object]] = []
    for index, capacity in enumerate(capacities, start=1):
        cycles.append(
            {
                "type": "discharge",
                "ambient_temperature": 24.0,
                "time": np.array([2026, 1, 1, index // 60, index % 60, 0]),
                "data": {
                    "Voltage_measured": np.array([4.1, 3.6, 2.7]),
                    "Temperature_measured": np.array([24.0, 28.0, 31.0]),
                    "Time": np.array([0.0, 900.0, 1800.0]),
                    "Capacity": capacity,
                },
            }
        )
    savemat(path, {path.stem: {"cycle": np.array(cycles, dtype=object)}})


def test_validate_command() -> None:
    exit_code = main(["validate", "--config", str(ROOT / "config" / "default.yaml")])

    assert exit_code == 0


def test_simulate_command_writes_csv(tmp_path: Path) -> None:
    output = tmp_path / "simulation.csv"
    plot = tmp_path / "simulation.html"

    exit_code = main(
        [
            "simulate",
            "--config",
            str(ROOT / "config" / "default.yaml"),
            "--output",
            str(output),
            "--plot",
            str(plot),
        ]
    )

    assert exit_code == 0
    assert output.is_file()
    assert plot.is_file()
    assert len(pd.read_csv(output)) == 288


def test_twin_command_writes_csv_and_plot(tmp_path: Path) -> None:
    output = tmp_path / "twin.csv"
    plot = tmp_path / "twin.html"

    exit_code = main(
        [
            "twin",
            "--config",
            str(ROOT / "config" / "default.yaml"),
            "--output",
            str(output),
            "--plot",
            str(plot),
        ]
    )

    frame = pd.read_csv(output)
    assert exit_code == 0
    assert plot.is_file()
    assert len(frame) == 288
    assert "expected_grid_power_kw" in frame
    assert "grid_power_residual_kw" in frame


def test_scenario_command_writes_labeled_csv_and_plot(tmp_path: Path) -> None:
    output = tmp_path / "scenario.csv"
    plot = tmp_path / "scenario.html"

    exit_code = main(
        [
            "scenario",
            "--config",
            str(ROOT / "config" / "default.yaml"),
            "--scenario",
            str(ROOT / "config" / "scenarios" / "pv-false-data-injection.yaml"),
            "--output",
            str(output),
            "--plot",
            str(plot),
        ]
    )

    frame = pd.read_csv(output)
    assert exit_code == 0
    assert plot.is_file()
    assert frame["scenario_active"].sum() == 36
    assert set(frame.loc[frame["scenario_active"], "ground_truth_label"]) == {"attack"}


def test_detect_command_writes_scored_csv_events_and_plot(tmp_path: Path) -> None:
    output = tmp_path / "detection.csv"
    events = tmp_path / "events.json"
    plot = tmp_path / "detection.html"

    exit_code = main(
        [
            "detect",
            "--config",
            str(ROOT / "config" / "default.yaml"),
            "--scenario",
            str(ROOT / "config" / "scenarios" / "pv-false-data-injection.yaml"),
            "--output",
            str(output),
            "--events",
            str(events),
            "--plot",
            str(plot),
        ]
    )

    frame = pd.read_csv(output)
    assert exit_code == 0
    assert events.is_file()
    assert plot.is_file()
    assert frame["detected"].sum() > 0
    assert "likely_event" in frame


def test_assess_command_writes_detection_alerts_and_risk_plot(tmp_path: Path) -> None:
    output = tmp_path / "assessment.csv"
    alerts = tmp_path / "alerts.json"
    plot = tmp_path / "risk.html"

    exit_code = main(
        [
            "assess",
            "--config",
            str(ROOT / "config" / "default.yaml"),
            "--scenario",
            str(ROOT / "config" / "scenarios" / "pv-false-data-injection.yaml"),
            "--output",
            str(output),
            "--alerts",
            str(alerts),
            "--plot",
            str(plot),
        ]
    )

    frame = pd.read_csv(output)
    assert exit_code == 0
    assert alerts.is_file()
    assert plot.is_file()
    assert frame["detected"].sum() > 0


def test_health_command_writes_cycle_health_alerts_and_plot(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_battery_mat(raw / "BTEST.mat", list(np.linspace(1.95, 1.30, 100)))
    output = tmp_path / "health.csv"
    alerts = tmp_path / "health-alerts.json"
    plot = tmp_path / "health.html"

    exit_code = main(
        [
            "health",
            "--config",
            str(ROOT / "config" / "default.yaml"),
            "--input",
            str(raw),
            "--output",
            str(output),
            "--alerts",
            str(alerts),
            "--plot",
            str(plot),
        ]
    )

    frame = pd.read_csv(output)
    assert exit_code == 0
    assert alerts.is_file()
    assert plot.is_file()
    assert "estimated_rul_cycles" in frame
