import streamlit as st

from phase1_data import load_data
from phase2_overview import (
    create_filters,
    apply_filters,
    calculate_kpis,
    render_overview,
)
from phase3_charts import render_charts
from phase4_demographics import render_demographics
from phase5_ward import render_ward
from phase6_map import render_map
from phase7_explorer import render_explorer
from phase8_prediction import render_prediction
from phase9_manual import render_manual
from phase10_validation_kpi import render_validation_kpi
from phase11_drilldown_export import render_drilldown_export


st.set_page_config(
    page_title="Health Programme Management Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>

    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 1rem;
    }

    .global-filter-heading {
        background: linear-gradient(90deg, #eaf4ff, #f8fbff);
        border: 1px solid #c9dced;
        border-left: 5px solid #1769aa;
        border-radius: 12px;
        padding: 9px 14px;
        margin: 4px 0 7px 0;
    }

    .global-filter-title {
        font-size: 19px;
        font-weight: 750;
        color: #123b5d;
    }

    .global-filter-subtitle {
        font-size: 12px;
        color: #607080;
        margin-top: 2px;
    }

    /*
    ============================================================
    GLOBAL FILTER CONTAINER
    Excel-style sticky / freeze behaviour
    ============================================================
    */

    .st-key-global_filter_container {
        position: sticky;
        top: 0.25rem;
        z-index: 999;
        background: rgba(255, 255, 255, 0.98);
        border-radius: 12px;
        padding: 4px 4px 8px 4px;
        margin-bottom: 10px;
        box-shadow: 0 4px 16px rgba(30, 60, 90, 0.12);
        backdrop-filter: blur(5px);
    }

    /*
    ============================================================
    FILTER WIDGETS
    ============================================================
    */

    div[data-testid="stMultiSelect"] label,
    div[data-testid="stDateInput"] label {
        font-size: 12px;
        font-weight: 650;
    }

    div[data-testid="stMultiSelect"] {
        margin-bottom: 0;
    }

    div[data-testid="stDateInput"] {
        margin-bottom: 0;
    }

    /*
    ============================================================
    RESET BUTTON
    ============================================================
    */

    .st-key-global_reset_filters button {
        border-radius: 8px;
        font-weight: 700;
    }

    /*
    ============================================================
    KPI
    ============================================================
    */

    [data-testid="stMetric"] {
        padding: 7px 10px;
    }

    /*
    ============================================================
    SIDEBAR
    ============================================================
    */

    section[data-testid="stSidebar"] {
        width: 250px;
    }

    /*
    ============================================================
    FOOTER
    ============================================================
    */

    .dashboard-footer {
        text-align: center;
        color: #777;
        font-size: 12px;
        padding-top: 18px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


st.title("🏥 Health Programme Management Dashboard")
st.caption("Live Google Sheet Based Programme Monitoring System")


def get_data():
    return load_data()


df = get_data()


if df is None or df.empty:

    st.error("No data available from the Google Sheet.")

    st.info(
        "Please verify that the Google Sheet is shared as "
        "'Anyone with the link - Viewer' and that the configured "
        "worksheet GID is correct."
    )

    st.stop()


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

st.sidebar.title("📌 Dashboard Menu")


page = st.sidebar.radio(
    "Select Section",
    [
        "Overview",
        "Charts & Trends",
        "Demographics",
        "Ward Analysis",
        "Map",
        "Data Explorer",
        "Prediction",
        "User Manual",
        "Validation & KPI",
        "Drill-down & Export",
    ],
)


st.sidebar.divider()

st.sidebar.caption(
    f"Records loaded: {len(df):,}"
)


# ============================================================
# ONE GLOBAL FILTER
# ============================================================

filter_values = create_filters(df)


filtered_df = apply_filters(
    df=df,
    **filter_values,
)


st.caption(
    f"📊 Filtered Records: **{len(filtered_df):,}** / **{len(df):,}**"
)


# ============================================================
# MANAGEMENT KPI STRIP
# ============================================================

kpis = calculate_kpis(filtered_df)


c1, c2, c3, c4 = st.columns(4)


with c1:

    st.metric(
        "Total Records",
        f"{kpis.get('total_records', len(filtered_df)):,}",
    )


with c2:

    st.metric(
        "Diseases",
        f"{kpis.get('diseases', 0):,}",
    )


with c3:

    st.metric(
        "Facilities",
        f"{kpis.get('facilities', 0):,}",
    )


with c4:

    st.metric(
        "Wards",
        f"{kpis.get('wards', 0):,}",
    )


st.divider()


# ============================================================
# EXISTING DASHBOARD SECTIONS
# ============================================================

try:

    if page == "Overview":

        render_overview(filtered_df)

    elif page == "Charts & Trends":

        render_charts(filtered_df)

    elif page == "Demographics":

        render_demographics(filtered_df)

    elif page == "Ward Analysis":

        render_ward(filtered_df)

    elif page == "Map":

        render_map(filtered_df)

    elif page == "Data Explorer":

        render_explorer(filtered_df)

    elif page == "Prediction":

        render_prediction(filtered_df)

    elif page == "User Manual":

        render_manual()

    elif page == "Validation & KPI":

        render_validation_kpi(filtered_df)

    elif page == "Drill-down & Export":

        render_drilldown_export(filtered_df)


except Exception as e:

    st.error(
        "This dashboard section could not be loaded."
    )

    st.exception(e)


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="dashboard-footer">
        Health Programme Management Dashboard |
        Live Google Sheet Based Monitoring System
    </div>
    """,
    unsafe_allow_html=True,
)
