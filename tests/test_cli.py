from pathlib import Path

import pandas as pd

from cps_sentinel.__main__ import main

ROOT = Path(__file__).resolve().parents[1]


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
