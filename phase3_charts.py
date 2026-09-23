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

def _valid_text_mask(series):
text = (
series
.fillna("")
.astype(str)
.str.strip()
)

```
return ~text.str.lower().isin(
    ["", "nan", "nat", "none", "null"]
)
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
    and value.lower() not in {
        "nan",
        "nat",
        "none",
        "null",
    }
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

def sort_key(value):
    text = str(value).strip().lower()

    if text in month_map:
        return (0, month_map[text], text)

    try:
        return (1, int(float(text)), text)
    except Exception:
        return (2, 999, text)

return sorted(
    months,
    key=sort_key,
)
```

def render_charts(df):

```
st.subheader("Charts & Trends")

if df is None or df.empty:
    st.warning(
        "No records available for the selected filters."
    )
    return

st.caption(
    "Month-wise, disease-wise, facility-wise, ward-wise "
    "and pathogen-wise analysis based on the selected "
    "Global Dashboard Filters."
)

# ========================================================
# 1. MONTH-WISE PROGRAMME TREND
# ========================================================

st.markdown("### Month-wise Programme Trend")

if "Month" in df.columns:

    month_series = _clean_series(
        df,
        "Month",
    )

    month_series = month_series[
        _valid_text_mask(month_series)
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

            order_map = {
                month: index
                for index, month
                in enumerate(ordered_months)
            }

            month_counts["sort_order"] = (
                month_counts["Month"]
                .map(order_map)
                .fillna(999)
            )

            month_counts = (
                month_counts
                .sort_values(
                    ["sort_order", "Month"]
                )
                .drop(
                    columns=["sort_order"]
                )
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
            "Month information is not available "
            "for the selected records."
        )

# ========================================================
# 2. MONTHLY DISEASE COMPARISON
# ========================================================

st.divider()

st.markdown("### Monthly Disease Comparison")

if "Month" in df.columns and "Disease" in df.columns:

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
        _valid_text_mask(temp["Month"])
        & _valid_text_mask(temp["Disease"])
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
            cross_tab
            .sum()
            .sort_values(ascending=False)
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
            "Chart displays the top 10 diseases by "
            "total records within the selected filters."
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

st.markdown("### Disease-wise Burden")

if "Disease" in df.columns:

    disease_series = _clean_series(
        df,
        "Disease",
    )

    disease_series = disease_series[
        _valid_text_mask(disease_series)
    ]

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

# ========================================================
# 4. FACILITY-WISE BURDEN
# ========================================================

st.divider()

st.markdown("### Facility-wise Burden")

if "Facility Name" in df.columns:

    facility_series = _clean_series(
        df,
        "Facility Name",
    )

    facility_series = facility_series[
        _valid_text_mask(facility_series)
    ]

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

# ========================================================
# 5. WARD-WISE BURDEN
# ========================================================

st.divider()

st.markdown("### Ward-wise Burden")

if "Ward Name" in df.columns:

    ward_series = _clean_series(
        df,
        "Ward Name",
    )

    ward_series = ward_series[
        _valid_text_mask(ward_series)
    ]

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

# ========================================================
# 6. OPD / IPD DISTRIBUTION
# ========================================================

st.divider()

st.markdown("### OPD / IPD Distribution")

if "OPD/IPD" in df.columns:

    opd_series = _clean_series(
        df,
        "OPD/IPD",
    )

    opd_series = opd_series[
        _valid_text_mask(opd_series)
    ]

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

# ========================================================
# 7. REPORTING DATE TREND
# ========================================================

st.divider()

st.markdown("### Reporting Date Trend")

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

# ========================================================
# 8. TREND SUMMARY
# ========================================================

st.divider()

st.markdown("### Trend Summary")

summary_columns = st.columns(4)

with summary_columns[0]:

    st.metric(
        "Records Analysed",
        f"{len(df):,}",
    )

with summary_columns[1]:

    if "Disease" in df.columns:

        disease_count = _clean_series(
            df,
            "Disease",
        )

        disease_count = disease_count[
            _valid_text_mask(disease_count)
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

        facility_count = _clean_series(
            df,
            "Facility Name",
        )

        facility_count = facility_count[
            _valid_text_mask(facility_count)
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

        ward_count = _clean_series(
            df,
            "Ward Name",
        )

        ward_count = ward_count[
            _valid_text_mask(ward_count)
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

# ========================================================
# 9. PATHOGEN-WISE ANALYSIS
# ========================================================

st.divider()

st.markdown(
    "### Test Performed Pathogen-wise Analysis"
)

pathogen_column = "Test Performed Pathogen Name"

if pathogen_column not in df.columns:

    st.info(
        "Pathogen analysis is not available because "
        "'Test Performed Pathogen Name' is not present "
        "in the dataset."
    )

else:

    pathogen_series = _clean_series(
        df,
        pathogen_column,
    )

    pathogen_series = pathogen_series[
        _valid_text_mask(pathogen_series)
    ]

    if pathogen_series.empty:

        st.info(
            "No pathogen records are available "
            "for the selected filters."
        )

    else:

        st.markdown(
            "#### Overall Pathogen Burden"
        )

        pathogen_counts = (
            pathogen_series
            .value_counts()
            .rename_axis("Pathogen")
            .reset_index(name="Records")
        )

        total_pathogen_records = int(
            pathogen_counts["Records"].sum()
        )

        pathogen_counts["Share %"] = (
            pathogen_counts["Records"]
            / total_pathogen_records
            * 100
        ).round(2)

        pathogen_metrics = st.columns(3)

        with pathogen_metrics[0]:

            st.metric(
                "Unique Pathogens",
                f"{pathogen_counts['Pathogen'].nunique():,}",
            )

        with pathogen_metrics[1]:

            st.metric(
                "Records with Pathogen",
                f"{total_pathogen_records:,}",
            )

        with pathogen_metrics[2]:

            coverage = (
                total_pathogen_records
                / len(df)
                * 100
                if len(df) > 0
                else 0
            )

            st.metric(
                "Pathogen Data Coverage",
                f"{coverage:.2f}%",
            )

        st.markdown(
            "#### Top Pathogens"
        )

        top_pathogens = (
            pathogen_counts
            .head(15)
            .copy()
        )

        render_bar_chart(
            top_pathogens.set_index(
                "Pathogen"
            )["Records"],
            use_container_width=True,
        )

        st.dataframe(
            pathogen_counts,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown(
            "#### Pathogen-wise Monthly Trend"
        )

        if "Month" in df.columns:

            pathogen_month = df[
                [
                    pathogen_column,
                    "Month",
                ]
            ].copy()

            pathogen_month[
                pathogen_column
            ] = (
                pathogen_month[
                    pathogen_column
                ]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_month["Month"] = (
                pathogen_month["Month"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_month = pathogen_month[
                _valid_text_mask(
                    pathogen_month[pathogen_column]
                )
                & _valid_text_mask(
                    pathogen_month["Month"]
                )
            ]

            if not pathogen_month.empty:

                top_10_pathogens = (
                    pathogen_month[
                        pathogen_column
                    ]
                    .value_counts()
                    .head(10)
                    .index
                    .tolist()
                )

                pathogen_month = pathogen_month[
                    pathogen_month[
                        pathogen_column
                    ].isin(top_10_pathogens)
                ]

                monthly_pathogen = pd.crosstab(
                    pathogen_month["Month"],
                    pathogen_month[
                        pathogen_column
                    ],
                )

                ordered_months = _month_order(
                    pathogen_month
                )

                available_months = [
                    month
                    for month in ordered_months
                    if month in monthly_pathogen.index
                ]

                remaining_months = [
                    month
                    for month in monthly_pathogen.index
                    if month not in available_months
                ]

                monthly_pathogen = (
                    monthly_pathogen
                    .reindex(
                        available_months
                        + remaining_months
                    )
                )

                render_line_chart(
                    monthly_pathogen,
                    use_container_width=True,
                )

                st.dataframe(
                    monthly_pathogen,
                    use_container_width=True,
                )

            else:

                st.info(
                    "Month information is not available "
                    "for pathogen analysis."
                )

        else:

            st.info(
                "Month column is not available "
                "for pathogen monthly analysis."
            )

        st.markdown(
            "#### Pathogen-wise Ward Distribution"
        )

        ward_column = "Ward Name"

        if ward_column in df.columns:

            pathogen_ward = df[
                [
                    ward_column,
                    pathogen_column,
                ]
            ].copy()

            pathogen_ward[ward_column] = (
                pathogen_ward[ward_column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_ward[pathogen_column] = (
                pathogen_ward[pathogen_column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_ward = pathogen_ward[
                _valid_text_mask(
                    pathogen_ward[ward_column]
                )
                & _valid_text_mask(
                    pathogen_ward[pathogen_column]
                )
            ]

            if not pathogen_ward.empty:

                top_wards = (
                    pathogen_ward[ward_column]
                    .value_counts()
                    .head(15)
                    .index
                    .tolist()
                )

                pathogen_ward = pathogen_ward[
                    pathogen_ward[ward_column].isin(
                        top_wards
                    )
                ]

                ward_pathogen_table = pd.crosstab(
                    pathogen_ward[ward_column],
                    pathogen_ward[pathogen_column],
                )

                ward_totals = (
                    ward_pathogen_table
                    .sum(axis=1)
                    .sort_values(
                        ascending=False
                    )
                )

                render_bar_chart(
                    ward_totals,
                    use_container_width=True,
                )

                st.dataframe(
                    ward_pathogen_table,
                    use_container_width=True,
                )

            else:

                st.info(
                    "Ward information is not available "
                    "for pathogen analysis."
                )

        else:

            st.info(
                "'Ward Name' column is not available "
                "for pathogen analysis."
            )

        st.markdown(
            "#### Pathogen-wise Facility Distribution"
        )

        facility_column = "Facility Name"

        if facility_column in df.columns:

            pathogen_facility = df[
                [
                    facility_column,
                    pathogen_column,
                ]
            ].copy()

            pathogen_facility[facility_column] = (
                pathogen_facility[facility_column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_facility[pathogen_column] = (
                pathogen_facility[pathogen_column]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            pathogen_facility = pathogen_facility[
                _valid_text_mask(
                    pathogen_facility[facility_column]
                )
                & _valid_text_mask(
                    pathogen_facility[pathogen_column]
                )
            ]

            if not pathogen_facility.empty:

                top_facilities = (
                    pathogen_facility[
                        facility_column
                    ]
                    .value_counts()
                    .head(15)
                    .index
                    .tolist()
                )

                pathogen_facility = pathogen_facility[
                    pathogen_facility[
                        facility_column
                    ].isin(top_facilities)
                ]

                facility_pathogen_table = pd.crosstab(
                    pathogen_facility[
                        facility_column
                    ],
                    pathogen_facility[
                        pathogen_column
                    ],
                )

                facility_totals = (
                    facility_pathogen_table
                    .sum(axis=1)
                    .sort_values(
                        ascending=False
                    )
                )

                render_bar_chart(
                    facility_totals,
                    use_container_width=True,
                )

                st.dataframe(
                    facility_pathogen_table,
                    use_container_width=True,
                )

            else:

                st.info(
                    "Facility information is not available "
                    "for pathogen analysis."
                )

        else:

            st.info(
                "'Facility Name' column is not available "
                "for pathogen analysis."
            )

        st.markdown(
            "#### Complete Pathogen Summary"
        )

        st.dataframe(
            pathogen_counts,
            use_container_width=True,
            hide_index=True,
        )
```
