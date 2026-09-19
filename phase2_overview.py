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
# GLOBAL CONTROL PANEL CSS
# ============================================================

def _inject_control_css():

    st.markdown(
        """
        <style>

        /* =====================================================
           GLOBAL DASHBOARD CONTROL PANEL
           ===================================================== */

        .global-control-panel {
            position: sticky;
            top: 0;
            z-index: 999;

            background: rgba(255, 255, 255, 0.98);

            border: 1px solid #d9dee5;
            border-radius: 10px;

            padding: 12px 14px 8px 14px;

            margin-top: -8px;
            margin-bottom: 18px;

            box-shadow:
                0 3px 12px rgba(0, 0, 0, 0.08);
        }

        .global-control-title {
            font-size: 18px;
            font-weight: 700;

            color: #1f3c88;

            margin-bottom: 2px;
        }

        .global-control-subtitle {
            font-size: 12px;
            color: #666;

            margin-bottom: 8px;
        }

        .global-control-divider {
            border-top: 1px solid #e4e7eb;

            margin-top: 5px;
            margin-bottom: 8px;
        }

        /* Keep Streamlit horizontal blocks compact */

        div[data-testid="stHorizontalBlock"] {
            gap: 0.55rem;
        }

        /* Compact multiselect */

        div[data-baseweb="select"] {
            min-height: 38px;
        }

        /* Make control labels slightly smaller */

        div[data-testid="stWidgetLabel"] p {
            font-size: 13px !important;
            font-weight: 600 !important;
        }

        /* Sticky panel should remain above page content */

        section.main > div {
            overflow: visible;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# HELPERS
# ============================================================

def _unique(df, column):

    if not column or column not in df.columns:
        return []

    values = (
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
        .tolist()
    )

    return sorted(values, key=str)


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

    # --------------------------------------------------------
    # CSS
    # --------------------------------------------------------

    _inject_control_css()

    # --------------------------------------------------------
    # PANEL START
    # --------------------------------------------------------

    st.markdown(
        '<div class="global-control-panel">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="global-control-title">'
        '🎛️ Global Dashboard Controls'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="global-control-subtitle">'
        'All selected filters apply across the complete dashboard'
        '</div>',
        unsafe_allow_html=True,
    )

    reset_version = st.session_state.get(
        "filter_reset_version",
        0
    )

    # ========================================================
    # ROW 1
    # ========================================================

    row1 = st.columns(
        [
            0.8,   # Year
            1.0,   # Month
            0.8,   # Week
            1.5,   # Disease
            1.6,   # Facility
            1.2,   # Ward
            1.0,   # Gender
        ]
    )

    # --------------------------------------------------------
    # YEAR
    # --------------------------------------------------------

    years = []

    if "Year" in df.columns:

        year_series = pd.to_numeric(
            df["Year"],
            errors="coerce"
        ).dropna()

        if not year_series.empty:

            years = sorted(
                year_series
                .astype(int)
                .unique()
                .tolist(),
                reverse=True
            )

    with row1[0]:

        selected_years = st.multiselect(
            "📅 Year",
            years,
            default=[],
            key=f"filter_years_{reset_version}",
            placeholder="All"
        )

    # --------------------------------------------------------
    # MONTH
    # --------------------------------------------------------

    available_months = _unique(
        df,
        "Month"
    )

    months = [
        month
        for month in MONTH_ORDER
        if month in available_months
    ]

    for month in available_months:

        if month not in months:
            months.append(month)

    with row1[1]:

        selected_months = st.multiselect(
            "📆 Month",
            months,
            default=[],
            key=f"filter_months_{reset_version}",
            placeholder="All"
        )

    # --------------------------------------------------------
    # WEEK
    # --------------------------------------------------------

    weeks = _unique(
        df,
        "Week"
    )

    with row1[2]:

        selected_weeks = st.multiselect(
            "📅 Week",
            weeks,
            default=[],
            key=f"filter_weeks_{reset_version}",
            placeholder="All"
        )

    # --------------------------------------------------------
    # DISEASE
    # --------------------------------------------------------

    diseases = _unique(
        df,
        "Confirmed Diagnosis"
    )

    with row1[3]:

        selected_diseases = st.multiselect(
            "🦠 Disease",
            diseases,
            default=[],
            key=f"filter_diseases_{reset_version}",
            placeholder="All Diseases"
        )

    # --------------------------------------------------------
    # FACILITY
    # --------------------------------------------------------

    facilities = _unique(
        df,
        "Facility Name Lform"
    )

    with row1[4]:

        selected_facilities = st.multiselect(
            "🏥 Facility",
            facilities,
            default=[],
            key=f"filter_facilities_{reset_version}",
            placeholder="All Facilities"
        )

    # --------------------------------------------------------
    # WARD
    # --------------------------------------------------------

    wards = _unique(
        df,
        "Ward"
    )

    with row1[5]:

        selected_wards = st.multiselect(
            "🗺️ Ward",
            wards,
            default=[],
            key=f"filter_wards_{reset_version}",
            placeholder="All Wards"
        )

    # --------------------------------------------------------
    # GENDER
    # --------------------------------------------------------

    genders = _unique(
        df,
        "Gender"
    )

    with row1[6]:

        selected_genders = st.multiselect(
            "👥 Gender",
            genders,
            default=[],
            key=f"filter_genders_{reset_version}",
            placeholder="All"
        )

    # ========================================================
    # ROW 2
    # ========================================================

    row2 = st.columns(
        [
            1.15,  # Age Group
            1.05,  # OPD/IPD
            1.35,  # Area
            1.15,  # Status
            1.25,  # Start Date
            1.25,  # End Date
            0.65,  # Refresh
            0.65,  # Reset
        ]
    )

    # --------------------------------------------------------
    # AGE GROUP
    # --------------------------------------------------------

    selected_age_groups = []

    if "Age" in df.columns:

        with row2[0]:

            selected_age_groups = st.multiselect(
                "🎂 Age Group",
                AGE_GROUP_ORDER,
                default=[],
                key=f"filter_age_groups_{reset_version}",
                placeholder="All Ages"
            )

    # --------------------------------------------------------
    # OPD / IPD
    # --------------------------------------------------------

    opd_ipd = _unique(
        df,
        "Opd Ipd"
    )

    with row2[1]:

        selected_opd_ipd = st.multiselect(
            "🏥 OPD / IPD",
            opd_ipd,
            default=[],
            key=f"filter_opd_ipd_{reset_version}",
            placeholder="All"
        )

    # --------------------------------------------------------
    # AREA / LOCATION
    # --------------------------------------------------------

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

    areas = (
        _unique(df, area_column)
        if area_column
        else []
    )

    selected_areas = []

    if area_column:

        with row2[2]:

            selected_areas = st.multiselect(
                "📍 Area / Location",
                areas,
                default=[],
                key=f"filter_areas_{reset_version}",
                placeholder="All Areas"
            )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status_column = None

    for candidate in [
        "Status",
        "Case Status",
        "Record Status",
    ]:

        if candidate in df.columns:

            status_column = candidate
            break

    statuses = (
        _unique(df, status_column)
        if status_column
        else []
    )

    selected_status = []

    if status_column:

        with row2[3]:

            selected_status = st.multiselect(
                "📌 Status",
                statuses,
                default=[],
                key=f"filter_status_{reset_version}",
                placeholder="All"
            )

    # ========================================================
    # REPORTING DATE
    # ========================================================

    date_from = None
    date_to = None

    min_date = None
    max_date = None

    if "Reporting Date" in df.columns:

        reporting_dates = pd.to_datetime(
            df["Reporting Date"],
            errors="coerce"
        ).dropna()

        if not reporting_dates.empty:

            min_date = reporting_dates.min().date()
            max_date = reporting_dates.max().date()

    # --------------------------------------------------------
    # START DATE
    # --------------------------------------------------------

    with row2[4]:

        if min_date is not None:

            start_date = st.date_input(
                "📅 Starting Date",
                value=None,
                min_value=min_date,
                max_value=max_date,
                key=f"filter_start_date_{reset_version}",
                help=(
                    "If not selected, data starts "
                    "from earliest available date."
                )
            )

        else:

            start_date = None

    # --------------------------------------------------------
    # END DATE
    # --------------------------------------------------------

    with row2[5]:

        if min_date is not None:

            end_date = st.date_input(
                "📅 Ending Date",
                value=None,
                min_value=min_date,
                max_value=max_date,
                key=f"filter_end_date_{reset_version}",
                help=(
                    "If not selected, data continues "
                    "up to latest available date."
                )
            )

        else:

            end_date = None

    # --------------------------------------------------------
    # DATE LOGIC
    # --------------------------------------------------------

    if min_date is not None:

        if start_date is None:

            date_from = min_date

        else:

            date_from = start_date

        if end_date is None:

            date_to = max_date

        else:

            date_to = end_date

        # ----------------------------------------------------
        # INVALID RANGE
        # ----------------------------------------------------

        if (
            date_from is not None
            and date_to is not None
            and date_from > date_to
        ):

            date_from = None
            date_to = None

    # ========================================================
    # REFRESH BUTTON
    # ========================================================

    with row2[6]:

        st.markdown(
            "<div style='height:25px'></div>",
            unsafe_allow_html=True
        )

        refresh_clicked = st.button(
            "🔄",
            key="refresh_data_button",
            use_container_width=True,
            help="Reload latest data from Google Sheets"
        )

        if refresh_clicked:

            refresh_data()
            st.rerun()

    # ========================================================
    # RESET BUTTON
    # ========================================================

    with row2[7]:

        st.markdown(
            "<div style='height:25px'></div>",
            unsafe_allow_html=True
        )

        st.button(
            "↩️",
            key="reset_filters_button",
            use_container_width=True,
            help="Clear all dashboard filters",
            on_click=_reset_filter_state,
        )

    # ========================================================
    # DATE RANGE WARNING
    # ========================================================

    if (
        min_date is not None
        and start_date is not None
        and end_date is not None
        and start_date > end_date
    ):

        st.error(
            "⚠️ Ending Date cannot be earlier "
            "than Starting Date. "
            "Date filter is not applied."
        )

    # ========================================================
    # AVAILABLE DATE INFORMATION
    # ========================================================

    if min_date is not None:

        st.caption(
            f"📅 Available reporting period: "
            f"{min_date.strftime('%d-%m-%Y')} "
            f"to "
            f"{max_date.strftime('%d-%m-%Y')}"
        )

    # --------------------------------------------------------
    # PANEL END
    # --------------------------------------------------------

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

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
            .isin(
                selected_age_groups
            )
        ]

    # ========================================================
    # AREA / LOCATION
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

        valid_date_mask = (
            reporting_dates.notna()
            &
            (
                reporting_dates.dt.date
                >= date_from
            )
            &
            (
                reporting_dates.dt.date
                <= date_to
            )
        )

        out = out[
            valid_date_mask
        ]

    return out


# ============================================================
# KPI CALCULATION
# ============================================================

def calculate_kpis(df):

    disease = (
        df["Confirmed Diagnosis"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        if "Confirmed Diagnosis" in df.columns
        else pd.Series(dtype="int64")
    )

    ward = (
        df["Ward"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        if "Ward" in df.columns
        else pd.Series(dtype="int64")
    )

    facility = (
        df["Facility Name Lform"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        if "Facility Name Lform" in df.columns
        else pd.Series(dtype="int64")
    )

    return {

        "total": len(df),

        "opd": int(
            df["Opd Ipd"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("OPD")
            .sum()
        )
        if "Opd Ipd" in df.columns
        else 0,

        "ipd": int(
            df["Opd Ipd"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("IPD")
            .sum()
        )
        if "Opd Ipd" in df.columns
        else 0,

        "male": int(
            df["Gender"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("M")
            .sum()
        )
        if "Gender" in df.columns
        else 0,

        "female": int(
            df["Gender"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("F")
            .sum()
        )
        if "Gender" in df.columns
        else 0,

        "transgender": int(
            df["Gender"]
            .astype(str)
            .str.strip()
            .str.lower()
            .eq("transgender")
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

    """
    IMPORTANT:
    Global filters are created in app.py.

    This function receives the already-filtered
    dataframe and DOES NOT create filters again.
    """

    filtered = df.copy()

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

    st.info(
        f"🎛️ Currently showing "
        f"**{len(filtered):,}** filtered records"
    )

    # ========================================================
    # EMPTY RESULT
    # ========================================================

    if filtered.empty:

        st.error(
            "⚠️ No records match the selected "
            "Global Dashboard Controls."
        )

        st.info(
            "Please change one or more filters "
            "from the Global Dashboard Controls."
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
