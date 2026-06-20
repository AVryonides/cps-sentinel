"""Interactive NASA battery health and RUL report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from cps_sentinel.config import HealthConfig


def build_health_figure(frame: pd.DataFrame, config: HealthConfig) -> go.Figure:
    """Build capacity, SOH, and RUL panels for all batteries."""
    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.09,
        subplot_titles=(
            "Measured discharge capacity",
            "State of health",
            "Causal remaining-useful-life estimate",
        ),
    )
    colors = ("#42C6D7", "#E5A93D", "#6E9CF5", "#E66565")
    for (battery_id, rows), color in zip(
        frame.groupby("battery_id", sort=True), colors, strict=False
    ):
        figure.add_trace(
            go.Scatter(
                x=rows["cycle_index"],
                y=rows["capacity_ah"],
                name=str(battery_id),
                legendgroup=str(battery_id),
                line={"color": color},
            ),
            row=1,
            col=1,
        )
        figure.add_trace(
            go.Scatter(
                x=rows["cycle_index"],
                y=rows["state_of_health"] * 100,
                name=f"{battery_id} SOH",
                legendgroup=str(battery_id),
                showlegend=False,
                line={"color": color},
            ),
            row=2,
            col=1,
        )
        figure.add_trace(
            go.Scatter(
                x=rows["cycle_index"],
                y=rows["estimated_rul_cycles"],
                name=f"{battery_id} estimated RUL",
                legendgroup=str(battery_id),
                showlegend=False,
                line={"color": color},
            ),
            row=3,
            col=1,
        )
        figure.add_trace(
            go.Scatter(
                x=rows["cycle_index"],
                y=rows["actual_rul_cycles"],
                name=f"{battery_id} observed RUL",
                legendgroup=str(battery_id),
                showlegend=False,
                line={"color": color, "dash": "dot"},
            ),
            row=3,
            col=1,
        )
    figure.add_hline(
        y=config.end_of_life_capacity_ah,
        line_dash="dash",
        line_color="#E66565",
        annotation_text="NASA EOL: 1.4 Ah",
        row=1,
        col=1,
    )
    figure.add_hline(
        y=config.critical_soh_fraction * 100,
        line_dash="dash",
        line_color="#E66565",
        annotation_text="Critical SOH",
        row=2,
        col=1,
    )
    figure.update_yaxes(title_text="Capacity (Ah)", row=1, col=1)
    figure.update_yaxes(title_text="SOH (%)", row=2, col=1)
    figure.update_yaxes(title_text="Cycles", row=3, col=1)
    figure.update_xaxes(title_text="Discharge cycle", row=3, col=1)
    figure.update_layout(
        title="CPS Sentinel - Phase 7 NASA battery health validation",
        template="plotly_white",
        height=1050,
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.04},
    )
    return figure


def write_health_plot(frame: pd.DataFrame, config: HealthConfig, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    build_health_figure(frame, config).write_html(output, include_plotlyjs=True)
    return output
