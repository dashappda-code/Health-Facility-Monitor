import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from phase2_overview import (
    apply_filters,
    create_filters,
)


# ============================================================
# PREDICTION PAGE
# ============================================================

def render_prediction(df):

    filters = create_filters(df)

    filtered_df = apply_filters(
        df,
        **filters,
    )

    st.title(
        "🔮 Trend Projection"
    )

    st.caption(
        "Exploratory case-count projection based on historical trend"
    )

    st.warning(
        "This is an exploratory statistical projection, "
        "not a clinical diagnosis or official forecast."
    )

    if filtered_df.empty:

        st.warning(
            "No records match the selected filters."
        )

        return

    # ========================================================
    # MONTHLY DATA
    # ========================================================

    data = filtered_df.copy()

    data = data.dropna(
        subset=[
            "Reporting Date",
        ]
    )

    if data.empty:

        st.warning(
            "Reporting Date data is not available."
        )

        return

    monthly = (
        data
        .set_index("Reporting Date")
        .resample("MS")
        .size()
        .reset_index(
            name="Cases"
        )
    )

    if len(monthly) < 3:

        st.info(
            "At least 3 months of historical data "
            "is recommended for trend projection."
        )

        return

    # ========================================================
    # HISTORICAL TREND
    # ========================================================

    st.subheader(
        "📈 Historical Monthly Cases"
    )

    fig_history = px.line(
        monthly,
        x="Reporting Date",
        y="Cases",
        markers=True,
        title="Historical Monthly Cases",
    )

    fig_history.update_layout(
        height=450
    )

    st.plotly_chart(
        fig_history,
        use_container_width=True,
    )

    # ========================================================
    # LINEAR PROJECTION
    # ========================================================

    horizon = st.slider(
        "Projection months",
        min_value=1,
        max_value=6,
        value=3,
    )

    y = monthly["Cases"].astype(float).values

    x = np.arange(
        len(y),
        dtype=float,
    )

    # Linear regression
    slope, intercept = np.polyfit(
        x,
        y,
        1,
    )

    future_x = np.arange(
        len(y),
        len(y) + horizon,
        dtype=float,
    )

    predictions = (
        intercept
        + slope * future_x
    )

    predictions = np.maximum(
        predictions,
        0,
    )

    last_date = monthly[
        "Reporting Date"
    ].max()

    future_dates = pd.date_range(
        start=last_date
        + pd.offsets.MonthBegin(1),
        periods=horizon,
        freq="MS",
    )

    forecast = pd.DataFrame(
        {
            "Reporting Date": future_dates,
            "Cases": predictions,
            "Type": "Projected",
        }
    )

    historical = monthly[
        [
            "Reporting Date",
            "Cases",
        ]
    ].copy()

    historical["Type"] = (
        "Historical"
    )

    combined = pd.concat(
        [
            historical,
            forecast,
        ],
        ignore_index=True,
    )

    # ========================================================
    # FORECAST CHART
    # ========================================================

    st.subheader(
        "🔮 Historical + Projected Trend"
    )

    fig_forecast = px.line(
        combined,
        x="Reporting Date",
        y="Cases",
        color="Type",
        markers=True,
        title="Historical and Projected Monthly Cases",
    )

    fig_forecast.update_layout(
        height=500
    )

    st.plotly_chart(
        fig_forecast,
        use_container_width=True,
    )

    # ========================================================
    # FORECAST TABLE
    # ========================================================

    st.subheader(
        "Projected Cases"
    )

    forecast_display = forecast.copy()

    forecast_display["Cases"] = (
        forecast_display["Cases"]
        .round()
        .astype(int)
    )

    forecast_display[
        "Reporting Date"
    ] = forecast_display[
        "Reporting Date"
    ].dt.strftime(
        "%b %Y"
    )

    st.dataframe(
        forecast_display,
        use_container_width=True,
        hide_index=True,
    )
