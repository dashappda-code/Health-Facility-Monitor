import streamlit as st
import pandas as pd


def _clean_values(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="string")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _missing_count(df, column):
    if df is None or df.empty or column not in df.columns:
        return len(df) if df is not None else 0

    values = _clean_values(df, column)

    return int(
        (
            values.eq("")
            | values.eq("nan")
            | values.eq("NaT")
        ).sum()
    )


def _valid_count(df, column):
    if df is None or df.empty or column not in df.columns:
        return 0

    values = _clean_values(df, column)

    return int(
        (
            values.ne("")
            & values.ne("nan")
            & values.ne("NaT")
        ).sum()
    )


def _unique_count(df, column):
    if df is None or df.empty or column not in df.columns:
        return 0

    values = _clean_values(df, column)

    values = values[
        values.ne("")
        & values.ne("nan")
        & values.ne("NaT")
    ]

    return int(values.nunique())


def _percentage(part, total):
    if total == 0:
        return 0.0

    return round((part / total) * 100, 2)


def _quality_status(completeness):
    if completeness >= 95:
        return "Good"
    if completeness >= 85:
        return "Needs Review"
    return "Attention Required"


def render_validation_kpi(df):

    st.subheader("✅ Validation & KPI")

    st.caption(
        "Data quality, completeness, consistency and programme KPI "
        "assessment for the currently filtered dataset."
    )

    # =========================================================
    # EMPTY DATA
    # =========================================================

    if df is None or df.empty:
        st.warning(
            "No records are available for validation under the "
            "currently selected filters."
        )
        return

    total_records = len(df)

    # =========================================================
    # 1. CORE DATASET KPI
    # =========================================================

    st.markdown("### 📊 Core Dataset KPI")

    unique_diseases = _unique_count(df, "Disease")
    unique_facilities = _unique_count(df, "Facility Name")
    unique_wards = _unique_count(df, "Ward Name")
    unique_genders = _unique_count(df, "Gender")
    unique_age_groups = _unique_count(df, "Age Group")

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        st.metric(
            "Total Records",
            f"{total_records:,}",
        )

    with k2:
        st.metric(
            "Diseases",
            f"{unique_diseases:,}",
        )

    with k3:
        st.metric(
            "Facilities",
            f"{unique_facilities:,}",
        )

    with k4:
        st.metric(
            "Wards",
            f"{unique_wards:,}",
        )

    with k5:
        st.metric(
            "Age Groups",
            f"{unique_age_groups:,}",
        )

    # =========================================================
    # 2. REPORTING PERIOD
    # =========================================================

    st.markdown("### 📅 Reporting Period Validation")

    if "Reporting Date" in df.columns:

        dates = pd.to_datetime(
            df["Reporting Date"],
            errors="coerce",
        )

        valid_dates = dates.dropna()

        invalid_dates = int(dates.isna().sum())

        if not valid_dates.empty:
            min_date = valid_dates.min()
            max_date = valid_dates.max()

            d1, d2, d3 = st.columns(3)

            with d1:
                st.metric(
                    "Earliest Reporting Date",
                    min_date.strftime("%d-%m-%Y"),
                )

            with d2:
                st.metric(
                    "Latest Reporting Date",
                    max_date.strftime("%d-%m-%Y"),
                )

            with d3:
                st.metric(
                    "Invalid / Missing Dates",
                    f"{invalid_dates:,}",
                )

            st.info(
                f"Reporting period covered by the filtered dataset: "
                f"**{min_date.strftime('%d-%m-%Y')}** to "
                f"**{max_date.strftime('%d-%m-%Y')}**."
            )

        else:
            st.error(
                "No valid Reporting Date values are available "
                "in the filtered dataset."
            )

    else:
        st.warning(
            "Reporting Date column is not available."
        )

    # =========================================================
    # 3. DATA COMPLETENESS
    # =========================================================

    st.markdown("### 🧾 Data Completeness")

    completeness_columns = [
        ("Reporting Date", "Reporting Date"),
        ("Year", "Year"),
        ("Month", "Month"),
        ("Week", "Week"),
        ("Disease", "Disease"),
        ("Facility Name", "Facility"),
        ("Ward Name", "Ward"),
        ("Gender", "Gender"),
        ("Age", "Age"),
        ("Age Group", "Age Group"),
        ("OPD/IPD", "OPD/IPD"),
        ("Patient Address", "Patient Address"),
    ]

    completeness_rows = []

    for column, display_name in completeness_columns:

        if column not in df.columns:
            completeness_rows.append(
                {
                    "Field": display_name,
                    "Available": "No",
                    "Valid Records": 0,
                    "Missing Records": total_records,
                    "Completeness (%)": 0.0,
                    "Status": "Attention Required",
                }
            )
            continue

        if column == "Reporting Date":

            dates = pd.to_datetime(
                df[column],
                errors="coerce",
            )

            valid_count = int(dates.notna().sum())

        elif column == "Age":

            age = pd.to_numeric(
                df[column],
                errors="coerce",
            )

            valid_count = int(
                age.between(
                    0,
                    120,
                ).sum()
            )

        else:

            valid_count = _valid_count(
                df,
                column,
            )

        missing_count = total_records - valid_count

        completeness = _percentage(
            valid_count,
            total_records,
        )

        completeness_rows.append(
            {
                "Field": display_name,
                "Available": "Yes",
                "Valid Records": valid_count,
                "Missing Records": missing_count,
                "Completeness (%)": completeness,
                "Status": _quality_status(
                    completeness
                ),
            }
        )

    completeness_df = pd.DataFrame(
        completeness_rows
    )

    st.dataframe(
        completeness_df,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # 4. OVERALL COMPLETENESS
    # =========================================================

    valid_completeness = completeness_df[
        completeness_df["Available"].eq("Yes")
    ]["Completeness (%)"]

    if not valid_completeness.empty:

        overall_completeness = round(
            valid_completeness.mean(),
            2,
        )

        st.markdown("### 📈 Overall Data Completeness")

        c1, c2 = st.columns(2)

        with c1:
            st.metric(
                "Average Field Completeness",
                f"{overall_completeness:.2f}%",
            )

        with c2:
            st.metric(
                "Overall Status",
                _quality_status(
                    overall_completeness
                ),
            )

    # =========================================================
    # 5. AGE VALIDATION
    # =========================================================

    st.markdown("### 🎂 Age Validation")

    if "Age" in df.columns:

        age = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

        valid_age = age.between(
            0,
            120,
        )

        missing_age = int(
            age.isna().sum()
        )

        invalid_age = int(
            (
                age.notna()
                & ~valid_age
            ).sum()
        )

        valid_age_count = int(
            valid_age.sum()
        )

        a1, a2, a3, a4 = st.columns(4)

        with a1:
            st.metric(
                "Valid Age",
                f"{valid_age_count:,}",
            )

        with a2:
            st.metric(
                "Missing Age",
                f"{missing_age:,}",
            )

        with a3:
            st.metric(
                "Invalid Age",
                f"{invalid_age:,}",
            )

        with a4:
            st.metric(
                "Age Completeness",
                f"{_percentage(valid_age_count, total_records):.2f}%",
            )

        if invalid_age > 0:
            st.warning(
                "Some records contain age values outside the "
                "expected 0–120 year range."
            )

    else:
        st.warning(
            "Age column is not available."
        )

    # =========================================================
    # 6. GENDER VALIDATION
    # =========================================================

    st.markdown("### 👤 Gender Validation")

    if "Gender" in df.columns:

        gender = _clean_values(
            df,
            "Gender",
        )

        gender_non_blank = gender[
            gender.ne("")
            & gender.ne("nan")
        ]

        gender_counts = (
            gender_non_blank
            .value_counts()
            .rename_axis("Gender")
            .reset_index(
                name="Records"
            )
        )

        if not gender_counts.empty:

            st.dataframe(
                gender_counts,
                use_container_width=True,
                hide_index=True,
            )

            missing_gender = int(
                (
                    gender.eq("")
                    | gender.eq("nan")
                ).sum()
            )

            st.caption(
                f"Missing/blank gender records: "
                f"**{missing_gender:,}**"
            )

        else:
            st.warning(
                "No usable Gender values found."
            )

    # =========================================================
    # 7. DISEASE VALIDATION
    # =========================================================

    st.markdown("### 🦠 Disease Validation")

    if "Disease" in df.columns:

        disease = _clean_values(
            df,
            "Disease",
        )

        disease_non_blank = disease[
            disease.ne("")
            & disease.ne("nan")
        ]

        disease_counts = (
            disease_non_blank
            .value_counts()
            .rename_axis("Disease")
            .reset_index(
                name="Records"
            )
        )

        d1, d2 = st.columns(2)

        with d1:
            st.metric(
                "Unique Diseases",
                f"{disease_counts.shape[0]:,}",
            )

        with d2:
            missing_disease = int(
                (
                    disease.eq("")
                    | disease.eq("nan")
                ).sum()
            )

            st.metric(
                "Missing Disease",
                f"{missing_disease:,}",
            )

        if not disease_counts.empty:
            st.dataframe(
                disease_counts,
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # 8. FACILITY VALIDATION
    # =========================================================

    st.markdown("### 🏥 Facility Validation")

    if "Facility Name" in df.columns:

        facility = _clean_values(
            df,
            "Facility Name",
        )

        valid_facility = facility[
            facility.ne("")
            & facility.ne("nan")
        ]

        facility_counts = (
            valid_facility
            .value_counts()
            .rename_axis("Facility")
            .reset_index(
                name="Records"
            )
        )

        f1, f2 = st.columns(2)

        with f1:
            st.metric(
                "Unique Facilities",
                f"{facility_counts.shape[0]:,}",
            )

        with f2:
            missing_facility = int(
                (
                    facility.eq("")
                    | facility.eq("nan")
                ).sum()
            )

            st.metric(
                "Missing Facility",
                f"{missing_facility:,}",
            )

        if not facility_counts.empty:
            st.markdown("#### Facility Record Distribution")

            st.dataframe(
                facility_counts.head(20),
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # 9. WARD VALIDATION
    # =========================================================

    st.markdown("### 📍 Ward Validation")

    if "Ward Name" in df.columns:

        ward = _clean_values(
            df,
            "Ward Name",
        )

        valid_ward = ward[
            ward.ne("")
            & ward.ne("nan")
        ]

        ward_counts = (
            valid_ward
            .value_counts()
            .rename_axis("Ward")
            .reset_index(
                name="Records"
            )
        )

        w1, w2 = st.columns(2)

        with w1:
            st.metric(
                "Unique Wards",
                f"{ward_counts.shape[0]:,}",
            )

        with w2:
            missing_ward = int(
                (
                    ward.eq("")
                    | ward.eq("nan")
                ).sum()
            )

            st.metric(
                "Missing Ward",
                f"{missing_ward:,}",
            )

        if not ward_counts.empty:
            st.markdown("#### Ward Record Distribution")

            st.dataframe(
                ward_counts.head(25),
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # 10. OPD / IPD VALIDATION
    # =========================================================

    st.markdown("### 🏨 OPD / IPD Validation")

    if "OPD/IPD" in df.columns:

        opd_ipd = _clean_values(
            df,
            "OPD/IPD",
        )

        valid_opd_ipd = opd_ipd[
            opd_ipd.ne("")
            & opd_ipd.ne("nan")
        ]

        opd_ipd_counts = (
            valid_opd_ipd
            .value_counts()
            .rename_axis("OPD / IPD")
            .reset_index(
                name="Records"
            )
        )

        if not opd_ipd_counts.empty:

            st.dataframe(
                opd_ipd_counts,
                use_container_width=True,
                hide_index=True,
            )

            missing_opd_ipd = int(
                (
                    opd_ipd.eq("")
                    | opd_ipd.eq("nan")
                ).sum()
            )

            st.caption(
                f"Missing/blank OPD/IPD records: "
                f"**{missing_opd_ipd:,}**"
            )

    # =========================================================
    # 11. DUPLICATE RECORD CHECK
    # =========================================================

    st.markdown("### 🔎 Duplicate Record Check")

    if total_records > 0:

        duplicate_count = int(
            df.duplicated(
                keep=False
            ).sum()
        )

        duplicate_rows = int(
            df.duplicated(
                keep="first"
            ).sum()
        )

        unique_rows = int(
            total_records
            - duplicate_rows
        )

        q1, q2, q3 = st.columns(3)

        with q1:
            st.metric(
                "Total Records",
                f"{total_records:,}",
            )

        with q2:
            st.metric(
                "Duplicate Rows",
                f"{duplicate_rows:,}",
            )

        with q3:
            st.metric(
                "Unique Rows",
                f"{unique_rows:,}",
            )

        if duplicate_rows > 0:

            st.warning(
                f"{duplicate_rows:,} duplicate row(s) detected "
                "based on complete-row comparison."
            )

            duplicate_preview = df[
                df.duplicated(
                    keep=False
                )
            ].head(100)

            with st.expander(
                "View Duplicate Record Preview"
            ):
                st.dataframe(
                    duplicate_preview,
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.success(
                "No complete-row duplicates detected "
                "in the filtered dataset."
            )

    # =========================================================
    # 12. YEAR / MONTH VALIDATION
    # =========================================================

    st.markdown("### 🗓️ Year & Month Validation")

    if "Year" in df.columns:

        year_values = _clean_values(
            df,
            "Year",
        )

        year_counts = (
            year_values[
                year_values.ne("")
                & year_values.ne("nan")
            ]
            .value_counts()
            .rename_axis("Year")
            .reset_index(
                name="Records"
            )
        )

        if not year_counts.empty:
            st.dataframe(
                year_counts,
                use_container_width=True,
                hide_index=True,
            )

    if "Month" in df.columns:

        month_values = _clean_values(
            df,
            "Month",
        )

        month_counts = (
            month_values[
                month_values.ne("")
                & month_values.ne("nan")
            ]
            .value_counts()
            .rename_axis("Month")
            .reset_index(
                name="Records"
            )
        )

        if not month_counts.empty:

            st.markdown("#### Month-wise Record Count")

            st.dataframe(
                month_counts,
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # 13. VALIDATION SUMMARY
    # =========================================================

    st.markdown("### 🧮 Validation Summary")

    summary_rows = []

    validation_items = [
        ("Reporting Date", "Reporting Date"),
        ("Disease", "Disease"),
        ("Facility", "Facility Name"),
        ("Ward", "Ward Name"),
        ("Gender", "Gender"),
        ("Age", "Age"),
        ("Age Group", "Age Group"),
        ("OPD/IPD", "OPD/IPD"),
    ]

    for label, column in validation_items:

        if column not in df.columns:

            summary_rows.append(
                {
                    "Validation Item": label,
                    "Valid / Available": 0,
                    "Missing / Invalid": total_records,
                    "Completeness (%)": 0.0,
                    "Status": "Attention Required",
                }
            )

            continue

        if column == "Reporting Date":

            values = pd.to_datetime(
                df[column],
                errors="coerce",
            )

            valid_count = int(
                values.notna().sum()
            )

        elif column == "Age":

            values = pd.to_numeric(
                df[column],
                errors="coerce",
            )

            valid_count = int(
                values.between(
                    0,
                    120,
                ).sum()
            )

        else:

            valid_count = _valid_count(
                df,
                column,
            )

        invalid_or_missing = (
            total_records
            - valid_count
        )

        completeness = _percentage(
            valid_count,
            total_records,
        )

        summary_rows.append(
            {
                "Validation Item": label,
                "Valid / Available": valid_count,
                "Missing / Invalid": invalid_or_missing,
                "Completeness (%)": completeness,
                "Status": _quality_status(
                    completeness
                ),
            }
        )

    validation_summary = pd.DataFrame(
        summary_rows
    )

    st.dataframe(
        validation_summary,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # 14. MANAGEMENT INTERPRETATION
    # =========================================================

    st.markdown("### 📝 Management Interpretation")

    overall_score = (
        validation_summary["Completeness (%)"]
        .mean()
        if not validation_summary.empty
        else 0
    )

    overall_score = round(
        float(overall_score),
        2,
    )

    if overall_score >= 95:

        st.success(
            f"Overall field completeness is "
            f"**{overall_score:.2f}%**. "
            "The selected dataset has high recorded-field completeness."
        )

    elif overall_score >= 85:

        st.warning(
            f"Overall field completeness is "
            f"**{overall_score:.2f}%**. "
            "Some fields require data-quality review."
        )

    else:

        st.error(
            f"Overall field completeness is "
            f"**{overall_score:.2f}%**. "
            "Data-quality improvement should be prioritised before "
            "using the affected fields for detailed interpretation."
        )

    if "Reporting Date" in df.columns:

        date_values = pd.to_datetime(
            df["Reporting Date"],
            errors="coerce",
        )

        if date_values.isna().any():

            st.warning(
                "Missing or invalid Reporting Date values were detected. "
                "Time-series analysis may therefore exclude some records."
            )

    if "Age" in df.columns:

        age_values = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

        invalid_age_count = int(
            (
                age_values.notna()
                & ~age_values.between(
                    0,
                    120,
                )
            ).sum()
        )

        if invalid_age_count > 0:

            st.warning(
                f"{invalid_age_count:,} age value(s) fall outside "
                "the expected 0–120 year range."
            )

    st.info(
        "Validation results apply to the currently filtered dataset. "
        "Change the Global Dashboard Filters to perform validation "
        "for a specific year, month, disease, facility, ward or "
        "other management segment."
    )
