import streamlit as st
import pandas as pd


# ============================================================
# COLUMN FINDER
# ============================================================

def find_column(df, possible_names):

    for name in possible_names:

        if name in df.columns:
            return name

    lower_map = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for name in possible_names:

        key = str(name).strip().lower()

        if key in lower_map:
            return lower_map[key]

    return None


# ============================================================
# UNIQUE CLEAN VALUES
# ============================================================

def get_values(df, column):

    if column is None or column not in df.columns:
        return []

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[
        values != ""
    ]

    return sorted(
        values.unique().tolist()
    )


# ============================================================
# CREATE GLOBAL FILTERS
# ============================================================

def create_filters(df):

    # --------------------------------------------------------
    # COLUMN IDENTIFICATION
    # --------------------------------------------------------

    year_col = find_column(
        df,
        [
            "Year",
            "year",
        ],
    )

    month_col = find_column(
        df,
        [
            "Month",
            "month",
        ],
    )

    week_col = find_column(
        df,
        [
            "Week",
            "week",
        ],
    )

    disease_col = find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "disease",
        ],
    )

    facility_col = find_column(
        df,
        [
            "Facility Name",
            "Facility",
            "facility",
        ],
    )

    ward_col = find_column(
        df,
        [
            "Ward Name",
            "Ward",
            "ward",
        ],
    )

    gender_col = find_column(
        df,
        [
            "Gender",
            "Sex",
            "gender",
        ],
    )

    age_group_col = find_column(
        df,
        [
            "Age Group",
            "Age group",
            "AgeGroup",
        ],
    )

    opd_ipd_col = find_column(
        df,
        [
            "OPD/IPD",
            "OPD IPD",
            "OPD_IPD",
        ],
    )

    area_col = find_column(
        df,
        [
            "Patient Address",
            "Area",
            "Address",
            "Location",
        ],
    )

    status_col = find_column(
        df,
        [
            "Confirmed Diagnosis",
            "Status",
            "Diagnosis",
        ],
    )

    date_col = find_column(
        df,
        [
            "Reporting Date",
            "Date",
            "Reporting date",
        ],
    )


    # --------------------------------------------------------
    # OPTIONS
    # --------------------------------------------------------

    years = get_values(
        df,
        year_col,
    )

    months = get_values(
        df,
        month_col,
    )

    weeks = get_values(
        df,
        week_col,
    )

    diseases = get_values(
        df,
        disease_col,
    )

    facilities = get_values(
        df,
        facility_col,
    )

    wards = get_values(
        df,
        ward_col,
    )

    genders = get_values(
        df,
        gender_col,
    )

    age_groups = get_values(
        df,
        age_group_col,
    )

    opd_ipd = get_values(
        df,
        opd_ipd_col,
    )

    areas = get_values(
        df,
        area_col,
    )

    status = get_values(
        df,
        status_col,
    )


    # ========================================================
    # SESSION STATE INITIALIZATION
    # ========================================================

    filter_keys = {

        "global_years": years,

        "global_months": months,

        "global_weeks": weeks,

        "global_diseases": diseases,

        "global_facilities": facilities,

        "global_wards": wards,

        "global_genders": genders,

        "global_age_groups": age_groups,

        "global_opd_ipd": opd_ipd,

        "global_areas": areas,

        "global_status": status,

    }


    for key, default_value in filter_keys.items():

        if key not in st.session_state:

            st.session_state[key] = default_value


    # ========================================================
    # RESET FUNCTION
    # ========================================================

    if st.session_state.get(
        "reset_dashboard_filters",
        False
    ):

        st.session_state.global_years = years
        st.session_state.global_months = months
        st.session_state.global_weeks = weeks
        st.session_state.global_diseases = diseases
        st.session_state.global_facilities = facilities
        st.session_state.global_wards = wards
        st.session_state.global_genders = genders
        st.session_state.global_age_groups = age_groups
        st.session_state.global_opd_ipd = opd_ipd
        st.session_state.global_areas = areas
        st.session_state.global_status = status

        st.session_state.reset_dashboard_filters = False


    # ========================================================
    # GLOBAL FILTER UI
    # ========================================================

    with st.container():

        st.markdown(
            """
            <div style="
                background:#f8f9fa;
                border:1px solid #d6d6d6;
                border-radius:8px;
                padding:10px 12px 4px 12px;
                margin-bottom:10px;
            ">
                <div style="
                    font-size:18px;
                    font-weight:600;
                    margin-bottom:2px;
                ">
                    🎛️ Global Dashboard Control
                </div>

                <div style="
                    font-size:12px;
                    color:#666;
                    margin-bottom:4px;
                ">
                    These filters apply across the dashboard.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


        # ====================================================
        # ROW 1
        # ====================================================

        r1 = st.columns(4)

        with r1[0]:

            selected_years = st.multiselect(
                "Year",
                years,
                key="global_years",
            )

        with r1[1]:

            selected_months = st.multiselect(
                "Month",
                months,
                key="global_months",
            )

        with r1[2]:

            selected_weeks = st.multiselect(
                "Week",
                weeks,
                key="global_weeks",
            )

        with r1[3]:

            selected_diseases = st.multiselect(
                "Disease",
                diseases,
                key="global_diseases",
            )


        # ====================================================
        # ROW 2
        # ====================================================

        r2 = st.columns(4)

        with r2[0]:

            selected_facilities = st.multiselect(
                "Facility",
                facilities,
                key="global_facilities",
            )

        with r2[1]:

            selected_wards = st.multiselect(
                "Ward",
                wards,
                key="global_wards",
            )

        with r2[2]:

            selected_genders = st.multiselect(
                "Gender",
                genders,
                key="global_genders",
            )

        with r2[3]:

            selected_age_groups = st.multiselect(
                "Age Group",
                age_groups,
                key="global_age_groups",
            )


        # ====================================================
        # ROW 3
        # ====================================================

        r3 = st.columns(4)

        with r3[0]:

            selected_opd_ipd = st.multiselect(
                "OPD / IPD",
                opd_ipd,
                key="global_opd_ipd",
            )

        with r3[1]:

            selected_areas = st.multiselect(
                "Area",
                areas,
                key="global_areas",
            )

        with r3[2]:

            selected_status = st.multiselect(
                "Status / Diagnosis",
                status,
                key="global_status",
            )

        with r3[3]:

            refresh_clicked = st.button(
                "🔄 Refresh Data",
                use_container_width=True,
            )

            reset_clicked = st.button(
                "↩️ Reset Filters",
                use_container_width=True,
            )


        # ====================================================
        # DATE FILTER
        # ====================================================

        date_from = None
        date_to = None

        if date_col is not None:

            date_series = pd.to_datetime(
                df[date_col],
                errors="coerce",
            )

            valid_dates = date_series.dropna()

            if not valid_dates.empty:

                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()

                d1, d2 = st.columns(2)

                with d1:

                    date_from = st.date_input(
                        "Starting Date",
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="global_date_from",
                    )

                with d2:

                    date_to = st.date_input(
                        "Ending Date",
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="global_date_to",
                    )


        # ====================================================
        # BUTTON ACTIONS
        # ====================================================

        if refresh_clicked:

            try:

                from phase1_data import refresh_data

                refresh_data()

                st.cache_data.clear()

                st.rerun()

            except Exception:

                st.warning(
                    "Data refresh could not be completed."
                )


        if reset_clicked:

            st.session_state.reset_dashboard_filters = True

            st.rerun()


    # ========================================================
    # RETURN FILTER VALUES
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

        "area_column": area_col,

        "status_column": status_col,

        "date_from": date_from,

        "date_to": date_to,

    }


# ============================================================
# FILTER HELPER
# ============================================================

def _filter_multiselect(
    data,
    column,
    selected_values,
):

    if (
        column is None
        or column not in data.columns
        or not selected_values
    ):

        return data

    values = (
        data[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return data[
        values.isin(
            [str(x).strip() for x in selected_values]
        )
    ]


# ============================================================
# APPLY GLOBAL FILTERS
# ============================================================

def apply_filters(
    df,
    selected_years=None,
    selected_months=None,
    selected_weeks=None,
    selected_diseases=None,
    selected_facilities=None,
    selected_wards=None,
    selected_genders=None,
    selected_age_groups=None,
    selected_opd_ipd=None,
    selected_areas=None,
    selected_status=None,
    area_column=None,
    status_column=None,
    date_from=None,
    date_to=None,
):

    data = df.copy()


    # --------------------------------------------------------
    # YEAR
    # --------------------------------------------------------

    if selected_years:

        year_col = find_column(
            data,
            ["Year", "year"],
        )

        data = _filter_multiselect(
            data,
            year_col,
            selected_years,
        )


    # --------------------------------------------------------
    # MONTH
    # --------------------------------------------------------

    month_col = find_column(
        data,
        ["Month", "month"],
    )

    data = _filter_multiselect(
        data,
        month_col,
        selected_months,
    )


    # --------------------------------------------------------
    # WEEK
    # --------------------------------------------------------

    week_col = find_column(
        data,
        ["Week", "week"],
    )

    data = _filter_multiselect(
        data,
        week_col,
        selected_weeks,
    )


    # --------------------------------------------------------
    # DISEASE
    # --------------------------------------------------------

    disease_col = find_column(
        data,
        ["Disease", "Disease Name", "disease"],
    )

    data = _filter_multiselect(
        data,
        disease_col,
        selected_diseases,
    )


    # --------------------------------------------------------
    # FACILITY
    # --------------------------------------------------------

    facility_col = find_column(
        data,
        ["Facility Name", "Facility", "facility"],
    )

    data = _filter_multiselect(
        data,
        facility_col,
        selected_facilities,
    )


    # --------------------------------------------------------
    # WARD
    # --------------------------------------------------------

    ward_col = find_column(
        data,
        ["Ward Name", "Ward", "ward"],
    )

    data = _filter_multiselect(
        data,
        ward_col,
        selected_wards,
    )


    # --------------------------------------------------------
    # GENDER
    # --------------------------------------------------------

    gender_col = find_column(
        data,
        ["Gender", "Sex", "gender"],
    )

    data = _filter_multiselect(
        data,
        gender_col,
        selected_genders,
    )


    # --------------------------------------------------------
    # AGE GROUP
    # --------------------------------------------------------

    age_group_col = find_column(
        data,
        ["Age Group", "Age group", "AgeGroup"],
    )

    data = _filter_multiselect(
        data,
        age_group_col,
        selected_age_groups,
    )


    # --------------------------------------------------------
    # OPD / IPD
    # --------------------------------------------------------

    opd_ipd_col = find_column(
        data,
        [
            "OPD/IPD",
            "OPD IPD",
            "OPD_IPD",
        ],
    )

    data = _filter_multiselect(
        data,
        opd_ipd_col,
        selected_opd_ipd,
    )


    # --------------------------------------------------------
    # AREA
    # --------------------------------------------------------

    data = _filter_multiselect(
        data,
        area_column,
        selected_areas,
    )


    # --------------------------------------------------------
    # STATUS / DIAGNOSIS
    # --------------------------------------------------------

    data = _filter_multiselect(
        data,
        status_column,
        selected_status,
    )


    # --------------------------------------------------------
    # REPORTING DATE
    # --------------------------------------------------------

    date_col = find_column(
        data,
        [
            "Reporting Date",
            "Date",
            "Reporting date",
        ],
    )

    if date_col is not None:

        date_series = pd.to_datetime(
            data[date_col],
            errors="coerce",
        )

        if date_from is not None:

            date_from = pd.to_datetime(
                date_from
            )

            data = data[
                date_series >= date_from
            ]

            date_series = pd.to_datetime(
                data[date_col],
                errors="coerce",
            )


        if date_to is not None:

            date_to = pd.to_datetime(
                date_to
            ) + pd.Timedelta(
                days=1
            ) - pd.Timedelta(
                microseconds=1
            )

            data = data[
                date_series <= date_to
            ]


    return data


# ============================================================
# KPI CALCULATION
# ============================================================

def calculate_kpis(df):

    total_records = len(df)


    disease_col = find_column(
        df,
        ["Disease", "Disease Name", "disease"],
    )

    facility_col = find_column(
        df,
        ["Facility Name", "Facility", "facility"],
    )

    ward_col = find_column(
        df,
        ["Ward Name", "Ward", "ward"],
    )

    date_col = find_column(
        df,
        [
            "Reporting Date",
            "Date",
            "Reporting date",
        ],
    )


    diseases = (
        df[disease_col].nunique()
        if disease_col
        else 0
    )

    facilities = (
        df[facility_col].nunique()
        if facility_col
        else 0
    )

    wards = (
        df[ward_col].nunique()
        if ward_col
        else 0
    )


    reporting_period = "Not available"


    if date_col:

        dates = pd.to_datetime(
            df[date_col],
            errors="coerce",
        ).dropna()

        if not dates.empty:

            reporting_period = (
                f"{dates.min().strftime('%d-%m-%Y')}"
                f" to "
                f"{dates.max().strftime('%d-%m-%Y')}"
            )


    return {

        "total_records": total_records,

        "diseases": diseases,

        "facilities": facilities,

        "wards": wards,

        "reporting_period": reporting_period,

    }


# ============================================================
# OVERVIEW
# ============================================================

def render_overview(df):

    st.markdown(
        "## 📊 Programme Overview"
    )

    if df is None or df.empty:

        st.warning(
            "No records available for the selected filters."
        )

        return


    kpis = calculate_kpis(df)


    # ========================================================
    # KPI ROW
    # ========================================================

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:

        st.metric(
            "Total Records",
            f"{kpis['total_records']:,}",
        )

    with c2:

        st.metric(
            "Diseases",
            f"{kpis['diseases']:,}",
        )

    with c3:

        st.metric(
            "Facilities",
            f"{kpis['facilities']:,}",
        )

    with c4:

        st.metric(
            "Wards",
            f"{kpis['wards']:,}",
        )

    with c5:

        st.metric(
            "Reporting Period",
            kpis["reporting_period"],
        )


    # ========================================================
    # TOP FACILITIES / WARDS
    # ========================================================

    col1, col2 = st.columns(2)


    with col1:

        st.markdown(
            "### 🏥 Top Facilities"
        )

        facility_col = find_column(
            df,
            [
                "Facility Name",
                "Facility",
                "facility",
            ],
        )

        if facility_col:

            facility_table = (
                df[facility_col]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
                .head(10)
                .rename_axis("Facility")
                .reset_index(
                    name="Records"
                )
            )

            st.dataframe(
                facility_table,
                use_container_width=True,
                hide_index=True,
            )


    with col2:

        st.markdown(
            "### 🏘️ Top Wards"
        )

        ward_col = find_column(
            df,
            [
                "Ward Name",
                "Ward",
                "ward",
            ],
        )

        if ward_col:

            ward_table = (
                df[ward_col]
                .fillna("Unknown")
                .astype(str)
                .value_counts()
                .head(10)
                .rename_axis("Ward")
                .reset_index(
                    name="Records"
                )
            )

            st.dataframe(
                ward_table,
                use_container_width=True,
                hide_index=True,
            )


    # ========================================================
    # MONTHLY TREND
    # ========================================================

    st.markdown(
        "### 📅 Monthly Trend"
    )

    month_col = find_column(
        df,
        [
            "Month",
            "month",
        ],
    )

    if month_col:

        monthly = (
            df[month_col]
            .fillna("Unknown")
            .astype(str)
            .value_counts()
            .rename_axis("Month")
            .reset_index(
                name="Records"
            )
        )

        st.bar_chart(
            monthly.set_index("Month")
        )


    st.caption(
        f"Showing {len(df):,} records after applying global filters."
    )
