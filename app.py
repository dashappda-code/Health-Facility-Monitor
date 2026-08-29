import re
from io import StringIO

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Health Facility Monitor",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# GOOGLE SHEET CONFIGURATION
# ============================================================

GOOGLE_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "18qfha01Czh10i4PDRUpuumtRVwbQv7Pn09jFxGSbXHg/"
    "edit?gid=1168281274#gid=1168281274"
)


# ============================================================
# EXPECTED COLUMNS
# ============================================================

EXPECTED_COLUMNS = [
    "Year",
    "Month",
    "Week",
    "MSU Unique Code",
    "Form Type",
    "Reporting Date",
    "Date Of Onset",
    "Gender",
    "Age",
    "Patient Address",
    "Ward",
    "Confirmed Diagnosis",
    "Opd Ipd",
    "Test Performed",
    "Pathogen Name",
    "Pathogen Subtype",
    "Facility Name Lform",
    "Facility Type",
    "PUBLIC / PRIVATE FACILITIES",
    "Week range",
]


# ============================================================
# GOOGLE SHEET URL CONVERSION
# ============================================================

def convert_to_csv_url(sheet_url: str) -> str:
    """
    Convert a Google Sheets edit URL into a CSV export URL.
    """

    match = re.search(
        r"/spreadsheets/d/([a-zA-Z0-9-_]+)",
        sheet_url,
    )

    if not match:
        raise ValueError("Invalid Google Sheets URL.")

    sheet_id = match.group(1)

    gid_match = re.search(
        r"[#&?]gid=(\d+)",
        sheet_url,
    )

    gid = gid_match.group(1) if gid_match else "0"

    return (
        f"https://docs.google.com/spreadsheets/d/"
        f"{sheet_id}/export?format=csv&gid={gid}"
    )


# ============================================================
# LOAD GOOGLE SHEET
# ============================================================

@st.cache_data(ttl=60)
def load_google_sheet(sheet_url: str) -> pd.DataFrame:
    """
    Load live data from Google Sheets.
    Data cache expires after 60 seconds.
    """

    csv_url = convert_to_csv_url(sheet_url)

    response = requests.get(
        csv_url,
        timeout=30,
    )

    response.raise_for_status()

    if not response.text.strip():
        raise ValueError(
            "Google Sheet returned empty data."
        )

    return pd.read_csv(
        StringIO(response.text)
    )


# ============================================================
# DATA CLEANING
# ============================================================

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize the dataset.
    """

    df = df.copy()

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Clean column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # --------------------------------------------------------
    # Normalize Week range column
    # --------------------------------------------------------

    if "Week.1" in df.columns:
        df = df.rename(
            columns={
                "Week.1": "Week range"
            }
        )

    # --------------------------------------------------------
    # Clean text columns
    # --------------------------------------------------------

    text_columns = df.select_dtypes(
        include="object"
    ).columns

    for column in text_columns:
        df[column] = (
            df[column]
            .astype(str)
            .str.strip()
            .replace(
                {
                    "nan": np.nan,
                    "None": np.nan,
                    "": np.nan,
                }
            )
        )

    # --------------------------------------------------------
    # Convert dates
    # --------------------------------------------------------

    for column in [
        "Reporting Date",
        "Date Of Onset",
    ]:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column],
                errors="coerce",
                dayfirst=True,
            )

    # --------------------------------------------------------
    # Convert numeric columns
    # --------------------------------------------------------

    if "Age" in df.columns:
        df["Age"] = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

    if "Year" in df.columns:
        df["Year"] = pd.to_numeric(
            df["Year"],
            errors="coerce",
        ).astype("Int64")

    return df


# ============================================================
# DATA VALIDATION
# ============================================================

def validate_columns(
    df: pd.DataFrame,
):
    """
    Check required columns.
    """

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]

    return missing_columns


# ============================================================
# APPLY FILTERS
# ============================================================

def apply_filters(
    df: pd.DataFrame,
    selected_years,
    selected_months,
    selected_weeks,
    selected_diseases,
    selected_wards,
    selected_genders,
    selected_opd_ipd,
    date_from,
    date_to,
):
    """
    Apply all dashboard filters to the dataset.
    """

    filtered = df.copy()

    # Year
    if selected_years:
        filtered = filtered[
            filtered["Year"].isin(
                selected_years
            )
        ]

    # Month
    if selected_months:
        filtered = filtered[
            filtered["Month"].isin(
                selected_months
            )
        ]

    # Week
    if selected_weeks:
        filtered = filtered[
            filtered["Week"].isin(
                selected_weeks
            )
        ]

    # Disease
    if selected_diseases:
        filtered = filtered[
            filtered["Confirmed Diagnosis"].isin(
                selected_diseases
            )
        ]

    # Ward
    if selected_wards:
        filtered = filtered[
            filtered["Ward"].isin(
                selected_wards
            )
        ]

    # Gender
    if selected_genders:
        filtered = filtered[
            filtered["Gender"].isin(
                selected_genders
            )
        ]

    # OPD / IPD
    if selected_opd_ipd:
        filtered = filtered[
            filtered["Opd Ipd"].isin(
                selected_opd_ipd
            )
        ]

    # Reporting date range
    if date_from is not None:
        filtered = filtered[
            filtered["Reporting Date"].dt.date
            >= date_from
        ]

    if date_to is not None:
        filtered = filtered[
            filtered["Reporting Date"].dt.date
            <= date_to
        ]

    return filtered


# ============================================================
# KPI CALCULATIONS
# ============================================================

def calculate_kpis(df: pd.DataFrame):
    """
    Calculate KPI values from filtered data.
    """

    total_cases = len(df)

    opd_cases = (
        df["Opd Ipd"].eq("OPD").sum()
        if "Opd Ipd" in df.columns
        else 0
    )

    ipd_cases = (
        df["Opd Ipd"].eq("IPD").sum()
        if "Opd Ipd" in df.columns
        else 0
    )

    male_cases = (
        df["Gender"].eq("M").sum()
        if "Gender" in df.columns
        else 0
    )

    female_cases = (
        df["Gender"].eq("F").sum()
        if "Gender" in df.columns
        else 0
    )

    transgender_cases = (
        df["Gender"].eq("Transgender").sum()
        if "Gender" in df.columns
        else 0
    )

    # Top disease
    if (
        not df.empty
        and "Confirmed Diagnosis" in df.columns
    ):
        disease_counts = (
            df["Confirmed Diagnosis"]
            .dropna()
            .value_counts()
        )

        top_disease = (
            disease_counts.index[0]
            if not disease_counts.empty
            else "N/A"
        )
    else:
        top_disease = "N/A"

    # Top ward
    if (
        not df.empty
        and "Ward" in df.columns
    ):
        ward_counts = (
            df["Ward"]
            .dropna()
            .value_counts()
        )

        top_ward = (
            ward_counts.index[0]
            if not ward_counts.empty
            else "N/A"
        )
    else:
        top_ward = "N/A"

    return {
        "total_cases": total_cases,
        "opd_cases": opd_cases,
        "ipd_cases": ipd_cases,
        "male_cases": male_cases,
        "female_cases": female_cases,
        "transgender_cases": transgender_cases,
        "top_disease": top_disease,
        "top_ward": top_ward,
    }


# ============================================================
# LOAD DATA
# ============================================================

try:

    with st.spinner(
        "Loading live data from Google Sheets..."
    ):
        raw_df = load_google_sheet(
            GOOGLE_SHEET_URL
        )

    df = clean_data(raw_df)

except Exception as error:

    st.error(
        "Unable to load data from Google Sheets."
    )

    st.exception(error)

    st.stop()


# ============================================================
# VALIDATE DATA
# ============================================================

missing_columns = validate_columns(df)

if missing_columns:

    st.warning(
        "Some expected columns are missing "
        "from the Google Sheet."
    )

    st.write(missing_columns)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "Dashboard Controls"
)

# Refresh
if st.sidebar.button(
    "🔄 Refresh Data",
    use_container_width=True,
):

    st.cache_data.clear()
    st.rerun()


st.sidebar.divider()


# ============================================================
# FILTER OPTIONS
# ============================================================

# Year
year_options = sorted(
    df["Year"]
    .dropna()
    .unique()
    .tolist()
)

selected_years = st.sidebar.multiselect(
    "Year",
    options=year_options,
    default=year_options,
)


# Month
month_order = [
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

available_months = [
    month
    for month in month_order
    if month in df["Month"].dropna().unique()
]

selected_months = st.sidebar.multiselect(
    "Month",
    options=available_months,
    default=available_months,
)


# Week
week_order = [
    "Week 1",
    "Week 2",
    "Week 3",
    "Week 4",
    "Week 5",
]

available_weeks = [
    week
    for week in week_order
    if week in df["Week"].dropna().unique()
]

# Add any unexpected week values
extra_weeks = [
    week
    for week in df["Week"].dropna().unique()
    if week not in available_weeks
]

available_weeks.extend(
    sorted(extra_weeks)
)

selected_weeks = st.sidebar.multiselect(
    "Week",
    options=available_weeks,
    default=available_weeks,
)


# Disease
disease_options = sorted(
    df["Confirmed Diagnosis"]
    .dropna()
    .unique()
    .tolist()
)

selected_diseases = st.sidebar.multiselect(
    "Disease",
    options=disease_options,
)


# Ward
ward_options = sorted(
    df["Ward"]
    .dropna()
    .unique()
    .tolist()
)

selected_wards = st.sidebar.multiselect(
    "Ward",
    options=ward_options,
)


# Gender
gender_order = [
    "M",
    "F",
    "Transgender",
]

available_genders = [
    gender
    for gender in gender_order
    if gender in df["Gender"].dropna().unique()
]

selected_genders = st.sidebar.multiselect(
    "Gender",
    options=available_genders,
)


# OPD / IPD
opd_ipd_options = [
    value
    for value in ["OPD", "IPD"]
    if value in df["Opd Ipd"].dropna().unique()
]

selected_opd_ipd = st.sidebar.multiselect(
    "OPD / IPD",
    options=opd_ipd_options,
)


# ============================================================
# DATE FILTER
# ============================================================

st.sidebar.subheader(
    "Reporting Date"
)

valid_dates = df[
    "Reporting Date"
].dropna()

if not valid_dates.empty:

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()

    selected_date_range = st.sidebar.date_input(
        "Date range",
        value=(
            min_date,
            max_date,
        ),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(
        selected_date_range,
        tuple,
    ) and len(selected_date_range) == 2:

        date_from = selected_date_range[0]
        date_to = selected_date_range[1]

    else:

        date_from = min_date
        date_to = max_date

else:

    date_from = None
    date_to = None


# ============================================================
# APPLY FILTERS
# ============================================================

filtered_df = apply_filters(
    df=df,
    selected_years=selected_years,
    selected_months=selected_months,
    selected_weeks=selected_weeks,
    selected_diseases=selected_diseases,
    selected_wards=selected_wards,
    selected_genders=selected_genders,
    selected_opd_ipd=selected_opd_ipd,
    date_from=date_from,
    date_to=date_to,
)


# ============================================================
# CALCULATE KPIs
# ============================================================

kpis = calculate_kpis(
    filtered_df
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "🏥 Health Facility Monitor"
)

st.caption(
    "Public Health Surveillance and "
    "Epidemiological Monitoring Dashboard"
)

st.divider()


# ============================================================
# FILTER STATUS
# ============================================================

st.info(
    f"Showing **{len(filtered_df):,}** "
    f"of **{len(df):,}** total records"
)


# ============================================================
# KPI CARDS
# ============================================================

st.subheader(
    "Key Indicators"
)


# First row
col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Total Cases",
        f"{kpis['total_cases']:,}",
    )

with col2:

    st.metric(
        "OPD Cases",
        f"{kpis['opd_cases']:,}",
    )

with col3:

    st.metric(
        "IPD Cases",
        f"{kpis['ipd_cases']:,}",
    )

with col4:

    st.metric(
        "Male",
        f"{kpis['male_cases']:,}",
    )


# Second row
col5, col6, col7, col8 = st.columns(4)

with col5:

    st.metric(
        "Female",
        f"{kpis['female_cases']:,}",
    )

with col6:

    st.metric(
        "Transgender",
        f"{kpis['transgender_cases']:,}",
    )

with col7:

    st.metric(
        "Top Disease",
        kpis["top_disease"],
    )

with col8:

    st.metric(
        "Top Ward",
        kpis["top_ward"],
    )


st.divider()


# ============================================================
# FILTERED DATA PREVIEW
# ============================================================

st.subheader(
    "Filtered Records"
)

if filtered_df.empty:

    st.warning(
        "No records match the selected filters."
    )

else:

    st.dataframe(
        filtered_df.head(100),
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
# CHARTS & ANALYTICS
# ============================================================

st.divider()

st.subheader("📊 Charts & Analytics")

if filtered_df.empty:

    st.warning(
        "No data available for charts with the selected filters."
    )

else:

    # ========================================================
    # PREPARE CHART DATA
    # ========================================================

    chart_df = filtered_df.copy()

    # --------------------------------------------------------
    # Month ordering
    # --------------------------------------------------------

    month_order = [
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

    # ========================================================
    # ROW 1
    # ========================================================

    chart_col1, chart_col2 = st.columns(2)

    # --------------------------------------------------------
    # 1. YEAR COMPARISON
    # --------------------------------------------------------

    with chart_col1:

        st.markdown("### 📅 Year Comparison")

        if "Year" in chart_df.columns:

            yearly_data = (
                chart_df
                .dropna(subset=["Year"])
                .groupby("Year")
                .size()
                .reset_index(name="Cases")
            )

            yearly_data["Year"] = (
                yearly_data["Year"]
                .astype(int)
                .astype(str)
            )

            if not yearly_data.empty:

                fig_year = px.bar(
                    yearly_data,
                    x="Year",
                    y="Cases",
                    text="Cases",
                    title="Total Cases by Year",
                )

                fig_year.update_traces(
                    textposition="outside"
                )

                fig_year.update_layout(
                    xaxis_title="Year",
                    yaxis_title="Cases",
                    height=400,
                )

                st.plotly_chart(
                    fig_year,
                    use_container_width=True,
                )

            else:

                st.info(
                    "No year data available."
                )

    # --------------------------------------------------------
    # 2. MONTHLY TREND
    # --------------------------------------------------------

    with chart_col2:

        st.markdown("### 📈 Monthly Trend")

        if "Month" in chart_df.columns:

            monthly_data = (
                chart_df
                .dropna(subset=["Month"])
                .groupby(
                    ["Year", "Month"],
                    dropna=False,
                )
                .size()
                .reset_index(name="Cases")
            )

            monthly_data["Month"] = pd.Categorical(
                monthly_data["Month"],
                categories=month_order,
                ordered=True,
            )

            monthly_data = (
                monthly_data
                .sort_values(
                    ["Year", "Month"]
                )
            )

            if not monthly_data.empty:

                monthly_data["Year"] = (
                    monthly_data["Year"]
                    .astype(str)
                )

                fig_month = px.line(
                    monthly_data,
                    x="Month",
                    y="Cases",
                    color="Year",
                    markers=True,
                    title="Monthly Case Trend",
                )

                fig_month.update_layout(
                    xaxis_title="Month",
                    yaxis_title="Cases",
                    height=400,
                )

                st.plotly_chart(
                    fig_month,
                    use_container_width=True,
                )

            else:

                st.info(
                    "No monthly data available."
                )


    # ========================================================
    # ROW 2
    # ========================================================

    chart_col3, chart_col4 = st.columns(2)

    # --------------------------------------------------------
    # 3. WEEKLY TREND
    # --------------------------------------------------------

    with chart_col3:

        st.markdown("### 📆 Weekly Trend")

        if "Week" in chart_df.columns:

            weekly_data = (
                chart_df
                .dropna(subset=["Week"])
                .groupby(
                    ["Year", "Week"],
                    dropna=False,
                )
                .size()
                .reset_index(name="Cases")
            )

            # Extract week number for sorting
            weekly_data["Week Number"] = (
                weekly_data["Week"]
                .astype(str)
                .str.extract(
                    r"(\d+)"
                )[0]
                .astype(float)
            )

            weekly_data = (
                weekly_data
                .sort_values(
                    ["Year", "Week Number"]
                )
            )

            weekly_data["Year"] = (
                weekly_data["Year"]
                .astype(str)
            )

            if not weekly_data.empty:

                fig_week = px.line(
                    weekly_data,
                    x="Week",
                    y="Cases",
                    color="Year",
                    markers=True,
                    title="Weekly Case Trend",
                )

                fig_week.update_layout(
                    xaxis_title="Week",
                    yaxis_title="Cases",
                    height=400,
                )

                st.plotly_chart(
                    fig_week,
                    use_container_width=True,
                )

            else:

                st.info(
                    "No weekly data available."
                )


    # --------------------------------------------------------
    # 4. DISEASE DISTRIBUTION
    # --------------------------------------------------------

    with chart_col4:

        st.markdown("### 🦠 Disease Distribution")

        if "Confirmed Diagnosis" in chart_df.columns:

            disease_data = (
                chart_df[
                    "Confirmed Diagnosis"
                ]
                .dropna()
                .value_counts()
                .reset_index()
            )

            disease_data.columns = [
                "Disease",
                "Cases",
            ]

            # Show top 15 diseases
            disease_data = disease_data.head(15)

            if not disease_data.empty:

                fig_disease = px.bar(
                    disease_data.sort_values(
                        "Cases"
                    ),
                    x="Cases",
                    y="Disease",
                    orientation="h",
                    text="Cases",
                    title="Top 15 Diseases",
                )

                fig_disease.update_traces(
                    textposition="outside"
                )

                fig_disease.update_layout(
                    xaxis_title="Cases",
                    yaxis_title="Disease",
                    height=500,
                )

                st.plotly_chart(
                    fig_disease,
                    use_container_width=True,
                )

            else:

                st.info(
                    "No disease data available."
                )


    # ========================================================
    # ROW 3
    # ========================================================

    st.markdown("### 🏙️ Ward-wise Cases")

    if "Ward" in chart_df.columns:

        ward_data = (
            chart_df[
                "Ward"
            ]
            .dropna()
            .value_counts()
            .reset_index()
        )

        ward_data.columns = [
            "Ward",
            "Cases",
        ]

        # Top 15 wards
        ward_data = ward_data.head(15)

        if not ward_data.empty:

            fig_ward = px.bar(
                ward_data.sort_values(
                    "Cases"
                ),
                x="Cases",
                y="Ward",
                orientation="h",
                text="Cases",
                title="Top 15 Wards by Case Count",
            )

            fig_ward.update_traces(
                textposition="outside"
            )

            fig_ward.update_layout(
                xaxis_title="Cases",
                yaxis_title="Ward",
                height=550,
            )

            st.plotly_chart(
                fig_ward,
                use_container_width=True,
            )

        else:

            st.info(
                "No ward data available."
            )




# ============================================================
# DATA SUMMARY
# ============================================================

with st.expander(
    "Data Summary"
):

    summary_col1, summary_col2 = st.columns(2)

    with summary_col1:

        st.write(
            "**Dataset Information**"
        )

        st.write(
            f"Original records: "
            f"{len(df):,}"
        )

        st.write(
            f"Filtered records: "
            f"{len(filtered_df):,}"
        )

        st.write(
            f"Columns: "
            f"{len(df.columns)}"
        )

    with summary_col2:

        st.write(
            "**Current Filters**"
        )

        st.write(
            f"Years: "
            f"{', '.join(map(str, selected_years))}"
        )

        st.write(
            f"Months: "
            f"{', '.join(selected_months) if selected_months else 'All'}"
        )

        st.write(
            f"Wards: "
            f"{len(selected_wards) if selected_wards else 'All'}"
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Health Facility Monitor | "
    "Live Google Sheets Data Source"
)
