```python
import streamlit as st
import pandas as pd

from chart_helpers import (
    render_bar_chart,
    render_line_chart,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _clean_series(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="object")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _valid_text_series(series):
    if series is None or series.empty:
        return series

    return series[
        series.ne("")
        & series.str.lower().ne("nan")
        & series.str.lower().ne("nat")
        & series.str.lower().ne("none")
        & series.str.lower().ne("null")
    ]


# ============================================================
# MONTH NORMALIZATION
# ============================================================

CALENDAR_MONTHS = [
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


def _normalize_month(value):
    if pd.isna(value):
        return None

    text = str(value).strip().lower()

    month_map = {
        "january": "Jan",
        "jan": "Jan",
        "1": "Jan",
        "01": "Jan",

        "february": "Feb",
        "feb": "Feb",
        "2": "Feb",
        "02": "Feb",

        "march": "Mar",
        "mar": "Mar",
        "3": "Mar",
        "03": "Mar",

        "april": "Apr",
        "apr": "Apr",
        "4": "Apr",
        "04": "Apr",

        "may": "May",
        "5": "May",
        "05": "May",

        "june": "Jun",
        "jun": "Jun",
        "6": "Jun",
        "06": "Jun",

        "july": "Jul",
        "jul": "Jul",
        "7": "Jul",
        "07": "Jul",

        "august": "Aug",
        "aug": "Aug",
        "8": "Aug",
        "08": "Aug",

        "september": "Sep",
        "sep": "Sep",
        "sept": "Sep",
        "9": "Sep",
        "09": "Sep",

        "october": "Oct",
        "oct": "Oct",
        "10": "Oct",

        "november": "Nov",
        "nov": "Nov",
        "11": "Nov",

        "december": "Dec",
        "dec": "Dec",
        "12": "Dec",
    }

    return month_map.get(text)


# ============================================================
# WARD SORTING
# ============================================================

def _ward_sort_key(value):
    text = str(value).strip().upper()

    if text.startswith("WARD "):
        text = text.replace("WARD ", "", 1).strip()

    if text.startswith("W"):
        text = text[1:].strip()

    try:
        return (0, int(text))
    except ValueError:
        return (1, text)


def _sort_ward_dataframe(df, column="Ward"):
    if df is None or df.empty or column not in df.columns:
        return df

    result = df.copy()

    result["_ward_sort_key"] = result[column].apply(
        _ward_sort_key
    )

    result = (
        result
        .sort_values(
            "_ward_sort_key",
            kind="stable",
        )
        .drop(
            columns="_ward_sort_key"
        )
        .reset_index(drop=True)
    )

    return result


# ============================================================
# MAIN CHART RENDERER
# ============================================================

def render_charts(df):

    st.subheader("📈 Charts & Trends")

    if df is None or df.empty:
        st.warning(
            "No records available for the selected filters."
        )
        return

    st.caption(
        "Month-wise, disease-wise, pathogen-wise, "
        "facility-wise and ward-wise analysis based on "
        "the currently selected Global Dashboard Filters."
    )

    # ========================================================
    # 1. MONTH-WISE PROGRAMME TREND
    # ========================================================

    st.markdown(
        "### 🗓️ Month-wise Programme Trend"
    )

    if "Month" in df.columns:

        month_series = _clean_series(
            df,
            "Month",
        )

        month_series = _valid_text_series(
            month_series
        )

        if not month_series.empty:

            normalized_months = (
                month_series
                .apply(_normalize_month)
                .dropna()
            )

            if not normalized_months.empty:

                month_counts = (
                    normalized_months
                    .value_counts()
                    .rename_axis("Month")
                    .reset_index(name="Records")
                )

                # Create all 12 months in fixed calendar order.
                ordered_month_df = pd.DataFrame(
                    {
                        "Month": CALENDAR_MONTHS
                    }
                )

                ordered_month_df = ordered_month_df.merge(
                    month_counts,
                    on="Month",
                    how="left",
                )

                ordered_month_df["Records"] = (
                    ordered_month_df["Records"]
                    .fillna(0)
                    .astype(int)
                )

                # Direct Streamlit chart is intentionally used
                # here to preserve the Jan-Dec row order.
                chart_df = ordered_month_df.set_index(
                    "Month"
                )[["Records"]]

                st.bar_chart(
                    chart_df,
                    use_container_width=True,
                )

                st.dataframe(
                    ordered_month_df,
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "Month information is not available "
                    "for the selected records."
                )

        else:

            st.info(
                "Month information is not available "
                "for the selected records."
            )

    # ========================================================
    # 2. MONTHLY DISEASE COMPARISON
    # ========================================================

    st.divider()

    st.markdown(
        "### 🦠 Monthly Disease Comparison"
    )

    if (
        "Month" in df.columns
        and "Disease" in df.columns
    ):

        temp = df[
            ["Month", "Disease"]
        ].copy()

        temp["Month"] = _clean_series(
            temp,
            "Month",
        )

        temp["Disease"] = _clean_series(
            temp,
            "Disease",
        )

        temp = temp[
            temp["Month"].ne("")
            & temp["Disease"].ne("")
            & temp["Month"].str.lower().ne("nan")
            & temp["Disease"].str.lower().ne("nan")
            & temp["Month"].str.lower().ne("none")
            & temp["Disease"].str.lower().ne("none")
        ]

        if not temp.empty:

            temp["Month"] = (
                temp["Month"]
                .apply(_normalize_month)
            )

            temp = temp.dropna(
                subset=["Month"]
            )

            if not temp.empty:

                # Identify the top 10 diseases.
                disease_totals = (
                    temp["Disease"]
                    .value_counts()
                    .head(10)
                )

                selected_diseases = (
                    disease_totals.index.tolist()
                )

                temp = temp[
                    temp["Disease"].isin(
                        selected_diseases
                    )
                ]

                cross_tab = pd.crosstab(
                    temp["Month"],
                    temp["Disease"],
                )

                # Create all 12 months to guarantee
                # calendar order even when a month has
                # zero records.
                ordered_disease_df = pd.DataFrame(
                    index=CALENDAR_MONTHS
                )

                for disease in selected_diseases:
                    if disease in cross_tab.columns:
                        ordered_disease_df[disease] = (
                            cross_tab[disease]
                            .reindex(
                                CALENDAR_MONTHS,
                                fill_value=0,
                            )
                        )
                    else:
                        ordered_disease_df[disease] = 0

                ordered_disease_df = (
                    ordered_disease_df
                    .fillna(0)
                    .astype(int)
                )

                st.line_chart(
                    ordered_disease_df,
                    use_container_width=True,
                )

                st.caption(
                    "The chart displays the top 10 diseases "
                    "by total records within the selected "
                    "filters. Months are shown in calendar order."
                )

                display_disease_df = (
                    ordered_disease_df
                    .reset_index()
                    .rename(
                        columns={
                            "index": "Month"
                        }
                    )
                )

                st.dataframe(
                    display_disease_df,
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "Disease/month information is not "
                    "available for the selected records."
                )

        else:

            st.info(
                "Disease/month information is not "
                "available for the selected records."
            )

    # ========================================================
    # 3. DISEASE-WISE BURDEN
    # ========================================================

    st.divider()

    st.markdown(
        "### 🦠 Disease-wise Burden"
    )

    if "Disease" in df.columns:

        disease_series = _clean_series(
            df,
            "Disease",
        )

        disease_series = _valid_text_series(
            disease_series
        )

        if not disease_series.empty:

            disease_counts = (
                disease_series
                .value_counts()
                .head(15)
                .rename_axis("Disease")
                .reset_index(name="Records")
            )

            render_bar_chart(
                disease_counts.set_index(
                    "Disease"
                )["Records"],
                use_container_width=True,
            )

            st.dataframe(
                disease_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Disease information is not available."
            )

    # ========================================================
    # 4. TEST PERFORMED / PATHOGEN NAME-WISE ANALYSIS
    # ========================================================

    st.divider()

    st.markdown(
        "### 🧪 Test Performed / Pathogen Name-wise Analysis"
    )

    pathogen_column = None

    pathogen_candidates = [
        "Test Performed Pathogen Name",
        "Pathogen Name",
        "Test Performed Pathogen",
        "Pathogen",
    ]

    for candidate in pathogen_candidates:

        if candidate in df.columns:
            pathogen_column = candidate
            break

    # --------------------------------------------------------
    # CASE 1:
    # A combined pathogen column already exists.
    # --------------------------------------------------------

    if pathogen_column is not None:

        pathogen_series = _clean_series(
            df,
            pathogen_column,
        )

        pathogen_series = _valid_text_series(
            pathogen_series
        )

        if not pathogen_series.empty:

            pathogen_counts = (
                pathogen_series
                .value_counts()
                .head(20)
                .rename_axis(
                    "Test Performed Pathogen Name"
                )
                .reset_index(
                    name="Records"
                )
            )

            render_bar_chart(
                pathogen_counts.set_index(
                    "Test Performed Pathogen Name"
                )["Records"],
                use_container_width=True,
            )

            st.dataframe(
                pathogen_counts,
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                f"Pathogen analysis is based on the "
                f"'{pathogen_column}' field."
            )

        else:

            st.info(
                "Pathogen information is not available "
                "for the selected records."
            )

    # --------------------------------------------------------
    # CASE 2:
    # Separate Test Performed and Pathogen Name columns exist.
    # --------------------------------------------------------

    elif (
        "Test Performed" in df.columns
        and "Pathogen Name" in df.columns
    ):

        pathogen_temp = df[
            [
                "Test Performed",
                "Pathogen Name",
            ]
        ].copy()

        pathogen_temp["Test Performed"] = (
            _clean_series(
                pathogen_temp,
                "Test Performed",
            )
        )

        pathogen_temp["Pathogen Name"] = (
            _clean_series(
                pathogen_temp,
                "Pathogen Name",
            )
        )

        pathogen_temp = pathogen_temp[
            pathogen_temp["Test Performed"].ne("")
            & pathogen_temp["Pathogen Name"].ne("")
            & pathogen_temp["Test Performed"]
            .str.lower()
            .ne("nan")
            & pathogen_temp["Pathogen Name"]
            .str.lower()
            .ne("nan")
            & pathogen_temp["Test Performed"]
            .str.lower()
            .ne("none")
            & pathogen_temp["Pathogen Name"]
            .str.lower()
            .ne("none")
        ]

        if not pathogen_temp.empty:

            pathogen_temp[
                "Test Performed Pathogen Name"
            ] = (
                pathogen_temp["Test Performed"]
                + " - "
                + pathogen_temp["Pathogen Name"]
            )

            pathogen_counts = (
                pathogen_temp[
                    "Test Performed Pathogen Name"
                ]
                .value_counts()
                .head(20)
                .rename_axis(
                    "Test Performed Pathogen Name"
                )
                .reset_index(
                    name="Records"
                )
            )

            render_bar_chart(
                pathogen_counts.set_index(
                    "Test Performed Pathogen Name"
                )["Records"],
                use_container_width=True,
            )

            st.dataframe(
                pathogen_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Test performed and pathogen information "
                "is not available for the selected records."
            )

    else:

        st.info(
            "Test Performed / Pathogen Name fields are "
            "not available in the current dataset."
        )

    # ========================================================
    # 5. FACILITY-WISE BURDEN
    # ========================================================

    st.divider()

    st.markdown(
        "### 🏥 Facility-wise Burden"
    )

    if "Facility Name" in df.columns:

        facility_series = _clean_series(
            df,
            "Facility Name",
        )

        facility_series = _valid_text_series(
            facility_series
        )

        if not facility_series.empty:

            facility_counts = (
                facility_series
                .value_counts()
                .head(20)
                .rename_axis("Facility")
                .reset_index(name="Records")
            )

            render_bar_chart(
                facility_counts.set_index(
                    "Facility"
                )["Records"],
                use_container_width=True,
            )

            st.dataframe(
                facility_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Facility information is not available."
            )

    # ========================================================
    # 6. WARD-WISE BURDEN
    # ========================================================

    st.divider()

    st.markdown(
        "### 📍 Ward-wise Burden"
    )

    if "Ward Name" in df.columns:

        ward_series = _clean_series(
            df,
            "Ward Name",
        )

        ward_series = _valid_text_series(
            ward_series
        )

        if not ward_series.empty:

            ward_counts = (
                ward_series
                .value_counts()
                .rename_axis("Ward")
                .reset_index(name="Records")
            )

            ward_counts = _sort_ward_dataframe(
                ward_counts,
                "Ward",
            )

            render_bar_chart(
                ward_counts.set_index(
                    "Ward"
                )["Records"],
                use_container_width=True,
            )

            st.dataframe(
                ward_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Ward information is not available."
            )

    # ========================================================
    # 7. OPD / IPD DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 🏨 OPD / IPD Distribution"
    )

    if "OPD/IPD" in df.columns:

        opd_series = _clean_series(
            df,
            "OPD/IPD",
        )

        opd_series = _valid_text_series(
            opd_series
        )

        if not opd_series.empty:

            opd_counts = (
                opd_series
                .value_counts()
                .rename_axis("OPD/IPD")
                .reset_index(name="Records")
            )

            render_bar_chart(
                opd_counts.set_index(
                    "OPD/IPD"
                )["Records"],
                use_container_width=True,
            )

            st.dataframe(
                opd_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "OPD/IPD information is not available."
            )

    # ========================================================
    # 8. REPORTING DATE TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 📅 Reporting Date Trend"
    )

    if "Reporting Date" in df.columns:

        date_df = df[
            ["Reporting Date"]
        ].copy()

        date_df["Reporting Date"] = (
            pd.to_datetime(
                date_df["Reporting Date"],
                errors="coerce",
            )
        )

        date_df = date_df.dropna(
            subset=["Reporting Date"]
        )

        if not date_df.empty:

            daily_counts = (
                date_df
                .assign(
                    Date=lambda x:
                    x["Reporting Date"].dt.normalize()
                )
                .groupby("Date")
                .size()
                .rename("Records")
            )

            render_line_chart(
                daily_counts,
                use_container_width=True,
            )

        else:

            st.info(
                "Valid reporting dates are not available."
            )

    # ========================================================
    # 9. TREND SUMMARY
    # ========================================================

    st.divider()

    st.markdown(
        "### 📌 Trend Summary"
    )

    summary_columns = st.columns(4)

    # --------------------------------------------------------
    # Records
    # --------------------------------------------------------

    with summary_columns[0]:

        st.metric(
            "Records Analysed",
            f"{len(df):,}",
        )

    # --------------------------------------------------------
    # Diseases
    # --------------------------------------------------------

    with summary_columns[1]:

        if "Disease" in df.columns:

            disease_count = _clean_series(
                df,
                "Disease",
            )

            disease_count = _valid_text_series(
                disease_count
            )

            st.metric(
                "Diseases",
                f"{disease_count.nunique():,}",
            )

        else:

            st.metric(
                "Diseases",
                "0",
            )

    # --------------------------------------------------------
    # Facilities
    # --------------------------------------------------------

    with summary_columns[2]:

        if "Facility Name" in df.columns:

            facility_count = _clean_series(
                df,
                "Facility Name",
            )

            facility_count = _valid_text_series(
                facility_count
            )

            st.metric(
                "Facilities",
                f"{facility_count.nunique():,}",
            )

        else:

            st.metric(
                "Facilities",
                "0",
            )

    # --------------------------------------------------------
    # Wards
    # --------------------------------------------------------

    with summary_columns[3]:

        if "Ward Name" in df.columns:

            ward_count = _clean_series(
                df,
                "Ward Name",
            )

            ward_count = _valid_text_series(
                ward_count
            )

            st.metric(
                "Wards",
                f"{ward_count.nunique():,}",
            )

        else:

            st.metric(
                "Wards",
                "0",
            )
```
