import pandas as pd
import streamlit as st

from phase1_data import refresh_data


# ============================================================
# FILTER DATA
# ============================================================

def apply_filters(
    df,
    selected_years,
    selected_months,
    selected_weeks,
    selected_diseases,
    selected_wards,
    selected_genders,
    selected_opd_ipd,
    date_from,
    date_to,
):

    filtered = df.copy()

    if selected_years:

        filtered = filtered[
            filtered["Year"].isin(
                selected_years
            )
        ]

    if selected_months:

        filtered = filtered[
            filtered["Month"].isin(
                selected_months
            )
        ]

    if selected_weeks:

        filtered = filtered[
            filtered["Week"].isin(
                selected_weeks
            )
        ]

    if selected_diseases:

        filtered = filtered[
            filtered[
                "Confirmed Diagnosis"
            ].isin(
                selected_diseases
            )
        ]

    if selected_wards:

        filtered = filtered[
            filtered["Ward"].isin(
                selected_wards
            )
        ]

    if selected_genders:

        filtered = filtered[
            filtered["Gender"].isin(
                selected_genders
            )
        ]

    if selected_opd_ipd:

        filtered = filtered[
            filtered["Opd Ipd"].isin(
                selected_opd_ipd
            )
        ]

    if date_from is not None:

        filtered = filtered[
            filtered["Reporting Date"].dt.date
            >= date_from
        ]

    if date_to is not None:

        filtered = filtered[
            filtered["Reporting Date"].dt.date
            <= date_to
        ]

    return filtered


# ============================================================
# SIDEBAR FILTERS
# ============================================================

def create_filters(df):

    st.sidebar.divider()

    if st.sidebar.button(
        "🔄 Refresh Data",
        use_container_width=True,
    ):

        refresh_data()

    st.sidebar.divider()

    # --------------------------------------------------------
    # Year
    # --------------------------------------------------------

    years = sorted(
        df["Year"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_years = st.sidebar.multiselect(
        "Year",
        years,
        default=years,
    )

    # --------------------------------------------------------
    # Month
    # --------------------------------------------------------

    month_order = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    available_months = [
        month
        for month in month_order
        if month in
        df["Month"].dropna().unique()
    ]

    selected_months = st.sidebar.multiselect(
        "Month",
        available_months,
        default=available_months,
    )

    # --------------------------------------------------------
    # Week
    # --------------------------------------------------------

    week_values = (
        df["Week"]
        .dropna()
        .unique()
        .tolist()
    )

    def week_sort(value):

        text = str(value)

        digits = pd.Series(
            text
        ).str.extract(
            r"(\d+)"
        ).iloc[0, 0]

        return (
            int(digits)
            if pd.notna(digits)
            else 999
        )

    week_values = sorted(
        week_values,
        key=week_sort,
    )

    selected_weeks = st.sidebar.multiselect(
        "Week",
        week_values,
        default=week_values,
    )

    # --------------------------------------------------------
    # Disease
    # --------------------------------------------------------

    diseases = sorted(
        df["Confirmed Diagnosis"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_diseases = st.sidebar.multiselect(
        "Disease",
        diseases,
    )

    # --------------------------------------------------------
    # Ward
    # --------------------------------------------------------

    wards = sorted(
        df["Ward"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_wards = st.sidebar.multiselect(
        "Ward",
        wards,
    )

    # --------------------------------------------------------
    # Gender
    # --------------------------------------------------------

    gender_order = [
        "M",
        "F",
        "Transgender",
    ]

    genders = [
        gender
        for gender in gender_order
        if gender in
        df["Gender"].dropna().unique()
    ]

    selected_genders = st.sidebar.multiselect(
        "Gender",
        genders,
    )

    # --------------------------------------------------------
    # OPD / IPD
    # --------------------------------------------------------

    opd_ipd = [
        value
        for value in [
            "OPD",
            "IPD",
        ]
        if value in
        df["Opd Ipd"].dropna().unique()
    ]

    selected_opd_ipd = st.sidebar.multiselect(
        "OPD / IPD",
        opd_ipd,
    )

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    st.sidebar.subheader(
        "Reporting Date"
    )

    valid_dates = (
        df["Reporting Date"]
        .dropna()
    )

    if not valid_dates.empty:

        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()

        date_range = st.sidebar.date_input(
            "Date range",
            value=(
                min_date,
                max_date,
            ),
            min_value=min_date,
            max_value=max_date,
        )

        if (
            isinstance(
                date_range,
                tuple,
            )
            and len(date_range) == 2
        ):

            date_from = date_range[0]
            date_to = date_range[1]

        else:

            date_from = min_date
            date_to = max_date

    else:

        date_from = None
        date_to = None

    return {
        "selected_years": selected_years,
        "selected_months": selected_months,
        "selected_weeks": selected_weeks,
        "selected_diseases": selected_diseases,
        "selected_wards": selected_wards,
        "selected_genders": selected_genders,
        "selected_opd_ipd": selected_opd_ipd,
        "date_from": date_from,
        "date_to": date_to,
    }


# ============================================================
# KPIs
# ============================================================

def calculate_kpis(df):

    total = len(df)

    opd = (
        df["Opd Ipd"]
        .eq("OPD")
        .sum()
    )

    ipd = (
        df["Opd Ipd"]
        .eq("IPD")
        .sum()
    )

    male = (
        df["Gender"]
        .eq("M")
        .sum()
    )

    female = (
        df["Gender"]
        .eq("F")
        .sum()
    )

    transgender = (
        df["Gender"]
        .eq("Transgender")
        .sum()
    )

    disease_counts = (
        df["Confirmed Diagnosis"]
        .dropna()
        .value_counts()
    )

    ward_counts = (
        df["Ward"]
        .dropna()
        .value_counts()
    )

    return {
        "total": total,
        "opd": opd,
        "ipd": ipd,
        "male": male,
        "female": female,
        "transgender": transgender,
        "top_disease": (
            disease_counts.index[0]
            if not disease_counts.empty
            else "N/A"
        ),
        "top_ward": (
            ward_counts.index[0]
            if not ward_counts.empty
            else "N/A"
        ),
    }


# ============================================================
# OVERVIEW PAGE
# ============================================================

def render_overview(df):

    filters = create_filters(df)

    filtered_df = apply_filters(
        df,
        **filters,
    )

    kpis = calculate_kpis(
        filtered_df
    )

    st.title(
        "🏥 Health Facility Monitor"
    )

    st.caption(
        "Public Health Surveillance and "
        "Epidemiological Monitoring Dashboard"
    )

    st.info(
        f"Showing **{len(filtered_df):,}** "
        f"of **{len(df):,}** total records"
    )

    st.subheader(
        "Key Indicators"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Cases",
            f"{kpis['total']:,}",
        )

    with col2:
        st.metric(
            "OPD Cases",
            f"{kpis['opd']:,}",
        )

    with col3:
        st.metric(
            "IPD Cases",
            f"{kpis['ipd']:,}",
        )

    with col4:
        st.metric(
            "Male",
            f"{kpis['male']:,}",
        )

    col5, col6, col7, col8 = st.columns(4)

    with col5:
        st.metric(
            "Female",
            f"{kpis['female']:,}",
        )

    with col6:
        st.metric(
            "Transgender",
            f"{kpis['transgender']:,}",
        )

    with col7:
        st.metric(
            "Top Disease",
            kpis["top_disease"],
        )

    with col8:
        st.metric(
            "Top Ward",
            kpis["top_ward"],
        )

    st.divider()

    st.subheader(
        "Filtered Records"
    )

    st.dataframe(
        filtered_df.head(100),
        use_container_width=True,
        hide_index=True,
    )

    return filtered_df
