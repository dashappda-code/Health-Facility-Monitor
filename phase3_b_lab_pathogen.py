import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from chart_helpers import (
    render_bar_chart,
)


# ============================================================
# CONFIGURATION
# ============================================================

MONTH_ORDER = [
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


MONTH_LOOKUP = {
    "january": "Jan",
    "jan": "Jan",
    "01": "Jan",
    "1": "Jan",

    "february": "Feb",
    "feb": "Feb",
    "02": "Feb",
    "2": "Feb",

    "march": "Mar",
    "mar": "Mar",
    "03": "Mar",
    "3": "Mar",

    "april": "Apr",
    "apr": "Apr",
    "04": "Apr",
    "4": "Apr",

    "may": "May",
    "05": "May",
    "5": "May",

    "june": "Jun",
    "jun": "Jun",
    "06": "Jun",
    "6": "Jun",

    "july": "Jul",
    "jul": "Jul",
    "07": "Jul",
    "7": "Jul",

    "august": "Aug",
    "aug": "Aug",
    "08": "Aug",
    "8": "Aug",

    "september": "Sep",
    "sep": "Sep",
    "09": "Sep",
    "9": "Sep",

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


WARD_ORDER = [
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
# COLUMN HELPER
# ============================================================

def _find_column(df, candidates):

    if df is None or df.empty:
        return None

    normalized = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    # Exact match
    for candidate in candidates:

        key = str(candidate).strip().lower()

        if key in normalized:
            return normalized[key]

    # Partial match
    for col in df.columns:

        col_norm = (
            str(col)
            .strip()
            .lower()
        )

        for candidate in candidates:

            candidate_norm = (
                str(candidate)
                .strip()
                .lower()
            )

            if (
                candidate_norm in col_norm
                or col_norm in candidate_norm
            ):
                return col

    return None


# ============================================================
# TEXT CLEANING
# ============================================================

def _clean_text_series(series):

    if series is None:
        return pd.Series(dtype="object")

    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
        .replace(
            {
                "nan": "",
                "None": "",
                "none": "",
                "NaN": "",
            }
        )
    )


# ============================================================
# VALID VALUE MASK
# ============================================================

def _valid_value_mask(series):

    cleaned = _clean_text_series(series)

    return (
        cleaned.ne("")
        & cleaned.str.lower().ne("na")
        & cleaned.str.lower().ne("n/a")
        & cleaned.str.lower().ne("null")
        & cleaned.str.lower().ne("-")
    )


# ============================================================
# MONTH NORMALISATION
# ============================================================

def _normalise_month(value):
    """
    Safely normalise month values.

    Supports:
    - pandas Series
    - single values
    """

    # --------------------------------------------------------
    # IMPORTANT:
    # If a Series is supplied, process each value separately.
    # --------------------------------------------------------

    if isinstance(value, pd.Series):

        return value.apply(
            _normalise_month
        )

    # --------------------------------------------------------
    # Handle missing single value
    # --------------------------------------------------------

    if pd.isna(value):
        return ""

    # --------------------------------------------------------
    # Convert to text
    # --------------------------------------------------------

    text = str(value).strip()

    if not text:
        return ""

    lower = text.lower()

    # --------------------------------------------------------
    # Direct lookup
    # --------------------------------------------------------

    if lower in MONTH_LOOKUP:
        return MONTH_LOOKUP[lower]

    # --------------------------------------------------------
    # Handle common formats
    # --------------------------------------------------------

    # January 2026
    # January-2026
    # January/2026
    # Jan 2026
    # Jan-2026

    for key, month_name in MONTH_LOOKUP.items():

        if len(key) >= 3:

            if lower.startswith(
                key[:3]
            ):
                return month_name

    # --------------------------------------------------------
    # Handle date values
    # --------------------------------------------------------

    try:

        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if not pd.isna(parsed):

            return parsed.strftime("%b")

    except Exception:
        pass

    # --------------------------------------------------------
    # Numeric month fallback
    # --------------------------------------------------------

    try:

        numeric_value = int(
            float(text)
        )

        if 1 <= numeric_value <= 12:

            return MONTH_ORDER[
                numeric_value - 1
            ]

    except Exception:
        pass

    # --------------------------------------------------------
    # Final fallback
    # --------------------------------------------------------

    return text[:3].title()


# ============================================================
# MONTH ORDER VALUE
# ============================================================

def _month_order_value(value):

    try:

        return MONTH_ORDER.index(
            value
        )

    except ValueError:

        return 999


# ============================================================
# ORDER MONTH CHART DATA
# ============================================================

def _ordered_month_chart_data(
    chart_data
):

    if chart_data is None:
        return pd.DataFrame()

    if chart_data.empty:
        return chart_data.copy()

    plot_df = chart_data.copy()

    if "Month" not in plot_df.columns:
        return plot_df

    plot_df["Month"] = _normalise_month(
        plot_df["Month"]
    )

    plot_df["_MONTH_ORDER"] = (
        plot_df["Month"]
        .apply(
            _month_order_value
        )
    )

    plot_df = (
        plot_df
        .sort_values(
            "_MONTH_ORDER",
            kind="stable",
        )
        .drop(
            columns=[
                "_MONTH_ORDER"
            ],
            errors="ignore",
        )
        .reset_index(
            drop=True
        )
    )

    return plot_df


# ============================================================
# WARD NORMALISATION
# ============================================================

def _normalise_ward(value):
    """
    Safely normalise ward values.

    Supports:
    - pandas Series
    - single values
    """

    # --------------------------------------------------------
    # IMPORTANT:
    # Handle Series safely.
    # --------------------------------------------------------

    if isinstance(value, pd.Series):

        return value.apply(
            _normalise_ward
        )

    # --------------------------------------------------------
    # Missing value
    # --------------------------------------------------------

    if pd.isna(value):
        return ""

    text = str(value).strip()

    if not text:
        return ""

    # --------------------------------------------------------
    # Remove common ward prefixes
    # --------------------------------------------------------

    cleaned = (
        text
        .replace(
            "Ward",
            ""
        )
        .replace(
            "WARD",
            ""
        )
        .replace(
            "ward",
            ""
        )
        .replace(
            "-",
            " "
        )
        .strip()
    )

    if not cleaned:
        return ""

    first_token = (
        cleaned.split()[0]
    )

    if first_token.upper() in WARD_ORDER:

        return first_token.upper()

    return cleaned.upper()


# ============================================================
# WARD ORDER VALUE
# ============================================================

def _ward_order_value(value):

    try:

        return WARD_ORDER.index(
            value
        )

    except ValueError:

        return 999


# ============================================================
# COUNT TABLE
# ============================================================

def _count_table(
    df,
    column,
    output_name,
    include_empty=False,
):

    if df is None or df.empty:

        return pd.DataFrame(
            columns=[
                output_name,
                "Records",
            ]
        )

    if column not in df.columns:

        return pd.DataFrame(
            columns=[
                output_name,
                "Records",
            ]
        )

    temp = df.copy()

    temp[output_name] = (
        _clean_text_series(
            temp[column]
        )
    )

    if not include_empty:

        temp = temp[
            _valid_value_mask(
                temp[output_name]
            )
        ]

    if temp.empty:

        return pd.DataFrame(
            columns=[
                output_name,
                "Records",
            ]
        )

    result = (
        temp
        .groupby(
            output_name,
            dropna=False,
        )
        .size()
        .reset_index(
            name="Records"
        )
        .sort_values(
            "Records",
            ascending=False,
            kind="stable",
        )
        .reset_index(
            drop=True
        )
    )

    return result


# ============================================================
# PREPARE WORKING DATA
# ============================================================

def _prepare_working_data(df):

    if df is None:
        return pd.DataFrame()

    if df.empty:
        return df.copy()

    work_df = df.copy()

    # ========================================================
    # FIND SOURCE COLUMNS
    # ========================================================

    month_col = _find_column(
        work_df,
        [
            "Month",
            "Month Name",
            "Reporting Month",
            "Month-Year",
            "Month Year",
        ],
    )

    test_col = _find_column(
        work_df,
        [
            "Test Performed",
            "Test Performed Name",
            "Test",
            "Laboratory Test",
            "Test Name",
        ],
    )

    pathogen_col = _find_column(
        work_df,
        [
            "Pathogen Name",
            "Pathogen",
            "Detected Pathogen",
            "Organism",
        ],
    )

    facility_col = _find_column(
        work_df,
        [
            "Facility Name",
            "Facility",
            "Health Facility",
            "Hospital",
        ],
    )

    ward_col = _find_column(
        work_df,
        [
            "Ward",
            "Ward Name",
            "BMC Ward",
            "Administrative Ward",
        ],
    )

    # ========================================================
    # CREATE STANDARD INTERNAL COLUMNS
    # ========================================================

    if month_col is not None:

        work_df["_LAB_MONTH"] = (
            _normalise_month(
                work_df[month_col]
            )
        )

    else:

        work_df["_LAB_MONTH"] = ""

    if test_col is not None:

        work_df["_LAB_TEST"] = (
            _clean_text_series(
                work_df[test_col]
            )
        )

    else:

        work_df["_LAB_TEST"] = ""

    if pathogen_col is not None:

        work_df["_LAB_PATHOGEN"] = (
            _clean_text_series(
                work_df[pathogen_col]
            )
        )

    else:

        work_df["_LAB_PATHOGEN"] = ""

    if facility_col is not None:

        work_df["_LAB_FACILITY"] = (
            _clean_text_series(
                work_df[facility_col]
            )
        )

    else:

        work_df["_LAB_FACILITY"] = ""

    if ward_col is not None:

        work_df["_LAB_WARD"] = (
            _normalise_ward(
                work_df[ward_col]
            )
        )

    else:

        work_df["_LAB_WARD"] = ""

    return work_df


# ============================================================
# MONTH LINE CHART WITH DATA LABELS
# ============================================================

def _render_month_line_chart(
    chart_data,
    title,
    height=420,
):

    if (
        chart_data is None
        or chart_data.empty
    ):

        st.info(
            "No monthly data available for this analysis."
        )

        return

    plot_df = (
        _ordered_month_chart_data(
            chart_data
        )
    )

    if plot_df.empty:

        st.info(
            "No monthly data available for this analysis."
        )

        return

    plot_df["Records"] = (
        pd.to_numeric(
            plot_df["Records"],
            errors="coerce",
        )
        .fillna(0)
    )

    # ========================================================
    # FIGURE
    # ========================================================

    fig = go.Figure()

    # ========================================================
    # DATA LABELS
    # ========================================================

    label_values = (
        plot_df["Records"]
        .astype(int)
        .map(
            lambda value:
            f"{value:,}"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df[
                "Month"
            ].astype(str),

            y=plot_df[
                "Records"
            ],

            mode=(
                "lines+markers+text"
            ),

            text=label_values,

            textposition=(
                "top center"
            ),

            textfont=dict(
                size=12,
            ),

            cliponaxis=False,

            name="Records",

            hovertemplate=(
                "Month: %{x}<br>"
                "Records: %{y:,}"
                "<extra></extra>"
            ),
        )
    )

    # ========================================================
    # AXES
    # ========================================================

    fig.update_xaxes(
        title="Month",
        categoryorder="array",
        categoryarray=MONTH_ORDER,
    )

    fig.update_yaxes(
        title="Records",
        rangemode="tozero",
    )

    # ========================================================
    # LAYOUT
    # ========================================================

    fig.update_layout(
        title=title,

        height=height,

        margin=dict(
            l=45,
            r=30,
            t=70,
            b=55,
        ),

        hovermode="x unified",
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_lab_pathogen(df):

    st.header(
        "Laboratory & Pathogen Analysis"
    )

    st.caption(
        "Interactive analysis of laboratory tests "
        "and identified pathogens."
    )

    # ========================================================
    # PREPARE DATA
    # ========================================================

    work_df = _prepare_working_data(
        df
    )

    if work_df.empty:

        st.warning(
            "No data available for Laboratory & Pathogen Analysis."
        )

        return

    # ========================================================
    # COLUMN AVAILABILITY
    # ========================================================

    has_test = (
        "_LAB_TEST" in work_df.columns
        and _valid_value_mask(
            work_df["_LAB_TEST"]
        ).any()
    )

    has_pathogen = (
        "_LAB_PATHOGEN" in work_df.columns
        and _valid_value_mask(
            work_df["_LAB_PATHOGEN"]
        ).any()
    )

    has_month = (
        "_LAB_MONTH" in work_df.columns
        and _valid_value_mask(
            work_df["_LAB_MONTH"]
        ).any()
    )

    has_facility = (
        "_LAB_FACILITY" in work_df.columns
        and _valid_value_mask(
            work_df["_LAB_FACILITY"]
        ).any()
    )

    has_ward = (
        "_LAB_WARD" in work_df.columns
        and _valid_value_mask(
            work_df["_LAB_WARD"]
        ).any()
    )

    # ========================================================
    # 1. LABORATORY & PATHOGEN SUMMARY
    # ========================================================

    st.subheader(
        "Laboratory & Pathogen Summary"
    )

    total_records = len(
        work_df
    )

    pathogen_records = 0

    if has_pathogen:

        pathogen_records = int(
            _valid_value_mask(
                work_df["_LAB_PATHOGEN"]
            ).sum()
        )

    test_types = 0

    if has_test:

        test_types = int(
            work_df.loc[
                _valid_value_mask(
                    work_df["_LAB_TEST"]
                ),
                "_LAB_TEST",
            ]
            .nunique()
        )

    pathogen_types = 0

    if has_pathogen:

        pathogen_types = int(
            work_df.loc[
                _valid_value_mask(
                    work_df["_LAB_PATHOGEN"]
                ),
                "_LAB_PATHOGEN",
            ]
            .nunique()
        )

    top_test = "N/A"

    if has_test:

        test_table = _count_table(
            work_df,
            "_LAB_TEST",
            "Test Performed",
        )

        if not test_table.empty:

            top_test = str(
                test_table.iloc[0][
                    "Test Performed"
                ]
            )

    top_pathogen = "N/A"

    if has_pathogen:

        pathogen_table = _count_table(
            work_df,
            "_LAB_PATHOGEN",
            "Pathogen Name",
        )

        if not pathogen_table.empty:

            top_pathogen = str(
                pathogen_table.iloc[0][
                    "Pathogen Name"
                ]
            )

    kpi1, kpi2, kpi3 = st.columns(
        3
    )

    kpi4, kpi5, kpi6 = st.columns(
        3
    )

    kpi1.metric(
        "Total Tests / Records",
        f"{total_records:,}",
    )

    kpi2.metric(
        "Pathogen Records",
        f"{pathogen_records:,}",
    )

    kpi3.metric(
        "Test Types",
        f"{test_types:,}",
    )

    kpi4.metric(
        "Pathogen Types",
        f"{pathogen_types:,}",
    )

    kpi5.metric(
        "Top Test",
        top_test,
    )

    kpi6.metric(
        "Top Pathogen",
        top_pathogen,
    )

    st.divider()

    # ========================================================
    # 2. TEST PERFORMED-WISE ANALYSIS
    # ========================================================

    st.subheader(
        "Test Performed-wise Analysis"
    )

    if has_test:

        test_table = _count_table(
            work_df,
            "_LAB_TEST",
            "Test Performed",
        )

        if not test_table.empty:

            render_bar_chart(
                test_table,
                x_col="Test Performed",
                y_col="Records",
                title=(
                    "Laboratory Tests by Test Performed"
                ),
            )

            st.dataframe(
                test_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No valid Test Performed data available."
            )

    else:

        st.info(
            "Test Performed column was not found."
        )

    st.divider()

    # ========================================================
    # 3. PATHOGEN NAME-WISE ANALYSIS
    # ========================================================

    st.subheader(
        "Pathogen Name-wise Analysis"
    )

    if has_pathogen:

        pathogen_table = _count_table(
            work_df,
            "_LAB_PATHOGEN",
            "Pathogen Name",
        )

        if not pathogen_table.empty:

            render_bar_chart(
                pathogen_table,
                x_col="Pathogen Name",
                y_col="Records",
                title=(
                    "Pathogen Distribution"
                ),
            )

            st.dataframe(
                pathogen_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No valid Pathogen Name data available."
            )

    else:

        st.info(
            "Pathogen Name column was not found."
        )

    st.divider()

    # ========================================================
    # 4. TEST × PATHOGEN ANALYSIS
    # ========================================================

    st.subheader(
        "Test × Pathogen Analysis"
    )

    if has_test and has_pathogen:

        cross_df = work_df[
            _valid_value_mask(
                work_df["_LAB_TEST"]
            )
            &
            _valid_value_mask(
                work_df["_LAB_PATHOGEN"]
            )
        ].copy()

        if not cross_df.empty:

            cross_table = (
                cross_df
                .groupby(
                    [
                        "_LAB_TEST",
                        "_LAB_PATHOGEN",
                    ]
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .rename(
                    columns={
                        "_LAB_TEST":
                        "Test Performed",

                        "_LAB_PATHOGEN":
                        "Pathogen Name",
                    }
                )
                .sort_values(
                    "Records",
                    ascending=False,
                    kind="stable",
                )
                .reset_index(
                    drop=True
                )
            )

            st.dataframe(
                cross_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No records are available for Test × Pathogen analysis."
            )

    else:

        st.info(
            "Both Test Performed and Pathogen Name are required "
            "for Test × Pathogen analysis."
        )

    st.divider()

    # ========================================================
    # 5. MONTH-WISE LABORATORY TEST TREND
    # ========================================================

    st.subheader(
        "Month-wise Laboratory Test Trend"
    )

    if has_month:

        month_test_df = work_df[
            _valid_value_mask(
                work_df["_LAB_MONTH"]
            )
            &
            _valid_value_mask(
                work_df["_LAB_TEST"]
            )
        ].copy()

        if not month_test_df.empty:

            month_test = (
                month_test_df
                .groupby(
                    "_LAB_MONTH"
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .rename(
                    columns={
                        "_LAB_MONTH":
                        "Month"
                    }
                )
            )

            _render_month_line_chart(
                month_test,
                "Monthly Laboratory Test Trend",
                height=420,
            )

        else:

            st.info(
                "No monthly laboratory test data available."
            )

    else:

        st.info(
            "Month information was not found."
        )

    st.divider()

    # ========================================================
    # 6. MONTH-WISE PATHOGEN TREND
    # ========================================================

    st.subheader(
        "Month-wise Pathogen Trend"
    )

    if has_month and has_pathogen:

        month_pathogen_df = work_df[
            _valid_value_mask(
                work_df["_LAB_MONTH"]
            )
            &
            _valid_value_mask(
                work_df["_LAB_PATHOGEN"]
            )
        ].copy()

        if not month_pathogen_df.empty:

            month_pathogen = (
                month_pathogen_df
                .groupby(
                    "_LAB_MONTH"
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .rename(
                    columns={
                        "_LAB_MONTH":
                        "Month"
                    }
                )
            )

            _render_month_line_chart(
                month_pathogen,
                "Monthly Pathogen Trend",
                height=420,
            )

        else:

            st.info(
                "No monthly pathogen data available."
            )

    else:

        st.info(
            "Month and Pathogen Name information "
            "are required for this analysis."
        )

    st.divider()

    # ========================================================
    # 7. SELECTED LABORATORY ITEM TREND
    # ========================================================

    st.subheader(
        "Selected Laboratory Item Trend"
    )

    available_options = []

    if has_test:

        available_options.append(
            "Test Performed"
        )

    if has_pathogen:

        available_options.append(
            "Pathogen Name"
        )

    if not available_options:

        st.info(
            "No laboratory or pathogen fields are available."
        )

    elif not has_month:

        st.info(
            "Month information is required for trend analysis."
        )

    else:

        selected_label = st.selectbox(
            "Select Item Type",
            available_options,
            key="lab_selected_item_type",
        )

        if selected_label == "Test Performed":

            source_column = "_LAB_TEST"

        else:

            source_column = "_LAB_PATHOGEN"

        selected_items = (
            work_df.loc[
                _valid_value_mask(
                    work_df[source_column]
                ),
                source_column,
            ]
            .drop_duplicates()
            .tolist()
        )

        selected_items = [
            str(item)
            for item in selected_items
            if str(item).strip()
        ]

        selected_items = sorted(
            selected_items,
            key=lambda x: x.lower(),
        )

        if selected_items:

            default_items = selected_items[
                :5
            ]

            selected_values = st.multiselect(
                f"Select {selected_label}",
                selected_items,
                default=default_items,
                key="lab_selected_items",
            )

            if selected_values:

                selected_df = work_df[
                    _valid_value_mask(
                        work_df["_LAB_MONTH"]
                    )
                    &
                    work_df[
                        source_column
                    ].isin(
                        selected_values
                    )
                ].copy()

                if not selected_df.empty:

                    trend_df = (
                        selected_df
                        .groupby(
                            [
                                "_LAB_MONTH",
                                source_column,
                            ]
                        )
                        .size()
                        .reset_index(
                            name="Records"
                        )
                        .rename(
                            columns={
                                "_LAB_MONTH":
                                "Month",

                                source_column:
                                "Selected Item",
                            }
                        )
                    )

                    trend_df["Month"] = pd.Categorical(
                        trend_df["Month"],
                        categories=MONTH_ORDER,
                        ordered=True,
                    )

                    trend_df = (
                        trend_df
                        .sort_values(
                            [
                                "Month",
                                "Selected Item",
                            ],
                            kind="stable",
                        )
                        .reset_index(
                            drop=True
                        )
                    )

                    # ====================================================
                    # MULTI-TRACE FIGURE
                    # ====================================================

                    fig = go.Figure()

                    for item_name in selected_values:

                        item_df = trend_df[
                            trend_df[
                                "Selected Item"
                            ].astype(str)
                            == str(item_name)
                        ].copy()

                        if item_df.empty:
                            continue

                        # ----------------------------------------------
                        # Reindex all months
                        # ----------------------------------------------

                        item_df = (
                            item_df
                            .set_index(
                                "Month"
                            )
                            .reindex(
                                MONTH_ORDER
                            )
                            .reset_index()
                        )

                        item_df[
                            "Selected Item"
                        ] = str(item_name)

                        item_df[
                            "Records"
                        ] = (
                            pd.to_numeric(
                                item_df[
                                    "Records"
                                ],
                                errors="coerce",
                            )
                            .fillna(0)
                        )

                        # ----------------------------------------------
                        # Visible labels
                        #
                        # Zero values intentionally have blank labels
                        # to prevent unnecessary chart clutter.
                        # ----------------------------------------------

                        label_values = (
                            item_df[
                                "Records"
                            ]
                            .astype(int)
                            .map(
                                lambda value:
                                f"{value:,}"
                                if value != 0
                                else ""
                            )
                        )

                        fig.add_trace(
                            go.Scatter(
                                x=item_df[
                                    "Month"
                                ].astype(str),

                                y=item_df[
                                    "Records"
                                ],

                                mode=(
                                    "lines+markers+text"
                                ),

                                text=label_values,

                                textposition=(
                                    "top center"
                                ),

                                textfont=dict(
                                    size=10,
                                ),

                                cliponaxis=False,

                                name=str(
                                    item_name
                                ),

                                hovertemplate=(
                                    "Month: %{x}<br>"
                                    "Records: %{y:,}<br>"
                                    f"Item: {item_name}"
                                    "<extra></extra>"
                                ),
                            )
                        )

                    # ====================================================
                    # AXES
                    # ====================================================

                    fig.update_xaxes(
                        title="Month",
                        categoryorder="array",
                        categoryarray=MONTH_ORDER,
                    )

                    fig.update_yaxes(
                        title="Records",
                        rangemode="tozero",
                    )

                    # ====================================================
                    # LAYOUT
                    # ====================================================

                    fig.update_layout(
                        title=(
                            f"Monthly Trend — "
                            f"{selected_label}"
                        ),

                        height=470,

                        margin=dict(
                            l=45,
                            r=30,
                            t=80,
                            b=55,
                        ),

                        hovermode="x unified",

                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="left",
                            x=0,
                        ),
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                    )

                else:

                    st.info(
                        "No records available for the selected items."
                    )

            else:

                st.info(
                    f"Select at least one "
                    f"{selected_label.lower()} "
                    "to display the trend."
                )

        else:

            st.info(
                f"No valid "
                f"{selected_label.lower()} "
                "data available."
            )

    st.divider()

    # ========================================================
    # 8. FACILITY-WISE LABORATORY ANALYSIS
    # ========================================================

    st.subheader(
        "Facility-wise Laboratory Analysis"
    )

    if has_facility and has_test:

        facility_test_df = work_df[
            _valid_value_mask(
                work_df["_LAB_FACILITY"]
            )
            &
            _valid_value_mask(
                work_df["_LAB_TEST"]
            )
        ].copy()

        if not facility_test_df.empty:

            facility_table = (
                facility_test_df
                .groupby(
                    "_LAB_FACILITY"
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .rename(
                    columns={
                        "_LAB_FACILITY":
                        "Facility Name"
                    }
                )
                .sort_values(
                    "Records",
                    ascending=False,
                    kind="stable",
                )
                .reset_index(
                    drop=True
                )
            )

            render_bar_chart(
                facility_table,
                x_col="Facility Name",
                y_col="Records",
                title=(
                    "Laboratory Records by Facility"
                ),
            )

            st.dataframe(
                facility_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No facility-wise laboratory records available."
            )

    else:

        st.info(
            "Facility and Test Performed information "
            "are required for facility-wise analysis."
        )

    st.divider()

    # ========================================================
    # 9. WARD-WISE LABORATORY ANALYSIS
    # ========================================================

    st.subheader(
        "Ward-wise Laboratory Analysis"
    )

    if has_ward and has_test:

        ward_test_df = work_df[
            _valid_value_mask(
                work_df["_LAB_WARD"]
            )
            &
            _valid_value_mask(
                work_df["_LAB_TEST"]
            )
        ].copy()

        if not ward_test_df.empty:

            ward_table = (
                ward_test_df
                .groupby(
                    "_LAB_WARD"
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .rename(
                    columns={
                        "_LAB_WARD":
                        "Ward"
                    }
                )
            )

            ward_table[
                "_WARD_ORDER"
            ] = (
                ward_table[
                    "Ward"
                ]
                .apply(
                    _ward_order_value
                )
            )

            ward_table = (
                ward_table
                .sort_values(
                    "_WARD_ORDER",
                    kind="stable",
                )
                .drop(
                    columns=[
                        "_WARD_ORDER"
                    ]
                )
                .reset_index(
                    drop=True
                )
            )

            render_bar_chart(
                ward_table,
                x_col="Ward",
                y_col="Records",
                title=(
                    "Laboratory Records by Ward"
                ),
            )

            st.dataframe(
                ward_table,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No ward-wise laboratory records available."
            )

    else:

        st.info(
            "Ward and Test Performed information "
            "are required for ward-wise analysis."
        )

    st.divider()

    # ========================================================
    # 10. DETAILED LABORATORY RECORDS
    # ========================================================

    st.subheader(
        "Detailed Laboratory Records"
    )

    detail_columns = []

    preferred_columns = [
        "Facility Name",
        "Ward",
        "Test Performed",
        "Pathogen Name",
        "Month",
        "Date",
        "Age",
        "Gender",
    ]

    for col in preferred_columns:

        actual_col = _find_column(
            work_df,
            [col],
        )

        if (
            actual_col is not None
            and actual_col not in detail_columns
        ):

            detail_columns.append(
                actual_col
            )

    if not detail_columns:

        detail_columns = [
            col
            for col in work_df.columns
            if not str(col).startswith(
                "_"
            )
        ]

    detail_df = work_df[
        detail_columns
    ].copy()

    st.dataframe(
        detail_df,
        use_container_width=True,
        hide_index=True,
    )
