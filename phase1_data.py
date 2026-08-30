import re
from io import StringIO

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
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
    "Week range",
]


# ============================================================
# GOOGLE SHEET URL
# ============================================================

def convert_to_csv_url(sheet_url: str) -> str:

    match = re.search(
        r"/spreadsheets/d/([a-zA-Z0-9-_]+)",
        sheet_url,
    )

    if not match:
        raise ValueError(
            "Invalid Google Sheets URL."
        )

    sheet_id = match.group(1)

    gid_match = re.search(
        r"[#&?]gid=(\d+)",
        sheet_url,
    )

    gid = (
        gid_match.group(1)
        if gid_match
        else "0"
    )

    return (
        f"https://docs.google.com/spreadsheets/d/"
        f"{sheet_id}/export?format=csv&gid={gid}"
    )


# ============================================================
# LOAD GOOGLE SHEET
# ============================================================

@st.cache_data(ttl=60)
def load_google_sheet() -> pd.DataFrame:

    csv_url = convert_to_csv_url(
        GOOGLE_SHEET_URL
    )

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
# CLEAN DATA
# ============================================================

def clean_data(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    # Remove completely empty rows
    df = df.dropna(how="all")

    # Clean column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # Normalize Week range
    if "Week.1" in df.columns:

        df = df.rename(
            columns={
                "Week.1": "Week range"
            }
        )

    # Clean text values
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

    # Dates
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

    # Age
    if "Age" in df.columns:

        df["Age"] = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

    # Year
    if "Year" in df.columns:

        df["Year"] = pd.to_numeric(
            df["Year"],
            errors="coerce",
        ).astype("Int64")

    return df


# ============================================================
# VALIDATION
# ============================================================

def validate_columns(
    df: pd.DataFrame,
):

    missing = [
        column
        for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]

    return missing


# ============================================================
# LOAD + CLEAN + VALIDATE
# ============================================================

def load_data() -> pd.DataFrame:

    raw_df = load_google_sheet()

    df = clean_data(raw_df)

    missing_columns = validate_columns(df)

    if missing_columns:

        st.warning(
            "Some expected columns are missing "
            "from the Google Sheet."
        )

        st.write(
            missing_columns
        )

    return df


# ============================================================
# REFRESH FUNCTION
# ============================================================

def refresh_data():

    st.cache_data.clear()

    st.rerun()
