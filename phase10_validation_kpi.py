import streamlit as st
import pandas as pd


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def find_column(df, possible_names):
    """
    Find the first matching column from a list of possible names.
    Matching is case-insensitive and ignores spaces/underscores.
    """
    normalized = {
        str(col).strip().lower().replace(" ", "").replace("_", ""): col
        for col in df.columns
    }

    for name in possible_names:
        key = str(name).strip().lower().replace(" ", "").replace("_", "")

        if key in normalized:
            return normalized[key]

    return None


def safe_unique(df, column):
    if column and column in df.columns:
        return df[column].dropna().astype(str).str.strip().replace("", pd.NA).dropna().nunique()
    return 0


def clean_series(df, column):
    if column and column in df.columns:
        return (
            df[column]
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
    return pd.Series([pd.NA] * len(df), index=df.index)


# ============================================================
# MANAGEMENT KPI DASHBOARD
# ============================================================

def render_management_kpis(df):

    st.subheader("📊 Management KPI Dashboard")

    if df is None or df.empty:
        st.warning("No data available for KPI calculation.")
        return

    # --------------------------------------------------------
    # Detect important columns
    # --------------------------------------------------------

    facility_col = find_column(
        df,
        [
            "Facility",
            "Facility Name",
            "Health Facility",
            "Health Facility Name",
            "Hospital",
            "Hospital Name",
            "PHC",
            "UPHC",
            "Centre",
            "Center",
        ],
    )

    ward_col = find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "Ward No",
            "Ward Number",
            "Administrative Ward",
        ],
    )

    gender_col = find_column(
        df,
        [
            "Gender",
            "Sex",
        ],
    )

    age_col = find_column(
        df,
        [
            "Age",
            "Age Years",
            "Age (Years)",
        ],
    )

    date_col = find_column(
        df,
        [
            "Date",
            "Case Date",
            "Date of Diagnosis",
            "Diagnosis Date",
            "Reporting Date",
            "Report Date",
            "Registration Date",
        ],
    )

    disease_col = find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "Diagnosis",
            "Disease/Diagnosis",
        ],
    )

    # --------------------------------------------------------
    # Basic totals
    # --------------------------------------------------------

    total_records = len(df)

    total_facilities = safe_unique(df, facility_col)

    total_wards = safe_unique(df, ward_col)

    total_genders = safe_unique(df, gender_col)

    # --------------------------------------------------------
    # Missing data
    # --------------------------------------------------------

    missing_cells = int(df.isna().sum().sum())

    total_cells = int(df.shape[0] * df.shape[1])

    if total_cells > 0:
        completeness = ((total_cells - missing_cells) / total_cells) * 100
    else:
        completeness = 0

    duplicate_rows = int(df.duplicated().sum())

    # --------------------------------------------------------
    # KPI cards
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "📋 Total Records",
        f"{total_records:,}",
    )

    c2.metric(
        "🏥 Facilities",
        f"{total_facilities:,}",
    )

    c3.metric(
        "🗺️ Wards",
        f"{total_wards:,}",
    )

    c4.metric(
        "📈 Data Completeness",
        f"{completeness:.1f}%",
    )

    c5, c6, c7, c8 = st.columns(4)

    c5.metric(
        "👥 Gender Categories",
        f"{total_genders:,}",
    )

    c6.metric(
        "⚠️ Missing Cells",
        f"{missing_cells:,}",
    )

    c7.metric(
        "♻️ Duplicate Rows",
        f"{duplicate_rows:,}",
    )

    c8.metric(
        "📑 Columns",
        f"{len(df.columns):,}",
    )

    st.divider()

    # ========================================================
    # TOP FACILITY
    # ========================================================

    if facility_col:

        facility_data = clean_series(df, facility_col)

        facility_counts = (
            facility_data
            .value_counts()
            .rename_axis("Facility")
            .reset_index(name="Records")
        )

        if not facility_counts.empty:

            top_facility = facility_counts.iloc[0]

            st.markdown("### 🏥 Top Burden Facility")

            f1, f2 = st.columns([2, 1])

            f1.metric(
                "Highest Record Facility",
                str(top_facility["Facility"]),
            )

            f2.metric(
                "Records",
                f"{int(top_facility['Records']):,}",
            )

            with st.expander("View facility-wise ranking"):

                st.dataframe(
                    facility_counts,
                    use_container_width=True,
                    hide_index=True,
                )

    else:

        st.info(
            "Facility column was not automatically identified. "
            "Please check the Google Sheet column name."
        )

    # ========================================================
    # TOP WARD
    # ========================================================

    if ward_col:

        ward_data = clean_series(df, ward_col)

        ward_counts = (
            ward_data
            .value_counts()
            .rename_axis("Ward")
            .reset_index(name="Records")
        )

        if not ward_counts.empty:

            top_ward = ward_counts.iloc[0]

            st.markdown("### 🗺️ Top Burden Ward")

            w1, w2 = st.columns([2, 1])

            w1.metric(
                "Highest Record Ward",
                str(top_ward["Ward"]),
            )

            w2.metric(
                "Records",
                f"{int(top_ward['Records']):,}",
            )

            with st.expander("View ward-wise ranking"):

                st.dataframe(
                    ward_counts,
                    use_container_width=True,
                    hide_index=True,
                )

    else:

        st.info(
            "Ward column was not automatically identified. "
            "Please check the Google Sheet column name."
        )

    # ========================================================
    # MONTHLY ANALYSIS
    # ========================================================

    st.markdown("### 📅 Monthly Management Analysis")

    if date_col:

        temp = df.copy()

        temp["_dashboard_date"] = pd.to_datetime(
            temp[date_col],
            errors="coerce",
            dayfirst=True,
        )

        valid_dates = temp["_dashboard_date"].notna().sum()

        if valid_dates > 0:

            temp["_month"] = temp["_dashboard_date"].dt.to_period("M").astype(str)

            monthly = (
                temp.dropna(subset=["_dashboard_date"])
                .groupby("_month")
                .size()
                .reset_index(name="Records")
                .sort_values("_month")
            )

            st.line_chart(
                monthly.set_index("_month")["Records"]
            )

            st.dataframe(
                monthly,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.warning(
                "Date column detected, but no valid dates could be converted."
            )

    else:

        st.info(
            "Date column was not automatically identified. "
            "Monthly analysis requires a valid date column."
        )

    # ========================================================
    # DATA QUALITY
    # ========================================================

    st.divider()

    st.markdown("### 🔍 Data Validation")

    validation_rows = []

    for col in df.columns:

        missing = int(df[col].isna().sum())

        blanks = int(
            (
                df[col]
                .astype(str)
                .str.strip()
                .isin(["", "nan", "None", "NA", "N/A"])
            ).sum()
        )

        unique = int(df[col].nunique(dropna=True))

        validation_rows.append(
            {
                "Column": col,
                "Missing": missing,
                "Blank / Invalid": blanks,
                "Unique Values": unique,
            }
        )

    validation_df = pd.DataFrame(validation_rows)

    st.dataframe(
        validation_df,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # DETECTED COLUMNS
    # ========================================================

    with st.expander("🔧 Detected Data Fields"):

        detected = pd.DataFrame(
            {
                "Field": [
                    "Facility",
                    "Ward",
                    "Gender",
                    "Age",
                    "Date",
                    "Disease",
                ],
                "Detected Column": [
                    facility_col or "Not detected",
                    ward_col or "Not detected",
                    gender_col or "Not detected",
                    age_col or "Not detected",
                    date_col or "Not detected",
                    disease_col or "Not detected",
                ],
            }
        )

        st.dataframe(
            detected,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_validation_kpi(df):

    render_management_kpis(df)
