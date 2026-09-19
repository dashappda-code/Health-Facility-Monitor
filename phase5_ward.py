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


def render_ward(df):

    st.subheader("📍 Ward Analysis")

    if df is None or df.empty:
        st.warning(
            "No records available for the selected filters."
        )
        return

    st.caption(
        "Ward-wise burden, disease distribution, facility distribution "
        "and demographic analysis based on the selected Global Dashboard Filters."
    )

    # =========================================================
    # 1. WARD SUMMARY
    # =========================================================

    st.markdown("### 📊 Ward Summary")

    if "Ward Name" not in df.columns:
        st.warning(
            "Ward information is not available in the dataset."
        )
        return

    ward = _clean_text(
        df,
        "Ward Name",
    )

    ward = ward[
        ward.ne("")
        & ward.ne("nan")
        & ward.ne("NaT")
    ]

    if ward.empty:
        st.warning(
            "No valid ward records are available."
        )
        return

    ward_counts = (
        ward
        .value_counts()
        .rename_axis("Ward")
        .reset_index(name="Records")
    )

    total_valid_ward_records = int(
        ward_counts["Records"].sum()
    )

    ward_counts["Percentage"] = (
        ward_counts["Records"]
        / total_valid_ward_records
        * 100
    ).round(2)

    ward_counts.insert(
        0,
        "Rank",
        range(1, len(ward_counts) + 1),
    )

    # =========================================================
    # 2. TOP BURDEN WARD
    # =========================================================

    st.markdown("### 🏆 Top Burden Ward")

    top_ward = ward_counts.iloc[0]

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Top Ward",
            str(top_ward["Ward"]),
        )

    with c2:
        st.metric(
            "Records",
            f"{int(top_ward['Records']):,}",
        )

    with c3:
        st.metric(
            "Share",
            f"{float(top_ward['Percentage']):.2f}%",
        )

    with c4:
        st.metric(
            "Total Wards",
            f"{len(ward_counts):,}",
        )

    # =========================================================
    # 3. WARD-WISE RANKING
    # =========================================================

    st.divider()

    st.markdown("### 📋 Ward-wise Burden Ranking")

    display_wards = ward_counts.copy()

    display_wards["Percentage"] = (
        display_wards["Percentage"]
        .map(lambda x: f"{x:.2f}%")
    )

    st.dataframe(
        display_wards,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # 4. WARD-WISE BAR CHART
    # =========================================================

    st.markdown("### 📊 Ward-wise Record Distribution")

    chart_wards = ward_counts.head(25)

    st.bar_chart(
        chart_wards.set_index("Ward")["Records"],
        use_container_width=True,
    )

    if len(ward_counts) > 25:
        st.caption(
            "Chart displays the top 25 wards by record volume. "
            "The table above contains all available wards."
        )

    # =========================================================
    # 5. TOP 10 WARDS
    # =========================================================

    st.divider()

    st.markdown("### 🔝 Top 10 Burden Wards")

    top10 = ward_counts.head(10).copy()

    top10_display = top10[
        [
            "Rank",
            "Ward",
            "Records",
            "Percentage",
        ]
    ].copy()

    top10_display["Percentage"] = (
        top10_display["Percentage"]
        .map(lambda x: f"{x:.2f}%")
    )

    st.dataframe(
        top10_display,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # 6. DISEASE × WARD
    # =========================================================

    st.divider()

    st.markdown("### 🦠 Disease-wise Ward Burden")

    if "Disease" in df.columns:

        disease_ward = df[
            [
                "Ward Name",
                "Disease",
            ]
        ].copy()

        disease_ward["Ward Name"] = (
            disease_ward["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_ward["Disease"] = (
            disease_ward["Disease"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_ward = disease_ward[
            disease_ward["Ward Name"].ne("")
            & disease_ward["Disease"].ne("")
            & disease_ward["Ward Name"].ne("nan")
            & disease_ward["Disease"].ne("nan")
        ]

        if not disease_ward.empty:

            disease_ward_table = pd.crosstab(
                disease_ward["Ward Name"],
                disease_ward["Disease"],
            )

            # Keep top 10 diseases overall.
            top_diseases = (
                disease_ward_table
                .sum(axis=0)
                .sort_values(
                    ascending=False
                )
                .head(10)
                .index
                .tolist()
            )

            disease_ward_table = (
                disease_ward_table[
                    top_diseases
                ]
            )

            # Keep top 25 wards for visual readability.
            top_wards = (
                disease_ward_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .head(25)
                .index
            )

            disease_ward_table = (
                disease_ward_table
                .loc[top_wards]
            )

            st.bar_chart(
                disease_ward_table,
                use_container_width=True,
            )

            st.caption(
                "Chart displays the top 10 diseases across "
                "the top 25 wards by record volume."
            )

            st.dataframe(
                disease_ward_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Disease and Ward information is not available."
            )

    # =========================================================
    # 7. FACILITY × WARD
    # =========================================================

    st.divider()

    st.markdown("### 🏥 Facility-wise Ward Distribution")

    if "Facility Name" in df.columns:

        facility_ward = df[
            [
                "Ward Name",
                "Facility Name",
            ]
        ].copy()

        facility_ward["Ward Name"] = (
            facility_ward["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_ward["Facility Name"] = (
            facility_ward["Facility Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_ward = facility_ward[
            facility_ward["Ward Name"].ne("")
            & facility_ward["Facility Name"].ne("")
            & facility_ward["Ward Name"].ne("nan")
            & facility_ward["Facility Name"].ne("nan")
        ]

        if not facility_ward.empty:

            facility_ward_table = pd.crosstab(
                facility_ward["Ward Name"],
                facility_ward["Facility Name"],
            )

            top_facilities = (
                facility_ward_table
                .sum(axis=0)
                .sort_values(
                    ascending=False
                )
                .head(10)
                .index
                .tolist()
            )

            facility_ward_table = (
                facility_ward_table[
                    top_facilities
                ]
            )

            top_wards = (
                facility_ward_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .head(25)
                .index
            )

            facility_ward_table = (
                facility_ward_table
                .loc[top_wards]
            )

            st.bar_chart(
                facility_ward_table,
                use_container_width=True,
            )

            st.caption(
                "Chart displays the top 10 facilities across "
                "the top 25 wards by record volume."
            )

            st.dataframe(
                facility_ward_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Facility and Ward information is not available."
            )

    # =========================================================
    # 8. WARD × GENDER
    # =========================================================

    st.divider()

    st.markdown("### 👥 Ward-wise Gender Distribution")

    if "Gender" in df.columns:

        ward_gender = df[
            [
                "Ward Name",
                "Gender",
            ]
        ].copy()

        ward_gender["Ward Name"] = (
            ward_gender["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_gender["Gender"] = (
            ward_gender["Gender"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_gender = ward_gender[
            ward_gender["Ward Name"].ne("")
            & ward_gender["Gender"].ne("")
            & ward_gender["Ward Name"].ne("nan")
            & ward_gender["Gender"].ne("nan")
        ]

        if not ward_gender.empty:

            gender_table = pd.crosstab(
                ward_gender["Ward Name"],
                ward_gender["Gender"],
            )

            top_wards = (
                gender_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .head(20)
                .index
            )

            gender_table = (
                gender_table
                .loc[top_wards]
            )

            st.bar_chart(
                gender_table,
                use_container_width=True,
            )

            st.dataframe(
                gender_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Ward and Gender information is not available."
            )

    # =========================================================
    # 9. WARD × AGE GROUP
    # =========================================================

    st.divider()

    st.markdown("### 🎂 Ward-wise Age Group Distribution")

    if "Age Group" in df.columns:

        ward_age = df[
            [
                "Ward Name",
                "Age Group",
            ]
        ].copy()

        ward_age["Ward Name"] = (
            ward_age["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_age["Age Group"] = (
            ward_age["Age Group"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_age = ward_age[
            ward_age["Ward Name"].ne("")
            & ward_age["Age Group"].ne("")
            & ward_age["Ward Name"].ne("nan")
            & ward_age["Age Group"].ne("nan")
        ]

        if not ward_age.empty:

            age_table = pd.crosstab(
                ward_age["Ward Name"],
                ward_age["Age Group"],
            )

            top_wards = (
                age_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .head(20)
                .index
            )

            age_table = (
                age_table
                .loc[top_wards]
            )

            st.bar_chart(
                age_table,
                use_container_width=True,
            )

            st.dataframe(
                age_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Ward and Age Group information is not available."
            )

    # =========================================================
    # 10. TOP WARD × TOP FACILITY DETAIL
    # =========================================================

    st.divider()

    st.markdown("### 🏥 Top Ward – Facility Detail")

    if "Facility Name" in df.columns:

        top_ward_name = str(
            top_ward["Ward"]
        )

        ward_facility_df = df[
            df["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq(top_ward_name)
        ].copy()

        if not ward_facility_df.empty:

            facility_values = (
                ward_facility_df["Facility Name"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            facility_values = facility_values[
                facility_values.ne("")
                & facility_values.ne("nan")
            ]

            if not facility_values.empty:

                top_facilities = (
                    facility_values
                    .value_counts()
                    .rename_axis("Facility")
                    .reset_index(name="Records")
                )

                top_facilities.insert(
                    0,
                    "Rank",
                    range(
                        1,
                        len(top_facilities) + 1,
                    ),
                )

                st.dataframe(
                    top_facilities,
                    use_container_width=True,
                    hide_index=True,
                )

            else:
                st.info(
                    "Facility information is not available "
                    "for the top burden ward."
                )

        else:
            st.info(
                "No records found for the top burden ward."
            )

    # =========================================================
    # 11. WARD DATA QUALITY
    # =========================================================

    st.divider()

    st.markdown("### ℹ️ Ward Data Quality")

    total_records = len(df)

    missing_ward = (
        total_records
        - len(ward)
    )

    ward_quality = pd.DataFrame(
        {
            "Indicator": [
                "Total Records",
                "Records with Valid Ward",
                "Records with Missing / Blank Ward",
                "Unique Wards",
            ],
            "Count": [
                total_records,
                len(ward),
                missing_ward,
                len(ward_counts),
            ],
        }
    )

    st.dataframe(
        ward_quality,
        use_container_width=True,
        hide_index=True,
    )
