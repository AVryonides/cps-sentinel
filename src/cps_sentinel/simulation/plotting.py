"""Interactive Plotly visualization for Phase 1 simulation output."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from cps_sentinel.config import BatteryConfig
from cps_sentinel.plot_style import apply_report_layout, lift_subplot_titles


def build_simulation_figure(frame: pd.DataFrame, battery: BatteryConfig) -> go.Figure:
    """Build a three-panel physical overview of a nanogrid run."""
    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("PV and load", "Battery and grid power", "Battery state of charge"),
    )
    lift_subplot_titles(figure)
    figure.add_trace(
        go.Scatter(x=frame["timestamp"], y=frame["pv_kw"], name="PV", line={"color": "#E0A11A"}),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"], y=frame["load_kw"], name="Load", line={"color": "#304C89"}
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["battery_power_kw"],
            name="Battery power",
            line={"color": "#2E8B57"},
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["grid_power_kw"],
            name="Grid power",
            line={"color": "#B14A4A"},
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=frame["timestamp"],
            y=frame["battery_soc"] * 100,
            name="SOC",
            line={"color": "#157A8A", "width": 2.5},
        ),
        row=3,
        col=1,
    )
    figure.add_hline(
        y=battery.minimum_soc * 100,
        line_dash="dot",
        line_color="#9B2C2C",
        annotation_text="Minimum SOC",
        row=3,
        col=1,
    )
    figure.add_hline(
        y=battery.maximum_soc * 100,
        line_dash="dot",
        line_color="#2F855A",
        annotation_text="Maximum SOC",
        row=3,
        col=1,
    )
    figure.update_yaxes(title_text="Power (kW)", row=1, col=1)
    figure.update_yaxes(title_text="Power (kW)", row=2, col=1)
    figure.update_yaxes(title_text="SOC (%)", range=[0, 100], row=3, col=1)
    apply_report_layout(
        figure,
        title="CPS Sentinel - Phase 1 nanogrid simulation",
        height=850,
    )
    return figure


def write_simulation_plot(frame: pd.DataFrame, battery: BatteryConfig, path: str | Path) -> Path:
    """Write a self-contained interactive HTML simulation report."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    build_simulation_figure(frame, battery).write_html(output, include_plotlyjs=True)
    return output
