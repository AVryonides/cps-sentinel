import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.io import savemat

from cps_sentinel.config import Settings, load_settings
from cps_sentinel.health import (
    analyze_battery_health,
    build_health_alerts,
    evaluate_rul,
    load_nasa_batteries,
    load_nasa_battery,
    write_health_alerts,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def settings() -> Settings:
    return load_settings(ROOT / "config" / "default.yaml")


def write_battery_mat(path: Path, capacities: list[float]) -> Path:
    cycles: list[dict[str, object]] = []
    for index, capacity in enumerate(capacities, start=1):
        cycles.append(
            {
                "type": "discharge",
                "ambient_temperature": 24.0,
                "time": np.array([2026, 1, 1, 0, index, 0]),
                "data": {
                    "Voltage_measured": np.array([4.1, 3.6, 2.7]),
                    "Temperature_measured": np.array([24.0, 28.0, 31.0]),
                    "Time": np.array([0.0, 900.0, 1800.0]),
                    "Capacity": capacity,
                },
            }
        )
        cycles.append(
            {
                "type": "charge",
                "ambient_temperature": 24.0,
                "time": np.array([2026, 1, 1, 1, index, 0]),
                "data": {"Voltage_measured": np.array([3.0, 4.2])},
            }
        )
    savemat(path, {path.stem: {"cycle": np.array(cycles, dtype=object)}})
    return path


def test_nasa_matlab_loader_extracts_discharge_contract(tmp_path: Path) -> None:
    source = write_battery_mat(tmp_path / "BTEST.mat", [1.95, 1.90, 1.85])

    frame = load_nasa_battery(source)

    assert list(frame["cycle_index"]) == [1, 2, 3]
    assert list(frame["capacity_ah"]) == pytest.approx([1.95, 1.90, 1.85])
    assert frame["minimum_voltage_v"].min() == pytest.approx(2.7)
    assert frame["maximum_temperature_c"].max() == pytest.approx(31.0)
    assert frame["timestamp"].str.endswith("+00:00").all()


def test_directory_loader_combines_batteries(tmp_path: Path) -> None:
    write_battery_mat(tmp_path / "B0001.mat", [1.9, 1.8])
    write_battery_mat(tmp_path / "B0002.mat", [1.85, 1.75])

    frame = load_nasa_batteries(tmp_path)

    assert set(frame["battery_id"]) == {"B0001", "B0002"}
    assert len(frame) == 4


def test_causal_health_baseline_estimates_degradation_and_rul(settings: Settings) -> None:
    cycles = np.arange(1, 101)
    frame = pd.DataFrame(
        {
            "battery_id": "BTEST",
            "cycle_index": cycles,
            "capacity_ah": 2.0 - 0.007 * cycles,
        }
    )

    analyzed = analyze_battery_health(frame, settings.health)
    evaluation = evaluate_rul(analyzed)

    assert analyzed.loc[0, "estimated_rul_cycles"] != analyzed.loc[0, "estimated_rul_cycles"]
    assert analyzed.loc[30, "estimated_rul_cycles"] == pytest.approx(54.7, abs=1)
    assert analyzed.iloc[-1]["health_status"] == "critical"
    assert evaluation.evaluated_predictions > 70
    assert evaluation.mae_cycles < 1.0


def test_health_alert_is_explainable_and_serializable(settings: Settings, tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "battery_id": "BTEST",
            "cycle_index": np.arange(1, 101),
            "capacity_ah": 2.0 - 0.007 * np.arange(1, 101),
        }
    )
    analyzed = analyze_battery_health(frame, settings.health)
    alerts = build_health_alerts(analyzed)
    output = write_health_alerts(alerts, tmp_path / "health-alerts.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert alerts[0].health_status == "critical"
    assert "rated capacity" in alerts[0].physical_impact
    assert any("replacement" in action for action in alerts[0].recommended_actions)
    assert payload[0]["battery_id"] == "BTEST"
