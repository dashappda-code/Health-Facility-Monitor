import streamlit as st
import pandas as pd
import plotly.express as px

# ============================================================

# HELPER FUNCTIONS

# ============================================================

def _clean_text(series):
if series is None:
return pd.Series(dtype="object")

```
return (
    series
    .fillna("")
    .astype(str)
    .str.strip()
)
```

def _valid_text(series):
text = _clean_text(series)

```
return ~text.str.lower().isin(
    [
        "",
        "nan",
        "nat",
        "none",
        "null",
        "na",
        "n/a",
    ]
)
```

def _get_column(df, candidates):
"""
Return the first available column from a list of candidates.
This keeps the dashboard compatible with both raw and
normalized column names.
"""

```
if df is None or df.empty:
    return None

for column in candidates:
    if column in df.columns:
        return column

return None
```

def _count_table(df, column, name="Cases", top_n=None):
"""
Create a clean frequency table.
"""

```
if (
    df is None
    or df.empty
    or column is None
    or column not in df.columns
):
    return pd.DataFrame()

series = _clean_text(df[column])

series = series[
    _valid_text(series)
]

if series.empty:
    return pd.DataFrame()

table = (
    series
    .value_counts()
    .rename_axis("Category")
    .reset_index(name=name)
)

if top_n is not None:
    table = table.head(top_n)

return table
```

def _month_sort_key(value):
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

```
text = str(value).strip().lower()

if text in month_map:
    return (0, month_map[text], text)

try:
    return (1, int(float(text)), text)
except Exception:
    return (2, 999, text)
```

def _ordered_months(df):
if (
df is None
or df.empty
or "Month" not in df.columns
):
return []

```
months = _clean_text(
    df["Month"]
)

months = months[
    _valid_text(months)
]

if months.empty:
    return []

return sorted(
    months.unique().tolist(),
    key=_month_sort_key,
)
```

def _safe_chart(fig, height=450):
"""
Apply a simple, stable Plotly layout.
"""

```
fig.update_layout(
    height=height,
    margin=dict(
        l=20,
        r=20,
        t=60,
        b=40,
    ),
    legend_title_text="",
)

return fig
```

def _show_bar(
table,
category_column="Category",
value_column="Cases",
title="",
height=450,
horizontal=False,
):
if table is None or table.empty:
return

```
chart_table = table.copy()

if horizontal:
    chart_table = chart_table.sort_values(
        value_column,
        ascending=True,
    )

    fig = px.bar(
        chart_table,
        x=value_column,
        y=category_column,
        orientation="h",
        text=value_column,
        title=title,
    )
else:
    fig = px.bar(
        chart_table,
        x=category_column,
        y=value_column,
        text=value_column,
        title=title,
    )

fig.update_traces(
    textposition="outside"
)

st.plotly_chart(
    _safe_chart(
        fig,
        height,
    ),
    use_container_width=True,
)
```

# ============================================================

# MAIN CHART FUNCTION

# ============================================================

def render_charts(df):

```
st.subheader("📈 Charts & Trends")

if df is None or df.empty:
    st.warning(
        "No records available for the selected filters."
    )
    return

st.caption(
    "Detailed programme analysis based on the currently "
    "selected Global Dashboard Filters."
)

# ========================================================
# COLUMN MAPPING
# ========================================================

disease_column = _get_column(
    df,
    [
        "Disease",
        "Confirmed Diagnosis",
    ],
)

facility_column = _get_column(
    df,
    [
        "Facility Name",
        "Facility Name Lform",
    ],
)

ward_column = _get_column(
    df,
    [
        "Ward Name",
        "Ward",
        "Zone/Administrative Ward Name",
    ],
)

gender_column = _get_column(
    df,
    [
        "Gender",
    ],
)

age_column = _get_column(
    df,
    [
        "Age",
    ],
)

age_group_column = _get_column(
    df,
    [
        "Age Group",
    ],
)

opd_column = _get_column(
    df,
    [
        "OPD/IPD",
        "Opd Ipd",
    ],
)

pathogen_column = _get_column(
    df,
    [
        "Test Performed Pathogen Name",
        "Pathogen Name",
    ],
)

test_column = _get_column(
    df,
    [
        "Test Performed",
    ],
)

# ========================================================
# 1. MONTH-WISE PROGRAMME TREND
# ========================================================

st.markdown(
    "### 🗓️ Month-wise Programme Trend"
)

if "Month" in df.columns:

    month_table = _count_table(
        df,
        "Month",
        name="Records",
    )

    if not month_table.empty:

        ordered_months = _ordered_months(df)

        if ordered_months:

            month_order_map = {
                month: index
                for index, month
                in enumerate(
                    ordered_months
                )
            }

            month_table[
                "_sort"
            ] = (
                month_table["Category"]
                .map(
                    month_order_map
                )
                .fillna(999)
            )

            month_table = (
                month_table
                .sort_values(
                    "_sort"
                )
                .drop(
                    columns=["_sort"]
                )
                .reset_index(
                    drop=True
                )
            )

        month_table = month_table.rename(
            columns={
                "Category": "Month"
            }
        )

        _show_bar(
            month_table,
            category_column="Month",
            value_column="Records",
            title="Monthly Programme Record Volume",
            height=430,
        )

        st.dataframe(
            month_table,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "Month information is not available."
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
    and disease_column is not None
):

    temp = df[
        [
            "Month",
            disease_column,
        ]
    ].copy()

    temp["Month"] = _clean_text(
        temp["Month"]
    )

    temp[disease_column] = _clean_text(
        temp[disease_column]
    )

    temp = temp[
        _valid_text(temp["Month"])
        & _valid_text(
            temp[disease_column]
        )
    ]

    if not temp.empty:

        disease_month = pd.crosstab(
            temp["Month"],
            temp[disease_column],
        )

        disease_totals = (
            disease_month
            .sum(axis=0)
            .sort_values(
                ascending=False
            )
        )

        top_diseases = (
            disease_totals
            .head(10)
            .index
            .tolist()
        )

        disease_month = (
            disease_month[
                top_diseases
            ]
        )

        ordered_months = _ordered_months(
            temp
        )

        available_months = [
            month
            for month in ordered_months
            if month in disease_month.index
        ]

        remaining_months = [
            month
            for month in disease_month.index
            if month not in available_months
        ]

        disease_month = disease_month.reindex(
            available_months
            + remaining_months
        )

        fig = px.line(
            disease_month,
            x=disease_month.index,
            y=disease_month.columns,
            markers=True,
            title=(
                "Monthly Disease Trend — "
                "Top 10 Diseases"
            ),
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Records",
        )

        st.plotly_chart(
            _safe_chart(
                fig,
                500,
            ),
            use_container_width=True,
        )

        st.dataframe(
            disease_month,
            use_container_width=True,
        )

    else:
        st.info(
            "Disease/month information is not available."
        )

# ========================================================
# 3. DISEASE-WISE BURDEN
# ========================================================

st.divider()

st.markdown(
    "### 🦠 Disease-wise Burden"
)

if disease_column is not None:

    disease_table = _count_table(
        df,
        disease_column,
        name="Cases",
        top_n=15,
    )

    if not disease_table.empty:

        disease_table = disease_table.rename(
            columns={
                "Category": "Disease"
            }
        )

        _show_bar(
            disease_table,
            category_column="Disease",
            value_column="Cases",
            title="Top 15 Diseases by Reported Records",
            height=600,
            horizontal=True,
        )

        st.dataframe(
            disease_table,
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

if facility_column is not None:

    facility_table = _count_table(
        df,
        facility_column,
        name="Cases",
        top_n=20,
    )

    if not facility_table.empty:

        facility_table = facility_table.rename(
            columns={
                "Category": "Facility"
            }
        )

        _show_bar(
            facility_table,
            category_column="Facility",
            value_column="Cases",
            title="Top 20 Facilities by Reported Records",
            height=650,
            horizontal=True,
        )

        st.dataframe(
            facility_table,
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

if ward_column is not None:

    ward_table = _count_table(
        df,
        ward_column,
        name="Cases",
        top_n=20,
    )

    if not ward_table.empty:

        ward_table = ward_table.rename(
            columns={
                "Category": "Ward"
            }
        )

        _show_bar(
            ward_table,
            category_column="Ward",
            value_column="Cases",
            title="Top 20 Wards by Reported Records",
            height=600,
            horizontal=True,
        )

        st.dataframe(
            ward_table,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "Ward information is not available."
        )

# ========================================================
# 6. GENDER-WISE ANALYSIS
# ========================================================

st.divider()

st.markdown(
    "### 👥 Gender-wise Distribution"
)

if gender_column is not None:

    gender_table = _count_table(
        df,
        gender_column,
        name="Cases",
    )

    if not gender_table.empty:

        gender_table = gender_table.rename(
            columns={
                "Category": "Gender"
            }
        )

        _show_bar(
            gender_table,
            category_column="Gender",
            value_column="Cases",
            title="Reported Records by Gender",
            height=420,
        )

        st.dataframe(
            gender_table,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "Gender information is not available."
        )

# ========================================================
# 7. AGE-WISE ANALYSIS
# ========================================================

st.divider()

st.markdown(
    "### 👶 Age-wise Distribution"
)

if age_group_column is not None:

    age_group_table = _count_table(
        df,
        age_group_column,
        name="Cases",
    )

    if not age_group_table.empty:

        age_group_order = [
            "0-4",
            "5-14",
            "15-24",
            "25-44",
            "45-64",
            "65+",
        ]

        age_group_table = age_group_table.rename(
            columns={
                "Category": "Age Group"
            }
        )

        age_group_table[
            "_sort"
        ] = (
            age_group_table["Age Group"]
            .map(
                {
                    value: index
                    for index, value
                    in enumerate(
                        age_group_order
                    )
                }
            )
            .fillna(999)
        )

        age_group_table = (
            age_group_table
            .sort_values(
                "_sort"
            )
            .drop(
                columns=["_sort"]
            )
            .reset_index(
                drop=True
            )
        )

        _show_bar(
            age_group_table,
            category_column="Age Group",
            value_column="Cases",
            title="Reported Records by Age Group",
            height=450,
        )

        st.dataframe(
            age_group_table,
            use_container_width=True,
            hide_index=True,
        )

elif age_column is not None:

    age_series = pd.to_numeric(
        df[age_column],
        errors="coerce",
    ).dropna()

    if not age_series.empty:

        age_table = (
            age_series
            .astype(int)
            .value_counts()
            .sort_index()
            .rename_axis("Age")
            .reset_index(
                name="Cases"
            )
        )

        fig = px.bar(
            age_table,
            x="Age",
            y="Cases",
            title="Age-wise Reported Records",
        )

        st.plotly_chart(
            _safe_chart(
                fig,
                450,
            ),
            use_container_width=True,
        )

        st.dataframe(
            age_table,
            use_container_width=True,
            hide_index=True,
        )

else:
    st.info(
        "Age information is not available."
    )

# ========================================================
# 8. OPD / IPD DISTRIBUTION
# ========================================================

st.divider()

st.markdown(
    "### 🏨 OPD / IPD Distribution"
)

if opd_column is not None:

    opd_table = _count_table(
        df,
        opd_column,
        name="Cases",
    )

    if not opd_table.empty:

        opd_table = opd_table.rename(
            columns={
                "Category": "OPD/IPD"
            }
        )

        _show_bar(
            opd_table,
            category_column="OPD/IPD",
            value_column="Cases",
            title="OPD / IPD Distribution",
            height=420,
        )

        st.dataframe(
            opd_table,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "OPD/IPD information is not available."
        )

# ========================================================
# 9. TEST PERFORMED ANALYSIS
# ========================================================

st.divider()

st.markdown(
    "### 🧪 Test Performed Analysis"
)

if test_column is not None:

    test_table = _count_table(
        df,
        test_column,
        name="Records",
        top_n=20,
    )

    if not test_table.empty:

        test_table = test_table.rename(
            columns={
                "Category": "Test Performed"
            }
        )

        _show_bar(
            test_table,
            category_column="Test Performed",
            value_column="Records",
            title="Top Tests Performed",
            height=600,
            horizontal=True,
        )

        st.dataframe(
            test_table,
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info(
            "Test performed information is not available."
        )

# ========================================================
# 10. PATHOGEN-WISE ANALYSIS
# ========================================================

st.divider()

st.markdown(
    "### 🧫 Test Performed Pathogen-wise Analysis"
)

if pathogen_column is None:

    st.info(
        "Pathogen analysis is not available because "
        "the pathogen column is not present in the dataset."
    )

else:

    pathogen_series = _clean_text(
        df[pathogen_column]
    )

    pathogen_series = pathogen_series[
        _valid_text(
            pathogen_series
        )
    ]

    if pathogen_series.empty:

        st.info(
            "No pathogen records are available "
            "for the selected filters."
        )

    else:

        # ------------------------------------------------
        # 10A. PATHOGEN KPI
        # ------------------------------------------------

        pathogen_table = (
            pathogen_series
            .value_counts()
            .rename_axis("Pathogen")
            .reset_index(
                name="Records"
            )
        )

        total_pathogen_records = int(
            pathogen_table["Records"].sum()
        )

        unique_pathogens = int(
            pathogen_table[
                "Pathogen"
            ].nunique()
        )

        coverage = (
            total_pathogen_records
            / len(df)
            * 100
            if len(df) > 0
            else 0
        )

        pathogen_kpis = st.columns(3)

        with pathogen_kpis[0]:

            st.metric(
                "Unique Pathogens",
                f"{unique_pathogens:,}",
            )

        with pathogen_kpis[1]:

            st.metric(
                "Records with Pathogen",
                f"{total_pathogen_records:,}",
            )

        with pathogen_kpis[2]:

            st.metric(
                "Pathogen Data Coverage",
                f"{coverage:.2f}%",
            )

        # ------------------------------------------------
        # 10B. TOP PATHOGENS
        # ------------------------------------------------

        st.markdown(
            "#### Top Pathogens"
        )

        top_pathogens = (
            pathogen_table
            .head(15)
            .copy()
        )

        top_pathogens["Share %"] = (
            top_pathogens["Records"]
            / total_pathogen_records
            * 100
        ).round(2)

        _show_bar(
            top_pathogens,
            category_column="Pathogen",
            value_column="Records",
            title=(
                "Top 15 Pathogens by "
                "Reported Records"
            ),
            height=600,
            horizontal=True,
        )

        st.dataframe(
            top_pathogens,
            use_container_width=True,
            hide_index=True,
        )

        # ------------------------------------------------
        # 10C. PATHOGEN MONTHLY TREND
        # ------------------------------------------------

        st.markdown(
            "#### Pathogen-wise Monthly Trend"
        )

        if "Month" in df.columns:

            pathogen_month = df[
                [
                    "Month",
                    pathogen_column,
                ]
            ].copy()

            pathogen_month[
                "Month"
            ] = _clean_text(
                pathogen_month["Month"]
            )

            pathogen_month[
                pathogen_column
            ] = _clean_text(
                pathogen_month[
                    pathogen_column
                ]
            )

            pathogen_month = pathogen_month[
                _valid_text(
                    pathogen_month["Month"]
                )
                & _valid_text(
                    pathogen_month[
                        pathogen_column
                    ]
                )
            ]

            if not pathogen_month.empty:

                top_10 = (
                    pathogen_month[
                        pathogen_column
                    ]
                    .value_counts()
                    .head(10)
                    .index
                    .tolist()
                )

                pathogen_month = (
                    pathogen_month[
                        pathogen_month[
                            pathogen_column
                        ].isin(
                            top_10
                        )
                    ]
                )

                monthly_pathogen = pd.crosstab(
                    pathogen_month["Month"],
                    pathogen_month[
                        pathogen_column
                    ],
                )

                ordered_months = _ordered_months(
                    pathogen_month
                )

                available_months = [
                    month
                    for month in ordered_months
                    if month
                    in monthly_pathogen.index
                ]

                remaining_months = [
                    month
                    for month in monthly_pathogen.index
                    if month
                    not in available_months
                ]

                monthly_pathogen = (
                    monthly_pathogen
                    .reindex(
                        available_months
                        + remaining_months
                    )
                )

                fig = px.line(
                    monthly_pathogen,
                    x=monthly_pathogen.index,
                    y=monthly_pathogen.columns,
                    markers=True,
                    title=(
                        "Monthly Pathogen Trend — "
                        "Top 10 Pathogens"
                    ),
                )

                fig.update_layout(
                    xaxis_title="Month",
                    yaxis_title="Records",
                )

                st.plotly_chart(
                    _safe_chart(
                        fig,
                        500,
                    ),
                    use_container_width=True,
                )

                st.dataframe(
                    monthly_pathogen,
                    use_container_width=True,
                )

            else:

                st.info(
                    "No valid month/pathogen combination "
                    "is available."
                )

        # ------------------------------------------------
        # 10D. PATHOGEN-WISE WARD DISTRIBUTION
        # ------------------------------------------------

        st.markdown(
            "#### Pathogen-wise Ward Distribution"
        )

        if ward_column is not None:

            pathogen_ward = df[
                [
                    ward_column,
                    pathogen_column,
                ]
            ].copy()

            pathogen_ward[
                ward_column
            ] = _clean_text(
                pathogen_ward[
                    ward_column
                ]
            )

            pathogen_ward[
                pathogen_column
            ] = _clean_text(
                pathogen_ward[
                    pathogen_column
                ]
            )

            pathogen_ward = pathogen_ward[
                _valid_text(
                    pathogen_ward[
                        ward_column
                    ]
                )
                & _valid_text(
                    pathogen_ward[
                        pathogen_column
                    ]
                )
            ]

            if not pathogen_ward.empty:

                ward_pathogen = pd.crosstab(
                    pathogen_ward[
                        ward_column
                    ],
                    pathogen_ward[
                        pathogen_column
                    ],
                )

                ward_totals = (
                    ward_pathogen
                    .sum(axis=1)
                    .sort_values(
                        ascending=False
                    )
                    .head(15)
                )

                ward_totals_df = (
                    ward_totals
                    .rename(
                        "Cases"
                    )
                    .rename_axis(
                        "Ward"
                    )
                    .reset_index()
                )

                _show_bar(
                    ward_totals_df,
                    category_column="Ward",
                    value_column="Cases",
                    title=(
                        "Top 15 Wards with "
                        "Pathogen Records"
                    ),
                    height=550,
                    horizontal=True,
                )

                selected_wards = (
                    ward_totals.index
                )

                ward_pathogen = (
                    ward_pathogen
                    .loc[
                        selected_wards
                    ]
                )

                st.dataframe(
                    ward_pathogen,
                    use_container_width=True,
                )

            else:

                st.info(
                    "Ward/pathogen information is not available."
                )

        else:

            st.info(
                "Ward information is not available."
            )

        # ------------------------------------------------
        # 10E. PATHOGEN-WISE FACILITY DISTRIBUTION
        # ------------------------------------------------

        st.markdown(
            "#### Pathogen-wise Facility Distribution"
        )

        if facility_column is not None:

            pathogen_facility = df[
                [
                    facility_column,
                    pathogen_column,
                ]
            ].copy()

            pathogen_facility[
                facility_column
            ] = _clean_text(
                pathogen_facility[
                    facility_column
                ]
            )

            pathogen_facility[
                pathogen_column
            ] = _clean_text(
                pathogen_facility[
                    pathogen_column
                ]
            )

            pathogen_facility = (
                pathogen_facility[
                    _valid_text(
                        pathogen_facility[
                            facility_column
                        ]
                    )
                    & _valid_text(
                        pathogen_facility[
                            pathogen_column
                        ]
                    )
                ]
            )

            if not pathogen_facility.empty:

                facility_pathogen = pd.crosstab(
                    pathogen_facility[
                        facility_column
                    ],
                    pathogen_facility[
                        pathogen_column
                    ],
                )

                facility_totals = (
                    facility_pathogen
                    .sum(axis=1)
                    .sort_values(
                        ascending=False
                    )
                    .head(15)
                )

                facility_totals_df = (
                    facility_totals
                    .rename(
                        "Cases"
                    )
                    .rename_axis(
                        "Facility"
                    )
                    .reset_index()
                )

                _show_bar(
                    facility_totals_df,
                    category_column="Facility",
                    value_column="Cases",
                    title=(
                        "Top 15 Facilities with "
                        "Pathogen Records"
                    ),
                    height=600,
                    horizontal=True,
                )

                selected_facilities = (
                    facility_totals.index
                )

                facility_pathogen = (
                    facility_pathogen
                    .loc[
                        selected_facilities
                    ]
                )

                st.dataframe(
                    facility_pathogen,
                    use_container_width=True,
                )

            else:

                st.info(
                    "Facility/pathogen information "
                    "is not available."
                )

        else:

            st.info(
                "Facility information is not available."
            )

        # ------------------------------------------------
        # 10F. COMPLETE PATHOGEN SUMMARY
        # ------------------------------------------------

        st.markdown(
            "#### Complete Pathogen Summary"
        )

        pathogen_table["Share %"] = (
            pathogen_table["Records"]
            / total_pathogen_records
            * 100
        ).round(2)

        st.dataframe(
            pathogen_table,
            use_container_width=True,
            hide_index=True,
        )

# ========================================================
# 11. REPORTING DATE TREND
# ========================================================

st.divider()

st.markdown(
    "### 📅 Reporting Date Trend"
)

if "Reporting Date" in df.columns:

    date_series = pd.to_datetime(
        df["Reporting Date"],
        errors="coerce",
    )

    date_series = date_series.dropna()

    if not date_series.empty:

        daily = (
            date_series
            .dt.normalize()
            .value_counts()
            .sort_index()
            .rename_axis("Date")
            .reset_index(
                name="Records"
            )
        )

        fig = px.line(
            daily,
            x="Date",
            y="Records",
            markers=True,
            title="Reporting Volume by Date",
        )

        st.plotly_chart(
            _safe_chart(
                fig,
                450,
            ),
            use_container_width=True,
        )

    else:
        st.info(
            "Valid reporting dates are not available."
        )

# ========================================================
# 12. OVERALL TREND SUMMARY
# ========================================================

st.divider()

st.markdown(
    "### 📌 Trend Summary"
)

summary = st.columns(5)

with summary[0]:

    st.metric(
        "Records Analysed",
        f"{len(df):,}",
    )

with summary[1]:

    if disease_column is not None:

        values = _clean_text(
            df[disease_column]
        )

        values = values[
            _valid_text(values)
        ]

        st.metric(
            "Diseases",
            f"{values.nunique():,}",
        )

    else:

        st.metric(
            "Diseases",
            "0",
        )

with summary[2]:

    if facility_column is not None:

        values = _clean_text(
            df[facility_column]
        )

        values = values[
            _valid_text(values)
        ]

        st.metric(
            "Facilities",
            f"{values.nunique():,}",
        )

    else:

        st.metric(
            "Facilities",
            "0",
        )

with summary[3]:

    if ward_column is not None:

        values = _clean_text(
            df[ward_column]
        )

        values = values[
            _valid_text(values)
        ]

        st.metric(
            "Wards",
            f"{values.nunique():,}",
        )

    else:

        st.metric(
            "Wards",
            "0",
        )

with summary[4]:

    if pathogen_column is not None:

        values = _clean_text(
            df[pathogen_column]
        )

        values = values[
            _valid_text(values)
        ]

        st.metric(
            "Pathogens",
            f"{values.nunique():,}",
        )

    else:

        st.metric(
            "Pathogens",
            "0",
        )
```
