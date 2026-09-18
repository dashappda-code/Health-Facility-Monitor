import pandas as pd
import plotly.express as px
import streamlit as st

from phase2_overview import apply_filters, create_filters


AGE_BINS = [-1, 4, 14, 24, 44, 64, float("inf")]
AGE_LABELS = ["0-4", "5-14", "15-24", "25-44", "45-64", "65+"]


def _case_count(df, columns, name="Cases"):
    if not all(column in df.columns for column in columns):
        return pd.DataFrame()

    return (
        df.dropna(subset=columns)
        .groupby(columns, dropna=False)
        .size()
        .reset_index(name=name)
    )


def _layout(fig, height=430):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text="",
    )
    return fig


def _prepare_age_data(data):
    result = data.copy()

    if "Age" not in result.columns:
        return result

    result["Age"] = pd.to_numeric(result["Age"], errors="coerce")
    result = result[result["Age"].between(0, 120, inclusive="both")]

    result["Age Group"] = pd.cut(
        result["Age"],
        bins=AGE_BINS,
        labels=AGE_LABELS,
    )

    return result


def render_demographics(df):

    filters = create_filters(df)

    filtered_df = apply_filters(
        df,
        **filters,
    )

    st.title("🔬 Demographics & Disease Analytics")
    st.caption(
        "Age, gender, service type and disease distribution from the selected records"
    )

    if filtered_df.empty:
        st.warning("No records match the selected filters.")
        return

    data = _prepare_age_data(filtered_df)

    # ========================================================
    # SUMMARY
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Records Analysed", f"{len(filtered_df):,}")

    if "Age" in data.columns:
        c2.metric(
            "Median Age",
            f"{data['Age'].median():.0f}" if data["Age"].notna().any() else "N/A",
        )
        c3.metric(
            "Age Range",
            (
                f"{data['Age'].min():.0f}–{data['Age'].max():.0f}"
                if data["Age"].notna().any()
                else "N/A"
            ),
        )
    else:
        c2.metric("Median Age", "N/A")
        c3.metric("Age Range", "N/A")

    if "Gender" in data.columns:
        c4.metric(
            "Gender Categories",
            f"{data['Gender'].nunique(dropna=True):,}",
        )
    else:
        c4.metric("Gender Categories", "0")

    st.divider()

    # ========================================================
    # ROW 1 — GENDER + AGE
    # ========================================================

    left, right = st.columns(2)

    with left:
        st.subheader("👥 Gender Distribution")

        if "Gender" in data.columns:
            gender = (
                data["Gender"]
                .dropna()
                .value_counts()
                .rename_axis("Gender")
                .reset_index(name="Cases")
            )

            if not gender.empty:
                fig = px.pie(
                    gender,
                    names="Gender",
                    values="Cases",
                    hole=0.45,
                    title="Cases by Gender",
                )
                st.plotly_chart(
                    _layout(fig, 430),
                    use_container_width=True,
                )

    with right:
        st.subheader("🎂 Age Group Distribution")

        if "Age Group" in data.columns:
            age_data = (
                data["Age Group"]
                .value_counts()
                .reindex(AGE_LABELS, fill_value=0)
                .rename_axis("Age Group")
                .reset_index(name="Cases")
            )

            fig = px.bar(
                age_data,
                x="Age Group",
                y="Cases",
                text="Cases",
                title="Cases by Age Group",
            )
            fig.update_traces(textposition="outside")

            st.plotly_chart(
                _layout(fig, 430),
                use_container_width=True,
            )

    # ========================================================
    # ROW 2 — OPD/IPD + AGE PROFILE
    # ========================================================

    left, right = st.columns(2)

    with left:
        st.subheader("🏥 OPD vs IPD")

        if "Opd Ipd" in data.columns:
            opd_ipd = (
                data["Opd Ipd"]
                .dropna()
                .value_counts()
                .rename_axis("Type")
                .reset_index(name="Cases")
            )

            if not opd_ipd.empty:
                fig = px.bar(
                    opd_ipd,
                    x="Type",
                    y="Cases",
                    text="Cases",
                    title="Service Type Distribution",
                )
                fig.update_traces(textposition="outside")

                st.plotly_chart(
                    _layout(fig, 430),
                    use_container_width=True,
                )

    with right:
        st.subheader("📊 Age Profile")

        if "Age" in data.columns and data["Age"].notna().any():
            fig = px.histogram(
                data,
                x="Age",
                nbins=20,
                title="Age Distribution",
                labels={"Age": "Age", "count": "Cases"},
            )

            st.plotly_chart(
                _layout(fig, 430),
                use_container_width=True,
            )

    # ========================================================
    # DISEASE × GENDER
    # ========================================================

    st.divider()
    st.subheader("🦠 Top 10 Diseases × Gender")

    if all(
        column in data.columns
        for column in ["Confirmed Diagnosis", "Gender"]
    ):
        top_diseases = (
            data["Confirmed Diagnosis"]
            .dropna()
            .value_counts()
            .head(10)
            .index
            .tolist()
        )

        disease_gender = _case_count(
            data[
                data["Confirmed Diagnosis"].isin(top_diseases)
            ],
            ["Confirmed Diagnosis", "Gender"],
        )

        if not disease_gender.empty:
            disease_gender["Confirmed Diagnosis"] = pd.Categorical(
                disease_gender["Confirmed Diagnosis"],
                categories=top_diseases,
                ordered=True,
            )

            fig = px.bar(
                disease_gender,
                x="Confirmed Diagnosis",
                y="Cases",
                color="Gender",
                barmode="group",
                title="Top Diseases by Gender",
            )

            fig.update_layout(xaxis_tickangle=-45)

            st.plotly_chart(
                _layout(fig, 520),
                use_container_width=True,
            )

    # ========================================================
    # DISEASE × AGE GROUP
    # ========================================================

    st.subheader("🧬 Top 10 Diseases × Age Group")

    if all(
        column in data.columns
        for column in ["Confirmed Diagnosis", "Age Group"]
    ):
        top_diseases = (
            data["Confirmed Diagnosis"]
            .dropna()
            .value_counts()
            .head(10)
            .index
            .tolist()
        )

        disease_age = _case_count(
            data[
                data["Confirmed Diagnosis"].isin(top_diseases)
            ],
            ["Confirmed Diagnosis", "Age Group"],
        )

        if not disease_age.empty:
            disease_age["Age Group"] = pd.Categorical(
                disease_age["Age Group"],
                categories=AGE_LABELS,
                ordered=True,
            )

            fig = px.bar(
                disease_age,
                x="Confirmed Diagnosis",
                y="Cases",
                color="Age Group",
                barmode="stack",
                title="Top Diseases by Age Group",
            )

            fig.update_layout(xaxis_tickangle=-45)

            st.plotly_chart(
                _layout(fig, 520),
                use_container_width=True,
            )

    # ========================================================
    # DISEASE × GENDER HEATMAP
    # ========================================================

    st.subheader("🌡️ Disease × Gender Heatmap")

    if all(
        column in data.columns
        for column in ["Confirmed Diagnosis", "Gender"]
    ):
        heatmap_data = data[
            data["Confirmed Diagnosis"].isin(top_diseases)
        ]

        heatmap = _case_count(
            heatmap_data,
            ["Confirmed Diagnosis", "Gender"],
        )

        if not heatmap.empty:
            pivot = (
                heatmap
                .pivot(
                    index="Confirmed Diagnosis",
                    columns="Gender",
                    values="Cases",
                )
                .fillna(0)
            )

            pivot = pivot.loc[
                pivot.sum(axis=1).sort_values(
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

            st.plotly_chart(
                _layout(fig, 600),
                use_container_width=True,
            )

    # ========================================================
    # AGE DATA TABLE
    # ========================================================

    st.divider()
    st.subheader("📋 Age Group Summary")

    if "Age Group" in data.columns:
        age_summary = (
            data["Age Group"]
            .value_counts()
            .reindex(AGE_LABELS, fill_value=0)
            .rename_axis("Age Group")
            .reset_index(name="Cases")
        )

        age_summary["Share (%)"] = (
            age_summary["Cases"]
            / max(len(data), 1)
            * 100
        ).round(2)

        st.dataframe(
            age_summary,
            use_container_width=True,
            hide_index=True,
        )
