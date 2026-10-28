"""Time-series preparation: monthly aggregation."""

import pandas as pd


def monthly_series(df: pd.DataFrame, train_no=None, zone=None, train_type=None) -> pd.DataFrame:
    """Aggregate to monthly average delay with a DatetimeIndex."""
    tmp = df.copy()
    if "train_no" in tmp.columns and train_no is not None:
        tmp = tmp[tmp["train_no"] == train_no]
    if "zone" in tmp.columns and zone is not None:
        tmp = tmp[tmp["zone"] == zone]
    if "train_type" in tmp.columns and train_type is not None:
        tmp = tmp[tmp["train_type"] == train_type]
    tmp["date"] = pd.to_datetime(tmp["date"])
    monthly = tmp.resample("ME", on="date")["delay_minutes"].mean().reset_index()
    monthly.columns = ["month", "avg_delay"]
    monthly = monthly.dropna()
    return monthly


def monthly_series_from_df(df: pd.DataFrame) -> pd.Series:
    """Return a Series with DatetimeIndex for time-series models."""
    tmp = df.copy()
    if "month" in tmp.columns and "date" not in tmp.columns:
        tmp["date"] = pd.to_datetime(tmp["month"].astype(str) + "-01")
    if "avg_delay" in tmp.columns and "delay_minutes" not in tmp.columns:
        tmp["delay_minutes"] = tmp["avg_delay"]
    monthly = monthly_series(tmp)
    monthly["month"] = pd.to_datetime(monthly["month"])
    series = monthly.set_index("month")["avg_delay"]
    series.index = pd.to_datetime(series.index)
    return series
