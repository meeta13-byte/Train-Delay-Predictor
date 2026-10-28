import streamlit as st
from pathlib import Path


def icon_blob(icon_name="chart"):
    icon_path = Path(__file__).parent.parent / "assets" / "icons" / f"{icon_name}.svg"
    icon_svg = icon_path.read_text() if icon_path.exists() else ""
    html = f"""
    <div class="icon-blob">
        <div style="width:32px;height:32px;">{icon_svg}</div>
    </div>
    """
    return html


def feature_card(title, description, icon="chart"):
    html = f"""
    <div class="feature-card">
        {icon_blob(icon)}
        <div class="feature-card-title">{title}</div>
        <div class="feature-card-desc">{description}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def kpi_tile(label, value, trend=None, trend_type="up"):
    trend_html = ""
    if trend:
        color = "#2EAD7A" if trend_type == "up" else "#E5484D"
        arrow = "▲" if trend_type == "up" else "▼"
        trend_html = f'<div class="kpi-trend" style="color:{color};">{arrow} {trend}</div>'
    html = f"""
    <div class="kpi-tile">
        <div class="kpi-icon-blob"></div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {trend_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def battery_meter(label, percentage):
    pct = max(0, min(100, percentage))
    html = f"""
    <div class="kpi-tile">
        <div class="kpi-icon-blob"></div>
        <div class="kpi-label">{label}</div>
        <div class="battery-meter">
            <div class="battery-shell">
                <div class="battery-fill" style="width:{pct}%"></div>
            </div>
            <div class="battery-text">{pct:.1f}%</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def info_card(label, value):
    html = f"""
    <div class="floating-card">
        <div class="floating-card-label">{label}</div>
        <div class="floating-card-value">{value}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
