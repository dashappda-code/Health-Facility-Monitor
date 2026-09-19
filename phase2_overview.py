import pandas as pd
import streamlit as st

from phase1_data import refresh_data


# ============================================================
# CONSTANTS
# ============================================================

MONTH_ORDER = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

AGE_GROUP_ORDER = [
    "<1 Year",
    "1–4 Years",
    "5–14 Years",
    "15–24 Years",
    "25–44 Years",
    "45–59 Years",
    "60+ Years",
    "Unknown",
]


# ============================================================
# HELPERS
# ============================================================

def _unique(df, column):

    if column not in df.columns:
        return []

    return sorted(
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
        .replace(
            {
                "": pd.NA,
                "nan": pd.NA,
                "None": pd.NA,
                "NA": pd.NA,
                "N/A": pd.NA,
            }
        )
        .dropna()
        .unique()
        .tolist(),
        key=str
    )


def _reset_filter_state():

    st.session_state["filter_reset_version"] = (
        st.session_state.get(
            "filter_reset_version",
            0
        ) + 1
    )


def _create_age_group(age_series):

    age = pd.to_numeric(
        age_series,
        errors="coerce"
    )

    def classify(value):

        if pd.isna(value):
            return "Unknown"

        if value < 1:
            return "<1 Year"

        if value <= 4:
            return "1–4 Years"

        if value <= 14:
            return "5–14 Years"

        if value <= 24:
            return "15–24 Years"

        if value <= 44:
            return "25–44 Years"

        if value <= 59:
            return "45–59 Years"

        return "60+ Years"

    return age.apply(classify)


# ============================================================
# GLOBAL DASHBOARD FILTERS
# ============================================================

def create_filters(df):

    st.sidebar.divider()

    st.sidebar.subheader(
        "🎛️ Dashboard Controls"
    )

    st.sidebar.caption(
        "All selected filters apply to the complete dashboard."
    )

    # ========================================================
    # REFRESH / RESET
    # ========================================================

    refresh_col, reset_col = st.sidebar.columns(2)

    with refresh_col:

        if st.button(
            "🔄 Refresh",
            key="refresh_data_button",
            use_container_width=True,
            help="Reload latest data from Google Sheets"
        ):

            refresh_data()

            st.rerun()

    with reset_col:

        st.button(
            "↩️ Reset",
            key="reset_filters_button",
            use_container_width=True,
            help="Clear all dashboard filters",
            on_click=_reset_filter_state,
        )

    reset_version = st.session_state.get(
        "filter_reset_version",
        0
    )

    # ========================================================
    # YEAR
    # ========================================================

    years = []

    if "Year" in df.columns:

        year_series = pd.to_numeric(
            df["Year"],
            errors="coerce"
        ).dropna()

        years = sorted(
            year_series.astype(int).unique().tolist(),
            reverse=True
        )

    selected_years = st.sidebar.multiselect(
        "📅 Year",
        years,
        default=[],
        key=f"filter_years_{reset_version}",
        placeholder="All Years"
    )

    # ========================================================
    # MONTH
    # ========================================================

    available_months = _unique(
        df,
        "Month"
    )

    months = [
        month
        for month in MONTH_ORDER
        if month in available_months
    ]

    # Add any non-standard month values
    for month in available_months:

        if month not in months:

            months.append(month)

    selected_months = st.sidebar.multiselect(
        "📆 Month",
        months,
        default=[],
        key=f"filter_months_{reset_version}",
        placeholder="All Months"
    )

    # ========================================================
    # WEEK
    # ========================================================

    weeks = _unique(
        df,
        "Week"
    )

    selected_weeks = st.sidebar.multiselect(
        "📅 Week",
        weeks,
        default=[],
        key=f"filter_weeks_{reset_version}",
        placeholder="All Weeks"
    )

    # ========================================================
    # DISEASE
    # ========================================================

    diseases = _unique(
        df,
        "Confirmed Diagnosis"
    )

    selected_diseases = st.sidebar.multiselect(
        "🦠 Disease",
        diseases,
        default=[],
        key=f"filter_diseases_{reset_version}",
        placeholder="All Diseases"
    )

    # ========================================================
    # FACILITY
    # ========================================================

    facilities = _unique(
        df,
        "Facility Name Lform"
    )

    selected_facilities = st.sidebar.multiselect(
        "🏥 Facility",
        facilities,
        default=[],
        key=f"filter_facilities_{reset_version}",
        placeholder="All Facilities"
    )

    # ========================================================
    # WARD
    # ========================================================

    wards = _unique(
        df,
        "Ward"
    )

    selected_wards = st.sidebar.multiselect(
        "🗺️ Ward",
        wards,
        default=[],
        key=f"filter_wards_{reset_version}",
        placeholder="All Wards"
    )

    # ========================================================
    # GENDER
    # ========================================================

    genders = _unique(
        df,
        "Gender"
    )

    selected_genders = st.sidebar.multiselect(
        "👥 Gender",
        genders,
        default=[],
        key=f"filter_genders_{reset_version}",
        placeholder="All Genders"
    )

    # ========================================================
    # AGE GROUP
    # ========================================================

    selected_age_groups = []

    if "Age" in df.columns:

        selected_age_groups = st.sidebar.multiselect(
            "🎂 Age Group",
            AGE_GROUP_ORDER,
            default=[],
            key=f"filter_age_groups_{reset_version}",
            placeholder="All Age Groups"
        )

    # ========================================================
    # OPD / IPD
    # ========================================================

    opd_ipd = _unique(
        df,
        "Opd Ipd"
    )

    selected_opd_ipd = st.sidebar.multiselect(
        "🏥 OPD / IPD",
        opd_ipd,
        default=[],
        key=f"filter_opd_ipd_{reset_version}",
        placeholder="All OPD / IPD"
    )

    # ========================================================
    # AREA / LOCATION
    # ========================================================

    area_column = None

    for candidate in [
        "Area",
        "Area Name",
        "Locality",
        "Location",
    ]:

        if candidate in df.columns:

            area_column = candidate
            break

    areas = _unique(
        df,
        area_column
    ) if area_column else []

    selected_areas = st.sidebar.multiselect(
        "📍 Area / Location",
        areas,
        default=[],
        key=f"filter_areas_{reset_version}",
        placeholder="All Areas"
    )

    # ========================================================
    # STATUS
    # ========================================================

    status_column = None

    for candidate in [
        "Status",
        "Case Status",
        "Record Status",
    ]:

        if candidate in df.columns:

            status_column = candidate
            break

    statuses = _unique(
        df,
        status_column
    ) if status_column else []

    selected_status = st.sidebar.multiselect(
        "📌 Status",
        statuses,
        default=[],
        key=f"filter_status_{reset_version}",
        placeholder="All Status"
    )

    # ========================================================
    # REPORTING DATE
    # ========================================================

    date_from = None
    date_to = None

    if "Reporting Date" in df.columns:

        reporting_dates = pd.to_datetime(
            df["Reporting Date"],
            errors="coerce"
        ).dropna()

        if not reporting_dates.empty:

            min_date = reporting_dates.min().date()
            max_date = reporting_dates.max().date()

            date_range = st.sidebar.date_input(
                "📅 Reporting Date",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key=f"filter_date_range_{reset_version}",
            )

            if isinstance(
                date_range,
                tuple
            ):

                if len(date_range) == 2:

                    date_from = date_range[0]
                    date_to = date_range[1]

                elif len(date_range) == 1:

                    date_from = date_range[0]
                    date_to = date_range[0]

            else:

                date_from = date_range
                date_to = date_range

    # ========================================================
    # RETURN FILTER SETTINGS
    # ========================================================

    return {
        "selected_years": selected_years,
        "selected_months": selected_months,
        "selected_weeks": selected_weeks,
        "selected_diseases": selected_diseases,
        "selected_facilities": selected_facilities,
        "selected_wards": selected_wards,
        "selected_genders": selected_genders,
        "selected_age_groups": selected_age_groups,
        "selected_opd_ipd": selected_opd_ipd,
        "selected_areas": selected_areas,
        "selected_status": selected_status,
        "area_column": area_column,
        "status_column": status_column,
        "date_from": date_from,
        "date_to": date_to,
    }


# ============================================================
# APPLY GLOBAL FILTERS
# ============================================================

def apply_filters(
    df,
    selected_years,
    selected_months,
    selected_weeks,
    selected_diseases,
    selected_facilities,
    selected_wards,
    selected_genders,
    selected_age_groups,
    selected_opd_ipd,
    selected_areas,
    selected_status,
    area_column,
    status_column,
    date_from,
    date_to,
):

    out = df.copy()

    # ========================================================
    # STANDARD FILTERS
    # ========================================================

    filters = [
        ("Year", selected_years),
        ("Month", selected_months),
        ("Week", selected_weeks),
        ("Confirmed Diagnosis", selected_diseases),
        ("Facility Name Lform", selected_facilities),
        ("Ward", selected_wards),
        ("Gender", selected_genders),
        ("Opd Ipd", selected_opd_ipd),
    ]

    for column, values in filters:

        if values and column in out.columns:

            out = out[
                out[column]
                .astype(str)
                .str.strip()
                .isin(
                    [
                        str(value).strip()
                        for value in values
                    ]
                )
            ]

    # ========================================================
    # AGE GROUP
    # ========================================================

    if (
        selected_age_groups
        and "Age" in out.columns
    ):

        out["_Dashboard_Age_Group"] = (
            _create_age_group(
                out["Age"]
            )
        )

        out = out[
            out["_Dashboard_Age_Group"]
            .isin(selected_age_groups)
        ]

    # ========================================================
    # AREA
    # ========================================================

    if (
        selected_areas
        and area_column
        and area_column in out.columns
    ):

        out = out[
            out[area_column]
            .astype(str)
            .str.strip()
            .isin(
                [
                    str(value).strip()
                    for value in selected_areas
                ]
            )
        ]

    # ========================================================
    # STATUS
    # ========================================================

    if (
        selected_status
        and status_column
        and status_column in out.columns
    ):

        out = out[
            out[status_column]
            .astype(str)
            .str.strip()
            .isin(
                [
                    str(value).strip()
                    for value in selected_status
                ]
            )
        ]

    # ========================================================
    # REPORTING DATE
    # ========================================================

    if (
        date_from is not None
        and date_to is not None
        and "Reporting Date" in out.columns
    ):

        reporting_dates = pd.to_datetime(
            out["Reporting Date"],
            errors="coerce"
        )

        out = out[
            (
                reporting_dates.dt.date
                >= date_from
            )
            &
            (
                reporting_dates.dt.date
                <= date_to
            )
        ]

    return out


# ============================================================
# KPI CALCULATION
# ============================================================

def calculate_kpis(df):

    disease = (
        df["Confirmed Diagnosis"]
        .dropna()
        .value_counts()
        if "Confirmed Diagnosis" in df.columns
        else pd.Series(dtype="int64")
    )

    ward = (
        df["Ward"]
        .dropna()
        .value_counts()
        if "Ward" in df.columns
        else pd.Series(dtype="int64")
    )

    facility = (
        df["Facility Name Lform"]
        .dropna()
        .value_counts()
        if "Facility Name Lform" in df.columns
        else pd.Series(dtype="int64")
    )

    return {

        "total": len(df),

        "opd": int(
            df["Opd Ipd"]
            .eq("OPD")
            .sum()
        )
        if "Opd Ipd" in df.columns
        else 0,

        "ipd": int(
            df["Opd Ipd"]
            .eq("IPD")
            .sum()
        )
        if "Opd Ipd" in df.columns
        else 0,

        "male": int(
            df["Gender"]
            .eq("M")
            .sum()
        )
        if "Gender" in df.columns
        else 0,

        "female": int(
            df["Gender"]
            .eq("F")
            .sum()
        )
        if "Gender" in df.columns
        else 0,

        "transgender": int(
            df["Gender"]
            .eq("Transgender")
            .sum()
        )
        if "Gender" in df.columns
        else 0,

        "top_disease": (
            disease.index[0]
            if len(disease)
            else "N/A"
        ),

        "top_ward": (
            ward.index[0]
            if len(ward)
            else "N/A"
        ),

        "top_facility": (
            facility.index[0]
            if len(facility)
            else "N/A"
        ),
    }


# ============================================================
# OVERVIEW
# ============================================================

def render_overview(df):

    filters = create_filters(df)

    filtered = apply_filters(
        df,
        **filters
    )

    k = calculate_kpis(
        filtered
    )

    st.title(
        "🏥 Health Facility Monitor"
    )

    st.caption(
        "Public Health Surveillance "
        "and Management Dashboard"
    )

    # ========================================================
    # FILTER STATUS
    # ========================================================

    if len(df) > 0:

        percentage = (
            len(filtered)
            / len(df)
            * 100
        )

        st.info(
            f"🎛️ Showing **{len(filtered):,}** "
            f"of **{len(df):,}** records "
            f"({percentage:.1f}%)"
        )

    # ========================================================
    # EMPTY RESULT
    # ========================================================

    if filtered.empty:

        st.error(
            "⚠️ No records match the selected "
            "Dashboard Controls."
        )

        st.info(
            "Please change one or more filters "
            "from the Dashboard Controls."
        )

        return

    # ========================================================
    # KPI ROW 1
    # ========================================================

    cols = st.columns(4)

    for col, label, value in [

        (
            cols[0],
            "Total Cases",
            k["total"]
        ),

        (
            cols[1],
            "OPD Cases",
            k["opd"]
        ),

        (
            cols[2],
            "IPD Cases",
            k["ipd"]
        ),

        (
            cols[3],
            "Top Ward",
            k["top_ward"]
        ),
    ]:

        col.metric(
            label,
            f"{value:,}"
            if isinstance(value, int)
            else value
        )

    # ========================================================
    # KPI ROW 2
    # ========================================================

    cols = st.columns(4)

    for col, label, value in [

        (
            cols[0],
            "Male",
            k["male"]
        ),

        (
            cols[1],
            "Female",
            k["female"]
        ),

        (
            cols[2],
            "Top Disease",
            k["top_disease"]
        ),

        (
            cols[3],
            "Top Facility",
            k["top_facility"]
        ),
    ]:

        col.metric(
            label,
            f"{value:,}"
            if isinstance(value, int)
            else value
        )

    # ========================================================
    # FILTERED DATA PREVIEW
    # ========================================================

    st.divider()

    st.subheader(
        "📋 Filtered Records Preview"
    )

    st.dataframe(
        filtered.head(100),
        use_container_width=True,
        hide_index=True
    )
