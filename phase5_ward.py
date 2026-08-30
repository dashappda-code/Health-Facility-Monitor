import pandas as pd
import plotly.express as px
import streamlit as st

from phase2_overview import (
    apply_filters,
    create_filters,
)


# ============================================================
# WARD ANALYSIS
# ============================================================

def render_ward_analysis(df):

    filters = create_filters(df)

    filtered_df = apply_filters(
        df,
        **filters,
    )

    st.title(
        "🏙️ Ward Analysis"
    )

    if filtered_df.empty:

        st.warning(
            "No records match the selected filters."
        )

        return

    # ========================================================
    # WARD RANKING
    # ========================================================

    ward_data = (
        filtered_df[
            "Ward"
        ]
        .dropna()
        .value_counts()
        .reset_index()
    )

    ward_data.columns = [
        "Ward",
        "Cases",
    ]

    st.subheader(
        "Ward Case Ranking"
    )

    st.dataframe(
        ward_data,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # WARD BAR CHART
    # ========================================================

    fig = px.bar(
        ward_data.sort_values(
            "Cases"
        ),
        x="Cases",
        y="Ward",
        orientation="h",
        text="Cases",
        title="Cases by Ward",
    )

    fig.update_traces(
        textposition="outside"
    )

    fig.update_layout(
        height=700
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    # ========================================================
    # TOP DISEASE BY WARD
    # ========================================================

    st.subheader(
        "🦠 Disease Pattern by Ward"
    )

    ward_disease = (
        filtered_df
        .dropna(
            subset=[
                "Ward",
                "Confirmed Diagnosis",
            ]
        )
        .groupby(
            [
                "Ward",
                "Confirmed Diagnosis",
            ]
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    if not ward_disease.empty:

        top_disease_by_ward = (
            ward_disease
            .sort_values(
                [
                    "Ward",
                    "Cases",
                ],
                ascending=[
                    True,
                    False,
                ],
            )
            .groupby(
                "Ward",
                as_index=False,
            )
            .first()
        )

        top_disease_by_ward = (
            top_disease_by_ward[
                [
                    "Ward",
                    "Confirmed Diagnosis",
                    "Cases",
                ]
            ]
            .sort_values(
                "Cases",
                ascending=False,
            )
        )

        st.dataframe(
            top_disease_by_ward,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # WARD × OPD/IPD
    # ========================================================

    st.subheader(
        "🏥 Ward × OPD/IPD"
    )

    ward_opd = (
        filtered_df
        .dropna(
            subset=[
                "Ward",
                "Opd Ipd",
            ]
        )
        .groupby(
            [
                "Ward",
                "Opd Ipd",
            ]
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    if not ward_opd.empty:

        fig = px.bar(
            ward_opd,
            x="Ward",
            y="Cases",
            color="Opd Ipd",
            barmode="group",
            title="OPD vs IPD by Ward",
        )

        fig.update_layout(
            height=600,
            xaxis_tickangle=-45,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )
