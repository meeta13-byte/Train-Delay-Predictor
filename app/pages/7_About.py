import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.components.layout import page_container, navbar, footer

st.set_page_config(page_title="About - RailPulse", page_icon="🚂", layout="wide", initial_sidebar_state="collapsed")
page_container()
navbar()

st.markdown("## About")

st.markdown("### Project Title")
st.write("Indian Railways Train Delay Analysis and Forecasting System")

st.markdown("### Problem Statement")
st.write("Indian Railways runs thousands of passenger trains daily, and delays are frequent. This project builds a Python-based analytics pipeline that reads, cleans, analyzes and forecasts train delays.")

st.markdown("### Objectives")
st.write("1. Multi-format data ingestion\n2. Data cleaning and preprocessing\n3. Relational data model with SQL database\n4. Analytical SQL queries\n5. Visualizations\n6. Time-series forecasting with ARIMA")

st.markdown("### Tech Stack")
st.write("Python, pandas, numpy, matplotlib, seaborn, plotly, statsmodels, SQLAlchemy, openpyxl, scikit-learn")

st.markdown("### Note")
st.write("Data is simulated for academic purposes. UI built with Streamlit following the RailPulse design system.")

footer()
