"""Framework-neutral analysis and explanatory figures for the web dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from cps_sentinel.config import Settings, load_settings
from cps_sentinel.detection import (
    DetectionEvaluation,
    HybridDetector,
    aggregate_events,
    evaluate_detection,
)
from cps_sentinel.health import (
    HealthAlert,
    RulEvaluation,
    build_health_alerts,
    evaluate_rul,
)
from cps_sentinel.health.plotting import build_health_figure
from cps_sentinel.risk import AlertRecord, assess_events
from cps_sentinel.scenarios import ScenarioSpec, load_scenario
from cps_sentinel.simulation import run_simulation
from cps_sentinel.swat import (
    SwatEvaluation,
    SwatEvent,
    aggregate_swat_events,
    evaluate_swat_detection,
)
from cps_sentinel.swat.plotting import build_swat_figure
from cps_sentinel.twin import run_digital_twin

PLOT_BACKGROUND = "#101720"
GRID_COLOR = "#263241"
TEXT_COLOR = "#DCE4EC"
MUTED_COLOR = "#8E9BA8"
CYAN = "#42C6D7"
AMBER = "#E5A93D"
RED = "#E66565"
BLUE = "#6E9CF5"


@dataclass(frozen=True)
class DashboardResult:
    scenario: ScenarioSpec
    frame: pd.DataFrame
    evaluation: DetectionEvaluation
    alerts: tuple[AlertRecord, ...]

    @property
    def primary_alert(self) -> AlertRecord | None:
        return self.alerts[0] if self.alerts else None


@dataclass(frozen=True)
class HealthDashboardResult:
    frame: pd.DataFrame
    evaluation: RulEvaluation
    alerts: tuple[HealthAlert, ...]


@dataclass(frozen=True)
class SwatDashboardResult:
    frame: pd.DataFrame
    evaluation: SwatEvaluation
    events: tuple[SwatEvent, ...]


@dataclass(frozen=True)
class ExternalTrackState:
    status: str
    message: str
    result: HealthDashboardResult | SwatDashboardResult | None = None


def scenario_catalog(root: Path, settings: Settings) -> dict[str, Path]:
    """Return display names and paths with the flagship scenario first."""
    directory = root / "config" / "scenarios"
    total_steps = settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
    paths = sorted(directory.glob("*.yaml"))
    flagship = directory / "pv-false-data-injection.yaml"
    ordered = [flagship, *(path for path in paths if path != flagship)]
    return {load_scenario(path, total_steps).name: path for path in ordered}


@lru_cache(maxsize=16)
def run_dashboard_scenario(config_path: str, scenario_path: str) -> DashboardResult:
    """Run the production simulation-to-alert pipeline for one dashboard scenario."""
    settings = load_settings(config_path)
    total_steps = settings.simulation.duration_hours * 60 // settings.simulation.timestep_minutes
    scenario = load_scenario(scenario_path, total_steps)
    normal = run_digital_twin(settings, run_simulation(settings))
    observed = run_digital_twin(settings, run_simulation(settings, scenario))
    detector = HybridDetector(settings.detection, settings.random_seed).fit(normal)
    frame = detector.detect(observed)
    events = aggregate_events(frame)
    return DashboardResult(
        scenario=scenario,
        frame=frame,
        evaluation=evaluate_detection(frame),
        alerts=tuple(assess_events(frame, events, settings)),
    )


@lru_cache(maxsize=4)
def load_health_dashboard_result(path: str | Path) -> ExternalTrackState:
    """Load generated NASA health results without reading or exposing raw source data."""
    source = Path(path)
    if not source.is_file():
        return ExternalTrackState(
            status="not_ready",
            message="Run the Phase 7 health command to generate the local dashboard result.",
        )
    try:
        frame = pd.read_csv(source)
        required = {
            "battery_id",
            "cycle_index",
            "capacity_ah",
            "state_of_health",
            "health_status",
            "estimated_rul_cycles",
            "actual_rul_cycles",
        }
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")
        result = HealthDashboardResult(
            frame=frame,
            evaluation=evaluate_rul(frame),
            alerts=tuple(build_health_alerts(frame)),
        )
    except (OSError, ValueError, pd.errors.ParserError) as error:
        return ExternalTrackState(
            status="error", message=f"Health result could not be loaded: {error}"
        )
    return ExternalTrackState(
        status="ready",
        message="NASA battery validation result loaded from the local processed-data boundary.",
        result=result,
    )


@lru_cache(maxsize=4)
def load_swat_dashboard_result(path: str | Path, settings: Settings) -> ExternalTrackState:
    """Load generated SWaT results while keeping restricted historian files outside the UI."""
    source = Path(path)
    if not source.is_file():
        return ExternalTrackState(
            status="not_ready",
            message="Run the Phase 8 SWaT command after receiving authorized iTrust files.",
        )
    try:
        frame = pd.read_csv(source)
        required = {
            "timestamp",
            "is_attack",
            "anomaly_score",
            "anomaly_threshold",
            "detected",
            "top_contributors",
        }
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"missing columns: {sorted(missing)}")
        result = SwatDashboardResult(
            frame=frame,
            evaluation=evaluate_swat_detection(frame),
            events=tuple(aggregate_swat_events(frame, settings.swat)),
        )
    except (OSError, ValueError, pd.errors.ParserError) as error:
        return ExternalTrackState(
            status="error", message=f"SWaT result could not be loaded: {error}"
        )
    return ExternalTrackState(
        status="ready",
        message=(
            "SWaT validation result loaded; restricted raw historian data remains outside the UI."
        ),
        result=result,
    )


def build_health_dashboard_figure(result: HealthDashboardResult, settings: Settings) -> go.Figure:
    """Restyle the Phase 7 report for the unified dark operations interface."""
    figure = build_health_figure(result.frame, settings.health)
    return _style_external_figure(figure, "Battery capacity, health, and remaining life")


def build_swat_dashboard_figure(result: SwatDashboardResult) -> go.Figure:
    """Restyle the Phase 8 report for the unified dark operations interface."""
    figure = build_swat_figure(result.frame, list(result.events), result.evaluation)
    return _style_external_figure(
        figure,
        "Industrial process anomaly evidence",
        top_margin=155,
    )


def plain_language_summary(result: DashboardResult) -> tuple[str, str]:
    """Explain the diagnosis and consequence without requiring CPS expertise."""
    alert = result.primary_alert
    if alert is None:
        return (
            "No persistent anomaly was found",
            "The observed system stayed close to the behavior predicted by the digital twin.",
        )
    summaries = {
        "pv_sensor_integrity_event": (
            "The PV sensor became unreliable",
            "The controller received a solar-generation value that disagreed with both the "
            "physical system and the independent digital twin. This changed battery and grid "
            "decisions during the highlighted interval.",
        ),
        "load_sensor_integrity_event": (
            "The load sensor became unreliable",
            "Reported demand separated from the independent estimate, so controller decisions "
            "were based on a misleading view of the nanogrid.",
        ),
        "battery_command_integrity_event": (
            "The battery received an unexpected command",
            "The command delivered to the battery differed from the controller request, changing "
            "physical power flow and potentially moving state of charge toward a limit.",
        ),
        "battery_state_divergence": (
            "Battery behavior no longer matched its model",
            "Observed battery state drifted away from the physics-based estimate, which may "
            "indicate degradation, a sensor problem, or an unmodelled operating change.",
        ),
        "power_flow_anomaly": (
            "Power moved differently than expected",
            "Battery or grid exchange separated from the digital-twin prediction for long enough "
            "to be treated as a persistent event.",
        ),
    }
    return summaries.get(
        alert.likely_event,
        (
            "The system entered an unusual operating state",
            "Multiple measurements differed from the normal physical relationship learned from "
            "clean operation. An operator should review the evidence before changing control.",
        ),
    )


def build_sensor_figure(result: DashboardResult) -> go.Figure:
    """Compare physical, reported, and independently expected sensor values."""
    frame = result.frame
    timestamps = frame["timestamp"].astype(str).tolist()
    figure = go.Figure()
    for column, name, color, width, dash in (
        ("true_pv_kw", "Physical PV", CYAN, 2.2, None),
        ("pv_kw", "Value reported to controller", AMBER, 2.6, None),
        ("expected_pv_kw", "Digital-twin expectation", BLUE, 2.0, "dash"),
    ):
        figure.add_trace(
            go.Scatter(
                x=timestamps,
                y=frame[column],
                name=name,
                mode="lines",
                line={"color": color, "width": width, "dash": dash},
                hovertemplate=f"{name}: %{{y:.2f}} kW<extra></extra>",
            )
        )
    _add_event_window(figure, result)
    return _finish_figure(
        figure,
        title="Did the sensor tell the truth?",
        y_title="PV power (kW)",
        height=430,
    )


def build_consequence_figure(result: DashboardResult, settings: Settings) -> go.Figure:
    """Show how the event changed grid exchange and battery state."""
    frame = result.frame
    timestamps = frame["timestamp"].astype(str).tolist()
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.13,
        subplot_titles=("Grid exchange", "Battery state of charge"),
    )
    for column, name, color, dash in (
        ("grid_power_kw", "Observed grid power", AMBER, None),
        ("expected_grid_power_kw", "Expected grid power", BLUE, "dash"),
    ):
        figure.add_trace(
            go.Scatter(
                x=timestamps,
                y=frame[column],
                name=name,
                line={"color": color, "width": 2.2, "dash": dash},
            ),
            row=1,
            col=1,
        )
    for column, name, color, dash in (
        ("battery_soc", "Observed battery SOC", CYAN, None),
        ("expected_battery_soc", "Expected battery SOC", BLUE, "dash"),
    ):
        figure.add_trace(
            go.Scatter(
                x=timestamps,
                y=frame[column],
                name=name,
                line={"color": color, "width": 2.2, "dash": dash},
            ),
            row=2,
            col=1,
        )
    battery = settings.simulation.battery
    figure.add_hline(
        y=battery.minimum_soc,
        line_dash="dot",
        line_color=RED,
        annotation_text="Minimum safe SOC",
        row=2,
        col=1,
    )
    figure.add_hline(
        y=battery.maximum_soc,
        line_dash="dot",
        line_color=RED,
        annotation_text="Maximum safe SOC",
        row=2,
        col=1,
    )
    _add_event_window(figure, result, rows=(1, 2))
    figure.update_yaxes(title_text="Power (kW)", row=1, col=1)
    figure.update_yaxes(title_text="SOC", range=[0, 1], row=2, col=1)
    return _finish_figure(
        figure,
        title="What changed in the physical system?",
        height=610,
    )


def build_detection_figure(result: DashboardResult) -> go.Figure:
    """Explain how residual evidence became a persistent detection."""
    frame = result.frame
    timestamps = frame["timestamp"].astype(str).tolist()
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.15,
        subplot_titles=("Difference between observation and twin", "Detector confidence"),
    )
    for column, name, color in (
        ("pv_residual_kw", "PV difference", AMBER),
        ("grid_power_residual_kw", "Grid difference", RED),
        ("battery_power_residual_kw", "Battery difference", CYAN),
    ):
        figure.add_trace(
            go.Scatter(
                x=timestamps,
                y=frame[column],
                name=name,
                line={"color": color, "width": 2},
            ),
            row=1,
            col=1,
        )
    figure.add_trace(
        go.Scatter(
            x=timestamps,
            y=frame["confidence"] * 100,
            name="Detection confidence",
            fill="tozeroy",
            line={"color": BLUE, "width": 2},
        ),
        row=2,
        col=1,
    )
    figure.add_hline(
        y=70,
        line_dash="dot",
        line_color=MUTED_COLOR,
        annotation_text="High-confidence reference",
        row=2,
        col=1,
    )
    _add_event_window(figure, result, rows=(1, 2))
    figure.update_yaxes(title_text="Difference (kW)", row=1, col=1)
    figure.update_yaxes(title_text="Confidence (%)", range=[0, 105], row=2, col=1)
    return _finish_figure(
        figure,
        title="Why did CPS Sentinel raise an alert?",
        height=610,
    )


def _add_event_window(
    figure: go.Figure,
    result: DashboardResult,
    rows: tuple[int, ...] | None = None,
) -> None:
    active = result.frame.loc[result.frame["scenario_active"].astype(bool), "timestamp"]
    if active.empty:
        return
    kwargs = {
        "x0": str(active.iloc[0]),
        "x1": str(active.iloc[-1]),
        "fillcolor": RED,
        "opacity": 0.10,
        "line_width": 0,
        "annotation_text": "Event active",
        "annotation_position": "top left",
    }
    if rows is None:
        figure.add_vrect(**kwargs)
        return
    for row in rows:
        figure.add_vrect(**kwargs, row=row, col=1)


def _finish_figure(
    figure: go.Figure,
    *,
    title: str,
    height: int,
    y_title: str | None = None,
) -> go.Figure:
    figure.update_layout(
        title={"text": title, "font": {"size": 18, "color": TEXT_COLOR}},
        template="plotly_dark",
        paper_bgcolor=PLOT_BACKGROUND,
        plot_bgcolor=PLOT_BACKGROUND,
        font={"family": "Inter, system-ui, sans-serif", "color": TEXT_COLOR},
        height=height,
        hovermode="x unified",
        margin={"l": 58, "r": 24, "t": 72, "b": 48},
        legend={"orientation": "h", "y": 1.07, "x": 0},
    )
    figure.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    figure.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    if y_title:
        figure.update_yaxes(title_text=y_title)
    return figure


def _style_external_figure(figure: go.Figure, title: str, top_margin: int = 72) -> go.Figure:
    figure.update_layout(
        title={"text": title, "font": {"size": 18, "color": TEXT_COLOR}},
        template="plotly_dark",
        paper_bgcolor=PLOT_BACKGROUND,
        plot_bgcolor=PLOT_BACKGROUND,
        font={"family": "Inter, system-ui, sans-serif", "color": TEXT_COLOR},
        hovermode="x unified",
        margin={"l": 58, "r": 24, "t": top_margin, "b": 48},
    )
    figure.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    figure.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    return figure
