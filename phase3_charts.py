import streamlit as st
import pandas as pd

from chart_helpers import (
render_bar_chart,
render_line_chart,
)

def _clean_series(df, column):
if df is None or df.empty or column not in df.columns:
return pd.Series(dtype="object")

```
return (
    df[column]
    .fillna("")
    .astype(str)
    .str.strip()
)
```

def _valid_series(df, column):
series = _clean_series(df, column)

```
if series.empty:
    return series

return series[
    series.ne("")
    & series.ne("nan")
    & series.ne("NaN")
    & series.ne("NaT")
    & series.ne("None")
]
```

def _month_order(df):
if df is None or df.empty or "Month" not in df.columns:
return []

```
months = (
    df["Month"]
    .fillna("")
    .astype(str)
    .str.strip()
)

months = [
    value
    for value in months.unique().tolist()
    if value
    and value.lower() not in {"nan", "nat", "none"}
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
```

def render_charts(df):

```
st.subheader("📈 Charts & Trends")

if df is None or df.empty:
    st.warning(
        "No records available for the selected filters."
    )
    return

st.caption(
    "Month-wise, disease-wise, facility-wise, ward-wise "
    "and pathogen-wise analysis based on the currently "
    "selected Global Dashboard Filters."
)

# ---------------------------------------------------------
# 1. MONTH-WISE ANALYSIS
# ---------------------------------------------------------

st.markdown("### 🗓️ Month-wise Programme Trend")

if "Month" in df.columns:

    month_series = _valid_series(
        df,
        "Month",
    )

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

        render_bar_chart(
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

        render_line_chart(
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

    disease_series = _valid_series(
        df,
        "Disease",
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

    facility_series = _valid_series(
        df,
        "Facility Name",
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

    ward_series = _valid_series(
        df,
        "Ward Name",
    )

    if not ward_series.empty:

        ward_counts = (
            ward_series
            .value_counts()
            .head(20)
            .rename_axis("Ward")
            .reset_index(name="Records")
        )

        render_bar_chart(
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

    opd_series = _valid_series(
        df,
        "OPD/IPD",
    )

    if not opd_series.empty:

        opd_counts = (
            opd_series
            .value_counts()
            .rename_axis("OPD/IPD")
            .reset_index(name="Records")
        )

        render_bar_chart(
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
# 7. TEST PERFORMED PATHOGEN-WISE ANALYSIS
# ---------------------------------------------------------

st.divider()

st.markdown(
    "### 🧬 Test Performed Pathogen-wise Analysis"
)

pathogen_column = None

if "Test Performed Pathogen Name" in df.columns:
    pathogen_column = "Test Performed Pathogen Name"

elif "Pathogen Name" in df.columns:
    pathogen_column = "Pathogen Name"

if pathogen_column is not None:

    pathogen_series = _valid_series(
        df,
        pathogen_column,
    )

    if not pathogen_series.empty:

        # -------------------------------------------------
        # Pathogen KPI summary
        # -------------------------------------------------

        pathogen_total = len(pathogen_series)

        unique_pathogens = (
            pathogen_series
            .nunique()
        )

        total_records = len(df)

        if total_records > 0:
            pathogen_coverage = (
                pathogen_total
                / total_records
                * 100
            )
        else:
            pathogen_coverage = 0

        pathogen_kpi = st.columns(3)

        with pathogen_kpi[0]:
            st.metric(
                "Records with Pathogen",
                f"{pathogen_total:,}",
            )

        with pathogen_kpi[1]:
            st.metric(
                "Unique Pathogens",
                f"{unique_pathogens:,}",
            )

        with pathogen_kpi[2]:
            st.metric(
                "Pathogen Data Coverage",
                f"{pathogen_coverage:.1f}%",
            )

        # -------------------------------------------------
        # Top Pathogens
        # -------------------------------------------------

        st.markdown(
            "#### Top Pathogens by Recorded Cases"
        )

        pathogen_counts = (
            pathogen_series
            .value_counts()
            .head(15)
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

        # -------------------------------------------------
        # Pathogen-wise Monthly Trend
        # -------------------------------------------------

        if "Month" in df.columns:

            st.markdown(
                "#### Pathogen-wise Monthly Trend"
            )

            pathogen_month_df = df[
                ["Month", pathogen_column]
            ].copy()

            pathogen_month_df["Month"] = (
                pathogen_month_df["Month"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_month_df[
                pathogen_column
            ] = (
                pathogen_month_df[
                    pathogen_column
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_month_df = (
                pathogen_month_df[
                    pathogen_month_df["Month"].ne("")
                    & pathogen_month_df[
                        pathogen_column
                    ].ne("")
                    & pathogen_month_df[
                        pathogen_column
                    ].str.lower().ne("nan")
                ]
            )

            if not pathogen_month_df.empty:

                pathogen_month_crosstab = pd.crosstab(
                    pathogen_month_df["Month"],
                    pathogen_month_df[
                        pathogen_column
                    ],
                )

                ordered_months = _month_order(df)

                available_months = [
                    month
                    for month in ordered_months
                    if month
                    in pathogen_month_crosstab.index
                ]

                remaining_months = [
                    month
                    for month
                    in pathogen_month_crosstab.index
                    if month
                    not in available_months
                ]

                pathogen_month_crosstab = (
                    pathogen_month_crosstab.reindex(
                        available_months
                        + remaining_months
                    )
                )

                top_pathogens = (
                    pathogen_month_crosstab
                    .sum()
                    .sort_values(
                        ascending=False
                    )
                    .head(10)
                    .index
                    .tolist()
                )

                if top_pathogens:

                    pathogen_month_chart = (
                        pathogen_month_crosstab[
                            top_pathogens
                        ]
                    )

                    render_line_chart(
                        pathogen_month_chart,
                        use_container_width=True,
                    )

                    st.caption(
                        "Monthly trend displays the top 10 "
                        "pathogens by total records."
                    )

        # -------------------------------------------------
        # Pathogen-wise Facility Distribution
        # -------------------------------------------------

        if "Facility Name" in df.columns:

            st.markdown(
                "#### Pathogen-wise Facility Distribution"
            )

            pathogen_facility_df = df[
                [
                    pathogen_column,
                    "Facility Name",
                ]
            ].copy()

            pathogen_facility_df[
                pathogen_column
            ] = (
                pathogen_facility_df[
                    pathogen_column
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_facility_df[
                "Facility Name"
            ] = (
                pathogen_facility_df[
                    "Facility Name"
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_facility_df = (
                pathogen_facility_df[
                    pathogen_facility_df[
                        pathogen_column
                    ].ne("")
                    & pathogen_facility_df[
                        pathogen_column
                    ].str.lower().ne("nan")
                    & pathogen_facility_df[
                        "Facility Name"
                    ].ne("")
                    & pathogen_facility_df[
                        "Facility Name"
                    ].str.lower().ne("nan")
                ]
            )

            if not pathogen_facility_df.empty:

                facility_pathogen = pd.crosstab(
                    pathogen_facility_df[
                        "Facility Name"
                    ],
                    pathogen_facility_df[
                        pathogen_column
                    ],
                )

                top_pathogens = (
                    facility_pathogen
                    .sum()
                    .sort_values(
                        ascending=False
                    )
                    .head(10)
                    .index
                    .tolist()
                )

                top_facilities = (
                    facility_pathogen
                    .sum(axis=1)
                    .sort_values(
                        ascending=False
                    )
                    .head(15)
                    .index
                    .tolist()
                )

                facility_pathogen = (
                    facility_pathogen
                    .loc[
                        top_facilities,
                        top_pathogens,
                    ]
                )

                render_line_chart(
                    facility_pathogen,
                    use_container_width=True,
                )

                st.caption(
                    "Distribution of the top 10 pathogens "
                    "across the top 15 facilities."
                )

        # -------------------------------------------------
        # Pathogen-wise Ward Distribution
        # -------------------------------------------------

        if "Ward Name" in df.columns:

            st.markdown(
                "#### Pathogen-wise Ward Distribution"
            )

            pathogen_ward_df = df[
                [
                    pathogen_column,
                    "Ward Name",
                ]
            ].copy()

            pathogen_ward_df[
                pathogen_column
            ] = (
                pathogen_ward_df[
                    pathogen_column
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_ward_df[
                "Ward Name"
            ] = (
                pathogen_ward_df[
                    "Ward Name"
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_ward_df = (
                pathogen_ward_df[
                    pathogen_ward_df[
                        pathogen_column
                    ].ne("")
                    & pathogen_ward_df[
                        pathogen_column
                    ].str.lower().ne("nan")
                    & pathogen_ward_df[
                        "Ward Name"
                    ].ne("")
                    & pathogen_ward_df[
                        "Ward Name"
                    ].str.lower().ne("nan")
                ]
            )

            if not pathogen_ward_df.empty:

                ward_pathogen = pd.crosstab(
                    pathogen_ward_df[
                        "Ward Name"
                    ],
                    pathogen_ward_df[
                        pathogen_column
                    ],
                )

                top_pathogens = (
                    ward_pathogen
                    .sum()
                    .sort_values(
                        ascending=False
                    )
                    .head(10)
                    .index
                    .tolist()
                )

                top_wards = (
                    ward_pathogen
                    .sum(axis=1)
                    .sort_values(
                        ascending=False
                    )
                    .head(20)
                    .index
                    .tolist()
                )

                ward_pathogen = (
                    ward_pathogen
                    .loc[
                        top_wards,
                        top_pathogens,
                    ]
                )

                render_line_chart(
                    ward_pathogen,
                    use_container_width=True,
                )

                st.caption(
                    "Distribution of the top 10 pathogens "
                    "across the top 20 wards."
                )

        # -------------------------------------------------
        # Complete Pathogen Summary
        # -------------------------------------------------

        st.markdown(
            "#### Complete Pathogen Summary"
        )

        complete_pathogen = (
            pathogen_series
            .value_counts()
            .rename_axis(
                "Test Performed Pathogen Name"
            )
            .reset_index(
                name="Records"
            )
        )

        complete_pathogen[
            "Percentage"
        ] = (
            complete_pathogen["Records"]
            / complete_pathogen["Records"].sum()
            * 100
        ).round(1)

        st.dataframe(
            complete_pathogen,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "Test Performed Pathogen Name information "
            "is not available for the selected records."
        )

else:
    st.info(
        "The selected dataset does not contain "
        "'Test Performed Pathogen Name' or 'Pathogen Name'."
    )

# ---------------------------------------------------------
# 8. REPORTING DATE TREND
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

        render_line_chart(
            daily_counts,
            use_container_width=True,
        )

    else:
        st.info(
            "Valid reporting dates are not available."
        )

# ---------------------------------------------------------
# 9. SUMMARY
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
            & disease_count.str.lower().ne("nan")
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
            & facility_count.str.lower().ne("nan")
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
            & ward_count.str.lower().ne("nan")
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
```
