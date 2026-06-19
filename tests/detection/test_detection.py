import json
from pathlib import Path

import pandas as pd
import pytest

from cps_sentinel.config import Settings, load_settings
from cps_sentinel.detection import (
    HybridDetector,
    aggregate_events,
    evaluate_detection,
    write_events,
)
from cps_sentinel.scenarios import load_scenario
from cps_sentinel.simulation import run_simulation
from cps_sentinel.twin import run_digital_twin

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def settings() -> Settings:
    return load_settings(ROOT / "config" / "default.yaml")


@pytest.fixture
def normal_twin(settings: Settings) -> pd.DataFrame:
    return run_digital_twin(settings, run_simulation(settings))


@pytest.fixture
def detector(settings: Settings, normal_twin: pd.DataFrame) -> HybridDetector:
    return HybridDetector(settings.detection, settings.random_seed).fit(normal_twin)


def _scenario_frame(settings: Settings, filename: str) -> pd.DataFrame:
    spec = load_scenario(ROOT / "config" / "scenarios" / filename, total_steps=288)
    return run_digital_twin(settings, run_simulation(settings, spec))


def test_fit_is_required(settings: Settings, normal_twin: pd.DataFrame) -> None:
    unfitted = HybridDetector(settings.detection, settings.random_seed)

    with pytest.raises(RuntimeError, match="fit"):
        unfitted.detect(normal_twin)


def test_clean_baseline_has_low_persistent_false_detection_rate(
    detector: HybridDetector, normal_twin: pd.DataFrame
) -> None:
    detected = detector.detect(normal_twin)

    assert detected["detected"].mean() < 0.02


def test_flagship_attack_is_detected_and_diagnosed(
    settings: Settings, detector: HybridDetector
) -> None:
    frame = detector.detect(_scenario_frame(settings, "pv-false-data-injection.yaml"))
    evaluation = evaluate_detection(frame)
    events = aggregate_events(frame)

    assert evaluation.precision > 0.95
    assert evaluation.recall > 0.95
    assert evaluation.f1 > 0.95
    assert evaluation.detection_delay_steps is not None
    assert evaluation.detection_delay_steps <= 2
    assert len(events) == 1
    assert events[0].likely_event == "pv_sensor_integrity_event"
    assert events[0].affected_component == "pv_sensor"
    assert "pv_residual_kw" in events[0].evidence


def test_command_attack_identifies_command_path(
    settings: Settings, detector: HybridDetector
) -> None:
    frame = detector.detect(_scenario_frame(settings, "battery-actuator-manipulation.yaml"))
    events = aggregate_events(frame)

    assert events
    assert events[0].likely_event == "battery_command_integrity_event"
    assert events[0].affected_component == "battery_command_path"


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
def test_every_catalog_scenario_produces_an_event(
    settings: Settings, detector: HybridDetector, filename: str
) -> None:
    frame = detector.detect(_scenario_frame(settings, filename))

    assert evaluate_detection(frame).event_detected
    assert aggregate_events(frame)


def test_event_json_is_serializable(
    settings: Settings, detector: HybridDetector, tmp_path: Path
) -> None:
    frame = detector.detect(_scenario_frame(settings, "pv-false-data-injection.yaml"))
    output = write_events(aggregate_events(frame), tmp_path / "events.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload[0]["affected_component"] == "pv_sensor"
    assert payload[0]["severity"] in {"high", "critical"}
