import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st


# ============================================================
# COMMON HELPERS
# ============================================================

def _layout(fig, height=500):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text="",
        hovermode="x unified"
    )
    return fig


def _safe_numeric(series):
    return pd.to_numeric(
        series,
        errors="coerce"
    )


def _month_column(df):
    """
    Detects a usable month/date column.
    """

    candidates = [
        "Month",
        "month",
        "Month Name",
        "Month_Name",
        "Date",
        "date",
        "Registration Date",
        "Registration_Date"
    ]

    for col in candidates:
        if col in df.columns:
            return col

    return None


def _convert_month_order(df, month_col):
    """
    Converts common month formats into chronological
    month order where possible.
    """

    result = df.copy()

    month_order = [
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
        "Dec"
    ]

    month_map = {
        "January": "Jan",
        "February": "Feb",
        "March": "Mar",
        "April": "Apr",
        "May": "May",
        "June": "Jun",
        "July": "Jul",
        "August": "Aug",
        "September": "Sep",
        "October": "Oct",
        "November": "Nov",
        "December": "Dec"
    }

    result[month_col] = (
        result[month_col]
        .astype(str)
        .str.strip()
        .replace(month_map)
    )

    result[month_col] = pd.Categorical(
        result[month_col],
        categories=month_order,
        ordered=True
    )

    return result


# ============================================================
# MONTHLY CASE DATA
# ============================================================

def _monthly_cases(df):

    month_col = _month_column(df)

    if month_col is None:
        return None, None

    temp = df.copy()

    # --------------------------------------------------------
    # If actual date column
    # --------------------------------------------------------

    if (
        "date" in month_col.lower()
        or "registration" in month_col.lower()
    ):

        parsed = pd.to_datetime(
            temp[month_col],
            errors="coerce",
            dayfirst=True
        )

        if parsed.notna().sum() > 0:

            temp["_PredictionMonth"] = (
                parsed
                .dt.to_period("M")
                .astype(str)
            )

            monthly = (
                temp
                .dropna(
                    subset=["_PredictionMonth"]
                )
                .groupby("_PredictionMonth")
                .size()
                .reset_index(
                    name="Cases"
                )
            )

            monthly["Month"] = pd.to_datetime(
                monthly["_PredictionMonth"]
                + "-01",
                errors="coerce"
            )

            monthly = monthly.sort_values(
                "Month"
            )

            return monthly, "Date"

    # --------------------------------------------------------
    # Month name column
    # --------------------------------------------------------

    temp = _convert_month_order(
        temp,
        month_col
    )

    monthly = (
        temp
        .dropna(subset=[month_col])
        .groupby(month_col, observed=True)
        .size()
        .reset_index(
            name="Cases"
        )
    )

    monthly = monthly.rename(
        columns={
            month_col: "Month"
        }
    )

    month_order = [
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
        "Dec"
    ]

    monthly["Month"] = pd.Categorical(
        monthly["Month"],
        categories=month_order,
        ordered=True
    )

    monthly = monthly.sort_values(
        "Month"
    )

    return monthly, "Month"


# ============================================================
# SIMPLE TREND FORECAST
# ============================================================

def _linear_forecast(values, periods=1):

    values = np.asarray(
        values,
        dtype=float
    )

    values = values[
        np.isfinite(values)
    ]

    if len(values) == 0:
        return []

    if len(values) == 1:

        return [
            max(
                0,
                float(values[-1])
            )
            for _ in range(periods)
        ]

    x = np.arange(
        len(values),
        dtype=float
    )

    try:

        slope, intercept = np.polyfit(
            x,
            values,
            1
        )

    except Exception:

        return [
            max(
                0,
                float(values[-1])
            )
            for _ in range(periods)
        ]

    future_x = np.arange(
        len(values),
        len(values) + periods,
        dtype=float
    )

    predictions = (
        slope * future_x
        + intercept
    )

    predictions = np.maximum(
        predictions,
        0
    )

    return predictions.tolist()


# ============================================================
# TREND CLASSIFICATION
# ============================================================

def _trend_direction(values):

    if len(values) < 2:
        return "Insufficient data"

    first = float(values[0])
    last = float(values[-1])

    if first == 0:

        if last > 0:
            return "Increasing"

        return "Stable"

    change = (
        (last - first)
        / abs(first)
        * 100
    )

    if change >= 10:
        return "Increasing"

    if change <= -10:
        return "Decreasing"

    return "Relatively stable"


# ============================================================
# PREDICTION KPI
# ============================================================

def _prediction_summary(
    monthly,
    prediction
):

    if monthly is None or monthly.empty:
        return

    historical_total = int(
        monthly["Cases"].sum()
    )

    average_cases = float(
        monthly["Cases"].mean()
    )

    latest_cases = int(
        monthly["Cases"].iloc[-1]
    )

    predicted_cases = int(
        round(
            prediction
        )
    )

    if latest_cases > 0:

        change = (
            (predicted_cases - latest_cases)
            / latest_cases
            * 100
        )

    else:

        change = 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Historical Cases",
        f"{historical_total:,}"
    )

    c2.metric(
        "Average Cases / Period",
        f"{average_cases:,.1f}"
    )

    c3.metric(
        "Latest Period Cases",
        f"{latest_cases:,}"
    )

    c4.metric(
        "Next Period Trend Estimate",
        f"{predicted_cases:,}",
        delta=f"{change:+.1f}%"
    )


# ============================================================
# MONTHLY TREND ANALYSIS
# ============================================================

def _monthly_prediction_analysis(df):

    monthly, month_type = _monthly_cases(
        df
    )

    if monthly is None or monthly.empty:

        st.warning(
            "A usable Month or Date column was not found "
            "for prediction analysis."
        )

        return

    if len(monthly) < 2:

        st.warning(
            "At least two historical periods are required "
            "for trend estimation."
        )

        st.dataframe(
            monthly,
            use_container_width=True,
            hide_index=True
        )

        return

    # --------------------------------------------------------
    # Historical values
    # --------------------------------------------------------

    historical_values = (
        monthly["Cases"]
        .astype(float)
        .tolist()
    )

    # --------------------------------------------------------
    # Next-period estimate
    # --------------------------------------------------------

    predictions = _linear_forecast(
        historical_values,
        periods=1
    )

    next_prediction = (
        predictions[0]
        if predictions
        else historical_values[-1]
    )

    _prediction_summary(
        monthly,
        next_prediction
    )

    st.divider()

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    trend = _trend_direction(
        historical_values
    )

    st.info(
        f"Historical trend classification: **{trend}**"
    )

    # --------------------------------------------------------
    # HISTORICAL CHART
    # --------------------------------------------------------

    chart_df = monthly.copy()

    chart_df["Type"] = "Historical"

    chart_df["Value"] = chart_df["Cases"]

    fig = px.line(
        chart_df,
        x="Month",
        y="Value",
        markers=True,
        title="Historical Monthly Case Trend"
    )

    fig.update_traces(
        name="Historical",
        showlegend=True
    )

    st.plotly_chart(
        _layout(fig, 500),
        use_container_width=True
    )

    # --------------------------------------------------------
    # FORECAST TABLE
    # --------------------------------------------------------

    st.subheader(
        "🔮 Next-period Trend Estimate"
    )

    if month_type == "Date":

        last_period = monthly[
            "Month"
        ].max()

        next_period = (
            last_period
            + pd.offsets.MonthBegin(1)
        )

        next_period_label = (
            next_period.strftime(
                "%B %Y"
            )
        )

    else:

        month_order = [
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
            "Dec"
        ]

        observed = [
            str(x)
            for x in monthly["Month"]
        ]

        last_month = observed[-1]

        try:

            last_index = (
                month_order.index(
                    last_month
                )
            )

            next_index = (
                last_index + 1
            ) % 12

            next_period_label = (
                month_order[next_index]
            )

        except ValueError:

            next_period_label = (
                "Next Period"
            )

    forecast_df = pd.DataFrame(
        {
            "Period": [
                next_period_label
            ],
            "Estimated Cases": [
                int(
                    round(
                        next_prediction
                    )
                )
            ],
            "Basis": [
                "Historical linear trend"
            ]
        }
    )

    st.dataframe(
        forecast_df,
        use_container_width=True,
        hide_index=True
    )

    # --------------------------------------------------------
    # HISTORICAL TABLE
    # --------------------------------------------------------

    st.subheader(
        "📋 Historical Monthly Data"
    )

    historical_table = monthly.copy()

    historical_table["Change (%)"] = (
        historical_table["Cases"]
        .pct_change()
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        * 100
    ).round(2)

    st.dataframe(
        historical_table,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# WARD PREDICTION
# ============================================================

def _ward_prediction(df):

    if "Ward" not in df.columns:

        st.info(
            "Ward column is not available."
        )

        return

    monthly_col = _month_column(
        df
    )

    if monthly_col is None:

        st.info(
            "Month/Date column is required "
            "for ward-level trend estimation."
        )

        return

    st.subheader(
        "🏙️ Ward-wise Trend Estimation"
    )

    ward_counts = (
        df["Ward"]
        .dropna()
        .value_counts()
    )

    if ward_counts.empty:

        st.info(
            "No ward data available."
        )

        return

    ward_options = list(
        ward_counts.head(30).index
    )

    selected_ward = st.selectbox(
        "Select Ward",
        ward_options
    )

    ward_df = df[
        df["Ward"] == selected_ward
    ].copy()

    monthly, month_type = _monthly_cases(
        ward_df
    )

    if monthly is None or monthly.empty:

        st.info(
            "No usable monthly data available "
            "for the selected ward."
        )

        return

    if len(monthly) < 2:

        st.warning(
            "At least two historical periods are required."
        )

        st.dataframe(
            monthly,
            use_container_width=True,
            hide_index=True
        )

        return

    values = (
        monthly["Cases"]
        .astype(float)
        .tolist()
    )

    prediction = _linear_forecast(
        values,
        periods=1
    )[0]

    trend = _trend_direction(
        values
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Ward Cases",
        f"{len(ward_df):,}"
    )

    c2.metric(
        "Latest Period",
        f"{int(values[-1]):,}"
    )

    c3.metric(
        "Next-period Estimate",
        f"{int(round(prediction)):,}"
    )

    st.caption(
        f"Historical trend: {trend}"
    )

    chart_df = monthly.copy()

    chart_df["Type"] = "Historical"

    fig = px.line(
        chart_df,
        x="Month",
        y="Cases",
        markers=True,
        title=f"{selected_ward} — Monthly Case Trend"
    )

    st.plotly_chart(
        _layout(fig, 450),
        use_container_width=True
    )


# ============================================================
# FACILITY PREDICTION
# ============================================================

def _facility_prediction(df):

    if "Facility Name Lform" not in df.columns:

        st.info(
            "Facility Name Lform column is not available."
        )

        return

    st.subheader(
        "🏥 Facility-wise Trend Estimation"
    )

    facility_counts = (
        df["Facility Name Lform"]
        .dropna()
        .value_counts()
    )

    if facility_counts.empty:

        st.info(
            "No facility data available."
        )

        return

    facility_options = list(
        facility_counts.head(30).index
    )

    selected_facility = st.selectbox(
        "Select Facility",
        facility_options
    )

    facility_df = df[
        df["Facility Name Lform"]
        == selected_facility
    ].copy()

    monthly, month_type = _monthly_cases(
        facility_df
    )

    if monthly is None or monthly.empty:

        st.info(
            "No usable monthly data available "
            "for the selected facility."
        )

        return

    if len(monthly) < 2:

        st.warning(
            "At least two historical periods are required."
        )

        st.dataframe(
            monthly,
            use_container_width=True,
            hide_index=True
        )

        return

    values = (
        monthly["Cases"]
        .astype(float)
        .tolist()
    )

    prediction = _linear_forecast(
        values,
        periods=1
    )[0]

    trend = _trend_direction(
        values
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Facility Cases",
        f"{len(facility_df):,}"
    )

    c2.metric(
        "Latest Period",
        f"{int(values[-1]):,}"
    )

    c3.metric(
        "Next-period Estimate",
        f"{int(round(prediction)):,}"
    )

    st.caption(
        f"Historical trend: {trend}"
    )

    fig = px.line(
        monthly,
        x="Month",
        y="Cases",
        markers=True,
        title=(
            f"{selected_facility} — "
            "Monthly Case Trend"
        )
    )

    st.plotly_chart(
        _layout(fig, 450),
        use_container_width=True
    )


# ============================================================
# MANAGEMENT INTERPRETATION
# ============================================================

def _management_notes(df):

    st.subheader(
        "📝 Management Planning Indicators"
    )

    notes = []

    # --------------------------------------------------------
    # Ward
    # --------------------------------------------------------

    if "Ward" in df.columns:

        ward_counts = (
            df["Ward"]
            .dropna()
            .value_counts()
        )

        if not ward_counts.empty:

            top_ward = ward_counts.index[0]

            top_cases = int(
                ward_counts.iloc[0]
            )

            notes.append(
                {
                    "Indicator": "Highest current ward burden",
                    "Finding": top_ward,
                    "Current Cases": top_cases
                }
            )

    # --------------------------------------------------------
    # Facility
    # --------------------------------------------------------

    if "Facility Name Lform" in df.columns:

        facility_counts = (
            df["Facility Name Lform"]
            .dropna()
            .value_counts()
        )

        if not facility_counts.empty:

            top_facility = (
                facility_counts.index[0]
            )

            top_cases = int(
                facility_counts.iloc[0]
            )

            notes.append(
                {
                    "Indicator": "Highest current facility burden",
                    "Finding": top_facility,
                    "Current Cases": top_cases
                }
            )

    # --------------------------------------------------------
    # Gender
    # --------------------------------------------------------

    if "Gender" in df.columns:

        gender_counts = (
            df["Gender"]
            .dropna()
            .value_counts()
        )

        if not gender_counts.empty:

            notes.append(
                {
                    "Indicator": "Most represented gender category",
                    "Finding": gender_counts.index[0],
                    "Current Cases": int(
                        gender_counts.iloc[0]
                    )
                }
            )

    # --------------------------------------------------------
    # Disease
    # --------------------------------------------------------

    if "Confirmed Diagnosis" in df.columns:

        disease_counts = (
            df["Confirmed Diagnosis"]
            .dropna()
            .value_counts()
        )

        if not disease_counts.empty:

            notes.append(
                {
                    "Indicator": "Most frequent diagnosis",
                    "Finding": disease_counts.index[0],
                    "Current Cases": int(
                        disease_counts.iloc[0]
                    )
                }
            )

    if notes:

        st.dataframe(
            pd.DataFrame(notes),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No management indicators could be calculated."
        )


# ============================================================
# MAIN FUNCTION
# ============================================================

def render_prediction(df):

    st.title(
        "🔮 Predictive & Trend Analysis"
    )

    st.caption(
        "Historical trend-based estimation for "
        "programme management and planning."
    )

    # --------------------------------------------------------
    # DATA CHECK
    # --------------------------------------------------------

    if df is None:

        st.error(
            "Data could not be loaded."
        )

        return

    if not isinstance(df, pd.DataFrame):

        st.error(
            "The supplied data is not a valid DataFrame."
        )

        return

    if df.empty:

        st.warning(
            "No data available for prediction analysis."
        )

        return

    # Global dashboard filters are already applied in app.py.
    filtered_df = df.copy()

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📈 Overall Trend",
            "🏙️ Ward Prediction",
            "🏥 Facility Prediction",
            "📝 Management Indicators"
        ]
    )

    # ========================================================
    # TAB 1
    # ========================================================

    with tab1:

        _monthly_prediction_analysis(
            filtered_df
        )

    # ========================================================
    # TAB 2
    # ========================================================

    with tab2:

        _ward_prediction(
            filtered_df
        )

    # ========================================================
    # TAB 3
    # ========================================================

    with tab3:

        _facility_prediction(
            filtered_df
        )

    # ========================================================
    # TAB 4
    # ========================================================

    with tab4:

        _management_notes(
            filtered_df
        )

        st.divider()

        st.info(
            "Prediction values are trend-based estimates "
            "derived from the available historical data. "
            "They should be used for programme planning and "
            "monitoring, not as confirmed future case counts."
        )


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================
# Multiple names are supported so that app.py can use
# any of the following without causing an ImportError.

def render_prediction_analysis(df):
    return render_prediction(df)


def render_predictive_analysis(df):
    return render_prediction(df)


def render_forecast(df):
    return render_prediction(df)
