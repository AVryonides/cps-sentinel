"""Interactive visualization of hybrid detection and ground-truth evaluation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_detection_figure(frame: pd.DataFrame) -> go.Figure:
    """Build residual, detector-layer, confidence, and timeline panels."""
    figure = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=(
            "Digital-twin residual evidence",
            "Physics and statistical detector layers",
            "Hybrid confidence and severity",
            "Detection versus evaluation-only ground truth",
        ),
    )
    for column, name, color in (
        ("pv_residual_kw", "PV residual", "#D69E2E"),
        ("grid_power_residual_kw", "Grid residual", "#C53030"),
        ("battery_power_residual_kw", "Battery residual", "#2F855A"),
    ):
        figure.add_trace(
            go.Scatter(x=frame["timestamp"], y=frame[column], name=name, line={"color": color}),
            row=1,
            col=1,
        )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["physics_score"],
            name="Physics score",
            line={"color": "#1769AA"},
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["ml_anomaly_percentile"],
            name="ML percentile",
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
            line={"color": "#C53030"},
        ),
        row=3,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["scenario_active"].astype(int),
            name="Ground truth",
            line={"color": "#718096", "shape": "hv"},
        ),
        row=4,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["detected"].astype(int),
            name="Detected",
            line={"color": "#E53E3E", "shape": "hv"},
        ),
        row=4,
        col=1,
    )
    figure.add_hline(y=1, line_dash="dot", line_color="#1769AA", row=2, col=1)
    figure.update_yaxes(title_text="Residual (kW)", row=1, col=1)
    figure.update_yaxes(title_text="Layer score", row=2, col=1)
    figure.update_yaxes(title_text="Confidence", range=[0, 1.05], row=3, col=1)
    figure.update_yaxes(title_text="Active", range=[-0.1, 1.1], row=4, col=1)
    figure.update_layout(
        title="CPS Sentinel - Phase 4 hybrid detection",
        template="plotly_white",
        height=1050,
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.04},
    )
    return figure


def write_detection_plot(frame: pd.DataFrame, path: str | Path) -> Path:
    """Write a self-contained interactive detection report."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    build_detection_figure(frame).write_html(output, include_plotlyjs=True)
    return output
