import streamlit as st
import pandas as pd

import phase1_data

def find_column(df, candidates):
if df is None or df.empty:
return None

```
columns = {
    str(col).strip().lower(): col
    for col in df.columns
}

for candidate in candidates:
    key = str(candidate).strip().lower()
    if key in columns:
        return columns[key]

return None
```

def get_values(df, column):
if df is None or df.empty:
return []

```
if column is None or column not in df.columns:
    return []

values = (
    df[column]
    .dropna()
    .astype(str)
    .str.strip()
)

values = values[
    (values != "")
    & (values != "nan")
    & (values != "None")
]

return sorted(
    values.unique().tolist(),
    key=lambda x: str(x).lower()
)
```

def _reset_filters():
current_version = st.session_state.get(
"filter_reset_version",
0
)

```
st.session_state["filter_reset_version"] = (
    current_version + 1
)

keys_to_remove = [
    key
    for key in list(st.session_state.keys())
    if str(key).startswith("global_")
]

for key in keys_to_remove:
    try:
        del st.session_state[key]
    except Exception:
        pass
```

def create_filters(df):

```
if df is None or df.empty:
    return {
        "selected_years": [],
        "selected_months": [],
        "selected_weeks": [],
        "selected_diseases": [],
        "selected_facilities": [],
        "selected_wards": [],
        "selected_genders": [],
        "selected_age_groups": [],
        "selected_opd_ipd": [],
        "date_column": "Reporting Date",
        "date_from": None,
        "date_to": None,
    }

reset_version = st.session_state.get(
    "filter_reset_version",
    0
)

st.markdown(
    """
    <div class="global-filter-heading">
        <div class="global-filter-title">
            🎛️ Global Dashboard Control
        </div>
        <div class="global-filter-subtitle">
            Select any filter to immediately update the dashboard.
            Blank filters represent all available data.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

button_col1, button_col2, _ = st.columns(
    [1, 1, 5]
)

with button_col1:
    refresh_clicked = st.button(
        "🔄 Refresh Data",
        key=f"global_refresh_{reset_version}",
        use_container_width=True,
    )

with button_col2:
    reset_clicked = st.button(
        "↺ Reset Filters",
        key=f"global_reset_{reset_version}",
        use_container_width=True,
    )

if refresh_clicked:
    with st.spinner(
        "Refreshing Google Sheet data..."
    ):
        phase1_data.refresh_data()

    st.rerun()

if reset_clicked:
    _reset_filters()
    st.rerun()

year_col = find_column(
    df,
    ["Year"]
)

month_col = find_column(
    df,
    ["Month"]
)

week_col = find_column(
    df,
    ["Week"]
)

disease_col = find_column(
    df,
    [
        "Disease",
        "Confirmed Diagnosis",
    ]
)

facility_col = find_column(
    df,
    [
        "Facility Name",
        "Facility Name Lform",
    ]
)

ward_col = find_column(
    df,
    [
        "Ward Name",
        "Ward",
    ]
)

gender_col = find_column(
    df,
    ["Gender"]
)

age_group_col = find_column(
    df,
    ["Age Group"]
)

opd_ipd_col = find_column(
    df,
    [
        "OPD/IPD",
        "Opd Ipd",
    ]
)

date_column = find_column(
    df,
    ["Reporting Date"]
)

years = get_values(
    df,
    year_col
)

months = get_values(
    df,
    month_col
)

weeks = get_values(
    df,
    week_col
)

diseases = get_values(
    df,
    disease_col
)

facilities = get_values(
    df,
    facility_col
)

wards = get_values(
    df,
    ward_col
)

genders = get_values(
    df,
    gender_col
)

age_groups = get_values(
    df,
    age_group_col
)

opd_ipd_values = get_values(
    df,
    opd_ipd_col
)

row1 = st.columns(4)

with row1[0]:
    selected_years = st.multiselect(
        "📅 Year",
        options=years,
        default=[],
        key=f"global_year_filter_{reset_version}",
        placeholder="Select Year",
    )

with row1[1]:
    selected_months = st.multiselect(
        "🗓️ Month",
        options=months,
        default=[],
        key=f"global_month_filter_{reset_version}",
        placeholder="Select Month",
    )

with row1[2]:
    selected_weeks = st.multiselect(
        "📆 Week",
        options=weeks,
        default=[],
        key=f"global_week_filter_{reset_version}",
        placeholder="Select Week",
    )

with row1[3]:
    selected_diseases = st.multiselect(
        "🦠 Disease",
        options=diseases,
        default=[],
        key=f"global_disease_filter_{reset_version}",
        placeholder="Select Disease",
    )

row2 = st.columns(4)

with row2[0]:
    selected_facilities = st.multiselect(
        "🏥 Facility",
        options=facilities,
        default=[],
        key=f"global_facility_filter_{reset_version}",
        placeholder="Select Facility",
    )

with row2[1]:
    selected_wards = st.multiselect(
        "🏘️ Ward",
        options=wards,
        default=[],
        key=f"global_ward_filter_{reset_version}",
        placeholder="Select Ward",
    )

with row2[2]:
    selected_genders = st.multiselect(
        "⚥ Gender",
        options=genders,
        default=[],
        key=f"global_gender_filter_{reset_version}",
        placeholder="Select Gender",
    )

with row2[3]:
    selected_age_groups = st.multiselect(
        "👥 Age Group",
        options=age_groups,
        default=[],
        key=f"global_age_group_filter_{reset_version}",
        placeholder="Select Age Group",
    )

row3 = st.columns(4)

with row3[0]:
    selected_opd_ipd = st.multiselect(
        "🏨 OPD / IPD",
        options=opd_ipd_values,
        default=[],
        key=f"global_opd_ipd_filter_{reset_version}",
        placeholder="Select OPD / IPD",
    )

with row3[1]:
    use_reporting_date = st.checkbox(
        "📅 Use Reporting Date",
        value=False,
        key=f"global_use_reporting_date_{reset_version}",
    )

date_from = None
date_to = None

if (
    use_reporting_date
    and date_column is not None
    and date_column in df.columns
):
    valid_dates = pd.to_datetime(
        df[date_column],
        errors="coerce"
    ).dropna()

    if not valid_dates.empty:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()

        date_col1, date_col2 = st.columns(2)

        with date_col1:
            date_from = st.date_input(
                "From Date",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                key=f"global_date_from_{reset_version}",
            )

        with date_col2:
            date_to = st.date_input(
                "To Date",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                key=f"global_date_to_{reset_version}",
            )

return {
    "selected_years": selected_years,
    "selected_months": selected_months,
    "selected_weeks": selected_weeks,
    "selected_diseases": selected_diseases,
    "selected_facilities": selected_facilities,
    "selected_wards": selected_wards,
    "selected_genders": selected_genders,
    "selected_age_groups": selected_age_groups,
    "selected_opd_ipd": selected_opd_ipd,
    "date_column": date_column,
    "date_from": date_from,
    "date_to": date_to,
}
```

def apply_filters(
df,
selected_years=None,
selected_months=None,
selected_weeks=None,
selected_diseases=None,
selected_facilities=None,
selected_wards=None,
selected_genders=None,
selected_age_groups=None,
selected_opd_ipd=None,
date_column=None,
date_from=None,
date_to=None,
):

```
if df is None or df.empty:
    return pd.DataFrame()

filtered = df.copy()

def apply_text_filter(
    current_df,
    selected_values,
    candidates,
):
    if not selected_values:
        return current_df

    column = find_column(
        current_df,
        candidates
    )

    if column is None:
        return current_df

    values = (
        current_df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    selected = {
        str(value).strip()
        for value in selected_values
    }

    return current_df[
        values.isin(selected)
    ]

filtered = apply_text_filter(
    filtered,
    selected_years,
    ["Year"],
)

filtered = apply_text_filter(
    filtered,
    selected_months,
    ["Month"],
)

filtered = apply_text_filter(
    filtered,
    selected_weeks,
    ["Week"],
)

filtered = apply_text_filter(
    filtered,
    selected_diseases,
    [
        "Disease",
        "Confirmed Diagnosis",
    ],
)

filtered = apply_text_filter(
    filtered,
    selected_facilities,
    [
        "Facility Name",
        "Facility Name Lform",
    ],
)

filtered = apply_text_filter(
    filtered,
    selected_wards,
    [
        "Ward Name",
        "Ward",
    ],
)

filtered = apply_text_filter(
    filtered,
    selected_genders,
    ["Gender"],
)

filtered = apply_text_filter(
    filtered,
    selected_age_groups,
    ["Age Group"],
)

filtered = apply_text_filter(
    filtered,
    selected_opd_ipd,
    [
        "OPD/IPD",
        "Opd Ipd",
    ],
)

if (
    date_column is not None
    and date_column in filtered.columns
    and date_from is not None
    and date_to is not None
):
    dates = pd.to_datetime(
        filtered[date_column],
        errors="coerce"
    )

    start_date = pd.Timestamp(
        date_from
    )

    end_date = (
        pd.Timestamp(date_to)
        + pd.Timedelta(days=1)
        - pd.Timedelta(nanoseconds=1)
    )

    filtered = filtered[
        dates.between(
            start_date,
            end_date,
            inclusive="both",
        )
    ]

return filtered.reset_index(
    drop=True
)
```

def calculate_kpis(df):

```
if df is None or df.empty:
    return {
        "total_records": 0,
        "diseases": 0,
        "facilities": 0,
        "wards": 0,
        "genders": 0,
        "age_groups": 0,
    }

disease_col = find_column(
    df,
    [
        "Disease",
        "Confirmed Diagnosis",
    ],
)

facility_col = find_column(
    df,
    [
        "Facility Name",
        "Facility Name Lform",
    ],
)

ward_col = find_column(
    df,
    [
        "Ward Name",
        "Ward",
    ],
)

gender_col = find_column(
    df,
    ["Gender"],
)

age_group_col = find_column(
    df,
    ["Age Group"],
)

def unique_count(column):

    if (
        column is None
        or column not in df.columns
    ):
        return 0

    values = (
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[
        (values != "")
        & (values != "nan")
        & (values != "None")
    ]

    return int(
        values.nunique()
    )

return {
    "total_records": int(len(df)),
    "diseases": unique_count(disease_col),
    "facilities": unique_count(facility_col),
    "wards": unique_count(ward_col),
    "genders": unique_count(gender_col),
    "age_groups": unique_count(age_group_col),
}
```

def render_overview(df):

```
st.subheader(
    "📊 Programme Overview"
)

if df is None or df.empty:
    st.warning(
        "No records available for the selected filters."
    )
    return

disease_col = find_column(
    df,
    [
        "Disease",
        "Confirmed Diagnosis",
    ],
)

facility_col = find_column(
    df,
    [
        "Facility Name",
        "Facility Name Lform",
    ],
)

ward_col = find_column(
    df,
    [
        "Ward Name",
        "Ward",
    ],
)

month_col = find_column(
    df,
    ["Month"],
)

st.markdown(
    "### Management Summary"
)

kpis = calculate_kpis(df)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "Records",
        f"{kpis['total_records']:,}",
    )

with c2:
    st.metric(
        "Diseases",
        f"{kpis['diseases']:,}",
    )

with c3:
    st.metric(
        "Facilities",
        f"{kpis['facilities']:,}",
    )

with c4:
    st.metric(
        "Wards",
        f"{kpis['wards']:,}",
    )

st.divider()

col1, col2 = st.columns(2)

with col1:

    st.markdown(
        "### 🏥 Top Facilities by Record Burden"
    )

    if facility_col is not None:

        facility_summary = (
            df[facility_col]
            .fillna("")
            .astype(str)
            .str.strip()
            .value_counts()
            .head(10)
        )

        facility_summary = facility_summary[
            facility_summary.index != ""
        ]

        if not facility_summary.empty:

            st.dataframe(
                facility_summary.rename(
                    "Records"
                ).to_frame(),
                use_container_width=True,
            )

        else:

            st.info(
                "Facility information not available."
            )

    else:

        st.info(
            "Facility information not available."
        )

with col2:

    st.markdown(
        "### 🏘️ Top Wards by Record Burden"
    )

    if ward_col is not None:

        ward_summary = (
            df[ward_col]
            .fillna("")
            .astype(str)
            .str.strip()
            .value_counts()
            .head(10)
        )

        ward_summary = ward_summary[
            ward_summary.index != ""
        ]

        if not ward_summary.empty:

            st.dataframe(
                ward_summary.rename(
                    "Records"
                ).to_frame(),
                use_container_width=True,
            )

        else:

            st.info(
                "Ward information not available."
            )

    else:

        st.info(
            "Ward information not available."
        )

st.divider()

st.markdown(
    "### 📅 Monthly Record Trend"
)

if month_col is not None:

    month_summary = (
        df[month_col]
        .fillna("")
        .astype(str)
        .str.strip()
        .value_counts()
    )

    month_summary = month_summary[
        month_summary.index != ""
    ]

    if not month_summary.empty:

        st.bar_chart(
            month_summary,
            use_container_width=True,
        )

    else:

        st.info(
            "Monthly information not available."
        )

if disease_col is not None:

    st.markdown(
        "### 🦠 Disease Distribution"
    )

    disease_summary = (
        df[disease_col]
        .fillna("")
        .astype(str)
        .str.strip()
        .value_counts()
        .head(15)
    )

    disease_summary = disease_summary[
        disease_summary.index != ""
    ]

    if not disease_summary.empty:

        st.dataframe(
            disease_summary.rename(
                "Records"
            ).to_frame(),
            use_container_width=True,
        )

    else:

        st.info(
            "Disease information not available."
        )
