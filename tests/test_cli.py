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


def _write_swat_csv(path: Path, rows: int, attack_start: int | None = None) -> None:
    index = np.arange(rows)
    attack = np.zeros(rows, dtype=bool)
    if attack_start is not None:
        attack[attack_start : attack_start + 40] = True
    pd.DataFrame(
        {
            "Timestamp": pd.date_range("2026-01-01", periods=rows, freq="s"),
            "LIT101": 500 + 12 * np.sin(index / 18) + attack * 200,
            "FIT101": 2.5 + 0.1 * np.cos(index / 13) - attack * 1.7,
            "MV101": (np.sin(index / 25) > 0).astype(float),
            "Normal/Attack": np.where(attack, "Attack", "Normal"),
        }
    ).to_csv(path, index=False)


def _write_scheduled_swat_xlsx(path: Path) -> None:
    rows: list[list[object]] = [
        ["", "P1", "", ""],
        ["GMT +0", "FIT 401", "LIT 301", "P601 Status"],
        ["timestamp", "value", "value", "value"],
    ]
    timestamps = pd.date_range("2019-07-20T04:35:00Z", "2019-07-20T08:25:00Z", freq="s")
    for index, timestamp in enumerate(timestamps):
        attack = (
            pd.Timestamp("2019-07-20T07:08:46Z")
            <= timestamp
            <= pd.Timestamp("2019-07-20T07:10:31Z")
        )
        rows.append(
            [
                timestamp.isoformat().replace("+00:00", "Z"),
                0.8 - attack * 0.35,
                800 + 5 * np.sin(index / 40) + attack * 200,
                "On" if attack else "Off",
            ]
        )
    pd.DataFrame(rows).to_excel(path, index=False, header=False)


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


def test_swat_command_writes_detection_events_and_plot(tmp_path: Path) -> None:
    normal = tmp_path / "normal.csv"
    attack = tmp_path / "attack.csv"
    _write_swat_csv(normal, 400)
    _write_swat_csv(attack, 250, attack_start=100)
    output = tmp_path / "swat-security.csv"
    events = tmp_path / "swat-events.json"
    plot = tmp_path / "swat.html"

    exit_code = main(
        [
            "swat",
            "--config",
            str(ROOT / "config" / "default.yaml"),
            "--normal",
            str(normal),
            "--attack",
            str(attack),
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


def test_swat_scheduled_run_command_writes_detection_events_and_plot(tmp_path: Path) -> None:
    scheduled = tmp_path / "swat-a4-a5.xlsx"
    _write_scheduled_swat_xlsx(scheduled)
    output = tmp_path / "swat-security.csv"
    events = tmp_path / "swat-events.json"
    plot = tmp_path / "swat.html"

    exit_code = main(
        [
            "swat",
            "--config",
            str(ROOT / "config" / "default.yaml"),
            "--scheduled-run",
            str(scheduled),
            "--schedule",
            "swat-a4-a5-jul-2019",
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
    assert frame["is_attack"].sum() > 0
    assert frame["detected"].sum() > 0


def test_demo_command_writes_reproducible_report_and_manifest(tmp_path: Path) -> None:
    output = tmp_path / "demo"

    exit_code = main(
        [
            "demo",
            "--config",
            str(ROOT / "config" / "default.yaml"),
            "--scenario",
            str(ROOT / "config" / "scenarios" / "pv-false-data-injection.yaml"),
            "--output-dir",
            str(output),
            "--health-result",
            str(tmp_path / "missing-health.csv"),
            "--swat-result",
            str(tmp_path / "missing-swat.csv"),
        ]
    )

    report = output / "demo-summary.md"
    manifest = output / "demo-manifest.json"
    detection = output / "nanogrid-detection.csv"
    events = output / "nanogrid-events.json"
    alerts = output / "nanogrid-alerts.json"

    assert exit_code == 0
    assert report.is_file()
    assert manifest.is_file()
    assert detection.is_file()
    assert events.is_file()
    assert alerts.is_file()
    report_text = report.read_text(encoding="utf-8")
    assert "CPS Sentinel reproducible demo" in report_text
    assert "Nanogrid attack/fault demonstrator" in report_text
    assert "NASA battery health validation" in report_text
    assert "iTrust SWaT security validation" in report_text
    assert "Raw NASA and iTrust/SWaT files are not copied" in report_text
