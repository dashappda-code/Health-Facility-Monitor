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
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
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

# Keep the original A-T ward order.
WARD_ORDER = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
    "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def _find_column(df, candidates):
    """
    Find a dataframe column using case-insensitive,
    whitespace-normalised matching.
    """

    if df is None or df.empty:
        return None

    normalised = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower()

        if key in normalised:
            return normalised[key]

    return None


def _clean_text_series(series):
    """
    Convert values to clean strings while preserving
    missing values as empty strings.
    """

    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _valid_value_mask(series):
    """
    Identify meaningful non-empty values.
    """

    cleaned = _clean_text_series(series)

    invalid_values = {
        "",
        "nan",
        "none",
        "null",
        "na",
        "n/a",
        "-",
    }

    return ~cleaned.str.lower().isin(
        invalid_values
    )


# ============================================================
# DATA PREPARATION
# ============================================================

def _prepare_working_data(df):
    """
    Prepare a safe working dataframe without changing
    the original dataframe.
    """

    if df is None:
        return pd.DataFrame()

    work_df = df.copy()

    # --------------------------------------------------------
    # Test Performed
    # --------------------------------------------------------

    test_col = _find_column(
        work_df,
        [
            "Test Performed",
            "Test performed",
            "Test",
        ],
    )

    if test_col:
        work_df["Test Performed"] = _clean_text_series(
            work_df[test_col]
        )
    else:
        work_df["Test Performed"] = ""

    # --------------------------------------------------------
    # Pathogen Name
    # --------------------------------------------------------

    pathogen_col = _find_column(
        work_df,
        [
            "Pathogen Name",
            "Pathogen name",
            "Pathogen",
        ],
    )

    if pathogen_col:
        work_df["Pathogen Name"] = _clean_text_series(
            work_df[pathogen_col]
        )
    else:
        work_df["Pathogen Name"] = ""

    # --------------------------------------------------------
    # Month
    # --------------------------------------------------------

    month_col = _find_column(
        work_df,
        [
            "Month",
            "month",
        ],
    )

    if month_col:
        work_df["Month"] = work_df[month_col]
    else:
        work_df["Month"] = ""

    # --------------------------------------------------------
    # Year
    # --------------------------------------------------------

    year_col = _find_column(
        work_df,
        [
            "Year",
            "year",
        ],
    )

    if year_col:
        work_df["Year"] = work_df[year_col]
    else:
        work_df["Year"] = ""

    # --------------------------------------------------------
    # Facility Name
    # --------------------------------------------------------

    facility_col = _find_column(
        work_df,
        [
            "Facility Name",
            "Facility name",
        ],
    )

    if facility_col:
        work_df["Facility Name"] = _clean_text_series(
            work_df[facility_col]
        )
    else:
        work_df["Facility Name"] = ""

    # --------------------------------------------------------
    # Facility Name Lform
    # --------------------------------------------------------

    facility_lform_col = _find_column(
        work_df,
        [
            "Facility Name Lform",
            "Facility Name L Form",
            "Facility Lform",
        ],
    )

    if facility_lform_col:
        work_df["Facility Name Lform"] = _clean_text_series(
            work_df[facility_lform_col]
        )
    else:
        work_df["Facility Name Lform"] = ""

    # --------------------------------------------------------
    # Ward Name
    # --------------------------------------------------------

    ward_name_col = _find_column(
        work_df,
        [
            "Ward Name",
            "Ward name",
        ],
    )

    if ward_name_col:
        work_df["Ward Name"] = _clean_text_series(
            work_df[ward_name_col]
        )
    else:
        work_df["Ward Name"] = ""

    # --------------------------------------------------------
    # Ward
    # --------------------------------------------------------

    ward_col = _find_column(
        work_df,
        [
            "Ward",
            "ward",
        ],
    )

    if ward_col:
        work_df["Ward"] = _clean_text_series(
            work_df[ward_col]
        )
    else:
        work_df["Ward"] = ""

    return work_df


# ============================================================
# MONTH HELPERS
# ============================================================

def _normalise_month(value):
    """
    Convert different month formats into Jan-Dec.
    """

    if pd.isna(value):
        return None

    text = str(value).strip().lower()

    if not text:
        return None

    # Numeric month
    try:
        numeric_value = float(text)

        if numeric_value.is_integer():
            month_number = int(numeric_value)

            if 1 <= month_number <= 12:
                return MONTH_ORDER[
                    month_number - 1
                ]

    except Exception:
        pass

    return MONTH_LOOKUP.get(text)


def _month_order_value(value):
    """
    Return month order for sorting.
    """

    try:
        return MONTH_ORDER.index(value)

    except ValueError:
        return 999


def _ordered_month_chart_data(month_df):
    """
    Sort monthly chart data chronologically.
    """

    if month_df is None or month_df.empty:
        return month_df

    result = month_df.copy()

    result["_month_order"] = (
        result["Month"]
        .apply(_month_order_value)
    )

    result = (
        result
        .sort_values("_month_order")
        .drop(columns="_month_order")
        .reset_index(drop=True)
    )

    return result


# ============================================================
# WARD HELPERS
# ============================================================

def _normalise_ward(value):
    """
    Normalise ward values while preserving A-T.
    """

    if pd.isna(value):
        return None

    text = str(value).strip().upper()

    if not text:
        return None

    # Exact A-T ward
    if text in WARD_ORDER:
        return text

    # Values such as "Ward A"
    if text.startswith("WARD "):

        candidate = (
            text
            .replace("WARD ", "", 1)
            .strip()
        )

        if candidate in WARD_ORDER:
            return candidate

    return text


def _ward_order_value(value):
    """
    Return ward order for A-T sorting.
    """

    try:
        return WARD_ORDER.index(value)

    except ValueError:
        return 999


# ============================================================
# COUNT TABLE
# ============================================================

def _count_table(
    df,
    column,
    output_name="Records",
    order_type=None,
):
    """
    Generate a count table for a selected field.
    """

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                column,
                output_name,
            ]
        )

    if column not in df.columns:
        return pd.DataFrame(
            columns=[
                column,
                output_name,
            ]
        )

    work = df.copy()

    work = work[
        _valid_value_mask(
            work[column]
        )
    ].copy()

    if work.empty:
        return pd.DataFrame(
            columns=[
                column,
                output_name,
            ]
        )

    if order_type == "ward":

        work[column] = (
            work[column]
            .apply(_normalise_ward)
        )

        work = work[
            work[column].notna()
        ].copy()

    result = (
        work
        .groupby(
            column,
            dropna=False,
        )
        .size()
        .reset_index(
            name=output_name
        )
    )

    if result.empty:
        return result

    if order_type == "ward":

        result["_order"] = (
            result[column]
            .apply(_ward_order_value)
        )

        result = (
            result
            .sort_values(
                [
                    "_order",
                    output_name,
                ],
                ascending=[
                    True,
                    False,
                ],
            )
            .drop(
                columns="_order"
            )
            .reset_index(
                drop=True
            )
        )

    else:

        result = (
            result
            .sort_values(
                output_name,
                ascending=False,
            )
            .reset_index(
                drop=True
            )
        )

    return result


# ============================================================
# MONTH LINE DATA PREPARATION
# ============================================================

def _prepare_month_single_series(
    df,
    value_column,
):
    """
    Prepare a single-series monthly dataset in the format
    expected by the global render_line_chart helper.
    """

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "Month",
                "Records",
            ]
        )

    work = df[
        _valid_value_mask(
            df[value_column]
        )
    ].copy()

    if work.empty:
        return pd.DataFrame(
            columns=[
                "Month",
                "Records",
            ]
        )

    work["Month"] = (
        work["Month"]
        .apply(_normalise_month)
    )

    work = work[
        work["Month"].notna()
    ].copy()

    if work.empty:
        return pd.DataFrame(
            columns=[
                "Month",
                "Records",
            ]
        )

    result = (
        work
        .groupby("Month")
        .size()
        .reset_index(
            name="Records"
        )
    )

    result = _ordered_month_chart_data(
        result
    )

    return result


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_lab_pathogen(filtered_df):

    # ========================================================
    # PREPARE DATA
    # ========================================================

    df = _prepare_working_data(
        filtered_df
    )

    if df.empty:

        st.info(
            "No laboratory or pathogen data is available "
            "for the selected filters."
        )

        return

    # ========================================================
    # 1. SUMMARY KPIs
    # ========================================================

    st.subheader(
        "Laboratory & Pathogen Analysis"
    )

    total_records = len(df)

    pathogen_records = int(
        _valid_value_mask(
            df["Pathogen Name"]
        ).sum()
    )

    test_types = int(
        df.loc[
            _valid_value_mask(
                df["Test Performed"]
            ),
            "Test Performed",
        ].nunique()
    )

    pathogen_types = int(
        df.loc[
            _valid_value_mask(
                df["Pathogen Name"]
            ),
            "Pathogen Name",
        ].nunique()
    )

    test_counts = _count_table(
        df,
        "Test Performed",
        "Records",
    )

    pathogen_counts = _count_table(
        df,
        "Pathogen Name",
        "Records",
    )

    top_test = (
        test_counts.iloc[0][
            "Test Performed"
        ]
        if not test_counts.empty
        else "N/A"
    )

    top_pathogen = (
        pathogen_counts.iloc[0][
            "Pathogen Name"
        ]
        if not pathogen_counts.empty
        else "N/A"
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)

    with k1:

        st.metric(
            "Total Records",
            f"{total_records:,}",
        )

    with k2:

        st.metric(
            "Pathogen Records",
            f"{pathogen_records:,}",
        )

    with k3:

        st.metric(
            "Test Types",
            f"{test_types:,}",
        )

    with k4:

        st.metric(
            "Pathogen Types",
            f"{pathogen_types:,}",
        )

    with k5:

        st.metric(
            "Top Test",
            str(top_test),
        )

    with k6:

        st.metric(
            "Top Pathogen",
            str(top_pathogen),
        )

    st.divider()

    # ========================================================
    # 2. TEST PERFORMED-WISE ANALYSIS
    # ========================================================

    st.markdown(
        "### 1. Test Performed-wise Analysis"
    )

    test_chart_data = _count_table(
        df,
        "Test Performed",
        "Records",
    )

    if test_chart_data.empty:

        st.info(
            "No Test Performed data available."
        )

    else:

        # IMPORTANT:
        # render_bar_chart accepts only:
        # data, use_container_width, height

        render_bar_chart(
            test_chart_data,
            use_container_width=True,
            height=400,
        )

        st.dataframe(
            test_chart_data,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    # ========================================================
    # 3. PATHOGEN NAME-WISE ANALYSIS
    # ========================================================

    st.markdown(
        "### 2. Pathogen Name-wise Analysis"
    )

    pathogen_chart_data = _count_table(
        df,
        "Pathogen Name",
        "Records",
    )

    if pathogen_chart_data.empty:

        st.info(
            "No Pathogen Name data available."
        )

    else:

        render_bar_chart(
            pathogen_chart_data,
            use_container_width=True,
            height=400,
        )

        st.dataframe(
            pathogen_chart_data,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    # ========================================================
    # 4. TEST × PATHOGEN ANALYSIS
    # ========================================================

    st.markdown(
        "### 3. Test × Pathogen Analysis"
    )

    cross_df = df[
        _valid_value_mask(
            df["Test Performed"]
        )
        &
        _valid_value_mask(
            df["Pathogen Name"]
        )
    ].copy()

    if cross_df.empty:

        st.info(
            "No Test × Pathogen data available."
        )

    else:

        matrix = pd.crosstab(
            cross_df["Test Performed"],
            cross_df["Pathogen Name"],
        )

        if matrix.empty:

            st.info(
                "No Test × Pathogen combinations available."
            )

        else:

            top_tests = (
                matrix
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .head(15)
                .index
            )

            top_pathogens = (
                matrix
                .sum(axis=0)
                .sort_values(
                    ascending=False
                )
                .head(15)
                .index
            )

            matrix = matrix.loc[
                top_tests,
                top_pathogens,
            ]

            st.dataframe(
                matrix,
                width="stretch",
            )

    st.divider()

    # ========================================================
    # 5. MONTH-WISE LABORATORY TEST TREND
    # ========================================================

    st.markdown(
        "### 4. Month-wise Laboratory Test Trend"
    )

    month_test_data = (
        _prepare_month_single_series(
            df,
            "Test Performed",
        )
    )

    if month_test_data.empty:

        st.info(
            "No monthly laboratory test data available."
        )

    else:

        # Global Show Data Labels switch from chart_helpers.py
        render_line_chart(
            month_test_data,
            use_container_width=True,
            height=400,
        )

        st.dataframe(
            month_test_data,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    # ========================================================
    # 6. MONTH-WISE PATHOGEN TREND
    # ========================================================

    st.markdown(
        "### 5. Month-wise Pathogen Trend"
    )

    month_pathogen_data = (
        _prepare_month_single_series(
            df,
            "Pathogen Name",
        )
    )

    if month_pathogen_data.empty:

        st.info(
            "No monthly pathogen data available."
        )

    else:

        # Global Show Data Labels switch from chart_helpers.py
        render_line_chart(
            month_pathogen_data,
            use_container_width=True,
            height=400,
        )

        st.dataframe(
            month_pathogen_data,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    # ========================================================
    # 7. SELECTED LABORATORY ITEM TREND
    # ========================================================

    st.markdown(
        "### 6. Selected Laboratory Item Trend"
    )

    item_type = st.selectbox(
        "Select Analysis Type",
        [
            "Test Performed",
            "Pathogen Name",
        ],
        key="lab_selected_item_type",
    )

    selected_column = item_type

    selected_df = df[
        _valid_value_mask(
            df[selected_column]
        )
    ].copy()

    if selected_df.empty:

        st.info(
            f"No {item_type} data available."
        )

    else:

        selected_df["Month"] = (
            selected_df["Month"]
            .apply(_normalise_month)
        )

        selected_df = selected_df[
            selected_df["Month"].notna()
        ].copy()

        if selected_df.empty:

            st.info(
                "No valid monthly data available."
            )

        else:

            # ------------------------------------------------
            # Top 10 items by overall records
            # ------------------------------------------------

            top_items = (
                selected_df[
                    selected_column
                ]
                .value_counts()
                .head(10)
                .index
                .tolist()
            )

            selected_df = selected_df[
                selected_df[
                    selected_column
                ].isin(top_items)
            ].copy()

            selected_item_data = (
                selected_df
                .groupby(
                    [
                        "Month",
                        selected_column,
                    ]
                )
                .size()
                .reset_index(
                    name="Records"
                )
            )

            # ------------------------------------------------
            # Month order
            # ------------------------------------------------

            valid_months = [
                month
                for month in MONTH_ORDER
                if month
                in selected_item_data[
                    "Month"
                ].unique()
            ]

            if not valid_months:

                st.info(
                    "No valid monthly records available."
                )

            else:

                pivot_data = (
                    selected_item_data
                    .pivot_table(
                        index="Month",
                        columns=selected_column,
                        values="Records",
                        aggfunc="sum",
                        fill_value=0,
                    )
                    .reindex(
                        valid_months
                    )
                    .fillna(0)
                )

                # ------------------------------------------------
                # Convert pivot table to helper-compatible format
                # ------------------------------------------------

                plot_df = (
                    pivot_data
                    .reset_index()
                )

                plot_df.columns = [
                    str(col)
                    for col in plot_df.columns
                ]

                # ------------------------------------------------
                # Global line-chart renderer
                #
                # The helper:
                # - uses one colour per item
                # - displays labels only when
                #   show_data_labels is enabled
                # - uses the same colour for labels
                # - uses bold labels
                # ------------------------------------------------

                render_line_chart(
                    plot_df,
                    use_container_width=True,
                    height=500,
                )

                # ------------------------------------------------
                # Detailed table
                # ------------------------------------------------

                st.dataframe(
                    plot_df,
                    width="stretch",
                    hide_index=True,
                )

    st.divider()

    # ========================================================
    # 8. FACILITY-WISE LABORATORY ANALYSIS
    # ========================================================

    st.markdown(
        "### 7. Facility-wise Laboratory Analysis"
    )

    facility_chart_data = _count_table(
        df,
        "Facility Name",
        "Records",
    )

    if facility_chart_data.empty:

        st.info(
            "No facility-wise laboratory data available."
        )

    else:

        render_bar_chart(
            facility_chart_data,
            use_container_width=True,
            height=400,
        )

        st.dataframe(
            facility_chart_data,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    # ========================================================
    # 9. WARD-WISE LABORATORY ANALYSIS
    # ========================================================

    st.markdown(
        "### 8. Ward-wise Laboratory Analysis"
    )

    ward_chart_data = _count_table(
        df,
        "Ward",
        "Records",
        order_type="ward",
    )

    if ward_chart_data.empty:

        st.info(
            "No ward-wise laboratory data available."
        )

    else:

        render_bar_chart(
            ward_chart_data,
            use_container_width=True,
            height=400,
        )

        st.dataframe(
            ward_chart_data,
            width="stretch",
            hide_index=True,
        )

    st.divider()

    # ========================================================
    # 10. DETAILED LABORATORY RECORDS
    # ========================================================

    st.markdown(
        "### 9. Detailed Laboratory Records"
    )

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

    available_columns = [
        col
        for col in preferred_columns
        if col in df.columns
    ]

    if available_columns:

        st.dataframe(
            df[available_columns],
            width="stretch",
            hide_index=True,
        )

    else:

        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
        )
