import streamlit as st


def filter_bar():
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            date_range = st.date_input("Date Range", value=[], key="date_range")
        with col2:
            zone = st.multiselect("Zone", ["NR", "CR", "NFR", "SBC", "ER"], key="zone_filter")
        with col3:
            train_type = st.multiselect("Train Type", ["Rajdhani", "Shatabdi", "Vande Bharat", "Superfast", "Mail/Express", "Passenger"], key="train_type_filter")
        with col4:
            season = st.multiselect("Season", ["Winter", "Summer", "Monsoon", "Post-Monsoon"], key="season_filter")
    return {"date_range": date_range, "zone": zone, "train_type": train_type, "season": season}
