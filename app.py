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


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Health Programme Management Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SIMPLE CSS - LIGHTWEIGHT
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    [data-testid="stMetric"] {
        padding: 8px 10px;
    }

    section[data-testid="stSidebar"] {
        width: 250px;
    }

    .dashboard-footer {
        text-align:center;
        color:#777;
        font-size:12px;
        padding-top:20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.title("🏥 Health Programme Management Dashboard")
st.caption("Live Google Sheet Based Programme Monitoring System")


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data(ttl=60, show_spinner="Loading programme data...")
def get_data():
    return load_data()


df = get_data()


# ============================================================
# DATA CHECK
# ============================================================

if df is None or df.empty:
    st.error("No data available from the Google Sheet.")
    st.info(
        "Please verify that the Google Sheet is shared as 'Anyone with the link - Viewer' "
        "and that the configured worksheet GID is correct."
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

st.sidebar.caption(f"Records loaded: {len(df):,}")


# ============================================================
# GLOBAL DASHBOARD CONTROL
# ============================================================

filter_values = create_filters(df)


# ============================================================
# EXTRACT FILTER VALUES
# ============================================================

selected_years = filter_values.get("selected_years", [])
selected_months = filter_values.get("selected_months", [])
selected_weeks = filter_values.get("selected_weeks", [])
selected_diseases = filter_values.get("selected_diseases", [])
selected_facilities = filter_values.get("selected_facilities", [])
selected_wards = filter_values.get("selected_wards", [])
selected_genders = filter_values.get("selected_genders", [])
selected_age_groups = filter_values.get("selected_age_groups", [])
selected_opd_ipd = filter_values.get("selected_opd_ipd", [])
selected_areas = filter_values.get("selected_areas", [])
selected_status = filter_values.get("selected_status", [])

area_column = filter_values.get("area_column")
status_column = filter_values.get("status_column")

date_from = filter_values.get("date_from")
date_to = filter_values.get("date_to")


# ============================================================
# APPLY GLOBAL FILTER
# ============================================================

filtered_df = apply_filters(
    df=df,
    selected_years=selected_years,
    selected_months=selected_months,
    selected_weeks=selected_weeks,
    selected_diseases=selected_diseases,
    selected_facilities=selected_facilities,
    selected_wards=selected_wards,
    selected_genders=selected_genders,
    selected_age_groups=selected_age_groups,
    selected_opd_ipd=selected_opd_ipd,
    selected_areas=selected_areas,
    selected_status=selected_status,
    area_column=area_column,
    status_column=status_column,
    date_from=date_from,
    date_to=date_to,
)


# ============================================================
# FILTER STATUS
# ============================================================

st.caption(
    f"📊 Filtered Records: **{len(filtered_df):,}** "
    f"/ {len(df):,}"
)


# ============================================================
# KPI STRIP
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
# PAGE ROUTING
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
    st.error("This dashboard section could not be loaded.")
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
