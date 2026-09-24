import streamlit as st
import pandas as pd
import altair as alt

from chart_helpers import (
    render_bar_chart,
    render_line_chart,
    register_displayed_chart,
    reset_displayed_chart_registry,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _clean_series(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="object")

    return (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
    )


def _normalize_month(value):
    if pd.isna(value):
        return None

    text = str(value).strip()

    month_map = {
        "1": "Jan",
        "01": "Jan",
        "jan": "Jan",
        "january": "Jan",

        "2": "Feb",
        "02": "Feb",
        "feb": "Feb",
        "february": "Feb",

        "3": "Mar",
        "03": "Mar",
        "mar": "Mar",
        "march": "Mar",

        "4": "Apr",
        "04": "Apr",
        "apr": "Apr",
        "april": "Apr",

        "5": "May",
        "05": "May",
        "may": "May",

        "6": "Jun",
        "06": "Jun",
        "jun": "Jun",
        "june": "Jun",

        "7": "Jul",
        "07": "Jul",
        "jul": "Jul",
        "july": "Jul",

        "8": "Aug",
        "08": "Aug",
        "aug": "Aug",
        "august": "Aug",

        "9": "Sep",
        "09": "Sep",
        "sep": "Sep",
        "september": "Sep",

        "10": "Oct",
        "oct": "Oct",
        "october": "Oct",

        "11": "Nov",
        "nov": "Nov",
        "november": "Nov",

        "12": "Dec",
        "dec": "Dec",
        "december": "Dec",
    }

    return month_map.get(text.lower(), text[:3].title())


def _normalize_year(value):
    if pd.isna(value):
        return None

    try:
        return int(float(value))
    except Exception:
        return str(value).strip()


def _build_year_month_timeline(df):
    """
    Build chronological Year-Month summary.

    Returns:
        table_df
        x_order
    """

    if df is None or df.empty:
        return pd.DataFrame(), []

    month_col = None
    year_col = None

    for col in ["Month", "month", "Month Name", "Reporting Month"]:
        if col in df.columns:
            month_col = col
            break

    for col in ["Year", "year", "Reporting Year"]:
        if col in df.columns:
            year_col = col
            break

    # --------------------------------------------------------
    # Preferred route: Month + Year
    # --------------------------------------------------------

    if month_col and year_col:

        temp = df[[year_col, month_col]].copy()

        temp["Year"] = temp[year_col].apply(_normalize_year)
        temp["Month"] = temp[month_col].apply(_normalize_month)

        month_order = {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }

        temp["Month_No"] = temp["Month"].map(month_order)

        temp = temp.dropna(
            subset=["Year", "Month"]
        )

        if temp.empty:
            return pd.DataFrame(), []

        grouped = (
            temp
            .groupby(
                ["Year", "Month", "Month_No"],
                dropna=False
            )
            .size()
            .reset_index(name="Records")
        )

        grouped = grouped.sort_values(
            ["Year", "Month_No"]
        )

        grouped["Period"] = (
            grouped["Year"].astype(str)
            + " - "
            + grouped["Month"].astype(str)
        )

        return (
            grouped[
                [
                    "Year",
                    "Month",
                    "Month_No",
                    "Period",
                    "Records",
                ]
            ].reset_index(drop=True),
            grouped["Period"].tolist(),
        )

    # --------------------------------------------------------
    # Fallback: Reporting Date
    # --------------------------------------------------------

    if "Reporting Date" in df.columns:

        temp = df.copy()

        temp["Reporting Date"] = pd.to_datetime(
            temp["Reporting Date"],
            errors="coerce"
        )

        temp = temp.dropna(
            subset=["Reporting Date"]
        )

        if temp.empty:
            return pd.DataFrame(), []

        temp["Year"] = temp["Reporting Date"].dt.year
        temp["Month_No"] = temp["Reporting Date"].dt.month
        temp["Month"] = temp["Reporting Date"].dt.strftime("%b")

        grouped = (
            temp
            .groupby(
                ["Year", "Month_No", "Month"],
                dropna=False
            )
            .size()
            .reset_index(name="Records")
        )

        grouped = grouped.sort_values(
            ["Year", "Month_No"]
        )

        grouped["Period"] = (
            grouped["Year"].astype(str)
            + " - "
            + grouped["Month"].astype(str)
        )

        return (
            grouped[
                [
                    "Year",
                    "Month",
                    "Month_No",
                    "Period",
                    "Records",
                ]
            ].reset_index(drop=True),
            grouped["Period"].tolist(),
        )

    return pd.DataFrame(), []


def _apply_chronological_zwsp(value):
    """
    Keeps chronological ordering while allowing
    Altair labels to remain readable.
    """

    if value is None:
        return value

    return str(value)


def _sort_ward_dataframe(df):
    if df is None or df.empty:
        return df

    result = df.copy()

    if "Records" in result.columns:
        result = result.sort_values(
            "Records",
            ascending=False
        )

    return result.reset_index(drop=True)


def _register_table_chart(
    chart,
    title,
    filename,
    table_df,
):
    """
    Register chart + exact table data used for the chart.

    displayed_chart_export.py reads this registration and
    places the corresponding table underneath the chart
    in the PDF.
    """

    try:
        register_displayed_chart(
            chart,
            title=title,
            filename=filename,
            table_data=table_df,
        )
    except TypeError:
        # Backward compatibility with older chart_helpers.py
        register_displayed_chart(
            chart,
            title=title,
            filename=filename,
        )


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_charts(df):

    if df is None or df.empty:
        st.info(
            "No data available for Charts & Trends analysis."
        )
        return

    # Reset displayed chart registry for this page render.
    reset_displayed_chart_registry()

    st.markdown(
        "## Charts & Trends"
    )

    st.caption(
        "Interactive programme trends, disease burden, "
        "laboratory/pathogen analysis, facility and ward "
        "distribution."
    )

    # ========================================================
    # 1. MONTH-WISE PROGRAMME TREND
    # ========================================================

    st.markdown(
        "### 1. Month-wise Programme Trend"
    )

    timeline_df, timeline_order = (
        _build_year_month_timeline(df)
    )

    if not timeline_df.empty:

        chart_series = pd.Series(
            timeline_df["Records"].values,
            index=timeline_df["Period"].values,
        )

        render_line_chart(
            chart_series,
            use_container_width=True,
            export_title="Month-wise Programme Trend",
            export_filename="month_wise_programme_trend",
        )

        _register_table_chart(
            None,
            "Month-wise Programme Trend",
            "month_wise_programme_trend",
            timeline_df[
                [
                    "Year",
                    "Month",
                    "Period",
                    "Records",
                ]
            ],
        )

    else:
        st.info(
            "Month-wise programme trend data is not available."
        )

    st.divider()

    # ========================================================
    # 2. MONTHLY DISEASE COMPARISON
    # ========================================================

    st.markdown(
        "### 2. Monthly Disease Comparison"
    )

    disease_col = None

    for col in [
        "Disease",
        "Disease Name",
        "Disease / Syndrome",
    ]:
        if col in df.columns:
            disease_col = col
            break

    if disease_col:

        disease_values = (
            _clean_series(df, disease_col)
            .value_counts()
            .index
            .tolist()
        )

        if disease_values:

            st.markdown(
                "#### Select Diseases"
            )

            # ------------------------------------------------
            # Compact disease selection
            # ------------------------------------------------

            selected_diseases = []

            selection_columns = st.columns(4)

            for idx, disease in enumerate(
                disease_values
            ):

                col_idx = idx % 4

                with selection_columns[col_idx]:

                    selected = st.checkbox(
                        str(disease),
                        value=True,
                        key=(
                            "phase3_monthly_disease_"
                            + str(idx)
                        ),
                    )

                    if selected:
                        selected_diseases.append(
                            disease
                        )

            # ------------------------------------------------
            # Data labels toggle
            # ------------------------------------------------

            show_labels = st.checkbox(
                "Show data labels",
                value=st.session_state.get(
                    "show_data_labels",
                    False
                ),
                key="phase3_monthly_disease_labels",
            )

            # ------------------------------------------------
            # Month detection
            # ------------------------------------------------

            month_col = None

            for col in [
                "Month",
                "month",
                "Month Name",
                "Reporting Month",
            ]:
                if col in df.columns:
                    month_col = col
                    break

            year_col = None

            for col in [
                "Year",
                "year",
                "Reporting Year",
            ]:
                if col in df.columns:
                    year_col = col
                    break

            # ------------------------------------------------
            # Build comparison table
            # ------------------------------------------------

            if selected_diseases:

                temp = df[
                    df[disease_col]
                    .astype(str)
                    .isin(
                        [
                            str(x)
                            for x in selected_diseases
                        ]
                    )
                ].copy()

                if (
                    month_col
                    and year_col
                ):

                    temp["__Year"] = temp[
                        year_col
                    ].apply(
                        _normalize_year
                    )

                    temp["__Month"] = temp[
                        month_col
                    ].apply(
                        _normalize_month
                    )

                    month_order = {
                        "Jan": 1,
                        "Feb": 2,
                        "Mar": 3,
                        "Apr": 4,
                        "May": 5,
                        "Jun": 6,
                        "Jul": 7,
                        "Aug": 8,
                        "Sep": 9,
                        "Oct": 10,
                        "Nov": 11,
                        "Dec": 12,
                    }

                    temp["__Month_No"] = (
                        temp["__Month"]
                        .map(month_order)
                    )

                    comparison_df = (
                        temp
                        .dropna(
                            subset=[
                                "__Year",
                                "__Month",
                            ]
                        )
                        .groupby(
                            [
                                "__Year",
                                "__Month",
                                "__Month_No",
                                disease_col,
                            ],
                            dropna=False,
                        )
                        .size()
                        .reset_index(
                            name="Records"
                        )
                    )

                    comparison_df = (
                        comparison_df
                        .sort_values(
                            [
                                "__Year",
                                "__Month_No",
                                disease_col,
                            ]
                        )
                    )

                    comparison_df[
                        "Period"
                    ] = (
                        comparison_df[
                            "__Year"
                        ].astype(str)
                        + " - "
                        + comparison_df[
                            "__Month"
                        ].astype(str)
                    )

                    # ----------------------------------------
                    # Altair chart
                    # ----------------------------------------

                    base = alt.Chart(
                        comparison_df
                    ).encode(
                        x=alt.X(
                            "Period:N",
                            sort=timeline_order
                            if timeline_order
                            else alt.SortField(
                                "__Month_No",
                                order="ascending",
                            ),
                            title="Reporting Month",
                            axis=alt.Axis(
                                labelAngle=-45
                            ),
                        ),
                        y=alt.Y(
                            "Records:Q",
                            title="Number of Records",
                        ),
                        color=alt.Color(
                            f"{disease_col}:N",
                            title="Disease",
                            legend=alt.Legend(
                                orient="bottom",

                                # IMPORTANT:
                                # Compact bottom legend.
                                columns=10,

                                direction="horizontal",

                                labelLimit=180,

                                columnPadding=8,

                                rowPadding=3,

                                symbolSize=90,

                                titlePadding=8,

                                labelFontSize=11,

                                titleFontSize=12,
                            ),
                        ),
                    )

                    bars = base.mark_line(
                        point=True
                    )

                    final_chart = bars

                    if show_labels:

                        labels = base.mark_text(
                            dy=-8,
                            fontSize=10,
                        ).encode(
                            text="Records:Q"
                        )

                        final_chart = (
                            bars + labels
                        )

                    # ----------------------------------------
                    # Larger chart area
                    # ----------------------------------------

                    final_chart = (
                        final_chart
                        .properties(
                            height=560,
                        )
                    )

                    # ----------------------------------------
                    # Register chart + table
                    # ----------------------------------------

                    _register_table_chart(
                        final_chart,
                        "Monthly Disease Comparison",
                        "monthly_disease_comparison",
                        comparison_df[
                            [
                                "__Year",
                                "__Month",
                                "Period",
                                disease_col,
                                "Records",
                            ]
                        ].rename(
                            columns={
                                "__Year": "Year",
                                "__Month": "Month",
                                disease_col: "Disease",
                            }
                        ),
                    )

                    st.altair_chart(
                        final_chart,
                        use_container_width=True,
                    )

                else:

                    # ----------------------------------------
                    # Month unavailable
                    # ----------------------------------------

                    monthly_df = (
                        temp
                        .groupby(
                            disease_col
                        )
                        .size()
                        .reset_index(
                            name="Records"
                        )
                        .sort_values(
                            "Records",
                            ascending=False,
                        )
                    )

                    chart = alt.Chart(
                        monthly_df
                    ).mark_bar().encode(
                        x=alt.X(
                            f"{disease_col}:N",
                            sort="-y",
                            title="Disease",
                            axis=alt.Axis(
                                labelAngle=-45
                            ),
                        ),
                        y=alt.Y(
                            "Records:Q",
                            title="Number of Records",
                        ),
                        color=alt.Color(
                            f"{disease_col}:N",
                            title="Disease",
                            legend=alt.Legend(
                                orient="bottom",
                                columns=10,
                                direction="horizontal",
                                labelLimit=180,
                                columnPadding=8,
                                rowPadding=3,
                                symbolSize=90,
                                titlePadding=8,
                                labelFontSize=11,
                                titleFontSize=12,
                            ),
                        ),
                    )

                    chart = chart.properties(
                        height=560
                    )

                    _register_table_chart(
                        chart,
                        "Monthly Disease Comparison",
                        "monthly_disease_comparison",
                        monthly_df.rename(
                            columns={
                                disease_col: "Disease"
                            }
                        ),
                    )

                    st.altair_chart(
                        chart,
                        use_container_width=True,
                    )

            else:

                st.info(
                    "Please select at least one disease."
                )

    else:

        st.info(
            "Disease column is not available."
        )

    st.divider()

    # ========================================================
    # 3. DISEASE-WISE BURDEN
    # ========================================================

    st.markdown(
        "### 3. Disease-wise Burden"
    )

    if disease_col:

        disease_burden = (
            _clean_series(
                df,
                disease_col
            )
            .value_counts()
            .rename_axis("Disease")
            .reset_index(
                name="Records"
            )
        )

        if not disease_burden.empty:

            chart_series = pd.Series(
                disease_burden["Records"].values,
                index=disease_burden[
                    "Disease"
                ].values,
            )

            render_bar_chart(
                chart_series,
                use_container_width=True,
                export_title="Disease-wise Burden",
                export_filename="disease_wise_burden",
            )

            st.dataframe(
                disease_burden,
                use_container_width=True,
                hide_index=True,
            )

            # Register table explicitly
            _register_table_chart(
                None,
                "Disease-wise Burden",
                "disease_wise_burden",
                disease_burden,
            )

        else:
            st.info(
                "Disease-wise burden data is not available."
            )

    else:

        st.info(
            "Disease column is not available."
        )

    st.divider()

    # ========================================================
    # 4. TEST PERFORMED / PATHOGEN NAME-WISE ANALYSIS
    # ========================================================

    st.markdown(
        "### 4. Test Performed / Pathogen Name-wise Analysis"
    )

    pathogen_col = None

    possible_pathogen_columns = [
        "Test Performed Pathogen Name",
        "Pathogen Name",
        "Test Performed Pathogen",
        "Pathogen",
    ]

    for col in possible_pathogen_columns:

        if col in df.columns:

            pathogen_col = col
            break

    # --------------------------------------------------------
    # Fallback combined column
    # --------------------------------------------------------

    if pathogen_col is None:

        test_col = None

        for col in [
            "Test Performed",
            "Test",
            "Laboratory Test",
        ]:

            if col in df.columns:

                test_col = col
                break

        pathogen_name_col = None

        for col in [
            "Pathogen Name",
            "Pathogen",
        ]:

            if col in df.columns:

                pathogen_name_col = col
                break

        if (
            test_col
            and pathogen_name_col
        ):

            temp_pathogen = df.copy()

            temp_pathogen[
                "__Test_Pathogen"
            ] = (
                temp_pathogen[
                    test_col
                ].fillna("")
                .astype(str)
                .str.strip()
                + " | "
                + temp_pathogen[
                    pathogen_name_col
                ].fillna("")
                .astype(str)
                .str.strip()
            )

            temp_pathogen[
                "__Test_Pathogen"
            ] = (
                temp_pathogen[
                    "__Test_Pathogen"
                ]
                .str.strip(" |")
            )

            pathogen_table = (
                temp_pathogen[
                    "__Test_Pathogen"
                ]
                .replace(
                    "",
                    pd.NA
                )
                .dropna()
                .value_counts()
                .rename_axis(
                    "Test / Pathogen"
                )
                .reset_index(
                    name="Records"
                )
            )

        else:

            pathogen_table = pd.DataFrame()

    else:

        pathogen_table = (
            _clean_series(
                df,
                pathogen_col
            )
            .value_counts()
            .rename_axis(
                "Test / Pathogen"
            )
            .reset_index(
                name="Records"
            )
        )

    if not pathogen_table.empty:

        chart_series = pd.Series(
            pathogen_table["Records"].values,
            index=pathogen_table[
                "Test / Pathogen"
            ].values,
        )

        render_bar_chart(
            chart_series,
            use_container_width=True,
            export_title=(
                "Test Performed / Pathogen "
                "Name-wise Analysis"
            ),
            export_filename=(
                "test_performed_pathogen_analysis"
            ),
        )

        st.dataframe(
            pathogen_table,
            use_container_width=True,
            hide_index=True,
        )

        _register_table_chart(
            None,
            "Test Performed / Pathogen Name-wise Analysis",
            "test_performed_pathogen_analysis",
            pathogen_table,
        )

    else:

        st.info(
            "Test Performed / Pathogen Name-wise data "
            "is not available."
        )

    st.divider()

    # ========================================================
    # 5. FACILITY-WISE BURDEN
    # ========================================================

    st.markdown(
        "### 5. Facility-wise Burden"
    )

    facility_col = None

    for col in [
        "Facility Name",
        "Facility",
        "Health Facility",
        "Facility_Name",
    ]:

        if col in df.columns:

            facility_col = col
            break

    if facility_col:

        facility_burden = (
            _clean_series(
                df,
                facility_col
            )
            .value_counts()
            .rename_axis(
                "Facility"
            )
            .reset_index(
                name="Records"
            )
        )

        if not facility_burden.empty:

            chart_series = pd.Series(
                facility_burden["Records"].values,
                index=facility_burden[
                    "Facility"
                ].values,
            )

            render_bar_chart(
                chart_series,
                use_container_width=True,
                export_title="Facility-wise Burden",
                export_filename="facility_wise_burden",
            )

            st.dataframe(
                facility_burden,
                use_container_width=True,
                hide_index=True,
            )

            _register_table_chart(
                None,
                "Facility-wise Burden",
                "facility_wise_burden",
                facility_burden,
            )

        else:

            st.info(
                "Facility-wise burden data is not available."
            )

    else:

        st.info(
            "Facility column is not available."
        )

    st.divider()

    # ========================================================
    # 6. WARD-WISE BURDEN
    # ========================================================

    st.markdown(
        "### 6. Ward-wise Burden"
    )

    ward_col = None

    for col in [
        "Ward",
        "Ward Name",
        "Ward_Name",
        "BMC Ward",
    ]:

        if col in df.columns:

            ward_col = col
            break

    if ward_col:

        ward_burden = (
            _clean_series(
                df,
                ward_col
            )
            .value_counts()
            .rename_axis(
                "Ward"
            )
            .reset_index(
                name="Records"
            )
        )

        ward_burden = _sort_ward_dataframe(
            ward_burden
        )

        if not ward_burden.empty:

            chart_series = pd.Series(
                ward_burden["Records"].values,
                index=ward_burden[
                    "Ward"
                ].values,
            )

            render_bar_chart(
                chart_series,
                use_container_width=True,
                export_title="Ward-wise Burden",
                export_filename="ward_wise_burden",
            )

            st.dataframe(
                ward_burden,
                use_container_width=True,
                hide_index=True,
            )

            _register_table_chart(
                None,
                "Ward-wise Burden",
                "ward_wise_burden",
                ward_burden,
            )

        else:

            st.info(
                "Ward-wise burden data is not available."
            )

    else:

        st.info(
            "Ward column is not available."
        )

    st.divider()

    # ========================================================
    # 7. OPD / IPD DISTRIBUTION
    # ========================================================

    st.markdown(
        "### 7. OPD / IPD Distribution"
    )

    opd_ipd_col = None

    for col in [
        "OPD / IPD",
        "OPD/IPD",
        "OPD_IPD",
        "OPD IPD",
        "OPD or IPD",
    ]:

        if col in df.columns:

            opd_ipd_col = col
            break

    if opd_ipd_col:

        opd_ipd_table = (
            _clean_series(
                df,
                opd_ipd_col
            )
            .value_counts()
            .rename_axis(
                "OPD / IPD"
            )
            .reset_index(
                name="Records"
            )
        )

        if not opd_ipd_table.empty:

            chart_series = pd.Series(
                opd_ipd_table["Records"].values,
                index=opd_ipd_table[
                    "OPD / IPD"
                ].values,
            )

            render_bar_chart(
                chart_series,
                use_container_width=True,
                export_title="OPD / IPD Distribution",
                export_filename="opd_ipd_distribution",
            )

            st.dataframe(
                opd_ipd_table,
                use_container_width=True,
                hide_index=True,
            )

            _register_table_chart(
                None,
                "OPD / IPD Distribution",
                "opd_ipd_distribution",
                opd_ipd_table,
            )

        else:

            st.info(
                "OPD / IPD data is not available."
            )

    else:

        st.info(
            "OPD / IPD column is not available."
        )

    st.divider()

    # ========================================================
    # 8. REPORTING DATE TREND
    # ========================================================

    st.markdown(
        "### 8. Reporting Date Trend"
    )

    if "Reporting Date" in df.columns:

        reporting_dates = pd.to_datetime(
            df["Reporting Date"],
            errors="coerce"
        )

        reporting_dates = (
            reporting_dates
            .dropna()
            .dt.date
            .value_counts()
            .sort_index()
        )

        if not reporting_dates.empty:

            reporting_table = (
                reporting_dates
                .rename_axis(
                    "Reporting Date"
                )
                .reset_index(
                    name="Records"
                )
            )

            reporting_table[
                "Reporting Date"
            ] = pd.to_datetime(
                reporting_table[
                    "Reporting Date"
                ]
            ).dt.strftime(
                "%Y-%m-%d"
            )

            chart_series = pd.Series(
                reporting_table["Records"].values,
                index=reporting_table[
                    "Reporting Date"
                ].values,
            )

            render_line_chart(
                chart_series,
                use_container_width=True,
                export_title="Reporting Date Trend",
                export_filename="reporting_date_trend",
            )

            st.dataframe(
                reporting_table,
                use_container_width=True,
                hide_index=True,
            )

            _register_table_chart(
                None,
                "Reporting Date Trend",
                "reporting_date_trend",
                reporting_table,
            )

        else:

            st.info(
                "Reporting Date trend data is not available."
            )

    else:

        st.info(
            "Reporting Date column is not available."
        )

    st.divider()

    # ========================================================
    # 9. TREND SUMMARY
    # ========================================================

    st.markdown(
        "### 9. Trend Summary"
    )

    summary_items = []

    # --------------------------------------------------------
    # Total records
    # --------------------------------------------------------

    summary_items.append(
        {
            "Metric": "Total Records",
            "Value": len(df),
        }
    )

    # --------------------------------------------------------
    # Diseases
    # --------------------------------------------------------

    if disease_col:

        summary_items.append(
            {
                "Metric": "Unique Diseases",
                "Value": int(
                    _clean_series(
                        df,
                        disease_col
                    ).nunique()
                ),
            }
        )

    # --------------------------------------------------------
    # Facilities
    # --------------------------------------------------------

    if facility_col:

        summary_items.append(
            {
                "Metric": "Unique Facilities",
                "Value": int(
                    _clean_series(
                        df,
                        facility_col
                    ).nunique()
                ),
            }
        )

    # --------------------------------------------------------
    # Wards
    # --------------------------------------------------------

    if ward_col:

        summary_items.append(
            {
                "Metric": "Unique Wards",
                "Value": int(
                    _clean_series(
                        df,
                        ward_col
                    ).nunique()
                ),
            }
        )

    # --------------------------------------------------------
    # Reporting period
    # --------------------------------------------------------

    if "Reporting Date" in df.columns:

        dates = pd.to_datetime(
            df["Reporting Date"],
            errors="coerce"
        ).dropna()

        if not dates.empty:

            summary_items.append(
                {
                    "Metric": "Reporting Period",
                    "Value": (
                        dates.min().strftime(
                            "%d-%b-%Y"
                        )
                        + " to "
                        + dates.max().strftime(
                            "%d-%b-%Y"
                        )
                    ),
                }
            )

    summary_df = pd.DataFrame(
        summary_items
    )

    if not summary_df.empty:

        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
        )

        _register_table_chart(
            None,
            "Trend Summary",
            "trend_summary",
            summary_df,
        )

    st.caption(
        "All charts and tables are based on the currently "
        "selected global filters."
    )
