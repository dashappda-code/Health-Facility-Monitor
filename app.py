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
    .block-container { padding-top: 0.8rem; padding-bottom: 1rem; }

    .global-filter-heading {
        background: linear-gradient(90deg, #eaf4ff, #f8fbff);
        border: 1px solid #c9dced;
        border-left: 5px solid #1769aa;
        border-radius: 12px;
        padding: 9px 14px;
        margin: 8px 0 8px 0;
    }
    .global-filter-title { font-size: 19px; font-weight: 750; color: #123b5d; }
    .global-filter-subtitle { font-size: 12px; color: #607080; margin-top: 2px; }

    /* Keep the filter form visually prominent while scrolling. */
    div[data-testid="stForm"] {
        border: 1px solid #d7e3ef;
        border-radius: 12px;
        padding: 7px 9px 9px 9px;
        background: rgba(255,255,255,0.98);
        box-shadow: 0 3px 12px rgba(30,60,90,0.08);
    }

    div[data-testid="stFormSubmitButton"] button {
        border-radius: 8px;
        font-weight: 700;
    }

    div[data-testid="stMultiSelect"] label,
    div[data-testid="stDateInput"] label {
        font-size: 12px;
        font-weight: 650;
    }

    [data-testid="stMetric"] { padding: 7px 10px; }
    section[data-testid="stSidebar"] { width: 250px; }

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


@st.cache_data(ttl=60, show_spinner="Loading programme data...")
def get_data():
    return load_data()


df = get_data()

if df is None or df.empty:
    st.error("No data available from the Google Sheet.")
    st.info(
        "Please verify that the Google Sheet is shared as 'Anyone with the link - Viewer' "
        "and that the configured worksheet GID is correct."
    )
    st.stop()

# ------------------------------------------------------------
# Sidebar navigation only. Filters are handled once globally
# by phase2_overview.create_filters().
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# ONE global filter -> ONE filtered dataframe
# ------------------------------------------------------------
filter_values = create_filters(df)

filtered_df = apply_filters(df=df, **filter_values)

st.caption(f"📊 Filtered Records: **{len(filtered_df):,}** / **{len(df):,}**")

# Management KPI strip
kpis = calculate_kpis(filtered_df)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Records", f"{kpis.get('total_records', len(filtered_df)):,}")
with c2:
    st.metric("Diseases", f"{kpis.get('diseases', 0):,}")
with c3:
    st.metric("Facilities", f"{kpis.get('facilities', 0):,}")
with c4:
    st.metric("Wards", f"{kpis.get('wards', 0):,}")

st.divider()

# ------------------------------------------------------------
# Existing dashboard sections - do not duplicate filters here.
# ------------------------------------------------------------
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

st.markdown(
    """
    <div class="dashboard-footer">
        Health Programme Management Dashboard |
        Live Google Sheet Based Monitoring System
    </div>
    """,
    unsafe_allow_html=True,
)

