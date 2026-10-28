import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.components.layout import page_container, navbar, footer
from src import api
from app.theme import apply_theme
import plotly.graph_objects as go

st.set_page_config(page_title="Forecast - RailPulse", page_icon="🚂", layout="wide", initial_sidebar_state="collapsed")
page_container()
navbar()

st.markdown("## Delay Forecast")
try:
    result = api.run_forecast(steps=3)
    series = result['series']
    fc = result['forecast']
    metrics = result['metrics']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("MAE", f"{metrics['mae']:.2f}")
    col2.metric("RMSE", f"{metrics['rmse']:.2f}")
    col3.metric("Forecast Steps", "3 months")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=series.index, y=series.values, mode='lines', name='History', line=dict(color='#6E7FE6', width=3)))
    fig.add_trace(go.Scatter(x=fc['forecast'].index, y=fc['forecast'].values, mode='lines', name='Forecast', line=dict(color='#FB7B1B', width=3, dash='dash')))
    fig.update_layout(title="ARIMA(1,1,1) Forecast - Next 3 Months", xaxis_title="Month", yaxis_title="Average Delay (min)")
    apply_theme(fig)
    st.plotly_chart(fig, use_container_width=True)
    
    forecast_df = fc['forecast'].reset_index()
    forecast_df.columns = ['Month', 'Forecast Delay (min)']
    st.dataframe(forecast_df)
    
    if Path('outputs/reports/forecast_next_3_months.csv').exists():
        with open('outputs/reports/forecast_next_3_months.csv') as f:
            st.download_button("Download Forecast CSV", f.read(), "forecast_next_3_months.csv", "text/csv")
except Exception as e:
    st.error(f"Error: {e}")
    st.info("Run the pipeline first: `python main.py`")

footer()
