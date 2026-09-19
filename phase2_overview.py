import pandas as pd
import streamlit as st

from phase1_data import refresh_data


MONTH_ORDER = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]


# ============================================================
# COLUMN HELPERS
# ============================================================

def find_column(df, keywords):
    if df is None or df.empty:
        return None

    columns = list(df.columns)

    for keyword in keywords:
        k = str(keyword).lower().strip()

        for col in columns:
            if str(col).lower().strip() == k:
                return col

    for keyword in keywords:
        k = str(keyword).lower().strip()

        for col in columns:
            if k in str(col).lower():
                return col

    return None


def get_values(df, column):
    if column is None or column not in df.columns:
        return []

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[values != ""]

    return sorted(
        values.unique().tolist(),
        key=str
    )


# ============================================================
# RESET
# ============================================================

FILTER_STATE_KEYS = [
    "global_year_filter",
    "global_month_filter",
    "global_week_filter",
    "global_disease_filter",
    "global_facility_filter",
    "global_ward_filter",
    "global_gender_filter",
    "global_age_filter",
    "global_opdipd_filter",
    "global_area_filter",
    "global_status_filter",
    "global_date_enabled",
    "global_date_from",
    "global_date_to",
]


def reset_filters():
    for key in FILTER_STATE_KEYS:
        st.session_state.pop(key, None)

    st.session_state["filter_reset_version"] = (
        st.session_state.get(
            "filter_reset_version",
            0
        ) + 1
    )


# ============================================================
# GLOBAL FILTER PANEL
# ============================================================

def create_filters(df):

    reset_version = st.session_state.get(
        "filter_reset_version",
        0
    )

    # --------------------------------------------------------
    # Actual live-sheet columns
    # --------------------------------------------------------

    year_col = find_column(
        df,
        ["year", "वर्ष"]
    )

    month_col = find_column(
        df,
        ["month", "महिना"]
    )

    week_col = find_column(
        df,
        ["week", "week no", "week number", "आठवडा"]
    )

    disease_col = find_column(
        df,
        [
            "disease",
            "confirmed diagnosis",
            "diagnosis",
            "disease name",
            "रोग",
        ]
    )

    facility_col = find_column(
        df,
        [
            "facility",
            "facility name",
            "facility name lform",
            "health facility",
            "institution",
            "आरोग्य केंद्र",
        ]
    )

    ward_col = find_column(
        df,
        [
            "ward",
            "ward name",
            "ward no",
            "ward number",
            "प्रभाग",
        ]
    )

    gender_col = find_column(
        df,
        [
            "gender",
            "sex",
            "लिंग",
        ]
    )

    age_group_col = find_column(
        df,
        [
            "age group",
            "age_group",
            "agegroup",
            "age category",
            "वयोगट",
        ]
    )

    opd_ipd_col = find_column(
        df,
        [
            "opd/ipd",
            "opd ipd",
            "opd_ipd",
            "patient type",
            "service type",
        ]
    )

    area_col = find_column(
        df,
        [
            "area",
            "area name",
            "locality",
            "location",
            "patient address",
            "परिसर",
        ]
    )

    status_col = find_column(
        df,
        [
            "status",
            "case status",
            "case_status",
            "diagnosis status",
        ]
    )

    date_col = find_column(
        df,
        [
            "reporting date",
            "date of reporting",
            "date",
            "event date",
            "दिनांक",
        ]
    )

    # --------------------------------------------------------
    # Values
    # --------------------------------------------------------

    years = get_values(df, year_col)

    months_raw = get_values(df, month_col)

    months = [
        m for m in MONTH_ORDER
        if m in months_raw
    ]

    if not months:
        months = months_raw

    weeks = get_values(df, week_col)
    diseases = get_values(df, disease_col)
    facilities = get_values(df, facility_col)
    wards = get_values(df, ward_col)
    genders = get_values(df, gender_col)
    age_groups = get_values(df, age_group_col)
    opd_ipd = get_values(df, opd_ipd_col)
    areas = get_values(df, area_col)
    statuses = get_values(df, status_col)

    # --------------------------------------------------------
    # Heading
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="global-filter-heading">
            <div class="global-filter-title">
                🎛️ Global Dashboard Control
            </div>
            <div class="global-filter-subtitle">
                Select any filter to apply it immediately •
                Blank filter = All Data
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # TOP ACTION BAR
    # --------------------------------------------------------

    action1, action2, action3 = st.columns(
        [1.4, 1.4, 7.2]
    )

    with action1:

        if st.button(
            "↩️ Reset",
            key=f"reset_filters_{reset_version}",
            use_container_width=True,
            help="Clear all filters and show all data",
        ):

            reset_filters()
            st.rerun()

    with action2:

        if st.button(
            "🔄 Refresh",
            key=f"refresh_sheet_{reset_version}",
            use_container_width=True,
            help="Fetch latest data from Google Sheet",
        ):

            with st.spinner(
                "Refreshing Google Sheet data..."
            ):

                refresh_data()

            st.success(
                "Google Sheet data refreshed."
            )

            st.rerun()

    with action3:

        st.caption(
            "💡 Select a value and the dashboard updates automatically. "
            "No Apply button required."
        )

    st.markdown("")

    # --------------------------------------------------------
    # PRIMARY FILTERS
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="filter-row-label">
            PRIMARY MANAGEMENT FILTERS
        </div>
        """,
        unsafe_allow_html=True
    )

    r1 = st.columns(6)

    with r1[0]:

        selected_years = st.multiselect(
            "📅 Year",
            options=years,
            default=[],
            key=f"global_year_filter_{reset_version}",
            placeholder="Select Year",
        )

    with r1[1]:

        selected_months = st.multiselect(
            "🗓️ Month",
            options=months,
            default=[],
            key=f"global_month_filter_{reset_version}",
            placeholder="Select Month",
        )

    with r1[2]:

        selected_weeks = st.multiselect(
            "📌 Week",
            options=weeks,
            default=[],
            key=f"global_week_filter_{reset_version}",
            placeholder="Select Week",
        )

    with r1[3]:

        selected_diseases = st.multiselect(
            "🦠 Disease",
            options=diseases,
            default=[],
            key=f"global_disease_filter_{reset_version}",
            placeholder="Select Disease",
        )

    with r1[4]:

        selected_facilities = st.multiselect(
            "🏥 Facility",
            options=facilities,
            default=[],
            key=f"global_facility_filter_{reset_version}",
            placeholder="Select Facility",
        )

    with r1[5]:

        selected_wards = st.multiselect(
            "🏘️ Ward",
            options=wards,
            default=[],
            key=f"global_ward_filter_{reset_version}",
            placeholder="Select Ward",
        )

    # --------------------------------------------------------
    # SECONDARY FILTERS
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="filter-row-label second">
            DEMOGRAPHIC / SERVICE FILTERS
        </div>
        """,
        unsafe_allow_html=True
    )

    r2 = st.columns(6)

    with r2[0]:

        selected_genders = st.multiselect(
            "⚥ Gender",
            options=genders,
            default=[],
            key=f"global_gender_filter_{reset_version}",
            placeholder="Select Gender",
        )

    with r2[1]:

        selected_age_groups = st.multiselect(
            "👤 Age Group",
            options=age_groups,
            default=[],
            key=f"global_age_filter_{reset_version}",
            placeholder="Select Age Group",
        )

    with r2[2]:

        selected_opd_ipd = st.multiselect(
            "🏨 OPD / IPD",
            options=opd_ipd,
            default=[],
            key=f"global_opdipd_filter_{reset_version}",
            placeholder="Select OPD / IPD",
        )

    with r2[3]:

        selected_areas = st.multiselect(
            "📍 Area",
            options=areas,
            default=[],
            key=f"global_area_filter_{reset_version}",
            placeholder="Select Area",
        )

    with r2[4]:

        selected_status = st.multiselect(
            "🔎 Status",
            options=statuses,
            default=[],
            key=f"global_status_filter_{reset_version}",
            placeholder="Select Status",
        )

    with r2[5]:

        # ----------------------------------------------------
        # DATE FILTER
        # ----------------------------------------------------

        date_from = None
        date_to = None

        date_enabled = st.checkbox(
            "📆 Use Reporting Date",
            value=False,
            key=f"global_date_enabled_{reset_version}",
        )

        if (
            date_enabled
            and date_col
            and date_col in df.columns
        ):

            dates = df[date_col].dropna()

            if not dates.empty:

                if not pd.api.types.is_datetime64_any_dtype(
                    dates
                ):

                    dates = pd.to_datetime(
                        dates,
                        errors="coerce"
                    ).dropna()

                if not dates.empty:

                    min_date = dates.min().date()
                    max_date = dates.max().date()

                    selected_range = st.date_input(
                        "Reporting Date",
                        value=(
                            min_date,
                            max_date
                        ),
                        min_value=min_date,
                        max_value=max_date,
                        key=f"global_date_range_{reset_version}",
                    )

                    if isinstance(
                        selected_range,
                        tuple
                    ):

                        if len(selected_range) == 2:

                            date_from = selected_range[0]
                            date_to = selected_range[1]

                        elif len(selected_range) == 1:

                            date_from = selected_range[0]
                            date_to = selected_range[0]

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

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
        "area_column": area_col,
        "status_column": status_col,
        "date_column": date_col,
        "date_from": date_from,
        "date_to": date_to,
    }


# ============================================================
# APPLY FILTERS
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
    date_column,
    date_from,
    date_to,
):

    if df is None or df.empty:
        return df

    mask = pd.Series(
        True,
        index=df.index
    )

    def apply_text_filter(
        column,
        selected
    ):

        nonlocal mask

        if (
            not column
            or column not in df.columns
            or not selected
        ):
            return

        selected_values = {
            str(x).strip()
            for x in selected
        }

        values = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        mask &= values.isin(
            selected_values
        )

    # --------------------------------------------------------
    # Canonical dashboard columns
    # --------------------------------------------------------

    apply_text_filter(
        "Year",
        selected_years
    )

    apply_text_filter(
        "Month",
        selected_months
    )

    apply_text_filter(
        "Week",
        selected_weeks
    )

    apply_text_filter(
        "Disease",
        selected_diseases
    )

    apply_text_filter(
        "Facility Name",
        selected_facilities
    )

    apply_text_filter(
        "Ward Name",
        selected_wards
    )

    apply_text_filter(
        "Gender",
        selected_genders
    )

    apply_text_filter(
        "Age Group",
        selected_age_groups
    )

    apply_text_filter(
        "OPD/IPD",
        selected_opd_ipd
    )

    # --------------------------------------------------------
    # Area / Status
    # --------------------------------------------------------

    apply_text_filter(
        area_column,
        selected_areas
    )

    apply_text_filter(
        status_column,
        selected_status
    )

    # --------------------------------------------------------
    # Reporting Date
    # --------------------------------------------------------

    if (
        date_column
        and date_column in df.columns
        and (
            date_from is not None
            or date_to is not None
        )
    ):

        dates = df[date_column]

        if not pd.api.types.is_datetime64_any_dtype(
            dates
        ):

            dates = pd.to_datetime(
                dates,
                errors="coerce"
            )

        if date_from is not None:

            mask &= (
                dates.dt.date >= date_from
            )

        if date_to is not None:

            mask &= (
                dates.dt.date <= date_to
            )

    return df.loc[mask]


# ============================================================
# KPI
# ============================================================

def calculate_kpis(df):

    if df is None or df.empty:

        return {
            "total_records": 0,
            "diseases": 0,
            "facilities": 0,
            "wards": 0,
            "total": 0,
            "opd": 0,
            "ipd": 0,
            "male": 0,
            "female": 0,
            "transgender": 0,
            "top_disease": "N/A",
            "top_ward": "N/A",
            "top_facility": "N/A",
        }

    disease_col = (
        "Disease"
        if "Disease" in df.columns
        else find_column(
            df,
            [
                "disease",
                "confirmed diagnosis",
                "diagnosis",
            ]
        )
    )

    facility_col = (
        "Facility Name"
        if "Facility Name" in df.columns
        else find_column(
            df,
            [
                "facility",
                "facility name",
                "facility name lform",
            ]
        )
    )

    ward_col = (
        "Ward Name"
        if "Ward Name" in df.columns
        else find_column(
            df,
            [
                "ward",
                "ward name",
            ]
        )
    )

    disease_counts = (
        df[disease_col]
        .dropna()
        .astype(str)
        .str.strip()
        .value_counts()
        if disease_col
        else pd.Series(dtype="int64")
    )

    ward_counts = (
        df[ward_col]
        .dropna()
        .astype(str)
        .str.strip()
        .value_counts()
        if ward_col
        else pd.Series(dtype="int64")
    )

    facility_counts = (
        df[facility_col]
        .dropna()
        .astype(str)
        .str.strip()
        .value_counts()
        if facility_col
        else pd.Series(dtype="int64")
    )

    # --------------------------------------------------------
    # OPD / IPD
    # --------------------------------------------------------

    opd_count = 0
    ipd_count = 0

    if "OPD/IPD" in df.columns:

        opd_values = (
            df["OPD/IPD"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        opd_count = int(
            opd_values.eq("OPD").sum()
        )

        ipd_count = int(
            opd_values.eq("IPD").sum()
        )

    # --------------------------------------------------------
    # Gender
    # --------------------------------------------------------

    male_count = 0
    female_count = 0
    transgender_count = 0

    if "Gender" in df.columns:

        gender_values = (
            df["Gender"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        male_count = int(
            gender_values.isin(
                ["M", "MALE"]
            ).sum()
        )

        female_count = int(
            gender_values.isin(
                ["F", "FEMALE"]
            ).sum()
        )

        transgender_count = int(
            gender_values.isin(
                ["TRANSGENDER", "TG", "T"]
            ).sum()
        )

    return {
        "total_records": len(df),

        "diseases": (
            int(df[disease_col].nunique())
            if disease_col
            else 0
        ),

        "facilities": (
            int(df[facility_col].nunique())
            if facility_col
            else 0
        ),

        "wards": (
            int(df[ward_col].nunique())
            if ward_col
            else 0
        ),

        "total": len(df),

        "opd": opd_count,
        "ipd": ipd_count,

        "male": male_count,
        "female": female_count,
        "transgender": transgender_count,

        "top_disease": (
            disease_counts.index[0]
            if len(disease_counts)
            else "N/A"
        ),

        "top_ward": (
            ward_counts.index[0]
            if len(ward_counts)
            else "N/A"
        ),

        "top_facility": (
            facility_counts.index[0]
            if len(facility_counts)
            else "N/A"
        ),
    }


# ============================================================
# OVERVIEW
# ============================================================

def render_overview(df):

    st.subheader(
        "📊 Programme Overview"
    )

    if df is None or df.empty:

        st.warning(
            "No records available for the selected filters."
        )

        return

    facility_col = (
        "Facility Name"
        if "Facility Name" in df.columns
        else find_column(
            df,
            [
                "facility",
                "facility name",
                "facility name lform",
            ]
        )
    )

    ward_col = (
        "Ward Name"
        if "Ward Name" in df.columns
        else find_column(
            df,
            [
                "ward",
                "ward name",
            ]
        )
    )

    disease_col = (
        "Disease"
        if "Disease" in df.columns
        else find_column(
            df,
            [
                "disease",
                "confirmed diagnosis",
                "diagnosis",
            ]
        )
    )

    date_col = find_column(
        df,
        [
            "reporting date",
            "date of reporting",
            "date",
            "event date",
        ]
    )

    # --------------------------------------------------------
    # Top facilities
    # --------------------------------------------------------

    c1, c2 = st.columns(2)

    with c1:

        st.markdown(
            "#### 🏥 Top Facilities"
        )

        if facility_col:

            counts = (
                df[facility_col]
                .dropna()
                .astype(str)
                .str.strip()
                .value_counts()
                .head(10)
            )

            st.dataframe(
                counts.rename("Records"),
                use_container_width=True,
            )

    with c2:

        st.markdown(
            "#### 🏘️ Top Burden Wards"
        )

        if ward_col:

            counts = (
                df[ward_col]
                .dropna()
                .astype(str)
                .str.strip()
                .value_counts()
                .head(10)
            )

            st.dataframe(
                counts.rename("Records"),
                use_container_width=True,
            )

    # --------------------------------------------------------
    # Monthly trend
    # --------------------------------------------------------

    st.markdown(
        "#### 📈 Monthly Trend"
    )

    if date_col:

        dates = df[date_col]

        if not pd.api.types.is_datetime64_any_dtype(
            dates
        ):

            dates = pd.to_datetime(
                dates,
                errors="coerce"
            )

        monthly = (
            dates
            .dropna()
            .dt.to_period("M")
            .value_counts()
            .sort_index()
        )

        if not monthly.empty:

            monthly.index = (
                monthly.index.astype(str)
            )

            st.line_chart(
                monthly,
                use_container_width=True
            )

    # --------------------------------------------------------
    # Disease distribution
    # --------------------------------------------------------

    st.markdown(
        "#### 🦠 Disease Distribution"
    )

    if disease_col:

        counts = (
            df[disease_col]
            .dropna()
            .astype(str)
            .str.strip()
            .value_counts()
            .head(15)
        )

        st.dataframe(
            counts.rename("Records"),
            use_container_width=True
        )
