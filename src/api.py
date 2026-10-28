"""API layer for the web UI (see src/bridge.py and server/). Functions return DataFrames or JSON-ready dicts."""

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


# ============================================================================
# JSON helpers for the web UI (server/ calls these through src/bridge.py).
# Every function below returns plain dicts / lists that json.dumps can handle
# once passed through `to_jsonable`.
# ============================================================================

import math
import re
import sqlite3
from datetime import date as _date, datetime as _datetime, time as _time

import numpy as np

SEASON_ORDER = ["Winter", "Summer", "Monsoon", "Post-Monsoon"]
CATEGORY_ORDER = ["On-time", "Minor", "Major", "Severe"]
TYPE_ORDER = ["Vande Bharat", "Shatabdi", "Rajdhani", "Duronto", "Superfast", "Mail/Express", "Passenger"]
SEVERE_MINUTES = 180
ON_TIME_MINUTES = 15

_CACHE = {}


def to_jsonable(obj):
    """Recursively convert pandas / numpy / datetime values to JSON-safe Python types."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, pd.DataFrame):
        return to_jsonable(obj.to_dict(orient="records"))
    if isinstance(obj, pd.Series):
        return to_jsonable(obj.tolist())
    if isinstance(obj, (pd.Timestamp, _datetime)):
        return None if pd.isna(obj) else obj.isoformat()
    if isinstance(obj, (_date, _time)):
        return obj.isoformat()
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    if obj is pd.NA or obj is pd.NaT:
        return None
    return obj


def _db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "railway.db"


def _cached(key, build):
    """Cache a value until the database file changes (e.g. after a pipeline re-run)."""
    stamp = _db_path().stat().st_mtime if _db_path().exists() else None
    hit = _CACHE.get(key)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    value = build()
    _CACHE[key] = (stamp, value)
    return value


def reset_cache() -> dict:
    global ENGINE
    _CACHE.clear()
    if ENGINE is not None:
        ENGINE.dispose()
        ENGINE = None
    return {"ok": True}


def _round(v, nd=1):
    return None if v is None or pd.isna(v) else round(float(v), nd)


def _delays_frame() -> pd.DataFrame:
    """All delay records joined with train attributes and calendar features."""
    def build():
        from src.cleaning.cleaner import add_features

        sql = (
            "SELECT d.date, d.train_no, d.station_code, d.delay_minutes, d.weather_condition, d.cancelled, "
            "t.train_name, t.train_type, t.zone, ts.distance_from_source_km, ts.stop_sequence "
            "FROM delay_records d JOIN trains t ON d.train_no = t.train_no "
            "LEFT JOIN train_stops ts ON ts.train_no = d.train_no AND ts.station_code = d.station_code"
        )
        df = pd.read_sql(sql, _get_engine())
        df["cancelled"] = df["cancelled"].astype(bool)
        df = add_features(df)
        df["date"] = pd.to_datetime(df["date"])
        return df

    return _cached("delays", build)


def _apply_filters(df: pd.DataFrame, filters: dict = None) -> pd.DataFrame:
    """Filter by date range, zones, train types and season. Cancelled runs are dropped."""
    f = filters or {}
    mask = ~df["cancelled"]
    if f.get("start"):
        mask &= df["date"] >= pd.Timestamp(f["start"])
    if f.get("end"):
        mask &= df["date"] <= pd.Timestamp(f["end"])
    if f.get("zones"):
        mask &= df["zone"].isin(f["zones"])
    if f.get("train_types"):
        mask &= df["train_type"].isin(f["train_types"])
    if f.get("season") and f["season"] != "All":
        mask &= df["season"] == f["season"]
    return df[mask]


def db_status() -> dict:
    path = _db_path()
    if not path.exists():
        return {"ready": False, "message": "Database not found. Run the pipeline first."}
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            n = conn.execute("SELECT COUNT(*) FROM delay_records").fetchone()[0]
    except sqlite3.Error as e:
        return {"ready": False, "message": f"Database is not usable: {e}"}
    return {"ready": n > 0, "records": n, "updated": _datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")}


def ui_meta() -> dict:
    """Options for filters and pickers."""
    df = _delays_frame()
    trains = list_trains().sort_values("train_no")
    stations = list_stations().sort_values("station_name")
    stops = list_train_stops()
    served = set(stops["station_code"])
    types = [t for t in TYPE_ORDER if t in set(trains["train_type"])]
    return to_jsonable({
        "zones": sorted(trains["zone"].dropna().unique().tolist()),
        "train_types": types,
        "seasons": SEASON_ORDER,
        "date_min": df["date"].min().date(),
        "date_max": df["date"].max().date(),
        "trains": trains[["train_no", "train_name", "train_type", "source_station_code", "destination_station_code"]],
        "stations": stations[stations["station_code"].isin(served)][["station_code", "station_name"]],
    })


def ui_home() -> dict:
    """Headline numbers for the landing page."""
    df = _apply_filters(_delays_frame())
    by_train = df.groupby(["train_no", "train_name"])["delay_minutes"].mean().sort_values(ascending=False)
    (top_no, top_name), top_avg = by_train.index[0], by_train.iloc[0]
    winter = df[df["season"] == "Winter"]["delay_minutes"].mean()
    rest = df[df["season"] != "Winter"]["delay_minutes"].mean()
    fog = df[df["month"].isin([12, 1])]["delay_minutes"].mean()
    by_season = df.groupby("season")["delay_minutes"].mean()
    this_month = _date.today().month
    month_avg = df[df["month"] == this_month]["delay_minutes"].mean()
    stations = df.groupby("station_code")["delay_minutes"].mean().sort_values(ascending=False)
    names = dict(zip(list_stations()["station_code"], list_stations()["station_name"]))
    return to_jsonable({
        "total_records": len(df),
        "avg_delay": _round(df["delay_minutes"].mean()),
        "ontime_pct": _round((df["delay_minutes"] <= ON_TIME_MINUTES).mean() * 100),
        "most_delayed_train": {"train_no": top_no, "train_name": top_name, "avg_delay": _round(top_avg)},
        "worst_station": {"station_code": stations.index[0], "station_name": names.get(stations.index[0]), "avg_delay": _round(stations.iloc[0])},
        "worst_season": {"season": by_season.idxmax(), "avg_delay": _round(by_season.max())},
        "fog_impact_pct": _round((fog / rest - 1) * 100, 0),
        "winter_avg": _round(winter),
        "fog_avg": _round(fog),
        "rest_avg": _round(rest),
        "month_name": _date.today().strftime("%B"),
        "month_avg_delay": _round(month_avg, 0),
        "period": [df["date"].min().date(), df["date"].max().date()],
        "n_trains": int(df["train_no"].nunique()),
        "n_stations": int(df["station_code"].nunique()),
    })


def _category_counts(df):
    counts = df["delay_category"].value_counts()
    return [{"category": c, "count": int(counts.get(c, 0))} for c in CATEGORY_ORDER]


def ui_dashboard(filters: dict = None) -> dict:
    df = _apply_filters(_delays_frame(), filters)
    if df.empty:
        return {"empty": True}
    monthly = df.groupby(df["date"].dt.to_period("M"))["delay_minutes"].mean()
    by_type = df.groupby("train_type")["delay_minutes"].agg(["mean", "count"]).reset_index()
    by_type = by_type.sort_values("mean", ascending=False)
    heat = df.groupby(["year", "month"])["delay_minutes"].mean().unstack("year").reindex(range(1, 13))
    return to_jsonable({
        "empty": False,
        "kpis": {
            "total_records": len(df),
            "avg_delay": _round(df["delay_minutes"].mean()),
            "ontime_pct": _round((df["delay_minutes"] <= ON_TIME_MINUTES).mean() * 100),
            "severe_count": int((df["delay_minutes"] > SEVERE_MINUTES).sum()),
        },
        "monthly": [{"month": str(p), "avg_delay": _round(v)} for p, v in monthly.items()],
        "by_type": [{"train_type": r.train_type, "avg_delay": _round(r.mean), "records": int(r.count)} for r in by_type.itertuples()],
        "categories": _category_counts(df),
        "heatmap": {
            "years": [int(y) for y in heat.columns],
            "months": [_date(2000, m, 1).strftime("%b") for m in heat.index],
            "values": [[_round(v) for v in row] for row in heat.values.tolist()],
        },
    })


def _box_stats(values: pd.Series) -> dict:
    v = values.dropna()
    q1, med, q3 = v.quantile([0.25, 0.5, 0.75])
    iqr = q3 - q1
    lo = v[v >= q1 - 1.5 * iqr].min()
    hi = v[v <= q3 + 1.5 * iqr].max()
    return {"q1": _round(q1), "median": _round(med), "q3": _round(q3), "lowerfence": _round(lo),
            "upperfence": _round(hi), "mean": _round(v.mean()), "n": int(len(v))}


def ui_delay_analysis(filters: dict = None) -> dict:
    df = _apply_filters(_delays_frame(), filters)
    if df.empty:
        return {"empty": True}
    d = df["delay_minutes"]
    upper = float(max(30, np.ceil(d.quantile(0.99) / 10) * 10))
    edges = np.arange(np.floor(min(d.min(), 0) / 10) * 10, upper + 10, 10)
    counts, edges = np.histogram(d.clip(upper=upper), bins=edges)
    seasons = [s for s in SEASON_ORDER if s in set(df["season"])]
    types = [t for t in TYPE_ORDER if t in set(df["train_type"])]
    weather = df.groupby("weather_condition")["delay_minutes"].agg(["mean", "count"]).sort_values("mean", ascending=False)
    sample = df.dropna(subset=["distance_from_source_km"]).sample(min(len(df), 1500), random_state=7)
    share = pd.crosstab(df["train_type"], df["delay_category"], normalize="index").reindex(index=types, columns=CATEGORY_ORDER, fill_value=0) * 100
    reasons = queries.common_delay_reasons(_get_engine())
    return to_jsonable({
        "empty": False,
        "histogram": {"edges": edges.tolist(), "counts": counts.tolist(), "clipped_at": upper},
        "by_season": [{"label": s, **_box_stats(df.loc[df["season"] == s, "delay_minutes"])} for s in seasons],
        "by_type": [{"label": t, **_box_stats(df.loc[df["train_type"] == t, "delay_minutes"])} for t in types],
        "by_weather": [{"weather": w, "avg_delay": _round(r["mean"]), "records": int(r["count"])} for w, r in weather.iterrows()],
        "scatter": {"distance": sample["distance_from_source_km"].round(0).tolist(),
                    "delay": sample["delay_minutes"].round(0).tolist(), "train_type": sample["train_type"].tolist()},
        "category_share": {"types": types, "series": [{"category": c, "values": [_round(v) for v in share[c]]} for c in CATEGORY_ORDER]},
        "reasons": [{"reason": r.reason, "count": int(r.cnt), "avg_delay": _round(r.avg_delay)} for r in reasons.itertuples()],
    })


def ui_train_explorer(train_no: int) -> dict:
    train_no = int(train_no)
    df = _delays_frame()
    df = df[(df["train_no"] == train_no)]
    trains = list_trains().set_index("train_no")
    if train_no not in trains.index:
        raise ValueError(f"Unknown train {train_no}")
    t = trains.loc[train_no]
    running = df[~df["cancelled"]]
    acc = queries.delay_accumulation_by_stop(_get_engine(), train_no)
    final = acc.iloc[-1]["avg_delay"] if len(acc) else None
    return to_jsonable({
        "train_no": train_no, "train_name": t["train_name"], "train_type": t["train_type"], "zone": t["zone"],
        "source": t["source_station_code"], "destination": t["destination_station_code"], "distance_km": t["distance_km"],
        "avg_delay": _round(running["delay_minutes"].mean()),
        "avg_delay_at_destination": _round(final),
        "ontime_pct": _round((running["delay_minutes"] <= ON_TIME_MINUTES).mean() * 100),
        "cancel_pct": _round(df.drop_duplicates("date")["cancelled"].mean() * 100),
        "journeys": int(df["date"].nunique()),
        "accumulation": acc[["stop_sequence", "station_code", "station_name", "avg_delay"]].round(1),
    })


def ui_stations() -> dict:
    df = _apply_filters(_delays_frame())
    agg = df.groupby("station_code")["delay_minutes"].agg(["mean", "count"]).reset_index()
    agg["ontime_pct"] = df.groupby("station_code")["delay_minutes"].apply(lambda s: (s <= ON_TIME_MINUTES).mean() * 100).values
    st = list_stations().merge(agg, on="station_code", how="inner").rename(columns={"mean": "avg_delay", "count": "records"})
    st = st.sort_values("avg_delay", ascending=False)
    st["avg_delay"] = st["avg_delay"].round(1)
    st["ontime_pct"] = st["ontime_pct"].round(1)
    stops = list_train_stops().sort_values(["train_no", "stop_sequence"])
    links = set()
    for _, g in stops.groupby("train_no"):
        codes = g["station_code"].tolist()
        links.update(tuple(sorted(pair)) for pair in zip(codes, codes[1:]))
    return to_jsonable({"stations": st, "worst": st.head(10), "links": sorted(links)})


def _forecast_series(scope: dict):
    scope = scope or {}
    kind, value = scope.get("kind", "all"), scope.get("value")
    kwargs = {}
    if kind == "zone" and value:
        kwargs["zone"] = value
    elif kind == "train_type" and value:
        kwargs["train_type"] = value
    elif kind == "train" and value:
        kwargs["train_no"] = int(value)
    monthly = queries.monthly_series_with_filters(_get_engine(), **kwargs)
    return prepare.monthly_series_from_df(monthly)


def ui_forecast(scope: dict = None) -> dict:
    """ARIMA(1,1,1) forecast plus the supporting time-series analysis for one scope."""
    import warnings

    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.tsa.stattools import acf, pacf

    from src.timeseries import smoothing

    def build():
        series = _forecast_series(scope)
        if len(series) < 24:
            return {"empty": True, "message": "Not enough monthly history for this selection (need 24 months)."}
        config = load_config()
        steps = int(config.get("forecast", {}).get("steps", 3))
        holdout = int(config.get("forecast", {}).get("holdout_months", 6))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # convergence chatter from statsmodels on short series
            metrics = arima_model.evaluate_holdout(series, holdout_months=holdout)
            fc = arima_model.forecast_next_months(series, steps=steps)
            decomp = seasonal_decompose(series, model="additive", period=12)
            sma, ema = smoothing.moving_averages(series)
            ses = smoothing.simple_exp_smooth(series)
            hw = smoothing.holt_winters(series)
            hw_fc = hw.forecast(steps)
        adf = arima_model.adf_test(series)
        nlags = min(18, len(series) // 2 - 1)
        idx = [d.strftime("%Y-%m") for d in series.index]
        f_idx = [d.strftime("%Y-%m") for d in fc["forecast"].index]
        conf = fc["conf_int"]
        values = [_round(v) for v in fc["forecast"]]
        return {
            "empty": False,
            "history": {"months": idx, "values": [_round(v) for v in series]},
            "forecast": {"months": f_idx, "values": values,
                         "lower": [_round(v) for v in conf.iloc[:, 0]], "upper": [_round(v) for v in conf.iloc[:, 1]]},
            "holdout": {"months": [d.strftime("%Y-%m") for d in metrics["test"].index],
                        "actual": [_round(v) for v in metrics["test"]], "predicted": [_round(v) for v in metrics["pred"]]},
            "kpis": {"next_month": values[0], "next_month_label": f_idx[0], "avg_3m": _round(np.mean(values)),
                     "mae": _round(metrics["mae"], 2), "rmse": _round(metrics["rmse"], 2),
                     "last_actual": _round(series.iloc[-1])},
            "decomposition": {"months": idx, "trend": [_round(v) for v in decomp.trend], "seasonal": [_round(v) for v in decomp.seasonal],
                              "resid": [_round(v) for v in decomp.resid]},
            "smoothing": {"months": idx, "sma": [_round(v) for v in sma], "ema": [_round(v) for v in ema],
                          "ses": [_round(v) for v in ses.fittedvalues], "holt_winters": [_round(v) for v in hw.fittedvalues],
                          "hw_forecast_months": [d.strftime("%Y-%m") for d in hw_fc.index], "hw_forecast": [_round(v) for v in hw_fc]},
            "adf": {"statistic": _round(adf["test_statistic"], 3), "p_value": _round(adf["p_value"], 4), "lags": adf["lags"],
                    "n_obs": adf["n_obs"], "critical_values": {k: _round(v, 3) for k, v in adf["critical_values"].items()},
                    "stationary": bool(adf["stationary"])},
            "acf": [_round(v, 3) for v in acf(series, nlags=nlags)],
            "pacf": [_round(v, 3) for v in pacf(series, nlags=nlags)],
            "conf_bound": _round(1.96 / math.sqrt(len(series)), 3),
        }

    key = ("forecast", (scope or {}).get("kind", "all"), str((scope or {}).get("value")))
    return to_jsonable(_cached(key, build))


# ---------------------------------------------------------------- pipeline page

def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _preview(df: pd.DataFrame, n: int = 8):
    return {"rows": len(df), "columns": list(df.columns), "head": to_jsonable(df.head(n).astype(object).where(df.head(n).notna(), None))}


def ui_pipeline() -> dict:
    """Everything the Data Pipeline page shows."""
    import json as _json

    from src.ingestion.csv_reader import read_delay_records_csv, read_trains_csv
    from src.ingestion.json_reader import read_stations_json
    from src.ingestion.txt_reader import parse_remark_line
    from src.ingestion.xml_reader import read_routes_xml
    from src.database.db_loader import run_integrity_check

    config = load_config()
    root = _project_root()
    raw = root / config["paths"]["raw_dir"]
    reports = root / config["paths"]["reports_dir"]

    files = []
    if raw.exists():
        readers = [
            ("trains.csv", "CSV", True, read_trains_csv),
            ("stations.json", "JSON", True, read_stations_json),
            ("routes.xml", "XML", True, read_routes_xml),
            ("delay_records.csv", "CSV", True, read_delay_records_csv),
        ]
        for name, fmt, structured, reader in readers:
            if (raw / name).exists():
                files.append({"file": name, "format": fmt, "structured": structured, **_preview(reader(raw / name))})
        txt = raw / "delay_remarks.txt"
        if txt.exists():
            lines = [ln.strip() for ln in txt.read_text().splitlines() if ln.strip()]
            codes = list_stations()["station_code"].tolist()
            parsed = [{"line": ln, **(parse_remark_line(ln, codes) or {"unparsed": True})} for ln in lines]
            files.append({"file": "delay_remarks.txt", "format": "TXT", "structured": False, "rows": len(lines),
                          "columns": ["date", "train_no", "station_code", "delay_minutes", "reason"], "lines": parsed})

    report = {}
    if (reports / "cleaning_report.json").exists():
        report = _json.loads((reports / "cleaning_report.json").read_text())

    engine = _get_engine()
    counts = {}
    with engine.begin() as conn:
        from sqlalchemy import text as _text
        for table in ["stations", "trains", "train_stops", "delay_records", "delay_remarks"]:
            counts[table] = conn.execute(_text(f"SELECT COUNT(*) FROM {table}")).scalar()

    return to_jsonable({
        "files": files,
        "cleaning": report,
        "relationships": RELATIONSHIPS,
        "er_diagram": er_diagram_mermaid(),
        "integrity": run_integrity_check(engine),
        "database": {"type": "SQLite", "url": str(_db_path().relative_to(root)), "tables": counts},
        "queries": list_predefined_queries(),
        "downloads": list_downloads(),
    })


RELATIONSHIPS = [
    {"parent": "stations", "child": "trains", "key": "source_station_code / destination_station_code", "cardinality": "1 : N",
     "meaning": "A station is the start or end of many trains"},
    {"parent": "trains", "child": "train_stops", "key": "train_no", "cardinality": "1 : N", "meaning": "A train has many timetable stops"},
    {"parent": "stations", "child": "train_stops", "key": "station_code", "cardinality": "1 : N", "meaning": "A station is a stop for many trains"},
    {"parent": "trains", "child": "delay_records", "key": "train_no", "cardinality": "1 : N", "meaning": "A train has a delay record per stop per day"},
    {"parent": "stations", "child": "delay_records", "key": "station_code", "cardinality": "1 : N", "meaning": "A station logs many delay records"},
    {"parent": "trains", "child": "delay_remarks", "key": "train_no", "cardinality": "1 : N", "meaning": "A train can have many text remarks"},
    {"parent": "stations", "child": "delay_remarks", "key": "station_code", "cardinality": "0..1 : N", "meaning": "A remark may mention a station"},
]


def er_diagram_mermaid() -> str:
    """Mermaid erDiagram generated from the SQLAlchemy models."""
    from src.database.schema import Base

    lines = ["erDiagram"]
    for table in Base.metadata.sorted_tables:
        lines.append(f"    {table.name} {{")
        for col in table.columns:
            typ = type(col.type).__name__.lower()
            tag = " PK" if col.primary_key else (" FK" if col.foreign_keys else "")
            lines.append(f"        {typ} {col.name}{tag}")
        lines.append("    }")
    lines += [
        '    stations ||--o{ trains : "starts / ends"',
        '    trains ||--o{ train_stops : "has stops"',
        '    stations ||--o{ train_stops : "is stop"',
        '    trains ||--o{ delay_records : "logs"',
        '    stations ||--o{ delay_records : "records"',
        '    trains ||--o{ delay_remarks : "remarks"',
        '    stations |o--o{ delay_remarks : "mentioned"',
    ]
    return "\n".join(lines)


PREDEFINED_QUERIES = {
    "top_delayed_trains": ("Top 10 most delayed trains", lambda e: queries.top_delayed_trains(e)),
    "worst_stations": ("Worst 10 stations by average delay", lambda e: queries.worst_stations(e)),
    "monthly_avg_delay": ("Monthly average delay", lambda e: queries.monthly_avg_delay(e)),
    "avg_delay_by_train_type": ("Average delay by train type", lambda e: queries.avg_delay_by_train_type(e)),
    "avg_delay_by_zone": ("Average delay by zone", lambda e: queries.avg_delay_by_zone(e)),
    "avg_delay_by_season": ("Average delay by season", lambda e: queries.avg_delay_by_season(e)),
    "avg_delay_by_weather": ("Average delay by weather", lambda e: queries.avg_delay_by_weather(e)),
    "ontime_performance": ("On-time performance per train", lambda e: queries.ontime_performance(e)),
    "common_delay_reasons": ("Delay reasons from text remarks", lambda e: queries.common_delay_reasons(e)),
}


def _capture_sql(fn):
    """Run a query function and return (DataFrame, SQL text it executed)."""
    from sqlalchemy import event

    engine = _get_engine()
    seen = []

    def grab(conn, cursor, statement, parameters, context, executemany):
        seen.append(statement)

    event.listen(engine, "before_cursor_execute", grab)
    try:
        df = fn(engine)
    finally:
        event.remove(engine, "before_cursor_execute", grab)
    sql = next((s for s in seen if s.lstrip().upper().startswith("SELECT")), seen[-1] if seen else "")
    return df, _pretty_sql(sql)


def _pretty_sql(sql: str) -> str:
    for kw in ["FROM", "JOIN", "LEFT JOIN", "WHERE", "GROUP BY", "ORDER BY", "LIMIT"]:
        sql = re.sub(rf"\s+(?<!LEFT ){kw}\b", "\n" + kw, sql)
    return sql.replace("\nJOIN", "\n  JOIN").strip()


def list_predefined_queries() -> list:
    def build():
        out = []
        for name, (label, fn) in PREDEFINED_QUERIES.items():
            _, sql = _capture_sql(fn)
            out.append({"name": name, "label": label, "sql": sql})
        return out
    return _cached("query_list", build)


def run_predefined_query(name: str) -> dict:
    if name not in PREDEFINED_QUERIES:
        raise ValueError(f"Unknown query: {name}")
    df, sql = _capture_sql(PREDEFINED_QUERIES[name][1])
    return to_jsonable({"name": name, "sql": sql, "columns": list(df.columns), "rows": df.round(2).head(500)})


_FORBIDDEN_SQL = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex|trigger)\b", re.I)


def run_select_query(sql: str, limit: int = 500) -> dict:
    """Run a single read-only SELECT. Opens SQLite in read-only mode as a second safety net."""
    stmt = (sql or "").strip().rstrip(";").strip()
    if not stmt:
        raise ValueError("Type a SELECT query.")
    if ";" in stmt:
        raise ValueError("Only one statement is allowed.")
    if not re.match(r"^(select|with)\b", stmt, re.I):
        raise ValueError("Only SELECT queries are allowed.")
    if _FORBIDDEN_SQL.search(stmt):
        raise ValueError("Only read-only SELECT queries are allowed.")
    with sqlite3.connect(f"file:{_db_path()}?mode=ro", uri=True) as conn:
        try:
            cur = conn.execute(stmt)
        except sqlite3.Error as e:
            raise ValueError(f"SQL error: {e}") from None
        cols = [c[0] for c in cur.description or []]
        rows = cur.fetchmany(limit + 1)
    truncated = len(rows) > limit
    return to_jsonable({"sql": stmt, "columns": cols, "rows": [dict(zip(cols, r)) for r in rows[:limit]], "truncated": truncated})


DOWNLOADABLE_DIRS = {"excel": "outputs/excel", "processed": "data/processed", "reports": "outputs/reports"}


def list_downloads() -> list:
    root = _project_root()
    out = []
    for group, rel in DOWNLOADABLE_DIRS.items():
        folder = root / rel
        if not folder.exists():
            continue
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix in (".xlsx", ".csv", ".json"):
                out.append({"group": group, "name": p.name, "path": f"{rel}/{p.name}", "size_kb": round(p.stat().st_size / 1024, 1)})
    return out


LAB_CHARTS = {
    "01_monthly_avg_delay": ("Monthly average delay", "Lab 6 · Visualisation"),
    "02_delay_histogram": ("Delay distribution", "Lab 6 · Visualisation"),
    "03_delay_kde_by_train_type": ("Delay distribution by train type (KDE)", "Lab 6 · Visualisation"),
    "04_delay_by_season": ("Delay by season", "Lab 6 · Visualisation"),
    "05_delay_by_train_type": ("Delay by train type", "Lab 6 · Visualisation"),
    "06_top_delayed_trains": ("Top 10 most delayed trains", "Lab 5 · SQL analysis"),
    "07_worst_stations": ("Worst 10 stations", "Lab 5 · SQL analysis"),
    "08_zone_by_year": ("Average delay by zone per year", "Lab 6 · Visualisation"),
    "09_stacked_delay_categories": ("Delay categories by train type", "Lab 6 · Visualisation"),
    "10_pie_delay_categories": ("Delay category share", "Lab 6 · Visualisation"),
    "11_donut_delay_reasons": ("Delay reasons from remarks", "Lab 1 · Unstructured data"),
    "12_heatmap_month_year": ("Month × year heatmap", "Lab 6 · Visualisation"),
    "13_correlation_heatmap": ("Correlation matrix", "Lab 6 · Visualisation"),
    "14_scatter_distance_delay": ("Distance vs delay", "Lab 6 · Visualisation"),
    "15_delay_accumulation": ("Delay accumulation along route", "Lab 6 · Visualisation"),
    "ts_decomposition": ("Time-series decomposition", "Lab 7 · Time series"),
}


def list_lab_charts() -> list:
    config = load_config()
    folder = _project_root() / config["paths"]["charts_dir"]
    if not folder.exists():
        return []
    out = []
    for p in sorted(folder.glob("*.png")):
        title, lab = LAB_CHARTS.get(p.stem, (p.stem.replace("_", " ").title(), "Lab outputs"))
        out.append({"file": p.name, "title": title, "lab": lab})
    return out


def ui_plan_journey(**p) -> dict:
    """JSON wrapper around plan_journey; dates and times are ISO strings."""
    from src import planner

    travel_date = _date.fromisoformat(p["travel_date"])
    leave_after = _time.fromisoformat(p["leave_after"]) if p.get("leave_after") else None
    try:
        r = plan_journey(
            to_code=p["to_code"], travel_date=travel_date, from_code=p.get("from_code") or None,
            train_no=int(p["train_no"]) if p.get("train_no") else None,
            train_type=p.get("train_type") or None, leave_after=leave_after,
        )
    except planner.PlannerError as e:
        return {"error": str(e)}
    opts = r["options"].copy()
    yours = r["your_train"]
    return to_jsonable({**{k: v for k, v in r.items() if k not in ("options", "your_train")},
                        "your_train": yours, "options": opts})
