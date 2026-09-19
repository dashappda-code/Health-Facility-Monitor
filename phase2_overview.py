```python
import streamlit as st
import pandas as pd


# ============================================================
# COLUMN HELPER
# ============================================================

def find_column(df, possible_names):

    for name in possible_names:

        if name in df.columns:
            return name

    return None


# ============================================================
# GLOBAL FILTERS
# ============================================================

def create_filters(df):

    result = {}

    def options(column):

        if column not in df.columns:
            return []

        values = (
            df[column]
            .dropna()
            .astype(str)
            .str.strip()
        )

        values = values[values != ""]

        return sorted(
            values.unique().tolist()
        )

    result["years"] = options("Year")
    result["months"] = options("Month")
    result["weeks"] = options("Week")
    result["diseases"] = options("Disease")
    result["facilities"] = options("Facility Name")
    result["wards"] = options("Ward Name")
    result["genders"] = options("Gender")
    result["age_groups"] = options("Age Group")
    result["opd_ipd"] = options("OPD/IPD")
    result["areas"] = options("Patient Address")
    result["status"] = options("Confirmed Diagnosis")

    result["selected_years"] = result["years"]
    result["selected_months"] = result["months"]
    result["selected_weeks"] = result["weeks"]
    result["selected_diseases"] = result["diseases"]
    result["selected_facilities"] = result["facilities"]
    result["selected_wards"] = result["wards"]
    result["selected_genders"] = result["genders"]
    result["selected_age_groups"] = result["age_groups"]
    result["selected_opd_ipd"] = result["opd_ipd"]
    result["selected_areas"] = result["areas"]
    result["selected_status"] = result["status"]

    result["area_column"] = "Patient Address"
    result["status_column"] = "Confirmed Diagnosis"

    result["date_from"] = None
    result["date_to"] = None

    return result


# ============================================================
# MULTI SELECT FILTER
# ============================================================

def _filter_multiselect(
    df,
    column,
    selected,
):

    if (
        column not in df.columns
        or not selected
    ):
        return df

    selected = set(
        str(x).strip()
        for x in selected
    )

    values = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return df.loc[
        values.isin(selected)
    ]


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
    date_from,
    date_to,
):

    if df is None or df.empty:
        return pd.DataFrame()

    filtered = df

    filters = [
        ("Year", selected_years),
        ("Month", selected_months),
        ("Week", selected_weeks),
        ("Disease", selected_diseases),
        ("Facility Name", selected_facilities),
        ("Ward Name", selected_wards),
        ("Gender", selected_genders),
        ("Age Group", selected_age_groups),
        ("OPD/IPD", selected_opd_ipd),
        (area_column, selected_areas),
        (status_column, selected_status),
    ]

    for column, selected in filters:

        if (
            column in filtered.columns
            and selected
        ):

            filtered = _filter_multiselect(
                filtered,
                column,
                selected,
            )

    # --------------------------------------------------------
    # Date filter
    # --------------------------------------------------------

    if (
        "Reporting Date" in filtered.columns
        and date_from is not None
    ):

        filtered = filtered.loc[
            filtered["Reporting Date"] >= pd.Timestamp(
                date_from
            )
        ]

    if (
        "Reporting Date" in filtered.columns
        and date_to is not None
    ):

        filtered = filtered.loc[
            filtered["Reporting Date"]
            <= pd.Timestamp(date_to)
        ]

    return filtered.reset_index(drop=True)


# ============================================================
# KPI CALCULATION
# ============================================================

def calculate_kpis(df):

    if df is None or df.empty:

        return {
            "records": 0,
            "diseases": 0,
            "facilities": 0,
            "wards": 0,
            "date_from": None,
            "date_to": None,
        }

    dates = pd.Series(dtype="datetime64[ns]")

    if "Reporting Date" in df.columns:
        dates = df["Reporting Date"].dropna()

    return {
        "records": len(df),

        "diseases": (
            df["Disease"]
            .replace("", pd.NA)
            .nunique()
            if "Disease" in df.columns
            else 0
        ),

        "facilities": (
            df["Facility Name"]
            .replace("", pd.NA)
            .nunique()
            if "Facility Name" in df.columns
            else 0
        ),

        "wards": (
            df["Ward Name"]
            .replace("", pd.NA)
            .nunique()
            if "Ward Name" in df.columns
            else 0
        ),

        "date_from": (
            dates.min()
            if not dates.empty
            else None
        ),

        "date_to": (
            dates.max()
            if not dates.empty
            else None
        ),
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
            "Selected filters नुसार कोणताही data उपलब्ध नाही."
        )

        return

    kpi = calculate_kpis(df)

    # ========================================================
    # KPI ROW
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Total Records",
            f"{kpi['records']:,}",
        )

    with c2:
        st.metric(
            "Diseases",
            f"{kpi['diseases']:,}",
        )

    with c3:
        st.metric(
            "Facilities",
            f"{kpi['facilities']:,}",
        )

    with c4:
        st.metric(
            "Wards",
            f"{kpi['wards']:,}",
        )

    # ========================================================
    # REPORTING PERIOD
    # ========================================================

    if (
        kpi["date_from"] is not None
        and kpi["date_to"] is not None
    ):

        st.caption(
            "Reporting Period: "
            f"{kpi['date_from'].strftime('%d-%m-%Y')}"
            " to "
            f"{kpi['date_to'].strftime('%d-%m-%Y')}"
        )

    st.markdown("---")

    # ========================================================
    # TOP FACILITY + TOP WARD
    # ========================================================

    left, right = st.columns(2)

    with left:

        st.markdown(
            "### 🏥 Top Facilities"
        )

        if "Facility Name" in df.columns:

            facility = (
                df["Facility Name"]
                .replace("", pd.NA)
                .dropna()
                .value_counts()
                .head(10)
                .rename("Records")
                .to_frame()
            )

            if not facility.empty:
                st.dataframe(
                    facility,
                    use_container_width=True,
                )

    with right:

        st.markdown(
            "### 🏘️ Top Wards"
        )

        if "Ward Name" in df.columns:

            ward = (
                df["Ward Name"]
                .replace("", pd.NA)
                .dropna()
                .value_counts()
                .head(10)
                .rename("Records")
                .to_frame()
            )

            if not ward.empty:
                st.dataframe(
                    ward,
                    use_container_width=True,
                )

    # ========================================================
    # MONTHLY TREND
    # ========================================================

    st.markdown("---")

    st.markdown(
        "### 📅 Monthly Trend"
    )

    if (
        "Reporting Date" in df.columns
        and df["Reporting Date"].notna().any()
    ):

        monthly = (
            df.dropna(
                subset=["Reporting Date"]
            )
            .assign(
                Month_Date=lambda x:
                x["Reporting Date"]
                .dt.to_period("M")
                .dt.to_timestamp()
            )
            .groupby("Month_Date")
            .size()
            .reset_index(name="Records")
            .sort_values("Month_Date")
        )

        if not monthly.empty:

            monthly["Month"] = (
                monthly["Month_Date"]
                .dt.strftime("%b-%Y")
            )

            st.line_chart(
                monthly.set_index("Month")[
                    ["Records"]
                ]
            )

    elif "Month" in df.columns:

        monthly = (
            df["Month"]
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .sort_index()
            .rename("Records")
            .to_frame()
        )

        st.bar_chart(monthly)

    # ========================================================
    # DATA STATUS
    # ========================================================

    st.markdown("---")

    st.caption(
        f"Showing {len(df):,} records based on current "
        "Dashboard Control selections."
    )
```
