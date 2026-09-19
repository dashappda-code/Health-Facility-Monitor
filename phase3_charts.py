import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# HELPERS
# ============================================================

def clean_series(series):

    return (
        series
        .astype(str)
        .str.strip()
        .replace(
            {
                "": pd.NA,
                "nan": pd.NA,
                "None": pd.NA,
                "NA": pd.NA,
                "N/A": pd.NA,
            }
        )
    )


def find_column(df, candidates):

    normalized = {
        str(col).strip().lower().replace(" ", "").replace("_", ""): col
        for col in df.columns
    }

    for candidate in candidates:

        key = (
            str(candidate)
            .strip()
            .lower()
            .replace(" ", "")
            .replace("_", "")
        )

        if key in normalized:
            return normalized[key]

    return None


def chart_layout(fig, height=450):

    fig.update_layout(
        height=height,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=40
        ),
        legend_title_text="",
        hovermode="x unified"
    )

    return fig


# ============================================================
# MONTH NORMALIZATION
# ============================================================

def create_month_sort(data, month_col):

    result = data.copy()

    result["_Month_Text"] = clean_series(
        result[month_col]
    )

    # Try converting directly to date
    parsed = pd.to_datetime(
        result["_Month_Text"],
        errors="coerce"
    )

    result["_Month_Date"] = parsed

    # If direct conversion fails, try common month formats
    missing = result["_Month_Date"].isna()

    if missing.any():

        formats = [
            "%B %Y",
            "%b %Y",
            "%B-%Y",
            "%b-%Y",
            "%m-%Y",
            "%m/%Y",
            "%Y-%m",
        ]

        for fmt in formats:

            parsed_try = pd.to_datetime(
                result.loc[missing, "_Month_Text"],
                format=fmt,
                errors="coerce"
            )

            result.loc[
                missing,
                "_Month_Date"
            ] = parsed_try

            missing = result["_Month_Date"].isna()

            if not missing.any():
                break

    return result


# ============================================================
# MAIN FUNCTION
# ============================================================

def render_charts(df):

    st.title("📈 Charts & Trends")

    st.caption(
        "Month-wise, year-wise, facility-wise and ward-wise "
        "programme trend analysis."
    )

    if df is None or df.empty:

        st.warning("No data available.")

        return

    data = df.copy()

    # ========================================================
    # COLUMN DETECTION
    # ========================================================

    month_col = find_column(
        data,
        [
            "Month",
            "Reporting Month",
            "Month Name",
            "Month-Year",
            "Month Year",
        ]
    )

    date_col = find_column(
        data,
        [
            "Date",
            "Date of Reporting",
            "Reporting Date",
            "Registration Date",
            "Case Date",
        ]
    )

    year_col = find_column(
        data,
        [
            "Year",
            "Reporting Year",
        ]
    )

    facility_col = find_column(
        data,
        [
            "Facility Name Lform",
            "Facility",
            "Facility Name",
            "Health Facility",
        ]
    )

    ward_col = find_column(
        data,
        [
            "Ward",
            "Ward Name",
            "Ward No",
            "Ward Number",
        ]
    )

    disease_col = find_column(
        data,
        [
            "Confirmed Diagnosis",
            "Disease",
            "Disease Name",
            "Diagnosis",
        ]
    )

    gender_col = find_column(
        data,
        [
            "Gender",
            "Sex",
        ]
    )

    # ========================================================
    # FILTER SECTION
    # ========================================================

    st.divider()

    st.subheader("🎛️ Trend Filters")

    c1, c2, c3 = st.columns(3)

    # --------------------------------------------------------
    # FACILITY FILTER
    # --------------------------------------------------------

    if facility_col:

        facilities = sorted(
            clean_series(
                data[facility_col]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_facilities = c1.multiselect(
            "🏥 Facility",
            facilities,
            placeholder="All Facilities"
        )

    else:

        selected_facilities = []

    # --------------------------------------------------------
    # WARD FILTER
    # --------------------------------------------------------

    if ward_col:

        wards = sorted(
            clean_series(
                data[ward_col]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_wards = c2.multiselect(
            "🗺️ Ward",
            wards,
            placeholder="All Wards"
        )

    else:

        selected_wards = []

    # --------------------------------------------------------
    # DISEASE FILTER
    # --------------------------------------------------------

    if disease_col:

        diseases = sorted(
            clean_series(
                data[disease_col]
            )
            .dropna()
            .unique()
            .tolist()
        )

        selected_diseases = c3.multiselect(
            "🦠 Disease / Diagnosis",
            diseases,
            placeholder="All Diseases"
        )

    else:

        selected_diseases = []

    # ========================================================
    # APPLY FILTERS
    # ========================================================

    filtered = data.copy()

    if selected_facilities:

        filtered = filtered[
            clean_series(
                filtered[facility_col]
            ).isin(selected_facilities)
        ]

    if selected_wards:

        filtered = filtered[
            clean_series(
                filtered[ward_col]
            ).isin(selected_wards)
        ]

    if selected_diseases:

        filtered = filtered[
            clean_series(
                filtered[disease_col]
            ).isin(selected_diseases)
        ]

    if filtered.empty:

        st.warning(
            "No records match the selected filters."
        )

        return

    # ========================================================
    # MANAGEMENT KPI
    # ========================================================

    st.divider()

    st.subheader("📊 Trend Management KPIs")

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Total Records",
        f"{len(filtered):,}"
    )

    k2.metric(
        "Facilities",
        f"{filtered[facility_col].nunique():,}"
        if facility_col
        else "0"
    )

    k3.metric(
        "Wards",
        f"{filtered[ward_col].nunique():,}"
        if ward_col
        else "0"
    )

    k4.metric(
        "Diseases",
        f"{filtered[disease_col].nunique():,}"
        if disease_col
        else "0"
    )

    # ========================================================
    # YEAR-WISE ANALYSIS
    # ========================================================

    st.divider()

    st.subheader("📅 Year-wise Case Comparison")

    if year_col:

        year_table = (
            filtered
            .groupby(year_col)
            .size()
            .reset_index(name="Cases")
        )

        year_table = year_table.sort_values(
            year_col
        )

        st.dataframe(
            year_table,
            use_container_width=True,
            hide_index=True
        )

        fig = px.bar(
            year_table,
            x=year_col,
            y="Cases",
            text="Cases",
            title="Year-wise Case Comparison"
        )

        fig.update_traces(
            textposition="outside"
        )

        st.plotly_chart(
            chart_layout(fig, 450),
            use_container_width=True
        )

    # ========================================================
    # MONTH-WISE ANALYSIS
    # ========================================================

    st.divider()

    st.subheader("📆 Month-wise Complete Analysis")

    if month_col:

        monthly = create_month_sort(
            filtered,
            month_col
        )

        monthly_table = (
            monthly
            .groupby(
                [
                    "_Month_Date",
                    "_Month_Text"
                ],
                dropna=False
            )
            .size()
            .reset_index(name="Cases")
        )

        monthly_table = monthly_table.sort_values(
            [
                "_Month_Date",
                "_Month_Text"
            ],
            na_position="last"
        )

        monthly_table = monthly_table.rename(
            columns={
                "_Month_Text": "Month"
            }
        )

        # Month share
        total_cases = monthly_table["Cases"].sum()

        monthly_table["Share (%)"] = (
            monthly_table["Cases"]
            / total_cases
            * 100
        ).round(2)

        st.dataframe(
            monthly_table[
                [
                    "Month",
                    "Cases",
                    "Share (%)"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        fig = px.line(
            monthly_table,
            x="Month",
            y="Cases",
            markers=True,
            text="Cases",
            title="Month-wise Case Trend"
        )

        fig.update_traces(
            textposition="top center"
        )

        st.plotly_chart(
            chart_layout(fig, 500),
            use_container_width=True
        )

    elif date_col:

        # ----------------------------------------------------
        # DATE-BASED MONTHLY ANALYSIS
        # ----------------------------------------------------

        temp = filtered.copy()

        temp["_Date"] = pd.to_datetime(
            temp[date_col],
            errors="coerce"
        )

        temp = temp.dropna(
            subset=["_Date"]
        )

        if not temp.empty:

            temp["_Month"] = (
                temp["_Date"]
                .dt.to_period("M")
                .astype(str)
            )

            monthly_table = (
                temp
                .groupby("_Month")
                .size()
                .reset_index(name="Cases")
            )

            monthly_table = monthly_table.sort_values(
                "_Month"
            )

            st.dataframe(
                monthly_table,
                use_container_width=True,
                hide_index=True
            )

            fig = px.line(
                monthly_table,
                x="_Month",
                y="Cases",
                markers=True,
                text="Cases",
                title="Month-wise Case Trend"
            )

            st.plotly_chart(
                chart_layout(fig, 500),
                use_container_width=True
            )

        else:

            st.warning(
                "Date column was found but valid dates "
                "could not be identified."
            )

    else:

        st.warning(
            "Month or Date column was not detected."
        )

    # ========================================================
    # MONTH × YEAR COMPARISON
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Month-wise Year Comparison"
    )

    comparison_source = None

    if date_col:

        temp = filtered.copy()

        temp["_Date"] = pd.to_datetime(
            temp[date_col],
            errors="coerce"
        )

        temp = temp.dropna(
            subset=["_Date"]
        )

        if not temp.empty:

            temp["_Year"] = temp["_Date"].dt.year
            temp["_Month_Number"] = temp["_Date"].dt.month
            temp["_Month_Name"] = temp["_Date"].dt.strftime("%b")

            comparison_source = temp

    elif month_col:

        temp = create_month_sort(
            filtered,
            month_col
        )

        temp = temp.dropna(
            subset=["_Month_Date"]
        )

        if not temp.empty:

            temp["_Year"] = (
                temp["_Month_Date"].dt.year
            )

            temp["_Month_Number"] = (
                temp["_Month_Date"].dt.month
            )

            temp["_Month_Name"] = (
                temp["_Month_Date"].dt.strftime("%b")
            )

            comparison_source = temp

    if comparison_source is not None:

        comparison = (
            comparison_source
            .groupby(
                [
                    "_Year",
                    "_Month_Number",
                    "_Month_Name"
                ]
            )
            .size()
            .reset_index(name="Cases")
        )

        comparison = comparison.sort_values(
            [
                "_Year",
                "_Month_Number"
            ]
        )

        fig = px.line(
            comparison,
            x="_Month_Name",
            y="Cases",
            color="_Year",
            markers=True,
            title="Monthly Comparison Across Years"
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Cases"
        )

        st.plotly_chart(
            chart_layout(fig, 550),
            use_container_width=True
        )

        comparison_display = comparison.rename(
            columns={
                "_Year": "Year",
                "_Month_Name": "Month"
            }
        )

        st.dataframe(
            comparison_display[
                [
                    "Year",
                    "Month",
                    "Cases"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # FACILITY-WISE MONTHLY TREND
    # ========================================================

    st.divider()

    st.subheader(
        "🏥 Facility-wise Monthly Trend"
    )

    if facility_col and month_col:

        temp = create_month_sort(
            filtered,
            month_col
        )

        temp = temp.dropna(
            subset=["_Month_Date"]
        )

        if not temp.empty:

            facility_month = (
                temp
                .groupby(
                    [
                        "_Month_Date",
                        facility_col
                    ]
                )
                .size()
                .reset_index(name="Cases")
            )

            top_facilities = (
                facility_month
                .groupby(facility_col)["Cases"]
                .sum()
                .sort_values(
                    ascending=False
                )
                .head(15)
                .index
            )

            facility_month = facility_month[
                facility_month[
                    facility_col
                ].isin(top_facilities)
            ]

            fig = px.line(
                facility_month,
                x="_Month_Date",
                y="Cases",
                color=facility_col,
                markers=True,
                title="Top 15 Facilities - Monthly Trend"
            )

            st.plotly_chart(
                chart_layout(fig, 600),
                use_container_width=True
            )

    # ========================================================
    # WARD-WISE MONTHLY TREND
    # ========================================================

    st.divider()

    st.subheader(
        "🗺️ Ward-wise Monthly Trend"
    )

    if ward_col and month_col:

        temp = create_month_sort(
            filtered,
            month_col
        )

        temp = temp.dropna(
            subset=["_Month_Date"]
        )

        if not temp.empty:

            ward_month = (
                temp
                .groupby(
                    [
                        "_Month_Date",
                        ward_col
                    ]
                )
                .size()
                .reset_index(name="Cases")
            )

            top_wards = (
                ward_month
                .groupby(ward_col)["Cases"]
                .sum()
                .sort_values(
                    ascending=False
                )
                .head(15)
                .index
            )

            ward_month = ward_month[
                ward_month[
                    ward_col
                ].isin(top_wards)
            ]

            fig = px.line(
                ward_month,
                x="_Month_Date",
                y="Cases",
                color=ward_col,
                markers=True,
                title="Top 15 Wards - Monthly Trend"
            )

            st.plotly_chart(
                chart_layout(fig, 600),
                use_container_width=True
            )

    # ========================================================
    # DISEASE-WISE TREND
    # ========================================================

    st.divider()

    st.subheader(
        "🦠 Disease-wise Monthly Trend"
    )

    if disease_col and month_col:

        temp = create_month_sort(
            filtered,
            month_col
        )

        temp = temp.dropna(
            subset=["_Month_Date"]
        )

        if not temp.empty:

            disease_month = (
                temp
                .groupby(
                    [
                        "_Month_Date",
                        disease_col
                    ]
                )
                .size()
                .reset_index(name="Cases")
            )

            top_diseases = (
                disease_month
                .groupby(disease_col)["Cases"]
                .sum()
                .sort_values(
                    ascending=False
                )
                .head(10)
                .index
            )

            disease_month = disease_month[
                disease_month[
                    disease_col
                ].isin(top_diseases)
            ]

            fig = px.line(
                disease_month,
                x="_Month_Date",
                y="Cases",
                color=disease_col,
                markers=True,
                title="Top 10 Diseases - Monthly Trend"
            )

            st.plotly_chart(
                chart_layout(fig, 600),
                use_container_width=True
            )

    # ========================================================
    # GENDER MONTHLY TREND
    # ========================================================

    st.divider()

    st.subheader(
        "👥 Gender-wise Monthly Trend"
    )

    if gender_col and month_col:

        temp = create_month_sort(
            filtered,
            month_col
        )

        temp = temp.dropna(
            subset=["_Month_Date"]
        )

        if not temp.empty:

            gender_month = (
                temp
                .groupby(
                    [
                        "_Month_Date",
                        gender_col
                    ]
                )
                .size()
                .reset_index(name="Cases")
            )

            fig = px.line(
                gender_month,
                x="_Month_Date",
                y="Cases",
                color=gender_col,
                markers=True,
                title="Gender-wise Monthly Trend"
            )

            st.plotly_chart(
                chart_layout(fig, 500),
                use_container_width=True
            )

    # ========================================================
    # TOP MONTH
    # ========================================================

    st.divider()

    st.subheader(
        "🏆 Highest Burden Month"
    )

    if month_col:

        temp = create_month_sort(
            filtered,
            month_col
        )

        month_summary = (
            temp
            .groupby("_Month_Text")
            .size()
            .reset_index(name="Cases")
            .sort_values(
                "Cases",
                ascending=False
            )
        )

        if not month_summary.empty:

            top_month = month_summary.iloc[0]

            c1, c2 = st.columns(2)

            c1.metric(
                "Highest Burden Month",
                str(top_month["_Month_Text"])
            )

            c2.metric(
                "Cases",
                f"{int(top_month['Cases']):,}"
            )

    # ========================================================
    # DATA NOTE
    # ========================================================

    st.info(
        "Trend analysis is based on the records available "
        "after applying the selected filters. "
        "Monthly comparison depends on the availability "
        "and quality of Month/Date fields in the source data."
    )

