import importlib.util
from pathlib import Path

import pytest
from nicegui.testing import user_simulation

from cps_sentinel.config import load_settings
from cps_sentinel.dashboard import (
    build_consequence_figure,
    build_detection_figure,
    build_sensor_figure,
    plain_language_summary,
    run_dashboard_scenario,
    scenario_catalog,
)

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
    assert figures[0].layout.title.text == "Did the sensor tell the truth?"


@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore:coroutine 'Outbox.loop' was never awaited:RuntimeWarning")
@pytest.mark.filterwarnings(
    "ignore:coroutine 'Drawer.__init__.<locals>._request_value' was never awaited:RuntimeWarning"
)
async def test_nicegui_page_exposes_complete_explanatory_story() -> None:
    async with user_simulation(build_page) as user:
        await user.open("/")
        await user.should_see("CPS Sentinel")
        await user.should_see("What happened?")
        await user.should_see("Did the sensor tell the truth?")
        await user.should_see("What changed in the nanogrid?")
        await user.should_see("Why was an alert raised?")
        await user.should_see("What should happen next?")
        await user.should_see("Terms used on this page")
        await user.should_see(marker="mobile-menu")
        await user.should_see(marker="scenario-select")
        await user.should_not_see("🛡️")
