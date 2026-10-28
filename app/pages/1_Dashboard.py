import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.components.layout import page_container, navbar, footer
from app.components.cards import kpi_tile, battery_meter
from app.components.filters import filter_bar
from app.components.charts import plot_monthly_trend, plot_train_type_bar, plot_delay_category_donut, plot_month_year_heatmap
from src import api
from app.theme import apply_theme

st.set_page_config(page_title="Dashboard - RailPulse", page_icon="🚂", layout="wide", initial_sidebar_state="collapsed")

page_container()
navbar()

st.markdown("## Dashboard")
st.markdown("Overview of train delays across Indian Railways")

filters = filter_bar()

try:
    kpi = api.get_summary_kpis()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_tile("Total Records", f"{kpi['total_records']:,}")
    with col2:
        kpi_tile("Average Delay", f"{kpi['avg_delay_overall']:.1f} min")
    with col3:
        battery_meter("On-time Performance", kpi['ontime_pct'])
    with col4:
        kpi_tile("Most Delayed", f"{kpi['most_delayed_train_avg']:.1f} min")
    
    st.markdown("<div style='margin-top:40px;'></div>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        with st.container():
            monthly = api.get_monthly_series()
            if not monthly.empty:
                fig = plot_monthly_trend(monthly)
                st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        with st.container():
            by_type = api.get_top_delayed_trains()
            if not by_type.empty:
                fig = plot_train_type_bar(by_type.rename(columns={'avg_delay': 'avg_delay'}))
                st.plotly_chart(fig, use_container_width=True)
    
    col_left2, col_right2 = st.columns(2)
    
    with col_left2:
        with st.container():
            delays = api.get_filtered_delays({})
            if not delays.empty:
                fig = plot_delay_category_donut(delays)
                st.plotly_chart(fig, use_container_width=True)
    
    with col_right2:
        with st.container():
            delays = api.get_filtered_delays({})
            if not delays.empty and 'year' in delays.columns and 'month' in delays.columns:
                heat = delays.groupby(['year','month'])['delay_minutes'].mean().reset_index(name='avg_delay')
                fig = plot_month_year_heatmap(heat)
                st.plotly_chart(fig, use_container_width=True)
    
except Exception as e:
    st.error(f"Error loading dashboard: {e}")
    st.info("Make sure the database is generated. Run: `python main.py`")

footer()
