import pandas as pd
import plotly.express as px
import streamlit as st

from phase2_overview import apply_filters, create_filters


# ============================================================
# COMMON CHART LAYOUT
# ============================================================

def _layout(fig, height=450):

    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text="",
        hovermode="x unified",
    )

    return fig


# ============================================================
# CLEAN VALUE
# ============================================================

def _clean(series):

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
# MAIN FUNCTION
# ============================================================

def render_ward_analysis(df):

    st.title("🏥 Facility-wise + Ward-wise Management Analysis")

    st.caption(
        "Interactive facility and ward burden monitoring, "
        "disease pattern, demographic distribution and monthly trend analysis."
    )

    # --------------------------------------------------------
    # BASIC CHECK
    # --------------------------------------------------------

    if df is None or df.empty:

        st.warning("No data available.")

        return

    # --------------------------------------------------------
    # STANDARD COLUMN CHECK
    # --------------------------------------------------------

    required_columns = {
        "Ward": "Ward",
        "Facility Name Lform": "Facility",
        "Confirmed Diagnosis": "Disease",
        "Gender": "Gender",
        "Month": "Month",
    }

    available = {
        key: value
        for key, value in required_columns.items()
        if key in df.columns
    }

    if "Ward" not in available and "Facility Name Lform" not in available:

        st.error(
            "Ward and Facility fields could not be found in the dataset."
        )

        st.write("Available columns:")

        st.write(list(df.columns))

        return

    # --------------------------------------------------------
    # GLOBAL FILTERS
    # --------------------------------------------------------

    try:

        filters = create_filters(df)

        filtered_df = apply_filters(
            df,
            **filters
        )

    except Exception:

        filtered_df = df.copy()

    # --------------------------------------------------------
    # EMPTY FILTER RESULT
    # --------------------------------------------------------

    if filtered_df.empty:

        st.warning(
            "No records match the selected filters."
        )

        return

    # --------------------------------------------------------
    # INTERACTIVE MANAGEMENT FILTERS
    # --------------------------------------------------------

    st.divider()

    st.subheader("🎛️ Management Filters")

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    # --------------------------------------------------------
    # FACILITY FILTER
    # --------------------------------------------------------

    facility_col = "Facility Name Lform"

    if facility_col in filtered_df.columns:

        facilities = sorted(
            _clean(filtered_df[facility_col])
            .dropna()
            .unique()
            .tolist()
        )

        with filter_col1:

            selected_facilities = st.multiselect(
                "🏥 Facility",
                facilities,
                placeholder="All Facilities",
            )

    else:

        selected_facilities = []

    # --------------------------------------------------------
    # WARD FILTER
    # --------------------------------------------------------

    ward_col = "Ward"

    if ward_col in filtered_df.columns:

        wards = sorted(
            _clean(filtered_df[ward_col])
            .dropna()
            .unique()
            .tolist()
        )

        with filter_col2:

            selected_wards = st.multiselect(
                "🗺️ Ward",
                wards,
                placeholder="All Wards",
            )

    else:

        selected_wards = []

    # --------------------------------------------------------
    # GENDER FILTER
    # --------------------------------------------------------

    gender_col = "Gender"

    if gender_col in filtered_df.columns:

        genders = sorted(
            _clean(filtered_df[gender_col])
            .dropna()
            .unique()
            .tolist()
        )

        with filter_col3:

            selected_genders = st.multiselect(
                "👥 Gender",
                genders,
                placeholder="All Genders",
            )

    else:

        selected_genders = []

    # --------------------------------------------------------
    # APPLY INTERACTIVE FILTERS
    # --------------------------------------------------------

    management_df = filtered_df.copy()

    if selected_facilities:

        management_df = management_df[
            _clean(
                management_df[facility_col]
            ).isin(selected_facilities)
        ]

    if selected_wards:

        management_df = management_df[
            _clean(
                management_df[ward_col]
            ).isin(selected_wards)
        ]

    if selected_genders:

        management_df = management_df[
            _clean(
                management_df[gender_col]
            ).isin(selected_genders)
        ]

    # --------------------------------------------------------
    # DISEASE FILTER
    # --------------------------------------------------------

    if "Confirmed Diagnosis" in management_df.columns:

        disease_values = sorted(
            _clean(
                management_df["Confirmed Diagnosis"]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_diseases = st.multiselect(
            "🦠 Disease / Confirmed Diagnosis",
            disease_values,
            placeholder="All Diseases",
        )

        if selected_diseases:

            management_df = management_df[
                _clean(
                    management_df["Confirmed Diagnosis"]
                ).isin(selected_diseases)
            ]

    # --------------------------------------------------------
    # NO DATA AFTER FILTER
    # --------------------------------------------------------

    if management_df.empty:

        st.warning(
            "No records available for the selected management filters."
        )

        return

    # ========================================================
    # MANAGEMENT KPI
    # ========================================================

    st.divider()

    st.subheader("📊 Management KPIs")

    total_cases = len(management_df)

    total_facilities = (
        management_df[facility_col]
        .nunique(dropna=True)
        if facility_col in management_df.columns
        else 0
    )

    total_wards = (
        management_df[ward_col]
        .nunique(dropna=True)
        if ward_col in management_df.columns
        else 0
    )

    total_diseases = (
        management_df["Confirmed Diagnosis"]
        .nunique(dropna=True)
        if "Confirmed Diagnosis" in management_df.columns
        else 0
    )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "📋 Total Cases",
        f"{total_cases:,}",
    )

    k2.metric(
        "🏥 Facilities",
        f"{total_facilities:,}",
    )

    k3.metric(
        "🗺️ Wards",
        f"{total_wards:,}",
    )

    k4.metric(
        "🦠 Diseases",
        f"{total_diseases:,}",
    )

    # ========================================================
    # TOP FACILITY + TOP WARD
    # ========================================================

    top_col1, top_col2 = st.columns(2)

    # --------------------------------------------------------
    # TOP FACILITY
    # --------------------------------------------------------

    with top_col1:

        st.subheader("🏥 Top Burden Facility")

        if facility_col in management_df.columns:

            facility_counts = (
                _clean(
                    management_df[facility_col]
                )
                .dropna()
                .value_counts()
                .rename_axis("Facility")
                .reset_index(name="Cases")
            )

            if not facility_counts.empty:

                top_facility = facility_counts.iloc[0]

                st.metric(
                    "Highest Case Facility",
                    str(top_facility["Facility"]),
                    f"{int(top_facility['Cases']):,} cases",
                )

            else:

                st.info("Facility data unavailable.")

    # --------------------------------------------------------
    # TOP WARD
    # --------------------------------------------------------

    with top_col2:

        st.subheader("🗺️ Top Burden Ward")

        if ward_col in management_df.columns:

            ward_counts = (
                _clean(
                    management_df[ward_col]
                )
                .dropna()
                .value_counts()
                .rename_axis("Ward")
                .reset_index(name="Cases")
            )

            if not ward_counts.empty:

                top_ward = ward_counts.iloc[0]

                st.metric(
                    "Highest Case Ward",
                    str(top_ward["Ward"]),
                    f"{int(top_ward['Cases']):,} cases",
                )

            else:

                st.info("Ward data unavailable.")

    # ========================================================
    # FACILITY RANKING
    # ========================================================

    st.divider()

    st.subheader("🏥 Facility-wise Case Burden")

    if facility_col in management_df.columns:

        facility_table = (
            _clean(
                management_df[facility_col]
            )
            .dropna()
            .value_counts()
            .rename_axis("Facility")
            .reset_index(name="Cases")
        )

        facility_table["Share (%)"] = (
            facility_table["Cases"]
            / facility_table["Cases"].sum()
            * 100
        ).round(2)

        facility_table.insert(
            0,
            "Rank",
            range(1, len(facility_table) + 1),
        )

        st.dataframe(
            facility_table,
            use_container_width=True,
            hide_index=True,
        )

        chart_df = (
            facility_table
            .head(20)
            .sort_values("Cases")
        )

        fig = px.bar(
            chart_df,
            x="Cases",
            y="Facility",
            orientation="h",
            text="Cases",
            title="Top 20 Facilities by Case Burden",
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            _layout(fig, 650),
            use_container_width=True,
        )

    # ========================================================
    # WARD RANKING
    # ========================================================

    st.divider()

    st.subheader("🗺️ Ward-wise Case Burden")

    if ward_col in management_df.columns:

        ward_table = (
            _clean(
                management_df[ward_col]
            )
            .dropna()
            .value_counts()
            .rename_axis("Ward")
            .reset_index(name="Cases")
        )

        ward_table["Share (%)"] = (
            ward_table["Cases"]
            / ward_table["Cases"].sum()
            * 100
        ).round(2)

        ward_table.insert(
            0,
            "Rank",
            range(1, len(ward_table) + 1),
        )

        st.dataframe(
            ward_table,
            use_container_width=True,
            hide_index=True,
        )

        chart_df = (
            ward_table
            .head(20)
            .sort_values("Cases")
        )

        fig = px.bar(
            chart_df,
            x="Cases",
            y="Ward",
            orientation="h",
            text="Cases",
            title="Top 20 Wards by Case Burden",
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            _layout(fig, 650),
            use_container_width=True,
        )

    # ========================================================
    # FACILITY × WARD MATRIX
    # ========================================================

    st.divider()

    st.subheader("🏥 Facility × 🗺️ Ward Management Matrix")

    if (
        facility_col in management_df.columns
        and ward_col in management_df.columns
    ):

        matrix = pd.crosstab(
            _clean(
                management_df[facility_col]
            ),
            _clean(
                management_df[ward_col]
            ),
        )

        if not matrix.empty:

            st.dataframe(
                matrix,
                use_container_width=True,
            )

    else:

        st.info(
            "Facility and Ward fields are required for this matrix."
        )

    # ========================================================
    # WARD × DISEASE
    # ========================================================

    st.divider()

    st.subheader("🦠 Ward × Disease Burden")

    if (
        ward_col in management_df.columns
        and "Confirmed Diagnosis" in management_df.columns
    ):

        ward_values = (
            _clean(
                management_df[ward_col]
            )
            .dropna()
            .value_counts()
            .head(15)
            .index
        )

        disease_values = (
            _clean(
                management_df["Confirmed Diagnosis"]
            )
            .dropna()
            .value_counts()
            .head(10)
            .index
        )

        heatmap_df = management_df[
            _clean(
                management_df[ward_col]
            ).isin(ward_values)
            &
            _clean(
                management_df["Confirmed Diagnosis"]
            ).isin(disease_values)
        ]

        if not heatmap_df.empty:

            matrix = pd.crosstab(
                _clean(
                    heatmap_df[ward_col]
                ),
                _clean(
                    heatmap_df["Confirmed Diagnosis"]
                ),
            )

            fig = px.imshow(
                matrix,
                text_auto=True,
                aspect="auto",
                title="Top Wards × Top Diseases",
                labels={
                    "x": "Disease",
                    "y": "Ward",
                    "color": "Cases",
                },
            )

            st.plotly_chart(
                _layout(fig, 650),
                use_container_width=True,
            )

    # ========================================================
    # GENDER DISTRIBUTION
    # ========================================================

    st.divider()

    st.subheader("👥 Gender Distribution")

    if "Gender" in management_df.columns:

        gender_table = (
            _clean(
                management_df["Gender"]
            )
            .dropna()
            .value_counts()
            .rename_axis("Gender")
            .reset_index(name="Cases")
        )

        if not gender_table.empty:

            c1, c2 = st.columns(2)

            with c1:

                fig = px.pie(
                    gender_table,
                    names="Gender",
                    values="Cases",
                    title="Gender-wise Case Distribution",
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

            with c2:

                st.dataframe(
                    gender_table,
                    use_container_width=True,
                    hide_index=True,
                )

    # ========================================================
    # MONTHLY TREND
    # ========================================================

    st.divider()

    st.subheader("📅 Monthly Case Comparison")

    if "Month" in management_df.columns:

        monthly = (
            _clean(
                management_df["Month"]
            )
            .dropna()
            .value_counts()
            .rename_axis("Month")
            .reset_index(name="Cases")
        )

        month_order = [
            "Jan", "Feb", "Mar", "Apr",
            "May", "Jun", "Jul", "Aug",
            "Sep", "Oct", "Nov", "Dec",
        ]

        month_map = {
            "January": "Jan",
            "February": "Feb",
            "March": "Mar",
            "April": "Apr",
            "May": "May",
            "June": "Jun",
            "July": "Jul",
            "August": "Aug",
            "September": "Sep",
            "October": "Oct",
            "November": "Nov",
            "December": "Dec",
        }

        monthly["Month"] = (
            monthly["Month"]
            .replace(month_map)
        )

        monthly["Month"] = pd.Categorical(
            monthly["Month"],
            categories=month_order,
            ordered=True,
        )

        monthly = monthly.sort_values("Month")

        fig = px.bar(
            monthly,
            x="Month",
            y="Cases",
            text="Cases",
            title="Monthly Case Comparison",
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            _layout(fig, 500),
            use_container_width=True,
        )

        st.dataframe(
            monthly,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # SELECTED DATA TABLE
    # ========================================================

    st.divider()

    st.subheader("📋 Filtered Management Dataset")

    st.caption(
        f"Showing {len(management_df):,} records after applying filters."
    )

    st.dataframe(
        management_df,
        use_container_width=True,
        hide_index=True,
    )
