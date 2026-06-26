import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from nicegui.testing import user_simulation

from cps_sentinel.config import load_settings
from cps_sentinel.dashboard import (
    HealthDashboardResult,
    SwatDashboardResult,
    build_consequence_figure,
    build_detection_figure,
    build_health_dashboard_figure,
    build_sensor_figure,
    build_swat_dashboard_figure,
    load_health_dashboard_result,
    load_swat_dashboard_result,
    plain_language_summary,
    run_dashboard_scenario,
    scenario_catalog,
)
from cps_sentinel.health import analyze_battery_health

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "default.yaml"
APP = ROOT / "app" / "nicegui_app.py"

SPEC = importlib.util.spec_from_file_location("cps_sentinel_nicegui_app", APP)
assert SPEC is not None and SPEC.loader is not None
APP_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP_MODULE)
build_page = APP_MODULE.build_page


@pytest.fixture
def flagship_result():
    settings = load_settings(CONFIG)
    catalog = scenario_catalog(ROOT, settings)
    return run_dashboard_scenario(str(CONFIG), str(catalog[next(iter(catalog))]))


def test_dashboard_analysis_explains_flagship_for_non_specialists(flagship_result) -> None:
    title, explanation = plain_language_summary(flagship_result)

    assert title == "The PV sensor became unreliable"
    assert "controller" in explanation
    assert "digital twin" in explanation
    assert flagship_result.primary_alert is not None


def test_explanatory_figures_mark_event_window(flagship_result) -> None:
    settings = load_settings(CONFIG)
    figures = (
        build_sensor_figure(flagship_result),
        build_consequence_figure(flagship_result, settings),
        build_detection_figure(flagship_result),
    )

    assert all(figure.layout.paper_bgcolor == "#101720" for figure in figures)
    assert all(figure.layout.shapes for figure in figures)
    assert all(figure.layout.margin.t >= 98 for figure in figures)
    assert all(figure.layout.margin.b >= 112 for figure in figures)
    assert all(figure.layout.legend.y <= -0.16 for figure in figures)
    assert figures[0].layout.title.text == "Did the sensor tell the truth?"


def test_external_tracks_report_not_ready_without_generated_results(tmp_path: Path) -> None:
    settings = load_settings(CONFIG)

    health = load_health_dashboard_result(tmp_path / "missing-health.csv")
    swat = load_swat_dashboard_result(tmp_path / "missing-swat.csv", settings)

    assert health.status == "not_ready"
    assert swat.status == "not_ready"
    assert health.result is None
    assert swat.result is None


def test_health_dashboard_loads_processed_boundary_and_builds_dark_figure(tmp_path: Path) -> None:
    settings = load_settings(CONFIG)
    raw = pd.DataFrame(
        {
            "battery_id": ["BTEST"] * 40,
            "cycle_index": np.arange(1, 41),
            "capacity_ah": np.linspace(1.95, 1.35, 40),
        }
    )
    processed = analyze_battery_health(raw, settings.health)
    path = tmp_path / "health.csv"
    processed.to_csv(path, index=False)

    state = load_health_dashboard_result(path)

    assert state.status == "ready"
    assert isinstance(state.result, HealthDashboardResult)
    figure = build_health_dashboard_figure(state.result, settings)
    assert figure.layout.paper_bgcolor == "#101720"
    assert figure.layout.margin.t == 130
    assert state.result.alerts[0].health_status == "critical"


def test_swat_dashboard_loads_derived_result_without_raw_data(tmp_path: Path) -> None:
    settings = load_settings(CONFIG)
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-01-01", periods=12, freq="s"),
            "is_attack": [False] * 5 + [True] * 4 + [False] * 3,
            "LIT101": np.linspace(500, 620, 12),
            "FIT101": np.linspace(2.5, 0.8, 12),
            "anomaly_score": [0.5] * 5 + [2.0] * 4 + [0.4] * 3,
            "anomaly_threshold": [1.0] * 12,
            "raw_anomaly": [False] * 5 + [True] * 4 + [False] * 3,
            "persistence_votes": [0] * 5 + [3] * 4 + [0] * 3,
            "detected": [False] * 5 + [True] * 4 + [False] * 3,
            "top_contributors": [""] * 5 + ["LIT101, FIT101"] * 4 + [""] * 3,
        }
    )
    path = tmp_path / "swat.csv"
    frame.to_csv(path, index=False)

    state = load_swat_dashboard_result(path, settings)

    assert state.status == "ready"
    assert isinstance(state.result, SwatDashboardResult)
    figure = build_swat_dashboard_figure(state.result)
    assert figure.layout.paper_bgcolor == "#101720"
    assert figure.layout.margin.t == 145
    assert state.result.evaluation.event_recall == 1.0
    assert state.result.events[0].top_affected_tags == ("FIT101", "LIT101")


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore:coroutine 'Outbox.loop' was never awaited:RuntimeWarning")
@pytest.mark.filterwarnings(
    "ignore:coroutine 'Drawer.__init__.<locals>._request_value' was never awaited:RuntimeWarning"
)
async def test_nicegui_page_exposes_complete_explanatory_story() -> None:
    async with user_simulation(build_page) as user:
        await user.open("/")
        await user.should_see("CPS Sentinel")
        await user.should_see("A dashboard for explaining CPS incidents")
        await user.should_see("What you are looking at")
        await user.should_see("What this means operationally")
        await user.should_see("Risk score")
        await user.should_see("What happened?")
        await user.should_see("Did the sensor tell the truth?")
        await user.should_see("What changed in the nanogrid?")
        await user.should_see("Why was an alert raised?")
        await user.should_see("What should happen next?")
        await user.should_see("Terms used on this page")
        await user.should_not_see("PHASE 10")
        await user.should_see(marker="mobile-menu")
        await user.should_see(marker="scenario-select")
        await user.should_see(marker="mode-nanogrid")
        await user.should_see(marker="mode-health")
        await user.should_see(marker="mode-swat")
        user.find("Battery health").click()
        await user.should_see("Battery degradation")
        user.find("SWaT security").click()
        await user.should_see("Industrial")
        await user.should_not_see("🛡️")
