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
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Health Programme Management Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# GLOBAL STYLING
# ============================================================

st.markdown(
    """
    <style>

    /* -------------------------------------------------------
       MAIN PAGE
       ------------------------------------------------------- */

    .block-container {
        padding-top: 0.8rem;
        padding-bottom: 1rem;
    }


    /* -------------------------------------------------------
       GLOBAL FILTER HEADING
       ------------------------------------------------------- */

    .global-filter-heading {
        background: linear-gradient(
            90deg,
            #eaf4ff,
            #f8fbff
        );

        border: 1px solid #c9dced;

        border-left: 5px solid #1769aa;

        border-radius: 12px;

        padding: 9px 14px;

        margin: 0 0 8px 0;
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


    /* -------------------------------------------------------
       STICKY GLOBAL FILTER
       
       The complete Global Dashboard Control container
       remains visible while the page is scrolled.
       ------------------------------------------------------- */

    div[data-testid="stVerticalBlock"]:has(
        .global-filter-heading
    ) {
        position: sticky;

        top: 0.25rem;

        z-index: 999;

        background: rgba(
            255,
            255,
            255,
            0.98
        );

        border-radius: 12px;

        padding: 5px 5px 7px 5px;

        box-shadow:
            0 4px 14px
            rgba(
                30,
                60,
                90,
                0.12
            );

        backdrop-filter: blur(6px);

        -webkit-backdrop-filter: blur(6px);
    }


    /* -------------------------------------------------------
       FILTER CONTAINER
       ------------------------------------------------------- */

    div[data-testid="stVerticalBlock"]:has(
        .global-filter-heading
    ) div[data-testid="stMultiSelect"] label,

    div[data-testid="stVerticalBlock"]:has(
        .global-filter-heading
    ) div[data-testid="stDateInput"] label {

        font-size: 12px;

        font-weight: 650;
    }


    /* -------------------------------------------------------
       MULTISELECT BOX
       ------------------------------------------------------- */

    div[data-testid="stVerticalBlock"]:has(
        .global-filter-heading
    ) div[data-baseweb="select"] {

        min-height: 38px;
    }


    /* -------------------------------------------------------
       RESET BUTTON
       ------------------------------------------------------- */

    div[data-testid="stVerticalBlock"]:has(
        .global-filter-heading
    ) div[data-testid="stButton"] button {

        border-radius: 8px;

        font-weight: 700;

        min-height: 34px;
    }


    /* -------------------------------------------------------
       DATE INPUT
       ------------------------------------------------------- */

    div[data-testid="stVerticalBlock"]:has(
        .global-filter-heading
    ) div[data-testid="stDateInput"] input {

        font-size: 13px;
    }


    /* -------------------------------------------------------
       KPI
       ------------------------------------------------------- */

    [data-testid="stMetric"] {
        padding: 7px 10px;
    }


    /* -------------------------------------------------------
       SIDEBAR
       ------------------------------------------------------- */

    section[data-testid="stSidebar"] {
        width: 250px;
    }


    /* -------------------------------------------------------
       FOOTER
       ------------------------------------------------------- */

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


# ============================================================
# DASHBOARD HEADER
# ============================================================

st.title(
    "🏥 Health Programme Management Dashboard"
)

st.caption(
    "Live Google Sheet Based Programme Monitoring System"
)


# ============================================================
# DATA LOADING
# ============================================================

def get_data():
    return load_data()


df = get_data()


# ============================================================
# DATA VALIDATION
# ============================================================

if df is None or df.empty:

    st.error(
        "No data available from the Google Sheet."
    )

    st.info(
        "Please verify that the Google Sheet is shared as "
        "'Anyone with the link - Viewer' and that the "
        "configured worksheet GID is correct."
    )

    st.stop()


# ============================================================
# SIDEBAR MENU
# ============================================================

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


# ============================================================
# GLOBAL FILTERS
# ============================================================

filter_values = create_filters(df)


# ============================================================
# APPLY FILTERS
# ============================================================

filtered_df = apply_filters(
    df=df,
    **filter_values,
)


# ============================================================
# FILTERED RECORD COUNT
# ============================================================

st.caption(
    f"📊 Filtered Records: "
    f"**{len(filtered_df):,}** / **{len(df):,}**"
)


# ============================================================
# GLOBAL KPI
# ============================================================

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


# ============================================================
# DASHBOARD SECTIONS
# ============================================================

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
