"""Static Matplotlib + Seaborn charts. Each function returns the figure and saves it."""

import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.config import get_path, load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# seaborn's boxplot still passes the deprecated `vert` argument to Matplotlib >= 3.11
warnings.filterwarnings("ignore", message="vert: bool was deprecated", category=matplotlib.MatplotlibDeprecationWarning)

PALETTE = ["#6E7FE6", "#33325C", "#B6C4F8", "#FB7B1B", "#8FA8F5", "#C9D3F7"]
CATEGORY_COLORS = {"On-time": "#2EAD7A", "Minor": "#FB7B1B", "Major": "#6E7FE6", "Severe": "#E5484D"}


def _save(fig, name: str):
    config = load_config()
    path = get_path(config, "charts_dir") / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)
    return fig


def plot_monthly_avg_delay(df: pd.DataFrame):
    """Line chart: monthly average delay over time."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    tmp = df.copy()
    tmp["month"] = pd.to_datetime(tmp["month"].astype(str) + "-01")
    ax.plot(tmp["month"], tmp["avg_delay"], marker="o", color=PALETTE[0], linewidth=2.5)
    ax.set_title("Monthly Average Delay")
    ax.set_xlabel("Month")
    ax.set_ylabel("Avg Delay (min)")
    ax.grid(alpha=0.3)
    return _save(fig, "01_monthly_avg_delay")


def plot_delay_histogram(delay_minutes) -> "object":
    """Histogram of delay minutes (Matplotlib)."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    values = pd.Series(delay_minutes).dropna()
    cap = values.quantile(0.99)  # a handful of very long delays would squash the plot
    sns.histplot(data=values[values <= cap], bins=40, ax=ax, color=PALETTE[0])
    ax.set_title(f"Delay Minutes Distribution (99% of records, up to {cap:.0f} min)")
    ax.set_xlabel("Delay (min)")
    ax.set_ylabel("Frequency")
    ax.grid(alpha=0.3, axis="y")
    return _save(fig, "02_delay_histogram")


def plot_delay_histogram_kde_by_train_type(df: pd.DataFrame):
    """Histogram with KDE by train type (Seaborn)."""
    fig, ax = plt.subplots(figsize=(10, 5))
    types = sorted(df["train_type"].dropna().astype(str).unique())
    df = df[df["delay_minutes"] <= df["delay_minutes"].quantile(0.99)]
    sns.histplot(data=df, x="delay_minutes", hue="train_type", hue_order=types, kde=True, ax=ax,
                 palette=(PALETTE * 2)[:len(types)], bins=40)
    ax.set_title("Delay Distribution by Train Type (99% of records)")
    ax.set_xlabel("Delay (min)")
    ax.set_ylabel("Frequency")
    return _save(fig, "03_delay_kde_by_train_type")


def plot_delay_by_season(df: pd.DataFrame):
    """Box-and-whisker plot of delay by season."""
    fig, ax = plt.subplots(figsize=(8, 5))
    order = [s for s in ["Winter", "Summer", "Monsoon", "Post-Monsoon"] if s in set(df["season"])]
    sns.boxplot(data=df, x="season", y="delay_minutes", hue="season", order=order, hue_order=order,
                ax=ax, palette=PALETTE[:len(order)], legend=False, showfliers=False)
    ax.set_title("Delay by Season")
    ax.set_xlabel("Season")
    ax.set_ylabel("Delay (min)")
    return _save(fig, "04_delay_by_season")


def plot_delay_by_train_type(df: pd.DataFrame):
    """Box plot of delay by train type."""
    fig, ax = plt.subplots(figsize=(10, 5))
    types = sorted(df["train_type"].dropna().astype(str).unique())
    sns.boxplot(data=df, x="train_type", y="delay_minutes", hue="train_type", order=types, hue_order=types,
                ax=ax, palette=(PALETTE * 2)[:len(types)], legend=False, showfliers=False)
    ax.set_title("Delay by Train Type")
    ax.set_xlabel("Train Type")
    ax.set_ylabel("Delay (min)")
    return _save(fig, "05_delay_by_train_type")


def plot_top_delayed_trains(df: pd.DataFrame):
    """Vertical bar chart: top 10 most delayed trains."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    top = df.head(10).sort_values("avg_delay")
    ax.barh(top["train_name"], top["avg_delay"], color=PALETTE[0])
    ax.set_title("Top 10 Most Delayed Trains")
    ax.set_xlabel("Average Delay (min)")
    ax.set_ylabel("Train")
    ax.grid(alpha=0.3, axis="x")
    return _save(fig, "06_top_delayed_trains")


def plot_worst_stations(df: pd.DataFrame):
    """Horizontal bar chart: worst 10 stations by average delay."""
    fig, ax = plt.subplots(figsize=(10, 6))
    worst = df.head(10).sort_values("avg_delay")
    ax.barh(worst["station_name"], worst["avg_delay"], color=PALETTE[3])
    ax.set_title("Worst 10 Stations by Average Delay")
    ax.set_xlabel("Average Delay (min)")
    ax.set_ylabel("Station")
    ax.grid(alpha=0.3, axis="x")
    return _save(fig, "07_worst_stations")


def plot_avg_delay_by_zone_per_year(df: pd.DataFrame):
    """Grouped bar chart: average delay by zone per year."""
    fig, ax = plt.subplots(figsize=(12, 5.5))
    tmp = df.copy()
    tmp["year"] = pd.to_numeric(tmp["year"], errors="coerce").astype(int)
    tmp["zone"] = tmp["zone"].astype(str)
    sns.barplot(data=tmp, x="zone", y="avg_delay", hue="year", ax=ax, palette=PALETTE[:tmp["year"].nunique()])
    ax.set_title("Average Delay by Zone per Year")
    ax.set_xlabel("Zone")
    ax.set_ylabel("Avg Delay (min)")
    ax.legend(title="Year")
    return _save(fig, "08_zone_by_year")


def plot_stacked_bar_delay_categories(df: pd.DataFrame):
    """Stacked bar: share (%) of journeys in each delay category per train type."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    cats = ["On-time", "Minor", "Major", "Severe"]
    share = pd.crosstab(df["train_type"].astype(str), df["delay_category"], normalize="index") * 100
    share = share.reindex(columns=cats, fill_value=0.0)
    bottoms = [0.0] * len(share)
    for c in cats:
        values = share[c].tolist()
        ax.bar(share.index, values, bottom=bottoms, label=c, color=CATEGORY_COLORS[c])
        bottoms = [b + v for b, v in zip(bottoms, values)]
    ax.set_title("Delay Categories Share by Train Type")
    ax.set_ylabel("Share of records (%)")
    ax.legend(title="Delay Category")
    return _save(fig, "09_stacked_delay_categories")


def plot_pie_delay_categories(df: pd.DataFrame):
    """Pie chart: share of delay categories."""
    fig, ax = plt.subplots(figsize=(8, 6))
    counts = df["delay_category"].value_counts()
    ax.pie(counts, labels=counts.index, autopct="%1.1f%%", colors=[CATEGORY_COLORS.get(c, PALETTE[5]) for c in counts.index])
    ax.set_title("Delay Category Share")
    return _save(fig, "10_pie_delay_categories")


def plot_donut_delay_reasons(df: pd.DataFrame):
    """Donut chart: share of delay reasons from remarks."""
    fig, ax = plt.subplots(figsize=(8, 6))
    reasons = df.head(6).sort_values("cnt")
    ax.pie(reasons["cnt"], labels=reasons["reason"], autopct="%1.1f%%", startangle=90)
    ax.set_title("Delay Reasons from Remarks")
    return _save(fig, "11_donut_delay_reasons")


def plot_heatmap_month_year(df: pd.DataFrame):
    """Heatmap: month x year average delay."""
    fig, ax = plt.subplots(figsize=(12, 5))
    tmp = df.copy()
    tmp["year"] = pd.to_numeric(tmp["year"], errors="coerce").astype(int)
    tmp["month"] = pd.to_numeric(tmp["month"], errors="coerce").astype(int)
    pivot = tmp.pivot(index="month", columns="year", values="avg_delay")
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="YlOrRd", ax=ax)
    ax.set_title("Month x Year Average Delay")
    ax.set_xlabel("Year")
    ax.set_ylabel("Month")
    return _save(fig, "12_heatmap_month_year")


def plot_correlation_heatmap(df: pd.DataFrame):
    """Heatmap: correlation matrix."""
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(df.corr(), annot=True, cmap="RdBu_r", ax=ax, vmin=-1, vmax=1)
    ax.set_title("Correlation Matrix")
    return _save(fig, "13_correlation_heatmap")


def plot_scatter_distance_vs_delay(df: pd.DataFrame):
    """Scatter: distance from source vs delay."""
    fig, ax = plt.subplots(figsize=(8, 6))
    pts = df.dropna(subset=["distance_from_source_km", "delay_minutes"])
    pts = pts.sample(min(len(pts), 5000), random_state=42)
    ax.scatter(pts["distance_from_source_km"], pts["delay_minutes"], alpha=0.25, s=8, color=PALETTE[0])
    ax.set_title("Distance vs Delay")
    ax.set_xlabel("Distance from Source (km)")
    ax.set_ylabel("Delay (min)")
    return _save(fig, "14_scatter_distance_delay")


def plot_delay_accumulation(df: pd.DataFrame):
    """Line chart: delay accumulation along the route for one train."""
    fig, ax = plt.subplots(figsize=(10, 5))
    tmp = df.copy()
    tmp = tmp.sort_values("stop_sequence")
    ax.plot(tmp["stop_sequence"], tmp["avg_delay"], marker="o", color=PALETTE[3], linewidth=2.5)
    ax.set_xticks(tmp["stop_sequence"], tmp["station_code"])
    title = f"Delay Accumulation Along Route (train {int(tmp['train_no'].iloc[0])})" if len(tmp) else "Delay Accumulation Along Route"
    ax.set_title(title)
    ax.set_xlabel("Station (in route order)")
    ax.set_ylabel("Avg Delay (min)")
    ax.grid(alpha=0.3)
    return _save(fig, "15_delay_accumulation")
