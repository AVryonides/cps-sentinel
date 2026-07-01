"""Interactive risk and response report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from cps_sentinel.config import BatteryConfig
from cps_sentinel.plot_style import apply_report_layout, lift_subplot_titles
from cps_sentinel.risk.assessment import AlertRecord


def build_risk_figure(
    frame: pd.DataFrame, alerts: list[AlertRecord], battery: BatteryConfig
) -> go.Figure:
    """Build physical-state, consequence, confidence, and risk panels."""
    figure = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=(
            "Battery state and configured safety envelope",
            "Physical power-flow consequence",
            "Detection confidence",
            "Event risk score (0-100)",
        ),
    )
    lift_subplot_titles(figure)
    figure.add_trace(
        go.Scatter(x=frame["timestamp"], y=frame["battery_soc"], name="Observed SOC"),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["expected_battery_soc"],
            name="Twin SOC",
            line={"dash": "dash"},
        ),
        row=1,
        col=1,
    )
    figure.add_hline(y=battery.minimum_soc, line_dash="dot", line_color="#C53030", row=1, col=1)
    figure.add_hline(y=battery.maximum_soc, line_dash="dot", line_color="#C53030", row=1, col=1)
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["grid_power_residual_kw"],
            name="Grid residual",
            line={"color": "#C53030"},
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["battery_command_residual_kw"],
            name="Command deviation",
            line={"color": "#805AD5"},
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["confidence"],
            name="Confidence",
            fill="tozeroy",
            line={"color": "#1769AA"},
        ),
        row=3,
        col=1,
    )
    risk_series = pd.Series(0.0, index=frame.index)
    timestamps = pd.to_datetime(frame["timestamp"], utc=True)
    for alert in alerts:
        active = (timestamps >= pd.to_datetime(alert.start_time, utc=True)) & (
            timestamps <= pd.to_datetime(alert.end_time, utc=True)
        )
        risk_series.loc[active] = alert.risk_score
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=risk_series,
            name="Risk score",
            fill="tozeroy",
            line={"color": "#E53E3E", "shape": "hv"},
        ),
        row=4,
        col=1,
    )
    figure.update_yaxes(title_text="SOC", range=[0, 1], row=1, col=1)
    figure.update_yaxes(title_text="Residual (kW)", row=2, col=1)
    figure.update_yaxes(title_text="Confidence", range=[0, 1.05], row=3, col=1)
    figure.update_yaxes(title_text="Risk", range=[0, 105], row=4, col=1)
    apply_report_layout(
        figure,
        title="CPS Sentinel - risk-ranked decision support",
        height=1050,
    )
    return figure


def write_risk_plot(
    frame: pd.DataFrame,
    alerts: list[AlertRecord],
    battery: BatteryConfig,
    path: str | Path,
) -> Path:
    """Write a self-contained interactive risk report."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    build_risk_figure(frame, alerts, battery).write_html(output, include_plotlyjs=True)
    return output
