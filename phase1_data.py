```python
import re
from io import StringIO

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# GOOGLE SHEET
# ============================================================

GOOGLE_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1Qm8wP8wM2kYx9YwK8mQm3hY9K0vQ2xY9"
    "/export?format=csv"
)


# ============================================================
# EXPECTED COLUMNS
# ============================================================

EXPECTED_COLUMNS = [
    "Reporting Date",
    "Year",
    "Month",
    "Week",
    "Week range",
    "Disease",
    "Facility Name",
    "Ward Name",
    "Gender",
    "Age",
    "Age Group",
    "OPD/IPD",
    "Patient Address",
    "Confirmed Diagnosis",
]


# ============================================================
# GOOGLE SHEET URL
# ============================================================

def convert_to_csv_url(url: str) -> str:
    """
    Converts normal Google Sheet URL to CSV export URL.
    """
    if "export?format=csv" in url:
        return url

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)

    if match:
        sheet_id = match.group(1)
        return (
            f"https://docs.google.com/spreadsheets/d/"
            f"{sheet_id}/export?format=csv"
        )

    return url


# ============================================================
# LOAD GOOGLE SHEET
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def load_google_sheet():

    csv_url = convert_to_csv_url(GOOGLE_SHEET_URL)

    response = requests.get(
        csv_url,
        timeout=(10, 30),
        headers={"User-Agent": "Mozilla/5.0"},
    )

    response.raise_for_status()

    df = pd.read_csv(
        StringIO(response.text),
        low_memory=False,
    )

    return df


# ============================================================
# SAFE DATE PARSER
# ============================================================

def _safe_parse_date(value):

    if pd.isna(value):
        return pd.NaT

    value_str = str(value).strip()

    if not value_str:
        return pd.NaT

    # --------------------------------------------------------
    # Numeric Excel / Google serial date
    # --------------------------------------------------------

    if re.fullmatch(r"\d+(\.\d+)?", value_str):

        try:
            number = float(value_str)

            # Excel / Google serial range
            if 20000 <= number <= 80000:

                dt = pd.Timestamp("1899-12-30") + pd.to_timedelta(
                    number,
                    unit="D",
                )

                if 2000 <= dt.year <= 2100:
                    return dt

            return pd.NaT

        except Exception:
            return pd.NaT

    # --------------------------------------------------------
    # Reject obviously invalid years
    # --------------------------------------------------------

    year_match = re.match(r"^(\d{4})[-/]", value_str)

    if year_match:

        year = int(year_match.group(1))

        if year < 2000 or year > 2100:
            return pd.NaT

    # --------------------------------------------------------
    # Normal date parsing
    # --------------------------------------------------------

    try:

        dt = pd.to_datetime(
            value_str,
            format="mixed",
            dayfirst=True,
            errors="coerce",
        )

        if pd.isna(dt):
            return pd.NaT

        if dt.year < 2000 or dt.year > 2100:
            return pd.NaT

        return dt

    except Exception:
        return pd.NaT


# ============================================================
# REPORTING DATE CLEANING
# ============================================================

def clean_reporting_date(series):

    values = []

    for value in series:

        values.append(
            _safe_parse_date(value)
        )

    return pd.Series(
        values,
        index=series.index,
        dtype="datetime64[ns]",
    )


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text_column(series):

    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )


# ============================================================
# AGE CLEANING
# ============================================================

def clean_age(series):

    numeric = pd.to_numeric(
        series,
        errors="coerce",
    )

    numeric = numeric.where(
        (numeric >= 0) &
        (numeric <= 120)
    )

    return numeric


# ============================================================
# AGE GROUP
# ============================================================

def create_age_group(age):

    if pd.isna(age):
        return "Unknown"

    age = float(age)

    if age < 1:
        return "Below 1 year"

    if age <= 4:
        return "1-4"

    if age <= 14:
        return "5-14"

    if age <= 24:
        return "15-24"

    if age <= 44:
        return "25-44"

    if age <= 64:
        return "45-64"

    return "65+"


# ============================================================
# CLEAN DATA
# ============================================================

def clean_data(df):

    df = df.copy()

    # --------------------------------------------------------
    # Standardize column names
    # --------------------------------------------------------

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # Add missing expected columns
    # --------------------------------------------------------

    for column in EXPECTED_COLUMNS:

        if column not in df.columns:
            df[column] = ""

    # --------------------------------------------------------
    # Text columns
    # --------------------------------------------------------

    text_columns = [
        "Year",
        "Month",
        "Week",
        "Week range",
        "Disease",
        "Facility Name",
        "Ward Name",
        "Gender",
        "Age Group",
        "OPD/IPD",
        "Patient Address",
        "Confirmed Diagnosis",
    ]

    for column in text_columns:

        if column in df.columns:
            df[column] = clean_text_column(
                df[column]
            )

    # --------------------------------------------------------
    # Reporting Date
    # --------------------------------------------------------

    if "Reporting Date" in df.columns:

        df["Reporting Date"] = clean_reporting_date(
            df["Reporting Date"]
        )

    # --------------------------------------------------------
    # Age
    # --------------------------------------------------------

    if "Age" in df.columns:

        df["Age"] = clean_age(
            df["Age"]
        )

    # --------------------------------------------------------
    # Create / repair Age Group
    # --------------------------------------------------------

    if "Age" in df.columns:

        calculated_age_group = df["Age"].apply(
            create_age_group
        )

        existing = (
            df["Age Group"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        df["Age Group"] = np.where(
            existing.eq(""),
            calculated_age_group,
            existing,
        )

    # --------------------------------------------------------
    # Repair Year from Reporting Date
    # --------------------------------------------------------

    if "Reporting Date" in df.columns:

        missing_year = (
            df["Year"]
            .fillna("")
            .astype(str)
            .str.strip()
            .eq("")
        )

        df.loc[missing_year, "Year"] = (
            df.loc[missing_year, "Reporting Date"]
            .dt.year
            .astype("Int64")
            .astype(str)
        )

    # --------------------------------------------------------
    # Remove completely empty rows
    # --------------------------------------------------------

    df = df.dropna(
        how="all"
    ).reset_index(drop=True)

    return df


# ============================================================
# VALIDATION
# ============================================================

def validate_reporting_dates(df):

    if (
        "Reporting Date" not in df.columns
        or df.empty
    ):
        return None, None

    dates = df["Reporting Date"].dropna()

    if dates.empty:
        return None, None

    return dates.min(), dates.max()


# ============================================================
# MAIN DATA LOADER
# ============================================================

@st.cache_data(ttl=60, show_spinner=False)
def load_data():

    raw_df = load_google_sheet()

    if raw_df is None:
        return pd.DataFrame()

    if raw_df.empty:
        return raw_df

    df = clean_data(raw_df)

    return df


# ============================================================
# MANUAL REFRESH
# ============================================================

def refresh_data():

    load_google_sheet.clear()
    load_data.clear()

    return load_data()
```
