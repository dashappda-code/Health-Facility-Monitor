import pandas as pd
import plotly.express as px
import streamlit as st

from phase2_overview import apply_filters, create_filters


def _layout(fig, height=450):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text="",
        hovermode="x unified"
    )
    return fig


def render_ward_analysis(df):
    """
    Ward-wise Management Analysis

    Provides:
    - Total cases
    - Wards covered
    - Facilities covered
    - Top burden ward
    - Ward-wise case ranking
    - Ward x Disease burden
    - Ward-wise facility coverage
    - Ward-wise gender distribution
    - Ward-wise monthly trend
    - Ward management summary
    """

    # ---------------------------------------------------------
    # FILTERS
    # ---------------------------------------------------------
    filters = create_filters(df)
    filtered_df = apply_filters(df, **filters)

    # ---------------------------------------------------------
    # PAGE HEADER
    # ---------------------------------------------------------
    st.title("🏙️ Ward-wise Management Analysis")
    st.caption(
        "Ward burden, disease pattern, facility coverage, "
        "gender distribution and monthly trends."
    )

    # ---------------------------------------------------------
    # EMPTY DATA CHECK
    # ---------------------------------------------------------
    if filtered_df.empty:
        st.warning("No records match the selected filters.")
        return

    # ---------------------------------------------------------
    # BASIC DATA CHECKS
    # ---------------------------------------------------------
    has_ward = "Ward" in filtered_df.columns
    has_facility = "Facility Name Lform" in filtered_df.columns
    has_disease = "Confirmed Diagnosis" in filtered_df.columns
    has_gender = "Gender" in filtered_df.columns
    has_month = "Month" in filtered_df.columns

    # ---------------------------------------------------------
    # TOP BURDEN WARD
    # ---------------------------------------------------------
    if has_ward:
        ward_counts = (
            filtered_df["Ward"]
            .dropna()
            .astype(str)
            .str.strip()
            .value_counts()
        )
    else:
        ward_counts = pd.Series(dtype="int64")

    if not ward_counts.empty:
        top_ward = ward_counts.index[0]
        top_ward_cases = int(ward_counts.iloc[0])
    else:
        top_ward = "N/A"
        top_ward_cases = 0

    # ---------------------------------------------------------
    # KPI CARDS
    # ---------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Total Cases",
        f"{len(filtered_df):,}"
    )

    k2.metric(
        "Wards Covered",
        f"{filtered_df['Ward'].nunique(dropna=True):,}"
        if has_ward else "0"
    )

    k3.metric(
        "Facilities Covered",
        f"{filtered_df['Facility Name Lform'].nunique(dropna=True):,}"
        if has_facility else "0"
    )

    k4.metric(
        "Top Burden Ward",
        f"{top_ward} ({top_ward_cases:,})"
    )

    # ---------------------------------------------------------
    # WARD-WISE CASE BURDEN
    # ---------------------------------------------------------
    st.divider()
    st.subheader("🏆 Ward-wise Case Burden Ranking")

    if has_ward and not ward_counts.empty:

        ward_table = (
            ward_counts
            .rename_axis("Ward")
            .reset_index(name="Cases")
        )

        total_ward_cases = ward_table["Cases"].sum()

        if total_ward_cases > 0:
            ward_table["Share (%)"] = (
                ward_table["Cases"] /
                total_ward_cases * 100
            ).round(2)
        else:
            ward_table["Share (%)"] = 0

        ward_table.insert(
            0,
            "Rank",
            range(1, len(ward_table) + 1)
        )

        st.dataframe(
            ward_table,
            use_container_width=True,
            hide_index=True
        )

        # Top 20 chart
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
            title="Top 20 Wards by Case Burden"
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            _layout(fig, 650),
            use_container_width=True
        )

    else:
        st.info("Ward data is not available.")

    # ---------------------------------------------------------
    # WARD x DISEASE
    # ---------------------------------------------------------
    st.divider()
    st.subheader("🦠 Ward × Disease Burden")

    if has_ward and has_disease:

        top_wards = (
            filtered_df["Ward"]
            .dropna()
            .astype(str)
            .str.strip()
            .value_counts()
            .head(15)
            .index
        )

        top_diseases = (
            filtered_df["Confirmed Diagnosis"]
            .dropna()
            .astype(str)
            .str.strip()
            .value_counts()
            .head(10)
            .index
        )

        matrix_df = filtered_df[
            filtered_df["Ward"].astype(str).str.strip().isin(top_wards)
            &
            filtered_df["Confirmed Diagnosis"]
            .astype(str)
            .str.strip()
            .isin(top_diseases)
        ]

        if not matrix_df.empty:

            heatmap = pd.crosstab(
                matrix_df["Ward"],
                matrix_df["Confirmed Diagnosis"]
            )

            fig = px.imshow(
                heatmap,
                text_auto=True,
                aspect="auto",
                title="Top 15 Wards × Top 10 Diseases",
                labels={
                    "x": "Confirmed Diagnosis",
                    "y": "Ward",
                    "color": "Cases"
                }
            )

            st.plotly_chart(
                _layout(fig, 650),
                use_container_width=True
            )

        else:
            st.info("No ward-disease data available.")

    else:
        st.info(
            "Ward or Confirmed Diagnosis column is not available."
        )

    # ---------------------------------------------------------
    # WARD-WISE FACILITY COVERAGE
    # ---------------------------------------------------------
    st.divider()
    st.subheader("🏥 Ward-wise Facility Coverage")

    if has_ward and has_facility:

        coverage_df = filtered_df.dropna(
            subset=["Ward", "Facility Name Lform"]
        ).copy()

        if not coverage_df.empty:

            agg = {
                "Cases": ("Ward", "size"),
                "Facilities": (
                    "Facility Name Lform",
                    "nunique"
                )
            }

            if has_disease:
                agg["Diseases"] = (
                    "Confirmed Diagnosis",
                    "nunique"
                )

            ward_facility = (
                coverage_df
                .groupby("Ward")
                .agg(**agg)
                .reset_index()
                .sort_values(
                    ["Cases", "Facilities"],
                    ascending=[False, False]
                )
            )

            st.dataframe(
                ward_facility.head(100),
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info(
                "No ward-facility data available."
            )

    else:
        st.info(
            "Ward or Facility Name Lform column is not available."
        )

    # ---------------------------------------------------------
    # WARD-WISE GENDER DISTRIBUTION
    # ---------------------------------------------------------
    st.divider()
    st.subheader("👥 Ward-wise Gender Distribution")

    if has_ward and has_gender:

        top_wards_gender = (
            filtered_df["Ward"]
            .dropna()
            .astype(str)
            .str.strip()
            .value_counts()
            .head(15)
            .index
        )

        gender_df = (
            filtered_df[
                filtered_df["Ward"]
                .astype(str)
                .str.strip()
                .isin(top_wards_gender)
                &
                filtered_df["Gender"].notna()
            ]
            .groupby(["Ward", "Gender"])
            .size()
            .reset_index(name="Cases")
        )

        if not gender_df.empty:

            fig = px.bar(
                gender_df,
                x="Ward",
                y="Cases",
                color="Gender",
                barmode="group",
                title="Gender Distribution in Top 15 Wards"
            )

            st.plotly_chart(
                _layout(fig, 500),
                use_container_width=True
            )

            st.dataframe(
                gender_df,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info(
                "No gender data available for selected wards."
            )

    else:
        st.info(
            "Ward or Gender column is not available."
        )

    # ---------------------------------------------------------
    # WARD-WISE MONTHLY TREND
    # ---------------------------------------------------------
    st.divider()
    st.subheader("📅 Ward-wise Monthly Trend")

    if has_ward and has_month:

        top10_wards = (
            filtered_df["Ward"]
            .dropna()
            .astype(str)
            .str.strip()
            .value_counts()
            .head(10)
            .index
        )

        monthly = (
            filtered_df[
                filtered_df["Ward"]
                .astype(str)
                .str.strip()
                .isin(top10_wards)
            ]
            .dropna(subset=["Ward", "Month"])
            .groupby(["Month", "Ward"])
            .size()
            .reset_index(name="Cases")
        )

        if not monthly.empty:

            month_order = [
                "Jan", "Feb", "Mar", "Apr",
                "May", "Jun", "Jul", "Aug",
                "Sep", "Oct", "Nov", "Dec"
            ]

            # Handle full month names also
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
                "December": "Dec"
            }

            monthly["Month"] = (
                monthly["Month"]
                .astype(str)
                .str.strip()
                .replace(month_map)
            )

            monthly["Month"] = pd.Categorical(
                monthly["Month"],
                categories=month_order,
                ordered=True
            )

            monthly = monthly.sort_values(
                ["Month", "Ward"]
            )

            fig = px.line(
                monthly,
                x="Month",
                y="Cases",
                color="Ward",
                markers=True,
                title="Monthly Case Trend — Top 10 Wards"
            )

            st.plotly_chart(
                _layout(fig, 520),
                use_container_width=True
            )

            st.dataframe(
                monthly,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info(
                "No monthly ward data available."
            )

    else:
        st.info(
            "Ward or Month column is not available."
        )

    # ---------------------------------------------------------
    # WARD MANAGEMENT SUMMARY
    # ---------------------------------------------------------
    st.divider()
    st.subheader("📋 Ward Management Summary")

    if has_ward:

        summary_df = filtered_df.dropna(
            subset=["Ward"]
        ).copy()

        if not summary_df.empty:

            agg = {
                "Cases": ("Ward", "size")
            }

            if has_facility:
                agg["Facilities"] = (
                    "Facility Name Lform",
                    "nunique"
                )

            if has_disease:
                agg["Diseases"] = (
                    "Confirmed Diagnosis",
                    "nunique"
                )

            if has_gender:
                agg["Gender Categories"] = (
                    "Gender",
                    "nunique"
                )

            summary = (
                summary_df
                .groupby("Ward")
                .agg(**agg)
                .reset_index()
            )

            total_cases = summary["Cases"].sum()

            if total_cases > 0:
                summary["Share (%)"] = (
                    summary["Cases"] /
                    total_cases * 100
                ).round(2)
            else:
                summary["Share (%)"] = 0

            summary = (
                summary
                .sort_values(
                    "Cases",
                    ascending=False
                )
                .reset_index(drop=True)
            )

            summary.insert(
                0,
                "Rank",
                range(1, len(summary) + 1)
            )

            st.dataframe(
                summary,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info(
                "No ward summary data available."
            )

    else:
        st.info(
            "Ward column is not available."
        )
