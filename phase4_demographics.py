import streamlit as st
import pandas as pd


def _clean_text(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="object")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


def render_demographics(df):

    st.subheader("👥 Demographic Analysis")

    if df is None or df.empty:
        st.warning(
            "No records available for the selected filters."
        )
        return

    st.caption(
        "Age-wise, age-group-wise, gender-wise and OPD/IPD "
        "analysis based on the selected Global Dashboard Filters."
    )

    # =========================================================
    # 1. DEMOGRAPHIC SUMMARY
    # =========================================================

    st.markdown("### 📊 Demographic Summary")

    total_records = len(df)

    if "Age" in df.columns:
        age_numeric = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )
        valid_age = age_numeric[
            age_numeric.between(0, 120)
        ]
    else:
        valid_age = pd.Series(
            dtype="float64"
        )

    if not valid_age.empty:
        mean_age = valid_age.mean()
        median_age = valid_age.median()
        min_age = valid_age.min()
        max_age = valid_age.max()
    else:
        mean_age = None
        median_age = None
        min_age = None
        max_age = None

    if "Gender" in df.columns:
        gender_values = _clean_text(
            df,
            "Gender",
        )
        gender_values = gender_values[
            gender_values.ne("")
            & gender_values.ne("nan")
        ]
        gender_count = gender_values.nunique()
    else:
        gender_count = 0

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric(
            "Records",
            f"{total_records:,}",
        )

    with c2:
        if mean_age is not None:
            st.metric(
                "Mean Age",
                f"{mean_age:.1f} years",
            )
        else:
            st.metric(
                "Mean Age",
                "N/A",
            )

    with c3:
        if median_age is not None:
            st.metric(
                "Median Age",
                f"{median_age:.1f} years",
            )
        else:
            st.metric(
                "Median Age",
                "N/A",
            )

    with c4:
        if min_age is not None:
            st.metric(
                "Minimum Age",
                f"{min_age:.0f}",
            )
        else:
            st.metric(
                "Minimum Age",
                "N/A",
            )

    with c5:
        if max_age is not None:
            st.metric(
                "Maximum Age",
                f"{max_age:.0f}",
            )
        else:
            st.metric(
                "Maximum Age",
                "N/A",
            )

    # =========================================================
    # 2. AGE GROUP-WISE ANALYSIS
    # =========================================================

    st.divider()

    st.markdown("### 🎂 Age Group-wise Distribution")

    if "Age Group" in df.columns:

        age_group = _clean_text(
            df,
            "Age Group",
        )

        age_group = age_group[
            age_group.ne("")
            & age_group.ne("nan")
            & age_group.ne("NaT")
        ]

        if not age_group.empty:

            age_group_counts = (
                age_group
                .value_counts()
                .rename_axis("Age Group")
                .reset_index(name="Records")
            )

            preferred_order = [
                "Below 1 year",
                "1-4",
                "5-14",
                "15-24",
                "25-44",
                "45-64",
                "65+",
                "Unknown",
            ]

            order_map = {
                value: index
                for index, value
                in enumerate(preferred_order)
            }

            age_group_counts["sort_order"] = (
                age_group_counts["Age Group"]
                .map(order_map)
                .fillna(999)
            )

            age_group_counts = (
                age_group_counts
                .sort_values(
                    ["sort_order", "Age Group"]
                )
                .drop(
                    columns=["sort_order"]
                )
                .reset_index(drop=True)
            )

            age_group_counts["Percentage"] = (
                age_group_counts["Records"]
                / age_group_counts["Records"].sum()
                * 100
            ).round(2)

            st.bar_chart(
                age_group_counts.set_index(
                    "Age Group"
                )["Records"],
                use_container_width=True,
            )

            display_age_group = age_group_counts.copy()

            display_age_group["Percentage"] = (
                display_age_group["Percentage"]
                .map(lambda x: f"{x:.2f}%")
            )

            st.dataframe(
                display_age_group,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Age Group information is not available."
            )

    # =========================================================
    # 3. GENDER-WISE ANALYSIS
    # =========================================================

    st.divider()

    st.markdown("### ⚧ Gender-wise Distribution")

    if "Gender" in df.columns:

        gender = _clean_text(
            df,
            "Gender",
        )

        gender = gender[
            gender.ne("")
            & gender.ne("nan")
            & gender.ne("NaT")
        ]

        if not gender.empty:

            gender_counts = (
                gender
                .value_counts()
                .rename_axis("Gender")
                .reset_index(name="Records")
            )

            gender_counts["Percentage"] = (
                gender_counts["Records"]
                / gender_counts["Records"].sum()
                * 100
            ).round(2)

            left, right = st.columns(
                [1.5, 1],
                gap="large",
            )

            with left:
                st.bar_chart(
                    gender_counts.set_index(
                        "Gender"
                    )["Records"],
                    use_container_width=True,
                )

            with right:
                display_gender = gender_counts.copy()

                display_gender["Percentage"] = (
                    display_gender["Percentage"]
                    .map(lambda x: f"{x:.2f}%")
                )

                st.dataframe(
                    display_gender,
                    use_container_width=True,
                    hide_index=True,
                )

        else:
            st.info(
                "Gender information is not available."
            )

    # =========================================================
    # 4. AGE-WISE ANALYSIS
    # =========================================================

    st.divider()

    st.markdown("### 📈 Age-wise Distribution")

    if "Age" in df.columns:

        age_data = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

        age_data = age_data[
            age_data.between(0, 120)
        ]

        if not age_data.empty:

            age_counts = (
                age_data
                .round()
                .astype(int)
                .value_counts()
                .sort_index()
                .rename_axis("Age")
                .reset_index(name="Records")
            )

            st.line_chart(
                age_counts.set_index(
                    "Age"
                )["Records"],
                use_container_width=True,
            )

            st.dataframe(
                age_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Valid age information is not available."
            )

    # =========================================================
    # 5. GENDER × AGE GROUP
    # =========================================================

    st.divider()

    st.markdown("### 👥 Gender × Age Group")

    if (
        "Gender" in df.columns
        and "Age Group" in df.columns
    ):

        cross_df = df[
            [
                "Gender",
                "Age Group",
            ]
        ].copy()

        cross_df["Gender"] = (
            cross_df["Gender"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        cross_df["Age Group"] = (
            cross_df["Age Group"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        cross_df = cross_df[
            cross_df["Gender"].ne("")
            & cross_df["Age Group"].ne("")
            & cross_df["Gender"].ne("nan")
            & cross_df["Age Group"].ne("nan")
        ]

        if not cross_df.empty:

            gender_age = pd.crosstab(
                cross_df["Age Group"],
                cross_df["Gender"],
            )

            preferred_order = [
                "Below 1 year",
                "1-4",
                "5-14",
                "15-24",
                "25-44",
                "45-64",
                "65+",
                "Unknown",
            ]

            available = [
                value
                for value in preferred_order
                if value in gender_age.index
            ]

            remaining = [
                value
                for value in gender_age.index
                if value not in available
            ]

            gender_age = gender_age.reindex(
                available + remaining
            )

            st.bar_chart(
                gender_age,
                use_container_width=True,
            )

            st.dataframe(
                gender_age.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Gender and Age Group cross-analysis "
                "is not available."
            )

    # =========================================================
    # 6. OPD / IPD DEMOGRAPHIC DISTRIBUTION
    # =========================================================

    st.divider()

    st.markdown("### 🏨 OPD / IPD Demographic Distribution")

    if "OPD/IPD" in df.columns:

        opd = _clean_text(
            df,
            "OPD/IPD",
        )

        opd = opd[
            opd.ne("")
            & opd.ne("nan")
            & opd.ne("NaT")
        ]

        if not opd.empty:

            opd_counts = (
                opd
                .value_counts()
                .rename_axis("OPD/IPD")
                .reset_index(name="Records")
            )

            opd_counts["Percentage"] = (
                opd_counts["Records"]
                / opd_counts["Records"].sum()
                * 100
            ).round(2)

            c1, c2 = st.columns(
                [1.5, 1],
                gap="large",
            )

            with c1:
                st.bar_chart(
                    opd_counts.set_index(
                        "OPD/IPD"
                    )["Records"],
                    use_container_width=True,
                )

            with c2:

                display_opd = opd_counts.copy()

                display_opd["Percentage"] = (
                    display_opd["Percentage"]
                    .map(lambda x: f"{x:.2f}%")
                )

                st.dataframe(
                    display_opd,
                    use_container_width=True,
                    hide_index=True,
                )

        else:
            st.info(
                "OPD/IPD information is not available."
            )

    # =========================================================
    # 7. AGE GROUP × OPD/IPD
    # =========================================================

    st.divider()

    st.markdown("### 🎂 Age Group × OPD/IPD")

    if (
        "Age Group" in df.columns
        and "OPD/IPD" in df.columns
    ):

        age_opd = df[
            [
                "Age Group",
                "OPD/IPD",
            ]
        ].copy()

        age_opd["Age Group"] = (
            age_opd["Age Group"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        age_opd["OPD/IPD"] = (
            age_opd["OPD/IPD"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        age_opd = age_opd[
            age_opd["Age Group"].ne("")
            & age_opd["OPD/IPD"].ne("")
            & age_opd["Age Group"].ne("nan")
            & age_opd["OPD/IPD"].ne("nan")
        ]

        if not age_opd.empty:

            age_opd_table = pd.crosstab(
                age_opd["Age Group"],
                age_opd["OPD/IPD"],
            )

            preferred_order = [
                "Below 1 year",
                "1-4",
                "5-14",
                "15-24",
                "25-44",
                "45-64",
                "65+",
                "Unknown",
            ]

            available = [
                value
                for value in preferred_order
                if value in age_opd_table.index
            ]

            remaining = [
                value
                for value in age_opd_table.index
                if value not in available
            ]

            age_opd_table = age_opd_table.reindex(
                available + remaining
            )

            st.bar_chart(
                age_opd_table,
                use_container_width=True,
            )

            st.dataframe(
                age_opd_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Age Group and OPD/IPD cross-analysis "
                "is not available."
            )

    # =========================================================
    # 8. DISEASE × GENDER
    # =========================================================

    st.divider()

    st.markdown("### 🦠 Disease × Gender")

    if (
        "Disease" in df.columns
        and "Gender" in df.columns
    ):

        disease_gender = df[
            [
                "Disease",
                "Gender",
            ]
        ].copy()

        disease_gender["Disease"] = (
            disease_gender["Disease"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_gender["Gender"] = (
            disease_gender["Gender"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_gender = disease_gender[
            disease_gender["Disease"].ne("")
            & disease_gender["Gender"].ne("")
            & disease_gender["Disease"].ne("nan")
            & disease_gender["Gender"].ne("nan")
        ]

        if not disease_gender.empty:

            disease_gender_table = pd.crosstab(
                disease_gender["Disease"],
                disease_gender["Gender"],
            )

            top_diseases = (
                disease_gender_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .head(10)
                .index
            )

            disease_gender_table = (
                disease_gender_table
                .loc[top_diseases]
            )

            st.bar_chart(
                disease_gender_table,
                use_container_width=True,
            )

            st.caption(
                "The chart displays the top 10 diseases "
                "by total records within the selected filters."
            )

            st.dataframe(
                disease_gender_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Disease and Gender cross-analysis "
                "is not available."
            )

    # =========================================================
    # 9. DATA QUALITY NOTE
    # =========================================================

    st.divider()

    st.markdown("### ℹ️ Demographic Data Quality")

    missing_age = 0
    missing_gender = 0
    missing_age_group = 0

    if "Age" in df.columns:
        age_numeric = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )
        missing_age = int(
            age_numeric.isna().sum()
        )

    if "Gender" in df.columns:
        gender_values = _clean_text(
            df,
            "Gender",
        )
        missing_gender = int(
            gender_values.eq("").sum()
        )

    if "Age Group" in df.columns:
        age_group_values = _clean_text(
            df,
            "Age Group",
        )
        missing_age_group = int(
            age_group_values.eq("").sum()
        )

    quality_table = pd.DataFrame(
        {
            "Indicator": [
                "Total Records",
                "Missing / Invalid Age",
                "Missing Gender",
                "Missing Age Group",
            ],
            "Count": [
                total_records,
                missing_age,
                missing_gender,
                missing_age_group,
            ],
        }
    )

    st.dataframe(
        quality_table,
        use_container_width=True,
        hide_index=True,
    )
