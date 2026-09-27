import streamlit as st
import pandas as pd
import numpy as np
import altair as alt


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
# COMPLETE MONTHLY SERIES
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

    first_year = int(
        monthly["Year_Number"].min()
    )

    first_month = int(
        monthly.loc[
            monthly["Year_Number"].idxmin(),
            "Month_Number",
        ]
    )

    last_year = int(
        monthly["Year_Number"].max()
    )

    latest_rows = monthly[
        monthly["Year_Number"]
        == last_year
    ]

    last_month = int(
        latest_rows["Month_Number"].max()
    )

    if start_date is None:

        start_date = pd.Timestamp(
            year=first_year,
            month=first_month,
            day=1,
        )

    if end_date is None:

        end_date = pd.Timestamp(
            year=last_year,
            month=last_month,
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
        complete["Period_Date"].dt.year
    )

    complete["Month_Number"] = (
        complete["Period_Date"].dt.month
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
# YEARLY SERIES
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
        yearly["Year_Number"]
        .astype(int)
        .astype(str)
    )

    return yearly.reset_index(drop=True)


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
            float(numeric.iloc[-1]),
        )

    # --------------------------------------------------------
    # RECENT WEIGHTED BASELINE
    # --------------------------------------------------------

    recent = numeric.tail(
        min(3, len(numeric))
    )

    weights = np.arange(
        1,
        len(recent) + 1,
        dtype=float,
    )

    recent_weighted = float(
        np.average(
            recent.to_numpy(dtype=float),
            weights=weights,
        )
    )

    # --------------------------------------------------------
    # LINEAR TREND
    # --------------------------------------------------------

    x = np.arange(
        len(numeric),
        dtype=float,
    )

    try:

        slope, intercept = np.polyfit(
            x,
            numeric.to_numpy(dtype=float),
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

    # --------------------------------------------------------
    # COMBINED ESTIMATE
    # --------------------------------------------------------

    projection = (
        recent_weighted * 0.70
        + trend_projection * 0.30
    )

    return max(
        0.0,
        float(projection),
    )


# ============================================================
# MULTI-STEP PROJECTION
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
# CHART HELPERS
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

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    if x_column not in chart_df.columns:
        return

    valid_y_columns = [
        column
        for column in y_columns
        if column in chart_df.columns
    ]

    if not valid_y_columns:
        return

    # --------------------------------------------------------
    # Convert wide data to long format
    #
    # IMPORTANT:
    # Do NOT use value_name="Records" because the source
    # dataframe may already contain a column named "Records".
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # LINE CHART
    # --------------------------------------------------------

    chart = (
        alt.Chart(long_df)
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
                    labelLimit=140,
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
                legend=alt.Legend(
                    orient="bottom",
                    direction="horizontal",
                    title=None,
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
        .properties(
            height=height,
            title=title,
        )
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )

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
        source["Year_Number"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if not years:
        return source

    if baseline_option == "All Available Years":
        return source.copy()

    baseline_map = {
        "Last 2 Years": 2,
        "Last 3 Years": 3,
        "Last 5 Years": 5,
    }

    number_of_years = baseline_map.get(
        baseline_option
    )

    if number_of_years is None:
        return source.copy()

    selected_years = years[
        -number_of_years:
    ]

    return source[
        source["Year_Number"]
        .isin(selected_years)
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
        or category_column not in source.columns
    ):
        return pd.DataFrame()

    temp = source.copy()

    temp[category_column] = (
        _clean_series(
            temp[category_column]
        )
    )

    temp = temp[
        temp[category_column].ne("")
        & temp[category_column].ne("nan")
        & temp[category_column].ne("NaT")
        & temp[category_column].ne("None")
    ]

    if temp.empty:
        return pd.DataFrame()

    rows = []

    for category in sorted(
        temp[category_column]
        .unique()
        .tolist(),
        key=lambda value:
        str(value).upper(),
    ):

        category_df = temp[
            temp[category_column]
            == category
        ]

        monthly = _monthly_counts(
            category_df
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
            monthly["Records"].iloc[-1]
        )

        recent_average = float(
            monthly["Records"]
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
                category_column: category,
                "Latest Period": int(latest),
                "Recent 3-Period Average": round(
                    recent_average,
                    1,
                ),
                "Next-Period Projection": round(
                    projection,
                    0,
                ),
            }
        )

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows)

    result = result.sort_values(
        "Next-Period Projection",
        ascending=False,
    ).reset_index(drop=True)

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

    time_df = _prepare_time_data(df)

    if time_df.empty:

        st.warning(
            "Valid Year and Month information is required "
            "for prediction analysis."
        )

        return

    available_years = sorted(
        time_df["Year_Number"]
        .unique()
        .tolist()
    )

    # ========================================================
    # 1. PREDICTION SUMMARY
    # ========================================================

    st.markdown(
        "### 1. 📊 Prediction Summary"
    )

    monthly_all = _monthly_counts(
        time_df
    )

    yearly_all = _yearly_counts(
        time_df
    )

    first_period = (
        monthly_all["Period"].iloc[0]
    )

    latest_period = (
        monthly_all["Period"].iloc[-1]
    )

    c1, c2, c3, c4 = st.columns(4)

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
    # 2. ANALYSIS CONTROLS
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. ⚙️ Projection Controls"
    )

    c1, c2 = st.columns(2)

    with c1:

        baseline_option = st.selectbox(
            "Historical Baseline",
            options=[
                "All Available Years",
                "Last 2 Years",
                "Last 3 Years",
                "Last 5 Years",
            ],
            index=0,
            key="prediction_baseline",
        )

    with c2:

        trend_view = st.radio(
            "Trend View",
            options=[
                "Monthly",
                "Yearly",
            ],
            horizontal=True,
            key="prediction_trend_view",
        )

    baseline_df = _baseline_source(
        time_df,
        baseline_option,
    )

    baseline_years = sorted(
        baseline_df["Year_Number"]
        .unique()
        .tolist()
    )

    if baseline_years:

        st.caption(
            "Projection baseline currently uses: "
            + ", ".join(
                str(year)
                for year in baseline_years
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
            dataframe=baseline_monthly[
                [
                    "Period",
                    "Records",
                ]
            ],
            x_column="Period",
            y_columns=["Records"],
            title=(
                "Historical Monthly Record Trend"
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
            dataframe=baseline_yearly[
                [
                    "Year",
                    "Records",
                ]
            ],
            x_column="Year",
            y_columns=["Records"],
            title=(
                "Historical Yearly Record Trend"
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

    baseline_monthly = _monthly_counts(
        baseline_df
    )

    moving_df = baseline_monthly[
        [
            "Period",
            "Records",
        ]
    ].copy()

    moving_df[
        "3-Month Moving Average"
    ] = (
        moving_df["Records"]
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
            "Actual Records vs 3-Month Moving Average"
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
            baseline_monthly["Records"]
        )
    )

    latest_row = (
        baseline_monthly.iloc[-1]
    )

    latest_value = float(
        latest_row["Records"]
    )

    latest_year = int(
        latest_row["Year_Number"]
    )

    latest_month = int(
        latest_row["Month_Number"]
    )

    next_year_value, next_month_value = (
        _next_month(
            latest_year,
            latest_month,
        )
    )

    next_period_label = (
        f"{MONTH_NAMES[next_month_value]}-"
        f"{next_year_value}"
    )

    recent_average = float(
        baseline_monthly[
            "Records"
        ]
        .tail(
            min(
                3,
                len(baseline_monthly),
            )
        )
        .mean()
    )

    c1, c2, c3 = st.columns(3)

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

        if next_month_projection is not None:

            st.metric(
                f"Projected {next_period_label}",
                f"{next_month_projection:,.0f}",
            )

    if next_month_projection is not None:

        next_change = _safe_percent_change(
            next_month_projection,
            latest_value,
        )

        if next_change is not None:

            st.caption(
                f"Projected change from the latest observed "
                f"period: {next_change:+.2f}%."
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

    projection_year = latest_year
    projection_month = latest_month

    for projected_value in projected_values:

        projection_year, projection_month = (
            _next_month(
                projection_year,
                projection_month,
            )
        )

        projection_rows.append(
            {
                "Period": (
                    f"{MONTH_NAMES[projection_month]}"
                    f"-{projection_year}"
                ),
                "Projected Records": round(
                    projected_value,
                    0,
                ),
            }
        )

    projection_12_df = pd.DataFrame(
        projection_rows
    )

    if not projection_12_df.empty:

        _render_line_chart(
            dataframe=projection_12_df,
            x_column="Period",
            y_columns=[
                "Projected Records"
            ],
            title=(
                "Indicative Next 12-Month Projection"
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
            time_df["Year_Number"]
            == current_latest_year
        ]
    )

    previous_years = [
        year
        for year in available_years
        if year < current_latest_year
    ]

    previous_year_records = None

    if previous_years:

        previous_year = max(
            previous_years
        )

        previous_year_records = len(
            time_df[
                time_df["Year_Number"]
                == previous_year
            ]
        )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            f"{current_latest_year} Records",
            f"{latest_year_records:,}",
        )

    with c2:

        if previous_year_records is not None:

            st.metric(
                "Previous Year Records",
                f"{previous_year_records:,}",
            )

        else:

            st.metric(
                "Previous Year Records",
                "N/A",
            )

    with c3:

        if next_year_projection is not None:

            st.metric(
                f"Projected Next 12 Months",
                f"{next_year_projection:,.0f}",
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

    if "Disease" in baseline_df.columns:

        diseases = (
            _clean_series(
                baseline_df["Disease"]
            )
        )

        diseases = diseases[
            diseases.ne("")
            & diseases.ne("nan")
            & diseases.ne("NaT")
            & diseases.ne("None")
        ]

        disease_options = (
            diseases
            .value_counts()
            .index
            .tolist()
        )

        if disease_options:

            selected_disease = (
                st.selectbox(
                    "Select Disease",
                    options=disease_options,
                    key=(
                        "prediction_disease_selector"
                    ),
                )
            )

            disease_source = baseline_df[
                _clean_series(
                    baseline_df["Disease"]
                )
                == selected_disease
            ].copy()

            disease_monthly = (
                _monthly_counts(
                    disease_source
                )
            )

            if not disease_monthly.empty:

                _render_line_chart(
                    dataframe=disease_monthly[
                        [
                            "Period",
                            "Records",
                        ]
                    ],
                    x_column="Period",
                    y_columns=["Records"],
                    title=(
                        f"{selected_disease} "
                        "Historical Monthly Trend"
                    ),
                    height=430,
                )

                disease_projection = (
                    _calculate_projection(
                        disease_monthly[
                            "Records"
                        ]
                    )
                )

                if disease_projection is not None:

                    st.metric(
                        (
                            "Indicative Next-Month "
                            f"Projection — "
                            f"{selected_disease}"
                        ),
                        f"{disease_projection:,.0f}",
                    )

        disease_projection_table = (
            _category_projection_table(
                baseline_df,
                "Disease",
            )
        )

        if not disease_projection_table.empty:

            st.markdown(
                "#### Disease Projection Comparison"
            )

            st.dataframe(
                disease_projection_table,
                use_container_width=True,
                hide_index=True,
            )

    else:

        st.info(
            "Disease column is not available."
        )

    # ========================================================
    # 9. WARD-WISE PROJECTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 9. 📍 Ward-wise Projection"
    )

    if "Ward Name" in baseline_df.columns:

        ward_projection_table = (
            _category_projection_table(
                baseline_df,
                "Ward Name",
            )
        )

        if not ward_projection_table.empty:

            ward_options = (
                ward_projection_table[
                    "Ward Name"
                ]
                .tolist()
            )

            selected_ward = (
                st.selectbox(
                    "Select Ward",
                    options=ward_options,
                    key=(
                        "prediction_ward_selector"
                    ),
                )
            )

            ward_source = baseline_df[
                _clean_series(
                    baseline_df[
                        "Ward Name"
                    ]
                )
                == selected_ward
            ].copy()

            ward_monthly = (
                _monthly_counts(
                    ward_source
                )
            )

            _render_line_chart(
                dataframe=ward_monthly[
                    [
                        "Period",
                        "Records",
                    ]
                ],
                x_column="Period",
                y_columns=["Records"],
                title=(
                    f"Ward {selected_ward} "
                    "Historical Monthly Trend"
                ),
                height=430,
            )

            selected_ward_projection = (
                _calculate_projection(
                    ward_monthly["Records"]
                )
            )

            if (
                selected_ward_projection
                is not None
            ):

                st.metric(
                    (
                        "Indicative Next-Month "
                        f"Projection — Ward "
                        f"{selected_ward}"
                    ),
                    (
                        f"{selected_ward_projection:,.0f}"
                    ),
                )

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
            "Ward Name column is not available."
        )

    # ========================================================
    # 10. FACILITY-WISE PROJECTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 10. 🏥 Facility-wise Projection"
    )

    if "Facility Name" in baseline_df.columns:

        facility_projection_table = (
            _category_projection_table(
                baseline_df,
                "Facility Name",
            )
        )

        if not facility_projection_table.empty:

            facility_options = (
                facility_projection_table[
                    "Facility Name"
                ]
                .tolist()
            )

            selected_facility = (
                st.selectbox(
                    "Select Facility",
                    options=facility_options,
                    key=(
                        "prediction_facility_selector"
                    ),
                )
            )

            facility_source = baseline_df[
                _clean_series(
                    baseline_df[
                        "Facility Name"
                    ]
                )
                == selected_facility
            ].copy()

            facility_monthly = (
                _monthly_counts(
                    facility_source
                )
            )

            _render_line_chart(
                dataframe=facility_monthly[
                    [
                        "Period",
                        "Records",
                    ]
                ],
                x_column="Period",
                y_columns=["Records"],
                title=(
                    f"{selected_facility} "
                    "Historical Monthly Trend"
                ),
                height=430,
            )

            selected_facility_projection = (
                _calculate_projection(
                    facility_monthly[
                        "Records"
                    ]
                )
            )

            if (
                selected_facility_projection
                is not None
            ):

                st.metric(
                    (
                        "Indicative Next-Month "
                        "Projection"
                    ),
                    (
                        f"{selected_facility_projection:,.0f}"
                    ),
                )

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
            "Facility Name column is not available."
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
                len(monthly_all),
            )
        )
        .copy()
    )

    recent[
        "3-Month Moving Average"
    ] = (
        recent["Records"]
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
                "Recent Baseline",
                "Trend Component",
                "Combined Projection",
                "Next-Month Projection",
                "Next-Year Projection",
                "Disease Analysis",
                "Ward Analysis",
                "Facility Analysis",
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
                    "Weighted average of the most recent "
                    "three monthly observations"
                ),
                (
                    "Simple linear trend fitted to the "
                    "selected historical monthly series"
                ),
                (
                    "70% recent weighted level and "
                    "30% historical linear trend"
                ),
                (
                    "One-step statistical projection from "
                    "the selected baseline"
                ),
                (
                    "Sum of 12 sequential monthly "
                    "statistical projections"
                ),
                (
                    "Separate monthly historical series "
                    "for each disease"
                ),
                (
                    "Separate monthly historical series "
                    "for each ward"
                ),
                (
                    "Separate monthly historical series "
                    "for each facility"
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
