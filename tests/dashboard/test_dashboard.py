from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_renders_complete_flagship_story() -> None:
    app = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=30)

    app.run()

    assert not app.exception
    assert len(app.metric) >= 14
    assert {tab.label for tab in app.tabs} == {
        "System Overview",
        "Digital Twin",
        "Detection Engine",
        "Alert & Response",
    }
    assert any("Recommended operator response" in item.value for item in app.markdown)


def test_dashboard_scenario_selector_is_populated() -> None:
    app = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=30)

    app.run()

    assert len(app.selectbox) == 1
    assert len(app.selectbox[0].options) == 8
