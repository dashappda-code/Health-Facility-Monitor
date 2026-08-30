import pandas as pd
import plotly.express as px
import streamlit as st

from phase2_overview import (
    apply_filters,
    create_filters,
)


# ============================================================
# CHART PAGE
# ============================================================

def render_charts(df):

    filters = create_filters(df)

    filtered_df = apply_filters(
        df,
        **filters,
    )

    st.title(
        "📊 Charts & Trends"
    )

    st.caption(
        "Dynamic analysis based on selected filters"
    )

    if filtered_df.empty:

        st.warning(
            "No records match the selected filters."
        )

        return

    chart_df = filtered_df.copy()

    # ========================================================
    # YEAR COMPARISON
    # ========================================================

    st.subheader(
        "📅 Year Comparison"
    )

    yearly = (
        chart_df
        .dropna(subset=["Year"])
        .groupby("Year")
        .size()
        .reset_index(name="Cases")
    )

    if not yearly.empty:

        yearly["Year"] = (
            yearly["Year"]
            .astype(int)
            .astype(str)
        )

        fig = px.bar(
            yearly,
            x="Year",
            y="Cases",
            text="Cases",
            title="Total Cases by Year",
        )

        fig.update_traces(
            textposition="outside"
        )

        fig.update_layout(
            height=400
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # ========================================================
    # MONTHLY TREND
    # ========================================================

    st.subheader(
        "📈 Monthly Trend"
    )

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

    monthly = (
        chart_df
        .dropna(
            subset=[
                "Year",
                "Month",
            ]
        )
        .groupby(
            [
                "Year",
                "Month",
            ]
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    if not monthly.empty:

        monthly["Month"] = pd.Categorical(
            monthly["Month"],
            categories=month_order,
            ordered=True,
        )

        monthly = monthly.sort_values(
            [
                "Year",
                "Month",
            ]
        )

        monthly["Year"] = (
            monthly["Year"]
            .astype(str)
        )

        fig = px.line(
            monthly,
            x="Month",
            y="Cases",
            color="Year",
            markers=True,
            title="Monthly Case Trend",
        )

        fig.update_layout(
            height=450
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # ========================================================
    # WEEKLY TREND
    # ========================================================

    st.subheader(
        "📆 Weekly Trend"
    )

    weekly = (
        chart_df
        .dropna(
            subset=[
                "Year",
                "Week",
            ]
        )
        .groupby(
            [
                "Year",
                "Week",
            ]
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    if not weekly.empty:

        weekly["Week Number"] = (
            weekly["Week"]
            .astype(str)
            .str.extract(
                r"(\d+)"
            )[0]
            .astype(float)
        )

        weekly = weekly.sort_values(
            [
                "Year",
                "Week Number",
            ]
        )

        weekly["Year"] = (
            weekly["Year"]
            .astype(str)
        )

        fig = px.line(
            weekly,
            x="Week",
            y="Cases",
            color="Year",
            markers=True,
            title="Weekly Case Trend",
        )

        fig.update_layout(
            height=450
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # ========================================================
    # DISEASE DISTRIBUTION
    # ========================================================

    st.subheader(
        "🦠 Disease Distribution"
    )

    disease = (
        chart_df[
            "Confirmed Diagnosis"
        ]
        .dropna()
        .value_counts()
        .head(15)
        .reset_index()
    )

    disease.columns = [
        "Disease",
        "Cases",
    ]

    if not disease.empty:

        fig = px.bar(
            disease.sort_values(
                "Cases"
            ),
            x="Cases",
            y="Disease",
            orientation="h",
            text="Cases",
            title="Top 15 Diseases",
        )

        fig.update_traces(
            textposition="outside"
        )

        fig.update_layout(
            height=550
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # ========================================================
    # WARD DISTRIBUTION
    # ========================================================

    st.subheader(
        "🏙️ Ward-wise Cases"
    )

    ward = (
        chart_df[
            "Ward"
        ]
        .dropna()
        .value_counts()
        .head(15)
        .reset_index()
    )

    ward.columns = [
        "Ward",
        "Cases",
    ]

    if not ward.empty:

        fig = px.bar(
            ward.sort_values(
                "Cases"
            ),
            x="Cases",
            y="Ward",
            orientation="h",
            text="Cases",
            title="Top 15 Wards",
        )

        fig.update_traces(
            textposition="outside"
        )

        fig.update_layout(
            height=550
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )
