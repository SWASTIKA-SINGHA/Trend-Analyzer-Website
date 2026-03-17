"""Plotly chart builders for trend analytics."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def build_interest_line_chart(df: pd.DataFrame, keyword: str) -> go.Figure:
    """Create an interactive line chart for keyword interest over time."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Keyword Popularity: {keyword}",
            template="plotly_white",
            xaxis_title="Date",
            yaxis_title="Popularity",
            annotations=[
                {
                    "text": (
                        "No data available for this keyword.\n"
                        "Try a more popular keyword, wider timeframe, or click Refresh Trends."
                    ),
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 13},
                    "align": "center",
                }
            ],
        )
        return fig

    fig = px.line(
        df,
        x="date",
        y="popularity",
        markers=True,
        title=f"Google Trends Popularity: {keyword}",
    )
    fig.update_layout(template="plotly_white", xaxis_title="Date", yaxis_title="Popularity (0–100)")
    fig.update_traces(line=dict(width=3), marker=dict(size=6))
    return fig


def build_multi_keyword_chart(df: pd.DataFrame, title: str) -> go.Figure:
    """Create a multi-line chart comparing popularity across related keywords."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title=title,
            template="plotly_white",
            xaxis_title="Date",
            yaxis_title="Popularity",
            annotations=[
                {
                    "text": (
                        "No comparison data available.\n"
                        "Google Trends may be rate-limiting requests. Try clicking Refresh Trends."
                    ),
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 13},
                    "align": "center",
                }
            ],
        )
        return fig

    fig = px.line(
        df,
        x="date",
        y="popularity",
        color="keyword",
        markers=True,
        title=title,
    )
    fig.update_layout(template="plotly_white", xaxis_title="Date", yaxis_title="Popularity (0–100)")
    return fig


def build_related_queries_bar_chart(df: pd.DataFrame, title: str) -> go.Figure:
    """Create a horizontal bar chart for related queries."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=title, template="plotly_white")
        return fig

    chart_df = df.head(10).sort_values("value", ascending=True)
    fig = px.bar(
        chart_df,
        x="value",
        y="query",
        orientation="h",
        title=title,
        text="value",
    )
    fig.update_layout(template="plotly_white", xaxis_title="Trend Score", yaxis_title="Query")
    return fig
