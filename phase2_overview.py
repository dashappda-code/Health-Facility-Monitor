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
    """Find a dataframe column using exact match first, then partial match."""
    if df is None or df.empty:
        return None

    columns = list(df.columns)

    # Exact match
    for keyword in keywords:
        k = str(keyword).lower().strip()

        for col in columns:
            if str(col).lower().strip() == k:
                return col

    # Partial match
    for keyword in keywords:
        k = str(keyword).lower().strip()

        for col in columns:
            if k in str(col).lower():
                return col

    return None


def get_values(df, column):
    """Return clean unique values from a column."""
    if column is None or column not in df.columns:
        return []

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[values != ""]

    return sorted(values.unique().tolist(), key=str)


# ============================================================
# FILTER STATE
# ============================================================

FILTER_KEYS = [
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
    "global_date_range",
]


def _reset_filters():
    """Clear all global filter selections."""
    for key in FILTER_KEYS:
        st.session_state.pop(key, None)


def _default_all(values, key):
    """
    Default dashboard state = ALL data.

    Empty selection is intentionally treated as ALL by apply_filters().
    However, on first load the widgets visually show all available values.
    """
    if key not in st.session_state:
        return list(values)

    current = st.session_state.get(key, [])

    if current is None:
        return []

    valid = set(values)

    return [
        value
        for value in current
        if value in valid
    ]


# ============================================================
# GLOBAL FILTER PANEL
# ============================================================

def create_filters(df):

    # --------------------------------------------------------
    # Identify actual live Google Sheet columns
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
        ],
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
        ],
    )

    ward_col = find_column(
        df,
        [
            "ward",
            "ward name",
            "ward no",
            "ward number",
            "प्रभाग",
        ],
    )

    gender_col = find_column(
        df,
        [
            "gender",
            "sex",
            "लिंग",
        ],
    )

    age_group_col = find_column(
        df,
        [
            "age group",
            "age_group",
            "agegroup",
            "age category",
            "वयोगट",
        ],
    )

    opd_ipd_col = find_column(
        df,
        [
            "opd/ipd",
            "opd ipd",
            "opd_ipd",
            "patient type",
            "service type",
        ],
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
        ],
    )

    status_col = find_column(
        df,
        [
            "status",
            "case status",
            "case_status",
            "diagnosis status",
        ],
    )

    date_col = find_column(
        df,
        [
            "reporting date",
            "date of reporting",
            "date",
            "event date",
            "दिनांक",
        ],
    )

    # --------------------------------------------------------
    # Available filter values
    # --------------------------------------------------------

    years = get_values(df, year_col)

    months_raw = get_values(df, month_col)

    months = [
        month
        for month in MONTH_ORDER
        if month in months_raw
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
    # Global dashboard control heading
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="global-filter-heading">
            <div class="global-filter-title">
                🎛️ Global Dashboard Control
            </div>
            <div class="global-filter-subtitle">
                Filters apply across all dashboard sections •
                Default view = complete available dataset
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    reset_clicked = False

    # --------------------------------------------------------
    # Filter form
    # --------------------------------------------------------

    with st.form(
        "global_dashboard_filter_form",
        clear_on_submit=False,
    ):

        st.markdown(
            """
            <div class="filter-row-label">
                PRIMARY MANAGEMENT FILTERS
            </div>
            """,
            unsafe_allow_html=True,
        )

        r1 = st.columns(6)

        # YEAR
        with r1[0]:
            selected_years = st.multiselect(
                "📅 Year",
                years,
                default=_default_all(
                    years,
                    "global_year_filter",
                ),
                key="global_year_filter",
            )

        # MONTH
        with r1[1]:
            selected_months = st.multiselect(
                "🗓️ Month",
                months,
                default=_default_all(
                    months,
                    "global_month_filter",
                ),
                key="global_month_filter",
            )

        # WEEK
        with r1[2]:
            selected_weeks = st.multiselect(
                "📌 Week",
                weeks,
                default=_default_all(
                    weeks,
                    "global_week_filter",
                ),
                key="global_week_filter",
            )

        # DISEASE
        with r1[3]:
            selected_diseases = st.multiselect(
                "🦠 Disease",
                diseases,
                default=_default_all(
                    diseases,
                    "global_disease_filter",
                ),
                key="global_disease_filter",
            )

        # FACILITY
        with r1[4]:
            selected_facilities = st.multiselect(
                "🏥 Facility",
                facilities,
                default=_default_all(
                    facilities,
                    "global_facility_filter",
                ),
                key="global_facility_filter",
            )

        # WARD
        with r1[5]:
            selected_wards = st.multiselect(
                "🏘️ Ward",
                wards,
                default=_default_all(
                    wards,
                    "global_ward_filter",
                ),
                key="global_ward_filter",
            )

        st.markdown(
            """
            <div class="filter-row-label second">
                DEMOGRAPHIC / SERVICE FILTERS
            </div>
            """,
            unsafe_allow_html=True,
        )

        r2 = st.columns(6)

        # GENDER
        with r2[0]:
            selected_genders = st.multiselect(
                "⚥ Gender",
                genders,
                default=_default_all(
                    genders,
                    "global_gender_filter",
                ),
                key="global_gender_filter",
            )

        # AGE GROUP
        with r2[1]:
            selected_age_groups = st.multiselect(
                "👤 Age Group",
                age_groups,
                default=_default_all(
                    age_groups,
                    "global_age_filter",
                ),
                key="global_age_filter",
            )

        # OPD / IPD
        with r2[2]:
            selected_opd_ipd = st.multiselect(
                "🏨 OPD / IPD",
                opd_ipd,
                default=_default_all(
                    opd_ipd,
                    "global_opdipd_filter",
                ),
                key="global_opdipd_filter",
            )

        # AREA
        with r2[3]:
            selected_areas = st.multiselect(
                "📍 Area",
                areas,
                default=_default_all(
                    areas,
                    "global_area_filter",
                ),
                key="global_area_filter",
            )

        # STATUS
        with r2[4]:
            selected_status = st.multiselect(
                "🔎 Status",
                statuses,
                default=_default_all(
                    statuses,
                    "global_status_filter",
                ),
                key="global_status_filter",
            )

        # REPORTING DATE
        with r2[5]:

            date_from = None
            date_to = None

            if date_col and date_col in df.columns:

                dates = df[date_col].dropna()

                if not dates.empty:

                    # phase1_data.py is responsible for safe date cleaning.
                    if not pd.api.types.is_datetime64_any_dtype(dates):

                        dates = pd.to_datetime(
                            dates,
                            errors="coerce",
                        ).dropna()

                    if not dates.empty:

                        min_date = dates.min().date()
                        max_date = dates.max().date()

                        current_range = st.session_state.get(
                            "global_date_range",
                            (min_date, max_date),
                        )

                        selected_range = st.date_input(
                            "📆 Reporting Date",
                            value=current_range,
                            min_value=min_date,
                            max_value=max_date,
                            key="global_date_range",
                        )

                        if isinstance(
                            selected_range,
                            tuple,
                        ):

                            if len(selected_range) == 2:

                                date_from = selected_range[0]
                                date_to = selected_range[1]

                            elif len(selected_range) == 1:

                                date_from = selected_range[0]
                                date_to = selected_range[0]

                        elif hasattr(
                            selected_range,
                            "year",
                        ):

                            date_from = selected_range
                            date_to = selected_range

        # ----------------------------------------------------
        # ACTION BUTTONS
        # ----------------------------------------------------

        st.markdown(
            '<div class="filter-actions">',
            unsafe_allow_html=True,
        )

        b1, b2, b3 = st.columns(
            [1.2, 1.2, 4.6]
        )

        with b1:

            st.form_submit_button(
                "✅ Apply Filters",
                type="primary",
                use_container_width=True,
            )

        with b2:

            reset_clicked = st.form_submit_button(
                "↩️ Reset to All",
                use_container_width=True,
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    if reset_clicked:

        _reset_filters()

        st.rerun()

    # --------------------------------------------------------
    # IMPORTANT:
    # The dictionary below MUST match apply_filters()
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
    date_column,
    date_from,
    date_to,
):

    if df is None or df.empty:
        return df

    # Start with ALL records.
    mask = pd.Series(
        True,
        index=df.index,
    )

    # --------------------------------------------------------
    # Text / categorical filters
    # --------------------------------------------------------

    def apply_text_filter(
        column,
        selected,
    ):

        nonlocal mask

        if not column:
            return

        if column not in df.columns:
            return

        if selected is None:
            return

        # Empty = ALL
        if len(selected) == 0:
            return

        selected_clean = {
            str(value).strip()
            for value in selected
        }

        column_values = (
            df[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        mask &= column_values.isin(
            selected_clean
        )

    mappings = [
        (
            find_column(
                df,
                ["year", "वर्ष"],
            ),
            selected_years,
        ),
        (
            find_column(
                df,
                ["month", "महिना"],
            ),
            selected_months,
        ),
        (
            find_column(
                df,
                ["week", "week no", "week number", "आठवडा"],
            ),
            selected_weeks,
        ),
        (
            find_column(
                df,
                [
                    "disease",
                    "confirmed diagnosis",
                    "diagnosis",
                    "रोग",
                ],
            ),
            selected_diseases,
        ),
        (
            find_column(
                df,
                [
                    "facility",
                    "facility name",
                    "facility name lform",
                    "health facility",
                    "institution",
                    "आरोग्य केंद्र",
                ],
            ),
            selected_facilities,
        ),
        (
            find_column(
                df,
                [
                    "ward",
                    "ward name",
                    "ward no",
                    "ward number",
                    "प्रभाग",
                ],
            ),
            selected_wards,
        ),
        (
            find_column(
                df,
                [
                    "gender",
                    "sex",
                    "लिंग",
                ],
            ),
            selected_genders,
        ),
        (
            find_column(
                df,
                [
                    "age group",
                    "age_group",
                    "agegroup",
                    "age category",
                    "वयोगट",
                ],
            ),
            selected_age_groups,
        ),
        (
            find_column(
                df,
                [
                    "opd/ipd",
                    "opd ipd",
                    "opd_ipd",
                    "patient type",
                    "service type",
                ],
            ),
            selected_opd_ipd,
        ),
        (
            area_column,
            selected_areas,
        ),
        (
            status_column,
            selected_status,
        ),
    ]

    for column, values in mappings:
        apply_text_filter(
            column,
            values,
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
                errors="coerce",
            )

        if date_from is not None:

            mask &= (
                dates.dt.date >= date_from
            )

        if date_to is not None:

            mask &= (
                dates.dt.date <= date_to
            )

    return df.loc[mask].copy()


# ============================================================
# KPI CALCULATION
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

    disease_col = find_column(
        df,
        [
            "disease",
            "confirmed diagnosis",
            "diagnosis",
            "disease name",
            "रोग",
        ],
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
        ],
    )

    ward_col = find_column(
        df,
        [
            "ward",
            "ward name",
            "ward no",
            "ward number",
            "प्रभाग",
        ],
    )

    opd_col = find_column(
        df,
        [
            "opd/ipd",
            "opd ipd",
            "opd_ipd",
            "patient type",
            "service type",
        ],
    )

    gender_col = find_column(
        df,
        [
            "gender",
            "sex",
            "लिंग",
        ],
    )

    # --------------------------------------------------------
    # Counts
    # --------------------------------------------------------

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

    if opd_col:

        opd_values = (
            df[opd_col]
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

    if gender_col:

        gender_values = (
            df[gender_col]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        male_count = int(
            gender_values.isin(
                ["M", "MALE", "पुरुष"]
            ).sum()
        )

        female_count = int(
            gender_values.isin(
                ["F", "FEMALE", "FEMALE", "स्त्री", "महिला"]
            ).sum()
        )

        transgender_count = int(
            gender_values.isin(
                [
                    "TRANSGENDER",
                    "TG",
                    "T",
                ]
            ).sum()
        )

    top_disease = (
        disease_counts.index[0]
        if len(disease_counts)
        else "N/A"
    )

    top_ward = (
        ward_counts.index[0]
        if len(ward_counts)
        else "N/A"
    )

    top_facility = (
        facility_counts.index[0]
        if len(facility_counts)
        else "N/A"
    )

    return {
        # Keys used by current app.py
        "total_records": len(df),
        "diseases": (
            int(
                df[disease_col]
                .dropna()
                .nunique()
            )
            if disease_col
            else 0
        ),
        "facilities": (
            int(
                df[facility_col]
                .dropna()
                .nunique()
            )
            if facility_col
            else 0
        ),
        "wards": (
            int(
                df[ward_col]
                .dropna()
                .nunique()
            )
            if ward_col
            else 0
        ),

        # Additional management KPI keys
        "total": len(df),
        "opd": opd_count,
        "ipd": ipd_count,
        "male": male_count,
        "female": female_count,
        "transgender": transgender_count,
        "top_disease": top_disease,
        "top_ward": top_ward,
        "top_facility": top_facility,
    }


# ============================================================
# OVERVIEW
# ============================================================

def render_overview(df):

    st.subheader("📊 Programme Overview")

    if df is None or df.empty:

        st.warning(
            "No records available for the selected filters."
        )

        return

    facility_col = find_column(
        df,
        [
            "facility",
            "facility name",
            "facility name lform",
            "health facility",
            "institution",
            "आरोग्य केंद्र",
        ],
    )

    ward_col = find_column(
        df,
        [
            "ward",
            "ward name",
            "ward no",
            "ward number",
            "प्रभाग",
        ],
    )

    disease_col = find_column(
        df,
        [
            "disease",
            "confirmed diagnosis",
            "diagnosis",
            "disease name",
            "रोग",
        ],
    )

    date_col = find_column(
        df,
        [
            "reporting date",
            "date of reporting",
            "date",
            "event date",
            "दिनांक",
        ],
    )

    # --------------------------------------------------------
    # Top Facility / Top Ward
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

        else:

            st.info(
                "Facility information is not available."
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

        else:

            st.info(
                "Ward information is not available."
            )

    # --------------------------------------------------------
    # Monthly Trend
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
                errors="coerce",
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
                use_container_width=True,
            )

        else:

            st.info(
                "No valid reporting-date data available."
            )

    else:

        st.info(
            "Reporting Date column is not available."
        )

    # --------------------------------------------------------
    # Disease Distribution
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
            use_container_width=True,
        )

    else:

        st.info(
            "Disease information is not available."
        )
