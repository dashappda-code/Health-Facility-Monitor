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
        StringIO(response.text)
    )


# ============================================================
# ROBUST DATE PARSER
# ============================================================

def parse_google_date(series: pd.Series) -> pd.Series:
    """
    Robust date parser for Google Sheets data.

    Handles:
    1. Normal dates:
       20-Aug-2026
       20/08/2026
       20-08-2026
       2026-08-20

    2. Excel / Google Sheets serial dates

    3. Existing datetime values

    Invalid dates become NaT.
    """

    if series is None:
        return series

    original = series.copy()

    # --------------------------------------------------------
    # Create empty datetime result
    # --------------------------------------------------------

    result = pd.Series(
        pd.NaT,
        index=series.index,
        dtype="datetime64[ns]",
    )

    # --------------------------------------------------------
    # CASE 1: Already datetime
    # --------------------------------------------------------

    datetime_mask = series.map(
        lambda x: isinstance(
            x,
            (
                pd.Timestamp,
                np.datetime64,
            ),
        )
    )

    if datetime_mask.any():

        result.loc[datetime_mask] = pd.to_datetime(
            series.loc[datetime_mask],
            errors="coerce",
        )

    # --------------------------------------------------------
    # Remaining values
    # --------------------------------------------------------

    remaining = ~datetime_mask

    if not remaining.any():
        return result

    remaining_values = series.loc[remaining]

    # --------------------------------------------------------
    # Try numeric conversion
    # --------------------------------------------------------

    numeric_values = pd.to_numeric(
        remaining_values,
        errors="coerce",
    )

    numeric_mask = numeric_values.notna()

    # --------------------------------------------------------
    # Google/Excel serial date handling
    #
    # Typical Excel/Google serial dates are around:
    # 40000 - 60000
    #
    # Example:
    # 2026 dates are approximately 46000+
    # --------------------------------------------------------

    serial_mask = (
        numeric_mask
        & (numeric_values >= 20000)
        & (numeric_values <= 80000)
    )

    if serial_mask.any():

        serial_dates = pd.to_datetime(
            numeric_values.loc[serial_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

        result.loc[
            serial_dates.index
        ] = serial_dates

    # --------------------------------------------------------
    # Remaining values are treated as text dates
    # --------------------------------------------------------

    text_mask = remaining & ~serial_mask

    if text_mask.any():

        text_values = (
            original.loc[text_mask]
            .astype(str)
            .str.strip()
        )

        # -----------------------------------------------
        # First attempt:
        # day-first
        # -----------------------------------------------

        parsed = pd.to_datetime(
            text_values,
            errors="coerce",
            dayfirst=True,
        )

        # -----------------------------------------------
        # Second attempt for values still not parsed
        # -----------------------------------------------

        failed_mask = parsed.isna()

        if failed_mask.any():

            parsed_fallback = pd.to_datetime(
                text_values.loc[failed_mask],
                errors="coerce",
                dayfirst=False,
            )

            parsed.loc[
                failed_mask
            ] = parsed_fallback

        result.loc[
            parsed.index
        ] = parsed

    # --------------------------------------------------------
    # Remove clearly invalid / unrealistic dates
    #
    # Your programme data is around 2024-2026.
    # We keep a broad safe range so future data does not break.
    # --------------------------------------------------------

    invalid_range = (
        (result < pd.Timestamp("2000-01-01"))
        | (result > pd.Timestamp("2100-12-31"))
    )

    result.loc[invalid_range] = pd.NaT

    return result


# ============================================================
# CLEAN DATA
# ============================================================

def clean_data(
    df: pd.DataFrame,
) -> pd.DataFrame:

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
    # Normalize Week range
    # --------------------------------------------------------

    if "Week.1" in df.columns:

        df = df.rename(
            columns={
                "Week.1": "Week range"
            }
        )

    # --------------------------------------------------------
    # Clean text values
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
                    "NaN": np.nan,
                    "": np.nan,
                }
            )
        )

    # ========================================================
    # ROBUST DATE CLEANING
    # ========================================================

    for column in [
        "Reporting Date",
        "Date Of Onset",
    ]:

        if column in df.columns:

            df[column] = parse_google_date(
                df[column]
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
    # MONTH CLEANING
    # ========================================================

    if "Month" in df.columns:

        df["Month"] = (
            df["Month"]
            .astype(str)
            .str.strip()
        )

        df["Month"] = df["Month"].replace(
            {
                "nan": np.nan,
                "None": np.nan,
                "NaN": np.nan,
                "": np.nan,
            }
        )

    # ========================================================
    # WEEK CLEANING
    # ========================================================

    if "Week" in df.columns:

        df["Week"] = (
            df["Week"]
            .astype(str)
            .str.strip()
        )

        df["Week"] = df["Week"].replace(
            {
                "nan": np.nan,
                "None": np.nan,
                "NaN": np.nan,
                "": np.nan,
            }
        )

    # ========================================================
    # CREATE / REPAIR YEAR FROM REPORTING DATE
    # ========================================================

    if "Reporting Date" in df.columns:

        valid_dates = df["Reporting Date"].notna()

        if "Year" not in df.columns:

            df["Year"] = pd.Series(
                pd.NA,
                index=df.index,
                dtype="Int64",
            )

        date_years = (
            df.loc[
                valid_dates,
                "Reporting Date"
            ]
            .dt.year
            .astype("Int64")
        )

        # Only fill missing Year values
        missing_year = (
            df["Year"].isna()
            & valid_dates
        )

        df.loc[
            missing_year,
            "Year"
        ] = date_years.loc[
            date_years.index.intersection(
                df.index[missing_year]
            )
        ]

        df["Year"] = df["Year"].astype("Int64")

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
# DATE VALIDATION MESSAGE
# ============================================================

def validate_reporting_dates(
    df: pd.DataFrame,
):

    if "Reporting Date" not in df.columns:
        return

    dates = df["Reporting Date"].dropna()

    if dates.empty:
        st.warning(
            "No valid Reporting Date values were found."
        )
        return

    min_date = dates.min()
    max_date = dates.max()

    st.info(
        f"📅 Available reporting period: "
        f"{min_date.strftime('%d-%b-%Y')} "
        f"to "
        f"{max_date.strftime('%d-%b-%Y')}"
    )


# ============================================================
# LOAD + CLEAN + VALIDATE
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

    # --------------------------------------------------------
    # Reporting Date validation
    # --------------------------------------------------------

    validate_reporting_dates(
        df
    )

    return df


# ============================================================
# REFRESH FUNCTION
# ============================================================

def refresh_data():

    st.cache_data.clear()

    st.rerun()
