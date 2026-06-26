"""Interactive visualization of observed and digital-twin behavior."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from cps_sentinel.plot_style import apply_report_layout, lift_subplot_titles


def build_twin_figure(frame: pd.DataFrame) -> go.Figure:
    """Build synchronized observed-versus-expected and residual panels."""
    figure = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=(
            "PV: observed vs expected",
            "Grid power: observed vs expected",
            "Battery SOC: observed vs expected",
            "Signed residuals",
        ),
    )
    lift_subplot_titles(figure)
    _add_pair(figure, frame, 1, "pv_kw", "expected_pv_kw", "PV")
    _add_pair(figure, frame, 2, "grid_power_kw", "expected_grid_power_kw", "Grid")
    _add_pair(figure, frame, 3, "battery_soc", "expected_battery_soc", "SOC", scale=100)
    for column, name, color in (
        ("pv_residual_kw", "PV residual", "#D69E2E"),
        ("grid_power_residual_kw", "Grid residual", "#C53030"),
        ("battery_power_residual_kw", "Battery residual", "#2F855A"),
    ):
        figure.add_trace(
            go.Scatter(x=frame["timestamp"], y=frame[column], name=name, line={"color": color}),
            row=4,
            col=1,
        )
    figure.add_hline(y=0, line_color="#718096", line_width=1, row=4, col=1)
    figure.update_yaxes(title_text="Power (kW)", row=1, col=1)
    figure.update_yaxes(title_text="Power (kW)", row=2, col=1)
    figure.update_yaxes(title_text="SOC (%)", range=[0, 100], row=3, col=1)
    figure.update_yaxes(title_text="Residual", row=4, col=1)
    apply_report_layout(
        figure,
        title="CPS Sentinel - Phase 2 digital twin",
        height=1000,
    )
    return figure


def write_twin_plot(frame: pd.DataFrame, path: str | Path) -> Path:
    """Write a self-contained interactive digital-twin report."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    build_twin_figure(frame).write_html(output, include_plotlyjs=True)
    return output


def _add_pair(
    figure: go.Figure,
    frame: pd.DataFrame,
    row: int,
    observed_column: str,
    expected_column: str,
    label: str,
    scale: float = 1.0,
) -> None:
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame[observed_column] * scale,
            name=f"Observed {label}",
            line={"color": "#1769AA"},
        ),
        row=row,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame[expected_column] * scale,
            name=f"Expected {label}",
            line={"color": "#DD6B20", "dash": "dash"},
        ),
        row=row,
        col=1,
    )
