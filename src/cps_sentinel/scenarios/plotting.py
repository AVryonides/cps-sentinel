"""Interactive scenario visualization with ground-truth attack windows."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from cps_sentinel.plot_style import apply_report_layout, lift_subplot_titles


def build_scenario_figure(frame: pd.DataFrame) -> go.Figure:
    """Build a synchronized view of sensing, commands, physical impact, and residuals."""
    figure = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=(
            "PV sensing and twin expectation",
            "Battery command path",
            "Physical grid response",
            "Digital-twin residuals",
        ),
    )
    lift_subplot_titles(figure)
    traces = (
        (1, "true_pv_kw", "True PV", "#2F855A", None),
        (1, "pv_kw", "Reported PV", "#1769AA", None),
        (1, "expected_pv_kw", "Expected PV", "#DD6B20", "dash"),
        (2, "requested_battery_power_kw", "Nominal command", "#1769AA", None),
        (2, "commanded_battery_power_kw", "Delivered command", "#C53030", "dash"),
        (2, "battery_power_kw", "Actual battery power", "#2F855A", None),
        (3, "grid_power_kw", "Physical grid power", "#1769AA", None),
        (3, "expected_grid_power_kw", "Expected grid power", "#DD6B20", "dash"),
        (4, "pv_residual_kw", "PV residual", "#D69E2E", None),
        (4, "grid_power_residual_kw", "Grid residual", "#C53030", None),
        (4, "battery_power_residual_kw", "Battery residual", "#2F855A", None),
    )
    for row, column, name, color, dash in traces:
        line = {"color": color}
        if dash:
            line["dash"] = dash
        figure.add_trace(
            go.Scatter(x=frame["timestamp"], y=frame[column], name=name, line=line),
            row=row,
            col=1,
        )

    active = frame[frame["scenario_active"]]
    if not active.empty:
        figure.add_vrect(
            x0=active["timestamp"].iloc[0],
            x1=active["timestamp"].iloc[-1],
            fillcolor="#E53E3E",
            opacity=0.10,
            line_width=0,
            annotation_text=str(active["scenario_name"].iloc[0]),
            annotation_position="top",
            row="all",
            col=1,
        )
    figure.add_hline(y=0, line_color="#718096", line_width=1, row=4, col=1)
    for row in range(1, 5):
        figure.update_yaxes(title_text="Power (kW)", row=row, col=1)
    apply_report_layout(
        figure,
        title="CPS Sentinel - attack and fault scenario",
        height=1050,
    )
    return figure


def write_scenario_plot(frame: pd.DataFrame, path: str | Path) -> Path:
    """Write a self-contained interactive scenario report."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    build_scenario_figure(frame).write_html(output, include_plotlyjs=True)
    return output
