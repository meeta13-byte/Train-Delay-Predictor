import streamlit as st
import sys
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.components.layout import page_container, navbar, footer
from app.components.cards import kpi_tile, battery_meter
from src import api
from src.planner import PlannerError
from app.theme import apply_theme
import plotly.graph_objects as go

st.set_page_config(page_title="Journey Planner - RailPulse", page_icon="🚂", layout="wide", initial_sidebar_state="collapsed")
page_container()
navbar()

st.markdown("## Journey Planner")
st.markdown("Enter your train or the kind of train you want. We predict how late it will be and check whether another train on the same route would get you there sooner.")

TRAIN_TYPES = ["Vande Bharat", "Shatabdi", "Rajdhani", "Duronto", "Superfast", "Mail/Express", "Passenger"]


def _fmt_dur(minutes):
    minutes = int(round(abs(minutes)))
    h, m = divmod(minutes, 60)
    return f"{h}h {m}m" if h else f"{m} min"


def _fmt_time(dt, travel_date):
    days = (dt.date() - travel_date).days
    return dt.strftime("%H:%M") + (f" (+{days}d)" if days > 0 else "")


try:
    trains = api.list_trains()
    stations = api.list_stations()
    stops = api.list_train_stops()
except Exception as e:
    st.error(f"Error: {e}")
    st.info("Run the pipeline first: `python main.py`")
    st.stop()

station_label = {r.station_code: f"{r.station_name} ({r.station_code})" for r in stations.itertuples()}
served = [c for c in station_label if c in set(stops["station_code"])]
train_label = {int(r.train_no): f"{r.train_no} - {r.train_name} ({r.train_type})" for r in trains.itertuples()}

with st.form("planner"):
    c1, c2 = st.columns(2)
    with c1:
        train_choice = st.selectbox(
            "Train number", [None] + sorted(train_label), format_func=lambda t: "Any train" if t is None else train_label[t],
            help="Leave as 'Any train' to search by category instead.",
        )
    with c2:
        type_choice = st.selectbox("Train category", [None] + TRAIN_TYPES, format_func=lambda t: "Any" if t is None else t,
                                   help="Used when no train number is chosen.")
    c3, c4, c5, c6 = st.columns(4)
    with c3:
        from_code = st.selectbox("From", [None] + served, format_func=lambda c: "Train's starting station" if c is None else station_label[c])
    with c4:
        to_code = st.selectbox("To (destination)", served, index=served.index("BPL") if "BPL" in served else 0, format_func=lambda c: station_label[c])
    with c5:
        travel_date = st.date_input("Date of travel", value=date.today())
    with c6:
        leave_after = st.time_input("Earliest I can leave", value=time(0, 0), step=900,
                                    help="Only show trains leaving at or after this time.")
    submitted = st.form_submit_button("Predict & compare", type="primary")

if not submitted:
    st.info("Pick a train (or a category and a From station), a destination and a date, then press **Predict & compare**.")
    footer()
    st.stop()

if train_choice is None and from_code is None:
    st.warning("Choose a From station when searching by category.")
    footer()
    st.stop()

try:
    result = api.plan_journey(
        to_code=to_code, travel_date=travel_date, from_code=from_code, train_no=train_choice,
        train_type=type_choice, leave_after=leave_after if leave_after != time(0, 0) else None,
    )
except PlannerError as e:
    st.warning(str(e))
    footer()
    st.stop()

if train_choice is not None and type_choice and type_choice != trains.set_index("train_no").loc[train_choice, "train_type"]:
    st.caption(f"Note: {train_label[train_choice]} is not a {type_choice} train; using the train number.")

options = result["options"]
yours = result["your_train"]
st.markdown(f"### {result['from_name']} → {result['to_name']} · {travel_date.strftime('%a %d %b %Y')}")

# ---- your train
if yours is not None:
    label = "Your train" if train_choice is not None else f"Best {yours['train_type']} train"
    st.markdown(f"#### {label}: {yours['train_no']} {yours['train_name']}")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_tile("Expected delay at destination", f"{yours['delay_at_to']:.0f} min")
    with k2:
        kpi_tile("Expected arrival", _fmt_time(yours["expected_arr"], travel_date))
    with k3:
        kpi_tile("Likely range", f"{yours['likely_low']:.0f}–{yours['likely_high']:.0f} min")
    with k4:
        battery_meter("Chance of on-time (≤15 min)", yours["on_time_pct"] or 0)
    st.caption(
        f"Scheduled {yours['sched_dep'].strftime('%H:%M')} → {_fmt_time(yours['sched_arr'], travel_date)}. "
        f"Expected at {result['from_code']} around {_fmt_time(yours['expected_dep'], travel_date)}. "
        f"Bad-day delay (95th percentile): {yours['worst_case']:.0f} min · cancellation rate {yours['cancel_pct']:.1f}%. "
        f"Based on: {yours['based_on']}."
    )
elif type_choice:
    st.info(f"No {type_choice} train runs on this route. Here are all the trains that do.")

# ---- suggestions
st.markdown("#### Suggestions")
if yours is None:
    best = options.iloc[0]
    st.success(f"Earliest expected arrival: {best['train_no']} {best['train_name']}, leaves {best['sched_dep'].strftime('%H:%M')}, "
               f"expected at {result['to_code']} at {_fmt_time(best['expected_arr'], travel_date)}.")
elif result["suggestions"]:
    for tip in result["suggestions"][:5]:
        st.success(tip["text"])
else:
    st.success("Your train is already the best option on this route for the time you want to leave.")

# ---- comparison chart: scheduled vs expected trip per train
fig = go.Figure()
order = options.iloc[::-1]
names = [f"{r.train_no} {r.train_name}" for r in order.itertuples()]
fig.add_trace(go.Bar(
    y=names, x=[(r.sched_arr - r.sched_dep).total_seconds() * 1000 for r in order.itertuples()],
    base=list(order["sched_dep"]), orientation="h", name="Timetable", marker_color="#B6C4F8",
    hovertemplate="%{y}<br>Scheduled %{base|%H:%M} → %{x}<extra></extra>",
))
fig.add_trace(go.Scatter(
    y=names, x=list(order["expected_arr"]), mode="markers", name="Expected arrival",
    marker=dict(color="#FB7B1B", size=12, symbol="diamond"),
    hovertemplate="%{y}<br>Expected arrival %{x|%H:%M}<extra></extra>",
))
fig.update_layout(title="When each train leaves and when it should really arrive", xaxis_title="Time", xaxis_type="date",
                  height=120 + 45 * len(options), barmode="overlay", legend=dict(orientation="h", y=-0.2))
apply_theme(fig)
st.plotly_chart(fig, use_container_width=True)

# ---- full table
table = options.assign(
    Train=options["train_no"].astype(str) + " " + options["train_name"],
    Category=options["train_type"],
    Departs=options["sched_dep"].map(lambda d: d.strftime("%H:%M")),
    **{
        "Scheduled arrival": options["sched_arr"].map(lambda d: _fmt_time(d, travel_date)),
        "Expected delay": options["delay_at_to"].map(lambda m: f"{m:.0f} min"),
        "Expected arrival": options["expected_arr"].map(lambda d: _fmt_time(d, travel_date)),
        "Journey": options["journey_minutes"].map(_fmt_dur),
        "On-time chance": options["on_time_pct"].map(lambda p: "–" if p is None else f"{p:.0f}%"),
        "Highlights": options["badges"].map(", ".join),
    },
)[["Train", "Category", "Departs", "Scheduled arrival", "Expected delay", "Expected arrival", "Journey", "On-time chance", "Highlights"]]
st.markdown("#### All trains on this route (sorted by expected arrival)")
st.dataframe(table, hide_index=True, use_container_width=True)
st.caption("Predictions use simulated historical delay data for the same month and day of the week. They are estimates, not live running status.")

footer()
