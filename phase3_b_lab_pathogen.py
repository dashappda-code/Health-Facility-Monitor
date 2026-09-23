import pandas as pd
import streamlit as st
import plotly.graph_objects as go


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
    "01": "Jan",
    "1": "Jan",
    "feb": "Feb",
    "february": "Feb",
    "02": "Feb",
    "2": "Feb",
    "mar": "Mar",
    "march": "Mar",
    "03": "Mar",
    "3": "Mar",
    "apr": "Apr",
    "april": "Apr",
    "04": "Apr",
    "4": "Apr",
    "may": "May",
    "05": "May",
    "5": "May",
    "jun": "Jun",
    "june": "Jun",
    "06": "Jun",
    "6": "Jun",
    "jul": "Jul",
    "july": "Jul",
    "07": "Jul",
    "7": "Jul",
    "aug": "Aug",
    "august": "Aug",
    "08": "Aug",
    "8": "Aug",
    "sep": "Sep",
    "sept": "Sep",
    "september": "Sep",
    "09": "Sep",
    "9": "Sep",
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


WARD_ORDER = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F/N",
    "F/S",
    "G/N",
    "G/S",
    "H/E",
    "H/W",
    "K/E",
    "K/W",
    "L",
    "M/E",
    "M/W",
    "N",
    "P/N",
    "P/S",
    "R/C",
    "R/N",
    "R/S",
    "S",
    "T",
]


# ============================================================
# COLUMN FINDER
# ============================================================

def _find_column(df, candidates):
    """
    Find the first matching column.

    Priority:
    1. Exact match
    2. Case-insensitive exact match
    3. Partial match
    """

    if df is None or df.empty:
        return None

    columns = list(df.columns)

    # Exact match
    for candidate in candidates:
        if candidate in columns:
            return candidate

    # Case-insensitive exact match
    lower_map = {
        str(col).strip().lower(): col
        for col in columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower()

        if key in lower_map:
            return lower_map[key]

    # Partial match
    for candidate in candidates:

        candidate_lower = (
            str(candidate)
            .strip()
            .lower()
        )

        for col in columns:

            col_lower = (
                str(col)
                .strip()
                .lower()
            )

            if candidate_lower in col_lower:
                return col

    return None


# ============================================================
# TEXT CLEANING
# ============================================================

def _clean_text_series(series):
    """
    Safely convert a pandas Series to cleaned text.
    """

    if series is None:
        return pd.Series(dtype="string")

    return (
        series
        .astype("string")
        .str.strip()
    )


def _valid_value_mask(series):
    """
    Return True for non-empty values.
    """

    cleaned = _clean_text_series(series)

    return (
        cleaned.notna()
        & cleaned.ne("")
        & cleaned.ne("nan")
        & cleaned.ne("None")
    )


# ============================================================
# MONTH NORMALISATION
# ============================================================

def _normalise_month(value):

    # Important:
    # Handle Series safely.
    if isinstance(value, pd.Series):
        return value.apply(_normalise_month)

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

    lower = text.lower()

    # Direct lookup
    if lower in MONTH_LOOKUP:
        return MONTH_LOOKUP[lower]

    # Remove separators
    cleaned = (
        lower
        .replace("-", " ")
        .replace("/", " ")
        .replace("_", " ")
    )

    # Month-name matching
    for key, month_name in MONTH_LOOKUP.items():

        if len(key) >= 3:

            if cleaned.startswith(
                key[:3]
            ):
                return month_name

    # Date parsing
    try:

        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if not pd.isna(parsed):
            return parsed.strftime("%b")

    except Exception:
        pass

    # Numeric month
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

    return text[:3].title()


# ============================================================
# MONTH ORDER VALUE
# ============================================================

def _month_order_value(month):

    try:
        return MONTH_ORDER.index(
            month
        )
    except ValueError:
        return 999


# ============================================================
# WARD NORMALISATION
# ============================================================

def _normalise_ward(value):

    if isinstance(value, pd.Series):
        return value.apply(_normalise_ward)

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

    # Standardise common formatting
    text = (
        text
        .upper()
        .replace(" ", "")
    )

    # Preserve normal ward values
    return text


# ============================================================
# WARD ORDER VALUE
# ============================================================

def _ward_order_value(ward):

    try:
        return WARD_ORDER.index(
            ward
        )
    except ValueError:
        return 999


# ============================================================
# COUNT TABLE
# ============================================================

def _count_table(
    df,
    group_column,
    output_column="Records",
):

    if (
        df is None
        or df.empty
        or group_column not in df.columns
    ):
        return pd.DataFrame(
            columns=[
                group_column,
                output_column,
            ]
        )

    working = df.copy()

    working[group_column] = (
        _clean_text_series(
            working[group_column]
        )
    )

    working = working[
        _valid_value_mask(
            working[group_column]
        )
    ].copy()

    if working.empty:
        return pd.DataFrame(
            columns=[
                group_column,
                output_column,
            ]
        )

    result = (
        working
        .groupby(
            group_column,
            dropna=False,
        )
        .size()
        .reset_index(
            name=output_column
        )
    )

    result = result.sort_values(
        output_column,
        ascending=False,
    ).reset_index(
        drop=True
    )

    return result


# ============================================================
# BAR CHART
# ============================================================

def _render_bar_chart(
    chart_data,
    x_column,
    y_column,
    title,
    height=450,
    horizontal=False,
):

    if (
        chart_data is None
        or chart_data.empty
    ):
        st.info(
            "No data available for this analysis."
        )
        return

    plot_df = chart_data.copy()

    if horizontal:

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=plot_df[x_column],
                y=plot_df[y_column],
                orientation="h",
                text=plot_df[x_column],
                textposition="outside",
                cliponaxis=False,
            )
        )

    else:

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=plot_df[x_column],
                y=plot_df[y_column],
                text=plot_df[y_column],
                textposition="outside",
                cliponaxis=False,
            )
        )

    fig.update_layout(
        title=title,
        height=height,
        margin=dict(
            l=20,
            r=40,
            t=60,
            b=40,
        ),
        xaxis_title=(
            x_column
            if not horizontal
            else ""
        ),
        yaxis_title=(
            y_column
            if not horizontal
            else ""
        ),
        showlegend=False,
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displayModeBar": False,
        },
    )


# ============================================================
# MONTH LINE CHART
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
            "No monthly data available."
        )
        return

    plot_df = chart_data.copy()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=plot_df["Month"],
            y=plot_df["Records"],
            mode="lines+markers+text",
            text=[
                str(int(v))
                if pd.notna(v)
                else ""
                for v in plot_df["Records"]
            ],
            textposition="top center",
            line=dict(
                width=2
            ),
            marker=dict(
                size=7
            ),
        )
    )

    fig.update_layout(
        title=title,
        height=height,
        margin=dict(
            l=20,
            r=30,
            t=60,
            b=40,
        ),
        xaxis=dict(
            categoryorder="array",
            categoryarray=MONTH_ORDER,
        ),
        yaxis=dict(
            title="Records",
            rangemode="tozero",
        ),
        showlegend=False,
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displayModeBar": False,
        },
    )


# ============================================================
# PREPARE WORKING DATA
# ============================================================

def _prepare_working_data(df):

    if df is None:
        return pd.DataFrame()

    if not isinstance(
        df,
        pd.DataFrame,
    ):
        return pd.DataFrame()

    if df.empty:
        return df.copy()

    work_df = df.copy()

    # --------------------------------------------------------
    # Month
    # --------------------------------------------------------

    month_col = _find_column(
        work_df,
        [
            "Month",
            "month",
            "MONTH",
        ],
    )

    if month_col:

        work_df["_LAB_MONTH"] = (
            _normalise_month(
                work_df[month_col]
            )
        )

    else:

        work_df["_LAB_MONTH"] = ""

    # --------------------------------------------------------
    # Ward
    # --------------------------------------------------------

    ward_col = _find_column(
        work_df,
        [
            "Ward",
            "Ward Name",
            "WARD",
        ],
    )

    if ward_col:

        work_df["_LAB_WARD"] = (
            _normalise_ward(
                work_df[ward_col]
            )
        )

    else:

        work_df["_LAB_WARD"] = ""

    return work_df


# ============================================================
# MONTHLY DATA
# ============================================================

def _ordered_month_chart_data(
    df,
    group_column=None,
):

    if (
        df is None
        or df.empty
        or "_LAB_MONTH" not in df.columns
    ):
        return pd.DataFrame()

    working = df.copy()

    working = working[
        working["_LAB_MONTH"].isin(
            MONTH_ORDER
        )
    ].copy()

    if working.empty:
        return pd.DataFrame()

    if group_column is None:

        monthly = (
            working
            .groupby(
                "_LAB_MONTH"
            )
            .size()
            .reset_index(
                name="Records"
            )
        )

        monthly = monthly.rename(
            columns={
                "_LAB_MONTH": "Month"
            }
        )

        monthly["_order"] = (
            monthly["Month"]
            .apply(
                _month_order_value
            )
        )

        monthly = (
            monthly
            .sort_values("_order")
            .drop(
                columns="_order"
            )
            .reset_index(
                drop=True
            )
        )

        return monthly

    if group_column not in working.columns:
        return pd.DataFrame()

    working[group_column] = (
        _clean_text_series(
            working[group_column]
        )
    )

    working = working[
        _valid_value_mask(
            working[group_column]
        )
    ].copy()

    if working.empty:
        return pd.DataFrame()

    result = (
        working
        .groupby(
            [
                "_LAB_MONTH",
                group_column,
            ]
        )
        .size()
        .reset_index(
            name="Records"
        )
    )

    result = result.rename(
        columns={
            "_LAB_MONTH": "Month"
        }
    )

    result["_order"] = (
        result["Month"]
        .apply(
            _month_order_value
        )
    )

    result = (
        result
        .sort_values(
            [
                "_order",
                group_column,
            ]
        )
        .drop(
            columns="_order"
        )
        .reset_index(
            drop=True
        )
    )

    return result


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_lab_pathogen(df):

    st.header(
        "Laboratory & Pathogen Analysis"
    )

    st.caption(
        "Laboratory testing and pathogen distribution analysis "
        "based on the currently filtered programme records."
    )

    # --------------------------------------------------------
    # VALIDATE DATA
    # --------------------------------------------------------

    if (
        df is None
        or not isinstance(
            df,
            pd.DataFrame
        )
        or df.empty
    ):

        st.warning(
            "No records are available for the selected filters."
        )

        return

    work_df = _prepare_working_data(
        df
    )

    # ========================================================
    # IDENTIFY IMPORTANT COLUMNS
    # ========================================================

    test_col = _find_column(
        work_df,
        [
            "Test Performed",
            "Test performed",
            "TEST PERFORMED",
        ],
    )

    pathogen_col = _find_column(
        work_df,
        [
            "Pathogen Name",
            "Pathogen name",
            "PATHOGEN NAME",
        ],
    )

    facility_col = _find_column(
        work_df,
        [
            "Facility Name Lform",
            "Facility Name",
            "Facility",
        ],
    )

    ward_col = _find_column(
        work_df,
        [
            "Ward",
            "Ward Name",
        ],
    )

    # ========================================================
    # 1. SUMMARY KPIs
    # ========================================================

    st.subheader(
        "Laboratory & Pathogen Summary"
    )

    total_records = len(work_df)

    test_records = 0
    unique_tests = 0

    pathogen_records = 0
    unique_pathogens = 0

    top_test = "Not available"
    top_pathogen = "Not available"

    if test_col:

        valid_tests = work_df[
            _valid_value_mask(
                work_df[test_col]
            )
        ].copy()

        test_records = len(
            valid_tests
        )

        if test_records > 0:

            test_counts = (
                _clean_text_series(
                    valid_tests[test_col]
                )
                .value_counts()
            )

            unique_tests = (
                test_counts.shape[0]
            )

            if not test_counts.empty:

                top_test = str(
                    test_counts.index[0]
                )

    if pathogen_col:

        valid_pathogens = work_df[
            _valid_value_mask(
                work_df[pathogen_col]
            )
        ].copy()

        pathogen_records = len(
            valid_pathogens
        )

        if pathogen_records > 0:

            pathogen_counts = (
                _clean_text_series(
                    valid_pathogens[
                        pathogen_col
                    ]
                )
                .value_counts()
            )

            unique_pathogens = (
                pathogen_counts.shape[0]
            )

            if not pathogen_counts.empty:

                top_pathogen = str(
                    pathogen_counts.index[0]
                )

    k1, k2, k3, k4, k5, k6 = st.columns(
        6
    )

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
            f"{unique_tests:,}",
        )

    with k4:

        st.metric(
            "Pathogen Types",
            f"{unique_pathogens:,}",
        )

    with k5:

        st.metric(
            "Top Test",
            top_test,
        )

    with k6:

        st.metric(
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

    if not test_col:

        st.warning(
            "The 'Test Performed' column is not available."
        )

    else:

        test_table = _count_table(
            work_df,
            test_col,
            "Records",
        )

        if test_table.empty:

            st.info(
                "No laboratory test information is available."
            )

        else:

            test_table = test_table.rename(
                columns={
                    test_col: "Test Performed"
                }
            )

            chart_table = (
                test_table
                .head(20)
                .sort_values(
                    "Records",
                    ascending=True,
                )
            )

            _render_bar_chart(
                chart_table,
                x_column="Records",
                y_column="Test Performed",
                title="Laboratory Tests by Test Performed",
                height=650,
                horizontal=True,
            )

            st.dataframe(
                test_table,
                width="stretch",
                hide_index=True,
            )

    st.divider()

    # ========================================================
    # 3. PATHOGEN NAME-WISE ANALYSIS
    # ========================================================

    st.subheader(
        "Pathogen Name-wise Analysis"
    )

    if not pathogen_col:

        st.warning(
            "The 'Pathogen Name' column is not available."
        )

    else:

        pathogen_table = _count_table(
            work_df,
            pathogen_col,
            "Records",
        )

        if pathogen_table.empty:

            st.info(
                "No pathogen information is available."
            )

        else:

            pathogen_table = pathogen_table.rename(
                columns={
                    pathogen_col: "Pathogen Name"
                }
            )

            chart_table = (
                pathogen_table
                .head(20)
                .sort_values(
                    "Records",
                    ascending=True,
                )
            )

            _render_bar_chart(
                chart_table,
                x_column="Records",
                y_column="Pathogen Name",
                title="Pathogen Distribution",
                height=650,
                horizontal=True,
            )

            st.dataframe(
                pathogen_table,
                width="stretch",
                hide_index=True,
            )

    st.divider()

    # ========================================================
    # 4. TEST × PATHOGEN ANALYSIS
    # ========================================================

    st.subheader(
        "Test × Pathogen Analysis"
    )

    if not test_col or not pathogen_col:

        st.warning(
            "Both 'Test Performed' and 'Pathogen Name' "
            "columns are required for this analysis."
        )

    else:

        cross_df = work_df.copy()

        cross_df["_TEST"] = (
            _clean_text_series(
                cross_df[test_col]
            )
        )

        cross_df["_PATHOGEN"] = (
            _clean_text_series(
                cross_df[pathogen_col]
            )
        )

        cross_df = cross_df[
            _valid_value_mask(
                cross_df["_TEST"]
            )
            & _valid_value_mask(
                cross_df["_PATHOGEN"]
            )
        ].copy()

        if cross_df.empty:

            st.info(
                "No Test × Pathogen records are available."
            )

        else:

            cross_table = (
                cross_df
                .groupby(
                    [
                        "_TEST",
                        "_PATHOGEN",
                    ]
                )
                .size()
                .reset_index(
                    name="Records"
                )
            )

            cross_table = cross_table.rename(
                columns={
                    "_TEST": "Test Performed",
                    "_PATHOGEN": "Pathogen Name",
                }
            )

            cross_table = (
                cross_table
                .sort_values(
                    "Records",
                    ascending=False,
                )
                .reset_index(
                    drop=True
                )
            )

            st.dataframe(
                cross_table,
                width="stretch",
                hide_index=True,
            )

    st.divider()

    # ========================================================
    # 5. MONTH-WISE LABORATORY TEST TREND
    # ========================================================

    st.subheader(
        "Month-wise Laboratory Test Trend"
    )

    if not test_col:

        st.warning(
            "The 'Test Performed' column is not available."
        )

    else:

        monthly_test = _ordered_month_chart_data(
            work_df,
            test_col,
        )

        if monthly_test.empty:

            st.info(
                "Monthly laboratory test data is not available."
            )

        else:

            _render_month_line_chart(
                monthly_test,
                "Month-wise Laboratory Test Trend",
            )

            st.dataframe(
                monthly_test,
                width="stretch",
                hide_index=True,
            )

    st.divider()

    # ========================================================
    # 6. MONTH-WISE PATHOGEN TREND
    # ========================================================

    st.subheader(
        "Month-wise Pathogen Trend"
    )

    if not pathogen_col:

        st.warning(
            "The 'Pathogen Name' column is not available."
        )

    else:

        monthly_pathogen = (
            _ordered_month_chart_data(
                work_df,
                pathogen_col,
            )
        )

        if monthly_pathogen.empty:

            st.info(
                "Monthly pathogen data is not available."
            )

        else:

            _render_month_line_chart(
                monthly_pathogen,
                "Month-wise Pathogen Trend",
            )

            st.dataframe(
                monthly_pathogen,
                width="stretch",
                hide_index=True,
            )

    st.divider()

    # ========================================================
    # 7. SELECTED LABORATORY ITEM TREND
    # ========================================================

    st.subheader(
        "Selected Laboratory Item Trend"
    )

    selectable_items = []

    item_mapping = {}

    if test_col:

        test_values = (
            _clean_text_series(
                work_df[test_col]
            )
        )

        test_values = test_values[
            _valid_value_mask(
                test_values
            )
        ].unique()

        for value in test_values:

            display_name = (
                f"Test: {value}"
            )

            selectable_items.append(
                display_name
            )

            item_mapping[
                display_name
            ] = (
                "Test Performed",
                str(value),
            )

    if pathogen_col:

        pathogen_values = (
            _clean_text_series(
                work_df[pathogen_col]
            )
        )

        pathogen_values = pathogen_values[
            _valid_value_mask(
                pathogen_values
            )
        ].unique()

        for value in pathogen_values:

            display_name = (
                f"Pathogen: {value}"
            )

            selectable_items.append(
                display_name
            )

            item_mapping[
                display_name
            ] = (
                "Pathogen Name",
                str(value),
            )

    if not selectable_items:

        st.info(
            "No laboratory or pathogen items are available."
        )

    else:

        selected_items = st.multiselect(
            "Select Test Performed or Pathogen Name",
            options=selectable_items,
            default=selectable_items[
                :1
            ],
            key="lab_selected_items",
        )

        if not selected_items:

            st.info(
                "Select at least one laboratory item."
            )

        else:

            fig = go.Figure()

            for selected_item in selected_items:

                item_type, item_value = (
                    item_mapping[
                        selected_item
                    ]
                )

                if item_type == "Test Performed":

                    if not test_col:
                        continue

                    mask = (
                        _clean_text_series(
                            work_df[test_col]
                        )
                        == item_value
                    )

                else:

                    if not pathogen_col:
                        continue

                    mask = (
                        _clean_text_series(
                            work_df[pathogen_col]
                        )
                        == item_value
                    )

                selected_df = (
                    work_df[
                        mask
                    ].copy()
                )

                if selected_df.empty:
                    continue

                monthly_selected = (
                    selected_df[
                        "_LAB_MONTH"
                    ]
                    .value_counts()
                    .reindex(
                        MONTH_ORDER,
                        fill_value=0,
                    )
                    .reset_index()
                )

                monthly_selected.columns = [
                    "Month",
                    "Records",
                ]

                # Zero values are intentionally not labelled
                # to keep multi-item trend charts readable.
                labels = [
                    str(int(value))
                    if value > 0
                    else ""
                    for value
                    in monthly_selected[
                        "Records"
                    ]
                ]

                fig.add_trace(
                    go.Scatter(
                        x=monthly_selected[
                            "Month"
                        ],
                        y=monthly_selected[
                            "Records"
                        ],
                        mode=(
                            "lines+markers+text"
                        ),
                        name=selected_item,
                        text=labels,
                        textposition=(
                            "top center"
                        ),
                        marker=dict(
                            size=7
                        ),
                    )
                )

            fig.update_layout(
                title=(
                    "Selected Laboratory Item "
                    "Monthly Trend"
                ),
                height=480,
                margin=dict(
                    l=20,
                    r=30,
                    t=60,
                    b=40,
                ),
                xaxis=dict(
                    categoryorder="array",
                    categoryarray=MONTH_ORDER,
                ),
                yaxis=dict(
                    title="Records",
                    rangemode="tozero",
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
                width="stretch",
                config={
                    "displayModeBar": False,
                },
            )

    st.divider()

    # ========================================================
    # 8. FACILITY-WISE LABORATORY ANALYSIS
    # ========================================================

    st.subheader(
        "Facility-wise Laboratory Analysis"
    )

    if not facility_col:

        st.warning(
            "Facility information is not available."
        )

    else:

        facility_df = work_df.copy()

        facility_df["_FACILITY"] = (
            _clean_text_series(
                facility_df[facility_col]
            )
        )

        facility_df = facility_df[
            _valid_value_mask(
                facility_df["_FACILITY"]
            )
        ].copy()

        if facility_df.empty:

            st.info(
                "No facility-wise laboratory data is available."
            )

        else:

            facility_test = (
                facility_df
                .groupby(
                    "_FACILITY"
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .sort_values(
                    "Records",
                    ascending=False,
                )
                .reset_index(
                    drop=True
                )
            )

            facility_test = facility_test.rename(
                columns={
                    "_FACILITY": "Facility Name"
                }
            )

            chart_table = (
                facility_test
                .head(20)
                .sort_values(
                    "Records",
                    ascending=True,
                )
            )

            _render_bar_chart(
                chart_table,
                x_column="Records",
                y_column="Facility Name",
                title="Top 20 Facilities by Laboratory Records",
                height=700,
                horizontal=True,
            )

            st.dataframe(
                facility_test,
                width="stretch",
                hide_index=True,
            )

    st.divider()

    # ========================================================
    # 9. WARD-WISE LABORATORY ANALYSIS
    # ========================================================

    st.subheader(
        "Ward-wise Laboratory Analysis"
    )

    if not ward_col:

        st.warning(
            "Ward information is not available."
        )

    else:

        ward_df = work_df.copy()

        ward_df["_WARD"] = (
            _normalise_ward(
                ward_df[ward_col]
            )
        )

        ward_df = ward_df[
            _valid_value_mask(
                ward_df["_WARD"]
            )
        ].copy()

        if ward_df.empty:

            st.info(
                "No ward-wise laboratory data is available."
            )

        else:

            ward_table = (
                ward_df
                .groupby(
                    "_WARD"
                )
                .size()
                .reset_index(
                    name="Records"
                )
            )

            ward_table = ward_table.rename(
                columns={
                    "_WARD": "Ward"
                }
            )

            ward_table["_order"] = (
                ward_table["Ward"]
                .apply(
                    _ward_order_value
                )
            )

            ward_table = (
                ward_table
                .sort_values(
                    [
                        "Records",
                        "_order",
                    ],
                    ascending=[
                        False,
                        True,
                    ],
                )
                .drop(
                    columns="_order"
                )
                .reset_index(
                    drop=True
                )
            )

            chart_table = (
                ward_table
                .head(24)
                .sort_values(
                    "Records",
                    ascending=True,
                )
            )

            _render_bar_chart(
                chart_table,
                x_column="Records",
                y_column="Ward",
                title="Laboratory Records by Ward",
                height=700,
                horizontal=True,
            )

            st.dataframe(
                ward_table,
                width="stretch",
                hide_index=True,
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
        "Year",
        "Month",
        "Week",
        "MSU Unique Code",
        "Form Type",
        "Reporting Date",
        "Date Of Onset",
        "Gender",
        "Age",
        "Patient Address",
        "Ward",
        "Confirmed Diagnosis",
        "Opd Ipd",
        "Test Performed",
        "Pathogen Name",
        "Facility Name Lform",
        "Facility Type",
        "PUBLIC / PRIVATE FACILITIES",
    ]

    for column in preferred_columns:

        if column in df.columns:
            detail_columns.append(
                column
            )

    if not detail_columns:

        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
        )

    else:

        detail_df = df[
            detail_columns
        ].copy()

        st.dataframe(
            detail_df,
            width="stretch",
            hide_index=True,
            height=500,
        )

    st.caption(
        f"Laboratory analysis based on "
        f"{len(work_df):,} filtered records."
    )
