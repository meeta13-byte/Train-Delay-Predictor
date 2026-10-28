"""Thin API layer for the UI (Streamlit). Functions return DataFrames, dicts or figures."""

from pathlib import Path

import pandas as pd

from src.config import load_config
from src.database import queries
from src.database.db_loader import get_engine
from src.ingestion.loader import load_all
from src.cleaning.cleaner import run_cleaning
from src.timeseries import arima_model, prepare


ENGINE = None


def _get_engine():
    global ENGINE
    if ENGINE is None:
        ENGINE = get_engine("sqlite")
    return ENGINE


def get_summary_kpis() -> dict:
    engine = _get_engine()
    monthly = queries.monthly_avg_delay(engine)
    top_train = queries.top_delayed_trains(engine, 1)
    worst_station = queries.worst_stations(engine, 1)
    ontime = queries.ontime_performance(engine)
    return {
        "total_records": int(pd.read_sql("SELECT COUNT(*) as c FROM delay_records", engine).iloc[0]["c"]),
        "avg_delay_overall": float(monthly["avg_delay"].mean()) if not monthly.empty else 0.0,
        "most_delayed_train": top_train.iloc[0]["train_name"] if not top_train.empty else None,
        "most_delayed_train_avg": float(top_train.iloc[0]["avg_delay"]) if not top_train.empty else None,
        "worst_station": worst_station.iloc[0]["station_name"] if not worst_station.empty else None,
        "worst_station_avg": float(worst_station.iloc[0]["avg_delay"]) if not worst_station.empty else None,
        "ontime_pct": float(ontime["ontime_pct"].mean()) if not ontime.empty else 0.0,
    }


def get_filtered_delays(filters: dict, limit: int = 10000) -> pd.DataFrame:
    """Delay records (with calendar / category features) matching `filters`; limit=None for all."""
    from src.cleaning.cleaner import add_features

    engine = _get_engine()
    sql = "SELECT * FROM delay_records WHERE 1=1"
    params = {}
    if filters.get("train_no"):
        sql += " AND train_no = :train_no"
        params["train_no"] = filters["train_no"]
    if filters.get("station_code"):
        sql += " AND station_code = :station_code"
        params["station_code"] = filters["station_code"]
    if limit:
        sql += f" LIMIT {int(limit)}"
    df = pd.read_sql(sql, engine, params=params)
    return add_features(df)


def get_top_delayed_trains(n: int = 10) -> pd.DataFrame:
    return queries.top_delayed_trains(_get_engine(), n)


def get_delay_by_train_type() -> pd.DataFrame:
    return queries.avg_delay_by_train_type(_get_engine())


def get_station_delays() -> pd.DataFrame:
    return queries.worst_stations(_get_engine(), 100)


def get_monthly_series(filters: dict = None):
    filters = filters or {}
    return queries.monthly_series_with_filters(
        _get_engine(),
        train_no=filters.get("train_no"),
        zone=filters.get("zone"),
        train_type=filters.get("train_type"),
    )


def run_forecast(filters: dict = None, steps: int = 3) -> dict:
    config = load_config()
    steps = int(config.get("forecast", {}).get("steps", steps))
    monthly = get_monthly_series(filters)
    series = prepare.monthly_series_from_df(monthly)
    metrics = arima_model.evaluate_holdout(series, holdout_months=int(config.get("forecast", {}).get("holdout_months", 6)))
    fc = arima_model.forecast_next_months(series, steps=steps)
    return {"metrics": metrics, "forecast": fc, "series": series}


def get_chart(name: str, filters: dict = None):
    from src.visualization import static_charts

    filters = filters or {}
    engine = _get_engine()
    if name == "monthly":
        return static_charts.plot_monthly_avg_delay(get_monthly_series(filters))
    if name == "top_trains":
        return static_charts.plot_top_delayed_trains(get_top_delayed_trains(10))
    if name == "worst_stations":
        return static_charts.plot_worst_stations(get_station_delays())
    raise ValueError(f"Unknown chart: {name}")


def list_trains() -> pd.DataFrame:
    engine = _get_engine()
    return pd.read_sql("SELECT * FROM trains", engine)


def list_stations() -> pd.DataFrame:
    engine = _get_engine()
    return pd.read_sql("SELECT * FROM stations", engine)


def list_zones() -> pd.DataFrame:
    engine = _get_engine()
    return pd.read_sql("SELECT DISTINCT zone FROM trains", engine)


def plan_journey(to_code: str, travel_date, from_code: str = None, train_no: int = None,
                 train_type: str = None, leave_after=None) -> dict:
    """Predicted delay for a train plus ranked alternatives on the same route.

    See src/planner.py. Raises planner.PlannerError for bad input.
    """
    from src import planner

    return planner.plan_journey(
        _get_engine(), to_code=to_code, travel_date=travel_date, from_code=from_code,
        train_no=train_no, train_type=train_type, leave_after=leave_after,
    )


def list_train_stops() -> pd.DataFrame:
    engine = _get_engine()
    return pd.read_sql("SELECT * FROM train_stops ORDER BY train_no, stop_sequence", engine)
