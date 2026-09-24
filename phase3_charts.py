import re

import pandas as pd
import streamlit as st
import altair as alt

from chart_helpers import (
    render_bar_chart,
    render_line_chart,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _clean_series(
    df,
    column,
):

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):

        return pd.Series(
            dtype="object"
        )

    return (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )


# ============================================================
# MONTH HELPERS
# ============================================================

CALENDAR_MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


MONTH_NUMBER_MAP = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def _normalize_month(value):

    if pd.isna(value):
        return None

    text = str(value).strip().lower()

    if text in MONTH_NUMBER_MAP:

        number = MONTH_NUMBER_MAP[text]

        return CALENDAR_MONTHS[
            number - 1
        ]

    # Numeric month
    try:

        number = int(float(text))

        if 1 <= number <= 12:

            return CALENDAR_MONTHS[
                number - 1
            ]

    except Exception:
        pass

    return None


def _normalize_year(value):

    if pd.isna(value):
        return None

    text = str(value).strip()

    match = re.search(
        r"(19|20)\d{2}",
        text,
    )

    if match:
        return int(
            match.group(0)
        )

    return None


# ============================================================
# YEAR-MONTH TIMELINE
# ============================================================

def _build_year_month_timeline(
    df,
    month_col="Month",
    year_col=None,
):

    if (
        df is None
        or df.empty
        or month_col not in df.columns
        or year_col is None
        or year_col not in df.columns
    ):

        return pd.DataFrame()

    temp = df[
        [
            month_col,
            year_col,
        ]
    ].copy()

    temp["Month_Normalized"] = (
        temp[month_col]
        .apply(
            _normalize_month
        )
    )

    temp["Year_Normalized"] = (
        temp[year_col]
        .apply(
            _normalize_year
        )
    )

    temp = temp.dropna(
        subset=[
            "Month_Normalized",
            "Year_Normalized",
        ]
    )

    if temp.empty:
        return pd.DataFrame()

    temp["Month_Number"] = (
        temp["Month_Normalized"]
        .map(
            {
                month: index + 1
                for index, month
                in enumerate(
                    CALENDAR_MONTHS
                )
            }
        )
    )

    grouped = (
        temp.groupby(
            [
                "Year_Normalized",
                "Month_Number",
                "Month_Normalized",
            ],
            dropna=False,
        )
        .size()
        .reset_index(
            name="Records"
        )
    )

    grouped = grouped.sort_values(
        [
            "Year_Normalized",
            "Month_Number",
        ]
    )

    grouped["Month-Year"] = (
        grouped["Month_Normalized"]
        + " "
        + grouped[
            "Year_Normalized"
        ].astype(int).astype(str)
    )

    return grouped[
        [
            "Year_Normalized",
            "Month_Number",
            "Month_Normalized",
            "Month-Year",
            "Records",
        ]
    ].reset_index(
        drop=True
    )


# ============================================================
# CHRONOLOGICAL DISPLAY LABEL
# ============================================================

def _apply_chronological_zwsp(
    df,
    label_col="Month-Year",
):

    result = df.copy()

    if label_col not in result.columns:
        return result

    labels = []

    for index, value in enumerate(
        result[label_col].astype(str)
    ):

        labels.append(
            ("\u200B" * (index + 1))
            + value
        )

    result[
        "_Chart_Label"
    ] = labels

    return result


# ============================================================
# WARD SORT
# ============================================================

def _sort_ward_dataframe(
    df,
    ward_column="Ward Name",
):

    if (
        df is None
        or df.empty
        or ward_column not in df.columns
    ):

        return df

    result = df.copy()

    result["_Ward_Sort"] = (
        result[ward_column]
        .astype(str)
        .str.extract(
            r"(\d+)",
            expand=False,
        )
    )

    result["_Ward_Number"] = pd.to_numeric(
        result["_Ward_Sort"],
        errors="coerce",
    )

    result = result.sort_values(
        [
            "_Ward_Number",
            ward_column,
        ],
        na_position="last",
    )

    result = result.drop(
        columns=[
            "_Ward_Sort",
            "_Ward_Number",
        ],
        errors="ignore",
    )

    return result.reset_index(
        drop=True
    )


# ============================================================
# MAIN RENDER
# ============================================================

def render_charts(df):

    if (
        df is None
        or df.empty
    ):

        st.warning(
            "No data available for Charts & Trends."
        )

        return

    st.header(
        "Charts & Trends"
    )

    # ========================================================
    # 1. MONTH-WISE PROGRAMME TREND
    # ========================================================

    st.subheader(
        "1. Month-wise Programme Trend"
    )

    if "Month" in df.columns:

        year_candidates = [
            "Year",
            "Reporting Year",
            "Year of Reporting",
        ]

        year_col = None

        for candidate in year_candidates:

            if candidate in df.columns:

                year_col = candidate
                break

        # ----------------------------------------------------
        # Year + Month analysis
        # ----------------------------------------------------

        if year_col is not None:

            timeline = (
                _build_year_month_timeline(
                    df,
                    month_col="Month",
                    year_col=year_col,
                )
            )

            if not timeline.empty:

                chart_data = (
                    _apply_chronological_zwsp(
                        timeline,
                        "Month-Year",
                    )
                )

                chart_series = (
                    chart_data[
                        [
                            "_Chart_Label",
                            "Records",
                        ]
                    ]
                )

                display_month_counts = (
                    timeline[
                        [
                            "Month-Year",
                            "Records",
                        ]
                    ]
                    .copy()
                )

                render_bar_chart(
                    chart_series,
                    title=(
                        "Month-wise Programme Trend"
                    ),
                    x_title="Month-Year",
                    y_title="Records",
                    export_title=(
                        "Month-wise Programme Trend"
                    ),
                    export_filename=(
                        "Month-wise_Programme_Trend"
                    ),
                    export_table=(
                        display_month_counts
                    ),
                )

                st.dataframe(
                    display_month_counts,
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                # ------------------------------------------------
                # Month-only fallback
                # ------------------------------------------------

                normalized_months = (
                    df["Month"]
                    .apply(
                        _normalize_month
                    )
                    .dropna()
                )

                month_counts = (
                    normalized_months
                    .value_counts()
                    .reindex(
                        CALENDAR_MONTHS,
                        fill_value=0,
                    )
                    .reset_index()
                )

                month_counts.columns = [
                    "Month",
                    "Records",
                ]

                chart_data = (
                    _apply_chronological_zwsp(
                        month_counts,
                        "Month",
                    )
                )

                chart_series = (
                    chart_data[
                        [
                            "_Chart_Label",
                            "Records",
                        ]
                    ]
                )

                render_bar_chart(
                    chart_series,
                    title=(
                        "Month-wise Programme Trend"
                    ),
                    x_title="Month",
                    y_title="Records",
                    export_title=(
                        "Month-wise Programme Trend"
                    ),
                    export_filename=(
                        "Month-wise_Programme_Trend"
                    ),
                    export_table=(
                        month_counts
                    ),
                )

                st.dataframe(
                    month_counts,
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            normalized_months = (
                df["Month"]
                .apply(
                    _normalize_month
                )
                .dropna()
            )

            month_counts = (
                normalized_months
                .value_counts()
                .reindex(
                    CALENDAR_MONTHS,
                    fill_value=0,
                )
                .reset_index()
            )

            month_counts.columns = [
                "Month",
                "Records",
            ]

            chart_data = (
                _apply_chronological_zwsp(
                    month_counts,
                    "Month",
                )
            )

            chart_series = (
                chart_data[
                    [
                        "_Chart_Label",
                        "Records",
                    ]
                ]
            )

            render_bar_chart(
                chart_series,
                title=(
                    "Month-wise Programme Trend"
                ),
                x_title="Month",
                y_title="Records",
                export_title=(
                    "Month-wise Programme Trend"
                ),
                export_filename=(
                    "Month-wise_Programme_Trend"
                ),
                export_table=(
                    month_counts
                ),
            )

            st.dataframe(
                month_counts,
                use_container_width=True,
                hide_index=True,
            )

    else:

        st.info(
            "Month column is not available."
        )

    # ========================================================
    # 2. MONTHLY DISEASE COMPARISON
    # ========================================================

    st.subheader(
        "2. Monthly Disease Comparison"
    )

    if (
        "Month" in df.columns
        and "Disease" in df.columns
    ):

        year_col = None

        for candidate in [
            "Year",
            "Reporting Year",
            "Year of Reporting",
        ]:

            if candidate in df.columns:

                year_col = candidate
                break

        disease_values = (
            _clean_series(
                df,
                "Disease",
            )
            .unique()
            .tolist()
        )

        disease_values = sorted(
            disease_values
        )

        if disease_values:

            st.caption(
                "Select diseases to display in the comparison chart."
            )

            selected_diseases = []

            checkbox_columns = st.columns(
                4
            )

            for index, disease in enumerate(
                disease_values
            ):

                with checkbox_columns[
                    index % 4
                ]:

                    selected = st.checkbox(
                        disease,
                        value=True,
                        key=(
                            "phase3_disease_"
                            + str(index)
                            + "_"
                            + re.sub(
                                r"\W+",
                                "_",
                                disease,
                            )
                        ),
                    )

                    if selected:

                        selected_diseases.append(
                            disease
                        )

            if not selected_diseases:

                st.info(
                    "Please select at least one disease."
                )

            else:

                temp = df.copy()

                temp[
                    "_Month_Normalized"
                ] = (
                    temp["Month"]
                    .apply(
                        _normalize_month
                    )
                )

                temp = temp[
                    temp[
                        "_Month_Normalized"
                    ].notna()
                ]

                temp = temp[
                    temp[
                        "Disease"
                    ].astype(str).str.strip()
                    .isin(
                        selected_diseases
                    )
                ]

                # ------------------------------------------------
                # Year + Month
                # ------------------------------------------------

                if year_col is not None:

                    temp[
                        "_Year_Normalized"
                    ] = (
                        temp[year_col]
                        .apply(
                            _normalize_year
                        )
                    )

                    temp = temp[
                        temp[
                            "_Year_Normalized"
                        ].notna()
                    ]

                    if not temp.empty:

                        temp[
                            "_Month_Number"
                        ] = (
                            temp[
                                "_Month_Normalized"
                            ].map(
                                {
                                    month: index + 1
                                    for index, month
                                    in enumerate(
                                        CALENDAR_MONTHS
                                    )
                                }
                            )
                        )

                        grouped = (
                            temp.groupby(
                                [
                                    "_Year_Normalized",
                                    "_Month_Number",
                                    "_Month_Normalized",
                                    "Disease",
                                ],
                                dropna=False,
                            )
                            .size()
                            .reset_index(
                                name="Records"
                            )
                        )

                        years = sorted(
                            grouped[
                                "_Year_Normalized"
                            ].dropna().unique()
                        )

                        full_rows = []

                        for year in years:

                            for month_number, month_name in enumerate(
                                CALENDAR_MONTHS,
                                start=1,
                            ):

                                for disease in selected_diseases:

                                    full_rows.append(
                                        {
                                            "Year": int(year),
                                            "Month_Number": month_number,
                                            "Month": month_name,
                                            "Disease": disease,
                                        }
                                    )

                        full_grid = pd.DataFrame(
                            full_rows
                        )

                        chart_disease_month = (
                            full_grid.merge(
                                grouped[
                                    [
                                        "_Year_Normalized",
                                        "_Month_Number",
                                        "_Month_Normalized",
                                        "Disease",
                                        "Records",
                                    ]
                                ],
                                left_on=[
                                    "Year",
                                    "Month_Number",
                                    "Month",
                                    "Disease",
                                ],
                                right_on=[
                                    "_Year_Normalized",
                                    "_Month_Number",
                                    "_Month_Normalized",
                                    "Disease",
                                ],
                                how="left",
                            )
                        )

                        chart_disease_month[
                            "Records"
                        ] = (
                            chart_disease_month[
                                "Records"
                            ]
                            .fillna(0)
                            .astype(int)
                        )

                        chart_disease_month[
                            "Month-Year"
                        ] = (
                            chart_disease_month[
                                "Month"
                            ]
                            + " "
                            + chart_disease_month[
                                "Year"
                            ].astype(str)
                        )

                        chart_disease_month[
                            "_Timeline_Order"
                        ] = (
                            chart_disease_month[
                                "Year"
                            ]
                            * 100
                            + chart_disease_month[
                                "Month_Number"
                            ]
                        )

                        chart_disease_month = (
                            chart_disease_month
                            .sort_values(
                                [
                                    "_Timeline_Order",
                                    "Disease",
                                ]
                            )
                        )

                        # ----------------------------------------
                        # Direct Altair chart
                        # ----------------------------------------

                        chart = (
                            alt.Chart(
                                chart_disease_month
                            )
                            .mark_line(
                                point=True,
                            )
                            .encode(
                                x=alt.X(
                                    "Month-Year:N",
                                    sort=alt.EncodingSortField(
                                        field="_Timeline_Order",
                                        order="ascending",
                                    ),
                                    title="Month-Year",
                                    axis=alt.Axis(
                                        labelAngle=-45,
                                    ),
                                ),
                                y=alt.Y(
                                    "Records:Q",
                                    title="Records",
                                ),
                                color=alt.Color(
                                    "Disease:N",
                                    legend=alt.Legend(
                                        orient="bottom",
                                        title="Disease",
                                        labelLimit=0,
                                        columns=10,
                                        symbolSize=90,
                                        labelFontSize=10,
                                        titleFontSize=11,
                                        rowPadding=4,
                                    ),
                                ),
                                tooltip=[
                                    alt.Tooltip(
                                        "Month-Year:N",
                                        title="Month-Year",
                                    ),
                                    alt.Tooltip(
                                        "Disease:N",
                                        title="Disease",
                                    ),
                                    alt.Tooltip(
                                        "Records:Q",
                                        title="Records",
                                        format=",",
                                    ),
                                ],
                            )
                            .properties(
                                height=540,
                                title=alt.TitleParams(
                                    text=(
                                        "Monthly Disease Comparison"
                                    ),
                                    fontSize=18,
                                    anchor="start",
                                ),
                            )
                            .configure_axis(
                                labelFontSize=11,
                                titleFontSize=12,
                            )
                            .configure_title(
                                fontSize=18
                            )
                        )

                        if st.session_state.get(
                            "show_data_labels",
                            False,
                        ):

                            labels = (
                                alt.Chart(
                                    chart_disease_month
                                )
                                .mark_text(
                                    dy=-8,
                                    fontSize=8,
                                )
                                .encode(
                                    x=alt.X(
                                        "Month-Year:N",
                                        sort=alt.EncodingSortField(
                                            field="_Timeline_Order",
                                            order="ascending",
                                        ),
                                    ),
                                    y=alt.Y(
                                        "Records:Q"
                                    ),
                                    color=alt.Color(
                                        "Disease:N",
                                        legend=None,
                                    ),
                                    text=alt.Text(
                                        "Records:Q",
                                        format=",",
                                    ),
                                )
                            )

                            chart = (
                                chart
                                + labels
                            )

                        st.altair_chart(
                            chart,
                            use_container_width=True,
                        )

                        # Register exact table
                        try:

                            from chart_helpers import (
                                register_displayed_chart,
                            )

                            export_table = (
                                chart_disease_month[
                                    [
                                        "Month-Year",
                                        "Disease",
                                        "Records",
                                    ]
                                ]
                                .copy()
                            )

                            register_displayed_chart(
                                chart=chart,
                                title=(
                                    "Monthly Disease Comparison"
                                ),
                                filename=(
                                    "Monthly_Disease_Comparison"
                                ),
                                table_data=export_table,
                            )

                        except Exception:
                            pass

                # ------------------------------------------------
                # Month-only fallback
                # ------------------------------------------------

                else:

                    grouped = (
                        temp.groupby(
                            [
                                "_Month_Normalized",
                                "Disease",
                            ]
                        )
                        .size()
                        .reset_index(
                            name="Records"
                        )
                    )

                    full_rows = []

                    for month_number, month_name in enumerate(
                        CALENDAR_MONTHS,
                        start=1,
                    ):

                        for disease in selected_diseases:

                            full_rows.append(
                                {
                                    "Month": month_name,
                                    "Month_Number": month_number,
                                    "Disease": disease,
                                }
                            )

                    full_grid = pd.DataFrame(
                        full_rows
                    )

                    chart_disease_month = (
                        full_grid.merge(
                            grouped,
                            left_on=[
                                "Month",
                                "Disease",
                            ],
                            right_on=[
                                "_Month_Normalized",
                                "Disease",
                            ],
                            how="left",
                        )
                    )

                    chart_disease_month[
                        "Records"
                    ] = (
                        chart_disease_month[
                            "Records"
                        ]
                        .fillna(0)
                        .astype(int)
                    )

                    chart_disease_month = (
                        chart_disease_month
                        .sort_values(
                            "Month_Number"
                        )
                    )

                    chart = (
                        alt.Chart(
                            chart_disease_month
                        )
                        .mark_line(
                            point=True,
                        )
                        .encode(
                            x=alt.X(
                                "Month:N",
                                sort=CALENDAR_MONTHS,
                                title="Month",
                                axis=alt.Axis(
                                    labelAngle=-45,
                                ),
                            ),
                            y=alt.Y(
                                "Records:Q",
                                title="Records",
                            ),
                            color=alt.Color(
                                "Disease:N",
                                legend=alt.Legend(
                                    orient="bottom",
                                    title="Disease",
                                    labelLimit=0,
                                    columns=10,
                                    symbolSize=90,
                                    labelFontSize=10,
                                    titleFontSize=11,
                                    rowPadding=4,
                                ),
                            ),
                            tooltip=[
                                alt.Tooltip(
                                    "Month:N",
                                    title="Month",
                                ),
                                alt.Tooltip(
                                    "Disease:N",
                                    title="Disease",
                                ),
                                alt.Tooltip(
                                    "Records:Q",
                                    title="Records",
                                    format=",",
                                ),
                            ],
                        )
                        .properties(
                            height=540,
                            title=alt.TitleParams(
                                text=(
                                    "Monthly Disease Comparison"
                                ),
                                fontSize=18,
                                anchor="start",
                            ),
                        )
                        .configure_axis(
                            labelFontSize=11,
                            titleFontSize=12,
                        )
                        .configure_title(
                            fontSize=18
                        )
                    )

                    if st.session_state.get(
                        "show_data_labels",
                        False,
                    ):

                        labels = (
                            alt.Chart(
                                chart_disease_month
                            )
                            .mark_text(
                                dy=-8,
                                fontSize=8,
                            )
                            .encode(
                                x=alt.X(
                                    "Month:N",
                                    sort=CALENDAR_MONTHS,
                                ),
                                y=alt.Y(
                                    "Records:Q"
                                ),
                                color=alt.Color(
                                    "Disease:N",
                                    legend=None,
                                ),
                                text=alt.Text(
                                    "Records:Q",
                                    format=",",
                                ),
                            )
                        )

                        chart = (
                            chart
                            + labels
                        )

                    st.altair_chart(
                        chart,
                        use_container_width=True,
                    )

                    try:

                        from chart_helpers import (
                            register_displayed_chart,
                        )

                        export_table = (
                            chart_disease_month[
                                [
                                    "Month",
                                    "Disease",
                                    "Records",
                                ]
                            ]
                            .copy()
                        )

                        register_displayed_chart(
                            chart=chart,
                            title=(
                                "Monthly Disease Comparison"
                            ),
                            filename=(
                                "Monthly_Disease_Comparison"
                            ),
                            table_data=export_table,
                        )

                    except Exception:
                        pass

    else:

        st.info(
            "Month and Disease columns are required."
        )

    # ========================================================
    # 3. DISEASE-WISE BURDEN
    # ========================================================

    st.subheader(
        "3. Disease-wise Burden"
    )

    if "Disease" in df.columns:

        disease_counts = (
            _clean_series(
                df,
                "Disease",
            )
            .value_counts()
            .head(15)
            .reset_index()
        )

        disease_counts.columns = [
            "Disease",
            "Records",
        ]

        render_bar_chart(
            disease_counts,
            title="Disease-wise Burden",
            x_title="Disease",
            y_title="Records",
            horizontal=True,
            export_title="Disease-wise Burden",
            export_filename="Disease-wise_Burden",
            export_table=disease_counts,
        )

        st.dataframe(
            disease_counts,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Disease column is not available."
        )

    # ========================================================
    # 4. TEST PERFORMED / PATHOGEN NAME
    # ========================================================

    st.subheader(
        "4. Test Performed / Pathogen Name-wise Analysis"
    )

    pathogen_column = None

    for candidate in [
        "Test Performed Pathogen Name",
        "Pathogen Name",
        "Test Performed Pathogen",
        "Pathogen",
    ]:

        if candidate in df.columns:

            pathogen_column = candidate
            break

    if pathogen_column:

        pathogen_counts = (
            _clean_series(
                df,
                pathogen_column,
            )
            .value_counts()
            .head(20)
            .reset_index()
        )

        pathogen_counts.columns = [
            pathogen_column,
            "Records",
        ]

        render_bar_chart(
            pathogen_counts,
            title=(
                "Test Performed / Pathogen Name-wise Analysis"
            ),
            x_title=pathogen_column,
            y_title="Records",
            horizontal=True,
            export_title=(
                "Test Performed Pathogen Name-wise Analysis"
            ),
            export_filename=(
                "Test_Performed_Pathogen_Name-wise_Analysis"
            ),
            export_table=pathogen_counts,
        )

        st.dataframe(
            pathogen_counts,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No pathogen-name column is available."
        )

    # ========================================================
    # 5. FACILITY-WISE BURDEN
    # ========================================================

    st.subheader(
        "5. Facility-wise Burden"
    )

    if "Facility Name" in df.columns:

        facility_counts = (
            _clean_series(
                df,
                "Facility Name",
            )
            .value_counts()
            .head(20)
            .reset_index()
        )

        facility_counts.columns = [
            "Facility Name",
            "Records",
        ]

        render_bar_chart(
            facility_counts,
            title="Facility-wise Burden",
            x_title="Facility Name",
            y_title="Records",
            horizontal=True,
            export_title="Facility-wise Burden",
            export_filename="Facility-wise_Burden",
            export_table=facility_counts,
        )

        st.dataframe(
            facility_counts,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Facility Name column is not available."
        )

    # ========================================================
    # 6. WARD-WISE BURDEN
    # ========================================================

    st.subheader(
        "6. Ward-wise Burden"
    )

    if "Ward Name" in df.columns:

        ward_counts = (
            _clean_series(
                df,
                "Ward Name",
            )
            .value_counts()
            .reset_index()
        )

        ward_counts.columns = [
            "Ward Name",
            "Records",
        ]

        ward_counts = (
            _sort_ward_dataframe(
                ward_counts,
                "Ward Name",
            )
        )

        render_bar_chart(
            ward_counts,
            title="Ward-wise Burden",
            x_title="Ward Name",
            y_title="Records",
            horizontal=True,
            export_title="Ward-wise Burden",
            export_filename="Ward-wise_Burden",
            export_table=ward_counts,
        )

        st.dataframe(
            ward_counts,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Ward Name column is not available."
        )

    # ========================================================
    # 7. OPD / IPD DISTRIBUTION
    # ========================================================

    st.subheader(
        "7. OPD / IPD Distribution"
    )

    if "OPD/IPD" in df.columns:

        opd_ipd_counts = (
            _clean_series(
                df,
                "OPD/IPD",
            )
            .value_counts()
            .reset_index()
        )

        opd_ipd_counts.columns = [
            "OPD/IPD",
            "Records",
        ]

        render_bar_chart(
            opd_ipd_counts,
            title="OPD / IPD Distribution",
            x_title="OPD/IPD",
            y_title="Records",
            export_title="OPD / IPD Distribution",
            export_filename="OPD_IPD_Distribution",
            export_table=opd_ipd_counts,
        )

        st.dataframe(
            opd_ipd_counts,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "OPD/IPD column is not available."
        )

    # ========================================================
    # 8. REPORTING DATE TREND
    # ========================================================

    st.subheader(
        "8. Reporting Date Trend"
    )

    if "Reporting Date" in df.columns:

        reporting_dates = pd.to_datetime(
            df["Reporting Date"],
            errors="coerce",
        ).dropna()

        if not reporting_dates.empty:

            daily_counts = (
                reporting_dates
                .dt.normalize()
                .value_counts()
                .sort_index()
                .reset_index()
            )

            daily_counts.columns = [
                "Reporting Date",
                "Records",
            ]

            render_line_chart(
                daily_counts,
                title="Reporting Date Trend",
                x_title="Reporting Date",
                y_title="Records",
                export_title="Reporting Date Trend",
                export_filename="Reporting_Date_Trend",
                export_table=daily_counts,
            )

            st.dataframe(
                daily_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No valid Reporting Date values found."
            )

    else:

        st.info(
            "Reporting Date column is not available."
        )

    # ========================================================
    # 9. TREND SUMMARY
    # ========================================================

    st.subheader(
        "9. Trend Summary"
    )

    total_records = len(
        df
    )

    total_diseases = (
        df["Disease"]
        .nunique()
        if "Disease" in df.columns
        else 0
    )

    total_facilities = (
        df["Facility Name"]
        .nunique()
        if "Facility Name" in df.columns
        else 0
    )

    total_wards = (
        df["Ward Name"]
        .nunique()
        if "Ward Name" in df.columns
        else 0
    )

    c1, c2, c3, c4 = st.columns(
        4
    )

    with c1:

        st.metric(
            "Records Analysed",
            f"{total_records:,}",
        )

    with c2:

        st.metric(
            "Diseases",
            f"{total_diseases:,}",
        )

    with c3:

        st.metric(
            "Facilities",
            f"{total_facilities:,}",
        )

    with c4:

        st.metric(
            "Wards",
            f"{total_wards:,}",
        )
