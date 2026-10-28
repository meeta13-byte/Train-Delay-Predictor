"""Analytical SQL queries over the railway database. Each returns a DataFrame."""

import pandas as pd
from sqlalchemy import text


def top_delayed_trains(engine, n: int = 10) -> pd.DataFrame:
    sql = text(
        "SELECT d.train_no, t.train_name, AVG(d.delay_minutes) AS avg_delay "
        "FROM delay_records d JOIN trains t ON d.train_no = t.train_no "
        "WHERE d.cancelled = 0 GROUP BY d.train_no, t.train_name ORDER BY avg_delay DESC LIMIT :n"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn, params={"n": n})


def worst_stations(engine, n: int = 10) -> pd.DataFrame:
    sql = text(
        "SELECT d.station_code, s.station_name, AVG(d.delay_minutes) AS avg_delay "
        "FROM delay_records d JOIN stations s ON d.station_code = s.station_code "
        "WHERE d.cancelled = 0 GROUP BY d.station_code, s.station_name ORDER BY avg_delay DESC LIMIT :n"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn, params={"n": n})


def monthly_avg_delay(engine) -> pd.DataFrame:
    sql = text(
        "SELECT strftime('%Y-%m', d.date) AS month, AVG(d.delay_minutes) AS avg_delay "
        "FROM delay_records d WHERE d.cancelled = 0 GROUP BY month ORDER BY month"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn)


def avg_delay_by_train_type(engine) -> pd.DataFrame:
    sql = text(
        "SELECT t.train_type, AVG(d.delay_minutes) AS avg_delay, COUNT(*) AS records "
        "FROM delay_records d JOIN trains t ON d.train_no = t.train_no "
        "WHERE d.cancelled = 0 GROUP BY t.train_type ORDER BY avg_delay DESC"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn)


def avg_delay_by_zone(engine) -> pd.DataFrame:
    sql = text(
        "SELECT t.zone, AVG(d.delay_minutes) AS avg_delay, COUNT(*) AS records "
        "FROM delay_records d JOIN trains t ON d.train_no = t.train_no "
        "WHERE d.cancelled = 0 GROUP BY t.zone ORDER BY avg_delay DESC"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn)


def avg_delay_by_season(engine) -> pd.DataFrame:
    sql = text(
        "SELECT CASE "
        "WHEN CAST(strftime('%m', d.date) AS INTEGER) IN (12,1,2) THEN 'Winter' "
        "WHEN CAST(strftime('%m', d.date) AS INTEGER) IN (3,4,5) THEN 'Summer' "
        "WHEN CAST(strftime('%m', d.date) AS INTEGER) IN (6,7,8) THEN 'Monsoon' "
        "ELSE 'Post-Monsoon' END AS season, "
        "AVG(d.delay_minutes) AS avg_delay, COUNT(*) AS records "
        "FROM delay_records d WHERE d.cancelled = 0 GROUP BY season ORDER BY avg_delay DESC"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn)


def avg_delay_by_weather(engine) -> pd.DataFrame:
    sql = text(
        "SELECT d.weather_condition, AVG(d.delay_minutes) AS avg_delay, COUNT(*) AS records "
        "FROM delay_records d WHERE d.cancelled = 0 GROUP BY d.weather_condition ORDER BY avg_delay DESC"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn)


def ontime_performance(engine) -> pd.DataFrame:
    sql = text(
        "SELECT t.train_no, t.train_name, "
        "AVG(CASE WHEN d.delay_minutes <= 15 THEN 1.0 ELSE 0 END) * 100 AS ontime_pct, "
        "COUNT(*) AS records FROM delay_records d JOIN trains t ON d.train_no = t.train_no "
        "WHERE d.cancelled = 0 GROUP BY t.train_no, t.train_name ORDER BY ontime_pct DESC"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn)


def delay_accumulation_by_stop(engine, train_no: int) -> pd.DataFrame:
    sql = text(
        "SELECT ts.train_no, ts.stop_sequence, ts.station_code, s.station_name, AVG(d.delay_minutes) AS avg_delay "
        "FROM train_stops ts JOIN delay_records d ON ts.train_no = d.train_no AND ts.station_code = d.station_code "
        "LEFT JOIN stations s ON ts.station_code = s.station_code "
        "WHERE ts.train_no = :train_no AND d.cancelled = 0 GROUP BY ts.train_no, ts.stop_sequence, ts.station_code, s.station_name "
        "ORDER BY ts.stop_sequence"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn, params={"train_no": train_no})


def common_delay_reasons(engine) -> pd.DataFrame:
    sql = text(
        "SELECT r.reason, COUNT(*) AS cnt, AVG(r.delay_minutes) AS avg_delay "
        "FROM delay_remarks r GROUP BY r.reason ORDER BY cnt DESC"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn)


def monthly_series_with_filters(engine, train_no: int = None, zone: str = None, train_type: str = None) -> pd.DataFrame:
    """Monthly average delay; optional filters on train_no / zone / train_type."""
    conditions = []
    params = {}
    if train_no is not None:
        conditions.append("d.train_no = :train_no")
        params["train_no"] = train_no
    if zone is not None:
        conditions.append("t.zone = :zone")
        params["zone"] = zone
    if train_type is not None:
        conditions.append("t.train_type = :train_type")
        params["train_type"] = train_type
    where = "".join(" AND " + c for c in conditions)
    sql = text(
        "SELECT strftime('%Y-%m', d.date) AS month, AVG(d.delay_minutes) AS avg_delay "
        "FROM delay_records d JOIN trains t ON d.train_no = t.train_no "
        "WHERE d.cancelled = 0" + where + " GROUP BY month ORDER BY month"
    )
    with engine.begin() as conn:
        return pd.read_sql(sql.text, conn, params=params)
