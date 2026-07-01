"""Shared Plotly layout helpers for readable CPS Sentinel reports."""

import plotly.graph_objects as go

REPORT_TOP_MARGIN = 130
REPORT_BOTTOM_MARGIN = 118
REPORT_SUBPLOT_TITLE_SHIFT = 26
REPORT_LEGEND_Y = -0.16


def lift_subplot_titles(figure: go.Figure, yshift: int = REPORT_SUBPLOT_TITLE_SHIFT) -> None:
    """Move subplot-title annotations upward before plot-specific annotations are added."""
    figure.update_annotations(yshift=yshift)


def apply_report_layout(
    figure: go.Figure,
    *,
    title: str,
    height: int,
    top_margin: int = REPORT_TOP_MARGIN,
    bottom_margin: int = REPORT_BOTTOM_MARGIN,
    legend_y: float = REPORT_LEGEND_Y,
) -> go.Figure:
    """Apply title, legend, and margin spacing for standalone HTML reports."""
    figure.update_layout(
        title={"text": title, "y": 0.985, "yanchor": "top"},
        template="plotly_white",
        height=height,
        hovermode="x unified",
        margin={"l": 64, "r": 32, "t": top_margin, "b": bottom_margin},
        legend={
            "orientation": "h",
            "x": 0,
            "xanchor": "left",
            "y": legend_y,
            "yanchor": "top",
        },
    )
    return figure
