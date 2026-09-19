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

    start_time = time.time()

    csv_url = convert_to_csv_url(
        GOOGLE_SHEET_URL
    )

    st.write(
        "🔗 Connecting to Google Sheet..."
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
            "Google Sheet connection timed out."
        )

    except requests.exceptions.ReadTimeout:

        raise RuntimeError(
            "Google Sheet download timed out."
        )

    except requests.exceptions.RequestException as e:

        raise RuntimeError(
            f"Google Sheet connection failed: {e}"
        )

    response.raise_for_status()

    if not response.text.strip():

        raise ValueError(
            "Google Sheet returned empty data."
        )

    download_time = time.time() - start_time

    st.write(
        f"✅ Google Sheet downloaded "
        f"in {download_time:.1f} seconds."
    )

    st.write(
        f"📦 File size: "
        f"{len(response.content) / 1024 / 1024:.2f} MB"
    )

    st.write(
        "📄 Reading CSV..."
    )

    read_start = time.time()

    df = pd.read_csv(
        StringIO(response.text),
        low_memory=False,
    )

    read_time = time.time() - read_start

    st.write(
        f"✅ CSV loaded in {read_time:.1f} seconds."
    )

    st.write(
        f"📊 Raw records: {len(df):,}"
    )

    return df


# ============================================================
# SAFE DATE PARSER
# ============================================================

def _safe_parse_date(value):
    """
    Parse one date value safely.

    Invalid values such as:
        4438
        4438-05-27
        6101-...
    are rejected.

    Valid reporting dates are restricted to:
        2000-01-01 through 2100-12-31
    """

    # --------------------------------------------------------
    # Missing value
    # --------------------------------------------------------

    if value is None:
        return pd.NaT

    try:

        if pd.isna(value):
            return pd.NaT

    except Exception:

        pass

    # --------------------------------------------------------
    # Convert to string
    # --------------------------------------------------------

    value_str = str(value).strip()

    if value_str == "":
        return pd.NaT

    lower_value = value_str.lower()

    if lower_value in {
        "nan",
        "none",
        "null",
        "nat",
        "na",
        "n/a",
    }:

        return pd.NaT

    # --------------------------------------------------------
    # Pure numeric values
    # --------------------------------------------------------

    numeric_value = None

    try:

        numeric_value = float(value_str)

    except (ValueError, TypeError):

        numeric_value = None

    if numeric_value is not None:

        # -----------------------------------------------
        # Google / Excel serial date
        # -----------------------------------------------

        if 20000 <= numeric_value <= 80000:

            try:

                parsed = (
                    pd.Timestamp(
                        "1899-12-30"
                    )
                    + pd.to_timedelta(
                        numeric_value,
                        unit="D",
                    )
                )

                if (
                    parsed >= pd.Timestamp(
                        "2000-01-01"
                    )
                    and parsed <= pd.Timestamp(
                        "2100-12-31"
                    )
                ):

                    return parsed

            except Exception:

                return pd.NaT

        # -----------------------------------------------
        # Numeric but NOT a valid serial date
        #
        # Example:
        # 4438
        # -----------------------------------------------

        return pd.NaT

    # --------------------------------------------------------
    # Explicitly reject obviously impossible years
    # --------------------------------------------------------

    year_match = re.match(
        r"^\s*(\d{4})[-/]",
        value_str,
    )

    if year_match:

        year = int(
            year_match.group(1)
        )

        if year < 2000 or year > 2100:

            return pd.NaT

    # --------------------------------------------------------
    # Try normal date parsing
    # --------------------------------------------------------

    try:

        parsed = pd.to_datetime(
            value_str,
            format="mixed",
            dayfirst=True,
            errors="coerce",
        )

    except Exception:

        return pd.NaT

    # --------------------------------------------------------
    # Final validation
    # --------------------------------------------------------

    if pd.isna(parsed):

        return pd.NaT

    try:

        parsed = pd.Timestamp(
            parsed
        )

    except Exception:

        return pd.NaT

    if (
        parsed < pd.Timestamp(
            "2000-01-01"
        )
        or parsed > pd.Timestamp(
            "2100-12-31"
        )
    ):

        return pd.NaT

    return parsed


# ============================================================
# REPORTING DATE CLEANING
# ============================================================

def clean_reporting_date(
    series: pd.Series,
) -> pd.Series:

    st.write(
        "📅 Cleaning Reporting Date..."
    )

    start_time = time.time()

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Do NOT create datetime64 Series and assign values into it.
    #
    # We first create Python objects.
    # This avoids the pandas 3.x / Python 3.14
    # OutOfBoundsDatetime assignment problem.
    # --------------------------------------------------------

    parsed_values = []

    invalid_count = 0
    valid_count = 0

    for value in series:

        parsed = _safe_parse_date(
            value
        )

        parsed_values.append(
            parsed
        )

        if pd.isna(parsed):

            invalid_count += 1

        else:

            valid_count += 1

    # --------------------------------------------------------
    # Convert ONLY validated values to datetime
    # --------------------------------------------------------

    result = pd.Series(
        parsed_values,
        index=series.index,
        dtype="datetime64[ns]",
    )

    elapsed = time.time() - start_time

    st.write(
        f"✅ Reporting Date processed "
        f"in {elapsed:.1f} seconds."
    )

    st.write(
        f"📅 Valid dates: {valid_count:,}"
    )

    st.write(
        f"⚠️ Invalid / blank dates: {invalid_count:,}"
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
        "🧹 Starting data cleaning..."
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
        include=[
            "object",
            "string",
        ]
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
                    "NULL": pd.NA,
                    "null": pd.NA,
                }
            )
        )

    # --------------------------------------------------------
    # Reporting Date
    # --------------------------------------------------------

    if "Reporting Date" in df.columns:

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
    # Repair Year from Reporting Date
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

            years = (
                df.loc[
                    missing_year,
                    "Reporting Date",
                ]
                .dt.year
                .astype("Int64")
            )

            df.loc[
                missing_year,
                "Year",
            ] = years

    elapsed = time.time() - start_time

    st.write(
        f"✅ Data cleaning completed "
        f"in {elapsed:.1f} seconds."
    )

    st.write(
        f"📊 Clean records: {len(df):,}"
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
# MAIN LOAD DATA
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
        f"{len(raw_df):,} records."
    )

    # --------------------------------------------------------
    # Cleaning
    # --------------------------------------------------------

    df = clean_data(
        raw_df
    )

    # --------------------------------------------------------
    # Validate columns
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
    # Validate dates
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
