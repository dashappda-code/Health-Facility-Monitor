import pandas as pd
import streamlit as st
import plotly.express as px

from chart_helpers import (
    render_bar_chart,
    render_line_chart,
    data_labels_enabled,
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
    "1": "Jan",
    "01": "Jan",
    "feb": "Feb",
    "february": "Feb",
    "2": "Feb",
    "02": "Feb",
    "mar": "Mar",
    "march": "Mar",
    "3": "Mar",
    "03": "Mar",
    "apr": "Apr",
    "april": "Apr",
    "4": "Apr",
    "04": "Apr",
    "may": "May",
    "5": "May",
    "05": "May",
    "jun": "Jun",
    "june": "Jun",
    "6": "Jun",
    "06": "Jun",
    "jul": "Jul",
    "july": "Jul",
    "7": "Jul",
    "07": "Jul",
    "aug": "Aug",
    "august": "Aug",
    "8": "Aug",
    "08": "Aug",
    "sep": "Sep",
    "sept": "Sep",
    "september": "Sep",
    "9": "Sep",
    "09": "Sep",
    "oct": "Oct",
    "october": "Oct",
    "10": "Oct",
    "nov": "Nov",
    "november": "Nov",
    "11": "Nov",
    "dec": "Dec",
    "december": "Dec",
    "12": "Dec",
}


# IMPORTANT:
# Keep existing Ward A-T ordering.
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
    Return the first matching column.

    Matching:
    1. Exact case-insensitive match
    2. Whitespace-insensitive match
    3. Partial match
    """

    if df is None or df.empty:
        return None

    columns = list(df.columns)

    column_map = {
        str(col).strip().lower(): col
        for col in columns
    }

    for candidate in candidates:

        key = (
            str(candidate)
            .strip()
            .lower()
        )

        if key in column_map:
            return column_map[key]

    # Partial matching
    for candidate in candidates:

        candidate_key = (
            str(candidate)
            .strip()
            .lower()
        )

        for col in columns:

            col_key = (
                str(col)
                .strip()
                .lower()
            )

            if candidate_key in col_key:
                return col

    return None


def _clean_text_series(series):
    """
    Safely clean text values.
    """

    if series is None:
        return pd.Series(
            dtype="object"
        )

    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _valid_value_mask(series):
    """
    Identify valid non-empty values.
    """

    cleaned = _clean_text_series(
        series
    )

    return (
        cleaned.ne("")
        & cleaned.str.lower().ne("nan")
        & cleaned.str.lower().ne("none")
        & cleaned.str.lower().ne("nat")
    )


# ============================================================
# DATA PREPARATION
# ============================================================

def _prepare_working_data(df):
    """
    Prepare a safe working copy without
    changing the original dataframe.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    working = df.copy()

    columns_to_clean = [
        "Test Performed",
        "Pathogen Name",
        "Month",
        "Year",
        "Facility Name",
        "Facility Name Lform",
        "Ward Name",
        "Ward",
    ]

    for col in columns_to_clean:

        if col in working.columns:

            working[col] = (
                _clean_text_series(
                    working[col]
                )
            )

    return working


# ============================================================
# MONTH HELPERS
# ============================================================

def _normalise_month(value):
    """
    Convert different month formats
    into standard Jan-Dec labels.
    """

    # Safety for Series
    if isinstance(value, pd.Series):

        return value.apply(
            _normalise_month
        )

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

    key = text.lower()

    # Direct lookup
    if key in MONTH_LOOKUP:
        return MONTH_LOOKUP[key]

    # Numeric month
    try:

        numeric = float(text)

        if numeric.is_integer():

            numeric = int(numeric)

            if 1 <= numeric <= 12:

                return MONTH_ORDER[
                    numeric - 1
                ]

    except Exception:
        pass

    # Date values
    try:

        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if not pd.isna(parsed):

            return parsed.strftime(
                "%b"
            )

    except Exception:
        pass

    # Month text beginning
    short_key = key[:3]

    if short_key in MONTH_LOOKUP:

        return MONTH_LOOKUP[
            short_key
        ]

    return text


def _month_order_value(value):
    """
    Return chronological order value.
    """

    month = _normalise_month(
        value
    )

    try:

        return (
            MONTH_ORDER.index(month)
            + 1
        )

    except ValueError:

        return 999


def _ordered_month_chart_data(
    month_df
):
    """
    Prepare explicitly ordered Jan-Dec data.
    """

    if (
        month_df is None
        or month_df.empty
        or "Month" not in month_df.columns
        or "Records" not in month_df.columns
    ):

        return pd.DataFrame()

    temp = month_df.copy()

    temp["Month"] = (
        temp["Month"]
        .map(_normalise_month)
    )

    temp = temp[
        temp["Month"].isin(
            MONTH_ORDER
        )
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    # Combine duplicate months if any
    temp = (
        temp
        .groupby(
            "Month",
            as_index=False,
        )["Records"]
        .sum()
    )

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
        .drop(
            columns="_Month_Order"
        )
        .reset_index(
            drop=True
        )
    )

    return temp[
        [
            "Month",
            "Records",
        ]
    ].copy()


# ============================================================
# WARD HELPERS
# ============================================================

def _normalise_ward(value):
    """
    Standardise ward labels while preserving
    A-T ordering.
    """

    if isinstance(value, pd.Series):

        return value.apply(
            _normalise_ward
        )

    if value is None:
        return ""

    try:

        if pd.isna(value):
            return ""

    except Exception:
        return ""

    text = (
        str(value)
        .strip()
        .upper()
    )

    if not text:
        return ""

    if text.startswith("WARD "):

        text = (
            text
            .replace(
                "WARD ",
                "",
                1,
            )
            .strip()
        )

    if text.startswith("W"):

        possible = (
            text[1:]
            .strip()
        )

        if possible in WARD_ORDER:

            return possible

    if text in WARD_ORDER:

        return text

    return text


def _ward_order_value(value):

    ward = _normalise_ward(
        value
    )

    try:

        return (
            WARD_ORDER.index(ward)
            + 1
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
    order_type=None,
):
    """
    Create frequency table with optional
    month or ward ordering.
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

    series = series[
        _valid_value_mask(series)
    ]

    if series.empty:
        return pd.DataFrame()

    result = (
        series
        .value_counts()
        .rename_axis(
            output_name
        )
        .reset_index(
            name="Records"
        )
    )

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
            .drop(
                columns="_Order"
            )
            .reset_index(
                drop=True
            )
        )

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
            .drop(
                columns="_Order"
            )
            .reset_index(
                drop=True
            )
        )

    return result


# ============================================================
# MONTH LINE CHART
# ============================================================

def _render_month_line_chart(
    chart_data,
    title,
    height=400,
):
    """
    Render monthly line chart.

    Data labels follow the global
    Show Data Labels switch.
    """

    if (
        chart_data is None
        or chart_data.empty
    ):

        return

    plot_df = chart_data.copy()

    plot_df["Month"] = pd.Categorical(
        plot_df["Month"],
        categories=MONTH_ORDER,
        ordered=True,
    )

    plot_df = (
        plot_df
        .sort_values(
            "Month",
            kind="stable",
        )
        .reset_index(
            drop=True
        )
    )

    # --------------------------------------------------------
    # GLOBAL DATA LABEL CONTROL
    # --------------------------------------------------------

    if data_labels_enabled():

        plot_df["Data Label"] = (
            plot_df["Records"]
            .fillna(0)
            .astype(int)
            .astype(str)
        )

        fig = px.line(
            plot_df,
            x="Month",
            y="Records",
            markers=True,
            text="Data Label",
            title=title,
            category_orders={
                "Month": MONTH_ORDER
            },
        )

        fig.update_traces(
            texttemplate="%{text}",
            textposition="top center",
            cliponaxis=False,
            mode="lines+markers+text",
            marker=dict(
                size=8
            ),
            line=dict(
                width=2
            ),
            textfont=dict(
                size=12
            ),
            hovertemplate=(
                "Month: %{x}<br>"
                "Records: %{y:,}"
                "<extra></extra>"
            ),
        )

    else:

        fig = px.line(
            plot_df,
            x="Month",
            y="Records",
            markers=True,
            title=title,
            category_orders={
                "Month": MONTH_ORDER
            },
        )

        fig.update_traces(
            mode="lines+markers",
            marker=dict(
                size=8
            ),
            line=dict(
                width=2
            ),
            hovertemplate=(
                "Month: %{x}<br>"
                "Records: %{y:,}"
                "<extra></extra>"
            ),
        )

    fig.update_xaxes(
        categoryorder="array",
        categoryarray=MONTH_ORDER,
    )

    fig.update_yaxes(
        rangemode="tozero"
    )

    fig.update_layout(
        height=height,
        margin=dict(
            l=40,
            r=30,
            t=60,
            b=40,
        ),
        showlegend=False,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# ============================================================
# SELECTED ITEM MULTI-LINE CHART
# ============================================================

def _render_selected_item_chart(
    plot_df,
    title,
    height=450,
):
    """
    Render selected laboratory item trend.

    Data labels follow the global
    Show Data Labels switch.
    """

    if (
        plot_df is None
        or plot_df.empty
    ):

        return

    # --------------------------------------------------------
    # DATA LABELS ONLY WHEN GLOBAL SWITCH IS ON
    # --------------------------------------------------------

    if data_labels_enabled():

        plot_df = plot_df.copy()

        if "Data Label" not in plot_df.columns:

            plot_df["Data Label"] = (
                plot_df["Records"]
                .fillna(0)
                .astype(int)
                .astype(str)
            )

        fig = px.line(
            plot_df,
            x="Month",
            y="Records",
            color="Selected Item",
            markers=True,
            text="Data Label",
            title=title,
            category_orders={
                "Month": MONTH_ORDER
            },
        )

        fig.update_traces(
            texttemplate="%{text}",
            textposition="top center",
            cliponaxis=False,
            mode="lines+markers+text",
            marker=dict(
                size=7
            ),
            textfont=dict(
                size=12
            ),
            hovertemplate=(
                "Month: %{x}<br>"
                "Records: %{y:,}<br>"
                "Item: %{fullData.name}"
                "<extra></extra>"
            ),
        )

    else:

        fig = px.line(
            plot_df,
            x="Month",
            y="Records",
            color="Selected Item",
            markers=True,
            title=title,
            category_orders={
                "Month": MONTH_ORDER
            },
        )

        fig.update_traces(
            mode="lines+markers",
            marker=dict(
                size=7
            ),
            hovertemplate=(
                "Month: %{x}<br>"
                "Records: %{y:,}<br>"
                "Item: %{fullData.name}"
                "<extra></extra>"
            ),
        )

    fig.update_xaxes(
        categoryorder="array",
        categoryarray=MONTH_ORDER,
    )

    fig.update_yaxes(
        rangemode="tozero"
    )

    fig.update_layout(
        height=height,
        margin=dict(
            l=40,
            r=30,
            t=60,
            b=40,
        ),
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


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_lab_pathogen(filtered_df):

    st.subheader(
        "Laboratory & Pathogen Analysis"
    )

    st.caption(
        "Laboratory testing and pathogen analysis based "
        "on the currently selected Global Dashboard Filters."
    )

    # ========================================================
    # DATA PREPARATION
    # ========================================================

    laboratory_records = (
        _prepare_working_data(
            filtered_df
        )
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

    if test_col is not None:

        valid_tests = (
            _clean_text_series(
                laboratory_records[
                    test_col
                ]
            )
        )

        valid_tests = valid_tests[
            _valid_value_mask(
                valid_tests
            )
        ]

        if not valid_tests.empty:

            test_types = (
                valid_tests.nunique()
            )

            test_counts = (
                valid_tests
                .value_counts()
            )

            if not test_counts.empty:

                top_test = str(
                    test_counts.index[0]
                )

    if pathogen_col is not None:

        valid_pathogens = (
            _clean_text_series(
                laboratory_records[
                    pathogen_col
                ]
            )
        )

        valid_pathogens = valid_pathogens[
            _valid_value_mask(
                valid_pathogens
            )
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
                .set_index(
                    "Test Performed"
                )["Records"],
                use_container_width=True,
                height=400,
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

    st.divider()

    # ========================================================
    # 3. PATHOGEN NAME-WISE ANALYSIS
    # ========================================================

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
                .set_index(
                    "Pathogen Name"
                )["Records"],
                use_container_width=True,
                height=400,
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

    st.divider()

    # ========================================================
    # 4. TEST × PATHOGEN ANALYSIS
    # ========================================================

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

        temp[test_col] = (
            _clean_text_series(
                temp[test_col]
            )
        )

        temp[pathogen_col] = (
            _clean_text_series(
                temp[pathogen_col]
            )
        )

        temp = temp[
            _valid_value_mask(
                temp[test_col]
            )
            & _valid_value_mask(
                temp[pathogen_col]
            )
        ].copy()

        if not temp.empty:

            cross_table = pd.crosstab(
                temp[test_col],
                temp[pathogen_col],
            )

            test_totals = (
                cross_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .head(15)
            )

            cross_table = (
                cross_table
                .loc[test_totals.index]
            )

            pathogen_totals = (
                cross_table
                .sum(axis=0)
                .sort_values(
                    ascending=False
                )
                .head(15)
            )

            cross_table = (
                cross_table[
                    pathogen_totals.index
                ]
            )

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

    st.divider()

    # ========================================================
    # 5. MONTH-WISE LABORATORY TEST TREND
    # ========================================================

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

        temp["Test"] = (
            _clean_text_series(
                temp[test_col]
            )
        )

        temp = temp[
            temp["Month"].isin(
                MONTH_ORDER
            )
            & _valid_value_mask(
                temp["Test"]
            )
        ].copy()

        if not temp.empty:

            month_test = (
                temp
                .groupby(
                    "Month",
                    sort=False,
                )
                .size()
                .rename(
                    "Records"
                )
                .reset_index()
            )

            chart_data = (
                _ordered_month_chart_data(
                    month_test
                )
            )

            if not chart_data.empty:

                _render_month_line_chart(
                    chart_data,
                    "Monthly Laboratory Test Trend",
                    height=400,
                )

                st.dataframe(
                    chart_data,
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

    st.divider()

    # ========================================================
    # 6. MONTH-WISE PATHOGEN TREND
    # ========================================================

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

        temp["Pathogen"] = (
            _clean_text_series(
                temp[pathogen_col]
            )
        )

        temp = temp[
            temp["Month"].isin(
                MONTH_ORDER
            )
            & _valid_value_mask(
                temp["Pathogen"]
            )
        ].copy()

        if not temp.empty:

            pathogen_month = (
                temp
                .groupby(
                    "Month",
                    sort=False,
                )
                .size()
                .rename(
                    "Records"
                )
                .reset_index()
            )

            chart_data = (
                _ordered_month_chart_data(
                    pathogen_month
                )
            )

            if not chart_data.empty:

                _render_month_line_chart(
                    chart_data,
                    "Monthly Pathogen Trend",
                    height=400,
                )

                st.dataframe(
                    chart_data,
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.info(
                "Month-wise pathogen data is not available."
            )

    else:

        st.info(
            "Month-wise pathogen trend requires "
            "'Month' and 'Pathogen Name'."
        )

    st.divider()

    
    # ========================================================
    # 7. SELECTED LABORATORY ITEM TREND
    # ========================================================

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

        # ----------------------------------------------------
        # LEVEL 1:
        # SELECT ANALYSIS TYPE
        # ----------------------------------------------------

        selected_item = st.selectbox(
            "Select Laboratory Item",
            options=[""] + available_items,
            format_func=lambda x: (
                "Select Test Performed / Pathogen Name"
                if x == ""
                else x
            ),
            key="lab_pathogen_selected_item",
        )

        # ----------------------------------------------------
        # SHOW LEVEL 2 ONLY AFTER LEVEL 1 IS SELECTED
        # ----------------------------------------------------

        if selected_item:

            if selected_item == "Test Performed":
                selected_column = test_col
            else:
                selected_column = pathogen_col

            selected_label = selected_item

            # ------------------------------------------------
            # PREPARE CURRENT FILTERED DATA
            # ------------------------------------------------

            temp = laboratory_records[
                [month_col, selected_column]
            ].copy()

            temp["Month"] = temp[
                month_col
            ].map(_normalise_month)

            temp["Selected Item"] = _clean_text_series(
                temp[selected_column]
            )

            temp = temp[
                temp["Month"].isin(MONTH_ORDER)
                & _valid_value_mask(
                    temp["Selected Item"]
                )
            ].copy()

            if not temp.empty:

                # --------------------------------------------
                # AVAILABLE INDICATORS
                # --------------------------------------------

                available_indicator_list = sorted(
                    temp["Selected Item"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .unique()
                    .tolist(),
                    key=lambda x: x.lower(),
                )

                if available_indicator_list:

                    # ----------------------------------------
                    # UNIQUE KEY BASED ON CURRENT INDICATORS
                    # This makes the selector refresh when
                    # Global Filters change the available list.
                    # ----------------------------------------

                    indicator_signature = "|".join(
                        available_indicator_list
                    )

                    selection_key = (
                        "lab_selected_indicators_"
                        + selected_item.lower().replace(
                            " ",
                            "_",
                        )
                        + "_"
                        + str(
                            abs(
                                hash(
                                    indicator_signature
                                )
                            )
                        )
                    )

                    reset_key = (
                        selection_key
                        + "_reset"
                    )

                    # ----------------------------------------
                    # LEVEL 2:
                    # USER SELECTS INDICATORS
                    #
                    # IMPORTANT:
                    # No default selection.
                    # User must manually select.
                    # ----------------------------------------

                    selected_indicators = st.multiselect(
                        f"Select {selected_label} Indicators",
                        options=available_indicator_list,
                        default=[],
                        key=selection_key,
                        help=(
                            "Select one or more indicators "
                            "to display the monthly trend."
                        ),
                    )

                    # ----------------------------------------
                    # RESET SELECTION
                    #
                    # Reset = CLEAR selection
                    # NOT Select All
                    # ----------------------------------------

                    def _reset_lab_indicator_selection():
                        st.session_state[
                            selection_key
                        ] = []

                    st.button(
                        "Reset Selection",
                        key=reset_key,
                        on_click=(
                            _reset_lab_indicator_selection
                        ),
                        help=(
                            "Clear the selected indicators."
                        ),
                    )

                    # ----------------------------------------
                    # NO INDICATOR SELECTED
                    # ----------------------------------------

                    if not selected_indicators:

                        st.info(
                            "Please select at least one "
                            f"{selected_label.lower()} indicator "
                            "to display the monthly trend."
                        )

                    else:

                        # ------------------------------------
                        # FILTER SELECTED INDICATORS
                        # ------------------------------------

                        selected_temp = temp[
                            temp["Selected Item"].isin(
                                selected_indicators
                            )
                        ].copy()

                        if not selected_temp.empty:

                            # --------------------------------
                            # MONTH × SELECTED ITEM
                            # --------------------------------

                            item_month = (
                                selected_temp
                                .groupby(
                                    [
                                        "Month",
                                        "Selected Item",
                                    ],
                                    sort=False,
                                )
                                .size()
                                .rename(
                                    "Records"
                                )
                                .reset_index()
                            )

                            item_month["Month"] = (
                                pd.Categorical(
                                    item_month["Month"],
                                    categories=MONTH_ORDER,
                                    ordered=True,
                                )
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
                                .reset_index(
                                    drop=True
                                )
                            )

                            # --------------------------------
                            # PIVOT
                            # --------------------------------

                            pivot_data = (
                                item_month
                                .pivot(
                                    index="Month",
                                    columns="Selected Item",
                                    values="Records",
                                )
                                .fillna(0)
                            )

                            pivot_data = (
                                pivot_data.reindex(
                                    MONTH_ORDER,
                                    fill_value=0,
                                )
                            )

                            pivot_data = (
                                pivot_data.reindex(
                                    columns=[
                                        item
                                        for item
                                        in selected_indicators
                                        if item
                                        in pivot_data.columns
                                    ],
                                    fill_value=0,
                                )
                            )

                            # --------------------------------
                            # LONG FORMAT FOR CHART
                            # --------------------------------

                            plot_df = (
                                pivot_data
                                .reset_index()
                                .melt(
                                    id_vars=["Month"],
                                    var_name="Selected Item",
                                    value_name="Records",
                                )
                            )

                            # --------------------------------
                            # DATA LABEL
                            # --------------------------------

                            plot_df[
                                "Data Label"
                            ] = (
                                plot_df[
                                    "Records"
                                ]
                                .fillna(0)
                                .astype(int)
                                .astype(str)
                            )

                            plot_df.loc[
                                plot_df[
                                    "Records"
                                ].eq(0),
                                "Data Label",
                            ] = ""

                            # --------------------------------
                            # RENDER CHART
                            # --------------------------------

                            _render_selected_item_chart(
                                plot_df,
                                f"Monthly Trend — "
                                f"{selected_label}",
                                height=450,
                            )

                            st.caption(
                                "Showing monthly trend for "
                                f"{len(selected_indicators):,} "
                                f"selected "
                                f"{selected_label.lower()}"
                                + (
                                    ""
                                    if len(
                                        selected_indicators
                                    ) == 1
                                    else "s"
                                )
                                + "."
                            )

                        else:

                            st.info(
                                "No trend data is available "
                                "for the selected indicators."
                            )

                else:

                    st.info(
                        f"No {selected_label.lower()} "
                        "indicators are available for "
                        "the selected Global Dashboard Filters."
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

    st.divider()

    # ========================================================
    # 8. FACILITY-WISE LABORATORY ANALYSIS
    # ========================================================

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
                .set_index(
                    "Facility Name"
                )["Records"],
                use_container_width=True,
                height=400,
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

    st.divider()

    # ========================================================
    # 9. WARD-WISE LABORATORY ANALYSIS
    # ========================================================

    st.markdown(
        "### 8. Ward-wise Laboratory Analysis"
    )

    if ward_col is not None:

        ward_table = _count_table(
            laboratory_records,
            ward_col,
            "Ward Name",
            order_type="ward",
        )

        if not ward_table.empty:

            render_bar_chart(
                ward_table
                .set_index(
                    "Ward Name"
                )["Records"],
                use_container_width=True,
                height=400,
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

    st.divider()

    # ========================================================
    # 10. DETAILED LABORATORY RECORDS
    # ========================================================

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

            detail_columns.append(
                column
            )

    if detail_columns:

        detail_df = laboratory_records[
            detail_columns
        ].copy()

    else:

        detail_df = (
            laboratory_records.copy()
        )

    st.dataframe(
        detail_df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        f"Laboratory analysis based on "
        f"{len(laboratory_records):,} "
        f"filtered records."
    )
