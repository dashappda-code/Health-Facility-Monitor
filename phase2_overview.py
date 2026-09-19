import streamlit as st
import pandas as pd
import phase1_data


# ============================================================
# GLOBAL FILTERS
# ============================================================

def create_filters(df):
    """
    Global dashboard filters.

    Reporting Date logic:
    - Start blank + End blank  = ALL data
    - Start selected           = Start date onwards
    - End selected             = Up to End date
    - Both selected            = Start date to End date inclusive

    All other filters:
    - Blank = ALL
    - Selection applies immediately
    """

    if df is None or df.empty:
        return {
            "start_date": None,
            "end_date": None,
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

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="global-filter-heading">
            <div class="global-filter-title">
                🎛️ Global Dashboard Control
            </div>
            <div class="global-filter-subtitle">
                Select filters to update the entire dashboard immediately.
                Leave a filter blank to include all records.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # Reset
    # --------------------------------------------------------

    reset_clicked = st.button(
        "↩️ Reset Filters",
        key="global_reset_filters",
    )

    if reset_clicked:

        keys_to_clear = [
            "filter_start_date",
            "filter_end_date",
            "filter_year",
            "filter_month",
            "filter_week",
            "filter_disease",
            "filter_facility",
            "filter_ward",
            "filter_gender",
            "filter_age_group",
            "filter_opd_ipd",
        ]

        for key in keys_to_clear:
            st.session_state.pop(key, None)

        st.rerun()

    # --------------------------------------------------------
    # Helper
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

        return sorted(values.unique().tolist())

    # --------------------------------------------------------
    # Reporting Date limits
    # --------------------------------------------------------

    min_date = None
    max_date = None

    if "Reporting Date" in df.columns:

        valid_dates = df["Reporting Date"].dropna()

        if not valid_dates.empty:

            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()

    # --------------------------------------------------------
    # Available values
    # --------------------------------------------------------

    years = unique_values("Year")
    months = unique_values("Month")
    weeks = unique_values("Week")
    diseases = unique_values("Disease")
    facilities = unique_values("Facility Name")
    wards = unique_values("Ward Name")
    genders = unique_values("Gender")
    age_groups = unique_values("Age Group")
    opd_ipd_values = unique_values("OPD/IPD")

    # ========================================================
    # REPORTING DATE
    # ========================================================

    st.markdown("#### 📅 Reporting Date")

    d1, d2 = st.columns(2)

    with d1:

        start_date = None

        if min_date is not None and max_date is not None:

            start_date = st.date_input(
                "Start Date",
                value=None,
                min_value=min_date,
                max_value=max_date,
                key="filter_start_date",
            )

    with d2:

        end_date = None

        if min_date is not None and max_date is not None:

            end_date = st.date_input(
                "End Date",
                value=None,
                min_value=min_date,
                max_value=max_date,
                key="filter_end_date",
            )

    # ========================================================
    # OTHER FILTERS
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        selected_year = st.multiselect(
            "📅 Year",
            options=years,
            default=[],
            key="filter_year",
        )

    with c2:

        selected_month = st.multiselect(
            "🗓️ Month",
            options=months,
            default=[],
            key="filter_month",
        )

    with c3:

        selected_week = st.multiselect(
            "📆 Week",
            options=weeks,
            default=[],
            key="filter_week",
        )

    with c4:

        selected_disease = st.multiselect(
            "🦠 Disease",
            options=diseases,
            default=[],
            key="filter_disease",
        )

    c5, c6, c7, c8 = st.columns(4)

    with c5:

        selected_facility = st.multiselect(
            "🏥 Facility",
            options=facilities,
            default=[],
            key="filter_facility",
        )

    with c6:

        selected_ward = st.multiselect(
            "📍 Ward",
            options=wards,
            default=[],
            key="filter_ward",
        )

    with c7:

        selected_gender = st.multiselect(
            "👤 Gender",
            options=genders,
            default=[],
            key="filter_gender",
        )

    with c8:

        selected_age_group = st.multiselect(
            "🎂 Age Group",
            options=age_groups,
            default=[],
            key="filter_age_group",
        )

    c9, c10 = st.columns(2)

    with c9:

        selected_opd_ipd = st.multiselect(
            "🏨 OPD / IPD",
            options=opd_ipd_values,
            default=[],
            key="filter_opd_ipd",
        )

    with c10:

        st.empty()

    # ========================================================
    # RETURN FILTER VALUES
    # ========================================================

    return {
        "start_date": start_date,
        "end_date": end_date,
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
    start_date=None,
    end_date=None,
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
    """
    Apply all global dashboard filters.

    Reporting Date:
    - Start only  -> Start onwards
    - End only    -> Up to End
    - Both        -> Start through End inclusive
    - Neither     -> ALL data
    """

    if df is None or df.empty:
        return pd.DataFrame()

    filtered = df.copy()

    # ========================================================
    # REPORTING DATE RANGE
    # ========================================================

    if "Reporting Date" in filtered.columns:

        reporting_dates = filtered["Reporting Date"]

        # Start Date selected
        if start_date is not None:

            start_timestamp = pd.Timestamp(start_date)

            filtered = filtered[
                reporting_dates >= start_timestamp
            ]

        # End Date selected
        if end_date is not None:

            # Include the complete End Date
            end_timestamp = (
                pd.Timestamp(end_date)
                + pd.Timedelta(days=1)
            )

            filtered = filtered[
                filtered["Reporting Date"] < end_timestamp
            ]

    # ========================================================
    # TEXT FILTER HELPER
    # ========================================================

    def apply_text_filter(data, column, values):

        if not values:
            return data

        if column not in data.columns:
            return data

        cleaned_values = [
            str(value).strip()
            for value in values
            if str(value).strip()
        ]

        if not cleaned_values:
            return data

        column_values = (
            data[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        return data[
            column_values.isin(cleaned_values)
        ]

    # ========================================================
    # APPLY FILTERS
    # ========================================================

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

        return int(values.nunique())

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

    st.subheader("📊 Programme Overview")

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

    # ========================================================
    # REPORTING PERIOD
    # ========================================================

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

    # ========================================================
    # DISEASE-WISE BURDEN
    # ========================================================

    if "Disease" in df.columns:

        disease_values = (
            df["Disease"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_values = disease_values[
            disease_values.ne("")
        ]

        if not disease_values.empty:

            disease_table = (
                disease_values
                .value_counts()
                .head(10)
                .rename_axis("Disease")
                .reset_index(name="Records")
            )

            st.markdown(
                "### 🦠 Disease-wise Burden"
            )

            st.dataframe(
                disease_table,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # TOP FACILITIES
    # ========================================================

    if "Facility Name" in df.columns:

        facility_values = (
            df["Facility Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_values = facility_values[
            facility_values.ne("")
        ]

        if not facility_values.empty:

            facility_table = (
                facility_values
                .value_counts()
                .head(10)
                .rename_axis("Facility")
                .reset_index(name="Records")
            )

            st.markdown(
                "### 🏥 Top Facilities"
            )

            st.dataframe(
                facility_table,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # TOP WARDS
    # ========================================================

    if "Ward Name" in df.columns:

        ward_values = (
            df["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_values = ward_values[
            ward_values.ne("")
        ]

        if not ward_values.empty:

            ward_table = (
                ward_values
                .value_counts()
                .head(10)
                .rename_axis("Ward")
                .reset_index(name="Records")
            )

            st.markdown(
                "### 📍 Top Burden Wards"
            )

            st.dataframe(
                ward_table,
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
