import pandas as pd
import plotly.express as px
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


def layout(fig, height=450):

    fig.update_layout(
        height=height,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20
        ),
        legend_title_text="",
        hovermode="x unified"
    )

    return fig


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
# MAIN FUNCTION
# ============================================================

def render_demographics(df):

    st.title("👥 Demographics & Disease Analysis")

    st.caption(
        "Age-wise, gender-wise and disease-wise analysis "
        "with management-oriented comparisons."
    )

    if df is None or df.empty:

        st.warning("No data available.")

        return

    data = df.copy()

    # ========================================================
    # COLUMN DETECTION
    # ========================================================

    age_col = find_column(
        data,
        [
            "Age",
            "Age Years",
            "Age (Years)",
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

    month_col = find_column(
        data,
        [
            "Month",
        ]
    )

    # ========================================================
    # FILTERS
    # ========================================================

    st.divider()

    st.subheader("🎛️ Analysis Filters")

    c1, c2 = st.columns(2)

    if gender_col:

        gender_values = sorted(
            clean_series(data[gender_col])
            .dropna()
            .unique()
            .tolist()
        )

        selected_gender = c1.multiselect(
            "👥 Gender",
            gender_values,
            placeholder="All Genders"
        )

    else:

        selected_gender = []

    if disease_col:

        disease_values = sorted(
            clean_series(data[disease_col])
            .dropna()
            .unique()
            .tolist()
        )

        selected_disease = c2.multiselect(
            "🦠 Disease / Diagnosis",
            disease_values,
            placeholder="All Diseases"
        )

    else:

        selected_disease = []

    filtered = data.copy()

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
    # KPI
    # ========================================================

    st.divider()

    st.subheader("📊 Demographic KPIs")

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Total Records",
        f"{len(filtered):,}"
    )

    k2.metric(
        "Gender Categories",
        f"{filtered[gender_col].nunique():,}"
        if gender_col
        else "0"
    )

    k3.metric(
        "Disease Categories",
        f"{filtered[disease_col].nunique():,}"
        if disease_col
        else "0"
    )

    k4.metric(
        "Facilities",
        f"{filtered[facility_col].nunique():,}"
        if facility_col
        else "0"
    )

    # ========================================================
    # AGE-WISE ANALYSIS
    # ========================================================

    st.divider()

    st.subheader("🎂 Age-wise Case Distribution")

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

        age_table["Share (%)"] = (
            age_table["Cases"]
            / age_table["Cases"].sum()
            * 100
        ).round(2)

        st.dataframe(
            age_table,
            use_container_width=True,
            hide_index=True
        )

        fig = px.bar(
            age_table,
            x="Age Group",
            y="Cases",
            text="Cases",
            title="Age-wise Case Distribution"
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            layout(fig, 500),
            use_container_width=True
        )

    else:

        st.warning(
            "Age column was not detected."
        )

    # ========================================================
    # GENDER ANALYSIS
    # ========================================================

    st.divider()

    st.subheader("👥 Gender-wise Case Distribution")

    if gender_col:

        gender_table = (
            clean_series(
                filtered[gender_col]
            )
            .dropna()
            .value_counts()
            .rename_axis("Gender")
            .reset_index(name="Cases")
        )

        gender_table["Share (%)"] = (
            gender_table["Cases"]
            / gender_table["Cases"].sum()
            * 100
        ).round(2)

        c1, c2 = st.columns(2)

        with c1:

            fig = px.pie(
                gender_table,
                names="Gender",
                values="Cases",
                title="Gender Distribution"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

        with c2:

            st.dataframe(
                gender_table,
                use_container_width=True,
                hide_index=True
            )

    else:

        st.warning(
            "Gender column was not detected."
        )

    # ========================================================
    # AGE × GENDER
    # ========================================================

    st.divider()

    st.subheader("👥 Age × Gender Analysis")

    if age_col and gender_col:

        age_gender = (
            filtered
            .groupby(
                [
                    "_Age_Group",
                    gender_col
                ]
            )
            .size()
            .reset_index(name="Cases")
        )

        age_gender = age_gender.rename(
            columns={
                "_Age_Group": "Age Group",
                gender_col: "Gender"
            }
        )

        fig = px.bar(
            age_gender,
            x="Age Group",
            y="Cases",
            color="Gender",
            barmode="group",
            text="Cases",
            title="Age Group × Gender"
        )

        st.plotly_chart(
            layout(fig, 550),
            use_container_width=True
        )

        st.dataframe(
            age_gender,
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # DISEASE BURDEN
    # ========================================================

    st.divider()

    st.subheader("🦠 Disease-wise Case Burden")

    if disease_col:

        disease_table = (
            clean_series(
                filtered[disease_col]
            )
            .dropna()
            .value_counts()
            .rename_axis("Disease")
            .reset_index(name="Cases")
        )

        disease_table["Share (%)"] = (
            disease_table["Cases"]
            / disease_table["Cases"].sum()
            * 100
        ).round(2)

        disease_table.insert(
            0,
            "Rank",
            range(
                1,
                len(disease_table) + 1
            )
        )

        st.dataframe(
            disease_table,
            use_container_width=True,
            hide_index=True
        )

        chart_df = (
            disease_table
            .head(20)
            .sort_values("Cases")
        )

        fig = px.bar(
            chart_df,
            x="Cases",
            y="Disease",
            orientation="h",
            text="Cases",
            title="Top 20 Diseases by Case Burden"
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            layout(fig, 650),
            use_container_width=True
        )

    else:

        st.warning(
            "Disease / diagnosis column was not detected."
        )

    # ========================================================
    # DISEASE × GENDER
    # ========================================================

    st.divider()

    st.subheader("🦠 Disease × Gender")

    if disease_col and gender_col:

        disease_gender = (
            filtered
            .groupby(
                [
                    disease_col,
                    gender_col
                ]
            )
            .size()
            .reset_index(name="Cases")
        )

        disease_gender = disease_gender.rename(
            columns={
                disease_col: "Disease",
                gender_col: "Gender"
            }
        )

        top_diseases = (
            disease_gender
            .groupby("Disease")["Cases"]
            .sum()
            .sort_values(
                ascending=False
            )
            .head(15)
            .index
        )

        chart_df = disease_gender[
            disease_gender["Disease"].isin(
                top_diseases
            )
        ]

        fig = px.bar(
            chart_df,
            x="Disease",
            y="Cases",
            color="Gender",
            barmode="group",
            title="Top Diseases by Gender"
        )

        fig.update_layout(
            xaxis_tickangle=-45
        )

        st.plotly_chart(
            layout(fig, 600),
            use_container_width=True
        )

    # ========================================================
    # DISEASE × AGE
    # ========================================================

    st.divider()

    st.subheader("🦠 Disease × Age Group")

    if disease_col and age_col:

        disease_age = (
            filtered
            .groupby(
                [
                    disease_col,
                    "_Age_Group"
                ]
            )
            .size()
            .reset_index(name="Cases")
        )

        disease_age = disease_age.rename(
            columns={
                disease_col: "Disease",
                "_Age_Group": "Age Group"
            }
        )

        top_diseases = (
            disease_age
            .groupby("Disease")["Cases"]
            .sum()
            .sort_values(
                ascending=False
            )
            .head(15)
            .index
        )

        heat_df = disease_age[
            disease_age["Disease"].isin(
                top_diseases
            )
        ]

        if not heat_df.empty:

            matrix = pd.pivot_table(
                heat_df,
                index="Disease",
                columns="Age Group",
                values="Cases",
                aggfunc="sum",
                fill_value=0
            )

            fig = px.imshow(
                matrix,
                text_auto=True,
                aspect="auto",
                title="Disease × Age Group"
            )

            st.plotly_chart(
                layout(fig, 650),
                use_container_width=True
            )

    # ========================================================
    # FACILITY × DEMOGRAPHICS
    # ========================================================

    st.divider()

    st.subheader(
        "🏥 Facility-wise Demographic Summary"
    )

    if facility_col:

        facility_demo = (
            filtered
            .groupby(facility_col)
            .agg(
                Cases=(facility_col, "size"),
                Wards=(
                    ward_col,
                    "nunique"
                ) if ward_col else (
                    facility_col,
                    "size"
                ),
                Diseases=(
                    disease_col,
                    "nunique"
                ) if disease_col else (
                    facility_col,
                    "size"
                ),
            )
            .reset_index()
        )

        facility_demo = facility_demo.rename(
            columns={
                facility_col: "Facility"
            }
        )

        facility_demo = facility_demo.sort_values(
            "Cases",
            ascending=False
        )

        st.dataframe(
            facility_demo,
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # WARD × DEMOGRAPHICS
    # ========================================================

    st.divider()

    st.subheader(
        "🗺️ Ward-wise Demographic Summary"
    )

    if ward_col:

        ward_demo = (
            filtered
            .groupby(ward_col)
            .agg(
                Cases=(ward_col, "size"),
                Facilities=(
                    facility_col,
                    "nunique"
                ) if facility_col else (
                    ward_col,
                    "size"
                ),
                Diseases=(
                    disease_col,
                    "nunique"
                ) if disease_col else (
                    ward_col,
                    "size"
                ),
            )
            .reset_index()
        )

        ward_demo = ward_demo.rename(
            columns={
                ward_col: "Ward"
            }
        )

        ward_demo = ward_demo.sort_values(
            "Cases",
            ascending=False
        )

        st.dataframe(
            ward_demo,
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # CLEANUP
    # ========================================================

    if "_Age_Group" in filtered.columns:

        filtered.drop(
            columns=["_Age_Group"],
            inplace=True
        )
