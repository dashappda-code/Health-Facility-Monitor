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


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="MSU Mumbai Public Health Surveillance Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# DASHBOARD STYLING
# =========================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 0.65rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }

    section[data-testid="stSidebar"] {
        width: 250px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border: 1px solid rgba(120, 140, 160, 0.35) !important;
        padding: 10px 12px 8px 12px !important;
        margin-top: 4px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    }

    div[data-testid="stMultiSelect"] label,
    div[data-testid="stDateInput"] label {
        font-size: 11px !important;
        font-weight: 650 !important;
        margin-bottom: 2px !important;
    }

    div[data-testid="stMultiSelect"] > div,
    div[data-testid="stDateInput"] > div {
        min-height: 36px !important;
    }

    div[data-testid="stMultiSelect"] [data-baseweb="select"] {
        min-height: 36px !important;
        border-radius: 7px !important;
    }

    div[data-testid="stDateInput"] input {
        min-height: 34px !important;
        border-radius: 7px !important;
    }

    .st-key-global_reset_filters button {
        min-height: 36px !important;
        border-radius: 7px !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 0.55rem !important;
    }

    [data-testid="stMetric"] {
        padding: 7px 10px !important;
    }

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


# =========================================================
# DASHBOARD HEADER
# =========================================================

st.title(
    "🏥 MSU Mumbai Public Health Surveillance Dashboard"
)

st.caption(
    "Surveillance • Monitoring • Analysis • Management"
)


# =========================================================
# DATA LOADING
# =========================================================

def get_data():
    return load_data()


df = get_data()


if df is None or df.empty:

    st.error(
        "No data available from the Google Sheet."
    )

    st.info(
        "Please verify that the Google Sheet is shared as "
        "'Anyone with the link - Viewer' and that the configured "
        "worksheet GID is correct."
    )

    st.stop()


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title(
    "📌 Dashboard Menu"
)


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


# =========================================================
# GLOBAL DASHBOARD CONTROL
# =========================================================

st.subheader(
    "🎛️ Global Dashboard Control"
)

st.caption(
    "Select any filter to update the entire dashboard immediately. "
    "Leave filters blank to include all records."
)


with st.container(
    border=True,
    key="global_filter_panel",
):

    filter_values = create_filters(
        df
    )


# =========================================================
# APPLY GLOBAL FILTERS
# =========================================================

filtered_df = apply_filters(
    df=df,
    **filter_values,
)


st.caption(
    f"📊 Filtered Records: "
    f"**{len(filtered_df):,}** / "
    f"**{len(df):,}**"
)


# =========================================================
# GLOBAL KPI
# =========================================================

kpis = calculate_kpis(
    filtered_df
)


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


# =========================================================
# DASHBOARD SECTIONS
# =========================================================

try:

    if page == "Overview":

        render_overview(
            filtered_df
        )

    elif page == "Charts & Trends":

        render_charts(
            filtered_df
        )

    elif page == "Demographics":

        render_demographics(
            filtered_df
        )

    elif page == "Ward Analysis":

        render_ward(
            filtered_df
        )

    elif page == "Map":

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

    elif page == "User Manual":

        render_manual()

    elif page == "Validation & KPI":

        render_validation_kpi(
            filtered_df
        )

    elif page == "Drill-down & Export":

        render_drilldown_export(
            filtered_df
        )


except Exception as e:

    st.error(
        "This dashboard section could not be loaded."
    )

    st.exception(e)


# =========================================================
# REFRESH GOOGLE SHEET DATA
# =========================================================

st.sidebar.markdown("---")


if st.sidebar.button(
    "🔄 Refresh Google Sheet Data",
    use_container_width=True,
):

    with st.spinner(
        "Refreshing Google Sheet data..."
    ):

        from phase1_data import refresh_data

        refresh_data()

    st.success(
        "Google Sheet data refreshed successfully."
    )

    st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="dashboard-footer">
        MSU Mumbai Public Health Surveillance Dashboard |
        Surveillance • Monitoring • Analysis • Management
    </div>
    """,
    unsafe_allow_html=True,
)
