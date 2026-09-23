import pandas as pd
import streamlit as st

from chart_helpers import (
    render_bar_chart,
    render_line_chart,
)


# ============================================================
# CONSTANTS
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
    "jan": "Jan",
    "january": "Jan",
    "feb": "Feb",
    "february": "Feb",
    "mar": "Mar",
    "march": "Mar",
    "apr": "Apr",
    "april": "Apr",
    "may": "May",
    "jun": "Jun",
    "june": "Jun",
    "jul": "Jul",
    "july": "Jul",
    "aug": "Aug",
    "august": "Aug",
    "sep": "Sep",
    "sept": "Sep",
    "september": "Sep",
    "oct": "Oct",
    "october": "Oct",
    "nov": "Nov",
    "november": "Nov",
    "dec": "Dec",
    "december": "Dec",
}


# IMPORTANT:
# Keep Ward ordering exactly as currently working.
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
# BASIC HELPERS
# ============================================================

def _find_column(df, candidates):
    """
    Return the first matching column from candidates.
    Matching is case-insensitive and whitespace-insensitive.
    """

    if df is None or df.empty:
        return None

    column_map = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower()

        if key in column_map:
            return column_map[key]

    return None


def _clean_text_series(series):
    """
    Clean text values safely.
    """

    if series is None:
        return pd.Series(dtype="string")

    return (
        series
        .astype("string")
        .fillna("")
        .str.strip()
    )


def _valid_value_mask(series):
    """
    Identify valid non-empty values.
    """

    cleaned = _clean_text_series(series)

    return (
        cleaned.ne("")
        & cleaned.ne("nan")
        & cleaned.ne("NaN")
        & cleaned.ne("None")
        & cleaned.ne("NaT")
    )


def _prepare_working_data(df):
    """
    Prepare a safe working copy without changing
    the original dataframe.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    working = df.copy()

    # --------------------------------------------------------
    # Standardise commonly used columns
    # --------------------------------------------------------

    if "Test Performed" in working.columns:
        working["Test Performed"] = _clean_text_series(
            working["Test Performed"]
        )

    if "Pathogen Name" in working.columns:
        working["Pathogen Name"] = _clean_text_series(
            working["Pathogen Name"]
        )

    if "Month" in working.columns:
        working["Month"] = _clean_text_series(
            working["Month"]
        )

    if "Year" in working.columns:
        working["Year"] = _clean_text_series(
            working["Year"]
        )

    if "Facility Name" in working.columns:
        working["Facility Name"] = _clean_text_series(
            working["Facility Name"]
        )

    if "Facility Name Lform" in working.columns:
        working["Facility Name Lform"] = _clean_text_series(
            working["Facility Name Lform"]
        )

    if "Ward Name" in working.columns:
        working["Ward Name"] = _clean_text_series(
            working["Ward Name"]
        )

    if "Ward" in working.columns:
        working["Ward"] = _clean_text_series(
            working["Ward"]
        )

    return working


# ============================================================
# MONTH HELPERS
# ============================================================

def _normalise_month(value):
    """
    Convert month values to standard Jan-Dec labels.

    Handles:
        Jan
        January
        JAN
        1
        01
        1.0
        etc.
    """

    if pd.isna(value):
        return ""

    text = str(value).strip()

    if not text:
        return ""

    # --------------------------------------------------------
    # Numeric month
    # --------------------------------------------------------

    try:
        numeric = float(text)

        if numeric.is_integer():
            numeric = int(numeric)

            if 1 <= numeric <= 12:
                return MONTH_ORDER[numeric - 1]

    except Exception:
        pass

    # --------------------------------------------------------
    # Text month
    # --------------------------------------------------------

    key = text.lower()

    if key in MONTH_LOOKUP:
        return MONTH_LOOKUP[key]

    # Handle first three characters
    short_key = key[:3]

    if short_key in MONTH_LOOKUP:
        return MONTH_LOOKUP[short_key]

    return text


def _month_order_value(value):
    """
    Return numeric month order.

    Jan = 1
    Feb = 2
    ...
    Dec = 12
    Unknown = 999
    """

    month = _normalise_month(value)

    try:
        return MONTH_ORDER.index(month) + 1
    except ValueError:
        return 999


def _prepare_month_series(df):
    """
    Prepare month-wise counts in strict Jan-Dec order.
    """

    if (
        df is None
        or df.empty
        or "Month" not in df.columns
    ):
        return pd.DataFrame()

    temp = df.copy()

    temp["Month"] = (
        temp["Month"]
        .map(_normalise_month)
    )

    temp = temp[
        temp["Month"].ne("")
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    monthly = (
        temp["Month"]
        .value_counts()
        .rename_axis("Month")
        .reset_index(name="Records")
    )

    monthly["_Month_Order"] = (
        monthly["Month"]
        .map(_month_order_value)
    )

    monthly = (
        monthly
        .sort_values(
            "_Month_Order",
            ascending=True,
            kind="stable",
        )
        .drop(columns=["_Month_Order"])
        .reset_index(drop=True)
    )

    return monthly


def _ordered_month_chart_data(month_df):
    """
    Final hard-fix for month charts.

    This follows the same approach used in phase3_charts.py:
    explicit month ordering + categorical ordering.

    Only months available in the selected data are displayed.
    """

    if (
        month_df is None
        or month_df.empty
        or "Month" not in month_df.columns
        or "Records" not in month_df.columns
    ):
        return pd.DataFrame()

    temp = month_df.copy()

    # --------------------------------------------------------
    # Standardise month names
    # --------------------------------------------------------

    temp["Month"] = (
        temp["Month"]
        .map(_normalise_month)
    )

    temp = temp[
        temp["Month"].ne("")
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # Explicit Jan-Dec numeric order
    # --------------------------------------------------------

    temp["_Month_Order"] = (
        temp["Month"]
        .map(_month_order_value)
    )

    temp = (
        temp
        .sort_values(
            "_Month_Order",
            ascending=True,
            kind="stable",
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Make Month an ordered categorical variable.
    # This prevents chart helper from falling back
    # to alphabetical ordering.
    # --------------------------------------------------------

    temp["Month"] = pd.Categorical(
        temp["Month"],
        categories=MONTH_ORDER,
        ordered=True,
    )

    temp = (
        temp
        .sort_values(
            "Month",
            ascending=True,
            kind="stable",
        )
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # Return Month as ordered categorical index
    # --------------------------------------------------------

    chart_data = (
        temp[
            [
                "Month",
                "Records",
            ]
        ]
        .set_index("Month")
    )

    return chart_data


# ============================================================
# WARD HELPERS
# ============================================================

def _normalise_ward(value):
    """
    Standardise ward labels.

    IMPORTANT:
    This is the existing working A-T logic.
    Do not change the ordering behaviour.
    """

    if pd.isna(value):
        return ""

    text = str(value).strip().upper()

    if not text:
        return ""

    # Remove common prefixes
    if text.startswith("WARD "):
        text = text.replace("WARD ", "", 1).strip()

    if text.startswith("W"):
        possible = text[1:].strip()

        if possible in WARD_ORDER:
            return possible

    if text in WARD_ORDER:
        return text

    return text


def _ward_order_value(value):
    """
    Return A-T ward order.
    """

    ward = _normalise_ward(value)

    try:
        return WARD_ORDER.index(ward) + 1
    except ValueError:
        return 999


# ============================================================
# COUNT TABLE
# ============================================================

def _count_table(
    df,
    column,
    output_name,
    order_type=None,
):
    """
    Create a count table.

    order_type:
        None
        month
        ward
    """

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return pd.DataFrame()

    series = _clean_text_series(
        df[column]
    )

    valid = series[
        series.ne("")
        & series.ne("nan")
        & series.ne("NaN")
        & series.ne("None")
        & series.ne("NaT")
    ]

    if valid.empty:
        return pd.DataFrame()

    result = (
        valid
        .value_counts()
        .rename_axis(output_name)
        .reset_index(name="Records")
    )

    # ========================================================
    # MONTH ORDER
    # ========================================================

    if order_type == "month":

        result[output_name] = (
            result[output_name]
            .map(_normalise_month)
        )

        result["_Order"] = (
            result[output_name]
            .map(_month_order_value)
        )

        result = (
            result
            .sort_values(
                "_Order",
                ascending=True,
                kind="stable",
            )
            .drop(columns=["_Order"])
            .reset_index(drop=True)
        )

    # ========================================================
    # WARD ORDER
    # ========================================================

    elif order_type == "ward":

        result[output_name] = (
            result[output_name]
            .map(_normalise_ward)
        )

        result["_Order"] = (
            result[output_name]
            .map(_ward_order_value)
        )

        result = (
            result
            .sort_values(
                "_Order",
                ascending=True,
                kind="stable",
            )
            .drop(columns=["_Order"])
            .reset_index(drop=True)
        )

    return result


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_lab_pathogen(filtered_df):

    st.subheader(
        "Laboratory & Pathogen Analysis"
    )

    st.caption(
        "Laboratory testing and pathogen analysis "
        "based on the currently selected Global Dashboard Filters."
    )

    # ========================================================
    # DATA PREPARATION
    # ========================================================

    laboratory_records = _prepare_working_data(
        filtered_df
    )

    if laboratory_records.empty:
        st.warning(
            "No laboratory or pathogen records are available "
            "for the selected filters."
        )
        return

    # ========================================================
    # COLUMN DETECTION
    # ========================================================

    test_col = _find_column(
        laboratory_records,
        [
            "Test Performed",
            "Test performed",
            "Test",
        ],
    )

    pathogen_col = _find_column(
        laboratory_records,
        [
            "Pathogen Name",
            "Pathogen",
        ],
    )

    facility_col = _find_column(
        laboratory_records,
        [
            "Facility Name",
            "Facility Name Lform",
        ],
    )

    ward_col = _find_column(
        laboratory_records,
        [
            "Ward Name",
            "Ward",
        ],
    )

    month_col = _find_column(
        laboratory_records,
        [
            "Month",
        ],
    )

    year_col = _find_column(
        laboratory_records,
        [
            "Year",
        ],
    )

    # ========================================================
    # 1. SUMMARY KPIs
    # ========================================================

    st.markdown(
        "### Laboratory & Pathogen Summary"
    )

    total_records = len(
        laboratory_records
    )

    pathogen_records = 0
    pathogen_types = 0
    test_types = 0

    top_test = "Not available"
    top_pathogen = "Not available"

    # --------------------------------------------------------
    # Test information
    # --------------------------------------------------------

    if test_col is not None:

        valid_tests = _clean_text_series(
            laboratory_records[test_col]
        )

        valid_tests = valid_tests[
            valid_tests.ne("")
            & valid_tests.ne("nan")
            & valid_tests.ne("None")
        ]

        if not valid_tests.empty:

            test_types = valid_tests.nunique()

            test_counts = (
                valid_tests
                .value_counts()
            )

            if not test_counts.empty:
                top_test = str(
                    test_counts.index[0]
                )

    # --------------------------------------------------------
    # Pathogen information
    # --------------------------------------------------------

    if pathogen_col is not None:

        valid_pathogens = _clean_text_series(
            laboratory_records[pathogen_col]
        )

        valid_pathogens = valid_pathogens[
            valid_pathogens.ne("")
            & valid_pathogens.ne("nan")
            & valid_pathogens.ne("None")
        ]

        pathogen_records = len(
            valid_pathogens
        )

        pathogen_types = (
            valid_pathogens.nunique()
        )

        if not valid_pathogens.empty:

            pathogen_counts = (
                valid_pathogens
                .value_counts()
            )

            if not pathogen_counts.empty:
                top_pathogen = str(
                    pathogen_counts.index[0]
                )

    kpi_cols = st.columns(6)

    with kpi_cols[0]:
        st.metric(
            "Total Records",
            f"{total_records:,}",
        )

    with kpi_cols[1]:
        st.metric(
            "Pathogen Records",
            f"{pathogen_records:,}",
        )

    with kpi_cols[2]:
        st.metric(
            "Test Types",
            f"{test_types:,}",
        )

    with kpi_cols[3]:
        st.metric(
            "Pathogen Types",
            f"{pathogen_types:,}",
        )

    with kpi_cols[4]:
        st.metric(
            "Top Test",
            top_test,
        )

    with kpi_cols[5]:
        st.metric(
            "Top Pathogen",
            top_pathogen,
        )

    st.divider()

    # ========================================================
    # 2. TEST PERFORMED-WISE ANALYSIS
    # ========================================================

    st.markdown(
        "### 1. Test Performed-wise Analysis"
    )

    if test_col is not None:

        test_table = _count_table(
            laboratory_records,
            test_col,
            "Test Performed",
        )

        if not test_table.empty:

            chart_table = (
                test_table
                .head(20)
                .sort_values(
                    "Records",
                    ascending=True,
                )
            )

            render_bar_chart(
                chart_table
                .set_index("Test Performed")[
                    "Records"
                ],
                use_container_width=True,
            )

            st.dataframe(
                test_table,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Test performed information is not available."
            )

    else:
        st.info(
            "The 'Test Performed' column is not available "
            "in the selected dataset."
        )

    # ========================================================
    # 3. PATHOGEN NAME-WISE ANALYSIS
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. Pathogen Name-wise Analysis"
    )

    if pathogen_col is not None:

        pathogen_table = _count_table(
            laboratory_records,
            pathogen_col,
            "Pathogen Name",
        )

        if not pathogen_table.empty:

            chart_table = (
                pathogen_table
                .head(20)
                .sort_values(
                    "Records",
                    ascending=True,
                )
            )

            render_bar_chart(
                chart_table
                .set_index("Pathogen Name")[
                    "Records"
                ],
                use_container_width=True,
            )

            st.dataframe(
                pathogen_table,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Pathogen information is not available."
            )

    else:
        st.info(
            "The 'Pathogen Name' column is not available "
            "in the selected dataset."
        )

    # ========================================================
    # 4. TEST × PATHOGEN ANALYSIS
    # ========================================================

    st.divider()

    st.markdown(
        "### 3. Test × Pathogen Analysis"
    )

    if (
        test_col is not None
        and pathogen_col is not None
    ):

        temp = laboratory_records[
            [
                test_col,
                pathogen_col,
            ]
        ].copy()

        temp[test_col] = _clean_text_series(
            temp[test_col]
        )

        temp[pathogen_col] = _clean_text_series(
            temp[pathogen_col]
        )

        temp = temp[
            temp[test_col].ne("")
            & temp[pathogen_col].ne("")
        ].copy()

        if not temp.empty:

            cross_table = pd.crosstab(
                temp[test_col],
                temp[pathogen_col],
            )

            # Keep top 15 tests by total records
            test_totals = (
                cross_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .head(15)
            )

            cross_table = cross_table.loc[
                test_totals.index
            ]

            # Keep top 15 pathogens
            pathogen_totals = (
                cross_table
                .sum(axis=0)
                .sort_values(
                    ascending=False
                )
                .head(15)
            )

            cross_table = cross_table[
                pathogen_totals.index
            ]

            st.dataframe(
                cross_table,
                use_container_width=True,
            )

        else:
            st.info(
                "Test and pathogen combination data "
                "is not available."
            )

    else:
        st.info(
            "Test × Pathogen analysis requires both "
            "'Test Performed' and 'Pathogen Name'."
        )

    # ========================================================
    # 5. MONTH-WISE LABORATORY TEST TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 4. Month-wise Laboratory Test Trend"
    )

    if (
        test_col is not None
        and month_col is not None
    ):

        temp = laboratory_records[
            [
                month_col,
                test_col,
            ]
        ].copy()

        temp["Month"] = (
            temp[month_col]
            .map(_normalise_month)
        )

        temp["Test"] = _clean_text_series(
            temp[test_col]
        )

        temp = temp[
            temp["Month"].ne("")
            & temp["Test"].ne("")
        ].copy()

        if not temp.empty:

            # ------------------------------------------------
            # Count test records by month
            # ------------------------------------------------

            month_test = (
                temp.groupby(
                    "Month",
                    sort=False,
                )
                .size()
                .rename("Records")
                .reset_index()
            )

            # ------------------------------------------------
            # HARD JAN-DEC ORDER FIX
            # ------------------------------------------------

            chart_data = _ordered_month_chart_data(
                month_test
            )

            if not chart_data.empty:

                render_line_chart(
                    chart_data,
                    height=400,
                    use_container_width=True,
                )

                display_table = (
                    chart_data
                    .reset_index()
                )

                st.dataframe(
                    display_table,
                    use_container_width=True,
                    hide_index=True,
                )

        else:
            st.info(
                "Month-wise laboratory test data "
                "is not available."
            )

    else:
        st.info(
            "Month-wise laboratory test trend requires "
            "'Month' and 'Test Performed'."
        )

    # ========================================================
    # 6. MONTH-WISE PATHOGEN TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 5. Month-wise Pathogen Trend"
    )

    if (
        pathogen_col is not None
        and month_col is not None
    ):

        temp = laboratory_records[
            [
                month_col,
                pathogen_col,
            ]
        ].copy()

        temp["Month"] = (
            temp[month_col]
            .map(_normalise_month)
        )

        temp["Pathogen"] = _clean_text_series(
            temp[pathogen_col]
        )

        temp = temp[
            temp["Month"].ne("")
            & temp["Pathogen"].ne("")
        ].copy()

        if not temp.empty:

            pathogen_month = (
                temp.groupby(
                    "Month",
                    sort=False,
                )
                .size()
                .rename("Records")
                .reset_index()
            )

            # ------------------------------------------------
            # HARD JAN-DEC ORDER FIX
            # ------------------------------------------------

            chart_data = _ordered_month_chart_data(
                pathogen_month
            )

            if not chart_data.empty:

                render_line_chart(
                    chart_data,
                    height=400,
                    use_container_width=True,
                )

                display_table = (
                    chart_data
                    .reset_index()
                )

                st.dataframe(
                    display_table,
                    use_container_width=True,
                    hide_index=True,
                )

        else:
            st.info(
                "Month-wise pathogen data "
                "is not available."
            )

    else:
        st.info(
            "Month-wise pathogen trend requires "
            "'Month' and 'Pathogen Name'."
        )

    # ========================================================
    # 7. SELECTED LABORATORY ITEM TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 6. Selected Laboratory Item Trend"
    )

    available_items = []

    if test_col is not None:
        available_items.append(
            "Test Performed"
        )

    if pathogen_col is not None:
        available_items.append(
            "Pathogen Name"
        )

    if (
        month_col is not None
        and available_items
    ):

        selected_item = st.selectbox(
            "Select Laboratory Item",
            available_items,
            key="lab_pathogen_selected_item",
        )

        if selected_item == "Test Performed":
            selected_column = test_col
            selected_label = "Test Performed"

        else:
            selected_column = pathogen_col
            selected_label = "Pathogen Name"

        temp = laboratory_records[
            [
                month_col,
                selected_column,
            ]
        ].copy()

        temp["Month"] = (
            temp[month_col]
            .map(_normalise_month)
        )

        temp["Selected Item"] = _clean_text_series(
            temp[selected_column]
        )

        temp = temp[
            temp["Month"].ne("")
            & temp["Selected Item"].ne("")
        ].copy()

        if not temp.empty:

            # ------------------------------------------------
            # Select top items based on current filters
            # ------------------------------------------------

            item_totals = (
                temp["Selected Item"]
                .value_counts()
                .head(10)
            )

            selected_items = (
                item_totals
                .index
                .tolist()
            )

            item_month = (
                temp[
                    temp["Selected Item"].isin(
                        selected_items
                    )
                ]
                .groupby(
                    [
                        "Month",
                        "Selected Item",
                    ],
                    sort=False,
                )
                .size()
                .rename("Records")
                .reset_index()
            )

            # ------------------------------------------------
            # IMPORTANT:
            # Month categorical order BEFORE chart
            # ------------------------------------------------

            item_month["Month"] = pd.Categorical(
                item_month["Month"],
                categories=MONTH_ORDER,
                ordered=True,
            )

            item_month = (
                item_month
                .sort_values(
                    [
                        "Month",
                        "Selected Item",
                    ],
                    kind="stable",
                )
                .reset_index(drop=True)
            )

            # ------------------------------------------------
            # Prepare chart in Month-first order
            # ------------------------------------------------

            pivot_data = (
                item_month
                .pivot(
                    index="Month",
                    columns="Selected Item",
                    values="Records",
                )
                .fillna(0)
            )

            # ------------------------------------------------
            # Explicit final Jan-Dec reindex
            # ------------------------------------------------

            pivot_data = pivot_data.reindex(
                [
                    month
                    for month in MONTH_ORDER
                    if month in pivot_data.index
                ]
            )

            # Keep categorical index explicitly ordered
            pivot_data.index = pd.CategoricalIndex(
                pivot_data.index,
                categories=MONTH_ORDER,
                ordered=True,
                name="Month",
            )

            render_line_chart(
                pivot_data,
                height=450,
                use_container_width=True,
            )

            st.caption(
                f"Showing monthly trend for the selected "
                f"{selected_label.lower()} values."
            )

        else:
            st.info(
                "No trend data is available for "
                "the selected laboratory item."
            )

    else:
        st.info(
            "Selected laboratory item trend is not available."
        )

    # ========================================================
    # 8. FACILITY-WISE LABORATORY ANALYSIS
    # ========================================================

    st.divider()

    st.markdown(
        "### 7. Facility-wise Laboratory Analysis"
    )

    if facility_col is not None:

        facility_table = _count_table(
            laboratory_records,
            facility_col,
            "Facility Name",
        )

        if not facility_table.empty:

            chart_table = (
                facility_table
                .head(20)
                .sort_values(
                    "Records",
                    ascending=True,
                )
            )

            render_bar_chart(
                chart_table
                .set_index("Facility Name")[
                    "Records"
                ],
                use_container_width=True,
            )

            st.dataframe(
                facility_table,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Facility-wise laboratory data "
                "is not available."
            )

    else:
        st.info(
            "Facility information is not available "
            "in the selected dataset."
        )

    # ========================================================
    # 9. WARD-WISE LABORATORY ANALYSIS
    # ========================================================

    st.divider()

    st.markdown(
        "### 8. Ward-wise Laboratory Analysis"
    )

    if ward_col is not None:

        # ====================================================
        # IMPORTANT:
        # DO NOT CHANGE THIS.
        # This is the working A-T ward ordering.
        # ====================================================

        ward_table = _count_table(
            laboratory_records,
            ward_col,
            "Ward Name",
            order_type="ward",
        )

        if not ward_table.empty:

            render_bar_chart(
                ward_table
                .set_index("Ward Name")[
                    "Records"
                ],
                use_container_width=True,
            )

            st.dataframe(
                ward_table,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Ward-wise laboratory data "
                "is not available."
            )

    else:
        st.info(
            "Ward information is not available "
            "in the selected dataset."
        )

    # ========================================================
    # 10. DETAILED LABORATORY RECORDS
    # ========================================================

    st.divider()

    st.markdown(
        "### 9. Detailed Laboratory Records"
    )

    detail_columns = []

    preferred_columns = [
        "Year",
        "Month",
        "Week",
        "Reporting Date",
        "Date Of Onset",
        "Facility Name",
        "Facility Name Lform",
        "Ward Name",
        "Ward",
        "Gender",
        "Age",
        "Patient Address",
        "Test Performed",
        "Pathogen Name",
        "Confirmed Diagnosis",
        "OPD/IPD",
        "Opd Ipd",
    ]

    for column in preferred_columns:

        if (
            column in laboratory_records.columns
            and column not in detail_columns
        ):
            detail_columns.append(column)

    if detail_columns:

        detail_df = laboratory_records[
            detail_columns
        ].copy()

    else:

        detail_df = laboratory_records.copy()

    st.dataframe(
        detail_df,
        use_container_width=True,
        hide_index=True,
    )
