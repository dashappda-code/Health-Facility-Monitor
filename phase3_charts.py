import streamlit as st
import pandas as pd
import altair as alt

from chart_helpers import (
    render_bar_chart,
    render_line_chart,
    register_displayed_chart,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _clean_series(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="object")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


# ============================================================
# MONTH ORDER
# ============================================================

CALENDAR_MONTHS = [
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

MONTH_NUMBER_MAP = {
    month: index
    for index, month in enumerate(
        CALENDAR_MONTHS,
        start=1,
    )
}


def _normalize_month(value):
    """
    Convert different month formats into standard Jan-Dec labels.
    """
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()

    if text in {"january", "jan", "1", "01"}:
        return "Jan"

    if text in {"february", "feb", "2", "02"}:
        return "Feb"

    if text in {"march", "mar", "3", "03"}:
        return "Mar"

    if text in {"april", "apr", "4", "04"}:
        return "Apr"

    if text in {"may", "5", "05"}:
        return "May"

    if text in {"june", "jun", "6", "06"}:
        return "Jun"

    if text in {"july", "jul", "7", "07"}:
        return "Jul"

    if text in {"august", "aug", "8", "08"}:
        return "Aug"

    if text in {"september", "sep", "sept", "9", "09"}:
        return "Sep"

    if text in {"october", "oct", "10"}:
        return "Oct"

    if text in {"november", "nov", "11"}:
        return "Nov"

    if text in {"december", "dec", "12"}:
        return "Dec"

    return text


# ============================================================
# YEAR NORMALIZATION
# ============================================================

def _normalize_year(value):
    """
    Convert different year formats into a numeric year.
    """
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    # Direct numeric year
    try:
        numeric = float(text)

        if numeric.is_integer():
            year = int(numeric)

            if 1900 <= year <= 2100:
                return year

    except Exception:
        pass

    # Date-like year values
    try:
        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if not pd.isna(parsed):
            year = int(parsed.year)

            if 1900 <= year <= 2100:
                return year

    except Exception:
        pass

    return ""


# ============================================================
# YEAR-MONTH TIMELINE
# ============================================================

def _build_year_month_timeline(
    data,
    year_column="Year",
    month_column="Month",
    value_column="Records",
):
    """
    Create a complete chronological Year-Month timeline.
    Missing months are retained with zero records.
    """

    if (
        data is None
        or data.empty
        or year_column not in data.columns
        or month_column not in data.columns
        or value_column not in data.columns
    ):
        return pd.DataFrame()

    temp = data.copy()

    temp["Month"] = temp[month_column].apply(
        _normalize_month
    )

    temp["Year"] = temp[year_column].apply(
        _normalize_year
    )

    temp["Year"] = pd.to_numeric(
        temp["Year"],
        errors="coerce",
    )

    temp = temp[
        temp["Month"].isin(CALENDAR_MONTHS)
        & temp["Year"].notna()
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    temp["Year"] = temp["Year"].astype(int)

    temp[value_column] = pd.to_numeric(
        temp[value_column],
        errors="coerce",
    ).fillna(0)

    temp["Month Number"] = temp["Month"].map(
        MONTH_NUMBER_MAP
    )

    temp = (
        temp
        .groupby(
            [
                "Year",
                "Month",
                "Month Number",
            ],
            as_index=False,
        )[value_column]
        .sum()
    )

    available_years = sorted(
        temp["Year"].unique().tolist()
    )

    if not available_years:
        return pd.DataFrame()

    full_index = pd.MultiIndex.from_product(
        [
            available_years,
            CALENDAR_MONTHS,
        ],
        names=[
            "Year",
            "Month",
        ],
    )

    temp = (
        temp[
            [
                "Year",
                "Month",
                value_column,
            ]
        ]
        .set_index(
            [
                "Year",
                "Month",
            ]
        )
        .reindex(
            full_index,
            fill_value=0,
        )
        .reset_index()
    )

    temp["Month Number"] = temp["Month"].map(
        MONTH_NUMBER_MAP
    )

    temp[value_column] = (
        pd.to_numeric(
            temp[value_column],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    temp["Sort Date"] = pd.to_datetime(
        dict(
            year=temp["Year"],
            month=temp["Month Number"],
            day=1,
        ),
        errors="coerce",
    )

    temp["Month-Year"] = (
        temp["Sort Date"]
        .dt
        .strftime("%b-%y")
    )

    temp = (
        temp
        .sort_values(
            "Sort Date",
            kind="stable",
        )
        .reset_index(drop=True)
    )

    return temp[
        [
            "Year",
            "Month",
            "Month Number",
            "Sort Date",
            "Month-Year",
            value_column,
        ]
    ]


# ============================================================
# CHART ORDER HELPERS
# ============================================================

def _apply_chronological_zwsp(label_list):
    """
    Adds increasing Zero-Width Spaces to force Streamlit's
    alphabetical sorting to match chronological order.
    """

    return [
        ("\u200b" * (i + 1)) + str(lbl)
        for i, lbl in enumerate(label_list)
    ]


# ============================================================
# WARD ORDER
# ============================================================

def _sort_ward_dataframe(
    df,
    column="Ward",
):
    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return df

    result = df.copy()

    result["_ward_order"] = (
        result[column]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    result = (
        result
        .sort_values(
            "_ward_order",
            kind="stable",
        )
        .drop(
            columns="_ward_order"
        )
        .reset_index(drop=True)
    )

    return result


# ============================================================
# MAIN CHART RENDERER
# ============================================================

def render_charts(df):

    st.subheader("📈 Charts & Trends")

    if df is None or df.empty:
        st.warning(
            "No records available for the selected filters."
        )
        return

    st.caption(
        "Month-wise, disease-wise, facility-wise and ward-wise "
        "analysis based on the currently selected Global Dashboard Filters."
    )

    # ========================================================
    # YEAR COLUMN DETECTION
    # ========================================================

    year_column = None

    possible_year_columns = [
        "Year",
        "Reporting Year",
        "Year of Reporting",
    ]

    for column in possible_year_columns:

        if column in df.columns:
            year_column = column
            break

    # ========================================================
    # 1. MONTH-WISE PROGRAMME TREND
    # ========================================================

    st.markdown(
        "### 🗓️ Month-wise Programme Trend"
    )

    if "Month" in df.columns:

        month_series = _clean_series(
            df,
            "Month",
        )

        month_series = month_series[
            month_series.ne("")
            & month_series.str.lower().ne("nan")
            & month_series.str.lower().ne("nat")
            & month_series.str.lower().ne("none")
        ]

        if not month_series.empty:

            use_year_month = False

            if year_column is not None:

                timeline_source = pd.DataFrame({
                    "Year": df[year_column],
                    "Month": df["Month"],
                })

                timeline_source["Records"] = 1

                year_month_data = (
                    _build_year_month_timeline(
                        timeline_source,
                        year_column="Year",
                        month_column="Month",
                        value_column="Records",
                    )
                )

                if not year_month_data.empty:

                    use_year_month = True

                    year_month_data = (
                        year_month_data
                        .sort_values(
                            "Sort Date",
                            kind="stable",
                        )
                        .reset_index(drop=True)
                    )

                    chart_labels = (
                        _apply_chronological_zwsp(
                            year_month_data[
                                "Month-Year"
                            ]
                        )
                    )

                    chart_series = pd.Series(
                        year_month_data[
                            "Records"
                        ].to_numpy(),
                        index=pd.CategoricalIndex(
                            chart_labels,
                            categories=chart_labels,
                            ordered=True,
                            name="Month-Year",
                        ),
                        name="Records",
                    )

                    render_bar_chart(
                        chart_series,
                        title="Month-wise Programme Trend",
                        filename="Month-wise_Programme_Trend",
                        use_container_width=True,
                    )

                    display_month_counts = (
                        year_month_data[
                            [
                                "Month-Year",
                                "Records",
                            ]
                        ].copy()
                    )

                    st.dataframe(
                        display_month_counts,
                        use_container_width=True,
                        hide_index=True,
                    )

            # ====================================================
            # FALLBACK: MONTH-ONLY ANALYSIS
            # ====================================================

            if not use_year_month:

                normalized_months = (
                    month_series.apply(
                        _normalize_month
                    )
                )

                month_counts = (
                    normalized_months
                    .value_counts()
                    .rename_axis("Month")
                    .reset_index(
                        name="Records"
                    )
                )

                month_counts = month_counts[
                    month_counts["Month"].isin(
                        CALENDAR_MONTHS
                    )
                ].copy()

                month_counts["_Month_Order"] = (
                    month_counts["Month"]
                    .map(MONTH_NUMBER_MAP)
                )

                month_counts = (
                    month_counts
                    .sort_values(
                        "_Month_Order"
                    )
                    .drop(
                        columns="_Month_Order"
                    )
                    .reset_index(drop=True)
                )

                chart_labels = [
                    ("\u200b" * MONTH_NUMBER_MAP[m])
                    + m
                    for m in month_counts["Month"]
                ]

                chart_series = pd.Series(
                    month_counts[
                        "Records"
                    ].to_numpy(),
                    index=pd.CategoricalIndex(
                        chart_labels,
                        categories=chart_labels,
                        ordered=True,
                        name="Month",
                    ),
                    name="Records",
                )

                render_bar_chart(
                    chart_series,
                    title="Month-wise Programme Trend",
                    filename="Month-wise_Programme_Trend",
                    use_container_width=True,
                )

                display_month_counts = (
                    month_counts.copy()
                )

                display_month_counts["Month"] = (
                    display_month_counts[
                        "Month"
                    ].astype(str)
                )

                st.dataframe(
                    display_month_counts,
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.info(
                "Month information is not available "
                "for the selected records."
            )

    # ========================================================
    # 2. MONTHLY DISEASE COMPARISON
    # ========================================================

    st.divider()

    st.markdown(
        "### 🦠 Monthly Disease Comparison"
    )

    if (
        "Month" in df.columns
        and "Disease" in df.columns
    ):

        temp_columns = [
            "Month",
            "Disease",
        ]

        if year_column is not None:
            temp_columns.append(
                year_column
            )

        temp = df[
            temp_columns
        ].copy()

        temp["Month"] = _clean_series(
            temp,
            "Month",
        )

        temp["Disease"] = _clean_series(
            temp,
            "Disease",
        )

        temp = temp[
            temp["Month"].ne("")
            & temp["Disease"].ne("")
            & temp["Month"].str.lower().ne("nan")
            & temp["Disease"].str.lower().ne("nan")
            & temp["Month"].str.lower().ne("none")
            & temp["Disease"].str.lower().ne("none")
        ]

        if not temp.empty:

            temp["Month"] = (
                temp["Month"]
                .apply(_normalize_month)
            )

            temp = temp[
                temp["Month"].isin(
                    CALENDAR_MONTHS
                )
            ].copy()

            if not temp.empty:

                use_year_month_disease = False

                # ====================================================
                # YEAR + MONTH DISEASE ANALYSIS
                # ====================================================

                if year_column is not None:

                    temp["Year"] = (
                        temp[year_column]
                        .apply(_normalize_year)
                    )

                    temp["Year"] = pd.to_numeric(
                        temp["Year"],
                        errors="coerce",
                    )

                    valid_year_temp = temp[
                        temp["Year"].notna()
                    ].copy()

                    if not valid_year_temp.empty:

                        valid_year_temp["Year"] = (
                            valid_year_temp[
                                "Year"
                            ].astype(int)
                        )

                        available_diseases = (
                            valid_year_temp[
                                "Disease"
                            ]
                            .dropna()
                            .astype(str)
                            .str.strip()
                        )

                        available_diseases = (
                            available_diseases[
                                available_diseases.ne("")
                                & available_diseases.str.lower().ne("nan")
                                & available_diseases.str.lower().ne("none")
                            ]
                            .drop_duplicates()
                            .sort_values(
                                key=lambda x: x.str.lower()
                            )
                            .tolist()
                        )

                        if available_diseases:

                            st.markdown(
                                "**Select diseases to display in the chart:**"
                            )

                            checkbox_columns = st.columns(4)

                            selected_diseases = []

                            for index, disease in enumerate(
                                available_diseases
                            ):

                                checkbox_column = (
                                    checkbox_columns[
                                        index % 4
                                    ]
                                )

                                checkbox_key = (
                                    "phase3_disease_"
                                    + str(index)
                                    + "_"
                                    + str(disease)
                                )

                                with checkbox_column:

                                    is_selected = st.checkbox(
                                        disease,
                                        value=True,
                                        key=checkbox_key,
                                    )

                                if is_selected:
                                    selected_diseases.append(
                                        disease
                                    )

                            disease_month = (
                                valid_year_temp
                                .groupby(
                                    [
                                        "Year",
                                        "Month",
                                        "Disease",
                                    ]
                                )
                                .size()
                                .rename("Records")
                                .reset_index()
                            )

                            available_years = sorted(
                                valid_year_temp[
                                    "Year"
                                ]
                                .unique()
                                .tolist()
                            )

                            full_index = (
                                pd.MultiIndex.from_product(
                                    [
                                        available_years,
                                        CALENDAR_MONTHS,
                                        available_diseases,
                                    ],
                                    names=[
                                        "Year",
                                        "Month",
                                        "Disease",
                                    ],
                                )
                            )

                            disease_month = (
                                disease_month
                                .set_index(
                                    [
                                        "Year",
                                        "Month",
                                        "Disease",
                                    ]
                                )
                                .reindex(
                                    full_index,
                                    fill_value=0,
                                )
                                .reset_index()
                            )

                            disease_month["Records"] = (
                                pd.to_numeric(
                                    disease_month[
                                        "Records"
                                    ],
                                    errors="coerce",
                                )
                                .fillna(0)
                                .astype(int)
                            )

                            disease_month["Month Number"] = (
                                disease_month[
                                    "Month"
                                ].map(
                                    MONTH_NUMBER_MAP
                                )
                            )

                            disease_month["Sort Date"] = (
                                pd.to_datetime(
                                    dict(
                                        year=disease_month[
                                            "Year"
                                        ],
                                        month=disease_month[
                                            "Month Number"
                                        ],
                                        day=1,
                                    ),
                                    errors="coerce",
                                )
                            )

                            disease_month["Month-Year"] = (
                                disease_month[
                                    "Sort Date"
                                ]
                                .dt
                                .strftime("%b-%y")
                            )

                            disease_month = (
                                disease_month
                                .sort_values(
                                    [
                                        "Sort Date",
                                        "Disease",
                                    ],
                                    kind="stable",
                                )
                                .reset_index(drop=True)
                            )

                            timeline_order = (
                                disease_month[
                                    [
                                        "Sort Date",
                                        "Month-Year",
                                    ]
                                ]
                                .drop_duplicates(
                                    subset=[
                                        "Month-Year"
                                    ]
                                )
                                .sort_values(
                                    "Sort Date",
                                    kind="stable",
                                )[
                                    "Month-Year"
                                ]
                                .tolist()
                            )

                            chart_disease_month = (
                                disease_month[
                                    disease_month[
                                        "Disease"
                                    ].isin(
                                        selected_diseases
                                    )
                                ].copy()
                            )

                            show_labels_ym = st.toggle(
                                "Show Data Labels",
                                value=False,
                                key="toggle_labels_ym",
                            )

                            if not chart_disease_month.empty:

                                base_chart = (
                                    alt.Chart(
                                        chart_disease_month
                                    )
                                    .encode(
                                        x=alt.X(
                                            "Month-Year:O",
                                            sort=timeline_order,
                                            title="Timeline",
                                            axis=alt.Axis(
                                                labelAngle=-45
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
                                    )
                                )

                                lines = (
                                    base_chart
                                    .mark_line(
                                        point=True
                                    )
                                )

                                if show_labels_ym:

                                    text_labels = (
                                        base_chart
                                        .mark_text(
                                            align="center",
                                            baseline="bottom",
                                            dy=-10,
                                            fontSize=11,
                                        )
                                        .encode(
                                            text=alt.Text(
                                                "Records:Q"
                                            )
                                        )
                                    )

                                    final_chart = (
                                        lines
                                        + text_labels
                                    ).properties(
                                        height=540
                                    )

                                else:

                                    final_chart = (
                                        lines
                                        .properties(
                                            height=540
                                        )
                                    )

                                # IMPORTANT:
                                # Register BEFORE displaying so the
                                # export system can capture the exact
                                # disease-month table.

                                register_displayed_chart(
                                    chart=final_chart,
                                    title="Monthly Disease Comparison",
                                    filename="Monthly_Disease_Comparison",
                                    table_data=chart_disease_month[
                                        [
                                            "Year",
                                            "Month",
                                            "Month-Year",
                                            "Disease",
                                            "Records",
                                        ]
                                    ],
                                )

                                st.altair_chart(
                                    final_chart,
                                    use_container_width=True,
                                )

                            else:

                                st.info(
                                    "No diseases are selected. "
                                    "Select at least one disease "
                                    "to display the chart."
                                )

                            use_year_month_disease = True

                # ====================================================
                # FALLBACK: MONTH-ONLY DISEASE ANALYSIS
                # ====================================================

                if not use_year_month_disease:

                    available_diseases = (
                        temp[
                            "Disease"
                        ]
                        .dropna()
                        .astype(str)
                        .str.strip()
                    )

                    available_diseases = (
                        available_diseases[
                            available_diseases.ne("")
                            & available_diseases.str.lower().ne("nan")
                            & available_diseases.str.lower().ne("none")
                        ]
                        .drop_duplicates()
                        .sort_values(
                            key=lambda x: x.str.lower()
                        )
                        .tolist()
                    )

                    if available_diseases:

                        st.markdown(
                            "**Select diseases to display in the chart:**"
                        )

                        checkbox_columns = st.columns(4)

                        selected_diseases = []

                        for index, disease in enumerate(
                            available_diseases
                        ):

                            checkbox_column = (
                                checkbox_columns[
                                    index % 4
                                ]
                            )

                            checkbox_key = (
                                "phase3_disease_month_"
                                + str(index)
                                + "_"
                                + str(disease)
                            )

                            with checkbox_column:

                                is_selected = st.checkbox(
                                    disease,
                                    value=True,
                                    key=checkbox_key,
                                )

                            if is_selected:
                                selected_diseases.append(
                                    disease
                                )

                        cross_tab = pd.crosstab(
                            temp["Month"],
                            temp["Disease"],
                        )

                        cross_tab = (
                            cross_tab
                            .reindex(
                                CALENDAR_MONTHS,
                                fill_value=0,
                            )
                        )

                        chart_diseases = [
                            disease
                            for disease in available_diseases
                            if disease in selected_diseases
                        ]

                        long_df = (
                            cross_tab[
                                chart_diseases
                            ]
                            .reset_index()
                            .melt(
                                id_vars="Month",
                                var_name="Disease",
                                value_name="Records",
                            )
                        )

                        show_labels_m = st.toggle(
                            "Show Data Labels",
                            value=False,
                            key="toggle_labels_m",
                        )

                        if not long_df.empty:

                            base_chart = (
                                alt.Chart(
                                    long_df
                                )
                                .encode(
                                    x=alt.X(
                                        "Month:O",
                                        sort=CALENDAR_MONTHS,
                                        title="Month",
                                        axis=alt.Axis(
                                            labelAngle=-45
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
                                )
                            )

                            lines = (
                                base_chart
                                .mark_line(
                                    point=True
                                )
                            )

                            if show_labels_m:

                                text_labels = (
                                    base_chart
                                    .mark_text(
                                        align="center",
                                        baseline="bottom",
                                        dy=-10,
                                        fontSize=11,
                                    )
                                    .encode(
                                        text=alt.Text(
                                            "Records:Q"
                                        )
                                    )
                                )

                                final_chart = (
                                    lines
                                    + text_labels
                                ).properties(
                                    height=540
                                )

                            else:

                                final_chart = (
                                    lines
                                    .properties(
                                        height=540
                                    )
                                )

                            register_displayed_chart(
                                chart=final_chart,
                                title="Monthly Disease Comparison",
                                filename="Monthly_Disease_Comparison",
                                table_data=long_df[
                                    [
                                        "Month",
                                        "Disease",
                                        "Records",
                                    ]
                                ],
                            )

                            st.altair_chart(
                                final_chart,
                                use_container_width=True,
                            )

                        else:

                            st.info(
                                "No diseases are selected. "
                                "Select at least one disease "
                                "to display the chart."
                            )

                    st.caption(
                        "Chart displays all available diseases "
                        "selected below the chart. Months are shown "
                        "in calendar order from January to December."
                    )

            else:

                st.info(
                    "Valid month information is not available "
                    "for the selected records."
                )

        else:

            st.info(
                "Disease/month information is not available "
                "for the selected records."
            )

    # ========================================================
    # 3. DISEASE-WISE BURDEN
    # ========================================================

    st.divider()

    st.markdown(
        "### 🦠 Disease-wise Burden"
    )

    if "Disease" in df.columns:

        disease_series = _clean_series(
            df,
            "Disease",
        )

        disease_series = disease_series[
            disease_series.ne("")
            & disease_series.str.lower().ne("nan")
            & disease_series.str.lower().ne("none")
        ]

        if not disease_series.empty:

            disease_counts = (
                disease_series
                .value_counts()
                .head(15)
                .rename_axis("Disease")
                .reset_index(
                    name="Records"
                )
            )

            render_bar_chart(
                disease_counts.set_index(
                    "Disease"
                )["Records"],
                title="Disease-wise Burden",
                filename="Disease-wise_Burden",
                use_container_width=True,
            )

            st.dataframe(
                disease_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Disease information is not available."
            )

    # ========================================================
    # 4. TEST PERFORMED / PATHOGEN NAME-WISE ANALYSIS
    # ========================================================

    st.divider()

    st.markdown(
        "### 🧪 Test Performed / Pathogen Name-wise Analysis"
    )

    pathogen_column = None

    possible_pathogen_columns = [
        "Test Performed Pathogen Name",
        "Pathogen Name",
        "Test Performed Pathogen",
        "Pathogen",
    ]

    for column in possible_pathogen_columns:

        if column in df.columns:
            pathogen_column = column
            break

    if pathogen_column is not None:

        pathogen_series = _clean_series(
            df,
            pathogen_column,
        )

        pathogen_series = pathogen_series[
            pathogen_series.ne("")
            & pathogen_series.str.lower().ne("nan")
            & pathogen_series.str.lower().ne("none")
        ]

        if not pathogen_series.empty:

            pathogen_counts = (
                pathogen_series
                .value_counts()
                .head(20)
                .rename_axis(
                    "Test Performed Pathogen Name"
                )
                .reset_index(
                    name="Records"
                )
            )

            render_bar_chart(
                pathogen_counts.set_index(
                    "Test Performed Pathogen Name"
                )["Records"],
                title="Test Performed / Pathogen Name-wise Analysis",
                filename="Test_Performed_Pathogen_Name-wise_Analysis",
                use_container_width=True,
            )

            st.dataframe(
                pathogen_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Test performed / pathogen information "
                "is not available for the selected records."
            )

    elif (
        "Test Performed" in df.columns
        and "Pathogen Name" in df.columns
    ):

        test_series = _clean_series(
            df,
            "Test Performed",
        )

        pathogen_series = _clean_series(
            df,
            "Pathogen Name",
        )

        combined = (
            test_series
            + " - "
            + pathogen_series
        )

        combined = combined[
            test_series.ne("")
            | pathogen_series.ne("")
        ]

        combined = combined[
            combined.str.strip().ne("")
        ]

        if not combined.empty:

            pathogen_counts = (
                combined
                .value_counts()
                .head(20)
                .rename_axis(
                    "Test Performed Pathogen Name"
                )
                .reset_index(
                    name="Records"
                )
            )

            render_bar_chart(
                pathogen_counts.set_index(
                    "Test Performed Pathogen Name"
                )["Records"],
                title="Test Performed / Pathogen Name-wise Analysis",
                filename="Test_Performed_Pathogen_Name-wise_Analysis",
                use_container_width=True,
            )

            st.dataframe(
                pathogen_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Test performed / pathogen information "
                "is not available for the selected records."
            )

    else:

        st.info(
            "Test performed / pathogen fields are not "
            "available in the current dataset."
        )

    # ========================================================
    # 5. FACILITY-WISE BURDEN
    # ========================================================

    st.divider()

    st.markdown(
        "### 🏥 Facility-wise Burden"
    )

    if "Facility Name" in df.columns:

        facility_series = _clean_series(
            df,
            "Facility Name",
        )

        facility_series = facility_series[
            facility_series.ne("")
            & facility_series.str.lower().ne("nan")
            & facility_series.str.lower().ne("none")
        ]

        if not facility_series.empty:

            facility_counts = (
                facility_series
                .value_counts()
                .head(20)
                .rename_axis("Facility")
                .reset_index(
                    name="Records"
                )
            )

            render_bar_chart(
                facility_counts.set_index(
                    "Facility"
                )["Records"],
                title="Facility-wise Burden",
                filename="Facility-wise_Burden",
                use_container_width=True,
            )

            st.dataframe(
                facility_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Facility information is not available."
            )

    # ========================================================
    # 6. WARD-WISE BURDEN
    # ========================================================

    st.divider()

    st.markdown(
        "### 📍 Ward-wise Burden"
    )

    if "Ward Name" in df.columns:

        ward_series = _clean_series(
            df,
            "Ward Name",
        )

        ward_series = ward_series[
            ward_series.ne("")
            & ward_series.str.lower().ne("nan")
            & ward_series.str.lower().ne("none")
        ]

        if not ward_series.empty:

            ward_counts = (
                ward_series
                .value_counts()
                .rename_axis("Ward")
                .reset_index(
                    name="Records"
                )
            )

            ward_counts = _sort_ward_dataframe(
                ward_counts,
                "Ward",
            )

            render_bar_chart(
                ward_counts.set_index(
                    "Ward"
                )["Records"],
                title="Ward-wise Burden",
                filename="Ward-wise_Burden",
                use_container_width=True,
            )

            st.dataframe(
                ward_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Ward information is not available."
            )

    # ========================================================
    # 7. OPD / IPD COMPARISON
    # ========================================================

    st.divider()

    st.markdown(
        "### 🏨 OPD / IPD Distribution"
    )

    if "OPD/IPD" in df.columns:

        opd_series = _clean_series(
            df,
            "OPD/IPD",
        )

        opd_series = opd_series[
            opd_series.ne("")
            & opd_series.str.lower().ne("nan")
            & opd_series.str.lower().ne("none")
        ]

        if not opd_series.empty:

            opd_counts = (
                opd_series
                .value_counts()
                .rename_axis("OPD/IPD")
                .reset_index(
                    name="Records"
                )
            )

            render_bar_chart(
                opd_counts.set_index(
                    "OPD/IPD"
                )["Records"],
                title="OPD / IPD Distribution",
                filename="OPD_IPD_Distribution",
                use_container_width=True,
            )

            st.dataframe(
                opd_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "OPD/IPD information is not available."
            )

    # ========================================================
    # 8. REPORTING DATE TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 📅 Reporting Date Trend"
    )

    if "Reporting Date" in df.columns:

        date_df = df[
            ["Reporting Date"]
        ].copy()

        date_df["Reporting Date"] = (
            pd.to_datetime(
                date_df["Reporting Date"],
                errors="coerce",
            )
        )

        date_df = date_df.dropna(
            subset=["Reporting Date"]
        )

        if not date_df.empty:

            daily_counts = (
                date_df
                .assign(
                    Date=lambda x:
                    x["Reporting Date"]
                    .dt
                    .normalize()
                )
                .groupby("Date")
                .size()
                .rename("Records")
            )

            render_line_chart(
                daily_counts,
                title="Reporting Date Trend",
                filename="Reporting_Date_Trend",
                use_container_width=True,
            )

            daily_display = (
                daily_counts
                .reset_index()
            )

            daily_display.columns = [
                "Reporting Date",
                "Records",
            ]

            st.dataframe(
                daily_display,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Valid reporting dates are not available."
            )

    # ========================================================
    # 9. TREND SUMMARY
    # ========================================================

    st.divider()

    st.markdown(
        "### 📌 Trend Summary"
    )

    summary_columns = st.columns(4)

    with summary_columns[0]:

        st.metric(
            "Records Analysed",
            f"{len(df):,}",
        )

    with summary_columns[1]:

        if "Disease" in df.columns:

            disease_count = _clean_series(
                df,
                "Disease",
            )

            disease_count = disease_count[
                disease_count.ne("")
                & disease_count.str.lower().ne("nan")
                & disease_count.str.lower().ne("none")
            ]

            st.metric(
                "Diseases",
                f"{disease_count.nunique():,}",
            )

        else:

            st.metric(
                "Diseases",
                "0",
            )

    with summary_columns[2]:

        if "Facility Name" in df.columns:

            facility_count = _clean_series(
                df,
                "Facility Name",
            )

            facility_count = facility_count[
                facility_count.ne("")
                & facility_count.str.lower().ne("nan")
                & facility_count.str.lower().ne("none")
            ]

            st.metric(
                "Facilities",
                f"{facility_count.nunique():,}",
            )

        else:

            st.metric(
                "Facilities",
                "0",
            )

    with summary_columns[3]:

        if "Ward Name" in df.columns:

            ward_count = _clean_series(
                df,
                "Ward Name",
            )

            ward_count = ward_count[
                ward_count.ne("")
                & ward_count.str.lower().ne("nan")
                & ward_count.str.lower().ne("none")
            ]

            st.metric(
                "Wards",
                f"{ward_count.nunique():,}",
            )

        else:

            st.metric(
                "Wards",
                "0",
            )
