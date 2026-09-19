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
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Health Programme Management Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div style="
        padding: 8px 0 14px 0;
        border-bottom: 1px solid #dddddd;
        margin-bottom: 12px;
    ">
        <h1 style="
            margin:0;
            padding:0;
        ">
            🏥 Health Programme Management Dashboard
        </h1>

        <div style="
            font-size:15px;
            margin-top:7px;
            color:#555;
        ">
            Live Google Sheet Based Programme Monitoring System
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATA
# ============================================================

try:
    df = load_data()

except Exception as e:

    st.error("❌ Google Sheet data loading failed.")

    st.exception(e)

    st.stop()


if df is None or df.empty:

    st.error(
        "❌ Google Sheet मधून data उपलब्ध नाही."
    )

    st.stop()


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:

    st.markdown(
        "## 🏥 Programme Dashboard"
    )

    st.markdown("---")

    page = st.radio(
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
        key="dashboard_page",
    )

    st.markdown("---")

    st.metric(
        "Total Records",
        f"{len(df):,}"
    )

    st.caption(
        "Live Google Sheet Data"
    )


# ============================================================
# GLOBAL DASHBOARD CONTROL
# ============================================================

st.markdown(
    """
    <div style="
        background:#f8f9fa;
        border:1px solid #d9d9d9;
        border-radius:8px;
        padding:12px 14px 4px 14px;
        margin-bottom:14px;
    ">
        <h3 style="
            margin:0 0 8px 0;
            font-size:19px;
        ">
            🎛️ Global Dashboard Control
        </h3>
        <div style="
            font-size:13px;
            color:#666;
            margin-bottom:8px;
        ">
            Select filters below. The selected data will be used across dashboard sections.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CREATE FILTER OPTIONS
# ============================================================

filter_values = create_filters(df)


# ============================================================
# HELPER
# ============================================================

def get_filter_value(primary, secondary, default=None):

    value = filter_values.get(primary)

    if value is None:
        value = filter_values.get(secondary)

    if value is None:
        value = default

    return value


# ============================================================
# FILTER VALUES
# ============================================================

selected_years = get_filter_value(
    "selected_years",
    "years",
    [],
)

selected_months = get_filter_value(
    "selected_months",
    "months",
    [],
)

selected_weeks = get_filter_value(
    "selected_weeks",
    "weeks",
    [],
)

selected_diseases = get_filter_value(
    "selected_diseases",
    "diseases",
    [],
)

selected_facilities = get_filter_value(
    "selected_facilities",
    "facilities",
    [],
)

selected_wards = get_filter_value(
    "selected_wards",
    "wards",
    [],
)

selected_genders = get_filter_value(
    "selected_genders",
    "genders",
    [],
)

selected_age_groups = get_filter_value(
    "selected_age_groups",
    "age_groups",
    [],
)

selected_opd_ipd = get_filter_value(
    "selected_opd_ipd",
    "opd_ipd",
    [],
)

selected_areas = get_filter_value(
    "selected_areas",
    "areas",
    [],
)

selected_status = get_filter_value(
    "selected_status",
    "status",
    [],
)

area_column = filter_values.get(
    "area_column",
    "Patient Address",
)

status_column = filter_values.get(
    "status_column",
    "Confirmed Diagnosis",
)

date_from = filter_values.get(
    "date_from"
)

date_to = filter_values.get(
    "date_to"
)


# ============================================================
# APPLY GLOBAL FILTER
# ============================================================

try:

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

except TypeError:

    # Compatibility with versions where apply_filters
    # does not accept selected_years.

    filtered_df = apply_filters(
        df=df,
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

st.markdown(
    """
    <div style="
        background:#eef6ff;
        border:1px solid #cfe2ff;
        border-radius:6px;
        padding:8px 12px;
        margin-bottom:15px;
        font-size:14px;
    ">
        <b>Dashboard Status:</b>
        Global filter applied to the selected dashboard section.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# RECORD SUMMARY
# ============================================================

c1, c2, c3 = st.columns(3)

with c1:

    st.metric(
        "Total Records",
        f"{len(df):,}",
    )

with c2:

    st.metric(
        "Selected Records",
        f"{len(filtered_df):,}",
    )

with c3:

    if len(df) > 0:

        percentage = (
            len(filtered_df) / len(df)
        ) * 100

        st.metric(
            "Selected %",
            f"{percentage:.1f}%",
        )

    else:

        st.metric(
            "Selected %",
            "0%",
        )


# ============================================================
# PAGE CONTENT
# ============================================================

try:

    # --------------------------------------------------------
    # PHASE 2
    # --------------------------------------------------------

    if page == "Overview":

        render_overview(
            filtered_df
        )


    # --------------------------------------------------------
    # PHASE 3
    # --------------------------------------------------------

    elif page == "Charts & Trends":

        render_charts(
            filtered_df
        )


    # --------------------------------------------------------
    # PHASE 4
    # --------------------------------------------------------

    elif page == "Demographics":

        render_demographics(
            filtered_df
        )


    # --------------------------------------------------------
    # PHASE 5
    # --------------------------------------------------------

    elif page == "Ward Analysis":

        render_ward_analysis(
            filtered_df
        )


    # --------------------------------------------------------
    # PHASE 6
    # --------------------------------------------------------

    elif page == "Map":

        render_map(
            filtered_df
        )


    # --------------------------------------------------------
    # PHASE 7
    # --------------------------------------------------------

    elif page == "Data Explorer":

        render_explorer(
            filtered_df
        )


    # --------------------------------------------------------
    # PHASE 8
    # --------------------------------------------------------

    elif page == "Prediction":

        render_prediction(
            filtered_df
        )


    # --------------------------------------------------------
    # PHASE 9
    # --------------------------------------------------------

    elif page == "User Manual":

        render_manual()


    # --------------------------------------------------------
    # PHASE 10
    # --------------------------------------------------------

    elif page == "Validation & KPI":

        render_validation_kpi(
            filtered_df
        )


    # --------------------------------------------------------
    # PHASE 11
    # --------------------------------------------------------

    elif page == "Drill-down & Export":

        render_drilldown_export(
            filtered_df
        )


except Exception as e:

    st.error(
        f"❌ Error while loading section: {page}"
    )

    st.exception(e)


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Health Programme Management Dashboard | "
    "Live Google Sheet Data"
)
