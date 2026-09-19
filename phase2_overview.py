import streamlit as st
import pandas as pd
import phase1_data


# ============================================================
# GLOBAL DASHBOARD CONTROL
# ============================================================

def create_filters(df):

    empty_filters = {
        "reporting_date": None,
        "year": [],
        "month": [],
        "week": [],
        "disease": [],
        "facility": [],
        "ward": [],
        "gender": [],
        "age_group": [],
        "opd_ipd": [],
    }

    if df is None or df.empty:
        return empty_filters

    # --------------------------------------------------------
    # Reset system
    # --------------------------------------------------------

    if "dashboard_filter_reset" not in st.session_state:
        st.session_state.dashboard_filter_reset = 0

    reset_id = st.session_state.dashboard_filter_reset
    prefix = f"dashboard_filter_{reset_id}"

    # --------------------------------------------------------
    # Unique values
    # --------------------------------------------------------

    def unique_values(column):

        if column not in df.columns:
            return []

        values = (
            df[column]
            .dropna()
            .astype(str)
            .str.strip()
        )

        values = values[
            values.ne("")
            & values.ne("nan")
            & values.ne("NaT")
        ]

        return sorted(
            values.unique().tolist()
        )

    years = unique_values("Year")
    months = unique_values("Month")
    weeks = unique_values("Week")
    diseases = unique_values("Disease")
    facilities = unique_values("Facility Name")
    wards = unique_values("Ward Name")
    genders = unique_values("Gender")
    age_groups = unique_values("Age Group")
    opd_ipd = unique_values("OPD/IPD")

    # --------------------------------------------------------
    # Date range
    # --------------------------------------------------------

    min_date = None
    max_date = None

    if "Reporting Date" in df.columns:

        dates = df["Reporting Date"].dropna()

        if not dates.empty:
            min_date = dates.min().date()
            max_date = dates.max().date()

    # ========================================================
    # ONE SINGLE PANEL
    # ========================================================

    with st.container(border=True):

        # ----------------------------------------------------
        # Panel Header
        # ----------------------------------------------------

        header_col, reset_col = st.columns(
            [8, 1.3],
            vertical_alignment="center",
        )

        with header_col:

            st.markdown(
                "### 🎛️ Global Dashboard Control"
            )

            st.caption(
                "Select any filter to update the entire "
                "dashboard immediately. Leave a filter blank "
                "to include all records."
            )

        with reset_col:

            reset_clicked = st.button(
                "↩️ Reset",
                key="global_reset_filters",
                use_container_width=True,
            )

        if reset_clicked:

            st.session_state.dashboard_filter_reset += 1
            st.rerun()

        # ----------------------------------------------------
        # ROW 1
        # ----------------------------------------------------

        row1 = st.columns(
            [1, 1, 1, 1.4, 2.2],
            gap="small",
        )

        with row1[0]:

            selected_year = st.multiselect(
                "📅 Year",
                options=years,
                default=[],
                key=f"{prefix}_year",
                placeholder="All Years",
            )

        with row1[1]:

            selected_month = st.multiselect(
                "🗓️ Month",
                options=months,
                default=[],
                key=f"{prefix}_month",
                placeholder="All Months",
            )

        with row1[2]:

            selected_week = st.multiselect(
                "📆 Week",
                options=weeks,
                default=[],
                key=f"{prefix}_week",
                placeholder="All Weeks",
            )

        with row1[3]:

            selected_disease = st.multiselect(
                "🦠 Disease",
                options=diseases,
                default=[],
                key=f"{prefix}_disease",
                placeholder="All Diseases",
            )

        with row1[4]:

            selected_facility = st.multiselect(
                "🏥 Facility",
                options=facilities,
                default=[],
                key=f"{prefix}_facility",
                placeholder="All Facilities",
            )

        # ----------------------------------------------------
        # ROW 2
        # ----------------------------------------------------

        row2 = st.columns(
            [1.5, 1, 1.1, 1.2, 2.8],
            gap="small",
        )

        with row2[0]:

            selected_ward = st.multiselect(
                "📍 Ward",
                options=wards,
                default=[],
                key=f"{prefix}_ward",
                placeholder="All Wards",
            )

        with row2[1]:

            selected_gender = st.multiselect(
                "👤 Gender",
                options=genders,
                default=[],
                key=f"{prefix}_gender",
                placeholder="All Genders",
            )

        with row2[2]:

            selected_age_group = st.multiselect(
                "🎂 Age Group",
                options=age_groups,
                default=[],
                key=f"{prefix}_age_group",
                placeholder="All Age Groups",
            )

        with row2[3]:

            selected_opd_ipd = st.multiselect(
                "🏨 OPD / IPD",
                options=opd_ipd,
                default=[],
                key=f"{prefix}_opd_ipd",
                placeholder="All",
            )

        with row2[4]:

            date_columns = st.columns(
                2,
                gap="small",
            )

            with date_columns[0]:

                from_date = st.date_input(
                    "📅 From Date",
                    value=None,
                    min_value=min_date,
                    max_value=max_date,
                    key=f"{prefix}_from_date",
                )

            with date_columns[1]:

                to_date = st.date_input(
                    "📅 To Date",
                    value=None,
                    min_value=min_date,
                    max_value=max_date,
                    key=f"{prefix}_to_date",
                )

            selected_reporting_date = None

            if (
                from_date is not None
                or to_date is not None
            ):

                selected_reporting_date = (
                    from_date,
                    to_date,
                )

    # ========================================================
    # RETURN
    # ========================================================

    return {
        "reporting_date": selected_reporting_date,
        "year": selected_year,
        "month": selected_month,
        "week": selected_week,
        "disease": selected_disease,
        "facility": selected_facility,
        "ward": selected_ward,
        "gender": selected_gender,
        "age_group": selected_age_group,
        "opd_ipd": selected_opd_ipd,
    }


# ============================================================
# APPLY FILTERS
# ============================================================

def apply_filters(
    df,
    reporting_date=None,
    year=None,
    month=None,
    week=None,
    disease=None,
    facility=None,
    ward=None,
    gender=None,
    age_group=None,
    opd_ipd=None,
):

    if df is None or df.empty:
        return pd.DataFrame()

    filtered = df.copy()

    # --------------------------------------------------------
    # Reporting Date
    # --------------------------------------------------------

    if (
        reporting_date is not None
        and "Reporting Date" in filtered.columns
    ):

        try:

            start_date = None
            end_date = None

            if isinstance(reporting_date, tuple):

                if len(reporting_date) == 2:
                    start_date = reporting_date[0]
                    end_date = reporting_date[1]

            else:

                start_date = reporting_date
                end_date = reporting_date

            if start_date is not None:

                start_timestamp = pd.Timestamp(
                    start_date
                )

                filtered = filtered[
                    filtered["Reporting Date"].notna()
                    & (
                        filtered["Reporting Date"].dt.normalize()
                        >= start_timestamp.normalize()
                    )
                ]

            if end_date is not None:

                end_timestamp = pd.Timestamp(
                    end_date
                )

                filtered = filtered[
                    filtered["Reporting Date"].notna()
                    & (
                        filtered["Reporting Date"].dt.normalize()
                        <= end_timestamp.normalize()
                    )
                ]

        except Exception:
            pass

    # --------------------------------------------------------
    # Text filter helper
    # --------------------------------------------------------

    def apply_text_filter(
        data,
        column,
        values,
    ):

        if not values:
            return data

        if column not in data.columns:
            return data

        values_clean = [
            str(value).strip()
            for value in values
            if str(value).strip()
        ]

        if not values_clean:
            return data

        column_values = (
            data[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        return data[
            column_values.isin(values_clean)
        ]

    # --------------------------------------------------------
    # Apply filters
    # --------------------------------------------------------

    filtered = apply_text_filter(
        filtered,
        "Year",
        year,
    )

    filtered = apply_text_filter(
        filtered,
        "Month",
        month,
    )

    filtered = apply_text_filter(
        filtered,
        "Week",
        week,
    )

    filtered = apply_text_filter(
        filtered,
        "Disease",
        disease,
    )

    filtered = apply_text_filter(
        filtered,
        "Facility Name",
        facility,
    )

    filtered = apply_text_filter(
        filtered,
        "Ward Name",
        ward,
    )

    filtered = apply_text_filter(
        filtered,
        "Gender",
        gender,
    )

    filtered = apply_text_filter(
        filtered,
        "Age Group",
        age_group,
    )

    filtered = apply_text_filter(
        filtered,
        "OPD/IPD",
        opd_ipd,
    )

    return filtered.reset_index(drop=True)


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
        }

    def count_unique(column):

        if column not in df.columns:
            return 0

        values = (
            df[column]
            .dropna()
            .astype(str)
            .str.strip()
        )

        values = values[
            values.ne("")
            & values.ne("nan")
        ]

        return int(
            values.nunique()
        )

    return {
        "total_records": int(len(df)),
        "diseases": count_unique("Disease"),
        "facilities": count_unique("Facility Name"),
        "wards": count_unique("Ward Name"),
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

    kpis = calculate_kpis(df)

    c1, c2, c3, c4 = st.columns(4)

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

    st.divider()

    # --------------------------------------------------------
    # Reporting Period
    # --------------------------------------------------------

    if "Reporting Date" in df.columns:

        dates = df["Reporting Date"].dropna()

        if not dates.empty:

            start_date = dates.min().strftime(
                "%d-%m-%Y"
            )

            end_date = dates.max().strftime(
                "%d-%m-%Y"
            )

            st.info(
                f"📅 Reporting Period: "
                f"**{start_date} to {end_date}**"
            )

    # --------------------------------------------------------
    # Disease-wise Burden
    # --------------------------------------------------------

    if "Disease" in df.columns:

        disease_counts = (
            df["Disease"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_counts = disease_counts[
            disease_counts.ne("")
        ]

        if not disease_counts.empty:

            top_disease = (
                disease_counts
                .value_counts()
                .head(10)
                .rename_axis("Disease")
                .reset_index(
                    name="Records"
                )
            )

            st.markdown(
                "### 🦠 Disease-wise Burden"
            )

            st.dataframe(
                top_disease,
                use_container_width=True,
                hide_index=True,
            )

    # --------------------------------------------------------
    # Top Facilities
    # --------------------------------------------------------

    if "Facility Name" in df.columns:

        facility_counts = (
            df["Facility Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_counts = facility_counts[
            facility_counts.ne("")
        ]

        if not facility_counts.empty:

            top_facilities = (
                facility_counts
                .value_counts()
                .head(10)
                .rename_axis("Facility")
                .reset_index(
                    name="Records"
                )
            )

            st.markdown(
                "### 🏥 Top Facilities"
            )

            st.dataframe(
                top_facilities,
                use_container_width=True,
                hide_index=True,
            )

    # --------------------------------------------------------
    # Top Burden Wards
    # --------------------------------------------------------

    if "Ward Name" in df.columns:

        ward_counts = (
            df["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_counts = ward_counts[
            ward_counts.ne("")
        ]

        if not ward_counts.empty:

            top_wards = (
                ward_counts
                .value_counts()
                .head(10)
                .rename_axis("Ward")
                .reset_index(
                    name="Records"
                )
            )

            st.markdown(
                "### 📍 Top Burden Wards"
            )

            st.dataframe(
                top_wards,
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# GOOGLE SHEET REFRESH
# ============================================================

st.sidebar.markdown("---")

if st.sidebar.button(
    "🔄 Refresh Google Sheet Data",
    use_container_width=True,
):

    with st.spinner(
        "Refreshing Google Sheet data..."
    ):

        phase1_data.refresh_data()

    st.success(
        "Google Sheet data refreshed successfully."
    )

    st.rerun()
