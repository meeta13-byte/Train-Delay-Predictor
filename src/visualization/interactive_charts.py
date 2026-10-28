"""Interactive Plotly charts. Each function returns the figure."""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def plot_interactive_monthly_trend(df) -> "object":
    """Interactive monthly trend line with hover."""
    tmp = df.copy()
    tmp["month"] = pd.to_datetime(tmp["month"].astype(str) + "-01") if "month" in tmp else None
    fig = px.line(tmp, x="month", y="avg_delay", title="Monthly Average Delay", hover_data=["avg_delay"])
    fig.update_layout(template="plotly_white")
    return fig


def plot_interactive_zone_bar(df):
    """Interactive grouped bar chart by zone."""
    fig = px.bar(df, x="zone", y="avg_delay", color="year", title="Avg Delay by Zone", barmode="group")
    fig.update_layout(template="plotly_white")
    return fig


def plot_station_map(df) -> "object":
    """Scatter map of stations sized/coloured by average delay."""
    fig = go.Figure(
        data=go.Scattergeo(
            locations=df["station_code"],
            lat=df["latitude"],
            lon=df["longitude"],
            text=df["station_name"],
            customdata=df["avg_delay"],
            mode="markers",
            marker=dict(
                size=(df["avg_delay"] / max(df["avg_delay"].max(), 1) * 12 + 4),
                color=df["avg_delay"],
                colorscale="Viridis",
                showscale=True,
            ),
        )
    )
    fig.update_layout(title="Station Average Delay Map", geo=dict(scope="world"))
    return fig
