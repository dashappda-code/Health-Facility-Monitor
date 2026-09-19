```python
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
    <h1 style="margin-bottom:0;">
        🏥 Health Programme Management Dashboard
    </h1>
    <p style="
        margin-top:4px;
        color:#666;
        font-size:14px;
    ">
        Live Google Sheet Based Programme Monitoring System
    </p>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD DATA
# ============================================================

try:

    df = load_data()

except Exception as e:

    st.error(
        "❌ Google Sheet data loading failed."
    )

    st.exception(e)

    st.stop()


if df is None or df.empty:

    st.error(
        "❌ Google Sheet मधून data उपलब्ध नाही."
    )

    st.stop()


# ============================================================
# SIDEBAR
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
            "Validation & KPI",
            "Drill-down & Export",
            "User Manual",
        ],
    )

    st.markdown("---")

    st.caption(
        f"Total records: {len(df):,}"
    )


# ============================================================
# CREATE FILTER VALUES
# ============================================================

filter_values = create_filters(
    df
)


# ============================================================
# FILTER VALUES
# ============================================================

selected_years = filter_values.get(
    "selected_years",
    filter_values.get("years", [])
)

selected_months = filter_values.get(
    "selected_months",
    filter_values.get("months", [])
)

selected_weeks = filter_values.get(
    "selected_weeks",
    filter_values.get("weeks", [])
)

selected_diseases = filter_values.get(
    "selected_diseases",
    filter_values.get("diseases", [])
)

selected_facilities = filter_values.get(
    "selected_facilities",
    filter_values.get("facilities", [])
)

selected_wards = filter_values.get(
    "selected_wards",
    filter_values.get("wards", [])
)

selected_genders = filter_values.get(
    "selected_genders",
    filter_values.get("genders", [])
)

selected_age_groups = filter_values.get(
    "selected_age_groups",
    filter_values.get("age_groups", [])
)

selected_opd_ipd = filter_values.get(
    "selected_opd_ipd",
    filter_values.get("opd_ipd", [])
)

selected_areas = filter_values.get(
    "selected_areas",
    filter_values.get("areas", [])
)

selected_status = filter_values.get(
    "selected_status",
    filter_values.get("status", [])
)

area_column = filter_values.get(
    "area_column",
    "Patient Address"
)

status_column = filter_values.get(
    "status_column",
    "Confirmed Diagnosis"
)

date_from = filter_values.get(
    "date_from"
)

date_to = filter_values.get(
    "date_to"
)


# ============================================================
# APPLY FILTERS
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
# SIMPLE STATUS BAR
# ============================================================

c1, c2 = st.columns(2)

with c1:

    st.metric(
        "Total Records",
        f"{len(df):,}"
    )

with c2:

    st.metric(
        "Selected Records",
        f"{len(filtered_df):,}"
    )


# ============================================================
# PAGE
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

        render_ward_analysis(
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

    elif page == "Validation & KPI":

        render_validation_kpi(
            filtered_df
        )

    elif page == "Drill-down & Export":

        render_drilldown_export(
            filtered_df
        )

    elif page == "User Manual":

        render_manual()


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
```
