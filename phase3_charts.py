import pandas as pd
import plotly.express as px
import streamlit as st

from phase2_overview import apply_filters, create_filters


# ============================================================
# CHART HELPERS
# ============================================================

def _case_count(df, group_columns, name="Cases"):
    """Return record counts grouped by one or more columns."""
    if not all(column in df.columns for column in group_columns):
        return pd.DataFrame()

    return (
        df.dropna(subset=group_columns)
        .groupby(group_columns, dropna=False)
        .size()
        .reset_index(name=name)
    )


def _sort_week(df):
    """Sort Week labels such as Week 1, Week 2, Week 3... correctly."""
    if df.empty or "Week" not in df.columns:
        return df

    result = df.copy()
    result["_week_number"] = (
        result["Week"]
        .astype(str)
        .str.extract(r"(\d+)", expand=False)
        .astype(float)
    )

    sort_columns = []
    if "Year" in result.columns:
        sort_columns.append("Year")
    sort_columns.append("_week_number")

    result = result.sort_values(sort_columns)
    return result.drop(columns=["_week_number"])


def _chart_layout(fig, height=420):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text="",
        hovermode="x unified",
    )
    return fig


# ============================================================
# CHART PAGE
# ============================================================

def render_charts(df):

    filters = create_filters(df)

    filtered_df = apply_filters(
        df,
        **filters,
    )

    st.title("📊 Charts & Analytics")
    st.caption(
        "Interactive trend, burden and facility analysis based on the selected filters"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary_cols = st.columns(4)

    summary_cols[0].metric(
        "Records Analysed",
        f"{len(filtered_df):,}",
    )

    if "Ward" in filtered_df.columns:
        summary_cols[1].metric(
            "Wards Covered",
            f"{filtered_df['Ward'].nunique(dropna=True):,}",
        )
    else:
        summary_cols[1].metric("Wards Covered", "0")

    if "Facility Name Lform" in filtered_df.columns:
        summary_cols[2].metric(
            "Facilities Covered",
            f"{filtered_df['Facility Name Lform'].nunique(dropna=True):,}",
        )
    else:
        summary_cols[2].metric("Facilities Covered", "0")

    if "Confirmed Diagnosis" in filtered_df.columns:
        summary_cols[3].metric(
            "Diseases Recorded",
            f"{filtered_df['Confirmed Diagnosis'].nunique(dropna=True):,}",
        )
    else:
        summary_cols[3].metric("Diseases Recorded", "0")

    if filtered_df.empty:
        st.warning("No records match the selected filters.")
        return

    st.divider()

    # ========================================================
    # TABS
    # ========================================================

    tab_trends, tab_burden, tab_facility = st.tabs(
        [
            "📈 Time Trends",
            "🏙️ Disease & Ward Burden",
            "🏥 Facility Performance",
        ]
    )

    # ========================================================
    # TAB 1 — TIME TRENDS
    # ========================================================

    with tab_trends:

        st.subheader("Year-wise Case Comparison")

        yearly = _case_count(filtered_df, ["Year"])

        if not yearly.empty:

            yearly["Year"] = yearly["Year"].astype(str)

            fig = px.bar(
                yearly,
                x="Year",
                y="Cases",
                text="Cases",
                title="Total Cases by Year",
            )

            fig.update_traces(textposition="outside")
            st.plotly_chart(
                _chart_layout(fig, 400),
                use_container_width=True,
            )

        st.subheader("Month-wise Case Trend")

        monthly = _case_count(
            filtered_df,
            ["Year", "Month"],
        )

        if not monthly.empty:

            month_order = [
                "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
            ]

            monthly["Month"] = pd.Categorical(
                monthly["Month"],
                categories=month_order,
                ordered=True,
            )

            monthly = monthly.sort_values(
                ["Year", "Month"]
            )

            monthly["Year"] = monthly["Year"].astype(str)

            fig = px.line(
                monthly,
                x="Month",
                y="Cases",
                color="Year",
                markers=True,
                title="Monthly Cases — Year-wise Comparison",
                custom_data=["Year"],
            )

            fig.update_traces(
                hovertemplate=(
                    "Month: %{x}<br>"
                    "Cases: %{y:,}<br>"
                    "Year: %{customdata[0]}"
                    "<extra></extra>"
                )
            )

            st.plotly_chart(
                _chart_layout(fig, 450),
                use_container_width=True,
            )

        st.subheader("Week-wise Case Trend")

        weekly = _case_count(
            filtered_df,
            ["Year", "Week"],
        )

        weekly = _sort_week(weekly)

        if not weekly.empty:

            weekly["Year"] = weekly["Year"].astype(str)

            fig = px.line(
                weekly,
                x="Week",
                y="Cases",
                color="Year",
                markers=True,
                title="Weekly Cases — Year-wise Comparison",
                custom_data=["Year"],
            )

            fig.update_traces(
                hovertemplate=(
                    "Week: %{x}<br>"
                    "Cases: %{y:,}<br>"
                    "Year: %{customdata[0]}"
                    "<extra></extra>"
                )
            )

            st.plotly_chart(
                _chart_layout(fig, 450),
                use_container_width=True,
            )

    # ========================================================
    # TAB 2 — DISEASE & WARD BURDEN
    # ========================================================

    with tab_burden:

        left, right = st.columns(2)

        with left:

            st.subheader("Top 15 Diseases")

            if "Confirmed Diagnosis" in filtered_df.columns:

                disease = (
                    filtered_df["Confirmed Diagnosis"]
                    .dropna()
                    .value_counts()
                    .head(15)
                    .rename_axis("Disease")
                    .reset_index(name="Cases")
                    .sort_values("Cases")
                )

                if not disease.empty:

                    fig = px.bar(
                        disease,
                        x="Cases",
                        y="Disease",
                        orientation="h",
                        text="Cases",
                        title="Top Disease Burden",
                    )

                    fig.update_traces(
                        textposition="outside"
                    )

                    st.plotly_chart(
                        _chart_layout(fig, 600),
                        use_container_width=True,
                    )

        with right:

            st.subheader("Top 15 Wards")

            if "Ward" in filtered_df.columns:

                ward = (
                    filtered_df["Ward"]
                    .dropna()
                    .value_counts()
                    .head(15)
                    .rename_axis("Ward")
                    .reset_index(name="Cases")
                    .sort_values("Cases")
                )

                if not ward.empty:

                    fig = px.bar(
                        ward,
                        x="Cases",
                        y="Ward",
                        orientation="h",
                        text="Cases",
                        title="Ward-wise Case Burden",
                    )

                    fig.update_traces(
                        textposition="outside"
                    )

                    st.plotly_chart(
                        _chart_layout(fig, 600),
                        use_container_width=True,
                    )

        st.divider()

        st.subheader("Gender Distribution")

        if "Gender" in filtered_df.columns:

            gender = (
                filtered_df["Gender"]
                .dropna()
                .value_counts()
                .rename_axis("Gender")
                .reset_index(name="Cases")
            )

            if not gender.empty:

                fig = px.bar(
                    gender,
                    x="Gender",
                    y="Cases",
                    text="Cases",
                    title="Cases by Gender",
                )

                fig.update_traces(textposition="outside")

                st.plotly_chart(
                    _chart_layout(fig, 380),
                    use_container_width=True,
                )

    # ========================================================
    # TAB 3 — FACILITY PERFORMANCE
    # ========================================================

    with tab_facility:

        st.subheader("Top 15 Facilities by Case Load")

        facility_column = "Facility Name Lform"

        if facility_column in filtered_df.columns:

            facility = (
                filtered_df[facility_column]
                .dropna()
                .value_counts()
                .head(15)
                .rename_axis("Facility")
                .reset_index(name="Cases")
                .sort_values("Cases")
            )

            if not facility.empty:

                fig = px.bar(
                    facility,
                    x="Cases",
                    y="Facility",
                    orientation="h",
                    text="Cases",
                    title="Facility-wise Case Load",
                )

                fig.update_traces(
                    textposition="outside"
                )

                st.plotly_chart(
                    _chart_layout(fig, 600),
                    use_container_width=True,
                )

        st.subheader("Facility Type Distribution")

        if "PUBLIC / PRIVATE FACILITIES" in filtered_df.columns:

            facility_type = (
                filtered_df["PUBLIC / PRIVATE FACILITIES"]
                .dropna()
                .value_counts()
                .rename_axis("Facility Type")
                .reset_index(name="Cases")
            )

            if not facility_type.empty:

                fig = px.pie(
                    facility_type,
                    names="Facility Type",
                    values="Cases",
                    hole=0.45,
                    title="Public / Private Case Distribution",
                )

                fig.update_traces(
                    textposition="inside",
                    textinfo="percent+label",
                )

                st.plotly_chart(
                    _chart_layout(fig, 430),
                    use_container_width=True,
                )

        st.divider()

        st.subheader("Top Facilities — Data Table")

        if facility_column in filtered_df.columns:

            facility_table = (
                filtered_df[facility_column]
                .dropna()
                .value_counts()
                .head(20)
                .rename_axis("Facility")
                .reset_index(name="Cases")
            )

            st.dataframe(
                facility_table,
                use_container_width=True,
                hide_index=True,
            )
