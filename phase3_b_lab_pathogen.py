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
import pandas as pd
import streamlit as st
import plotly.express as px

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
# MONTH LINE CHART WITH ACTIVE DATA LABELS
# ============================================================

def _render_month_line_chart(
    chart_data,
    title,
    height=400,
):
    """
    Render monthly line chart.

    IMPORTANT:
    Data labels are explicitly enabled using
    text + textposition.
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
    # IMPORTANT:
    # Build labels as a real column.
    # --------------------------------------------------------

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

    One Plotly trace is created per item so that
    data labels are correctly attached to the
    corresponding line.
    """

    if (
        plot_df is None
        or plot_df.empty
    ):

        return

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

        selected_item = st.selectbox(
            "Select Laboratory Item",
            available_items,
            key="lab_pathogen_selected_item",
        )

        if selected_item == "Test Performed":

            selected_column = test_col

        else:

            selected_column = pathogen_col

        selected_label = selected_item

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

        temp["Selected Item"] = (
            _clean_text_series(
                temp[selected_column]
            )
        )

        temp = temp[
            temp["Month"].isin(
                MONTH_ORDER
            )
            & _valid_value_mask(
                temp["Selected Item"]
            )
        ].copy()

        if not temp.empty:

            item_totals = (
                temp[
                    "Selected Item"
                ]
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
                    temp[
                        "Selected Item"
                    ].isin(
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
                .rename(
                    "Records"
                )
                .reset_index()
            )

            # ------------------------------------------------
            # COMPLETE JAN-DEC STRUCTURE
            # ------------------------------------------------

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

            # ------------------------------------------------
            # PIVOT
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
            # FORCE JAN-DEC
            # ------------------------------------------------

            pivot_data = (
                pivot_data
                .reindex(
                    MONTH_ORDER,
                    fill_value=0,
                )
            )

            # ------------------------------------------------
            # LONG FORMAT
            # ------------------------------------------------

            plot_df = (
                pivot_data
                .reset_index()
                .melt(
                    id_vars=[
                        "Month"
                    ],
                    var_name=(
                        "Selected Item"
                    ),
                    value_name="Records",
                )
            )

            # ------------------------------------------------
            # DATA LABELS
            # ------------------------------------------------

            plot_df["Data Label"] = (
                plot_df["Records"]
                .fillna(0)
                .astype(int)
                .astype(str)
            )

            # Zero values remain unlabeled
            plot_df.loc[
                plot_df["Records"].eq(0),
                "Data Label",
            ] = ""

            _render_selected_item_chart(
                plot_df,
                f"Monthly Trend — {selected_label}",
                height=450,
            )

            st.caption(
                f"Showing monthly trend for the selected "
                f"{selected_label.lower()} values."
            )

        else:

            st.info(
                "No trend data is available for the "
                "selected laboratory item."
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
