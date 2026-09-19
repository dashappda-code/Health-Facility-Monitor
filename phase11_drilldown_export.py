import io

import pandas as pd
import streamlit as st


def _clean_series(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="string")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _non_blank(df, column):
    values = _clean_series(df, column)

    return values[
        values.ne("")
        & values.ne("nan")
        & values.ne("NaT")
    ]


def _make_excel(df):
    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Filtered Data",
        )

    output.seek(0)

    return output.getvalue()


def _make_csv(df):
    return df.to_csv(
        index=False
    ).encode("utf-8-sig")


def _summary_table(df, column, label):
    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return pd.DataFrame(
            columns=[
                label,
                "Records",
                "Percentage",
            ]
        )

    values = _non_blank(
        df,
        column,
    )

    if values.empty:
        return pd.DataFrame(
            columns=[
                label,
                "Records",
                "Percentage",
            ]
        )

    counts = (
        values
        .value_counts()
        .rename_axis(label)
        .reset_index(
            name="Records"
        )
    )

    total = counts["Records"].sum()

    if total > 0:
        counts["Percentage"] = (
            counts["Records"]
            / total
            * 100
        ).round(2)

    return counts


def render_drilldown_export(df):

    st.subheader("🔎 Drill-down & Export")

    st.caption(
        "Detailed management-level drill-down and export "
        "for the currently filtered dataset."
    )

    # =========================================================
    # EMPTY DATA
    # =========================================================

    if df is None or df.empty:

        st.warning(
            "No records are available for drill-down or export "
            "under the currently selected filters."
        )

        return

    working_df = df.copy()

    total_records = len(
        working_df
    )

    # =========================================================
    # 1. CURRENT FILTERED DATASET SUMMARY
    # =========================================================

    st.markdown(
        "### 📊 Current Filtered Dataset"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Filtered Records",
            f"{total_records:,}",
        )

    with c2:
        if "Facility Name" in working_df.columns:
            facilities = _non_blank(
                working_df,
                "Facility Name",
            ).nunique()
        else:
            facilities = 0

        st.metric(
            "Facilities",
            f"{facilities:,}",
        )

    with c3:
        if "Ward Name" in working_df.columns:
            wards = _non_blank(
                working_df,
                "Ward Name",
            ).nunique()
        else:
            wards = 0

        st.metric(
            "Wards",
            f"{wards:,}",
        )

    with c4:
        if "Disease" in working_df.columns:
            diseases = _non_blank(
                working_df,
                "Disease",
            ).nunique()
        else:
            diseases = 0

        st.metric(
            "Diseases",
            f"{diseases:,}",
        )

    # =========================================================
    # 2. DRILL-DOWN SELECTORS
    # =========================================================

    st.markdown(
        "### 🎯 Management Drill-down"
    )

    st.caption(
        "These controls operate within the data already selected "
        "by the Global Dashboard Filters."
    )

    drill1, drill2, drill3 = st.columns(
        [1.4, 1.4, 1.4],
        gap="small",
    )

    with drill1:

        facility_options = sorted(
            _non_blank(
                working_df,
                "Facility Name",
            ).unique().tolist()
        ) if "Facility Name" in working_df.columns else []

        selected_drill_facility = st.multiselect(
            "🏥 Drill-down Facility",
            options=facility_options,
            default=[],
            placeholder="All Facilities",
            key="drilldown_facility",
        )

    with drill2:

        ward_options = sorted(
            _non_blank(
                working_df,
                "Ward Name",
            ).unique().tolist()
        ) if "Ward Name" in working_df.columns else []

        selected_drill_ward = st.multiselect(
            "📍 Drill-down Ward",
            options=ward_options,
            default=[],
            placeholder="All Wards",
            key="drilldown_ward",
        )

    with drill3:

        disease_options = sorted(
            _non_blank(
                working_df,
                "Disease",
            ).unique().tolist()
        ) if "Disease" in working_df.columns else []

        selected_drill_disease = st.multiselect(
            "🦠 Drill-down Disease",
            options=disease_options,
            default=[],
            placeholder="All Diseases",
            key="drilldown_disease",
        )

    drill_df = working_df.copy()

    if selected_drill_facility:
        if "Facility Name" in drill_df.columns:

            drill_df = drill_df[
                drill_df["Facility Name"]
                .fillna("")
                .astype(str)
                .str.strip()
                .isin(
                    selected_drill_facility
                )
            ]

    if selected_drill_ward:
        if "Ward Name" in drill_df.columns:

            drill_df = drill_df[
                drill_df["Ward Name"]
                .fillna("")
                .astype(str)
                .str.strip()
                .isin(
                    selected_drill_ward
                )
            ]

    if selected_drill_disease:
        if "Disease" in drill_df.columns:

            drill_df = drill_df[
                drill_df["Disease"]
                .fillna("")
                .astype(str)
                .str.strip()
                .isin(
                    selected_drill_disease
                )
            ]

    drill_df = (
        drill_df
        .reset_index(drop=True)
    )

    st.info(
        f"Drill-down Records: "
        f"**{len(drill_df):,}** / "
        f"**{len(working_df):,}**"
    )

    if drill_df.empty:

        st.warning(
            "No records match the selected drill-down criteria."
        )

        return

    # =========================================================
    # 3. FACILITY-WISE DRILL-DOWN
    # =========================================================

    st.markdown(
        "### 🏥 Facility-wise Drill-down"
    )

    if "Facility Name" in drill_df.columns:

        facility_table = _summary_table(
            drill_df,
            "Facility Name",
            "Facility",
        )

        if not facility_table.empty:

            st.dataframe(
                facility_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No usable facility information is available."
            )

    # =========================================================
    # 4. WARD-WISE DRILL-DOWN
    # =========================================================

    st.markdown(
        "### 📍 Ward-wise Drill-down"
    )

    if "Ward Name" in drill_df.columns:

        ward_table = _summary_table(
            drill_df,
            "Ward Name",
            "Ward",
        )

        if not ward_table.empty:

            st.dataframe(
                ward_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No usable ward information is available."
            )

    # =========================================================
    # 5. DISEASE-WISE DRILL-DOWN
    # =========================================================

    st.markdown(
        "### 🦠 Disease-wise Drill-down"
    )

    if "Disease" in drill_df.columns:

        disease_table = _summary_table(
            drill_df,
            "Disease",
            "Disease",
        )

        if not disease_table.empty:

            st.dataframe(
                disease_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No usable disease information is available."
            )

    # =========================================================
    # 6. FACILITY × WARD
    # =========================================================

    st.markdown(
        "### 🏥📍 Facility × Ward Analysis"
    )

    if (
        "Facility Name" in drill_df.columns
        and "Ward Name" in drill_df.columns
    ):

        facility_ward = drill_df.copy()

        facility_ward["Facility Name"] = (
            facility_ward["Facility Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_ward["Ward Name"] = (
            facility_ward["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_ward = facility_ward[
            facility_ward["Facility Name"].ne("")
            & facility_ward["Ward Name"].ne("")
        ]

        if not facility_ward.empty:

            facility_ward_table = (
                facility_ward
                .groupby(
                    [
                        "Facility Name",
                        "Ward Name",
                    ],
                    dropna=False,
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .sort_values(
                    "Records",
                    ascending=False,
                )
                .reset_index(
                    drop=True
                )
            )

            st.dataframe(
                facility_ward_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No complete Facility × Ward combinations "
                "are available."
            )

    # =========================================================
    # 7. FACILITY × DISEASE
    # =========================================================

    st.markdown(
        "### 🏥🦠 Facility × Disease Analysis"
    )

    if (
        "Facility Name" in drill_df.columns
        and "Disease" in drill_df.columns
    ):

        facility_disease = drill_df.copy()

        facility_disease["Facility Name"] = (
            facility_disease["Facility Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_disease["Disease"] = (
            facility_disease["Disease"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_disease = facility_disease[
            facility_disease["Facility Name"].ne("")
            & facility_disease["Disease"].ne("")
        ]

        if not facility_disease.empty:

            facility_disease_table = (
                facility_disease
                .groupby(
                    [
                        "Facility Name",
                        "Disease",
                    ],
                    dropna=False,
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .sort_values(
                    "Records",
                    ascending=False,
                )
                .reset_index(
                    drop=True
                )
            )

            st.dataframe(
                facility_disease_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No complete Facility × Disease combinations "
                "are available."
            )

    # =========================================================
    # 8. WARD × DISEASE
    # =========================================================

    st.markdown(
        "### 📍🦠 Ward × Disease Analysis"
    )

    if (
        "Ward Name" in drill_df.columns
        and "Disease" in drill_df.columns
    ):

        ward_disease = drill_df.copy()

        ward_disease["Ward Name"] = (
            ward_disease["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_disease["Disease"] = (
            ward_disease["Disease"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_disease = ward_disease[
            ward_disease["Ward Name"].ne("")
            & ward_disease["Disease"].ne("")
        ]

        if not ward_disease.empty:

            ward_disease_table = (
                ward_disease
                .groupby(
                    [
                        "Ward Name",
                        "Disease",
                    ],
                    dropna=False,
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .sort_values(
                    "Records",
                    ascending=False,
                )
                .reset_index(
                    drop=True
                )
            )

            st.dataframe(
                ward_disease_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No complete Ward × Disease combinations "
                "are available."
            )

    # =========================================================
    # 9. MONTH-WISE DRILL-DOWN
    # =========================================================

    st.markdown(
        "### 🗓️ Month-wise Drill-down"
    )

    if "Month" in drill_df.columns:

        month_table = _summary_table(
            drill_df,
            "Month",
            "Month",
        )

        if not month_table.empty:

            st.dataframe(
                month_table,
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # 10. GENDER-WISE DRILL-DOWN
    # =========================================================

    st.markdown(
        "### 👤 Gender-wise Drill-down"
    )

    if "Gender" in drill_df.columns:

        gender_table = _summary_table(
            drill_df,
            "Gender",
            "Gender",
        )

        if not gender_table.empty:

            st.dataframe(
                gender_table,
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # 11. AGE GROUP-WISE DRILL-DOWN
    # =========================================================

    st.markdown(
        "### 🎂 Age Group-wise Drill-down"
    )

    if "Age Group" in drill_df.columns:

        age_group_table = _summary_table(
            drill_df,
            "Age Group",
            "Age Group",
        )

        if not age_group_table.empty:

            st.dataframe(
                age_group_table,
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # 12. OPD / IPD DRILL-DOWN
    # =========================================================

    st.markdown(
        "### 🏨 OPD / IPD Drill-down"
    )

    if "OPD/IPD" in drill_df.columns:

        opd_ipd_table = _summary_table(
            drill_df,
            "OPD/IPD",
            "OPD / IPD",
        )

        if not opd_ipd_table.empty:

            st.dataframe(
                opd_ipd_table,
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # 13. RECORD-LEVEL DETAIL
    # =========================================================

    st.markdown(
        "### 📋 Record-level Detail"
    )

    st.caption(
        "The table below contains the records after both "
        "Global Dashboard Filters and Drill-down Filters."
    )

    display_limit = st.selectbox(
        "Number of records to display",
        options=[
            50,
            100,
            250,
            500,
            1000,
            2500,
        ],
        index=1,
        key="drilldown_display_limit",
    )

    st.dataframe(
        drill_df.head(
            display_limit
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"Showing first "
        f"{min(display_limit, len(drill_df)):,} "
        f"of {len(drill_df):,} drill-down records."
    )

    # =========================================================
    # 14. COLUMN SELECTION FOR EXPORT
    # =========================================================

    st.markdown(
        "### 📤 Export Configuration"
    )

    available_columns = (
        drill_df.columns.tolist()
    )

    default_columns = [
        column
        for column in [
            "Reporting Date",
            "Year",
            "Month",
            "Week",
            "Disease",
            "Facility Name",
            "Ward Name",
            "Gender",
            "Age",
            "Age Group",
            "OPD/IPD",
            "Patient Address",
            "Confirmed Diagnosis",
        ]
        if column in available_columns
    ]

    selected_columns = st.multiselect(
        "Select columns for custom export",
        options=available_columns,
        default=default_columns,
        key="drilldown_export_columns",
    )

    if not selected_columns:

        st.warning(
            "Select at least one column for custom export."
        )

    # =========================================================
    # 15. EXPORT DATA
    # =========================================================

    st.markdown(
        "### 💾 Download Filtered Data"
    )

    csv_data = _make_csv(
        drill_df
    )

    excel_data = _make_excel(
        drill_df
    )

    e1, e2 = st.columns(2)

    with e1:

        st.download_button(
            label="⬇️ Download Complete CSV",
            data=csv_data,
            file_name="dashboard_drilldown_filtered_data.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_drilldown_csv",
        )

    with e2:

        st.download_button(
            label="⬇️ Download Complete Excel",
            data=excel_data,
            file_name="dashboard_drilldown_filtered_data.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
            key="download_drilldown_excel",
        )

    # =========================================================
    # 16. CUSTOM COLUMN EXPORT
    # =========================================================

    if selected_columns:

        custom_export_df = drill_df[
            selected_columns
        ].copy()

        custom_csv = _make_csv(
            custom_export_df
        )

        custom_excel = _make_excel(
            custom_export_df
        )

        st.markdown(
            "### 📑 Custom Column Export"
        )

        c1, c2 = st.columns(2)

        with c1:

            st.download_button(
                label="⬇️ Download Selected Columns CSV",
                data=custom_csv,
                file_name="dashboard_custom_columns.csv",
                mime="text/csv",
                use_container_width=True,
                key="download_custom_csv",
            )

        with c2:

            st.download_button(
                label="⬇️ Download Selected Columns Excel",
                data=custom_excel,
                file_name="dashboard_custom_columns.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
                key="download_custom_excel",
            )

    # =========================================================
    # 17. EXPORT SCOPE INFORMATION
    # =========================================================

    st.markdown(
        "### ℹ️ Export Scope"
    )

    st.info(
        "Exports contain the records currently available after "
        "the Global Dashboard Filters and the Drill-down selections. "
        "If you need the complete dataset, reset all Global Dashboard "
        "Filters and keep all Drill-down selectors blank before export."
    )

    # =========================================================
    # 18. MANAGEMENT FOLLOW-UP
    # =========================================================

    st.markdown(
        "### 📝 Management Follow-up"
    )

    st.markdown(
        """
        The drill-down section can be used to identify:

        - Facilities contributing the highest record volume.
        - Wards contributing the highest record volume.
        - Disease concentration by facility.
        - Disease concentration by ward.
        - Facility × Ward combinations requiring review.
        - Monthly changes within a selected facility or ward.
        - Gender and age-group composition of selected records.
        - OPD/IPD distribution within a selected management segment.

        These outputs should be interpreted together with the
        Validation & KPI section and the quality/completeness of
        the underlying reporting data.
        """
    )

    st.success(
        "Drill-down and Export module is ready for the current "
        "filtered dataset."
    )
