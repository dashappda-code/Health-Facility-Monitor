import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

from chart_helpers import data_labels_enabled


# ============================================================
# CONFIGURATION
# ============================================================

MONTH_NAMES = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

MIN_YEAR = 2000
MAX_YEAR = 2100

DATA_LABEL_FONT_SIZE = 11

SERIES_COLORS = [
    "#1F77B4",
    "#FF7F0E",
    "#2CA02C",
    "#D62728",
    "#9467BD",
    "#8C564B",
    "#E377C2",
    "#7F7F7F",
    "#BCBD22",
    "#17BECF",
    "#393B79",
    "#637939",
    "#8C6D31",
    "#843C39",
    "#7B4173",
    "#3182BD",
    "#31A354",
    "#756BB1",
    "#636363",
    "#E6550D",
]


# ============================================================
# COMMON HELPERS
# ============================================================

def _clean_series(series):

    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _valid_text_values(series):

    values = _clean_series(series)

    return values[
        values.ne("")
        & values.ne("nan")
        & values.ne("NaT")
        & values.ne("None")
    ]


def _month_number(value):

    if pd.isna(value):
        return np.nan

    text = str(value).strip().lower()

    month_map = {
        "january": 1,
        "jan": 1,
        "1": 1,
        "01": 1,

        "february": 2,
        "feb": 2,
        "2": 2,
        "02": 2,

        "march": 3,
        "mar": 3,
        "3": 3,
        "03": 3,

        "april": 4,
        "apr": 4,
        "4": 4,
        "04": 4,

        "may": 5,
        "5": 5,
        "05": 5,

        "june": 6,
        "jun": 6,
        "6": 6,
        "06": 6,

        "july": 7,
        "jul": 7,
        "7": 7,
        "07": 7,

        "august": 8,
        "aug": 8,
        "8": 8,
        "08": 8,

        "september": 9,
        "sep": 9,
        "sept": 9,
        "9": 9,
        "09": 9,

        "october": 10,
        "oct": 10,
        "10": 10,

        "november": 11,
        "nov": 11,
        "11": 11,

        "december": 12,
        "dec": 12,
        "12": 12,
    }

    if text in month_map:
        return month_map[text]

    try:

        number = int(float(text))

        if 1 <= number <= 12:
            return number

    except Exception:
        pass

    return np.nan


def _next_month(year, month):

    if month == 12:
        return year + 1, 1

    return year, month + 1


def _safe_percent_change(current, previous):

    if previous is None:
        return None

    if previous == 0:
        return None

    return (
        (current - previous)
        / previous
        * 100
    )


def _series_color_map(series_names):

    return {
        name: SERIES_COLORS[
            index % len(SERIES_COLORS)
        ]
        for index, name in enumerate(series_names)
    }


# ============================================================
# CHECKBOX MULTISELECT
# ============================================================

def _checkbox_multiselect(
    label,
    options,
    key_prefix,
    default_count=None,
):

    options = list(options)

    if not options:
        return []

    init_key = f"{key_prefix}_initialized"
    select_all_key = f"{key_prefix}_select_all"

    option_keys = [
        f"{key_prefix}_option_{index}"
        for index in range(len(options))
    ]

    if init_key not in st.session_state:

        st.session_state[init_key] = True

        if (
            default_count is None
            or default_count >= len(options)
        ):

            st.session_state[
                select_all_key
            ] = True

            for option_key in option_keys:
                st.session_state[
                    option_key
                ] = True

        else:

            st.session_state[
                select_all_key
            ] = False

            for index, option_key in enumerate(
                option_keys
            ):

                st.session_state[
                    option_key
                ] = (
                    index < default_count
                )

    def select_all_changed():

        selected = bool(
            st.session_state.get(
                select_all_key,
                False,
            )
        )

        for option_key in option_keys:

            st.session_state[
                option_key
            ] = selected

    def individual_changed():

        all_selected = all(
            bool(
                st.session_state.get(
                    option_key,
                    False,
                )
            )
            for option_key in option_keys
        )

        st.session_state[
            select_all_key
        ] = all_selected

    selected_options = []

    with st.popover(
        label,
        use_container_width=True,
    ):

        st.checkbox(
            "Select All",
            key=select_all_key,
            on_change=select_all_changed,
        )

        st.divider()

        for index, option in enumerate(options):

            checked = st.checkbox(
                str(option),
                key=option_keys[index],
                on_change=individual_changed,
            )

            if checked:
                selected_options.append(
                    option
                )

    return selected_options


# ============================================================
# PREPARE TIME DATA
# ============================================================

def _prepare_time_data(df):

    if df is None or df.empty:
        return pd.DataFrame()

    temp = df.copy()

    # --------------------------------------------------------
    # YEAR
    # --------------------------------------------------------

    if "Year" in temp.columns:

        temp["Year_Number"] = pd.to_numeric(
            temp["Year"],
            errors="coerce",
        )

    elif "Reporting Date" in temp.columns:

        reporting_date = pd.to_datetime(
            temp["Reporting Date"],
            errors="coerce",
            dayfirst=True,
        )

        temp["Year_Number"] = (
            reporting_date.dt.year
        )

    else:
        return pd.DataFrame()

    # --------------------------------------------------------
    # MONTH
    # --------------------------------------------------------

    if "Month" in temp.columns:

        temp["Month_Number"] = (
            temp["Month"]
            .map(_month_number)
        )

    elif "Reporting Date" in temp.columns:

        reporting_date = pd.to_datetime(
            temp["Reporting Date"],
            errors="coerce",
            dayfirst=True,
        )

        temp["Month_Number"] = (
            reporting_date.dt.month
        )

    else:
        return pd.DataFrame()

    temp = temp[
        temp["Year_Number"].between(
            MIN_YEAR,
            MAX_YEAR,
        )
        & temp["Month_Number"].between(
            1,
            12,
        )
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    temp["Year_Number"] = (
        temp["Year_Number"]
        .astype(int)
    )

    temp["Month_Number"] = (
        temp["Month_Number"]
        .astype(int)
    )

    temp["Period_Date"] = pd.to_datetime(
        dict(
            year=temp["Year_Number"],
            month=temp["Month_Number"],
            day=1,
        ),
        errors="coerce",
    )

    temp["Period"] = (
        temp["Period_Date"]
        .dt.strftime("%b-%Y")
    )

    temp = temp.sort_values(
        [
            "Year_Number",
            "Month_Number",
        ]
    )

    return temp.reset_index(drop=True)


# ============================================================
# MONTHLY COUNTS
# ============================================================

def _monthly_counts(
    source,
    start_date=None,
    end_date=None,
):

    if source is None or source.empty:
        return pd.DataFrame()

    monthly = (
        source
        .groupby(
            [
                "Year_Number",
                "Month_Number",
            ],
            observed=True,
        )
        .size()
        .reset_index(
            name="Records"
        )
    )

    if monthly.empty:
        return pd.DataFrame()

    monthly = monthly.sort_values(
        [
            "Year_Number",
            "Month_Number",
        ]
    )

    first_row = monthly.iloc[0]
    last_row = monthly.iloc[-1]

    if start_date is None:

        start_date = pd.Timestamp(
            year=int(
                first_row[
                    "Year_Number"
                ]
            ),
            month=int(
                first_row[
                    "Month_Number"
                ]
            ),
            day=1,
        )

    if end_date is None:

        end_date = pd.Timestamp(
            year=int(
                last_row[
                    "Year_Number"
                ]
            ),
            month=int(
                last_row[
                    "Month_Number"
                ]
            ),
            day=1,
        )

    full_dates = pd.date_range(
        start=start_date,
        end=end_date,
        freq="MS",
    )

    complete = pd.DataFrame(
        {
            "Period_Date": full_dates
        }
    )

    complete["Year_Number"] = (
        complete[
            "Period_Date"
        ].dt.year
    )

    complete["Month_Number"] = (
        complete[
            "Period_Date"
        ].dt.month
    )

    complete = complete.merge(
        monthly,
        how="left",
        on=[
            "Year_Number",
            "Month_Number",
        ],
    )

    complete["Records"] = (
        complete["Records"]
        .fillna(0)
        .astype(int)
    )

    complete["Period"] = (
        complete["Period_Date"]
        .dt.strftime("%b-%Y")
    )

    return complete


# ============================================================
# YEARLY COUNTS
# ============================================================

def _yearly_counts(source):

    if source is None or source.empty:
        return pd.DataFrame()

    yearly = (
        source
        .groupby(
            "Year_Number",
            observed=True,
        )
        .size()
        .reset_index(
            name="Records"
        )
        .sort_values(
            "Year_Number"
        )
    )

    yearly["Year"] = (
        yearly[
            "Year_Number"
        ]
        .astype(int)
        .astype(str)
    )

    return yearly.reset_index(
        drop=True
    )


# ============================================================
# PROJECTION MODEL
# ============================================================

def _calculate_projection(values):

    numeric = pd.to_numeric(
        values,
        errors="coerce",
    )

    numeric = numeric[
        np.isfinite(numeric)
    ].reset_index(drop=True)

    if numeric.empty:
        return None

    if len(numeric) == 1:

        return max(
            0.0,
            float(
                numeric.iloc[-1]
            ),
        )

    recent = numeric.tail(
        min(
            3,
            len(numeric),
        )
    )

    weights = np.arange(
        1,
        len(recent) + 1,
        dtype=float,
    )

    recent_weighted = float(
        np.average(
            recent.to_numpy(
                dtype=float
            ),
            weights=weights,
        )
    )

    x = np.arange(
        len(numeric),
        dtype=float,
    )

    try:

        slope, intercept = np.polyfit(
            x,
            numeric.to_numpy(
                dtype=float
            ),
            1,
        )

        trend_projection = (
            slope * len(numeric)
            + intercept
        )

    except Exception:

        trend_projection = (
            recent_weighted
        )

    projection = (
        recent_weighted * 0.70
        + trend_projection * 0.30
    )

    return max(
        0.0,
        float(projection),
    )


# ============================================================
# MULTI-PERIOD PROJECTION
# ============================================================

def _project_multiple_periods(
    values,
    periods,
):

    working_values = list(
        pd.to_numeric(
            values,
            errors="coerce",
        )
        .dropna()
        .astype(float)
    )

    projections = []

    for _ in range(periods):

        projected = (
            _calculate_projection(
                pd.Series(
                    working_values
                )
            )
        )

        if projected is None:
            break

        projections.append(
            projected
        )

        working_values.append(
            projected
        )

    return projections


# ============================================================
# STANDARD LINE CHART
# ============================================================

def _render_line_chart(
    dataframe,
    x_column,
    y_columns,
    title=None,
    height=430,
):

    if dataframe is None or dataframe.empty:
        return

    chart_df = dataframe.copy()

    if x_column not in chart_df.columns:
        return

    valid_y_columns = [
        column
        for column in y_columns
        if column in chart_df.columns
    ]

    if not valid_y_columns:
        return

    long_df = chart_df.melt(
        id_vars=[x_column],
        value_vars=valid_y_columns,
        var_name="Series",
        value_name="Value",
    )

    long_df["Value"] = pd.to_numeric(
        long_df["Value"],
        errors="coerce",
    )

    long_df = long_df.dropna(
        subset=["Value"]
    )

    if long_df.empty:
        return

    series_order = (
        long_df["Series"]
        .drop_duplicates()
        .tolist()
    )

    color_map = (
        _series_color_map(
            series_order
        )
    )

    color_scale = alt.Scale(
        domain=series_order,
        range=[
            color_map[
                series
            ]
            for series in series_order
        ],
    )

    base = alt.Chart(
        long_df
    )

    lines = (
        base
        .mark_line(
            point=True,
            strokeWidth=3,
        )
        .encode(
            x=alt.X(
                f"{x_column}:N",
                sort=None,
                axis=alt.Axis(
                    title=x_column,
                    labelAngle=-45,
                    labelLimit=150,
                ),
            ),
            y=alt.Y(
                "Value:Q",
                axis=alt.Axis(
                    title="Records"
                ),
            ),
            color=alt.Color(
                "Series:N",
                scale=color_scale,
                legend=alt.Legend(
                    orient="bottom",
                    direction="horizontal",
                    title=None,
                    columns=5,
                    labelLimit=300,
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{x_column}:N",
                    title=x_column,
                ),
                alt.Tooltip(
                    "Series:N",
                    title="Series",
                ),
                alt.Tooltip(
                    "Value:Q",
                    title="Records",
                    format=",.1f",
                ),
            ],
        )
    )

    chart = lines

    if data_labels_enabled():

        labels = (
            base
            .mark_text(
                dy=-10,
                fontSize=DATA_LABEL_FONT_SIZE,
                fontWeight="bold",
            )
            .encode(
                x=alt.X(
                    f"{x_column}:N",
                    sort=None,
                ),
                y=alt.Y(
                    "Value:Q"
                ),
                text=alt.Text(
                    "Value:Q",
                    format=",.0f",
                ),
                color=alt.Color(
                    "Series:N",
                    scale=color_scale,
                    legend=None,
                ),
            )
        )

        chart = (
            lines
            + labels
        )

    chart = chart.properties(
        height=height,
        title=title,
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# HISTORICAL + PROJECTED MULTI-SERIES CHART
# ============================================================

def _render_projection_chart(
    dataframe,
    title=None,
    height=500,
):

    if dataframe is None or dataframe.empty:
        return

    required_columns = {
        "Period",
        "Series",
        "Value",
        "Type",
        "Period_Order",
    }

    if not required_columns.issubset(
        dataframe.columns
    ):
        return

    chart_df = dataframe.copy()

    chart_df["Value"] = pd.to_numeric(
        chart_df["Value"],
        errors="coerce",
    )

    chart_df = chart_df.dropna(
        subset=["Value"]
    )

    if chart_df.empty:
        return

    chart_df = chart_df.sort_values(
        [
            "Period_Order",
            "Series",
            "Type",
        ]
    )

    series_order = (
        chart_df["Series"]
        .drop_duplicates()
        .tolist()
    )

    color_map = (
        _series_color_map(
            series_order
        )
    )

    color_scale = alt.Scale(
        domain=series_order,
        range=[
            color_map[
                series
            ]
            for series in series_order
        ],
    )

    historical_df = chart_df[
        chart_df["Type"]
        == "Historical"
    ].copy()

    projected_df = chart_df[
        chart_df["Type"]
        == "Projected"
    ].copy()

    layers = []

    if not historical_df.empty:

        historical_line = (
            alt.Chart(
                historical_df
            )
            .mark_line(
                point=True,
                strokeWidth=3,
            )
            .encode(
                x=alt.X(
                    "Period:N",
                    sort=alt.SortField(
                        field="Period_Order",
                        order="ascending",
                    ),
                    axis=alt.Axis(
                        title="Period",
                        labelAngle=-45,
                        labelLimit=150,
                    ),
                ),
                y=alt.Y(
                    "Value:Q",
                    axis=alt.Axis(
                        title="Records"
                    ),
                ),
                color=alt.Color(
                    "Series:N",
                    scale=color_scale,
                    legend=alt.Legend(
                        title=None,
                        orient="bottom",
                        direction="horizontal",
                        columns=5,
                        labelLimit=300,
                    ),
                ),
                detail="Series:N",
                tooltip=[
                    alt.Tooltip(
                        "Period:N",
                        title="Period",
                    ),
                    alt.Tooltip(
                        "Series:N",
                        title="Series",
                    ),
                    alt.Tooltip(
                        "Type:N",
                        title="Type",
                    ),
                    alt.Tooltip(
                        "Value:Q",
                        title="Records",
                        format=",.1f",
                    ),
                ],
            )
        )

        layers.append(
            historical_line
        )

        if data_labels_enabled():

            historical_labels = (
                alt.Chart(
                    historical_df
                )
                .mark_text(
                    dy=-10,
                    fontSize=DATA_LABEL_FONT_SIZE,
                    fontWeight="bold",
                )
                .encode(
                    x=alt.X(
                        "Period:N",
                        sort=alt.SortField(
                            field="Period_Order",
                            order="ascending",
                        ),
                    ),
                    y=alt.Y(
                        "Value:Q"
                    ),
                    text=alt.Text(
                        "Value:Q",
                        format=",.0f",
                    ),
                    color=alt.Color(
                        "Series:N",
                        scale=color_scale,
                        legend=None,
                    ),
                    detail="Series:N",
                )
            )

            layers.append(
                historical_labels
            )

    if not projected_df.empty:

        projected_line = (
            alt.Chart(
                projected_df
            )
            .mark_line(
                point=True,
                strokeWidth=3,
                strokeDash=[7, 5],
            )
            .encode(
                x=alt.X(
                    "Period:N",
                    sort=alt.SortField(
                        field="Period_Order",
                        order="ascending",
                    ),
                    axis=alt.Axis(
                        title="Period",
                        labelAngle=-45,
                        labelLimit=150,
                    ),
                ),
                y=alt.Y(
                    "Value:Q",
                    axis=alt.Axis(
                        title="Records"
                    ),
                ),
                color=alt.Color(
                    "Series:N",
                    scale=color_scale,
                    legend=alt.Legend(
                        title=None,
                        orient="bottom",
                        direction="horizontal",
                        columns=5,
                        labelLimit=300,
                    ),
                ),
                detail="Series:N",
                tooltip=[
                    alt.Tooltip(
                        "Period:N",
                        title="Period",
                    ),
                    alt.Tooltip(
                        "Series:N",
                        title="Series",
                    ),
                    alt.Tooltip(
                        "Type:N",
                        title="Type",
                    ),
                    alt.Tooltip(
                        "Value:Q",
                        title="Projected Records",
                        format=",.1f",
                    ),
                ],
            )
        )

        layers.append(
            projected_line
        )

        if data_labels_enabled():

            projected_labels = (
                alt.Chart(
                    projected_df
                )
                .mark_text(
                    dy=-11,
                    fontSize=DATA_LABEL_FONT_SIZE,
                    fontWeight="bold",
                )
                .encode(
                    x=alt.X(
                        "Period:N",
                        sort=alt.SortField(
                            field="Period_Order",
                            order="ascending",
                        ),
                    ),
                    y=alt.Y(
                        "Value:Q"
                    ),
                    text=alt.Text(
                        "Value:Q",
                        format=",.0f",
                    ),
                    color=alt.Color(
                        "Series:N",
                        scale=color_scale,
                        legend=None,
                    ),
                    detail="Series:N",
                )
            )

            layers.append(
                projected_labels
            )

    if not layers:
        return

    chart = alt.layer(
        *layers
    ).properties(
        height=height,
        title=title,
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )

    st.caption(
        "Solid line = historical records • "
        "Dotted line = projected records"
    )


# ============================================================
# BUILD MONTHLY PROJECTION SERIES
# ============================================================

def _build_monthly_projection_series(
    source,
    series_name,
    projection_months=1,
):

    monthly = _monthly_counts(
        source
    )

    if monthly.empty:
        return pd.DataFrame()

    rows = []

    for index, row in monthly.iterrows():

        rows.append(
            {
                "Period": row["Period"],
                "Period_Order": (
                    row["Period_Date"]
                ),
                "Series": series_name,
                "Value": float(
                    row["Records"]
                ),
                "Type": "Historical",
            }
        )

    projected_values = (
        _project_multiple_periods(
            monthly["Records"],
            projection_months,
        )
    )

    if not projected_values:
        return pd.DataFrame(rows)

    last_row = monthly.iloc[-1]

    year = int(
        last_row["Year_Number"]
    )

    month = int(
        last_row["Month_Number"]
    )

    # --------------------------------------------------------
    # Add historical endpoint to projected line so dotted line
    # visibly starts from the latest actual observation.
    # --------------------------------------------------------

    rows.append(
        {
            "Period": last_row[
                "Period"
            ],
            "Period_Order": last_row[
                "Period_Date"
            ],
            "Series": series_name,
            "Value": float(
                last_row["Records"]
            ),
            "Type": "Projected",
        }
    )

    for value in projected_values:

        year, month = _next_month(
            year,
            month,
        )

        period_date = pd.Timestamp(
            year=year,
            month=month,
            day=1,
        )

        rows.append(
            {
                "Period": (
                    period_date
                    .strftime("%b-%Y")
                ),
                "Period_Order": (
                    period_date
                ),
                "Series": series_name,
                "Value": float(value),
                "Type": "Projected",
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# BUILD YEARLY PROJECTION SERIES
# ============================================================

def _build_yearly_projection_series(
    source,
    series_name,
    projection_years=1,
):

    yearly = _yearly_counts(
        source
    )

    if yearly.empty:
        return pd.DataFrame()

    rows = []

    for _, row in yearly.iterrows():

        year = int(
            row["Year_Number"]
        )

        rows.append(
            {
                "Period": str(year),
                "Period_Order": (
                    pd.Timestamp(
                        year=year,
                        month=1,
                        day=1,
                    )
                ),
                "Series": series_name,
                "Value": float(
                    row["Records"]
                ),
                "Type": "Historical",
            }
        )

    projected_values = (
        _project_multiple_periods(
            yearly["Records"],
            projection_years,
        )
    )

    if not projected_values:
        return pd.DataFrame(rows)

    last_row = yearly.iloc[-1]

    last_year = int(
        last_row["Year_Number"]
    )

    rows.append(
        {
            "Period": str(
                last_year
            ),
            "Period_Order": (
                pd.Timestamp(
                    year=last_year,
                    month=1,
                    day=1,
                )
            ),
            "Series": series_name,
            "Value": float(
                last_row["Records"]
            ),
            "Type": "Projected",
        }
    )

    for index, value in enumerate(
        projected_values,
        start=1,
    ):

        year = (
            last_year
            + index
        )

        rows.append(
            {
                "Period": str(year),
                "Period_Order": (
                    pd.Timestamp(
                        year=year,
                        month=1,
                        day=1,
                    )
                ),
                "Series": series_name,
                "Value": float(value),
                "Type": "Projected",
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# BUILD PROJECTION SERIES
# ============================================================

def _build_projection_series(
    source,
    series_name,
    projection_mode,
):

    if projection_mode == "Next Month":

        return (
            _build_monthly_projection_series(
                source=source,
                series_name=series_name,
                projection_months=1,
            )
        )

    if projection_mode == "Next 12 Months":

        return (
            _build_monthly_projection_series(
                source=source,
                series_name=series_name,
                projection_months=12,
            )
        )

    return (
        _build_yearly_projection_series(
            source=source,
            series_name=series_name,
            projection_years=1,
        )
    )


# ============================================================
# PROJECTION SUMMARY TABLE FROM CHART DATA
# ============================================================

def _projection_summary_from_chart(
    chart_df,
    category_title,
):

    if chart_df is None or chart_df.empty:
        return pd.DataFrame()

    rows = []

    for series_name in (
        chart_df["Series"]
        .drop_duplicates()
        .tolist()
    ):

        series_df = chart_df[
            chart_df["Series"]
            == series_name
        ].copy()

        historical = series_df[
            series_df["Type"]
            == "Historical"
        ].sort_values(
            "Period_Order"
        )

        projected = series_df[
            series_df["Type"]
            == "Projected"
        ].sort_values(
            "Period_Order"
        )

        if historical.empty:
            continue

        latest_actual = float(
            historical[
                "Value"
            ].iloc[-1]
        )

        # First projected row may be the historical connection
        # point, therefore use rows after latest historical date.

        latest_historical_date = (
            historical[
                "Period_Order"
            ].max()
        )

        future_rows = projected[
            projected[
                "Period_Order"
            ]
            > latest_historical_date
        ]

        if future_rows.empty:
            projected_value = None
            projected_period = ""
        else:
            projected_value = float(
                future_rows[
                    "Value"
                ].iloc[-1]
            )

            projected_period = str(
                future_rows[
                    "Period"
                ].iloc[-1]
            )

        rows.append(
            {
                category_title: series_name,
                "Latest Actual": round(
                    latest_actual,
                    0,
                ),
                "Projected Period": (
                    projected_period
                ),
                "Projected Records": (
                    round(
                        projected_value,
                        0,
                    )
                    if projected_value
                    is not None
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# BASELINE FILTER
# ============================================================

def _baseline_source(
    source,
    baseline_option,
):

    if source is None or source.empty:
        return source

    years = sorted(
        source[
            "Year_Number"
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if not years:
        return source

    if (
        baseline_option
        == "All Available Years"
    ):
        return source.copy()

    baseline_map = {
        "Last 2 Years": 2,
        "Last 3 Years": 3,
        "Last 5 Years": 5,
    }

    number_of_years = (
        baseline_map.get(
            baseline_option
        )
    )

    if number_of_years is None:
        return source.copy()

    selected_years = years[
        -number_of_years:
    ]

    return source[
        source[
            "Year_Number"
        ].isin(
            selected_years
        )
    ].copy()


# ============================================================
# CATEGORY PROJECTION TABLE
# ============================================================

def _category_projection_table(
    source,
    category_column,
):

    if (
        source is None
        or source.empty
        or category_column
        not in source.columns
    ):
        return pd.DataFrame()

    temp = source.copy()

    temp[category_column] = (
        _clean_series(
            temp[
                category_column
            ]
        )
    )

    temp = temp[
        temp[
            category_column
        ].ne("")
        & temp[
            category_column
        ].ne("nan")
        & temp[
            category_column
        ].ne("NaT")
        & temp[
            category_column
        ].ne("None")
    ]

    if temp.empty:
        return pd.DataFrame()

    rows = []

    categories = (
        temp[
            category_column
        ]
        .value_counts()
        .index
        .tolist()
    )

    for category in categories:

        category_df = temp[
            temp[
                category_column
            ]
            == category
        ]

        monthly = (
            _monthly_counts(
                category_df
            )
        )

        if monthly.empty:
            continue

        projection = (
            _calculate_projection(
                monthly["Records"]
            )
        )

        if projection is None:
            continue

        latest = float(
            monthly[
                "Records"
            ].iloc[-1]
        )

        recent_average = float(
            monthly[
                "Records"
            ]
            .tail(
                min(
                    3,
                    len(monthly),
                )
            )
            .mean()
        )

        rows.append(
            {
                category_column: (
                    category
                ),
                "Latest Period": int(
                    latest
                ),
                (
                    "Recent 3-Period "
                    "Average"
                ): round(
                    recent_average,
                    1,
                ),
                (
                    "Next-Period "
                    "Projection"
                ): round(
                    projection,
                    0,
                ),
            }
        )

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(
        rows
    )

    result = result.sort_values(
        "Next-Period Projection",
        ascending=False,
    ).reset_index(
        drop=True
    )

    result.insert(
        0,
        "Rank",
        range(
            1,
            len(result) + 1,
        ),
    )

    return result


# ============================================================
# DISEASE OPTIONS
# ============================================================

def _get_disease_options(source):

    if (
        source is None
        or source.empty
        or "Disease"
        not in source.columns
    ):
        return []

    diseases = (
        _valid_text_values(
            source["Disease"]
        )
    )

    if diseases.empty:
        return []

    return (
        diseases
        .value_counts()
        .index
        .tolist()
    )


# ============================================================
# MAIN PAGE
# ============================================================

def render_prediction(df):

    st.subheader(
        "🔮 Prediction & Trend Projection"
    )

    if df is None or df.empty:

        st.warning(
            "No records available for the selected filters."
        )

        return

    st.caption(
        "Historical trend analysis and indicative programme "
        "projections based on the selected Global Dashboard Filters."
    )

    st.info(
        "⚠️ Projections shown on this page are statistical "
        "planning estimates based on historical record volume. "
        "They are not confirmed disease forecasts, outbreak "
        "predictions or clinical predictions."
    )

    # ========================================================
    # PREPARE DATA
    # ========================================================

    time_df = _prepare_time_data(
        df
    )

    if time_df.empty:

        st.warning(
            "Valid Year and Month information is required "
            "for prediction analysis."
        )

        return

    available_years = sorted(
        time_df[
            "Year_Number"
        ]
        .unique()
        .tolist()
    )

    # ========================================================
    # 1. PREDICTION SUMMARY
    # ========================================================

    st.markdown(
        "### 1. 📊 Prediction Summary"
    )

    monthly_all = (
        _monthly_counts(
            time_df
        )
    )

    yearly_all = (
        _yearly_counts(
            time_df
        )
    )

    first_period = (
        monthly_all[
            "Period"
        ].iloc[0]
    )

    latest_period = (
        monthly_all[
            "Period"
        ].iloc[-1]
    )

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:

        st.metric(
            "Historical Records",
            f"{len(time_df):,}",
        )

    with c2:

        st.metric(
            "Years Available",
            f"{len(available_years):,}",
        )

    with c3:

        st.metric(
            "First Period",
            first_period,
        )

    with c4:

        st.metric(
            "Latest Period",
            latest_period,
        )

    # ========================================================
    # 2. PROJECTION CONTROLS
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. ⚙️ Projection Controls"
    )

    c1, c2 = st.columns(2)

    with c1:

        baseline_option = (
            st.selectbox(
                "Historical Baseline",
                options=[
                    "All Available Years",
                    "Last 2 Years",
                    "Last 3 Years",
                    "Last 5 Years",
                ],
                index=0,
                key=(
                    "prediction_baseline"
                ),
            )
        )

    with c2:

        trend_view = st.radio(
            "Trend View",
            options=[
                "Monthly",
                "Yearly",
            ],
            horizontal=True,
            key=(
                "prediction_trend_view"
            ),
        )

    baseline_df = (
        _baseline_source(
            time_df,
            baseline_option,
        )
    )

    baseline_years = sorted(
        baseline_df[
            "Year_Number"
        ]
        .unique()
        .tolist()
    )

    if baseline_years:

        st.caption(
            "Projection baseline currently uses: "
            + ", ".join(
                str(year)
                for year
                in baseline_years
            )
        )

    # ========================================================
    # 3. HISTORICAL TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 3. 📈 Historical Trend"
    )

    if trend_view == "Monthly":

        baseline_monthly = (
            _monthly_counts(
                baseline_df
            )
        )

        _render_line_chart(
            dataframe=(
                baseline_monthly[
                    [
                        "Period",
                        "Records",
                    ]
                ]
            ),
            x_column="Period",
            y_columns=[
                "Records"
            ],
            title=(
                "Historical Monthly "
                "Record Trend"
            ),
            height=450,
        )

    else:

        baseline_yearly = (
            _yearly_counts(
                baseline_df
            )
        )

        _render_line_chart(
            dataframe=(
                baseline_yearly[
                    [
                        "Year",
                        "Records",
                    ]
                ]
            ),
            x_column="Year",
            y_columns=[
                "Records"
            ],
            title=(
                "Historical Yearly "
                "Record Trend"
            ),
            height=430,
        )

    # ========================================================
    # 4. MOVING AVERAGE
    # ========================================================

    st.divider()

    st.markdown(
        "### 4. 📊 Monthly Moving Average"
    )

    baseline_monthly = (
        _monthly_counts(
            baseline_df
        )
    )

    moving_df = (
        baseline_monthly[
            [
                "Period",
                "Records",
            ]
        ]
        .copy()
    )

    moving_df[
        "3-Month Moving Average"
    ] = (
        moving_df[
            "Records"
        ]
        .rolling(
            window=3,
            min_periods=1,
        )
        .mean()
        .round(2)
    )

    _render_line_chart(
        dataframe=moving_df,
        x_column="Period",
        y_columns=[
            "Records",
            "3-Month Moving Average",
        ],
        title=(
            "Actual Records vs "
            "3-Month Moving Average"
        ),
        height=450,
    )

    # ========================================================
    # 5. NEXT MONTH PROJECTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 5. 🔮 Next-Month Projection"
    )

    next_month_projection = (
        _calculate_projection(
            baseline_monthly[
                "Records"
            ]
        )
    )

    latest_row = (
        baseline_monthly.iloc[-1]
    )

    latest_value = float(
        latest_row["Records"]
    )

    latest_year = int(
        latest_row[
            "Year_Number"
        ]
    )

    latest_month = int(
        latest_row[
            "Month_Number"
        ]
    )

    (
        next_year_value,
        next_month_value,
    ) = _next_month(
        latest_year,
        latest_month,
    )

    next_period_label = (
        f"{MONTH_NAMES[next_month_value]}"
        f"-{next_year_value}"
    )

    recent_average = float(
        baseline_monthly[
            "Records"
        ]
        .tail(
            min(
                3,
                len(
                    baseline_monthly
                ),
            )
        )
        .mean()
    )

    c1, c2, c3 = (
        st.columns(3)
    )

    with c1:

        st.metric(
            "Latest Period Records",
            f"{latest_value:,.0f}",
        )

    with c2:

        st.metric(
            "Recent 3-Month Average",
            f"{recent_average:,.1f}",
        )

    with c3:

        if (
            next_month_projection
            is not None
        ):

            st.metric(
                (
                    f"Projected "
                    f"{next_period_label}"
                ),
                (
                    f"{next_month_projection:,.0f}"
                ),
            )

    if (
        next_month_projection
        is not None
    ):

        next_change = (
            _safe_percent_change(
                next_month_projection,
                latest_value,
            )
        )

        if next_change is not None:

            st.caption(
                "Projected change from "
                "the latest observed period: "
                f"{next_change:+.2f}%."
            )

    # ========================================================
    # 6. NEXT 12 MONTHS
    # ========================================================

    st.divider()

    st.markdown(
        "### 6. 📅 Next 12-Month Projection"
    )

    projected_values = (
        _project_multiple_periods(
            baseline_monthly[
                "Records"
            ],
            12,
        )
    )

    projection_rows = []

    projection_year = (
        latest_year
    )

    projection_month = (
        latest_month
    )

    for projected_value in (
        projected_values
    ):

        (
            projection_year,
            projection_month,
        ) = _next_month(
            projection_year,
            projection_month,
        )

        projection_rows.append(
            {
                "Period": (
                    f"{MONTH_NAMES[projection_month]}"
                    f"-{projection_year}"
                ),
                "Projected Records": (
                    round(
                        projected_value,
                        0,
                    )
                ),
            }
        )

    projection_12_df = (
        pd.DataFrame(
            projection_rows
        )
    )

    if not projection_12_df.empty:

        _render_line_chart(
            dataframe=projection_12_df,
            x_column="Period",
            y_columns=[
                "Projected Records"
            ],
            title=(
                "Indicative Next "
                "12-Month Projection"
            ),
            height=430,
        )

        st.dataframe(
            projection_12_df,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # 7. NEXT YEAR PROJECTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 7. 🗓️ Next-Year Projection"
    )

    next_year_projection = (
        projection_12_df[
            "Projected Records"
        ].sum()
        if not projection_12_df.empty
        else None
    )

    current_latest_year = max(
        available_years
    )

    latest_year_records = len(
        time_df[
            time_df[
                "Year_Number"
            ]
            == current_latest_year
        ]
    )

    previous_years = [
        year
        for year
        in available_years
        if year
        < current_latest_year
    ]

    previous_year_records = None

    if previous_years:

        previous_year = max(
            previous_years
        )

        previous_year_records = len(
            time_df[
                time_df[
                    "Year_Number"
                ]
                == previous_year
            ]
        )

    c1, c2, c3 = (
        st.columns(3)
    )

    with c1:

        st.metric(
            (
                f"{current_latest_year} "
                "Records"
            ),
            (
                f"{latest_year_records:,}"
            ),
        )

    with c2:

        if (
            previous_year_records
            is not None
        ):

            st.metric(
                "Previous Year Records",
                (
                    f"{previous_year_records:,}"
                ),
            )

        else:

            st.metric(
                "Previous Year Records",
                "N/A",
            )

    with c3:

        if (
            next_year_projection
            is not None
        ):

            st.metric(
                "Projected Next 12 Months",
                (
                    f"{next_year_projection:,.0f}"
                ),
            )

    st.caption(
        "The next-year figure is calculated as the sum of "
        "the 12 sequential monthly projections. If the latest "
        "observed year is incomplete, its raw total should not "
        "be interpreted as a full-year comparison."
    )

    # ========================================================
    # 8. DISEASE-WISE PROJECTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 8. 🦠 Disease-wise Projection"
    )

    st.caption(
        "Select one or multiple diseases to compare historical "
        "trends and future projections within the same chart."
    )

    disease_options = (
        _get_disease_options(
            baseline_df
        )
    )

    if disease_options:

        control1, control2 = (
            st.columns(
                [2, 1]
            )
        )

        with control1:

            selected_diseases = (
                _checkbox_multiselect(
                    label=(
                        "Select Disease(s)"
                    ),
                    options=(
                        disease_options
                    ),
                    key_prefix=(
                        "prediction_disease_multi"
                    ),
                    default_count=min(
                        5,
                        len(
                            disease_options
                        ),
                    ),
                )
            )

        with control2:

            disease_projection_mode = (
                st.radio(
                    "Projection Period",
                    options=[
                        "Next Month",
                        "Next 12 Months",
                        "Next Year",
                    ],
                    horizontal=False,
                    key=(
                        "prediction_disease_mode"
                    ),
                )
            )

        if not selected_diseases:

            st.info(
                "Please select at least "
                "one disease."
            )

        else:

            disease_chart_frames = []

            for disease in (
                selected_diseases
            ):

                disease_source = (
                    baseline_df[
                        _clean_series(
                            baseline_df[
                                "Disease"
                            ]
                        )
                        == disease
                    ]
                    .copy()
                )

                disease_series = (
                    _build_projection_series(
                        source=(
                            disease_source
                        ),
                        series_name=(
                            disease
                        ),
                        projection_mode=(
                            disease_projection_mode
                        ),
                    )
                )

                if not disease_series.empty:

                    disease_chart_frames.append(
                        disease_series
                    )

            if disease_chart_frames:

                disease_chart_df = (
                    pd.concat(
                        disease_chart_frames,
                        ignore_index=True,
                    )
                )

                _render_projection_chart(
                    dataframe=(
                        disease_chart_df
                    ),
                    title=(
                        "Disease-wise Historical "
                        "and Projected Trend"
                    ),
                    height=520,
                )

                st.caption(
                    f"{len(selected_diseases)} disease(s) selected: "
                    + ", ".join(
                        selected_diseases
                    )
                )

                disease_summary = (
                    _projection_summary_from_chart(
                        disease_chart_df,
                        "Disease",
                    )
                )

                if not disease_summary.empty:

                    st.markdown(
                        "#### Selected Disease "
                        "Projection Summary"
                    )

                    st.dataframe(
                        disease_summary,
                        use_container_width=True,
                        hide_index=True,
                    )

            disease_projection_table = (
                _category_projection_table(
                    baseline_df,
                    "Disease",
                )
            )

            if (
                not disease_projection_table.empty
            ):

                st.markdown(
                    "#### All Disease "
                    "Next-Period Comparison"
                )

                st.dataframe(
                    disease_projection_table,
                    use_container_width=True,
                    hide_index=True,
                )

    else:

        st.info(
            "Disease information is "
            "not available."
        )

    # ========================================================
    # 9. WARD-WISE PROJECTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 9. 📍 Ward-wise Projection"
    )

    st.caption(
        "Select a ward and one or multiple diseases to compare "
        "disease-specific historical and projected trends within "
        "the selected ward."
    )

    if (
        "Ward Name"
        in baseline_df.columns
    ):

        ward_values = (
            _valid_text_values(
                baseline_df[
                    "Ward Name"
                ]
            )
        )

        ward_options = sorted(
            ward_values
            .unique()
            .tolist(),
            key=lambda value:
            str(value).upper(),
        )

        if ward_options:

            ward_control1, ward_control2 = (
                st.columns(
                    [1, 1]
                )
            )

            with ward_control1:

                selected_ward = (
                    st.selectbox(
                        "Select Ward",
                        options=(
                            ward_options
                        ),
                        key=(
                            "prediction_ward_selector"
                        ),
                    )
                )

            with ward_control2:

                ward_projection_mode = (
                    st.radio(
                        "Ward Projection Period",
                        options=[
                            "Next Month",
                            "Next 12 Months",
                            "Next Year",
                        ],
                        horizontal=False,
                        key=(
                            "prediction_ward_mode"
                        ),
                    )
                )

            ward_source = (
                baseline_df[
                    _clean_series(
                        baseline_df[
                            "Ward Name"
                        ]
                    )
                    == selected_ward
                ]
                .copy()
            )

            ward_disease_options = (
                _get_disease_options(
                    ward_source
                )
            )

            if ward_disease_options:

                selected_ward_diseases = (
                    _checkbox_multiselect(
                        label=(
                            "Select Disease(s) "
                            "for Ward Comparison"
                        ),
                        options=(
                            ward_disease_options
                        ),
                        key_prefix=(
                            "prediction_ward_disease_multi"
                        ),
                        default_count=min(
                            5,
                            len(
                                ward_disease_options
                            ),
                        ),
                    )
                )

                if (
                    not selected_ward_diseases
                ):

                    st.info(
                        "Please select at least "
                        "one disease."
                    )

                else:

                    ward_chart_frames = []

                    for disease in (
                        selected_ward_diseases
                    ):

                        disease_source = (
                            ward_source[
                                _clean_series(
                                    ward_source[
                                        "Disease"
                                    ]
                                )
                                == disease
                            ]
                            .copy()
                        )

                        series_df = (
                            _build_projection_series(
                                source=(
                                    disease_source
                                ),
                                series_name=(
                                    disease
                                ),
                                projection_mode=(
                                    ward_projection_mode
                                ),
                            )
                        )

                        if not series_df.empty:

                            ward_chart_frames.append(
                                series_df
                            )

                    if ward_chart_frames:

                        ward_chart_df = (
                            pd.concat(
                                ward_chart_frames,
                                ignore_index=True,
                            )
                        )

                        _render_projection_chart(
                            dataframe=(
                                ward_chart_df
                            ),
                            title=(
                                f"Ward {selected_ward} — "
                                "Disease-wise Historical "
                                "and Projected Trend"
                            ),
                            height=520,
                        )

                        st.caption(
                            (
                                f"Ward {selected_ward} • "
                                f"{len(selected_ward_diseases)} "
                                "disease(s) selected: "
                            )
                            + ", ".join(
                                selected_ward_diseases
                            )
                        )

                        ward_summary = (
                            _projection_summary_from_chart(
                                ward_chart_df,
                                "Disease",
                            )
                        )

                        if not ward_summary.empty:

                            st.markdown(
                                "#### Selected Ward "
                                "Disease Projection Summary"
                            )

                            st.dataframe(
                                ward_summary,
                                use_container_width=True,
                                hide_index=True,
                            )

            else:

                st.info(
                    "Disease information is not "
                    "available for the selected ward."
                )

            ward_projection_table = (
                _category_projection_table(
                    baseline_df,
                    "Ward Name",
                )
            )

            if (
                not ward_projection_table.empty
            ):

                st.markdown(
                    "#### Ward Projection Comparison"
                )

                st.dataframe(
                    ward_projection_table,
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.info(
                "No valid wards are available."
            )

    else:

        st.info(
            "Ward Name column is "
            "not available."
        )

    # ========================================================
    # 10. FACILITY-WISE PROJECTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 10. 🏥 Facility-wise Projection"
    )

    st.caption(
        "Select a facility and one or multiple diseases to compare "
        "disease-specific historical and projected trends within "
        "the selected facility."
    )

    if (
        "Facility Name"
        in baseline_df.columns
    ):

        facility_values = (
            _valid_text_values(
                baseline_df[
                    "Facility Name"
                ]
            )
        )

        facility_options = (
            facility_values
            .value_counts()
            .index
            .tolist()
        )

        if facility_options:

            facility_control1, facility_control2 = (
                st.columns(
                    [2, 1]
                )
            )

            with facility_control1:

                selected_facility = (
                    st.selectbox(
                        "Select Facility",
                        options=(
                            facility_options
                        ),
                        key=(
                            "prediction_facility_selector"
                        ),
                    )
                )

            with facility_control2:

                facility_projection_mode = (
                    st.radio(
                        "Facility Projection Period",
                        options=[
                            "Next Month",
                            "Next 12 Months",
                            "Next Year",
                        ],
                        horizontal=False,
                        key=(
                            "prediction_facility_mode"
                        ),
                    )
                )

            facility_source = (
                baseline_df[
                    _clean_series(
                        baseline_df[
                            "Facility Name"
                        ]
                    )
                    == selected_facility
                ]
                .copy()
            )

            facility_disease_options = (
                _get_disease_options(
                    facility_source
                )
            )

            if facility_disease_options:

                selected_facility_diseases = (
                    _checkbox_multiselect(
                        label=(
                            "Select Disease(s) "
                            "for Facility Comparison"
                        ),
                        options=(
                            facility_disease_options
                        ),
                        key_prefix=(
                            "prediction_facility_disease_multi"
                        ),
                        default_count=min(
                            5,
                            len(
                                facility_disease_options
                            ),
                        ),
                    )
                )

                if (
                    not selected_facility_diseases
                ):

                    st.info(
                        "Please select at least "
                        "one disease."
                    )

                else:

                    facility_chart_frames = []

                    for disease in (
                        selected_facility_diseases
                    ):

                        disease_source = (
                            facility_source[
                                _clean_series(
                                    facility_source[
                                        "Disease"
                                    ]
                                )
                                == disease
                            ]
                            .copy()
                        )

                        series_df = (
                            _build_projection_series(
                                source=(
                                    disease_source
                                ),
                                series_name=(
                                    disease
                                ),
                                projection_mode=(
                                    facility_projection_mode
                                ),
                            )
                        )

                        if not series_df.empty:

                            facility_chart_frames.append(
                                series_df
                            )

                    if facility_chart_frames:

                        facility_chart_df = (
                            pd.concat(
                                facility_chart_frames,
                                ignore_index=True,
                            )
                        )

                        _render_projection_chart(
                            dataframe=(
                                facility_chart_df
                            ),
                            title=(
                                f"{selected_facility} — "
                                "Disease-wise Historical "
                                "and Projected Trend"
                            ),
                            height=520,
                        )

                        st.caption(
                            (
                                f"{selected_facility} • "
                                f"{len(selected_facility_diseases)} "
                                "disease(s) selected: "
                            )
                            + ", ".join(
                                selected_facility_diseases
                            )
                        )

                        facility_summary = (
                            _projection_summary_from_chart(
                                facility_chart_df,
                                "Disease",
                            )
                        )

                        if (
                            not facility_summary.empty
                        ):

                            st.markdown(
                                "#### Selected Facility "
                                "Disease Projection Summary"
                            )

                            st.dataframe(
                                facility_summary,
                                use_container_width=True,
                                hide_index=True,
                            )

            else:

                st.info(
                    "Disease information is not available "
                    "for the selected facility."
                )

            facility_projection_table = (
                _category_projection_table(
                    baseline_df,
                    "Facility Name",
                )
            )

            if (
                not facility_projection_table.empty
            ):

                st.markdown(
                    "#### Facility Projection Comparison"
                )

                st.dataframe(
                    facility_projection_table,
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.info(
                "No valid facilities are available."
            )

    else:

        st.info(
            "Facility Name column is "
            "not available."
        )

    # ========================================================
    # 11. RECENT PERIOD PERFORMANCE
    # ========================================================

    st.divider()

    st.markdown(
        "### 11. 📋 Recent Period Performance"
    )

    recent = (
        monthly_all
        .tail(
            min(
                12,
                len(
                    monthly_all
                ),
            )
        )
        .copy()
    )

    recent[
        "3-Month Moving Average"
    ] = (
        recent[
            "Records"
        ]
        .rolling(
            window=3,
            min_periods=1,
        )
        .mean()
        .round(2)
    )

    recent[
        "Difference from Moving Average"
    ] = (
        recent["Records"]
        - recent[
            "3-Month Moving Average"
        ]
    ).round(2)

    recent[
        "% Difference from Moving Average"
    ] = np.where(
        recent[
            "3-Month Moving Average"
        ].ne(0),
        (
            recent[
                "Difference from Moving Average"
            ]
            / recent[
                "3-Month Moving Average"
            ]
            * 100
        ).round(2),
        np.nan,
    )

    st.dataframe(
        recent[
            [
                "Period",
                "Records",
                "3-Month Moving Average",
                "Difference from Moving Average",
                "% Difference from Moving Average",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # 12. PROJECTION METHOD
    # ========================================================

    st.divider()

    st.markdown(
        "### 12. ℹ️ Projection Method & Interpretation"
    )

    method_table = pd.DataFrame(
        {
            "Component": [
                "Historical Input",
                "Time Ordering",
                "Historical Baseline",
                "Recent Baseline",
                "Trend Component",
                "Combined Projection",
                "Next-Month Projection",
                "Next 12-Month Projection",
                "Next-Year Projection",
                "Disease Comparison",
                "Ward-Disease Analysis",
                "Facility-Disease Analysis",
                "Chart Interpretation",
                "Interpretation",
            ],
            "Description": [
                (
                    "Records available after applying "
                    "Global Dashboard Filters"
                ),
                (
                    "Data is converted to Year-Month and "
                    "sorted chronologically before analysis"
                ),
                (
                    "All available years or the selected "
                    "recent 2, 3 or 5-year period"
                ),
                (
                    "Weighted average of the most recent "
                    "three observations"
                ),
                (
                    "Simple linear trend fitted to the "
                    "selected historical series"
                ),
                (
                    "70% recent weighted level and "
                    "30% historical linear trend"
                ),
                (
                    "One sequential monthly projection "
                    "after the latest observed month"
                ),
                (
                    "Twelve sequential monthly projections "
                    "after the latest observed month"
                ),
                (
                    "One-step projection based on the "
                    "historical annual record series"
                ),
                (
                    "Multiple selected diseases can be "
                    "compared within the same chart"
                ),
                (
                    "Multiple diseases can be compared "
                    "within a selected ward"
                ),
                (
                    "Multiple diseases can be compared "
                    "within a selected facility"
                ),
                (
                    "Solid lines represent historical records; "
                    "dotted lines represent projected records"
                ),
                (
                    "Programme planning support only; "
                    "not a confirmed epidemiological forecast"
                ),
            ],
        }
    )

    st.dataframe(
        method_table,
        use_container_width=True,
        hide_index=True,
    )

    st.warning(
        "Projection results should be interpreted alongside "
        "reporting completeness, seasonality, outbreaks, testing "
        "practices, programme changes and other epidemiological "
        "information. Zero-filled months represent months with "
        "no records in the selected data series and should be "
        "reviewed for possible reporting gaps before interpreting "
        "the projection."
    )
