
import streamlit as st
import pandas as pd
import altair as alt
import re

from chart_helpers import (
    render_bar_chart,
    render_line_chart,
)


# ============================================================
# CONFIGURATION
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

# Common colour for Month-wise and Ward-wise charts
CHART_LABEL_COLOR = "#1f77b4"

# Fixed Ward sequence
FIXED_WARD_ORDER = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
]


# ============================================================
# BASIC CLEANING HELPERS
# ============================================================

def _clean_series(df, column):

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return pd.Series(dtype="object")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _valid_text_series(series):

    if series is None or series.empty:
        return series

    return series[
        series.ne("")
        & series.str.lower().ne("nan")
        & series.str.lower().ne("nat")
        & series.str.lower().ne("none")
        & series.str.lower().ne("null")
    ]


# ============================================================
# MONTH NORMALIZATION
# ============================================================

def _normalize_month(value):

    if pd.isna(value):
        return None

    text = str(value).strip().lower()

    month_map = {

        "january": "Jan",
        "jan": "Jan",
        "1": "Jan",
        "01": "Jan",

        "february": "Feb",
        "feb": "Feb",
        "2": "Feb",
        "02": "Feb",

        "march": "Mar",
        "mar": "Mar",
        "3": "Mar",
        "03": "Mar",

        "april": "Apr",
        "apr": "Apr",
        "4": "Apr",
        "04": "Apr",

        "may": "May",
        "5": "May",
        "05": "May",

        "june": "Jun",
        "jun": "Jun",
        "6": "Jun",
        "06": "Jun",

        "july": "Jul",
        "jul": "Jul",
        "7": "Jul",
        "07": "Jul",

        "august": "Aug",
        "aug": "Aug",
        "8": "Aug",
        "08": "Aug",

        "september": "Sep",
        "sep": "Sep",
        "sept": "Sep",
        "9": "Sep",
        "09": "Sep",

        "october": "Oct",
        "oct": "Oct",
        "10": "Oct",

        "november": "Nov",
        "nov": "Nov",
        "11": "Nov",

        "december": "Dec",
        "dec": "Dec",
        "12": "Dec",
    }

    return month_map.get(text)


# ============================================================
# WARD NORMALIZATION
# ============================================================

def _extract_ward_letter(value):

    """
    Extracts the ward letter from common formats such as:

    A
    B
    Ward A
    WARD B
    Ward-A
    Ward_B
    A Ward
    B WARD
    """

    if pd.isna(value):
        return None

    text = str(value).strip().upper()

    # Replace separators
    text = re.sub(
        r"[-_/]+",
        " ",
        text,
    )

    # Normalize multiple spaces
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    # --------------------------------------------------------
    # Ward A / WARD A
    # --------------------------------------------------------

    match = re.search(
        r"\bWARD\s*([A-Z])\b",
        text,
    )

    if match:

        letter = match.group(1)

        if letter in FIXED_WARD_ORDER:
            return letter

    # --------------------------------------------------------
    # A Ward / B Ward
    # --------------------------------------------------------

    match = re.search(
        r"\b([A-Z])\s*WARD\b",
        text,
    )

    if match:

        letter = match.group(1)

        if letter in FIXED_WARD_ORDER:
            return letter

    # --------------------------------------------------------
    # Simple A / B / C
    # --------------------------------------------------------

    match = re.fullmatch(
        r"([A-Z])",
        text,
    )

    if match:

        letter = match.group(1)

        if letter in FIXED_WARD_ORDER:
            return letter

    return None


def _ward_sort_key(value):

    letter = _extract_ward_letter(value)

    if letter is not None:

        return (
            0,
            FIXED_WARD_ORDER.index(letter),
        )

    # Unknown ward names come after A-T
    return (
        1,
        str(value).upper(),
    )


def _sort_wards(df, column="Ward"):

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return df

    result = df.copy()

    result["_ward_sort_key"] = (
        result[column]
        .apply(_ward_sort_key)
    )

    result = (
        result
        .sort_values(
            "_ward_sort_key",
            kind="stable",
        )
        .drop(
            columns="_ward_sort_key"
        )
        .reset_index(
            drop=True,
        )
    )

    return result


# ============================================================
# MONTH-WISE PROGRAMME TREND
# ============================================================

def _render_month_chart(month_df):

    bars = (
        alt.Chart(month_df)
        .mark_bar(
            color=CHART_LABEL_COLOR
        )
        .encode(

            x=alt.X(
                "Month:N",
                sort=CALENDAR_MONTHS,
                title="Month",
                axis=alt.Axis(
                    labelAngle=0
                ),
            ),

            y=alt.Y(
                "Records:Q",
                title="Records",
            ),

            tooltip=[

                alt.Tooltip(
                    "Month:N",
                    title="Month",
                ),

                alt.Tooltip(
                    "Records:Q",
                    title="Records",
                    format=",",
                ),
            ],
        )
    )

    labels = (
        alt.Chart(month_df)
        .mark_text(
            dy=-10,
            fontSize=13,
            fontWeight="bold",
            color=CHART_LABEL_COLOR,
        )
        .encode(

            x=alt.X(
                "Month:N",
                sort=CALENDAR_MONTHS,
            ),

            y=alt.Y(
                "Records:Q",
            ),

            text=alt.Text(
                "Records:Q",
                format=",d",
            ),
        )
    )

    chart = (
        bars + labels
    ).properties(
        height=400,
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# MONTHLY DISEASE COMPARISON
# ============================================================

def _render_month_disease_chart(
    chart_df,
    disease_columns,
):

    long_df = (
        chart_df
        .reset_index()
        .rename(
            columns={
                "index": "Month"
            }
        )
    )

    long_df = long_df.melt(
        id_vars=[
            "Month"
        ],
        value_vars=disease_columns,
        var_name="Disease",
        value_name="Records",
    )

    # --------------------------------------------------------
    # Main disease lines
    # --------------------------------------------------------

    lines = (
        alt.Chart(long_df)
        .mark_line(
            point=True,
            strokeWidth=3,
        )
        .encode(

            x=alt.X(
                "Month:N",
                sort=CALENDAR_MONTHS,
                title="Month",
                axis=alt.Axis(
                    labelAngle=0
                ),
            ),

            y=alt.Y(
                "Records:Q",
                title="Records",
            ),

            color=alt.Color(
                "Disease:N",
                title="Disease",
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
    )

    # --------------------------------------------------------
    # Bold coloured labels
    # --------------------------------------------------------

    labels = (
        alt.Chart(long_df)
        .mark_text(
            dy=-12,
            fontSize=12,
            fontWeight="bold",
        )
        .encode(

            x=alt.X(
                "Month:N",
                sort=CALENDAR_MONTHS,
            ),

            y=alt.Y(
                "Records:Q",
            ),

            text=alt.Text(
                "Records:Q",
                format=",d",
            ),

            color=alt.Color(
                "Disease:N",
                legend=None,
            ),
        )
    )

    chart = (
        lines + labels
    ).properties(
        height=450,
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# WARD-WISE BURDEN
# ============================================================

def _render_ward_chart(ward_df):

    ward_df = ward_df.copy()

    # --------------------------------------------------------
    # Extract A-T position
    # --------------------------------------------------------

    ward_df["_ward_letter"] = (
        ward_df["Ward"]
        .apply(
            _extract_ward_letter
        )
    )

    ward_df["_ward_position"] = (
        ward_df["_ward_letter"]
        .apply(
            lambda x:
            FIXED_WARD_ORDER.index(x)
            if x in FIXED_WARD_ORDER
            else 999
        )
    )

    # --------------------------------------------------------
    # Strict A -> T sorting
    # --------------------------------------------------------

    ward_df = (
        ward_df
        .sort_values(
            "_ward_position",
            kind="stable",
        )
        .drop(
            columns=[
                "_ward_letter",
                "_ward_position",
            ]
        )
        .reset_index(
            drop=True,
        )
    )

    # --------------------------------------------------------
    # Actual display order
    # --------------------------------------------------------

    ward_order = (
        ward_df["Ward"]
        .astype(str)
        .tolist()
    )

    # --------------------------------------------------------
    # Bars
    # --------------------------------------------------------

    bars = (
        alt.Chart(ward_df)
        .mark_bar(
            color=CHART_LABEL_COLOR
        )
        .encode(

            x=alt.X(
                "Ward:N",
                sort=ward_order,
                title="Ward",
                axis=alt.Axis(
                    labelAngle=0
                ),
            ),

            y=alt.Y(
                "Records:Q",
                title="Records",
            ),

            tooltip=[

                alt.Tooltip(
                    "Ward:N",
                    title="Ward",
                ),

                alt.Tooltip(
                    "Records:Q",
                    title="Records",
                    format=",",
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # Bold data labels
    # --------------------------------------------------------

    labels = (
        alt.Chart(ward_df)
        .mark_text(
            dy=-10,
            fontSize=13,
            fontWeight="bold",
            color=CHART_LABEL_COLOR,
        )
        .encode(

            x=alt.X(
                "Ward:N",
                sort=ward_order,
            ),

            y=alt.Y(
                "Records:Q",
            ),

            text=alt.Text(
                "Records:Q",
                format=",d",
            ),
        )
    )

    # --------------------------------------------------------
    # Final chart
    # --------------------------------------------------------

    chart = (
        bars + labels
    ).properties(
        height=450,
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# MAIN CHART RENDER FUNCTION
# ============================================================

def render_charts(df):

    st.subheader(
        "📈 Charts & Trends"
    )

    if df is None or df.empty:

        st.warning(
            "No records available for the selected filters."
        )

        return

    st.caption(
        "Month-wise, disease-wise, pathogen-wise, "
        "facility-wise and ward-wise analysis based "
        "on the currently selected Global Dashboard Filters."
    )

    # ========================================================
    # MONTH-WISE PROGRAMME TREND
    # ========================================================

    st.markdown(
        "### 🗓️ Month-wise Programme Trend"
    )

    if "Month" in df.columns:

        month_series = _valid_text_series(
            _clean_series(
                df,
                "Month",
            )
        )

        if not month_series.empty:

            normalized_months = (
                month_series
                .apply(
                    _normalize_month
                )
                .dropna()
            )

            if not normalized_months.empty:

                month_counts = (
                    normalized_months
                    .value_counts()
                    .rename_axis(
                        "Month"
                    )
                    .reset_index(
                        name="Records"
                    )
                )

                ordered_month_df = (
                    pd.DataFrame(
                        {
                            "Month":
                            CALENDAR_MONTHS
                        }
                    )
                )

                ordered_month_df = (
                    ordered_month_df
                    .merge(
                        month_counts,
                        on="Month",
                        how="left",
                    )
                )

                ordered_month_df[
                    "Records"
                ] = (
                    ordered_month_df[
                        "Records"
                    ]
                    .fillna(0)
                    .astype(int)
                )

                _render_month_chart(
                    ordered_month_df
                )

                st.dataframe(
                    ordered_month_df,
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "Month information is not available "
                    "for the selected records."
                )

        else:

            st.info(
                "Month information is not available "
                "for the selected records."
            )

    # ========================================================
    # MONTHLY DISEASE COMPARISON
    # ========================================================

    st.divider()

    st.markdown(
        "### 🦠 Monthly Disease Comparison"
    )

    if (
        "Month" in df.columns
        and "Disease" in df.columns
    ):

        temp = df[
            [
                "Month",
                "Disease",
            ]
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
            & temp["Month"]
            .str.lower()
            .ne("nan")
            & temp["Disease"]
            .str.lower()
            .ne("nan")
            & temp["Month"]
            .str.lower()
            .ne("none")
            & temp["Disease"]
            .str.lower()
            .ne("none")
        ]

        if not temp.empty:

            temp["Month"] = (
                temp["Month"]
                .apply(
                    _normalize_month
                )
            )

            temp = temp.dropna(
                subset=[
                    "Month"
                ]
            )

            if not temp.empty:

                disease_totals = (
                    temp["Disease"]
                    .value_counts()
                    .head(10)
                )

                selected_diseases = (
                    disease_totals
                    .index
                    .tolist()
                )

                temp = temp[
                    temp["Disease"].isin(
                        selected_diseases
                    )
                ]

                cross_tab = pd.crosstab(
                    temp["Month"],
                    temp["Disease"],
                )

                ordered_disease_df = (
                    pd.DataFrame(
                        index=CALENDAR_MONTHS
                    )
                )

                for disease in selected_diseases:

                    if disease in cross_tab.columns:

                        ordered_disease_df[
                            disease
                        ] = (
                            cross_tab[
                                disease
                            ]
                            .reindex(
                                CALENDAR_MONTHS,
                                fill_value=0,
                            )
                        )

                    else:

                        ordered_disease_df[
                            disease
                        ] = 0

                ordered_disease_df = (
                    ordered_disease_df
                    .fillna(0)
                    .astype(int)
                )

                _render_month_disease_chart(
                    ordered_disease_df,
                    selected_diseases,
                )

                st.caption(
                    "The chart displays the top 10 diseases "
                    "by total records within the selected filters. "
                    "Months are shown in calendar order. "
                    "Data labels show record counts at each point."
                )

                display_disease_df = (
                    ordered_disease_df
                    .reset_index()
                    .rename(
                        columns={
                            "index": "Month"
                        }
                    )
                )

                st.dataframe(
                    display_disease_df,
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "Disease/month information is not available "
                    "for the selected records."
                )

        else:

            st.info(
                "Disease/month information is not available "
                "for the selected records."
            )

    # ========================================================
    # DISEASE-WISE BURDEN
    # ========================================================

    st.divider()

    st.markdown(
        "### 🦠 Disease-wise Burden"
    )

    if "Disease" in df.columns:

        disease_series = _valid_text_series(
            _clean_series(
                df,
                "Disease",
            )
        )

        if not disease_series.empty:

            disease_counts = (
                disease_series
                .value_counts()
                .head(15)
                .rename_axis(
                    "Disease"
                )
                .reset_index(
                    name="Records"
                )
            )

            render_bar_chart(
                disease_counts
                .set_index(
                    "Disease"
                )["Records"],
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
    # TEST PERFORMED / PATHOGEN NAME
    # ========================================================

    st.divider()

    st.markdown(
        "### 🧪 Test Performed / Pathogen Name-wise Analysis"
    )

    pathogen_column = None

    pathogen_candidates = [
        "Test Performed Pathogen Name",
        "Pathogen Name",
        "Test Performed Pathogen",
        "Pathogen",
    ]

    for candidate in pathogen_candidates:

        if candidate in df.columns:

            pathogen_column = candidate

            break

    # --------------------------------------------------------
    # CASE 1: Combined field
    # --------------------------------------------------------

    if pathogen_column is not None:

        pathogen_series = _valid_text_series(
            _clean_series(
                df,
                pathogen_column,
            )
        )

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
                pathogen_counts
                .set_index(
                    "Test Performed Pathogen Name"
                )["Records"],
                use_container_width=True,
            )

            st.dataframe(
                pathogen_counts,
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                f"Pathogen analysis is based on the "
                f"'{pathogen_column}' field."
            )

        else:

            st.info(
                "Pathogen information is not available "
                "for the selected records."
            )

    # --------------------------------------------------------
    # CASE 2: Separate fields
    # --------------------------------------------------------

    elif (
        "Test Performed" in df.columns
        and "Pathogen Name" in df.columns
    ):

        pathogen_temp = df[
            [
                "Test Performed",
                "Pathogen Name",
            ]
        ].copy()

        pathogen_temp[
            "Test Performed"
        ] = _clean_series(
            pathogen_temp,
            "Test Performed",
        )

        pathogen_temp[
            "Pathogen Name"
        ] = _clean_series(
            pathogen_temp,
            "Pathogen Name",
        )

        pathogen_temp = pathogen_temp[
            pathogen_temp[
                "Test Performed"
            ].ne("")
            & pathogen_temp[
                "Pathogen Name"
            ].ne("")
            & pathogen_temp[
                "Test Performed"
            ]
            .str.lower()
            .ne("nan")
            & pathogen_temp[
                "Pathogen Name"
            ]
            .str.lower()
            .ne("nan")
            & pathogen_temp[
                "Test Performed"
            ]
            .str.lower()
            .ne("none")
            & pathogen_temp[
                "Pathogen Name"
            ]
            .str.lower()
            .ne("none")
        ]

        if not pathogen_temp.empty:

            pathogen_temp[
                "Test Performed Pathogen Name"
            ] = (
                pathogen_temp[
                    "Test Performed"
                ]
                + " - "
                + pathogen_temp[
                    "Pathogen Name"
                ]
            )

            pathogen_counts = (
                pathogen_temp[
                    "Test Performed Pathogen Name"
                ]
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
                pathogen_counts
                .set_index(
                    "Test Performed Pathogen Name"
                )["Records"],
                use_container_width=True,
            )

            st.dataframe(
                pathogen_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Test performed and pathogen information "
                "is not available for the selected records."
            )

    else:

        st.info(
            "Test Performed / Pathogen Name fields are not "
            "available in the current dataset."
        )

    # ========================================================
    # FACILITY-WISE BURDEN
    # ========================================================

    st.divider()

    st.markdown(
        "### 🏥 Facility-wise Burden"
    )

    if "Facility Name" in df.columns:

        facility_series = _valid_text_series(
            _clean_series(
                df,
                "Facility Name",
            )
        )

        if not facility_series.empty:

            facility_counts = (
                facility_series
                .value_counts()
                .head(20)
                .rename_axis(
                    "Facility"
                )
                .reset_index(
                    name="Records"
                )
            )

            render_bar_chart(
                facility_counts
                .set_index(
                    "Facility"
                )["Records"],
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
    # WARD-WISE BURDEN
    # ========================================================

    st.divider()

    st.markdown(
        "### 📍 Ward-wise Burden"
    )

    if "Ward Name" in df.columns:

        ward_series = _valid_text_series(
            _clean_series(
                df,
                "Ward Name",
            )
        )

        if not ward_series.empty:

            ward_counts = (
                ward_series
                .value_counts()
                .rename_axis(
                    "Ward"
                )
                .reset_index(
                    name="Records"
                )
            )

            ward_counts = _sort_wards(
                ward_counts,
                "Ward",
            )

            _render_ward_chart(
                ward_counts
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
    # OPD / IPD DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 🏨 OPD / IPD Distribution"
    )

    if "OPD/IPD" in df.columns:

        opd_series = _valid_text_series(
            _clean_series(
                df,
                "OPD/IPD",
            )
        )

        if not opd_series.empty:

            opd_counts = (
                opd_series
                .value_counts()
                .rename_axis(
                    "OPD/IPD"
                )
                .reset_index(
                    name="Records"
                )
            )

            render_bar_chart(
                opd_counts
                .set_index(
                    "OPD/IPD"
                )["Records"],
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
    # REPORTING DATE TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 📅 Reporting Date Trend"
    )

    if "Reporting Date" in df.columns:

        date_df = df[
            [
                "Reporting Date"
            ]
        ].copy()

        date_df[
            "Reporting Date"
        ] = pd.to_datetime(
            date_df[
                "Reporting Date"
            ],
            errors="coerce",
        )

        date_df = date_df.dropna(
            subset=[
                "Reporting Date"
            ]
        )

        if not date_df.empty:

            daily_counts = (
                date_df
                .assign(
                    Date=lambda x:
                    x[
                        "Reporting Date"
                    ].dt.normalize()
                )
                .groupby(
                    "Date"
                )
                .size()
                .rename(
                    "Records"
                )
            )

            render_line_chart(
                daily_counts,
                use_container_width=True,
            )

        else:

            st.info(
                "Valid reporting dates are not available."
            )

    # ========================================================
    # TREND SUMMARY
    # ========================================================

    st.divider()

    st.markdown(
        "### 📌 Trend Summary"
    )

    summary_columns = st.columns(4)

    # --------------------------------------------------------
    # Records
    # --------------------------------------------------------

    with summary_columns[0]:

        st.metric(
            "Records Analysed",
            f"{len(df):,}",
        )

    # --------------------------------------------------------
    # Diseases
    # --------------------------------------------------------

    with summary_columns[1]:

        if "Disease" in df.columns:

            disease_count = _valid_text_series(
                _clean_series(
                    df,
                    "Disease",
                )
            )

            st.metric(
                "Diseases",
                f"{disease_count.nunique():,}",
            )

        else:

            st.metric(
                "Diseases",
                "0",
            )

    # --------------------------------------------------------
    # Facilities
    # --------------------------------------------------------

    with summary_columns[2]:

        if "Facility Name" in df.columns:

            facility_count = _valid_text_series(
                _clean_series(
                    df,
                    "Facility Name",
                )
            )

            st.metric(
                "Facilities",
                f"{facility_count.nunique():,}",
            )

        else:

            st.metric(
                "Facilities",
                "0",
            )

    # --------------------------------------------------------
    # Wards
    # --------------------------------------------------------

    with summary_columns[3]:

        if "Ward Name" in df.columns:

            ward_count = _valid_text_series(
                _clean_series(
                    df,
                    "Ward Name",
                )
            )

            st.metric(
                "Wards",
                f"{ward_count.nunique():,}",
            )

        else:

            st.metric(
                "Wards",
                "0",
            )

