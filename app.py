import re
from io import StringIO

import numpy as np
import pandas as pd
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
    "Week.1",
]


# ============================================================
# GOOGLE SHEET URL CONVERSION
# ============================================================

def convert_to_csv_url(sheet_url: str) -> str:
    """
    Convert a Google Sheets edit URL into a CSV export URL.
    """

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)

    if not match:
        raise ValueError("Invalid Google Sheets URL.")

    sheet_id = match.group(1)

    gid_match = re.search(r"[#&?]gid=(\d+)", sheet_url)

    if gid_match:
        gid = gid_match.group(1)
    else:
        gid = "0"

    return (
        f"https://docs.google.com/spreadsheets/d/"
        f"{sheet_id}/export?format=csv&gid={gid}"
    )


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data(ttl=60)
def load_google_sheet(sheet_url: str) -> pd.DataFrame:
    """
    Fetch live data from Google Sheets.
    Cache is automatically refreshed every 60 seconds.
    """

    csv_url = convert_to_csv_url(sheet_url)

    response = requests.get(
        csv_url,
        timeout=30,
    )

    response.raise_for_status()

    if not response.text.strip():
        raise ValueError("Google Sheet returned empty data.")

    df = pd.read_csv(StringIO(response.text))

    return df


# ============================================================
# DATA CLEANING
# ============================================================

def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize the raw Google Sheet data.
    """

    df = df.copy()

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Remove whitespace from column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Strip whitespace from text columns
    text_columns = df.select_dtypes(include="object").columns

    for column in text_columns:
        df[column] = (
            df[column]
            .astype(str)
            .str.strip()
            .replace({
                "nan": np.nan,
                "None": np.nan,
            })
        )

    # Convert dates
    for date_column in [
        "Reporting Date",
        "Date Of Onset",
    ]:
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(
                df[date_column],
                errors="coerce",
                dayfirst=True,
            )

    # Convert numeric fields
    if "Age" in df.columns:
        df["Age"] = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

    # Standardize Year
    if "Year" in df.columns:
        df["Year"] = (
            pd.to_numeric(
                df["Year"],
                errors="coerce",
            )
            .astype("Int64")
        )

    return df


# ============================================================
# DATA VALIDATION
# ============================================================

def validate_columns(df: pd.DataFrame):
    """
    Check whether the Google Sheet contains the expected columns.
    """

    actual_columns = set(df.columns)
    expected_columns = set(EXPECTED_COLUMNS)

    missing_columns = sorted(
        expected_columns - actual_columns
    )

    extra_columns = sorted(
        actual_columns - expected_columns
    )

    return missing_columns, extra_columns


# ============================================================
# LOAD DATA
# ============================================================

try:
    with st.spinner("Loading live data from Google Sheets..."):
        raw_df = load_google_sheet(GOOGLE_SHEET_URL)

    df = clean_data(raw_df)

except Exception as error:
    st.error(
        "Unable to load data from Google Sheets."
    )

    st.exception(error)

    st.stop()


# ============================================================
# VALIDATION
# ============================================================

missing_columns, extra_columns = validate_columns(df)

if missing_columns:
    st.warning(
        "Some expected columns are missing from the Google Sheet."
    )

    st.write(missing_columns)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("Dashboard Controls")

if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(
    "Data source: Live Google Sheet"
)

st.sidebar.caption(
    "Automatic cache refresh: 60 seconds"
)


# ============================================================
# HEADER
# ============================================================

st.title("🏥 Health Facility Monitor")

st.caption(
    "Public Health Surveillance and Epidemiological Monitoring Dashboard"
)

st.divider()


# ============================================================
# DATA STATUS
# ============================================================

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    st.metric(
        "Total Records",
        f"{len(df):,}",
    )

with status_col2:
    st.metric(
        "Total Columns",
        len(df.columns),
    )

with status_col3:
    if "Ward" in df.columns:
        ward_count = df["Ward"].nunique(
            dropna=True
        )
    else:
        ward_count = 0

    st.metric(
        "Wards",
        f"{ward_count:,}",
    )


# ============================================================
# DATA PREVIEW
# ============================================================

st.subheader("Live Data Preview")

st.dataframe(
    df.head(100),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# DATA INFORMATION
# ============================================================

with st.expander("Data Structure"):
    structure_df = pd.DataFrame(
        {
            "Column": df.columns,
            "Data Type": [
                str(df[column].dtype)
                for column in df.columns
            ],
            "Non-Empty Values": [
                int(df[column].notna().sum())
                for column in df.columns
            ],
        }
    )

    st.dataframe(
        structure_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Health Facility Monitor | Live Google Sheets Data Source"
)
