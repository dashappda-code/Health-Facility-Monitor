import re

import pandas as pd
import streamlit as st

from chart_helpers import (
    render_bar_chart,
    render_line_chart,
)


# ============================================================
# HELPERS
# ============================================================

def _find_column(df, candidates):
    """
    Return the first matching column from candidate names.
    Matching is case-insensitive and whitespace-insensitive.
    """

    if df is None or df.empty:
        return None

    normalized = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for candidate in candidates:

        key = str(candidate).strip().lower()

        if key in normalized:
            return normalized[key]

    return None


def _clean_text_series(series):
    return (
        series.astype("string")
        .fillna("")
        .str.strip()
        .replace(
            {
                "nan": "",
                "None": "",
                "NaN": "",
            }
        )
    )


def _valid_value_mask(series):
    cleaned = _clean_text_series(series)

    return (
        cleaned.ne("")
        & cleaned.str.lower().ne("na")
        & cleaned.str.lower().ne("n/a")
        & cleaned.str.lower().ne("none")
        & cleaned.str.lower().ne("null")
        & cleaned.str.lower().ne("-")
    )


# ============================================================
# MONTH ORDER
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


def _normalise_month(value):
    """
    Convert month values to standard Jan-Dec labels.
    """

    if pd.isna(value):
        return ""

    text = str(value).strip().lower()

    return MONTH_LOOKUP.get(
        text,
        str(value).strip(),
    )


def _month_order_value(value):
    """
    Return numeric month order for Jan-Dec.
    """

    if pd.isna(value):
        return 999

    normalised = _normalise_month(value)

    try:
        return MONTH_ORDER.index(
            normalised
        ) + 1
    except ValueError:
        return 999


# ============================================================
# WARD ORDER
# ============================================================

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


def _normalise_ward(value):
    """
    Standardise ward value for ordering.

    Handles simple ward names such as:
        A, B, C, ... T

    Also handles values such as:
        Ward A
        Ward-A
        A Ward
    """

    if pd.isna(value):
        return ""

    text = str(value).strip()

    if not text:
        return ""

    upper_text = text.upper()

    # Direct A-T match
    if upper_text in WARD_ORDER:
        return upper_text

    # Ward A / Ward-A / Ward A etc.
    match = re.search(
        r"\bWARD[\s\-_]*([A-T])\b",
        upper_text,
    )

    if match:
        return match.group(1)

    # A Ward / A-Ward etc.
    match = re.search(
        r"\b([A-T])[\s\-_]*WARD\b",
        upper_text,
    )

    if match:
        return match.group(1)

    return text


def _ward_order_value(value):
    """
    Return numeric ward order A-T.

    Unknown/non-standard ward names are placed
    after A-T wards.
    """

    if pd.isna(value):
        return 999

    normalised = _normalise_ward(value)

    if normalised in WARD_ORDER:
        return (
            WARD_ORDER.index(normalised) + 1
        )

    return 999


# ============================================================
# DATA PREPARATION
# ============================================================

def _prepare_working_data(df):
    """
    Prepare a safe copy of the filtered dataframe.

    Laboratory fields are detected dynamically so that
    existing data-cleaning logic remains untouched.
    """

    if df is None or df.empty:
        return pd.DataFrame(), {}

    work = df.copy()

    column_map = {

        "test": _find_column(
            work,
            [
                "Test Performed",
                "Test performed",
                "Test",
                "Laboratory Test",
            ],
        ),

        "pathogen": _find_column(
            work,
            [
                "Pathogen Name",
                "Pathogen name",
                "Pathogen",
            ],
        ),

        "month": _find_column(
            work,
            [
                "Month",
            ],
        ),

        "facility": _find_column(
            work,
            [
                "Facility Name",
                "Facility Name Lform",
                "Facility",
            ],
        ),

        "ward": _find_column(
            work,
            [
                "Ward Name",
                "Ward",
            ],
        ),

        "disease": _find_column(
            work,
            [
                "Disease",
                "Confirmed Diagnosis",
            ],
        ),

        "gender": _find_column(
            work,
            [
                "Gender",
            ],
        ),

        "age": _find_column(
            work,
            [
                "Age",
            ],
        ),

        "reporting_date": _find_column(
            work,
            [
                "Reporting Date",
            ],
        ),
    }

    return work, column_map


# ============================================================
# FREQUENCY TABLE
# ============================================================

def _count_table(
    df,
    column,
    output_name,
    order_type=None,
):
    """
    Create a frequency table.

    order_type:
        None  -> descending record count
        ward  -> A-T order
        month -> Jan-Dec order
    """

    if (
        df is None
        or df.empty
        or column is None
        or column not in df.columns
    ):
        return pd.DataFrame()

    temp = df[[column]].copy()

    temp[column] = _clean_text_series(
        temp[column]
    )

    temp = temp[
        _valid_value_mask(temp[column])
    ]

    if temp.empty:
        return pd.DataFrame()

    result = (
        temp[column]
        .value_counts()
        .rename_axis(output_name)
        .reset_index(name="Records")
    )

    # --------------------------------------------------------
    # MONTH ORDER
    # --------------------------------------------------------

    if order_type == "month":

        result["_Month_Order"] = (
            result[output_name]
            .map(_month_order_value)
        )

        result["_Month_Normalised"] = (
            result[output_name]
            .map(_normalise_month)
        )

        result = result.sort_values(
            [
                "_Month_Order",
                output_name,
            ],
            ascending=[
                True,
                True,
            ],
            kind="stable",
        )

        result[output_name] = (
            result["_Month_Normalised"]
        )

        result = result.drop(
            columns=[
                "_Month_Order",
                "_Month_Normalised",
            ]
        )

    # --------------------------------------------------------
    # WARD ORDER
    # --------------------------------------------------------

    elif order_type == "ward":

        result["_Ward_Order"] = (
            result[output_name]
            .map(_ward_order_value)
        )

        result["_Ward_Normalised"] = (
            result[output_name]
            .map(_normalise_ward)
        )

        result = result.sort_values(
            [
                "_Ward_Order",
                "_Ward_Normalised",
                output_name,
            ],
            ascending=[
                True,
                True,
                True,
            ],
            kind="stable",
        )

        # Keep original display value.
        result = result.drop(
            columns=[
                "_Ward_Order",
                "_Ward_Normalised",
            ]
        )

    return result.reset_index(
        drop=True
    )


# ============================================================
# MONTH-WISE SERIES
# ============================================================

def _prepare_month_series(
    df,
    month_col,
    category_col=None,
    selected_category=None,
):
    """
    Prepare month-wise record counts.

    FINAL ORDER:
        Jan
        Feb
        Mar
        Apr
        May
        Jun
        Jul
        Aug
        Sep
        Oct
        Nov
        Dec

    Only months present in the filtered data are displayed.
    """

    if (
        df is None
        or df.empty
        or month_col is None
        or month_col not in df.columns
    ):
        return pd.DataFrame()

    temp = df.copy()

    # --------------------------------------------------------
    # STANDARDISE MONTH
    # --------------------------------------------------------

    temp["_Month"] = (
        temp[month_col]
        .map(_normalise_month)
    )

    temp = temp[
        _valid_value_mask(
            temp["_Month"]
        )
    ]

    # --------------------------------------------------------
    # CATEGORY FILTER
    # --------------------------------------------------------

    if category_col is not None:

        if category_col not in temp.columns:
            return pd.DataFrame()

        temp["_Category"] = (
            _clean_text_series(
                temp[category_col]
            )
        )

        temp = temp[
            _valid_value_mask(
                temp["_Category"]
            )
        ]

        if selected_category is not None:

            temp = temp[
                temp["_Category"].eq(
                    selected_category
                )
            ]

    if temp.empty:
        return pd.DataFrame()

    # --------------------------------------------------------
    # COUNT
    # --------------------------------------------------------

    result = (
        temp.groupby(
            "_Month",
            sort=False,
        )
        .size()
        .reset_index(
            name="Records"
        )
    )

    # --------------------------------------------------------
    # FORCE JAN-DEC ORDER
    # --------------------------------------------------------

    result["_Month_Order"] = (
        result["_Month"]
        .map(_month_order_value)
    )

    result = result.sort_values(
        "_Month_Order",
        ascending=True,
        kind="stable",
    )

    result = result[
        [
            "_Month",
            "Records",
        ]
    ]

    result = result.rename(
        columns={
            "_Month": "Month"
        }
    )

    return result.reset_index(
        drop=True
    )


# ============================================================
# MAIN PAGE
# ============================================================

def render_lab_pathogen(df):

    # ========================================================
    # PAGE HEADER
    # ========================================================

    st.markdown(
        """
        <div style="
            font-size:28px;
            font-weight:700;
            margin-bottom:4px;
        ">
            Laboratory & Pathogen Analysis
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "Analysis of laboratory tests, pathogen detection, "
        "facilities, wards and monthly trends."
    )

    # ========================================================
    # EMPTY DATA CHECK
    # ========================================================

    if df is None or df.empty:

        st.warning(
            "No records are available for the selected filters."
        )

        return

    # ========================================================
    # PREPARE DATA
    # ========================================================

    work, columns = _prepare_working_data(
        df
    )

    test_col = columns.get(
        "test"
    )

    pathogen_col = columns.get(
        "pathogen"
    )

    month_col = columns.get(
        "month"
    )

    facility_col = columns.get(
        "facility"
    )

    ward_col = columns.get(
        "ward"
    )

    # ========================================================
    # CHECK REQUIRED COLUMNS
    # ========================================================

    missing_core = []

    if test_col is None:
        missing_core.append(
            "Test Performed"
        )

    if pathogen_col is None:
        missing_core.append(
            "Pathogen Name"
        )

    if missing_core:

        st.error(
            "The following laboratory field(s) were not found "
            "in the current dataset: "
            + ", ".join(missing_core)
        )

        st.info(
            "Please ensure that the source data contains "
            "Test Performed and Pathogen Name fields."
        )

        return

    # ========================================================
    # STANDARDISE LABORATORY FIELDS
    # ========================================================

    work["_Test"] = _clean_text_series(
        work[test_col]
    )

    work["_Pathogen"] = _clean_text_series(
        work[pathogen_col]
    )

    # ========================================================
    # KEEP LABORATORY RECORDS
    # ========================================================

    test_valid = _valid_value_mask(
        work["_Test"]
    )

    pathogen_valid = _valid_value_mask(
        work["_Pathogen"]
    )

    laboratory_records = work[
        test_valid | pathogen_valid
    ].copy()

    if laboratory_records.empty:

        st.warning(
            "No laboratory test or pathogen records are "
            "available for the selected filters."
        )

        return

    # ========================================================
    # KPI CALCULATIONS
    # ========================================================

    test_values = laboratory_records[
        "_Test"
    ]

    test_values = test_values[
        _valid_value_mask(
            test_values
        )
    ]

    pathogen_values = laboratory_records[
        "_Pathogen"
    ]

    pathogen_values = pathogen_values[
        _valid_value_mask(
            pathogen_values
        )
    ]

    test_counts = (
        test_values.value_counts()
    )

    pathogen_counts = (
        pathogen_values.value_counts()
    )

    total_tests = int(
        len(test_values)
    )

    total_pathogen_records = int(
        len(pathogen_values)
    )

    test_types = int(
        test_values.nunique()
    )

    pathogen_types = int(
        pathogen_values.nunique()
    )

    top_test = (
        test_counts.index[0]
        if not test_counts.empty
        else "N/A"
    )

    top_pathogen = (
        pathogen_counts.index[0]
        if not pathogen_counts.empty
        else "N/A"
    )

    # ========================================================
    # KPI SUMMARY
    # ========================================================

    st.subheader(
        "Laboratory & Pathogen Summary"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Tests",
        f"{total_tests:,}",
    )

    c2.metric(
        "Pathogen Records",
        f"{total_pathogen_records:,}",
    )

    c3.metric(
        "Test Types",
        f"{test_types:,}",
    )

    c4.metric(
        "Pathogen Types",
        f"{pathogen_types:,}",
    )

    c5, c6 = st.columns(2)

    c5.metric(
        "Top Test",
        top_test,
    )

    c6.metric(
        "Top Pathogen",
        top_pathogen,
    )

    st.divider()

    # ========================================================
    # 1. TEST PERFORMED-WISE ANALYSIS
    # ========================================================

    st.subheader(
        "1. Test Performed-wise Analysis"
    )

    test_table = _count_table(
        laboratory_records,
        "_Test",
        "Test Performed",
    )

    if not test_table.empty:

        left, right = st.columns(
            [1.35, 1]
        )

        with left:

            render_bar_chart(
                test_table.set_index(
                    "Test Performed"
                )["Records"],
                height=420,
            )

        with right:

            st.dataframe(
                test_table,
                use_container_width=True,
                hide_index=True,
            )

    else:

        st.info(
            "No Test Performed data available."
        )

    st.divider()

    # ========================================================
    # 2. PATHOGEN NAME-WISE ANALYSIS
    # ========================================================

    st.subheader(
        "2. Pathogen Name-wise Analysis"
    )

    pathogen_table = _count_table(
        laboratory_records,
        "_Pathogen",
        "Pathogen Name",
    )

    if not pathogen_table.empty:

        left, right = st.columns(
            [1.35, 1]
        )

        with left:

            render_bar_chart(
                pathogen_table.set_index(
                    "Pathogen Name"
                )["Records"],
                height=420,
            )

        with right:

            st.dataframe(
                pathogen_table,
                use_container_width=True,
                hide_index=True,
            )

    else:

        st.info(
            "No Pathogen Name data available."
        )

    st.divider()

    # ========================================================
    # 3. TEST × PATHOGEN ANALYSIS
    # ========================================================

    st.subheader(
        "3. Test × Pathogen Analysis"
    )

    cross_df = laboratory_records[
        [
            "_Test",
            "_Pathogen",
        ]
    ].copy()

    cross_df = cross_df[
        _valid_value_mask(
            cross_df["_Test"]
        )
        & _valid_value_mask(
            cross_df["_Pathogen"]
        )
    ]

    if not cross_df.empty:

        cross_table = pd.crosstab(
            cross_df["_Test"],
            cross_df["_Pathogen"],
        )

        cross_table.index.name = (
            "Test Performed"
        )

        cross_table.columns.name = (
            "Pathogen Name"
        )

        st.dataframe(
            cross_table,
            use_container_width=True,
        )

    else:

        st.info(
            "No Test × Pathogen records available."
        )

    st.divider()

    # ========================================================
    # 4. MONTH-WISE LABORATORY TEST TREND
    # ========================================================

    st.subheader(
        "4. Month-wise Laboratory Test Trend"
    )

    if month_col is not None:

        month_test = _prepare_month_series(
            laboratory_records,
            month_col,
            "_Test",
            None,
        )

        if not month_test.empty:

            # ------------------------------------------------
            # EXPLICIT JAN-DEC INDEX
            # ------------------------------------------------

            month_chart_data = (
                month_test
                .set_index("Month")
                .reindex(
                    [
                        month
                        for month in MONTH_ORDER
                        if month
                        in month_test["Month"].tolist()
                    ]
                )[
                    ["Records"]
                ]
            )

            render_line_chart(
                month_chart_data,
                height=400,
            )

            st.dataframe(
                month_test,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No month-wise laboratory test data available."
            )

    else:

        st.info(
            "Month field is not available."
        )

    st.divider()

    # ========================================================
    # 5. MONTH-WISE PATHOGEN TREND
    # ========================================================

    st.subheader(
        "5. Month-wise Pathogen Trend"
    )

    if month_col is not None:

        pathogen_month = _prepare_month_series(
            laboratory_records,
            month_col,
            "_Pathogen",
            None,
        )

        if not pathogen_month.empty:

            # ------------------------------------------------
            # EXPLICIT JAN-DEC INDEX
            # ------------------------------------------------

            pathogen_chart_data = (
                pathogen_month
                .set_index("Month")
                .reindex(
                    [
                        month
                        for month in MONTH_ORDER
                        if month
                        in pathogen_month[
                            "Month"
                        ].tolist()
                    ]
                )[
                    ["Records"]
                ]
            )

            render_line_chart(
                pathogen_chart_data,
                height=400,
            )

            st.dataframe(
                pathogen_month,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "No month-wise pathogen data available."
            )

    else:

        st.info(
            "Month field is not available."
        )

    st.divider()

    # ========================================================
    # 6. SELECTED TEST / PATHOGEN MONTHLY TREND
    # ========================================================

    st.subheader(
        "6. Selected Laboratory Item Trend"
    )

    trend_type = st.radio(
        "Select analysis",
        [
            "Test Performed",
            "Pathogen Name",
        ],
        horizontal=True,
        key="lab_trend_type",
    )

    if trend_type == "Test Performed":

        available_values = sorted(
            test_values.unique().tolist()
        )

        category_col = "_Test"

    else:

        available_values = sorted(
            pathogen_values.unique().tolist()
        )

        category_col = "_Pathogen"

    if available_values:

        selected_value = st.selectbox(
            f"Select {trend_type}",
            available_values,
            key="lab_selected_item",
        )

        if month_col is not None:

            selected_month = (
                _prepare_month_series(
                    laboratory_records,
                    month_col,
                    category_col,
                    selected_value,
                )
            )

            if not selected_month.empty:

                # --------------------------------------------
                # EXPLICIT JAN-DEC ORDER
                # --------------------------------------------

                selected_chart_data = (
                    selected_month
                    .set_index("Month")
                    .reindex(
                        [
                            month
                            for month in MONTH_ORDER
                            if month
                            in selected_month[
                                "Month"
                            ].tolist()
                        ]
                    )[
                        ["Records"]
                    ]
                )

                render_line_chart(
                    selected_chart_data,
                    height=400,
                )

                st.dataframe(
                    selected_month,
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "No monthly records available "
                    "for the selected item."
                )

        else:

            st.info(
                "Month field is not available."
            )

    st.divider()

    # ========================================================
    # 7. FACILITY-WISE LABORATORY ANALYSIS
    # ========================================================

    st.subheader(
        "7. Facility-wise Laboratory Analysis"
    )

    if facility_col is not None:

        facility_table = _count_table(
            laboratory_records,
            facility_col,
            "Facility Name",
        )

        if not facility_table.empty:

            left, right = st.columns(
                [1.35, 1]
            )

            with left:

                render_bar_chart(
                    facility_table
                    .set_index(
                        "Facility Name"
                    )["Records"]
                    .head(20),
                    height=450,
                )

            with right:

                st.dataframe(
                    facility_table,
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.info(
                "No facility-wise laboratory data available."
            )

    else:

        st.info(
            "Facility field is not available."
        )

    st.divider()

    # ========================================================
    # 8. WARD-WISE LABORATORY ANALYSIS
    # ========================================================

    st.subheader(
        "8. Ward-wise Laboratory Analysis"
    )

    if ward_col is not None:

        # ----------------------------------------------------
        # A-T ORDER
        # ----------------------------------------------------

        ward_table = _count_table(
            laboratory_records,
            ward_col,
            "Ward Name",
            order_type="ward",
        )

        if not ward_table.empty:

            left, right = st.columns(
                [1.35, 1]
            )

            with left:

                ward_chart_data = (
                    ward_table
                    .set_index(
                        "Ward Name"
                    )[
                        ["Records"]
                    ]
                )

                render_bar_chart(
                    ward_chart_data,
                    height=450,
                )

            with right:

                st.dataframe(
                    ward_table,
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.info(
                "No ward-wise laboratory data available."
            )

    else:

        st.info(
            "Ward field is not available."
        )

    st.divider()

    # ========================================================
    # 9. DETAILED LABORATORY RECORDS
    # ========================================================

    st.subheader(
        "9. Detailed Laboratory Records"
    )

    display_columns = []

    candidate_columns = [
        test_col,
        pathogen_col,
        month_col,
        facility_col,
        ward_col,
        columns.get("disease"),
        columns.get("gender"),
        columns.get("age"),
        columns.get("reporting_date"),
    ]

    for col in candidate_columns:

        if (
            col is not None
            and col in laboratory_records.columns
            and col not in display_columns
        ):

            display_columns.append(
                col
            )

    if display_columns:

        detail_df = laboratory_records[
            display_columns
        ].copy()

        rename_map = {}

        if test_col is not None:

            rename_map[
                test_col
            ] = "Test Performed"

        if pathogen_col is not None:

            rename_map[
                pathogen_col
            ] = "Pathogen Name"

        if month_col is not None:

            rename_map[
                month_col
            ] = "Month"

        if facility_col is not None:

            rename_map[
                facility_col
            ] = "Facility Name"

        if ward_col is not None:

            rename_map[
                ward_col
            ] = "Ward Name"

        disease_col = columns.get(
            "disease"
        )

        gender_col = columns.get(
            "gender"
        )

        age_col = columns.get(
            "age"
        )

        reporting_date_col = columns.get(
            "reporting_date"
        )

        if disease_col is not None:

            rename_map[
                disease_col
            ] = "Disease"

        if gender_col is not None:

            rename_map[
                gender_col
            ] = "Gender"

        if age_col is not None:

            rename_map[
                age_col
            ] = "Age"

        if reporting_date_col is not None:

            rename_map[
                reporting_date_col
            ] = "Reporting Date"

        detail_df = detail_df.rename(
            columns=rename_map
        )

        st.dataframe(
            detail_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No detailed laboratory fields are available."
        )
