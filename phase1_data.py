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
    "edit?gid=1910295094#gid=1910295094"
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
        StringIO(response.text),
        low_memory=False,
    )


# ============================================================
# FAST REPORTING DATE CLEANING
# ============================================================

def clean_reporting_date(
    series: pd.Series,
) -> pd.Series:

    # --------------------------------------------------------
    # Convert to string
    # --------------------------------------------------------

    s = (
        series
        .astype("string")
        .str.strip()
    )

    # --------------------------------------------------------
    # Empty values
    # --------------------------------------------------------

    s = s.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "None": pd.NA,
            "none": pd.NA,
            "NULL": pd.NA,
            "null": pd.NA,
        }
    )

    # ========================================================
    # NORMAL TEXT DATES
    # ========================================================

    result = pd.to_datetime(
        s,
        format="mixed",
        dayfirst=True,
        errors="coerce",
    )

    # ========================================================
    # GOOGLE / EXCEL SERIAL DATES
    # ========================================================

    numeric = pd.to_numeric(
        s,
        errors="coerce",
    )

    serial_mask = (
        result.isna()
        & numeric.notna()
        & (numeric >= 20000)
        & (numeric <= 80000)
    )

    if serial_mask.any():

        serial_result = pd.to_datetime(
            numeric.loc[serial_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

        # Important:
        # assign only valid serial dates
        valid_serial = serial_result.notna()

        if valid_serial.any():

            result.loc[
                serial_result.index[valid_serial]
            ] = serial_result.loc[
                valid_serial
            ]

    # ========================================================
    # REMOVE IMPOSSIBLE DATES
    # ========================================================

    invalid = (
        result.notna()
        & (
            (result < pd.Timestamp("2000-01-01"))
            | (
                result
                > pd.Timestamp("2100-12-31")
            )
        )
    )

    result.loc[invalid] = pd.NaT

    return result


# ============================================================
# CLEAN DATA
# ============================================================

def clean_data(
    df: pd.DataFrame,
) -> pd.DataFrame:

    df = df.copy()

    # --------------------------------------------------------
    # Remove empty rows
    # --------------------------------------------------------

    df = df.dropna(
        how="all"
    )

    # --------------------------------------------------------
    # Clean column names
    # --------------------------------------------------------

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    # --------------------------------------------------------
    # Normalize Week range
    # --------------------------------------------------------

    if "Week.1" in df.columns:

        df = df.rename(
            columns={
                "Week.1": "Week range"
            }
        )

    # ========================================================
    # TEXT CLEANING
    # ========================================================

    text_columns = df.select_dtypes(
        include=["object", "string"]
    ).columns

    for column in text_columns:

        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "": pd.NA,
                    "nan": pd.NA,
                    "NaN": pd.NA,
                    "None": pd.NA,
                    "none": pd.NA,
                }
            )
        )

    # ========================================================
    # REPORTING DATE
    # ========================================================

    if "Reporting Date" in df.columns:

        df["Reporting Date"] = (
            clean_reporting_date(
                df["Reporting Date"]
            )
        )

    # ========================================================
    # AGE
    # ========================================================

    if "Age" in df.columns:

        df["Age"] = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

    # ========================================================
    # YEAR
    # ========================================================

    if "Year" in df.columns:

        df["Year"] = pd.to_numeric(
            df["Year"],
            errors="coerce",
        ).astype("Int64")

    # ========================================================
    # MONTH
    # ========================================================

    if "Month" in df.columns:

        df["Month"] = (
            df["Month"]
            .astype("string")
            .str.strip()
        )

    # ========================================================
    # WEEK
    # ========================================================

    if "Week" in df.columns:

        df["Week"] = (
            df["Week"]
            .astype("string")
            .str.strip()
        )

    # ========================================================
    # WEEK RANGE
    # ========================================================

    if "Week range" in df.columns:

        df["Week range"] = (
            df["Week range"]
            .astype("string")
            .str.strip()
        )

    # ========================================================
    # REPAIR YEAR FROM REPORTING DATE
    # ========================================================

    if (
        "Reporting Date" in df.columns
        and "Year" in df.columns
    ):

        missing_year = (
            df["Year"].isna()
            & df["Reporting Date"].notna()
        )

        if missing_year.any():

            df.loc[
                missing_year,
                "Year"
            ] = (
                df.loc[
                    missing_year,
                    "Reporting Date"
                ]
                .dt.year
                .astype("Int64")
            )

    return df


# ============================================================
# VALIDATE COLUMNS
# ============================================================

def validate_columns(
    df: pd.DataFrame,
):

    return [
        column
        for column in EXPECTED_COLUMNS
        if column not in df.columns
    ]


# ============================================================
# REPORTING DATE VALIDATION
# ============================================================

def validate_reporting_dates(
    df: pd.DataFrame,
):

    if "Reporting Date" not in df.columns:
        return

    dates = df[
        "Reporting Date"
    ].dropna()

    if dates.empty:

        st.warning(
            "⚠️ No valid Reporting Date values found."
        )

        return

    min_date = dates.min()
    max_date = dates.max()

    st.info(
        "📅 Available reporting period: "
        f"{min_date.strftime('%d-%b-%Y')} "
        "to "
        f"{max_date.strftime('%d-%b-%Y')}"
    )


# ============================================================
# LOAD DATA
# ============================================================

def load_data() -> pd.DataFrame:

    raw_df = load_google_sheet()

    df = clean_data(
        raw_df
    )

    missing_columns = validate_columns(
        df
    )

    if missing_columns:

        st.warning(
            "Some expected columns are missing "
            "from the Google Sheet."
        )

        st.write(
            missing_columns
        )

    validate_reporting_dates(
        df
    )

    return df


# ============================================================
# REFRESH DATA
# ============================================================

def refresh_data():

    st.cache_data.clear()

    st.rerun()
