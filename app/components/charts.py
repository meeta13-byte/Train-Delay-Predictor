import plotly.graph_objects as go
import plotly.express as px
from app.theme import apply_theme, CHART_PALETTE


def plot_monthly_trend(df):
    fig = px.line(df, x="month", y="avg_delay", title="Monthly Average Delay", markers=True)
    fig.update_traces(line_color=CHART_PALETTE[0], line_width=3)
    fig.update_layout(xaxis_title="Month", yaxis_title="Average Delay (min)")
    apply_theme(fig)
    return fig


def plot_train_type_bar(df):
    fig = px.bar(df, x="train_type", y="avg_delay", title="Average Delay by Train Type")
    fig.update_traces(marker_color=CHART_PALETTE)
    fig.update_layout(xaxis_title="Train Type", yaxis_title="Average Delay (min)")
    apply_theme(fig)
    return fig


def plot_delay_category_donut(df):
    counts = df["delay_category"].value_counts()
    fig = go.Figure(data=[go.Pie(labels=counts.index, values=counts.values, hole=0.5)])
    fig.update_layout(title="Delay Category Share")
    apply_theme(fig)
    return fig


def plot_month_year_heatmap(df):
    pivot = df.pivot(index="month", columns="year", values="avg_delay")
    fig = go.Figure(data=go.Heatmap(z=pivot.values, x=[str(c) for c in pivot.columns], y=pivot.index, colorscale="Blues"))
    fig.update_layout(title="Month × Year Average Delay")
    apply_theme(fig)
    return fig
