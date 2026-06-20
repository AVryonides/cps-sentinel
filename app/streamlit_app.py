"""Interactive Phase 6 showcase dashboard for CPS Sentinel."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from cps_sentinel.config import Settings, load_settings
from cps_sentinel.detection import (
    DetectionEvaluation,
    HybridDetector,
    aggregate_events,
    evaluate_detection,
)
from cps_sentinel.risk import AlertRecord, assess_events
from cps_sentinel.risk.plotting import build_risk_figure
from cps_sentinel.scenarios import ScenarioSpec, load_scenario
from cps_sentinel.simulation import run_simulation
from cps_sentinel.twin import run_digital_twin

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "default.yaml"
SCENARIO_DIR = ROOT / "config" / "scenarios"
SETTINGS = load_settings(CONFIG_PATH)


@st.cache_data(show_spinner=False)
def run_dashboard_scenario(
    scenario_path: str,
) -> tuple[ScenarioSpec, pd.DataFrame, DetectionEvaluation, list[AlertRecord]]:
    """Execute the deterministic simulation-to-alert pipeline for one scenario."""
    settings = load_settings(CONFIG_PATH)
    total_steps = settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
    scenario = load_scenario(scenario_path, total_steps)
    normal_twin = run_digital_twin(settings, run_simulation(settings))
    scenario_twin = run_digital_twin(settings, run_simulation(settings, scenario))
    detector = HybridDetector(settings.detection, settings.random_seed).fit(normal_twin)
    frame = detector.detect(scenario_twin)
    evaluation = evaluate_detection(frame)
    alerts = assess_events(frame, aggregate_events(frame), settings)
    return scenario, frame, evaluation, alerts


def build_system_figure(frame: pd.DataFrame, settings: Settings) -> go.Figure:
    """Show observed, reported, and twin-estimated physical behavior."""
    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.09,
        subplot_titles=(
            "PV sensor and independent twin estimate",
            "Battery state of charge",
            "Grid exchange",
        ),
    )
    for column, name, color, dash in (
        ("true_pv_kw", "Physical PV", "#12B886", None),
        ("pv_kw", "Reported PV", "#F59F00", None),
        ("expected_pv_kw", "Twin PV", "#4C6EF5", "dash"),
    ):
        figure.add_trace(
            go.Scatter(
                x=frame["timestamp"],
                y=frame[column],
                name=name,
                line={"color": color, "dash": dash},
            ),
            row=1,
            col=1,
        )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["battery_soc"],
            name="Observed SOC",
            line={"color": "#12B886"},
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["expected_battery_soc"],
            name="Twin SOC",
            line={"color": "#4C6EF5", "dash": "dash"},
        ),
        row=2,
        col=1,
    )
    battery = settings.simulation.battery
    figure.add_hline(y=battery.minimum_soc, line_dash="dot", line_color="#FA5252", row=2, col=1)
    figure.add_hline(y=battery.maximum_soc, line_dash="dot", line_color="#FA5252", row=2, col=1)
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["grid_power_kw"],
            name="Observed grid",
            line={"color": "#12B886"},
        ),
        row=3,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["expected_grid_power_kw"],
            name="Twin grid",
            line={"color": "#4C6EF5", "dash": "dash"},
        ),
        row=3,
        col=1,
    )
    figure.update_yaxes(title_text="Power (kW)", row=1, col=1)
    figure.update_yaxes(title_text="SOC", range=[0, 1], row=2, col=1)
    figure.update_yaxes(title_text="Power (kW)", row=3, col=1)
    return _finish_figure(figure, 820)


def build_detection_figure(frame: pd.DataFrame) -> go.Figure:
    """Expose physics, statistical, and temporal detection evidence."""
    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.10,
        subplot_titles=("Residual evidence", "Hybrid detector layers", "Detection timeline"),
    )
    for column, name, color in (
        ("pv_residual_kw", "PV residual", "#F59F00"),
        ("grid_power_residual_kw", "Grid residual", "#FA5252"),
        ("battery_power_residual_kw", "Battery residual", "#12B886"),
    ):
        figure.add_trace(
            go.Scatter(x=frame["timestamp"], y=frame[column], name=name, line={"color": color}),
            row=1,
            col=1,
        )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["confidence"],
            name="Hybrid confidence",
            fill="tozeroy",
            line={"color": "#4C6EF5"},
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["ml_anomaly_percentile"],
            name="ML percentile",
            line={"color": "#845EF7", "dash": "dot"},
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["scenario_active"].astype(int),
            name="Evaluation label",
            line={"color": "#ADB5BD", "shape": "hv"},
        ),
        row=3,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["detected"].astype(int),
            name="Detected",
            line={"color": "#FA5252", "shape": "hv"},
        ),
        row=3,
        col=1,
    )
    figure.update_yaxes(title_text="Residual (kW)", row=1, col=1)
    figure.update_yaxes(title_text="Score", range=[0, 1.05], row=2, col=1)
    figure.update_yaxes(title_text="Active", range=[-0.1, 1.1], row=3, col=1)
    return _finish_figure(figure, 800)


def _finish_figure(figure: go.Figure, height: int) -> go.Figure:
    figure.update_layout(
        template="plotly_white",
        height=height,
        hovermode="x unified",
        margin={"l": 20, "r": 20, "t": 70, "b": 20},
        legend={"orientation": "h", "y": 1.08},
    )
    return figure


def _scenario_catalog() -> dict[str, Path]:
    total_steps = SETTINGS.simulation.duration_hours * 60 // SETTINGS.simulation.timestep_minutes
    paths = sorted(SCENARIO_DIR.glob("*.yaml"))
    flagship = SCENARIO_DIR / "pv-false-data-injection.yaml"
    ordered_paths = [flagship, *(path for path in paths if path != flagship)]
    return {load_scenario(path, total_steps).name: path for path in ordered_paths}


def _risk_color(level: str) -> str:
    return {
        "critical": "#FA5252",
        "high": "#FD7E14",
        "medium": "#F59F00",
        "low": "#12B886",
    }.get(level, "#4C6EF5")


st.set_page_config(
    page_title="CPS Sentinel | Mission Control",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    """
    <style>
    .stApp {background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 36%);}
    [data-testid="stSidebar"] {background: #0B1220;}
    [data-testid="stSidebar"] * {color: #E9ECEF;}
    .sentinel-hero {padding: 1.35rem 1.55rem; border-radius: 18px; color: white;
        background: linear-gradient(120deg, #0B1220 0%, #163B65 62%, #146C5A 100%);
        box-shadow: 0 12px 30px rgba(11,18,32,.18); margin-bottom: 1rem;}
    .sentinel-kicker {font-size: .76rem; letter-spacing: .16em; text-transform: uppercase;
        color: #74C0FC; font-weight: 700;}
    .sentinel-hero h1 {font-size: 2.35rem; line-height: 1.05; margin: .35rem 0 .55rem;}
    .sentinel-hero p {max-width: 790px; color: #DDE7F0; margin: 0;}
    .alert-card {border-left: 6px solid var(--risk-color); border-radius: 14px;
        background: white; padding: 1.2rem 1.3rem; box-shadow: 0 5px 20px rgba(15,23,42,.08);}
    .alert-label {font-size: .76rem; letter-spacing: .1em; text-transform: uppercase;
        color: #64748B; font-weight: 700;}
    .alert-title {font-size: 1.35rem; font-weight: 750; color: #0F172A; margin: .2rem 0;}
    div[data-testid="stMetric"] {background: white; border: 1px solid #E9ECEF;
        border-radius: 14px; padding: .85rem 1rem; box-shadow: 0 3px 12px rgba(15,23,42,.04);}
    </style>
    """,
    unsafe_allow_html=True,
)

catalog = _scenario_catalog()
with st.sidebar:
    st.markdown("## 🛡️ CPS Sentinel")
    st.caption("Digital-twin mission control")
    selected_name = st.selectbox("Scenario", options=list(catalog))
    st.markdown("#### Analysis pipeline")
    st.markdown(
        "① Simulate physical plant  \n"
        "② Predict with digital twin  \n"
        "③ Detect and diagnose  \n"
        "④ Rank risk and respond"
    )
    st.divider()
    st.caption("Detection never consumes scenario labels. Labels appear only in evaluation views.")

with st.spinner("Running deterministic CPS analysis…"):
    scenario, frame, evaluation, alerts = run_dashboard_scenario(str(catalog[selected_name]))

primary = alerts[0] if alerts else None
st.markdown(
    """
    <section class="sentinel-hero">
      <div class="sentinel-kicker">Phase 6 · Interactive CPS Demonstrator</div>
      <h1>Mission Control</h1>
      <p>Observe the physical nanogrid, compare it with an independent digital twin, inspect
      hybrid anomaly evidence, and move from detection to an operator-confirmed response.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

metric_columns = st.columns(5)
metric_columns[0].metric("System state", "ALERT" if primary else "NORMAL")
metric_columns[1].metric("Risk", f"{primary.risk_score:.1f} / 100" if primary else "0.0 / 100")
metric_columns[2].metric("Confidence", f"{primary.confidence:.0%}" if primary else "0%")
metric_columns[3].metric("Affected component", primary.affected_component if primary else "None")
delay = evaluation.detection_delay_steps
metric_columns[4].metric("Detection delay", f"{delay} step{'s' if delay != 1 else ''}")

overview_tab, twin_tab, detection_tab, response_tab = st.tabs(
    ["System Overview", "Digital Twin", "Detection Engine", "Alert & Response"]
)

with overview_tab:
    left, right = st.columns([2, 1])
    with left:
        st.subheader(scenario.name)
        scenario_kind = scenario.kind.value.replace("_", " ")
        st.caption(
            f"{scenario.ground_truth_label.title()} scenario · {scenario_kind} "
            f"· target: {scenario.target.value.replace('_', ' ')}"
        )
    with right:
        st.metric("Evaluation F1", f"{evaluation.f1:.3f}")
    st.plotly_chart(build_system_figure(frame, SETTINGS), use_container_width=True)

with twin_tab:
    st.subheader("Independent expected behavior")
    st.caption(
        "The twin predicts from reference profiles and its own state. Observations are introduced "
        "only after prediction to calculate residual evidence."
    )
    residual_columns = st.columns(4)
    residual_columns[0].metric("Peak PV residual", f"{frame['pv_residual_kw'].abs().max():.2f} kW")
    residual_columns[1].metric(
        "Peak grid residual", f"{frame['grid_power_residual_kw'].abs().max():.2f} kW"
    )
    residual_columns[2].metric(
        "Peak SOC residual", f"{frame['battery_soc_residual'].abs().max():.3f}"
    )
    residual_columns[3].metric(
        "Command deviation", f"{frame['battery_command_residual_kw'].abs().max():.2f} kW"
    )
    twin_figure = build_system_figure(frame, SETTINGS)
    twin_figure.update_layout(title="Observed system versus digital twin")
    st.plotly_chart(twin_figure, use_container_width=True)

with detection_tab:
    st.subheader("Explainable hybrid detection")
    st.caption(
        "Physics-threshold evidence and Isolation Forest novelty are temporally correlated before "
        "an event is diagnosed. Ground truth is shown only for retrospective evaluation."
    )
    detection_metrics = st.columns(4)
    detection_metrics[0].metric("Precision", f"{evaluation.precision:.3f}")
    detection_metrics[1].metric("Recall", f"{evaluation.recall:.3f}")
    detection_metrics[2].metric("False-positive rate", f"{evaluation.false_positive_rate:.3f}")
    detection_metrics[3].metric("Detected events", str(len(alerts)))
    st.plotly_chart(build_detection_figure(frame), use_container_width=True)

with response_tab:
    if primary:
        color = _risk_color(primary.risk_level)
        risk_label = escape(primary.risk_level)
        event_label = escape(primary.likely_event.replace("_", " ").title())
        st.markdown(
            f"""
            <div class="alert-card" style="--risk-color:{color}">
              <div class="alert-label">Priority {primary.priority} · {risk_label} risk</div>
              <div class="alert-title">{event_label}</div>
              <div>{escape(primary.physical_impact)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("### Recommended operator response")
        for index, action in enumerate(primary.recommended_actions, start=1):
            st.markdown(f"**{index}.** {action}")
        st.warning(primary.safety_note, icon="⚠️")
        st.plotly_chart(
            build_risk_figure(frame, alerts, SETTINGS.simulation.battery), use_container_width=True
        )
        with st.expander("Risk-score breakdown and evidence"):
            factors = pd.DataFrame(
                {
                    "Factor": ["Confidence", "Physical impact", "Duration", "Safety proximity"],
                    "Normalized value": [
                        primary.confidence_factor,
                        primary.impact_factor,
                        primary.duration_factor,
                        primary.safety_proximity_factor,
                    ],
                    "Configured weight": [
                        SETTINGS.risk.confidence_weight,
                        SETTINGS.risk.impact_weight,
                        SETTINGS.risk.duration_weight,
                        SETTINGS.risk.safety_proximity_weight,
                    ],
                }
            )
            st.dataframe(factors, hide_index=True, use_container_width=True)
            st.caption("Evidence: " + ", ".join(primary.evidence))
    else:
        st.success("No persistent event was detected. No response action is required.")

st.caption(
    "CPS Sentinel is a deterministic research prototype. Recommendations are decision support, "
    "not autonomous or certified safety control."
)
