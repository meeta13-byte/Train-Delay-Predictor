import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.components.layout import page_container, navbar, footer
import json

st.set_page_config(page_title="Data Pipeline - RailPulse", page_icon="🚂", layout="wide", initial_sidebar_state="collapsed")
page_container()
navbar()

st.markdown("## Data Pipeline")

with st.expander("1. Collection (Structured & Unstructured)", expanded=True):
    st.write("**Structured:** CSV, JSON, XML | **Unstructured:** TXT")
    col1, col2 = st.columns(2)
    with col1:
        st.write("Raw files in data/raw/")
    with col2:
        try:
            with open('data/raw/delay_remarks.txt') as f:
                st.code(f.read())
        except:
            pass

with st.expander("2. Cleaning"):
    try:
        with open('outputs/reports/cleaning_report.json') as f:
            report = json.load(f)
        st.json(report)
    except:
        st.info("Run pipeline to see cleaning report")

with st.expander("3. Database"):
    try:
        from src.database.db_loader import get_engine
        engine = get_engine()
        st.write("**Connection:** SQLite (data/railway.db)")
        for t in ['stations','trains','train_stops','delay_records','delay_remarks']:
            cnt = engine.execute(f"SELECT COUNT(*) FROM {t}").scalar()
            st.write(f"- {t}: {cnt} rows")
    except Exception as e:
        st.write(e)

with st.expander("4. Downloads"):
    for p in ['outputs/excel/railway_cleaned_data.xlsx', 'outputs/reports/forecast_next_3_months.csv']:
        if Path(p).exists():
            with open(p, 'rb') as f:
                st.download_button(f"Download {Path(p).name}", f.read(), Path(p).name)

footer()
