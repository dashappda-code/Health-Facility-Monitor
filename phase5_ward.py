import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# COMMON CHART LAYOUT
# ============================================================

def _layout(fig, height=450):

    fig.update_layout(
        height=height,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
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
# COLUMN FINDER
# ============================================================

def _find_column(df, candidates):

    if df is None or df.empty:
        return None

    # Exact match
    for candidate in candidates:

        for col in df.columns:

            if str(col).strip().lower() == candidate.lower():
                return col

    # Partial match
    for candidate in candidates:

        candidate = candidate.lower()

        for col in df.columns:

            if candidate in str(col).strip().lower():
                return col

    return None


# ============================================================
# SAFE UNIQUE VALUES
# ============================================================

def _unique_values(df, column):

    if column is None:
        return []

    if column not in df.columns:
        return []

    values = (
        _clean(df[column])
        .dropna()
        .unique()
        .tolist()
    )

    return sorted(values)


# ============================================================
# LOCAL MANAGEMENT FILTER
# ============================================================

def _apply_local_filter(
    df,
    column,
    selected_values,
):

    if (
        column is None
        or column not in df.columns
        or not selected_values
    ):
        return df

    return df[
        _clean(df[column]).isin(selected_values)
    ]


# ============================================================
# MAIN WARD ANALYSIS
# ============================================================

def render_ward(df):

    st.title(
        "🏥 Facility-wise + Ward-wise Management Analysis"
    )

    st.caption(
        "Interactive facility and ward burden monitoring, "
        "disease pattern, demographic distribution and monthly trend analysis."
    )

    # ========================================================
    # BASIC CHECK
    # ========================================================

    if df is None or df.empty:

        st.warning(
            "No records available for the selected global filters."
        )

        return

    # ========================================================
    # IDENTIFY STANDARD COLUMNS
    # ========================================================

    facility_col = _find_column(
        df,
        [
            "Facility Name Lform",
            "Facility",
            "Facility Name",
            "Health Facility",
            "Institution",
        ],
    )

    ward_col = _find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "Ward No",
            "Ward Number",
        ],
    )

    disease_col = _find_column(
        df,
        [
            "Confirmed Diagnosis",
            "Disease",
            "Disease Name",
            "Diagnosis",
        ],
    )

    gender_col = _find_column(
        df,
        [
            "Gender",
            "Sex",
        ],
    )

    month_col = _find_column(
        df,
        [
            "Month",
            "Reporting Month",
        ],
    )

    # ========================================================
    # DATA AVAILABILITY CHECK
    # ========================================================

    if facility_col is None and ward_col is None:

        st.error(
            "Ward and Facility fields could not be found in the dataset."
        )

        st.write("Available columns:")

        st.write(list(df.columns))

        return

    # ========================================================
    # MANAGEMENT FILTERS
    #
    # IMPORTANT:
    # Global Dashboard Filter is already applied in app.py.
    # Do NOT call create_filters() again here.
    # ========================================================

    st.divider()

    st.subheader("🎛️ Management Filters")

    f1, f2, f3, f4 = st.columns(4)

    # --------------------------------------------------------
    # FACILITY
    # --------------------------------------------------------

    selected_facilities = []

    if facility_col:

        facility_values = _unique_values(
            df,
            facility_col,
        )

        with f1:

            selected_facilities = st.multiselect(
                "🏥 Facility",
                facility_values,
                default=[],
                placeholder="All Facilities",
                key="ward_local_facility",
            )

    # --------------------------------------------------------
    # WARD
    # --------------------------------------------------------

    selected_wards = []

    if ward_col:

        ward_values = _unique_values(
            df,
            ward_col,
        )

        with f2:

            selected_wards = st.multiselect(
                "🗺️ Ward",
                ward_values,
                default=[],
                placeholder="All Wards",
                key="ward_local_ward",
            )

    # --------------------------------------------------------
    # GENDER
    # --------------------------------------------------------

    selected_genders = []

    if gender_col:

        gender_values = _unique_values(
            df,
            gender_col,
        )

        with f3:

            selected_genders = st.multiselect(
                "👥 Gender",
                gender_values,
                default=[],
                placeholder="All Genders",
                key="ward_local_gender",
            )

    # --------------------------------------------------------
    # DISEASE
    # --------------------------------------------------------

    selected_diseases = []

    if disease_col:

        disease_values = _unique_values(
            df,
            disease_col,
        )

        with f4:

            selected_diseases = st.multiselect(
                "🦠 Disease",
                disease_values,
                default=[],
                placeholder="All Diseases",
                key="ward_local_disease",
            )

    # ========================================================
    # APPLY LOCAL FILTERS
    # ========================================================

    management_df = df

    management_df = _apply_local_filter(
        management_df,
        facility_col,
        selected_facilities,
    )

    management_df = _apply_local_filter(
        management_df,
        ward_col,
        selected_wards,
    )

    management_df = _apply_local_filter(
        management_df,
        gender_col,
        selected_genders,
    )

    management_df = _apply_local_filter(
        management_df,
        disease_col,
        selected_diseases,
    )

    # ========================================================
    # EMPTY RESULT
    # ========================================================

    if management_df.empty:

        st.warning(
            "No records available for the selected management filters."
        )

        return

    # ========================================================
    # FILTER STATUS
    # ========================================================

    st.caption(
        f"Showing **{len(management_df):,}** records "
        f"from **{len(df):,}** globally filtered records."
    )

    # ========================================================
    # MANAGEMENT KPIs
    # ========================================================

    st.divider()

    st.subheader("📊 Management KPIs")

    total_cases = len(management_df)

    total_facilities = (
        management_df[facility_col].nunique(dropna=True)
        if facility_col
        else 0
    )

    total_wards = (
        management_df[ward_col].nunique(dropna=True)
        if ward_col
        else 0
    )

    total_diseases = (
        management_df[disease_col].nunique(dropna=True)
        if disease_col
        else 0
    )

    k1, k2, k3, k4 = st.columns(4)

    with k1:

        st.metric(
            "📋 Total Cases",
            f"{total_cases:,}",
        )

    with k2:

        st.metric(
            "🏥 Facilities",
            f"{total_facilities:,}",
        )

    with k3:

        st.metric(
            "🗺️ Wards",
            f"{total_wards:,}",
        )

    with k4:

        st.metric(
            "🦠 Diseases",
            f"{total_diseases:,}",
        )

    # ========================================================
    # TOP FACILITY + TOP WARD
    # ========================================================

    st.divider()

    top1, top2 = st.columns(2)

    # --------------------------------------------------------
    # TOP FACILITY
    # --------------------------------------------------------

    with top1:

        st.subheader("🏥 Top Burden Facility")

        if facility_col:

            facility_counts = (
                _clean(
                    management_df[facility_col]
                )
                .dropna()
                .value_counts()
            )

            if not facility_counts.empty:

                top_facility_name = facility_counts.index[0]
                top_facility_cases = int(
                    facility_counts.iloc[0]
                )

                st.metric(
                    "Highest Case Facility",
                    str(top_facility_name),
                    f"{top_facility_cases:,} cases",
                )

            else:

                st.info(
                    "Facility data unavailable."
                )

    # --------------------------------------------------------
    # TOP WARD
    # --------------------------------------------------------

    with top2:

        st.subheader("🗺️ Top Burden Ward")

        if ward_col:

            ward_counts = (
                _clean(
                    management_df[ward_col]
                )
                .dropna()
                .value_counts()
            )

            if not ward_counts.empty:

                top_ward_name = ward_counts.index[0]
                top_ward_cases = int(
                    ward_counts.iloc[0]
                )

                st.metric(
                    "Highest Case Ward",
                    str(top_ward_name),
                    f"{top_ward_cases:,} cases",
                )

            else:

                st.info(
                    "Ward data unavailable."
                )

    # ========================================================
    # FACILITY RANKING
    # ========================================================

    if facility_col:

        st.divider()

        st.subheader(
            "🏥 Facility-wise Case Burden"
        )

        facility_table = (
            _clean(
                management_df[facility_col]
            )
            .dropna()
            .value_counts()
            .rename_axis("Facility")
            .reset_index(name="Cases")
        )

        if not facility_table.empty:

            total_facility_cases = (
                facility_table["Cases"].sum()
            )

            facility_table["Share (%)"] = (
                facility_table["Cases"]
                / total_facility_cases
                * 100
            ).round(2)

            facility_table.insert(
                0,
                "Rank",
                range(
                    1,
                    len(facility_table) + 1,
                ),
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

    if ward_col:

        st.divider()

        st.subheader(
            "🗺️ Ward-wise Case Burden"
        )

        ward_table = (
            _clean(
                management_df[ward_col]
            )
            .dropna()
            .value_counts()
            .rename_axis("Ward")
            .reset_index(name="Cases")
        )

        if not ward_table.empty:

            total_ward_cases = (
                ward_table["Cases"].sum()
            )

            ward_table["Share (%)"] = (
                ward_table["Cases"]
                / total_ward_cases
                * 100
            ).round(2)

            ward_table.insert(
                0,
                "Rank",
                range(
                    1,
                    len(ward_table) + 1,
                ),
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

    if (
        facility_col
        and ward_col
    ):

        st.divider()

        st.subheader(
            "🏥 Facility × 🗺️ Ward Management Matrix"
        )

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

    # ========================================================
    # WARD × DISEASE
    # ========================================================

    if (
        ward_col
        and disease_col
    ):

        st.divider()

        st.subheader(
            "🦠 Ward × Disease Burden"
        )

        top_wards = (
            _clean(
                management_df[ward_col]
            )
            .dropna()
            .value_counts()
            .head(15)
            .index
        )

        top_diseases = (
            _clean(
                management_df[disease_col]
            )
            .dropna()
            .value_counts()
            .head(10)
            .index
        )

        heatmap_df = management_df[
            _clean(
                management_df[ward_col]
            ).isin(top_wards)
            &
            _clean(
                management_df[disease_col]
            ).isin(top_diseases)
        ]

        if not heatmap_df.empty:

            matrix = pd.crosstab(
                _clean(
                    heatmap_df[ward_col]
                ),
                _clean(
                    heatmap_df[disease_col]
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

    if gender_col:

        st.divider()

        st.subheader(
            "👥 Gender Distribution"
        )

        gender_table = (
            _clean(
                management_df[gender_col]
            )
            .dropna()
            .value_counts()
            .rename_axis("Gender")
            .reset_index(name="Cases")
        )

        if not gender_table.empty:

            g1, g2 = st.columns(2)

            with g1:

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

            with g2:

                st.dataframe(
                    gender_table,
                    use_container_width=True,
                    hide_index=True,
                )

    # ========================================================
    # MONTHLY TREND
    # ========================================================

    if month_col:

        st.divider()

        st.subheader(
            "📅 Monthly Case Comparison"
        )

        monthly = (
            _clean(
                management_df[month_col]
            )
            .dropna()
            .value_counts()
            .rename_axis("Month")
            .reset_index(name="Cases")
        )

        if not monthly.empty:

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

            monthly["Month"] = (
                monthly["Month"]
                .replace(month_map)
            )

            monthly["Month"] = pd.Categorical(
                monthly["Month"],
                categories=month_order,
                ordered=True,
            )

            monthly = (
                monthly
                .sort_values("Month")
            )

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
    # FILTERED DATA
    # ========================================================

    st.divider()

    st.subheader(
        "📋 Filtered Management Dataset"
    )

    st.caption(
        f"Showing {len(management_df):,} records."
    )

    st.dataframe(
        management_df,
        use_container_width=True,
        hide_index=True,
    )

