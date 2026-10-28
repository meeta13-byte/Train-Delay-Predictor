import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.components.layout import page_container, navbar, footer
from app.components.cards import feature_card, info_card
from src import api

st.set_page_config(page_title="RailPulse - Home", page_icon="🚂", layout="wide", initial_sidebar_state="collapsed")

page_container()
navbar()

# Hero Section
hero_col1, hero_col2 = st.columns([0.45, 0.55], gap="large")

with hero_col1:
    st.markdown(
        """
        <h1 class="hero-headline">Know when your train will run late, <span class="highlight">before it does</span></h1>
        <p class="hero-description">We collect, clean and analyse Indian Railways delay data from CSV, JSON, XML and text files, and forecast delays for the next 3 months.</p>
        """,
        unsafe_allow_html=True,
    )
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("Explore dashboard", type="primary"):
            st.switch_page("pages/1_Dashboard.py")
    with col_btn2:
        if st.button("See how it works"):
            st.switch_page("pages/5_Data_Pipeline.py")

with hero_col2:
    try:
        hero_svg = Path("app/assets/hero.svg").read_text()
        st.markdown(
            f"""
            <div class="hero-illustration">
                <div class="hero-blob"></div>
                <div class="hero-train">{hero_svg}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except:
        st.markdown('<div class="hero-illustration"><div class="hero-blob"></div></div>', unsafe_allow_html=True)
    try:
        kpi = api.get_summary_kpis()
        avg_delay = kpi.get('avg_delay_overall', 0)
        st.markdown(
            f"""
            <div class="floating-card" style="position:absolute;top:80px;right:60px;">
                <div class="floating-card-label">Avg delay overall</div>
                <div class="floating-card-value">{avg_delay:.1f} min</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except:
        pass

st.markdown("<div style='margin-top:80px;'></div>", unsafe_allow_html=True)
st.markdown("## Key insights")

try:
    kpi = api.get_summary_kpis()
    col1, col2, col3 = st.columns(3)
    with col1:
        train_name = kpi.get('most_delayed_train', 'N/A')[:30]
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="icon-blob"><div style="width:32px;height:32px;">🚂</div></div>
                <div class="feature-card-title">Most delayed train</div>
                <div class="feature-card-desc">{train_name}<br/>Avg: {kpi.get('most_delayed_train_avg', 0):.1f} min</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="icon-blob"><div style="width:32px;height:32px;">❄️</div></div>
                <div class="feature-card-title">Worst season</div>
                <div class="feature-card-desc">Winter (Fog)<br/>Highest delay impact</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        ontime = kpi.get('ontime_pct', 0)
        st.markdown(
            f"""
            <div class="feature-card">
                <div class="icon-blob"><div style="width:32px;height:32px;">⏱️</div></div>
                <div class="feature-card-title">On-time performance</div>
                <div class="feature-card-desc">{ontime:.1f}% trains ≤ 15 min late</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
except Exception as e:
    st.info("Run the pipeline first to see insights.")

st.markdown("<div style='margin-top:80px;'></div>", unsafe_allow_html=True)
st.markdown("## How it works")

steps = [
    ("Collect", "CSV, JSON, XML, TXT"),
    ("Clean", "Missing, duplicates, outliers"),
    ("Store", "SQL Database"),
    ("Analyse", "SQL Queries"),
    ("Visualise", "Charts & Dashboards"),
    ("Forecast", "ARIMA Time Series"),
]
cols = st.columns(6)
for i, (step, desc) in enumerate(steps):
    with cols[i]:
        st.markdown(
            f"""
            <div style="text-align:center;padding:20px;">
                <div style="width:60px;height:60px;background:var(--blob);border-radius:50%;margin:0 auto 12px;display:flex;align-items:center;justify-content:center;font-weight:600;">{i+1}</div>
                <div style="font-family:Montserrat,sans-serif;font-weight:600;color:var(--text-strong);margin-bottom:4px;">{step}</div>
                <div style="font-size:12px;color:var(--text-muted);">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

footer()
