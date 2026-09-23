import streamlit as st
import pandas as pd

from chart_helpers import (
render_bar_chart,
render_line_chart,
render_pie_chart,
)

# ============================================================

# HELPER FUNCTIONS

# ============================================================

def _clean_series(series):
"""Convert a pandas series to clean displayable text."""
if series is None:
return pd.Series(dtype="object")

```
return (
    series.astype("string")
    .fillna("")
    .str.strip()
    .replace({"nan": "", "None": "", "<NA>": ""})
)
```

def _valid_series(series):
"""Return non-empty values only."""
if series is None:
return pd.Series(dtype="object")

```
cleaned = _clean_series(series)
return cleaned[cleaned != ""]
```

def _find_column(df, candidates):
"""Return the first matching column from a list of candidates."""
if df is None or df.empty:
return None

```
for candidate in candidates:
    if candidate in df.columns:
        return candidate

return None
```

def _month_order(df):
"""Create chronological month ordering where possible."""
if df is None or df.empty:
return []

```
month_col = _find_column(
    df,
    ["Month", "month", "Reporting Month"]
)

if month_col is None:
    return []

month_values = _valid_series(df[month_col]).unique().tolist()

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
        return month_map[text]

    try:
        return int(text)
    except Exception:
        return 999

return sorted(month_values, key=sort_key)
```

def _show_no_data(message="No data available for this analysis."):
st.info(message)

# ============================================================

# MAIN CHART RENDERER

# ============================================================

def render_charts(df):
"""
Render programme-level analytical charts.

```
Expected normalized columns may include:
Reporting Date
Year
Month
Week
Week range
Disease
Facility Name
Ward Name
Gender
Age
Age Group
OPD/IPD
Patient Address
Confirmed Diagnosis

Pathogen analysis supports:
Test Performed Pathogen Name
Pathogen Name
"""

if df is None or df.empty:
    _show_no_data()
    return

data = df.copy()

# --------------------------------------------------------
# CLEAN COMMON COLUMNS
# --------------------------------------------------------

for col in data.columns:
    if data[col].dtype == "object" or str(data[col].dtype).startswith("string"):
        data[col] = _clean_series(data[col])

st.markdown("## Programme Analytics")

# ========================================================
# 1. MONTH-WISE PROGRAMME TREND
# ========================================================

st.markdown("### Month-wise Programme Trend")

month_col = _find_column(
    data,
    ["Month", "month", "Reporting Month"]
)

if month_col:
    month_df = (
        data.loc[_valid_series(data[month_col]).index]
        .groupby(month_col)
        .size()
        .reset_index(name="Cases")
    )

    ordered_months = _month_order(data)

    if ordered_months:
        month_df["_order"] = month_df[month_col].map(
            {month: i for i, month in enumerate(ordered_months)}
        )
        month_df = (
            month_df
            .sort_values("_order")
            .drop(columns="_order")
        )

    if not month_df.empty:
        render_line_chart(
            month_df,
            x=month_col,
            y="Cases",
            title="Monthly Programme Trend",
        )
    else:
        _show_no_data()
else:
    _show_no_data("Month column is not available.")

# ========================================================
# 2. MONTHLY DISEASE COMPARISON
# ========================================================

st.markdown("### Monthly Disease Comparison")

disease_col = _find_column(
    data,
    ["Disease", "Confirmed Diagnosis"]
)

if month_col and disease_col:

    temp = data[
        (_clean_series(data[month_col]) != "")
        & (_clean_series(data[disease_col]) != "")
    ].copy()

    if not temp.empty:
        monthly_disease = (
            temp.groupby([month_col, disease_col])
            .size()
            .reset_index(name="Cases")
        )

        if not monthly_disease.empty:
            render_bar_chart(
                monthly_disease,
                x=month_col,
                y="Cases",
                color=disease_col,
                title="Monthly Disease Comparison",
            )
    else:
        _show_no_data()
else:
    _show_no_data(
        "Month or disease information is not available."
    )

# ========================================================
# 3. DISEASE-WISE BURDEN
# ========================================================

st.markdown("### Disease-wise Burden")

if disease_col:

    disease_df = (
        _valid_series(data[disease_col])
        .value_counts()
        .reset_index()
    )

    disease_df.columns = [disease_col, "Cases"]

    if not disease_df.empty:
        render_bar_chart(
            disease_df,
            x=disease_col,
            y="Cases",
            title="Disease-wise Burden",
        )
    else:
        _show_no_data()
else:
    _show_no_data("Disease information is not available.")

# ========================================================
# 4. FACILITY-WISE BURDEN
# ========================================================

st.markdown("### Facility-wise Burden")

facility_col = _find_column(
    data,
    [
        "Facility Name",
        "Facility Name Lform",
        "MSU Unique Code",
    ]
)

if facility_col:

    facility_df = (
        _valid_series(data[facility_col])
        .value_counts()
        .head(20)
        .reset_index()
    )

    facility_df.columns = [facility_col, "Cases"]

    if not facility_df.empty:
        render_bar_chart(
            facility_df,
            x=facility_col,
            y="Cases",
            title="Top Facilities by Reported Cases",
        )
    else:
        _show_no_data()
else:
    _show_no_data("Facility information is not available.")

# ========================================================
# 5. WARD-WISE BURDEN
# ========================================================

st.markdown("### Ward-wise Burden")

ward_col = _find_column(
    data,
    [
        "Ward Name",
        "Ward",
    ]
)

if ward_col:

    ward_df = (
        _valid_series(data[ward_col])
        .value_counts()
        .head(20)
        .reset_index()
    )

    ward_df.columns = [ward_col, "Cases"]

    if not ward_df.empty:
        render_bar_chart(
            ward_df,
            x=ward_col,
            y="Cases",
            title="Top Wards by Reported Cases",
        )
    else:
        _show_no_data()
else:
    _show_no_data("Ward information is not available.")

# ========================================================
# 6. OPD / IPD DISTRIBUTION
# ========================================================

st.markdown("### OPD / IPD Distribution")

opd_col = _find_column(
    data,
    [
        "OPD/IPD",
        "Opd Ipd",
        "OPD IPD",
    ]
)

if opd_col:

    opd_df = (
        _valid_series(data[opd_col])
        .value_counts()
        .reset_index()
    )

    opd_df.columns = [opd_col, "Cases"]

    if not opd_df.empty:
        render_pie_chart(
            opd_df,
            names=opd_col,
            values="Cases",
            title="OPD / IPD Distribution",
        )
    else:
        _show_no_data()
else:
    _show_no_data("OPD/IPD information is not available.")

# ========================================================
# 7. PATHOGEN-WISE ANALYSIS
# ========================================================

st.markdown("## Test Performed Pathogen-wise Analysis")

pathogen_col = _find_column(
    data,
    [
        "Test Performed Pathogen Name",
        "Pathogen Name",
    ]
)

if pathogen_col:

    pathogen_values = _valid_series(data[pathogen_col])

    if not pathogen_values.empty:

        # ------------------------------------------------
        # PATHOGEN SUMMARY METRICS
        # ------------------------------------------------

        total_records = len(data)

        pathogen_records = len(pathogen_values)

        unique_pathogens = pathogen_values.nunique()

        coverage = (
            pathogen_records / total_records * 100
            if total_records > 0
            else 0
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Records with Pathogen",
                f"{pathogen_records:,}",
            )

        with c2:
            st.metric(
                "Unique Pathogens",
                f"{unique_pathogens:,}",
            )

        with c3:
            st.metric(
                "Pathogen Data Coverage",
                f"{coverage:.1f}%",
            )

        # ------------------------------------------------
        # TOP PATHOGENS
        # ------------------------------------------------

        st.markdown("### Top Pathogens by Recorded Cases")

        pathogen_df = (
            pathogen_values
            .value_counts()
            .reset_index()
        )

        pathogen_df.columns = [
            pathogen_col,
            "Cases",
        ]

        if not pathogen_df.empty:

            render_bar_chart(
                pathogen_df.head(20),
                x=pathogen_col,
                y="Cases",
                title="Top Pathogens by Recorded Cases",
            )

        # ------------------------------------------------
        # PATHOGEN MONTHLY TREND
        # ------------------------------------------------

        st.markdown("### Pathogen-wise Monthly Trend")

        if month_col:

            pathogen_month_df = data[
                (_clean_series(data[pathogen_col]) != "")
                & (_clean_series(data[month_col]) != "")
            ].copy()

            if not pathogen_month_df.empty:

                pathogen_month_df = (
                    pathogen_month_df
                    .groupby(
                        [month_col, pathogen_col]
                    )
                    .size()
                    .reset_index(name="Cases")
                )

                render_bar_chart(
                    pathogen_month_df,
                    x=month_col,
                    y="Cases",
                    color=pathogen_col,
                    title="Pathogen-wise Monthly Trend",
                )

            else:
                _show_no_data()

        # ------------------------------------------------
        # PATHOGEN FACILITY DISTRIBUTION
        # ------------------------------------------------

        st.markdown("### Pathogen-wise Facility Distribution")

        if facility_col:

            pathogen_facility_df = data[
                (_clean_series(data[pathogen_col]) != "")
                & (_clean_series(data[facility_col]) != "")
            ].copy()

            if not pathogen_facility_df.empty:

                pathogen_facility_df = (
                    pathogen_facility_df
                    .groupby(
                        [facility_col, pathogen_col]
                    )
                    .size()
                    .reset_index(name="Cases")
                )

                render_bar_chart(
                    pathogen_facility_df,
                    x=facility_col,
                    y="Cases",
                    color=pathogen_col,
                    title="Pathogen-wise Facility Distribution",
                )

            else:
                _show_no_data()

        # ------------------------------------------------
        # PATHOGEN WARD DISTRIBUTION
        # ------------------------------------------------

        st.markdown("### Pathogen-wise Ward Distribution")

        if ward_col:

            pathogen_ward_df = data[
                (_clean_series(data[pathogen_col]) != "")
                & (_clean_series(data[ward_col]) != "")
            ].copy()

            if not pathogen_ward_df.empty:

                pathogen_ward_df = (
                    pathogen_ward_df
                    .groupby(
                        [ward_col, pathogen_col]
                    )
                    .size()
                    .reset_index(name="Cases")
                )

                render_bar_chart(
                    pathogen_ward_df,
                    x=ward_col,
                    y="Cases",
                    color=pathogen_col,
                    title="Pathogen-wise Ward Distribution",
                )

            else:
                _show_no_data()

        # ------------------------------------------------
        # COMPLETE PATHOGEN SUMMARY TABLE
        # ------------------------------------------------

        st.markdown("### Complete Pathogen Summary")

        summary_df = (
            pathogen_values
            .value_counts()
            .reset_index()
        )

        summary_df.columns = [
            "Pathogen Name",
            "Cases",
        ]

        summary_df["Percentage"] = (
            summary_df["Cases"]
            / summary_df["Cases"].sum()
            * 100
        ).round(2)

        st.dataframe(
            summary_df,
            width="stretch",
            hide_index=True,
        )

    else:
        _show_no_data(
            "Pathogen column is available, but no pathogen values are recorded."
        )

else:

    st.warning(
        "Pathogen analysis is not available because "
        "'Test Performed Pathogen Name' / 'Pathogen Name' "
        "is not present in the current dataset."
    )

# ========================================================
# 8. REPORTING DATE TREND
# ========================================================

st.markdown("### Reporting Date Trend")

reporting_date_col = _find_column(
    data,
    [
        "Reporting Date",
        "Date",
    ]
)

if reporting_date_col:

    date_df = data.copy()

    date_df["_ReportingDate"] = pd.to_datetime(
        date_df[reporting_date_col],
        errors="coerce",
    )

    date_df = date_df.dropna(
        subset=["_ReportingDate"]
    )

    if not date_df.empty:

        daily_df = (
            date_df
            .groupby("_ReportingDate")
            .size()
            .reset_index(name="Cases")
            .sort_values("_ReportingDate")
        )

        render_line_chart(
            daily_df,
            x="_ReportingDate",
            y="Cases",
            title="Reporting Date-wise Trend",
        )

    else:
        _show_no_data(
            "Valid reporting dates are not available."
        )

else:
    _show_no_data(
        "Reporting Date information is not available."
    )

# ========================================================
# 9. ANALYTICAL SUMMARY
# ========================================================

st.markdown("## Trend Summary")

summary_cols = st.columns(3)

with summary_cols[0]:
    st.metric(
        "Total Records",
        f"{len(data):,}",
    )

with summary_cols[1]:

    if disease_col:
        disease_count = _valid_series(
            data[disease_col]
        ).nunique()
    else:
        disease_count = 0

    st.metric(
        "Diseases Recorded",
        f"{disease_count:,}",
    )

with summary_cols[2]:

    if facility_col:
        facility_count = _valid_series(
            data[facility_col]
        ).nunique()
    else:
        facility_count = 0

    st.metric(
        "Facilities Reporting",
        f"{facility_count:,}",
    )

st.caption(
    "Charts are generated from the currently loaded and filtered programme dataset."
)
```
