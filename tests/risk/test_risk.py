import json
from pathlib import Path

import pandas as pd
import pytest

from cps_sentinel.config import Settings, load_settings
from cps_sentinel.detection import HybridDetector, aggregate_events
from cps_sentinel.risk import assess_events, write_alerts
from cps_sentinel.scenarios import load_scenario
from cps_sentinel.simulation import run_simulation
from cps_sentinel.twin import run_digital_twin

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def settings() -> Settings:
    return load_settings(ROOT / "config" / "default.yaml")


@pytest.fixture
def detector(settings: Settings) -> HybridDetector:
    normal = run_digital_twin(settings, run_simulation(settings))
    return HybridDetector(settings.detection, settings.random_seed).fit(normal)


def _assess(
    settings: Settings, detector: HybridDetector, filename: str
) -> tuple[pd.DataFrame, list]:
    scenario = load_scenario(ROOT / "config" / "scenarios" / filename, total_steps=288)
    frame = detector.detect(run_digital_twin(settings, run_simulation(settings, scenario)))
    return frame, assess_events(frame, aggregate_events(frame), settings)


def test_flagship_alert_is_high_risk_and_actionable(
    settings: Settings, detector: HybridDetector
) -> None:
    _, alerts = _assess(settings, detector, "pv-false-data-injection.yaml")

    assert alerts
    alert = alerts[0]
    assert alert.risk_level in {"high", "critical"}
    assert 0 <= alert.risk_score <= 100
    assert alert.affected_component == "pv_sensor"
    assert "untrusted" in alert.recommended_actions[0]
    assert any("digital-twin" in action for action in alert.recommended_actions)
    assert "operator" in alert.safety_note


def test_command_attack_gets_command_path_containment(
    settings: Settings, detector: HybridDetector
) -> None:
    _, alerts = _assess(settings, detector, "battery-actuator-manipulation.yaml")

    assert alerts[0].affected_component == "battery_command_path"
    assert any(
        "Block the suspect command path" in action for action in alerts[0].recommended_actions
    )
    assert any("bounded" in action for action in alerts[0].recommended_actions)


def test_alerts_are_ranked_and_json_serializable(
    settings: Settings, detector: HybridDetector, tmp_path: Path
) -> None:
    _, alerts = _assess(settings, detector, "pv-false-data-injection.yaml")
    output = write_alerts(alerts, tmp_path / "alerts.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert [alert.priority for alert in alerts] == list(range(1, len(alerts) + 1))
    assert [alert.risk_score for alert in alerts] == sorted(
        [alert.risk_score for alert in alerts], reverse=True
    )
    assert payload[0]["risk_score"] == alerts[0].risk_score
    assert payload[0]["physical_impact"].startswith("Peak grid-flow divergence")


@pytest.mark.parametrize(
    "filename",
    [
        "battery-actuator-manipulation.yaml",
        "battery-command-delay.yaml",
        "battery-efficiency-loss.yaml",
        "pv-false-data-injection.yaml",
        "pv-replay-attack.yaml",
        "pv-sensor-failure.yaml",
        "pv-sensor-freeze.yaml",
        "pv-sensor-noise-fault.yaml",
    ],
)
def test_every_catalog_scenario_produces_a_bounded_alert(
    settings: Settings, detector: HybridDetector, filename: str
) -> None:
    _, alerts = _assess(settings, detector, filename)

    assert alerts
    assert all(0 <= alert.risk_score <= 100 for alert in alerts)
    assert all(alert.recommended_actions for alert in alerts)
