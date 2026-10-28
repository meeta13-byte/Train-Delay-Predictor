import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.components.layout import page_container, navbar, footer

st.set_page_config(page_title="Lab Outputs - RailPulse", page_icon="🚂", layout="wide", initial_sidebar_state="collapsed")
page_container()
navbar()

st.markdown("## Lab Outputs - Charts Gallery")

charts_dir = Path('outputs/charts')
if charts_dir.exists():
    charts = sorted(charts_dir.glob('*.png'))
    cols = st.columns(3)
    for i, chart in enumerate(charts):
        with cols[i % 3]:
            st.image(str(chart), use_container_width=True)
            st.caption(chart.name)
else:
    st.info("Run the pipeline to generate charts: `python main.py`")

footer()
