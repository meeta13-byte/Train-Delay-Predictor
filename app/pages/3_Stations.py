import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.components.layout import page_container, navbar, footer
from src import api
from app.theme import apply_theme
import plotly.express as px

st.set_page_config(page_title="Stations - RailPulse", page_icon="🚂", layout="wide", initial_sidebar_state="collapsed")
page_container()
navbar()

st.markdown("## Stations Analysis")
try:
    stations = api.get_station_delays()
    if not stations.empty:
        fig = px.bar(stations.head(10), x="avg_delay", y="station_name", orientation='h', title="Worst 10 Stations by Average Delay")
        apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(stations, use_container_width=True)
    else:
        st.info("No station data available.")
except Exception as e:
    st.error(f"Error: {e}")

footer()
