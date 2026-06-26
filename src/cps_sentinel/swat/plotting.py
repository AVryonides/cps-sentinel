"""Interactive report for SWaT attack-detection validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from cps_sentinel.plot_style import apply_report_layout, lift_subplot_titles
from cps_sentinel.swat.analysis import SwatEvaluation, SwatEvent


def build_swat_figure(
    frame: pd.DataFrame,
    events: list[SwatEvent],
    evaluation: SwatEvaluation,
) -> go.Figure:
    """Build anomaly evidence, labels, and leading affected-tag panels."""
    x = frame["timestamp"]
    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.10,
        subplot_titles=(
            "Anomaly score versus clean-data threshold",
            "Labeled attacks and persistent detections",
            "Most frequently implicated process tags",
        ),
        row_heights=(0.48, 0.24, 0.28),
    )
    lift_subplot_titles(figure, yshift=34)
    figure.add_trace(
        go.Scatter(x=x, y=frame["anomaly_score"], name="Anomaly score", line={"color": "#42C6D7"}),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=x,
            y=frame["anomaly_threshold"],
            name="Threshold",
            line={"color": "#E5A93D", "dash": "dash"},
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=x,
            y=frame["is_attack"].astype(int),
            name="Labeled attack",
            line={"color": "#E66565", "shape": "hv"},
            fill="tozeroy",
        ),
        row=2,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=x,
            y=frame["detected"].astype(int),
            name="Detected",
            line={"color": "#6E9CF5", "shape": "hv"},
        ),
        row=2,
        col=1,
    )
    counts: dict[str, int] = {}
    for event in events:
        for tag in event.top_affected_tags:
            counts[tag] = counts.get(tag, 0) + 1
    ranked = sorted(counts, key=lambda tag: (counts[tag], tag))[-12:]
    figure.add_trace(
        go.Bar(
            x=[counts[tag] for tag in ranked],
            y=ranked,
            orientation="h",
            name="Detected events",
            marker_color="#42C6D7",
        ),
        row=3,
        col=1,
    )
    figure.update_yaxes(title_text="Score", row=1, col=1)
    figure.update_yaxes(title_text="Active", tickvals=[0, 1], row=2, col=1)
    figure.update_xaxes(title_text="Event count", row=3, col=1)
    apply_report_layout(
        figure,
        title=(
            "CPS Sentinel - Phase 8 SWaT security validation"
            f"<br><sup>Point F1 {evaluation.f1:.3f} · Event recall "
            f"{evaluation.event_recall:.1%} · False-positive rate "
            f"{evaluation.false_positive_rate:.3%}</sup>"
        ),
        height=1000,
        top_margin=145,
    )
    return figure


def write_swat_plot(
    frame: pd.DataFrame,
    events: list[SwatEvent],
    evaluation: SwatEvaluation,
    path: str | Path,
) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    build_swat_figure(frame, events, evaluation).write_html(output, include_plotlyjs=True)
    return output
