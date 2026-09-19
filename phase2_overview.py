import streamlit as st
import pandas as pd


# ============================================================
# COLUMN FINDER
# ============================================================

def find_column(df, keywords):

    if df is None or df.empty:
        return None

    columns = list(df.columns)

    # Exact match first
    for keyword in keywords:
        keyword = keyword.lower().strip()

        for col in columns:
            if str(col).lower().strip() == keyword:
                return col

    # Partial match
    for keyword in keywords:
        keyword = keyword.lower().strip()

        for col in columns:
            if keyword in str(col).lower():
                return col

    return None


# ============================================================
# UNIQUE VALUES
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

    values = values[values != ""]

    return sorted(values.unique().tolist())


# ============================================================
# CREATE GLOBAL FILTERS
# ============================================================

def create_filters(df):

    st.markdown("### 🎛️ Global Dashboard Control")
    st.caption(
        "Select filters below. The selected data will be used across all dashboard sections."
    )

    # --------------------------------------------------------
    # Identify columns
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
            "disease name",
            "diagnosis",
            "disease/diagnosis",
            "रोग",
        ]
    )

    facility_col = find_column(
        df,
        [
            "facility",
            "facility name",
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
            "date",
            "reporting date",
            "date of reporting",
            "event date",
            "दिनांक",
        ]
    )

    # --------------------------------------------------------
    # FORM
    # --------------------------------------------------------

    with st.form("global_dashboard_filter_form"):

        # ====================================================
        # ROW 1
        # ====================================================

        r1 = st.columns(4)

        with r1[0]:
            year_values = get_values(df, year_col)

            selected_years = st.multiselect(
                "Year",
                year_values,
                default=year_values,
                key="global_year_filter",
            )

        with r1[1]:
            month_values = get_values(df, month_col)

            selected_months = st.multiselect(
                "Month",
                month_values,
                default=month_values,
                key="global_month_filter",
            )

        with r1[2]:
            week_values = get_values(df, week_col)

            selected_weeks = st.multiselect(
                "Week",
                week_values,
                default=week_values,
                key="global_week_filter",
            )

        with r1[3]:
            disease_values = get_values(df, disease_col)

            selected_diseases = st.multiselect(
                "Disease",
                disease_values,
                default=disease_values,
                key="global_disease_filter",
            )

        # ====================================================
        # ROW 2
        # ====================================================

        r2 = st.columns(4)

        with r2[0]:
            facility_values = get_values(df, facility_col)

            selected_facilities = st.multiselect(
                "Facility",
                facility_values,
                default=facility_values,
                key="global_facility_filter",
            )

        with r2[1]:
            ward_values = get_values(df, ward_col)

            selected_wards = st.multiselect(
                "Ward",
                ward_values,
                default=ward_values,
                key="global_ward_filter",
            )

        with r2[2]:
            gender_values = get_values(df, gender_col)

            selected_genders = st.multiselect(
                "Gender",
                gender_values,
                default=gender_values,
                key="global_gender_filter",
            )

        with r2[3]:
            age_values = get_values(df, age_group_col)

            selected_age_groups = st.multiselect(
                "Age Group",
                age_values,
                default=age_values,
                key="global_age_filter",
            )

        # ====================================================
        # ROW 3
        # ====================================================

        r3 = st.columns(3)

        with r3[0]:
            opd_values = get_values(df, opd_ipd_col)

            selected_opd_ipd = st.multiselect(
                "OPD / IPD",
                opd_values,
                default=opd_values,
                key="global_opdipd_filter",
            )

        with r3[1]:
            area_values = get_values(df, area_col)

            selected_areas = st.multiselect(
                "Area",
                area_values,
                default=area_values,
                key="global_area_filter",
            )

        with r3[2]:
            status_values = get_values(df, status_col)

            selected_status = st.multiselect(
                "Status",
                status_values,
                default=status_values,
                key="global_status_filter",
            )

        # ====================================================
        # DATE FILTER
        # ====================================================

        st.markdown("**📅 Reporting Date Range**")

        d1, d2 = st.columns(2)

        date_from = None
        date_to = None

        if date_col and date_col in df.columns:

            date_series = pd.to_datetime(
                df[date_col],
                errors="coerce"
            ).dropna()

            if not date_series.empty:

                min_date = date_series.min().date()
                max_date = date_series.max().date()

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
        # BUTTONS
        # ====================================================

        b1, b2 = st.columns([1, 5])

        with b1:
            apply_clicked = st.form_submit_button(
                "🔄 Apply Filters",
                type="primary",
                use_container_width=True,
            )

        with b2:
            reset_clicked = st.form_submit_button(
                "↩ Reset Filters",
                use_container_width=True,
            )

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    if reset_clicked:

        keys_to_clear = [
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
            "global_date_from",
            "global_date_to",
        ]

        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

        st.rerun()

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
# FAST FILTER FUNCTION
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

    if df is None or df.empty:
        return df

    # Start with all rows
    mask = pd.Series(True, index=df.index)

    def apply_text_filter(column, selected):

        nonlocal mask

        if column is None:
            return

        if column not in df.columns:
            return

        if selected is None:
            return

        # Empty selection = no records
        if len(selected) == 0:
            mask &= False
            return

        mask &= df[column].astype(str).isin(selected)

    # --------------------------------------------------------
    # Text filters
    # --------------------------------------------------------

    year_col = find_column(df, ["year", "वर्ष"])
    month_col = find_column(df, ["month", "महिना"])
    week_col = find_column(df, ["week", "week no", "week number", "आठवडा"])
    disease_col = find_column(
        df,
        ["disease", "disease name", "diagnosis", "रोग"]
    )
    facility_col = find_column(
        df,
        ["facility", "facility name", "health facility", "institution"]
    )
    ward_col = find_column(
        df,
        ["ward", "ward name", "ward no", "ward number"]
    )
    gender_col = find_column(
        df,
        ["gender", "sex", "लिंग"]
    )
    age_group_col = find_column(
        df,
        ["age group", "age_group", "agegroup", "age category"]
    )
    opd_ipd_col = find_column(
        df,
        ["opd/ipd", "opd ipd", "opd_ipd", "patient type", "service type"]
    )

    apply_text_filter(year_col, selected_years)
    apply_text_filter(month_col, selected_months)
    apply_text_filter(week_col, selected_weeks)
    apply_text_filter(disease_col, selected_diseases)
    apply_text_filter(facility_col, selected_facilities)
    apply_text_filter(ward_col, selected_wards)
    apply_text_filter(gender_col, selected_genders)
    apply_text_filter(age_group_col, selected_age_groups)
    apply_text_filter(opd_ipd_col, selected_opd_ipd)

    apply_text_filter(area_column, selected_areas)
    apply_text_filter(status_column, selected_status)

    # --------------------------------------------------------
    # Date filter
    # --------------------------------------------------------

    date_col = find_column(
        df,
        [
            "date",
            "reporting date",
            "date of reporting",
            "event date",
            "दिनांक",
        ]
    )

    if (
        date_col is not None
        and date_col in df.columns
        and (date_from is not None or date_to is not None)
    ):

        if pd.api.types.is_datetime64_any_dtype(df[date_col]):
            dates = df[date_col]
        else:
            dates = pd.to_datetime(
                df[date_col],
                errors="coerce",
                format="mixed"
            )

        if date_from is not None:
            mask &= dates.dt.date >= date_from

        if date_to is not None:
            mask &= dates.dt.date <= date_to

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
        }

    disease_col = find_column(
        df,
        ["disease", "disease name", "diagnosis", "रोग"]
    )

    facility_col = find_column(
        df,
        ["facility", "facility name", "health facility", "institution"]
    )

    ward_col = find_column(
        df,
        ["ward", "ward name", "ward no", "ward number"]
    )

    return {
        "total_records": len(df),

        "diseases": (
            df[disease_col].nunique()
            if disease_col
            else 0
        ),

        "facilities": (
            df[facility_col].nunique()
            if facility_col
            else 0
        ),

        "wards": (
            df[ward_col].nunique()
            if ward_col
            else 0
        ),
    }


# ============================================================
# OVERVIEW
# ============================================================

def render_overview(df):

    st.subheader("📊 Programme Overview")

    if df is None or df.empty:
        st.warning("No records available for the selected filters.")
        return

    facility_col = find_column(
        df,
        ["facility", "facility name", "health facility", "institution"]
    )

    ward_col = find_column(
        df,
        ["ward", "ward name", "ward no", "ward number"]
    )

    disease_col = find_column(
        df,
        ["disease", "disease name", "diagnosis", "रोग"]
    )

    date_col = find_column(
        df,
        [
            "date",
            "reporting date",
            "date of reporting",
            "event date",
            "दिनांक",
        ]
    )

    # ========================================================
    # TOP FACILITIES / WARDS
    # ========================================================

    c1, c2 = st.columns(2)

    with c1:

        st.markdown("#### 🏥 Top Facilities")

        if facility_col:

            facility_counts = (
                df[facility_col]
                .astype(str)
                .value_counts()
                .head(10)
            )

            if not facility_counts.empty:
                st.dataframe(
                    facility_counts.rename("Records"),
                    use_container_width=True,
                )

    with c2:

        st.markdown("#### 🏘️ Top Burden Wards")

        if ward_col:

            ward_counts = (
                df[ward_col]
                .astype(str)
                .value_counts()
                .head(10)
            )

            if not ward_counts.empty:
                st.dataframe(
                    ward_counts.rename("Records"),
                    use_container_width=True,
                )

    # ========================================================
    # MONTHLY TREND
    # ========================================================

    st.markdown("#### 📈 Monthly Trend")

    if date_col:

        if pd.api.types.is_datetime64_any_dtype(df[date_col]):
            dates = df[date_col]
        else:
            dates = pd.to_datetime(
                df[date_col],
                errors="coerce",
                format="mixed"
            )

        trend_df = (
            pd.DataFrame({"Date": dates})
            .dropna()
        )

        if not trend_df.empty:

            trend_df["Month"] = (
                trend_df["Date"]
                .dt.to_period("M")
                .astype(str)
            )

            monthly = (
                trend_df["Month"]
                .value_counts()
                .sort_index()
            )

            st.line_chart(monthly)

    # ========================================================
    # DISEASE DISTRIBUTION
    # ========================================================

    if disease_col:

        st.markdown("#### 🦠 Disease Distribution")

        disease_counts = (
            df[disease_col]
            .astype(str)
            .value_counts()
            .head(15)
        )

        st.bar_chart(disease_counts)
