import streamlit as st

from phase1_data import load_data
from phase2_overview import render_overview
from phase3_charts import render_charts
from phase4_demographics import render_demographics
from phase5_ward import render_ward_analysis
from phase6_map import render_map
from phase7_explorer import render_explorer
from phase8_prediction import render_prediction
from phase9_manual import render_manual


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Health Facility Monitor",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# LOAD DATA
# ============================================================

try:
    df = load_data()

except Exception as error:
    st.error("Unable to load data from Google Sheets.")
    st.exception(error)
    st.stop()


# ============================================================
# SIDEBAR HEADER
# ============================================================

st.sidebar.title("🏥 Health Facility Monitor")

st.sidebar.caption(
    "Public Health Surveillance Dashboard"
)

st.sidebar.divider()


# ============================================================
# DATA STATUS
# ============================================================

try:

    total_records = len(df)

    st.sidebar.success(
        f"🟢 Data Loaded\n\n"
        f"Records: {total_records:,}"
    )

except Exception:

    st.sidebar.info(
        "🟢 Data source connected"
    )


st.sidebar.divider()


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

page = st.sidebar.radio(
    "📌 Navigation",
    [
        "Overview",
        "Charts & Trends",
        "Demographics & Disease",
        "Ward Analysis",
        "Map View",
        "Data Explorer",
        "Prediction",
        "📘 User Manual",
    ],
)


# ============================================================
# PAGE ROUTING
# ============================================================

if page == "Overview":

    render_overview(df)


elif page == "Charts & Trends":

    render_charts(df)


elif page == "Demographics & Disease":

    render_demographics(df)


elif page == "Ward Analysis":

    render_ward_analysis(df)


elif page == "Map View":

    render_map(df)


elif page == "Data Explorer":

    render_explorer(df)


elif page == "Prediction":

    render_prediction(df)


elif page == "📘 User Manual":

    render_manual(df)


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "📊 Interactive Programme Monitoring System"
)

st.sidebar.caption(
    "Data Source: Live Google Sheets"
)


st.divider()

st.caption(
    "Health Facility Monitor | "
    "Live Google Sheets Data Source | "
    "For Programme Monitoring & Management Support"
)
