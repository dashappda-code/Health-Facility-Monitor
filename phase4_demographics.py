import pandas as pd
import plotly.express as px
import streamlit as st

from phase2_overview import (
    apply_filters,
    create_filters,
)


# ============================================================
# DEMOGRAPHICS PAGE
# ============================================================

def render_demographics(df):

    filters = create_filters(df)

    filtered_df = apply_filters(
        df,
        **filters,
    )

    st.title(
        "🔬 Demographics & Disease Analytics"
    )

    if filtered_df.empty:

        st.warning(
            "No records match the selected filters."
        )

        return

    data = filtered_df.copy()

    # ========================================================
    # AGE GROUP
    # ========================================================

    if "Age" in data.columns:

        data["Age Group"] = pd.cut(
            data["Age"],
            bins=[
                -1,
                4,
                14,
                24,
                44,
                64,
                float("inf"),
            ],
            labels=[
                "0-4",
                "5-14",
                "15-24",
                "25-44",
                "45-64",
                "65+",
            ],
        )

    # ========================================================
    # GENDER
    # ========================================================

    col1, col2 = st.columns(2)

    with col1:

        st.subheader(
            "👥 Gender Distribution"
        )

        gender = (
            data["Gender"]
            .dropna()
            .value_counts()
            .reset_index()
        )

        gender.columns = [
            "Gender",
            "Cases",
        ]

        if not gender.empty:

            fig = px.pie(
                gender,
                names="Gender",
                values="Cases",
                hole=0.45,
                title="Cases by Gender",
            )

            fig.update_layout(
                height=430
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    # ========================================================
    # OPD / IPD
    # ========================================================

    with col2:

        st.subheader(
            "🏥 OPD vs IPD"
        )

        opd_ipd = (
            data["Opd Ipd"]
            .dropna()
            .value_counts()
            .reset_index()
        )

        opd_ipd.columns = [
            "Type",
            "Cases",
        ]

        if not opd_ipd.empty:

            fig = px.bar(
                opd_ipd,
                x="Type",
                y="Cases",
                text="Cases",
                title="OPD vs IPD",
            )

            fig.update_traces(
                textposition="outside"
            )

            fig.update_layout(
                height=430
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    # ========================================================
    # AGE
    # ========================================================

    col3, col4 = st.columns(2)

    with col3:

        st.subheader(
            "🎂 Age Group Distribution"
        )

        age_order = [
            "0-4",
            "5-14",
            "15-24",
            "25-44",
            "45-64",
            "65+",
        ]

        age_data = (
            data["Age Group"]
            .value_counts()
            .reindex(
                age_order,
                fill_value=0,
            )
            .reset_index()
        )

        age_data.columns = [
            "Age Group",
            "Cases",
        ]

        fig = px.bar(
            age_data,
            x="Age Group",
            y="Cases",
            text="Cases",
            title="Cases by Age Group",
        )

        fig.update_traces(
            textposition="outside"
        )

        fig.update_layout(
            height=430
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # ========================================================
    # DISEASE × GENDER
    # ========================================================

    with col4:

        st.subheader(
            "🦠 Disease × Gender"
        )

        top_diseases = (
            data[
                "Confirmed Diagnosis"
            ]
            .dropna()
            .value_counts()
            .head(10)
            .index
            .tolist()
        )

        disease_gender = (
            data[
                data[
                    "Confirmed Diagnosis"
                ].isin(top_diseases)
            ]
            .dropna(
                subset=[
                    "Confirmed Diagnosis",
                    "Gender",
                ]
            )
            .groupby(
                [
                    "Confirmed Diagnosis",
                    "Gender",
                ]
            )
            .size()
            .reset_index(
                name="Cases"
            )
        )

        if not disease_gender.empty:

            fig = px.bar(
                disease_gender,
                x="Confirmed Diagnosis",
                y="Cases",
                color="Gender",
                barmode="group",
                title="Top 10 Diseases by Gender",
            )

            fig.update_layout(
                height=500,
                xaxis_tickangle=-45,
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

    # ========================================================
    # HEATMAP
    # ========================================================

    st.subheader(
        "🌡️ Disease × Gender Heatmap"
    )

    heatmap = (
        data[
            data[
                "Confirmed Diagnosis"
            ].isin(top_diseases)
        ]
        .dropna(
            subset=[
                "Confirmed Diagnosis",
                "Gender",
            ]
        )
        .groupby(
            [
                "Confirmed Diagnosis",
                "Gender",
            ]
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    if not heatmap.empty:

        pivot = heatmap.pivot(
            index="Confirmed Diagnosis",
            columns="Gender",
            values="Cases",
        ).fillna(0)

        pivot = pivot.loc[
            pivot.sum(
                axis=1
            ).sort_values(
                ascending=False
            ).index
        ]

        fig = px.imshow(
            pivot,
            text_auto=True,
            aspect="auto",
            title="Disease and Gender Case Distribution",
            labels={
                "x": "Gender",
                "y": "Disease",
                "color": "Cases",
            },
        )

        fig.update_layout(
            height=600
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )
