import pandas as pd
import streamlit as st


# ============================================================
# HELPERS
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
# AGE GROUP CREATION
# ============================================================

def create_age_group(age_series):

    age_numeric = pd.to_numeric(
        age_series,
        errors="coerce"
    )

    def classify(age):

        if pd.isna(age):
            return "Unknown"

        if age < 1:
            return "<1 Year"

        elif age <= 4:
            return "1–4 Years"

        elif age <= 14:
            return "5–14 Years"

        elif age <= 24:
            return "15–24 Years"

        elif age <= 44:
            return "25–44 Years"

        elif age <= 59:
            return "45–59 Years"

        else:
            return "60+ Years"

    return age_numeric.apply(classify)


# ============================================================
# MAIN FUNCTION
# ============================================================

def render_drilldown_export(df):

    st.title("🔎 Detailed Management Drill-down")

    st.caption(
        "Age-wise analysis, facility × ward drill-down and "
        "filtered data export."
    )

    if df is None or df.empty:

        st.warning("No data available.")

        return

    data = df.copy()

    # --------------------------------------------------------
    # DETECT COLUMNS
    # --------------------------------------------------------

    facility_col = find_column(
        data,
        [
            "Facility Name Lform",
            "Facility",
            "Facility Name",
            "Health Facility",
            "Health Facility Name",
        ],
    )

    ward_col = find_column(
        data,
        [
            "Ward",
            "Ward Name",
            "Ward No",
            "Ward Number",
        ],
    )

    age_col = find_column(
        data,
        [
            "Age",
            "Age Years",
            "Age (Years)",
        ],
    )

    gender_col = find_column(
        data,
        [
            "Gender",
            "Sex",
        ],
    )

    disease_col = find_column(
        data,
        [
            "Confirmed Diagnosis",
            "Disease",
            "Disease Name",
            "Diagnosis",
        ],
    )

    month_col = find_column(
        data,
        [
            "Month",
        ],
    )

    # ========================================================
    # MANAGEMENT FILTERS
    # ========================================================

    st.divider()

    st.subheader("🎛️ Detailed Filters")

    c1, c2, c3 = st.columns(3)

    # --------------------------------------------------------
    # FACILITY
    # --------------------------------------------------------

    if facility_col:

        facility_values = sorted(
            clean_series(data[facility_col])
            .dropna()
            .unique()
            .tolist()
        )

        selected_facility = c1.multiselect(
            "🏥 Facility",
            facility_values,
            placeholder="All Facilities",
        )

    else:

        selected_facility = []

    # --------------------------------------------------------
    # WARD
    # --------------------------------------------------------

    if ward_col:

        ward_values = sorted(
            clean_series(data[ward_col])
            .dropna()
            .unique()
            .tolist()
        )

        selected_ward = c2.multiselect(
            "🗺️ Ward",
            ward_values,
            placeholder="All Wards",
        )

    else:

        selected_ward = []

    # --------------------------------------------------------
    # GENDER
    # --------------------------------------------------------

    if gender_col:

        gender_values = sorted(
            clean_series(data[gender_col])
            .dropna()
            .unique()
            .tolist()
        )

        selected_gender = c3.multiselect(
            "👥 Gender",
            gender_values,
            placeholder="All Genders",
        )

    else:

        selected_gender = []

    # --------------------------------------------------------
    # DISEASE
    # --------------------------------------------------------

    if disease_col:

        disease_values = sorted(
            clean_series(data[disease_col])
            .dropna()
            .unique()
            .tolist()
        )

        selected_disease = st.multiselect(
            "🦠 Disease / Diagnosis",
            disease_values,
            placeholder="All Diseases",
        )

    else:

        selected_disease = []

    # --------------------------------------------------------
    # APPLY FILTERS
    # --------------------------------------------------------

    filtered = data.copy()

    if selected_facility:

        filtered = filtered[
            clean_series(
                filtered[facility_col]
            ).isin(selected_facility)
        ]

    if selected_ward:

        filtered = filtered[
            clean_series(
                filtered[ward_col]
            ).isin(selected_ward)
        ]

    if selected_gender:

        filtered = filtered[
            clean_series(
                filtered[gender_col]
            ).isin(selected_gender)
        ]

    if selected_disease:

        filtered = filtered[
            clean_series(
                filtered[disease_col]
            ).isin(selected_disease)
        ]

    if filtered.empty:

        st.warning(
            "No records match the selected filters."
        )

        return

    # ========================================================
    # FILTERED KPI
    # ========================================================

    st.divider()

    st.subheader("📊 Selected Population")

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Records",
        f"{len(filtered):,}",
    )

    k2.metric(
        "Facilities",
        f"{filtered[facility_col].nunique():,}"
        if facility_col
        else "0",
    )

    k3.metric(
        "Wards",
        f"{filtered[ward_col].nunique():,}"
        if ward_col
        else "0",
    )

    k4.metric(
        "Diseases",
        f"{filtered[disease_col].nunique():,}"
        if disease_col
        else "0",
    )

    # ========================================================
    # AGE-WISE ANALYSIS
    # ========================================================

    st.divider()

    st.subheader("👶 Age-wise Analysis")

    if age_col:

        filtered["_Age_Group"] = create_age_group(
            filtered[age_col]
        )

        age_order = [
            "<1 Year",
            "1–4 Years",
            "5–14 Years",
            "15–24 Years",
            "25–44 Years",
            "45–59 Years",
            "60+ Years",
            "Unknown",
        ]

        age_table = (
            filtered["_Age_Group"]
            .value_counts()
            .reindex(
                age_order,
                fill_value=0
            )
            .rename_axis("Age Group")
            .reset_index(name="Cases")
        )

        total_age_cases = age_table["Cases"].sum()

        if total_age_cases > 0:

            age_table["Share (%)"] = (
                age_table["Cases"]
                / total_age_cases
                * 100
            ).round(2)

        else:

            age_table["Share (%)"] = 0

        st.dataframe(
            age_table,
            use_container_width=True,
            hide_index=True,
        )

        st.bar_chart(
            age_table.set_index("Age Group")["Cases"]
        )

    else:

        st.warning(
            "Age column was not detected in the dataset."
        )

    # ========================================================
    # AGE × GENDER
    # ========================================================

    st.divider()

    st.subheader("👥 Age × Gender Distribution")

    if age_col and gender_col:

        age_gender = (
            filtered
            .groupby(
                [
                    "_Age_Group",
                    gender_col,
                ],
                dropna=False,
            )
            .size()
            .reset_index(name="Cases")
        )

        age_gender = age_gender.rename(
            columns={
                "_Age_Group": "Age Group",
                gender_col: "Gender",
            }
        )

        st.dataframe(
            age_gender,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # FACILITY × WARD DRILL-DOWN
    # ========================================================

    st.divider()

    st.subheader(
        "🏥 Facility × 🗺️ Ward Drill-down"
    )

    if facility_col and ward_col:

        drilldown = (
            filtered
            .groupby(
                [
                    facility_col,
                    ward_col,
                ]
            )
            .size()
            .reset_index(name="Cases")
            .sort_values(
                "Cases",
                ascending=False,
            )
        )

        drilldown.insert(
            0,
            "Rank",
            range(
                1,
                len(drilldown) + 1
            ),
        )

        st.dataframe(
            drilldown,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Facility and Ward fields are required."
        )

    # ========================================================
    # FACILITY × AGE
    # ========================================================

    st.divider()

    st.subheader(
        "🏥 Facility × Age Group"
    )

    if facility_col and age_col:

        facility_age = (
            filtered
            .groupby(
                [
                    facility_col,
                    "_Age_Group",
                ]
            )
            .size()
            .reset_index(name="Cases")
        )

        facility_age = facility_age.rename(
            columns={
                facility_col: "Facility",
                "_Age_Group": "Age Group",
            }
        )

        st.dataframe(
            facility_age,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # WARD × GENDER
    # ========================================================

    st.divider()

    st.subheader(
        "🗺️ Ward × Gender"
    )

    if ward_col and gender_col:

        ward_gender = (
            filtered
            .groupby(
                [
                    ward_col,
                    gender_col,
                ]
            )
            .size()
            .reset_index(name="Cases")
        )

        ward_gender = ward_gender.rename(
            columns={
                ward_col: "Ward",
                gender_col: "Gender",
            }
        )

        st.dataframe(
            ward_gender,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # MONTH × FACILITY
    # ========================================================

    st.divider()

    st.subheader(
        "📅 Month × Facility"
    )

    if month_col and facility_col:

        month_facility = (
            filtered
            .groupby(
                [
                    month_col,
                    facility_col,
                ]
            )
            .size()
            .reset_index(name="Cases")
        )

        month_facility = month_facility.rename(
            columns={
                month_col: "Month",
                facility_col: "Facility",
            }
        )

        st.dataframe(
            month_facility,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # EXPORT
    # ========================================================

    st.divider()

    st.subheader("📤 Export Filtered Data")

    export_df = filtered.copy()

    if "_Age_Group" in export_df.columns:

        export_df = export_df.drop(
            columns=["_Age_Group"]
        )

    csv_data = export_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="⬇️ Download Filtered CSV",
        data=csv_data,
        file_name="filtered_management_data.csv",
        mime="text/csv",
    )

    # ========================================================
    # FULL DATA VIEW
    # ========================================================

    with st.expander(
        "📋 View Filtered Records"
    ):

        st.dataframe(
            export_df,
            use_container_width=True,
            hide_index=True,
        )

