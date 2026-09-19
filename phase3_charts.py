import streamlit as st
import pandas as pd


def _clean_series(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="object")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _month_order(df):
    if df is None or df.empty or "Month" not in df.columns:
        return []

    months = (
        df["Month"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    months = [
        value
        for value in months.unique().tolist()
        if value and value.lower() not in {"nan", "nat"}
    ]

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

    def month_sort(value):
        text = str(value).strip().lower()

        if text in month_map:
            return (0, month_map[text], text)

        try:
            return (1, int(float(text)), text)
        except Exception:
            return (2, 999, text)

    return sorted(months, key=month_sort)


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

    # ---------------------------------------------------------
    # 1. MONTH-WISE ANALYSIS
    # ---------------------------------------------------------

    st.markdown("### 🗓️ Month-wise Programme Trend")

    if "Month" in df.columns:

        month_series = _clean_series(
            df,
            "Month",
        )

        month_series = month_series[
            month_series.ne("")
            & month_series.ne("nan")
            & month_series.ne("NaT")
        ]

        if not month_series.empty:

            month_counts = (
                month_series
                .value_counts()
                .rename_axis("Month")
                .reset_index(name="Records")
            )

            ordered_months = _month_order(df)

            if ordered_months:
                month_counts["sort_order"] = (
                    month_counts["Month"]
                    .map(
                        {
                            month: index
                            for index, month
                            in enumerate(ordered_months)
                        }
                    )
                    .fillna(999)
                )

                month_counts = (
                    month_counts
                    .sort_values(
                        ["sort_order", "Month"]
                    )
                    .drop(columns=["sort_order"])
                    .reset_index(drop=True)
                )

            st.bar_chart(
                month_counts.set_index("Month")["Records"],
                use_container_width=True,
            )

            st.dataframe(
                month_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:
            st.info(
                "Month information is not available for the selected records."
            )

    # ---------------------------------------------------------
    # 2. MONTHLY COMPARISON BY DISEASE
    # ---------------------------------------------------------

    st.divider()

    st.markdown("### 🦠 Monthly Disease Comparison")

    if (
        "Month" in df.columns
        and "Disease" in df.columns
    ):

        temp = df[
            ["Month", "Disease"]
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
        ]

        if not temp.empty:

            cross_tab = pd.crosstab(
                temp["Month"],
                temp["Disease"],
            )

            ordered_months = _month_order(df)

            available_months = [
                month
                for month in ordered_months
                if month in cross_tab.index
            ]

            remaining_months = [
                month
                for month in cross_tab.index
                if month not in available_months
            ]

            cross_tab = cross_tab.reindex(
                available_months + remaining_months
            )

            # Keep the chart readable by selecting the
            # most frequently reported diseases.
            disease_totals = (
                cross_tab.sum()
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

            st.line_chart(
                chart_data,
                use_container_width=True,
            )

            st.caption(
                "Chart displays the top 10 diseases by total "
                "records within the selected filters."
            )

        else:
            st.info(
                "Disease/month information is not available "
                "for the selected records."
            )

    # ---------------------------------------------------------
    # 3. DISEASE-WISE BURDEN
    # ---------------------------------------------------------

    st.divider()

    st.markdown("### 🦠 Disease-wise Burden")

    if "Disease" in df.columns:

        disease_series = _clean_series(
            df,
            "Disease",
        )

        disease_series = disease_series[
            disease_series.ne("")
            & disease_series.ne("nan")
            & disease_series.ne("NaT")
        ]

        if not disease_series.empty:

            disease_counts = (
                disease_series
                .value_counts()
                .head(15)
                .rename_axis("Disease")
                .reset_index(name="Records")
            )

            st.bar_chart(
                disease_counts.set_index("Disease")["Records"],
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

    # ---------------------------------------------------------
    # 4. FACILITY-WISE BURDEN
    # ---------------------------------------------------------

    st.divider()

    st.markdown("### 🏥 Facility-wise Burden")

    if "Facility Name" in df.columns:

        facility_series = _clean_series(
            df,
            "Facility Name",
        )

        facility_series = facility_series[
            facility_series.ne("")
            & facility_series.ne("nan")
            & facility_series.ne("NaT")
        ]

        if not facility_series.empty:

            facility_counts = (
                facility_series
                .value_counts()
                .head(20)
                .rename_axis("Facility")
                .reset_index(name="Records")
            )

            st.bar_chart(
                facility_counts.set_index("Facility")["Records"],
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

    # ---------------------------------------------------------
    # 5. WARD-WISE BURDEN
    # ---------------------------------------------------------

    st.divider()

    st.markdown("### 📍 Ward-wise Burden")

    if "Ward Name" in df.columns:

        ward_series = _clean_series(
            df,
            "Ward Name",
        )

        ward_series = ward_series[
            ward_series.ne("")
            & ward_series.ne("nan")
            & ward_series.ne("NaT")
        ]

        if not ward_series.empty:

            ward_counts = (
                ward_series
                .value_counts()
                .head(20)
                .rename_axis("Ward")
                .reset_index(name="Records")
            )

            st.bar_chart(
                ward_counts.set_index("Ward")["Records"],
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

    # ---------------------------------------------------------
    # 6. OPD / IPD COMPARISON
    # ---------------------------------------------------------

    st.divider()

    st.markdown("### 🏨 OPD / IPD Distribution")

    if "OPD/IPD" in df.columns:

        opd_series = _clean_series(
            df,
            "OPD/IPD",
        )

        opd_series = opd_series[
            opd_series.ne("")
            & opd_series.ne("nan")
            & opd_series.ne("NaT")
        ]

        if not opd_series.empty:

            opd_counts = (
                opd_series
                .value_counts()
                .rename_axis("OPD/IPD")
                .reset_index(name="Records")
            )

            st.bar_chart(
                opd_counts.set_index("OPD/IPD")["Records"],
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

    # ---------------------------------------------------------
    # 7. REPORTING DATE TREND
    # ---------------------------------------------------------

    st.divider()

    st.markdown("### 📅 Reporting Date Trend")

    if "Reporting Date" in df.columns:

        date_df = df[
            ["Reporting Date"]
        ].copy()

        date_df["Reporting Date"] = pd.to_datetime(
            date_df["Reporting Date"],
            errors="coerce",
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

            st.line_chart(
                daily_counts,
                use_container_width=True,
            )

        else:
            st.info(
                "Valid reporting dates are not available."
            )

    # ---------------------------------------------------------
    # 8. SUMMARY
    # ---------------------------------------------------------

    st.divider()

    st.markdown("### 📌 Trend Summary")

    summary_columns = st.columns(4)

    with summary_columns[0]:
        st.metric(
            "Records Analysed",
            f"{len(df):,}",
        )

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
