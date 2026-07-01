from pathlib import Path

import numpy as np
import pandas as pd

from cps_sentinel.config import load_settings
from cps_sentinel.detection import HybridDetector, aggregate_events
from cps_sentinel.detection.plotting import build_detection_figure
from cps_sentinel.health import analyze_battery_health
from cps_sentinel.health.plotting import build_health_figure
from cps_sentinel.risk import assess_events
from cps_sentinel.risk.plotting import build_risk_figure
from cps_sentinel.scenarios import load_scenario
from cps_sentinel.scenarios.plotting import build_scenario_figure
from cps_sentinel.simulation import run_simulation
from cps_sentinel.simulation.plotting import build_simulation_figure
from cps_sentinel.swat import SwatEvaluation, SwatEvent
from cps_sentinel.swat.plotting import build_swat_figure
from cps_sentinel.twin import run_digital_twin
from cps_sentinel.twin.plotting import build_twin_figure

ROOT = Path(__file__).resolve().parents[1]


def test_standalone_reports_reserve_space_for_titles_and_legends() -> None:
    settings = load_settings(ROOT / "config" / "default.yaml")
    normal = run_digital_twin(settings, run_simulation(settings))
    scenario = load_scenario(
        ROOT / "config" / "scenarios" / "pv-false-data-injection.yaml",
        total_steps=288,
    )
    attacked = run_digital_twin(settings, run_simulation(settings, scenario))
    detected = HybridDetector(settings.detection, settings.random_seed).fit(normal).detect(attacked)
    alerts = assess_events(detected, aggregate_events(detected), settings)

    figures = (
        build_simulation_figure(normal, settings.simulation.battery),
        build_twin_figure(normal),
        scenario_figure := build_scenario_figure(attacked),
        build_detection_figure(detected),
        build_risk_figure(detected, alerts, settings.simulation.battery),
        build_health_figure(_health_frame(settings), settings.health),
        build_swat_figure(*_swat_inputs()),
    )

    for figure in figures:
        assert figure.layout.margin.t >= 130
        assert figure.layout.margin.b >= 118
        assert figure.layout.legend.orientation == "h"
        assert figure.layout.legend.y <= -0.16
        assert figure.layout.legend.yanchor == "top"
        assert figure.layout.title.y >= 0.98

    scenario_annotations = [
        annotation
        for annotation in scenario_figure.layout.annotations
        if annotation.text == "PV sensor false-data injection"
    ]
    assert scenario_annotations
    assert all(annotation.xanchor == "center" for annotation in scenario_annotations)


def _health_frame(settings):
    raw = pd.DataFrame(
        {
            "battery_id": ["BTEST"] * 60,
            "cycle_index": np.arange(1, 61),
            "capacity_ah": np.linspace(1.95, 1.30, 60),
        }
    )
    return analyze_battery_health(raw, settings.health)


def _swat_inputs() -> tuple[pd.DataFrame, list[SwatEvent], SwatEvaluation]:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=12, freq="s"),
            "is_attack": [False] * 5 + [True] * 4 + [False] * 3,
            "anomaly_score": [0.5] * 5 + [2.0] * 4 + [0.4] * 3,
            "anomaly_threshold": [1.0] * 12,
            "detected": [False] * 5 + [True] * 4 + [False] * 3,
        }
    )
    event = SwatEvent(
        event_id="SWAT-E001",
        start_index=5,
        end_index=8,
        start_timestamp="2026-01-01T00:00:05Z",
        end_timestamp="2026-01-01T00:00:08Z",
        duration_steps=4,
        detected_points=4,
        peak_anomaly_score=2.0,
        top_affected_tags=("LIT101", "FIT101"),
        overlaps_labeled_attack=True,
        physical_context="Synthetic spacing regression event.",
        recommended_actions=("Review affected tags.",),
    )
    evaluation = SwatEvaluation(
        rows=12,
        attack_rows=4,
        precision=1.0,
        recall=1.0,
        f1=1.0,
        false_positive_rate=0.0,
        ground_truth_events=1,
        detected_attack_events=1,
        event_recall=1.0,
        median_detection_delay_steps=0.0,
    )
    return frame, [event], evaluation
