import re
import time
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
# GOOGLE SHEET URL → CSV URL
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

    start_time = time.time()

    csv_url = convert_to_csv_url(
        GOOGLE_SHEET_URL
    )

    st.write("🔗 Connecting to Google Sheet...")

    st.write(
        "📡 Requesting CSV data..."
    )

    try:

        response = requests.get(
            csv_url,
            timeout=(10, 30),
            headers={
                "User-Agent": "Mozilla/5.0"
            },
        )

    except requests.exceptions.ConnectTimeout:

        raise RuntimeError(
            "Google Sheet connection timed out "
            "while connecting."
        )

    except requests.exceptions.ReadTimeout:

        raise RuntimeError(
            "Google Sheet connection timed out "
            "while downloading data."
        )

    except requests.exceptions.RequestException as e:

        raise RuntimeError(
            f"Google Sheet connection failed: {e}"
        )

    download_time = time.time() - start_time

    st.write(
        f"✅ Google Sheet response received "
        f"in {download_time:.1f} seconds."
    )

    st.write(
        f"📦 Downloaded data size: "
        f"{len(response.content) / 1024 / 1024:.2f} MB"
    )

    response.raise_for_status()

    if not response.text.strip():

        raise ValueError(
            "Google Sheet returned empty data."
        )

    st.write(
        "📄 Reading CSV data..."
    )

    read_start = time.time()

    try:

        df = pd.read_csv(
            StringIO(response.text),
            low_memory=False,
        )

    except Exception as e:

        raise RuntimeError(
            f"CSV reading failed: {e}"
        )

    read_time = time.time() - read_start

    st.write(
        f"✅ CSV loaded in {read_time:.1f} seconds."
    )

    st.write(
        f"📊 Raw rows: {len(df):,}"
    )

    st.write(
        f"📊 Raw columns: {len(df.columns):,}"
    )

    return df


# ============================================================
# SAFE REPORTING DATE CLEANING
# ============================================================

def clean_reporting_date(
    series: pd.Series,
) -> pd.Series:

    s = (
        series
        .astype("string")
        .str.strip()
    )

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

    # --------------------------------------------------------
    # Numeric values
    # --------------------------------------------------------

    numeric = pd.to_numeric(
        s,
        errors="coerce",
    )

    serial_mask = (
        numeric.notna()
        & numeric.between(
            20000,
            80000,
        )
    )

    serial_dates = pd.Series(
        pd.NaT,
        index=s.index,
        dtype="datetime64[ns]",
    )

    if serial_mask.any():

        serial_dates.loc[
            serial_mask
        ] = pd.to_datetime(
            numeric.loc[serial_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

    # --------------------------------------------------------
    # Normal text dates
    # --------------------------------------------------------

    pure_numeric = s.str.fullmatch(
        r"\d+(\.\d+)?",
        na=False,
    )

    text_mask = (
        s.notna()
        & ~serial_mask
        & ~pure_numeric
    )

    text_dates = pd.Series(
        pd.NaT,
        index=s.index,
        dtype="datetime64[ns]",
    )

    if text_mask.any():

        text_dates.loc[
            text_mask
        ] = pd.to_datetime(
            s.loc[text_mask],
            format="mixed",
            dayfirst=True,
            errors="coerce",
        )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    result = text_dates.combine_first(
        serial_dates
    )

    # --------------------------------------------------------
    # Remove impossible dates
    # --------------------------------------------------------

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

    result = result.mask(
        invalid
    )

    return result


# ============================================================
# CLEAN DATA
# ============================================================

def clean_data(
    df: pd.DataFrame,
) -> pd.DataFrame:

    start_time = time.time()

    st.write(
        "🧹 Cleaning data..."
    )

    df = df.copy()

    # --------------------------------------------------------
    # Remove completely empty rows
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
    # Week range
    # --------------------------------------------------------

    if "Week.1" in df.columns:

        df = df.rename(
            columns={
                "Week.1": "Week range"
            }
        )

    # --------------------------------------------------------
    # Text columns
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Reporting Date
    # --------------------------------------------------------

    if "Reporting Date" in df.columns:

        st.write(
            "📅 Processing Reporting Date..."
        )

        df["Reporting Date"] = (
            clean_reporting_date(
                df["Reporting Date"]
            )
        )

    # --------------------------------------------------------
    # Age
    # --------------------------------------------------------

    if "Age" in df.columns:

        df["Age"] = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

    # --------------------------------------------------------
    # Year
    # --------------------------------------------------------

    if "Year" in df.columns:

        df["Year"] = pd.to_numeric(
            df["Year"],
            errors="coerce",
        ).astype("Int64")

    # --------------------------------------------------------
    # Month
    # --------------------------------------------------------

    if "Month" in df.columns:

        df["Month"] = (
            df["Month"]
            .astype("string")
            .str.strip()
        )

    # --------------------------------------------------------
    # Week
    # --------------------------------------------------------

    if "Week" in df.columns:

        df["Week"] = (
            df["Week"]
            .astype("string")
            .str.strip()
        )

    # --------------------------------------------------------
    # Week range
    # --------------------------------------------------------

    if "Week range" in df.columns:

        df["Week range"] = (
            df["Week range"]
            .astype("string")
            .str.strip()
        )

    # --------------------------------------------------------
    # Repair missing Year
    # --------------------------------------------------------

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

    clean_time = time.time() - start_time

    st.write(
        f"✅ Data cleaning completed "
        f"in {clean_time:.1f} seconds."
    )

    st.write(
        f"📊 Clean rows: {len(df):,}"
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

    dates = (
        df["Reporting Date"]
        .dropna()
    )

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
# MAIN DATA LOADER
# ============================================================

def load_data() -> pd.DataFrame:

    st.write(
        "▶️ load_data() started..."
    )

    # --------------------------------------------------------
    # Google Sheet
    # --------------------------------------------------------

    raw_df = load_google_sheet()

    st.success(
        f"✅ Google Sheet data received: "
        f"{len(raw_df):,} rows"
    )

    # --------------------------------------------------------
    # Cleaning
    # --------------------------------------------------------

    df = clean_data(
        raw_df
    )

    # --------------------------------------------------------
    # Columns
    # --------------------------------------------------------

    missing_columns = validate_columns(
        df
    )

    if missing_columns:

        st.warning(
            "⚠️ Some expected columns are missing "
            "from the Google Sheet."
        )

        st.write(
            missing_columns
        )

    # --------------------------------------------------------
    # Dates
    # --------------------------------------------------------

    validate_reporting_dates(
        df
    )

    st.success(
        f"🎉 load_data() completed successfully — "
        f"{len(df):,} records ready."
    )

    return df


# ============================================================
# REFRESH DATA
# ============================================================

def refresh_data():

    st.cache_data.clear()

    st.rerun()
