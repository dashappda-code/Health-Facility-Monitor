import pandas as pd
import streamlit as st


# ============================================================
# COLUMN DETECTION
# ============================================================

def find_column(df, candidates):

    normalized = {
        str(col).strip().lower().replace(" ", "").replace("_", ""): col
        for col in df.columns
    }

    for candidate in candidates:

        key = (
            str(candidate)
            .strip()
            .lower()
            .replace(" ", "")
            .replace("_", "")
        )

        if key in normalized:
            return normalized[key]

    return None


# ============================================================
# CLEAN VALUES
# ============================================================

def clean_series(series):

    return (
        series
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
    )


# ============================================================
# AGE GROUP
# ============================================================

def create_age_group(age_series):

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
# GLOBAL DASHBOARD CONTROL
# ============================================================

def render_dashboard_control(df):

    if df is None or df.empty:

        st.warning(
            "No data available for dashboard controls."
        )

        return df

    data = df.copy()

    # ========================================================
    # DETECT COLUMNS
    # ========================================================

    year_col = find_column(
        data,
        [
            "Year",
            "Reporting Year",
        ]
    )

    month_col = find_column(
        data,
        [
            "Month",
            "Reporting Month",
            "Month Name",
            "Month-Year",
            "Month Year",
        ]
    )

    date_col = find_column(
        data,
        [
            "Date",
            "Date of Reporting",
            "Reporting Date",
            "Registration Date",
            "Case Date",
        ]
    )

    facility_col = find_column(
        data,
        [
            "Facility Name Lform",
            "Facility",
            "Facility Name",
            "Health Facility",
        ]
    )

    ward_col = find_column(
        data,
        [
            "Ward",
            "Ward Name",
            "Ward No",
            "Ward Number",
        ]
    )

    gender_col = find_column(
        data,
        [
            "Gender",
            "Sex",
        ]
    )

    disease_col = find_column(
        data,
        [
            "Confirmed Diagnosis",
            "Disease",
            "Disease Name",
            "Diagnosis",
        ]
    )

    age_col = find_column(
        data,
        [
            "Age",
            "Age Years",
            "Age (Years)",
        ]
    )

    area_col = find_column(
        data,
        [
            "Area",
            "Area Name",
            "Locality",
            "Location",
        ]
    )

    status_col = find_column(
        data,
        [
            "Status",
            "Case Status",
            "Record Status",
        ]
    )

    # ========================================================
    # CONTROL HEADER
    # ========================================================

    st.sidebar.divider()

    st.sidebar.markdown(
        "## 🎛️ Dashboard Control"
    )

    st.sidebar.caption(
        "These filters control the complete dashboard."
    )

    # ========================================================
    # YEAR
    # ========================================================

    selected_year = []

    if year_col:

        year_values = (
            pd.to_numeric(
                data[year_col],
                errors="coerce"
            )
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )

        year_values = sorted(
            year_values,
            reverse=True
        )

        selected_year = st.sidebar.multiselect(
            "📅 Year",
            year_values,
            placeholder="All Years",
            key="global_year_filter"
        )

    # ========================================================
    # MONTH
    # ========================================================

    selected_month = []

    if month_col:

        month_values = sorted(
            clean_series(
                data[month_col]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_month = st.sidebar.multiselect(
            "📆 Month",
            month_values,
            placeholder="All Months",
            key="global_month_filter"
        )

    # ========================================================
    # FACILITY
    # ========================================================

    selected_facility = []

    if facility_col:

        facility_values = sorted(
            clean_series(
                data[facility_col]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_facility = st.sidebar.multiselect(
            "🏥 Facility",
            facility_values,
            placeholder="All Facilities",
            key="global_facility_filter"
        )

    # ========================================================
    # WARD
    # ========================================================

    selected_ward = []

    if ward_col:

        ward_values = sorted(
            clean_series(
                data[ward_col]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_ward = st.sidebar.multiselect(
            "🗺️ Ward",
            ward_values,
            placeholder="All Wards",
            key="global_ward_filter"
        )

    # ========================================================
    # GENDER
    # ========================================================

    selected_gender = []

    if gender_col:

        gender_values = sorted(
            clean_series(
                data[gender_col]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_gender = st.sidebar.multiselect(
            "👥 Gender",
            gender_values,
            placeholder="All Genders",
            key="global_gender_filter"
        )

    # ========================================================
    # DISEASE
    # ========================================================

    selected_disease = []

    if disease_col:

        disease_values = sorted(
            clean_series(
                data[disease_col]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_disease = st.sidebar.multiselect(
            "🦠 Disease / Diagnosis",
            disease_values,
            placeholder="All Diseases",
            key="global_disease_filter"
        )

    # ========================================================
    # AGE GROUP
    # ========================================================

    selected_age_group = []

    if age_col:

        age_group_values = [
            "<1 Year",
            "1–4 Years",
            "5–14 Years",
            "15–24 Years",
            "25–44 Years",
            "45–59 Years",
            "60+ Years",
            "Unknown",
        ]

        selected_age_group = st.sidebar.multiselect(
            "🎂 Age Group",
            age_group_values,
            placeholder="All Age Groups",
            key="global_age_filter"
        )

    # ========================================================
    # AREA / LOCATION
    # ========================================================

    selected_area = []

    if area_col:

        area_values = sorted(
            clean_series(
                data[area_col]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_area = st.sidebar.multiselect(
            "📍 Area / Location",
            area_values,
            placeholder="All Areas",
            key="global_area_filter"
        )

    # ========================================================
    # STATUS
    # ========================================================

    selected_status = []

    if status_col:

        status_values = sorted(
            clean_series(
                data[status_col]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_status = st.sidebar.multiselect(
            "📌 Status",
            status_values,
            placeholder="All Status",
            key="global_status_filter"
        )

    # ========================================================
    # APPLY FILTERS
    # ========================================================

    filtered = data.copy()

    # --------------------------------------------------------
    # YEAR
    # --------------------------------------------------------

    if selected_year and year_col:

        year_numeric = pd.to_numeric(
            filtered[year_col],
            errors="coerce"
        )

        filtered = filtered[
            year_numeric
            .isin(selected_year)
        ]

    # --------------------------------------------------------
    # MONTH
    # --------------------------------------------------------

    if selected_month and month_col:

        filtered = filtered[
            clean_series(
                filtered[month_col]
            ).isin(selected_month)
        ]

    # --------------------------------------------------------
    # FACILITY
    # --------------------------------------------------------

    if selected_facility and facility_col:

        filtered = filtered[
            clean_series(
                filtered[facility_col]
            ).isin(selected_facility)
        ]

    # --------------------------------------------------------
    # WARD
    # --------------------------------------------------------

    if selected_ward and ward_col:

        filtered = filtered[
            clean_series(
                filtered[ward_col]
            ).isin(selected_ward)
        ]

    # --------------------------------------------------------
    # GENDER
    # --------------------------------------------------------

    if selected_gender and gender_col:

        filtered = filtered[
            clean_series(
                filtered[gender_col]
            ).isin(selected_gender)
        ]

    # --------------------------------------------------------
    # DISEASE
    # --------------------------------------------------------

    if selected_disease and disease_col:

        filtered = filtered[
            clean_series(
                filtered[disease_col]
            ).isin(selected_disease)
        ]

    # --------------------------------------------------------
    # AGE GROUP
    # --------------------------------------------------------

    if selected_age_group and age_col:

        filtered["_Global_Age_Group"] = (
            create_age_group(
                filtered[age_col]
            )
        )

        filtered = filtered[
            filtered["_Global_Age_Group"]
            .isin(selected_age_group)
        ]

    # --------------------------------------------------------
    # AREA
    # --------------------------------------------------------

    if selected_area and area_col:

        filtered = filtered[
            clean_series(
                filtered[area_col]
            ).isin(selected_area)
        ]

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if selected_status and status_col:

        filtered = filtered[
            clean_series(
                filtered[status_col]
            ).isin(selected_status)
        ]

    # ========================================================
    # FILTER STATUS
    # ========================================================

    st.sidebar.divider()

    if filtered.empty:

        st.sidebar.error(
            "⚠️ No records match the selected filters."
        )

    else:

        st.sidebar.success(
            f"🟢 Filtered Records: {len(filtered):,}"
        )

    # ========================================================
    # RESET BUTTON
    # ========================================================

    if st.sidebar.button(
        "🔄 Reset All Filters",
        use_container_width=True
    ):

        keys = [
            "global_year_filter",
            "global_month_filter",
            "global_facility_filter",
            "global_ward_filter",
            "global_gender_filter",
            "global_disease_filter",
            "global_age_filter",
            "global_area_filter",
            "global_status_filter",
        ]

        for key in keys:

            if key in st.session_state:

                del st.session_state[key]

        st.rerun()

    return filtered


# ============================================================
# FILTER SUMMARY
# ============================================================

def render_filter_summary(original_df, filtered_df):

    if original_df is None or filtered_df is None:
        return

    total = len(original_df)

    filtered = len(filtered_df)

    if total == 0:
        return

    percentage = (
        filtered / total * 100
    )

    st.info(
        f"🎛️ Dashboard Filter Status: "
        f"Showing **{filtered:,} of {total:,} records "
        f"({percentage:.1f}%)**"
    )
