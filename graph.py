"""Plotly graph helpers for Internet Trend Radar."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def build_popularity_chart(df: pd.DataFrame, keyword: str) -> go.Figure:
    """Create an interactive line chart for keyword popularity."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"No data available for '{keyword}'",
            template="plotly_white",
            xaxis_title="Date",
            yaxis_title="Popularity",
        )
        return fig

    fig = px.line(
        df,
        x="date",
        y="popularity",
        title=f"Popularity Over Time: {keyword}",
        markers=True,
    )
    fig.update_layout(template="plotly_white", xaxis_title="Date", yaxis_title="Popularity (0-100)")
    fig.update_traces(line=dict(width=3), marker=dict(size=6))
    return fig
