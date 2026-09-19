import streamlit as st

from phase1_data import load_data
from phase2_overview import (
    create_filters,
    apply_filters,
    render_overview,
)

from phase3_charts import render_charts
from phase4_demographics import render_demographics
from phase5_ward import render_ward_analysis
from phase6_map import render_map
from phase7_explorer import render_explorer
from phase8_prediction import render_prediction
from phase9_manual import render_manual
from phase10_validation_kpi import render_validation_kpi
from phase11_drilldown_export import render_drilldown_export


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
# LOAD DATA FROM GOOGLE SHEETS
# ============================================================

try:

    df = load_data()

except Exception as error:

    st.error(
        "Unable to load data from Google Sheets."
    )

    st.exception(error)

    st.stop()


# ============================================================
# SIDEBAR HEADER
# ============================================================

st.sidebar.title(
    "🏥 Health Facility Monitor"
)

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


# ============================================================
# GLOBAL DASHBOARD CONTROLS
# ============================================================
#
# IMPORTANT:
# Dashboard Controls are created ONLY ONCE here.
#
# Do NOT create filters again inside individual modules.
#
# The same filtered dataframe will be sent to every page.
# ============================================================

filters = create_filters(df)


# ============================================================
# APPLY GLOBAL FILTERS
# ============================================================

filtered_df = apply_filters(
    df,
    **filters
)


# ============================================================
# GLOBAL FILTER STATUS
# ============================================================

st.sidebar.divider()

st.sidebar.markdown(
    "### 📊 Current Data View"
)

st.sidebar.metric(
    "Filtered Records",
    f"{len(filtered_df):,}"
)

st.sidebar.caption(
    f"Total available records: {len(df):,}"
)


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.divider()

page = st.sidebar.radio(
    "📌 Navigation",
    [
        "Overview",
        "📊 Management KPI & Validation",
        "Charts & Trends",
        "Demographics & Disease",
        "Ward Analysis",
        "Map View",
        "Data Explorer",
        "Prediction",
        "🔎 Detailed Drill-down",
        "📘 User Manual",
    ],
)


# ============================================================
# PAGE ROUTING
# ============================================================
#
# Every page receives filtered_df.
#
# Therefore:
#
# Year filter
# Month filter
# Disease filter
# Facility filter
# Ward filter
# Gender filter
# Age Group filter
# OPD/IPD filter
# Area filter
# Status filter
# Date filter
#
# all work across the selected page.
# ============================================================


if page == "Overview":

    render_overview(
        filtered_df
    )


elif page == "📊 Management KPI & Validation":

    render_validation_kpi(
        filtered_df
    )


elif page == "Charts & Trends":

    render_charts(
        filtered_df
    )


elif page == "Demographics & Disease":

    render_demographics(
        filtered_df
    )


elif page == "Ward Analysis":

    render_ward_analysis(
        filtered_df
    )


elif page == "Map View":

    render_map(
        filtered_df
    )


elif page == "Data Explorer":

    render_explorer(
        filtered_df
    )


elif page == "Prediction":

    render_prediction(
        filtered_df
    )


elif page == "🔎 Detailed Drill-down":

    render_drilldown_export(
        filtered_df
    )


elif page == "📘 User Manual":

    render_manual(
        filtered_df
    )


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
