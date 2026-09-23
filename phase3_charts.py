
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


# ============================================================
# MONTH ORDER
# ============================================================

def _month_sort_value(value):
    """
    Convert month values into calendar month numbers.

    Supports:
    January, Jan, JAN
    February, Feb, FEB
    ...
    December, Dec, DEC
    1, 01 ... 12
    """

    if pd.isna(value):
        return 999

    text = str(value).strip().lower()

    if text in {"", "nan", "nat", "none"}:
        return 999

    month_map = {
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sep": 9,
        "sept": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12,
    }

    if text in month_map:
        return month_map[text]

    # Numeric month
    try:
        number = int(float(text))

        if 1 <= number <= 12:
            return number

    except Exception:
        pass

    # Date-like month values
    try:
        parsed = pd.to_datetime(
            text,
            errors="coerce",
        )

        if not pd.isna(parsed):
            return int(parsed.month)

    except Exception:
        pass

    return 999


def _sort_month_dataframe(df, column="Month"):
    """
    Sort a dataframe strictly in calendar month order.
    """

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return df

    result = df.copy()

    result["_month_order"] = (
        result[column]
        .apply(_month_sort_value)
    )

    result = (
        result
        .sort_values(
            "_month_order",
            kind="stable",
        )
        .drop(
            columns="_month_order"
        )
        .reset_index(
            drop=True
        )
    )

    return result


# ============================================================
# WARD ORDER
# ============================================================

def _sort_ward_dataframe(df, column="Ward"):
    """
    Sort wards alphabetically:
    Ward A -> Ward B -> Ward C -> ... -> Ward T
    """

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return df

    result = df.copy()

    result["_ward_order"] = (
        result[column]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    result = (
        result
        .sort_values(
            "_ward_order",
            kind="stable",
        )
        .drop(
            columns="_ward_order"
        )
        .reset_index(
            drop=True
        )
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
        "Month-wise, disease-wise, facility-wise and ward-wise "
        "analysis based on the currently selected Global Dashboard Filters."
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

        month_series = month_series[
            month_series.ne("")
            & month_series.str.lower().ne("nan")
            & month_series.str.lower().ne("nat")
            & month_series.str.lower().ne("none")
        ]

        if not month_series.empty:

            month_counts = (
                month_series
                .value_counts()
                .rename_axis("Month")
                .reset_index(
                    name="Records"
                )
            )

            # ------------------------------------------------
            # FORCE JAN -> FEB -> MAR -> ... -> DEC
            # ------------------------------------------------

            month_counts = _sort_month_dataframe(
                month_counts,
                "Month",
            )

            # ------------------------------------------------
            # Keep categorical order
            # ------------------------------------------------

            ordered_month_labels = (
                month_counts["Month"]
                .astype(str)
                .tolist()
            )

            month_counts["Month"] = pd.Categorical(
                month_counts["Month"].astype(str),
                categories=ordered_month_labels,
                ordered=True,
            )

            month_counts = (
                month_counts
                .sort_values(
                    "Month",
                    kind="stable",
                )
                .reset_index(
                    drop=True
                )
            )

            chart_series = (
                month_counts
                .set_index("Month")["Records"]
            )

            render_bar_chart(
                chart_series,
                use_container_width=True,
            )

            display_month_counts = (
                month_counts.copy()
            )

            display_month_counts["Month"] = (
                display_month_counts["Month"]
                .astype(str)
            )

            st.dataframe(
                display_month_counts,
                use_container_width=True,
                hide_index=True,
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
            [
                "Month",
                "Disease",
            ]
        ].copy()

        temp["Month"] = (
            temp["Month"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        temp["Disease"] = (
            temp["Disease"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        temp = temp[
            temp["Month"].ne("")
            & temp["Disease"].ne("")
            & temp["Month"].str.lower().ne("nan")
            & temp["Disease"].str.lower().ne("nan")
            & temp["Month"].str.lower().ne("nat")
            & temp["Disease"].str.lower().ne("nat")
            & temp["Month"].str.lower().ne("none")
            & temp["Disease"].str.lower().ne("none")
        ]

        if not temp.empty:

            cross_tab = pd.crosstab(
                temp["Month"],
                temp["Disease"],
            )

            # ------------------------------------------------
            # FORCE CALENDAR MONTH ORDER
            # ------------------------------------------------

            month_index = pd.DataFrame(
                {
                    "Month": cross_tab.index.astype(str)
                }
            )

            month_index = _sort_month_dataframe(
                month_index,
                "Month",
            )

            ordered_months = (
                month_index["Month"]
                .tolist()
            )

            cross_tab.index = (
                cross_tab.index
                .astype(str)
            )

            cross_tab = cross_tab.reindex(
                ordered_months
            )

            # ------------------------------------------------
            # TOP 10 DISEASES
            # ------------------------------------------------

            disease_totals = (
                cross_tab
                .sum()
                .sort_values(
                    ascending=False
                )
            )

            selected_diseases = (
                disease_totals
                .head(10)
                .index
                .tolist()
            )

            chart_data = cross_tab[
                selected_diseases
            ]

            render_line_chart(
                chart_data,
                use_container_width=True,
            )

            st.caption(
                "Chart displays the top 10 diseases by total "
                "records within the selected filters. "
                "Months are shown in calendar order."
            )

        else:

            st.info(
                "Disease/month information is not available "
                "for the selected records."
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

        disease_series = disease_series[
            disease_series.ne("")
            & disease_series.str.lower().ne("nan")
            & disease_series.str.lower().ne("nat")
            & disease_series.str.lower().ne("none")
        ]

        if not disease_series.empty:

            disease_counts = (
                disease_series
                .value_counts()
                .head(15)
                .rename_axis("Disease")
                .reset_index(
                    name="Records"
                )
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
    # 4. FACILITY-WISE BURDEN
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

        facility_series = facility_series[
            facility_series.ne("")
            & facility_series.str.lower().ne("nan")
            & facility_series.str.lower().ne("nat")
            & facility_series.str.lower().ne("none")
        ]

        if not facility_series.empty:

            facility_counts = (
                facility_series
                .value_counts()
                .head(20)
                .rename_axis("Facility")
                .reset_index(
                    name="Records"
                )
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
    # 5. WARD-WISE BURDEN
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

        ward_series = ward_series[
            ward_series.ne("")
            & ward_series.str.lower().ne("nan")
            & ward_series.str.lower().ne("nat")
            & ward_series.str.lower().ne("none")
        ]

        if not ward_series.empty:

            ward_counts = (
                ward_series
                .value_counts()
                .rename_axis("Ward")
                .reset_index(
                    name="Records"
                )
            )

            # ------------------------------------------------
            # FORCE WARD A -> B -> C -> ... -> T
            # ------------------------------------------------

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
    # 6. OPD / IPD COMPARISON
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

        opd_series = opd_series[
            opd_series.ne("")
            & opd_series.str.lower().ne("nan")
            & opd_series.str.lower().ne("nat")
            & opd_series.str.lower().ne("none")
        ]

        if not opd_series.empty:

            opd_counts = (
                opd_series
                .value_counts()
                .rename_axis("OPD/IPD")
                .reset_index(
                    name="Records"
                )
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
    # 7. REPORTING DATE TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 📅 Reporting Date Trend"
    )

    if "Reporting Date" in df.columns:

        date_df = df[
            ["Reporting Date"]
        ].copy()

        date_df["Reporting Date"] = pd.to_datetime(
            date_df["Reporting Date"],
            errors="coerce",
        )

        date_df = date_df.dropna(
            subset=[
                "Reporting Date"
            ]
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
    # 8. SUMMARY
    # ========================================================

    st.divider()

    st.markdown(
        "### 📌 Trend Summary"
    )

    summary_columns = st.columns(4)

    # --------------------------------------------------------
    # RECORDS
    # --------------------------------------------------------

    with summary_columns[0]:

        st.metric(
            "Records Analysed",
            f"{len(df):,}",
        )

    # --------------------------------------------------------
    # DISEASES
    # --------------------------------------------------------

    with summary_columns[1]:

        if "Disease" in df.columns:

            disease_count = (
                df["Disease"]
                .dropna()
                .astype(str)
                .str.strip()
            )

            disease_count = disease_count[
                disease_count.ne("")
                & disease_count.str.lower().ne("nan")
                & disease_count.str.lower().ne("nat")
                & disease_count.str.lower().ne("none")
            ]

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
    # FACILITIES
    # --------------------------------------------------------

    with summary_columns[2]:

        if "Facility Name" in df.columns:

            facility_count = (
                df["Facility Name"]
                .dropna()
                .astype(str)
                .str.strip()
            )

            facility_count = facility_count[
                facility_count.ne("")
                & facility_count.str.lower().ne("nan")
                & facility_count.str.lower().ne("nat")
                & facility_count.str.lower().ne("none")
            ]

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
    # WARDS
    # --------------------------------------------------------

    with summary_columns[3]:

        if "Ward Name" in df.columns:

            ward_count = (
                df["Ward Name"]
                .dropna()
                .astype(str)
                .str.strip()
            )

            ward_count = ward_count[
                ward_count.ne("")
                & ward_count.str.lower().ne("nan")
                & ward_count.str.lower().ne("nat")
                & ward_count.str.lower().ne("none")
            ]

            st.metric(
                "Wards",
                f"{ward_count.nunique():,}",
            )

        else:

            st.metric(
                "Wards",
                "0",
            )


