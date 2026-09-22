import streamlit as st
import pandas as pd
import numpy as np

from chart_helpers import render_line_chart


def _clean_text(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="object")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _month_number(value):
    text = str(value).strip().lower()

    month_map = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "sept": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    if text in month_map:
        return month_map[text]

    try:
        number = int(float(text))

        if 1 <= number <= 12:
            return number

    except Exception:
        pass

    return 99


def _prepare_monthly_data(df):

    if df is None or df.empty:
        return pd.DataFrame()

    if "Month" not in df.columns:
        return pd.DataFrame()

    temp = df.copy()

    temp["Month"] = (
        temp["Month"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    temp = temp[
        temp["Month"].ne("")
        & temp["Month"].ne("nan")
        & temp["Month"].ne("NaT")
    ]

    if temp.empty:
        return pd.DataFrame()

    # ---------------------------------------------------------
    # Prefer Year + Month when Year is available
    # ---------------------------------------------------------

    if "Year" in temp.columns:

        temp["Year"] = (
            temp["Year"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        temp["Year_Number"] = pd.to_numeric(
            temp["Year"],
            errors="coerce",
        )

        temp["Month_Number"] = (
            temp["Month"]
            .map(_month_number)
        )

        valid_year = (
            temp["Year_Number"].notna()
            & temp["Year_Number"].between(
                2000,
                2100,
            )
        )

        valid_month = (
            temp["Month_Number"].between(
                1,
                12,
            )
        )

        temp = temp[
            valid_year
            & valid_month
        ]

        if temp.empty:
            return pd.DataFrame()

        monthly = (
            temp
            .groupby(
                [
                    "Year_Number",
                    "Month_Number",
                ],
                dropna=False,
            )
            .size()
            .reset_index(
                name="Records"
            )
        )

        monthly["Period"] = (
            monthly["Year_Number"]
            .astype(int)
            .astype(str)
            + "-"
            + monthly["Month_Number"]
            .astype(int)
            .astype(str)
            .str.zfill(2)
        )

        monthly = monthly.sort_values(
            [
                "Year_Number",
                "Month_Number",
            ]
        )

        return monthly.reset_index(
            drop=True
        )

    # ---------------------------------------------------------
    # Fallback: Month only
    # ---------------------------------------------------------

    temp["Month_Number"] = (
        temp["Month"]
        .map(_month_number)
    )

    temp = temp[
        temp["Month_Number"].between(
            1,
            12,
        )
    ]

    if temp.empty:
        return pd.DataFrame()

    monthly = (
        temp
        .groupby(
            "Month_Number"
        )
        .size()
        .reset_index(
            name="Records"
        )
    )

    monthly["Period"] = (
        monthly["Month_Number"]
        .astype(int)
        .map(
            {
                1: "January",
                2: "February",
                3: "March",
                4: "April",
                5: "May",
                6: "June",
                7: "July",
                8: "August",
                9: "September",
                10: "October",
                11: "November",
                12: "December",
            }
        )
    )

    return monthly.sort_values(
        "Month_Number"
    ).reset_index(
        drop=True
    )


def _calculate_projection(values):

    numeric = pd.to_numeric(
        values,
        errors="coerce",
    )

    numeric = numeric[
        np.isfinite(numeric)
    ]

    if numeric.empty:
        return None

    if len(numeric) == 1:
        return float(
            numeric.iloc[-1]
        )

    # ---------------------------------------------------------
    # Weighted recent baseline
    # ---------------------------------------------------------

    recent = numeric.tail(
        min(3, len(numeric))
    )

    weights = np.arange(
        1,
        len(recent) + 1,
        dtype=float,
    )

    weighted_average = float(
        np.average(
            recent,
            weights=weights,
        )
    )

    # ---------------------------------------------------------
    # Linear trend
    # ---------------------------------------------------------

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

        next_trend = (
            slope * len(numeric)
            + intercept
        )

    except Exception:

        next_trend = weighted_average

    # ---------------------------------------------------------
    # Combine recent level + trend
    # ---------------------------------------------------------

    projection = (
        weighted_average * 0.70
        + next_trend * 0.30
    )

    # Counts cannot be negative.
    projection = max(
        0,
        projection,
    )

    return float(
        projection
    )


def render_prediction(df):

    st.subheader("🔮 Prediction & Trend Projection")

    if df is None or df.empty:
        st.warning(
            "No records available for the selected filters."
        )
        return

    st.caption(
        "Historical trend and indicative projection based on "
        "the currently filtered programme data."
    )

    # =========================================================
    # IMPORTANT METHODOLOGICAL NOTE
    # =========================================================

    st.info(
        "⚠️ The projection shown in this section is an "
        "indicative statistical estimate based on historical "
        "record volume. It is not a confirmed disease forecast "
        "and should not be interpreted as a clinical prediction."
    )

    # =========================================================
    # 1. MONTHLY HISTORICAL DATA
    # =========================================================

    monthly = _prepare_monthly_data(
        df
    )

    if monthly.empty:

        st.warning(
            "Insufficient Year/Month information is available "
            "to generate a historical monthly projection."
        )

        return

    st.markdown("### 📈 Historical Monthly Trend")

    trend_data = monthly[
        [
            "Period",
            "Records",
        ]
    ].copy()

    trend_data = trend_data.set_index(
        "Period"
    )

    render_line_chart(
        trend_data["Records"],
        use_container_width=True,
    )

    # =========================================================
    # 2. MOVING AVERAGE
    # =========================================================

    st.divider()

    st.markdown("### 📊 Moving Average")

    moving_average = (
        monthly["Records"]
        .rolling(
            window=3,
            min_periods=1,
        )
        .mean()
        .round(2)
    )

    moving_df = pd.DataFrame(
        {
            "Period": monthly["Period"],
            "Actual Records": monthly["Records"],
            "3-Period Moving Average": moving_average,
        }
    )

    render_line_chart(
        moving_df.set_index(
            "Period"
        ),
        use_container_width=True,
    )

    # =========================================================
    # 3. INDICATIVE NEXT PERIOD PROJECTION
    # =========================================================

    st.divider()

    st.markdown(
        "### 🔮 Indicative Next-Period Projection"
    )

    projection = _calculate_projection(
        monthly["Records"]
    )

    if projection is None:

        st.warning(
            "Projection could not be calculated."
        )

    else:

        last_value = float(
            monthly["Records"]
            .iloc[-1]
        )

        recent_values = monthly[
            "Records"
        ].tail(
            min(3, len(monthly))
        )

        recent_average = float(
            recent_values.mean()
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Latest Period Records",
                f"{int(last_value):,}",
            )

        with c2:
            st.metric(
                "Recent 3-Period Average",
                f"{recent_average:,.1f}",
            )

        with c3:
            st.metric(
                "Indicative Next Period",
                f"{projection:,.0f}",
            )

        st.caption(
            "Projection is derived from recent record level "
            "and historical linear trend. It should be used "
            "for programme planning context only."
        )

    # =========================================================
    # 4. RECENT PERIOD PERFORMANCE
    # =========================================================

    st.divider()

    st.markdown("### 📋 Recent Period Performance")

    recent = monthly.tail(
        min(12, len(monthly))
    ).copy()

    recent["3-Period Moving Average"] = (
        recent["Records"]
        .rolling(
            window=3,
            min_periods=1,
        )
        .mean()
        .round(2)
    )

    recent["Difference from Moving Average"] = (
        recent["Records"]
        - recent["3-Period Moving Average"]
    ).round(2)

    st.dataframe(
        recent[
            [
                "Period",
                "Records",
                "3-Period Moving Average",
                "Difference from Moving Average",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # 5. DISEASE-WISE HISTORICAL TREND
    # =========================================================

    st.divider()

    st.markdown("### 🦠 Disease-wise Historical Trend")

    if (
        "Disease" in df.columns
        and "Year" in df.columns
        and "Month" in df.columns
    ):

        disease_df = df[
            [
                "Year",
                "Month",
                "Disease",
            ]
        ].copy()

        disease_df["Disease"] = (
            disease_df["Disease"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_df["Year_Number"] = pd.to_numeric(
            disease_df["Year"],
            errors="coerce",
        )

        disease_df["Month_Number"] = (
            disease_df["Month"]
            .fillna("")
            .astype(str)
            .str.strip()
            .map(_month_number)
        )

        disease_df = disease_df[
            disease_df["Disease"].ne("")
            & disease_df["Disease"].ne("nan")
            & disease_df["Year_Number"].between(
                2000,
                2100,
            )
            & disease_df["Month_Number"].between(
                1,
                12,
            )
        ]

        if not disease_df.empty:

            disease_totals = (
                disease_df["Disease"]
                .value_counts()
                .head(10)
            )

            selected_disease = st.selectbox(
                "Select disease",
                options=disease_totals.index.tolist(),
                key="prediction_disease",
            )

            selected_df = disease_df[
                disease_df["Disease"]
                == selected_disease
            ].copy()

            disease_monthly = (
                selected_df
                .groupby(
                    [
                        "Year_Number",
                        "Month_Number",
                    ]
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .sort_values(
                    [
                        "Year_Number",
                        "Month_Number",
                    ]
                )
            )

            disease_monthly["Period"] = (
                disease_monthly["Year_Number"]
                .astype(int)
                .astype(str)
                + "-"
                + disease_monthly["Month_Number"]
                .astype(int)
                .astype(str)
                .str.zfill(2)
            )

            render_line_chart(
                disease_monthly.set_index(
                    "Period"
                )["Records"],
                use_container_width=True,
            )

            disease_projection = (
                _calculate_projection(
                    disease_monthly["Records"]
                )
            )

            if disease_projection is not None:

                st.metric(
                    f"Indicative Next Period - {selected_disease}",
                    f"{disease_projection:,.0f}",
                )

                st.caption(
                    "This is an indicative historical-trend "
                    "projection, not a clinical or epidemiological forecast."
                )

        else:

            st.info(
                "Sufficient disease-wise monthly data "
                "is not available."
            )

    # =========================================================
    # 6. FACILITY-WISE TREND
    # =========================================================

    st.divider()

    st.markdown("### 🏥 Facility-wise Historical Trend")

    if (
        "Facility Name" in df.columns
        and "Year" in df.columns
        and "Month" in df.columns
    ):

        facility_df = df[
            [
                "Year",
                "Month",
                "Facility Name",
            ]
        ].copy()

        facility_df["Facility Name"] = (
            facility_df["Facility Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_df["Year_Number"] = pd.to_numeric(
            facility_df["Year"],
            errors="coerce",
        )

        facility_df["Month_Number"] = (
            facility_df["Month"]
            .fillna("")
            .astype(str)
            .str.strip()
            .map(_month_number)
        )

        facility_df = facility_df[
            facility_df["Facility Name"].ne("")
            & facility_df["Facility Name"].ne("nan")
            & facility_df["Year_Number"].between(
                2000,
                2100,
            )
            & facility_df["Month_Number"].between(
                1,
                12,
            )
        ]

        if not facility_df.empty:

            facility_totals = (
                facility_df["Facility Name"]
                .value_counts()
                .head(20)
            )

            selected_facility = st.selectbox(
                "Select facility",
                options=facility_totals.index.tolist(),
                key="prediction_facility",
            )

            selected_facility_df = facility_df[
                facility_df["Facility Name"]
                == selected_facility
            ].copy()

            facility_monthly = (
                selected_facility_df
                .groupby(
                    [
                        "Year_Number",
                        "Month_Number",
                    ]
                )
                .size()
                .reset_index(
                    name="Records"
                )
                .sort_values(
                    [
                        "Year_Number",
                        "Month_Number",
                    ]
                )
            )

            facility_monthly["Period"] = (
                facility_monthly["Year_Number"]
                .astype(int)
                .astype(str)
                + "-"
                + facility_monthly["Month_Number"]
                .astype(int)
                .astype(str)
                .str.zfill(2)
            )

            render_line_chart(
                facility_monthly.set_index(
                    "Period"
                )["Records"],
                use_container_width=True,
            )

            facility_projection = (
                _calculate_projection(
                    facility_monthly["Records"]
                )
            )

            if facility_projection is not None:

                st.metric(
                    f"Indicative Next Period - {selected_facility}",
                    f"{facility_projection:,.0f}",
                )

        else:

            st.info(
                "Sufficient facility-wise monthly data "
                "is not available."
            )

    # =========================================================
    # 7. MODEL / METHOD INFORMATION
    # =========================================================

    st.divider()

    st.markdown("### ℹ️ Projection Method")

    method_table = pd.DataFrame(
        {
            "Component": [
                "Historical input",
                "Recent baseline",
                "Trend component",
                "Projection type",
                "Interpretation",
            ],
            "Description": [
                "Monthly filtered programme records",
                "Weighted average of recent periods",
                "Simple linear historical trend",
                "Indicative next-period estimate",
                "Planning support only",
            ],
        }
    )

    st.dataframe(
        method_table,
        use_container_width=True,
        hide_index=True,
    )

    st.warning(
        "Programme managers should interpret projections "
        "alongside surveillance quality, reporting completeness, "
        "seasonality, outbreaks, testing practices and other "
        "epidemiological information."
    )
