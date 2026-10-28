"""Journey planner: predict a train's delay and suggest better trains on the same route.

For a trip From -> To on a date, every train that stops at From and later at To
is compared on *expected* arrival (timetable + predicted delay), so a train that
leaves later, or usually runs late, can still be the better choice.

Delay prediction uses the train's own history at that station for the same
month, adjusted for the day of the week. If there is no history for the train,
the average for its category on that corridor is used instead.
"""

from datetime import date, datetime, time, timedelta

import pandas as pd
from sqlalchemy import text

ON_TIME_MINUTES = 15
MIN_SAMPLE = 8
# Only suggest trains leaving at most this long before the user's train.
EARLIER_WINDOW_MINUTES = 120


class PlannerError(ValueError):
    """Raised for user-facing input problems (unknown train, wrong route...)."""


# ---------------------------------------------------------------- data access

def _load_timetable(engine) -> pd.DataFrame:
    sql = (
        "SELECT ts.train_no, ts.stop_sequence, ts.station_code, ts.scheduled_arrival, "
        "ts.scheduled_departure, ts.day, ts.distance_from_source_km, "
        "t.train_name, t.train_type, t.source_station_code, t.destination_station_code, "
        "s.station_name "
        "FROM train_stops ts JOIN trains t ON ts.train_no = t.train_no "
        "LEFT JOIN stations s ON ts.station_code = s.station_code"
    )
    with engine.begin() as conn:
        df = pd.read_sql(sql, conn)
    df["day"] = pd.to_numeric(df["day"], errors="coerce").fillna(1).astype(int)
    df["arr_min"] = df["scheduled_arrival"].map(_hhmm_to_min) + (df["day"] - 1) * 1440
    dep = df["scheduled_departure"].map(_hhmm_to_min)
    # a departure earlier on the clock than the arrival rolled over midnight
    dep_day = df["day"] + (dep < df["scheduled_arrival"].map(_hhmm_to_min)).astype(int)
    df["dep_min"] = dep + (dep_day - 1) * 1440
    return df


def _load_history(engine, station_code: str, train_nos) -> pd.DataFrame:
    train_nos = [int(t) for t in train_nos]
    if not train_nos:
        return pd.DataFrame(columns=["train_no", "date", "delay_minutes", "cancelled"])
    placeholders = ", ".join(f":t{i}" for i in range(len(train_nos)))
    sql = text(
        "SELECT train_no, date, delay_minutes, cancelled FROM delay_records "
        f"WHERE station_code = :station AND train_no IN ({placeholders})"
    )
    params = {"station": station_code, **{f"t{i}": t for i, t in enumerate(train_nos)}}
    with engine.begin() as conn:
        df = pd.read_sql(sql, conn, params=params)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["cancelled"] = df["cancelled"].astype(bool)
    return df.dropna(subset=["date"])


def _hhmm_to_min(value) -> int:
    s = str(value).strip()
    # tolerate full timestamps as well as 'HH:MM'
    s = s.split(" ")[-1]
    h, m = s.split(":")[:2]
    return int(h) * 60 + int(m)


# ---------------------------------------------------------------- prediction

def _predict_from_history(hist: pd.DataFrame, travel_date: date) -> dict:
    """Summarise historical delays into a prediction for `travel_date`."""
    if hist.empty:
        return None
    running = hist[~hist["cancelled"]]
    if running.empty:
        return None
    delays = running["delay_minutes"]
    month = running[running["date"].dt.month == travel_date.month]
    sample = month if len(month) >= MIN_SAMPLE else running

    # day-of-week effect, measured on the whole history so it is stable
    wd = running[running["date"].dt.dayofweek == travel_date.weekday()]["delay_minutes"]
    overall = delays.clip(lower=0).median()
    ratio = (wd.clip(lower=0).median() / overall) if overall > 0 and len(wd) >= MIN_SAMPLE else 1.0
    ratio = float(min(max(ratio, 0.7), 1.5))

    s = sample["delay_minutes"] * ratio
    month_all = hist[hist["date"].dt.month == travel_date.month]
    cancel_pool = month_all if len(month_all) >= MIN_SAMPLE else hist
    return {
        "expected_delay": round(float(s.median()), 0),
        "likely_low": round(float(s.quantile(0.2)), 0),
        "likely_high": round(float(s.quantile(0.8)), 0),
        "worst_case": round(float(s.quantile(0.95)), 0),
        "on_time_pct": round(float((s <= ON_TIME_MINUTES).mean() * 100), 1),
        "cancel_pct": round(float(cancel_pool["cancelled"].mean() * 100), 1),
        "sample_size": int(len(sample)),
        "weekday_factor": round(ratio, 2),
        "based_on": "this train, same month" if sample is month else "this train, all months",
    }


def predict_delays(engine, station_code: str, trains: pd.DataFrame, travel_date: date) -> dict:
    """Return {train_no: prediction} at `station_code` for each train in `trains`.

    Trains without history fall back to all trains of the same category here.
    """
    hist = _load_history(engine, station_code, trains["train_no"].tolist())
    type_of = dict(zip(trains["train_no"].astype(int), trains["train_type"]))
    hist["train_type"] = hist["train_no"].map(type_of)
    out = {}
    for train_no in trains["train_no"].astype(int):
        pred = _predict_from_history(hist[hist["train_no"] == train_no], travel_date)
        if pred is None:
            pred = _predict_from_history(hist[hist["train_type"] == type_of[train_no]], travel_date)
            if pred is not None:
                pred["based_on"] = f"other {type_of[train_no]} trains at this station"
        out[train_no] = pred
    return out


# ---------------------------------------------------------------- planner

def _fmt_dur(minutes: float) -> str:
    minutes = int(round(abs(minutes)))
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    return f"{h}h" if h else f"{m} min"


def _fmt_dt(dt: datetime, travel_date: date) -> str:
    s = dt.strftime("%H:%M")
    days = (dt.date() - travel_date).days
    return s + (f" (+{days}d)" if days > 0 else "")


def route_options(engine, from_code: str, to_code: str) -> pd.DataFrame:
    """All trains that stop at `from_code` and later at `to_code`."""
    tt = _load_timetable(engine)
    a = tt[tt["station_code"] == from_code]
    b = tt[tt["station_code"] == to_code][["train_no", "stop_sequence", "arr_min", "station_name"]]
    m = a.merge(b, on="train_no", suffixes=("_from", "_to"))
    m = m[m["stop_sequence_to"] > m["stop_sequence_from"]].copy()
    m["run_minutes"] = m["arr_min_to"] - m["dep_min"]
    return m.rename(columns={"station_name_from": "from_name", "station_name_to": "to_name"})


def plan_journey(
    engine,
    to_code: str,
    travel_date: date,
    from_code: str = None,
    train_no: int = None,
    train_type: str = None,
    leave_after: time = None,
) -> dict:
    """Predict the delay of the chosen train and rank every train on the route.

    Pass either `train_no` (your train) or just `train_type` (the kind of train
    you'd take). `from_code` defaults to the starting station of `train_no`.
    """
    tt = _load_timetable(engine)
    to_code = to_code.strip().upper()
    if from_code:
        from_code = from_code.strip().upper()

    chosen = None
    if train_no:
        train_no = int(train_no)
        stops = tt[tt["train_no"] == train_no].sort_values("stop_sequence")
        if stops.empty:
            raise PlannerError(f"Train {train_no} is not in the timetable.")
        chosen = stops.iloc[0]
        # the train number wins over a category picked by mistake
        train_type = chosen["train_type"]
        from_code = from_code or chosen["source_station_code"]
        codes = stops["station_code"].tolist()
        if from_code not in codes or to_code not in codes or codes.index(from_code) >= codes.index(to_code):
            raise PlannerError(
                f"{train_no} {chosen['train_name']} does not run {from_code} → {to_code}. "
                f"Its stops are: {' → '.join(codes)}."
            )
    if not from_code:
        raise PlannerError("Choose a boarding station (From), or enter a train number.")

    options = route_options(engine, from_code, to_code)
    if options.empty:
        raise PlannerError(f"No train in the timetable runs {from_code} → {to_code}.")

    start_of_day = datetime.combine(travel_date, time(0, 0))
    options["sched_dep"] = options["dep_min"].map(lambda m: start_of_day + timedelta(minutes=int(m % 1440)))
    options["sched_arr"] = options["sched_dep"] + pd.to_timedelta(options["run_minutes"], unit="m")
    if leave_after is not None:
        cutoff = datetime.combine(travel_date, leave_after)
        keep = options["sched_dep"] >= cutoff
        if train_no:
            keep |= options["train_no"] == train_no
        options = options[keep]
        if options.empty:
            raise PlannerError(f"No train leaves {from_code} for {to_code} after {leave_after.strftime('%H:%M')}.")

    pred_to = predict_delays(engine, to_code, options, travel_date)
    pred_from = predict_delays(engine, from_code, options, travel_date)

    rows = []
    for _, o in options.iterrows():
        tn = int(o["train_no"])
        p_to, p_from = pred_to.get(tn) or {}, pred_from.get(tn) or {}
        d_to = p_to.get("expected_delay", 0.0)
        d_from = max(p_from.get("expected_delay", 0.0), 0.0)
        exp_dep = o["sched_dep"] + timedelta(minutes=d_from)
        exp_arr = o["sched_arr"] + timedelta(minutes=d_to)
        rows.append({
            "train_no": tn,
            "train_name": o["train_name"],
            "train_type": o["train_type"],
            "sched_dep": o["sched_dep"],
            "sched_arr": o["sched_arr"],
            "expected_dep": exp_dep,
            "expected_arr": exp_arr,
            "delay_at_from": d_from,
            "delay_at_to": d_to,
            "likely_low": p_to.get("likely_low"),
            "likely_high": p_to.get("likely_high"),
            "worst_case": p_to.get("worst_case"),
            "on_time_pct": p_to.get("on_time_pct"),
            "cancel_pct": p_to.get("cancel_pct"),
            "based_on": p_to.get("based_on", "no history"),
            "journey_minutes": (exp_arr - exp_dep).total_seconds() / 60,
        })
    table = pd.DataFrame(rows).sort_values(["expected_arr", "sched_dep"]).reset_index(drop=True)

    # reference train: the one asked for, else the best of the chosen category
    if train_no:
        ref = table[table["train_no"] == train_no].iloc[0]
    elif train_type and (table["train_type"] == train_type).any():
        ref = table[table["train_type"] == train_type].iloc[0]
    else:
        ref = None

    table["badges"] = [[] for _ in range(len(table))]
    _add_badges(table)
    suggestions = _suggestions(table, ref, to_code, travel_date) if ref is not None else []

    from_name = options.iloc[0]["from_name"] or from_code
    to_name = options.iloc[0]["to_name"] or to_code
    return {
        "from_code": from_code,
        "to_code": to_code,
        "from_name": from_name,
        "to_name": to_name,
        "travel_date": travel_date,
        "your_train": ref.to_dict() if ref is not None else None,
        "options": table,
        "suggestions": suggestions,
    }


def _add_badges(table: pd.DataFrame) -> None:
    first = table["expected_arr"].idxmin()
    table.at[first, "badges"].append("Earliest arrival")
    fastest = table["journey_minutes"].idxmin()
    table.at[fastest, "badges"].append("Shortest journey")
    if table["on_time_pct"].notna().any():
        punctual = table["on_time_pct"].idxmax()
        table.at[punctual, "badges"].append("Most punctual")


def _suggestions(table: pd.DataFrame, ref, to_code: str, travel_date: date) -> list:
    """Plain-language tips comparing other trains with the reference train."""
    tips = []
    for _, r in table.iterrows():
        if r["train_no"] == ref["train_no"]:
            continue
        gain = (ref["expected_arr"] - r["expected_arr"]).total_seconds() / 60
        later = (r["sched_dep"] - ref["sched_dep"]).total_seconds() / 60
        name = f"{r['train_no']} {r['train_name']} ({r['train_type']})"
        dep = r["sched_dep"].strftime("%H:%M")
        arr = _fmt_dt(r["expected_arr"], travel_date)

        if later >= 15 and gain >= 10:
            kind = "leave_later_arrive_earlier"
            text_ = (f"Leave later, arrive earlier: {name} leaves at {dep}, {_fmt_dur(later)} after your train, "
                     f"but is expected at {to_code} at {arr}, {_fmt_dur(gain)} earlier.")
        elif later >= 30 and abs(gain) < 10:
            kind = "leave_later_same_arrival"
            text_ = (f"Same arrival, more time at home: {name} leaves at {dep}, {_fmt_dur(later)} after your train, "
                     f"and still reaches {to_code} at about the same time ({arr}).")
        elif gain >= 10 and r["delay_at_to"] > ref["delay_at_to"] + 10:
            kind = "late_but_earlier"
            text_ = (f"Late but still earlier: {name} usually runs about {_fmt_dur(r['delay_at_to'])} late, "
                     f"yet is still expected at {to_code} {_fmt_dur(gain)} before your train ({arr}).")
        elif gain >= 10 and later >= -EARLIER_WINDOW_MINUTES:
            kind = "arrives_earlier"
            when = (f"leaves {_fmt_dur(later)} before yours ({dep})" if later < 0 else f"leaves at {dep}")
            text_ = f"Arrives earlier: {name} {when} and is expected at {to_code} at {arr}, {_fmt_dur(gain)} before your train."
        else:
            continue
        if later < -EARLIER_WINDOW_MINUTES:
            continue
        tips.append({"train_no": int(r["train_no"]), "kind": kind, "gain_minutes": round(gain), "text": text_})

    order = {"leave_later_arrive_earlier": 0, "leave_later_same_arrival": 1, "late_but_earlier": 2, "arrives_earlier": 3}
    tips.sort(key=lambda t: (order[t["kind"]], -t["gain_minutes"]))
    return tips
