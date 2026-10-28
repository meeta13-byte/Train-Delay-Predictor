import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.components.layout import page_container, navbar, footer
from src import api
from app.theme import apply_theme
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Delay Analysis - RailPulse", page_icon="🚂", layout="wide", initial_sidebar_state="collapsed")
page_container()
navbar()

st.markdown("## Delay Analysis")
try:
    delays = api.get_filtered_delays({}, limit=None)
    trains = api.list_trains()
    if not delays.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.histogram(delays, x="delay_minutes", nbins=30, title="Delay Minutes Distribution")
            apply_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.box(delays.merge(trains[['train_no','train_type']], on='train_no', how='left'), x="train_type", y="delay_minutes", title="Delay by Train Type")
            apply_theme(fig)
            st.plotly_chart(fig, use_container_width=True)
        
        selected = st.selectbox("Select Train for Route Analysis", trains['train_no'].unique())
        try:
            from src.database import queries
            from src.database.db_loader import get_engine
            acc = queries.delay_accumulation_by_stop(get_engine(), train_no=int(selected))
            if not acc.empty:
                fig = px.line(acc, x="station_code", y="avg_delay", title="Delay Accumulation Along Route", markers=True,
                              labels={"station_code": "Station (in route order)", "avg_delay": "Average delay (min)"})
                apply_theme(fig)
                st.plotly_chart(fig, use_container_width=True)
        except:
            pass
    else:
        st.info("No delay data available.")
except Exception as e:
    st.error(f"Error: {e}")

footer()
