import pandas as pd
import streamlit as st

from phase1_data import refresh_data

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _unique(df, column):
    if column not in df.columns:
        return []
    return sorted(
        df[column].dropna().unique().tolist(),
        key=str
    )


def _reset_filter_state():
    """Clear all filter widget values before the next rerun."""
    filter_keys = [
        "filter_years",
        "filter_months",
        "filter_weeks",
        "filter_diseases",
        "filter_wards",
        "filter_genders",
        "filter_opd_ipd",
        "filter_date_range",
    ]

    for key in filter_keys:
        st.session_state.pop(key, None)


def create_filters(df):
    st.sidebar.divider()
    st.sidebar.subheader("Dashboard Controls")

    refresh_col, reset_col = st.sidebar.columns(2)

    with refresh_col:
        if st.button(
            "🔄 Refresh",
            key="refresh_data_button",
            use_container_width=True,
            help="Reload the latest data from Google Sheets",
        ):
            refresh_data()

    with reset_col:
        if st.button(
            "↩️ Reset",
            key="reset_filters_button",
            use_container_width=True,
            help="Clear all selected filters",
        ):
            _reset_filter_state()
            st.rerun()

    years = sorted(_unique(df, "Year"), key=lambda x: int(x))
    months = [
        m for m in MONTH_ORDER
        if m in _unique(df, "Month")
    ]
    weeks = _unique(df, "Week")
    diseases = _unique(df, "Confirmed Diagnosis")
    wards = _unique(df, "Ward")
    genders = _unique(df, "Gender")
    opd_ipd = _unique(df, "Opd Ipd")

    selected_years = st.sidebar.multiselect(
        "Year",
        years,
        default=years,
        key="filter_years",
    )

    selected_months = st.sidebar.multiselect(
        "Month",
        months,
        default=months,
        key="filter_months",
    )

    selected_weeks = st.sidebar.multiselect(
        "Week",
        weeks,
        default=weeks,
        key="filter_weeks",
    )

    selected_diseases = st.sidebar.multiselect(
        "Disease",
        diseases,
        default=[],
        key="filter_diseases",
    )

    selected_wards = st.sidebar.multiselect(
        "Ward",
        wards,
        default=[],
        key="filter_wards",
    )

    selected_genders = st.sidebar.multiselect(
        "Gender",
        genders,
        default=[],
        key="filter_genders",
    )

    selected_opd_ipd = st.sidebar.multiselect(
        "OPD / IPD",
        opd_ipd,
        default=[],
        key="filter_opd_ipd",
    )

    date_from = None
    date_to = None

    if "Reporting Date" in df.columns:
        dates = df["Reporting Date"].dropna()

        if not dates.empty:
            min_date = dates.min().date()
            max_date = dates.max().date()

            date_range = st.sidebar.date_input(
                "Reporting Date",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="filter_date_range",
            )

            if isinstance(date_range, tuple):
                if len(date_range) == 2:
                    date_from, date_to = date_range
                elif len(date_range) == 1:
                    date_from = date_to = date_range[0]

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
    out = df.copy()

    filters = [
        ("Year", selected_years),
        ("Month", selected_months),
        ("Week", selected_weeks),
        ("Confirmed Diagnosis", selected_diseases),
        ("Ward", selected_wards),
        ("Gender", selected_genders),
        ("Opd Ipd", selected_opd_ipd),
    ]

    for column, values in filters:
        if values and column in out.columns:
            out = out[out[column].isin(values)]

    if date_from is not None and "Reporting Date" in out.columns:
        out = out[
            out["Reporting Date"].dt.date >= date_from
        ]

    if date_to is not None and "Reporting Date" in out.columns:
        out = out[
            out["Reporting Date"].dt.date <= date_to
        ]

    return out


def calculate_kpis(df):
    disease = (
        df["Confirmed Diagnosis"].dropna().value_counts()
        if "Confirmed Diagnosis" in df.columns
        else pd.Series(dtype="int64")
    )

    ward = (
        df["Ward"].dropna().value_counts()
        if "Ward" in df.columns
        else pd.Series(dtype="int64")
    )

    facility = (
        df["Facility Name Lform"].dropna().value_counts()
        if "Facility Name Lform" in df.columns
        else pd.Series(dtype="int64")
    )

    return {
        "total": len(df),
        "opd": int(df["Opd Ipd"].eq("OPD").sum())
        if "Opd Ipd" in df.columns else 0,
        "ipd": int(df["Opd Ipd"].eq("IPD").sum())
        if "Opd Ipd" in df.columns else 0,
        "male": int(df["Gender"].eq("M").sum())
        if "Gender" in df.columns else 0,
        "female": int(df["Gender"].eq("F").sum())
        if "Gender" in df.columns else 0,
        "transgender": int(df["Gender"].eq("Transgender").sum())
        if "Gender" in df.columns else 0,
        "top_disease": disease.index[0]
        if len(disease) else "N/A",
        "top_ward": ward.index[0]
        if len(ward) else "N/A",
        "top_facility": facility.index[0]
        if len(facility) else "N/A",
    }


def render_overview(df):
    filters = create_filters(df)

    filtered = apply_filters(
        df,
        **filters
    )

    k = calculate_kpis(filtered)

    st.title("🏥 Health Facility Monitor")
    st.caption(
        "Public Health Surveillance and Management Dashboard"
    )

    st.info(
        f"Showing **{len(filtered):,}** of "
        f"**{len(df):,}** records"
    )

    cols = st.columns(4)

    for col, label, value in [
        (cols[0], "Total Cases", k["total"]),
        (cols[1], "OPD Cases", k["opd"]),
        (cols[2], "IPD Cases", k["ipd"]),
        (cols[3], "Top Ward", k["top_ward"]),
    ]:
        col.metric(
            label,
            f"{value:,}"
            if isinstance(value, int)
            else value,
        )

    cols = st.columns(4)

    for col, label, value in [
        (cols[0], "Male", k["male"]),
        (cols[1], "Female", k["female"]),
        (cols[2], "Top Disease", k["top_disease"]),
        (cols[3], "Top Facility", k["top_facility"]),
    ]:
        col.metric(
            label,
            f"{value:,}"
            if isinstance(value, int)
            else value,
        )

    st.divider()
    st.subheader("Filtered Records")

    st.dataframe(
        filtered.head(100),
        use_container_width=True,
        hide_index=True,
    )
