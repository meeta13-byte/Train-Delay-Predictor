import streamlit as st
from pathlib import Path


def inject_css():
    css_path = Path(__file__).parent.parent / "styles.css"
    if css_path.exists():
        css = css_path.read_text()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def navbar(active="home"):
    logo_path = Path(__file__).parent.parent / "assets" / "logo.svg"
    logo_svg = logo_path.read_text() if logo_path.exists() else ""
    nav_html = f"""
    <div class="navbar">
        <div class="navbar-brand">
            <div style="width:40px;height:40px;">{logo_svg}</div>
            <span>RailPulse</span>
        </div>
        <div class="navbar-links">
            <a href="/" class="navbar-link">Home</a>
            <a href="/Journey_Planner" class="navbar-link">Plan Journey</a>
            <a href="/Dashboard" class="navbar-link">Dashboard</a>
            <a href="/Delay_Analysis" class="navbar-link">Delays</a>
            <a href="/Stations" class="navbar-link">Stations</a>
            <a href="/Forecast" class="navbar-link">Forecast</a>
            <a href="/Data_Pipeline" class="navbar-link">Data Pipeline</a>
            <a href="/About" class="navbar-link">About</a>
        </div>
    </div>
    """
    st.markdown(nav_html, unsafe_allow_html=True)


def page_container():
    inject_css()


def footer():
    st.markdown(
        """
    <div style="text-align:center;padding:40px 0 20px 0;color:var(--text-muted);font-size:13px;">
        <div style="font-family:Montserrat, sans-serif;font-weight:600;color:var(--text-strong);margin-bottom:8px;">RailPulse</div>
        <div>Academic DAV mini-project • Data is simulated for academic purposes</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
