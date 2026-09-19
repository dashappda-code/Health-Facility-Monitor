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
# SAFE SINGLE DATE CONVERSION
# ============================================================

def _safe_parse_one_date(value):
    """
    Convert one date value safely.

    Supported:
    - 20-Aug-2026
    - 20-August-2026
    - 20/08/2026
    - 20-08-2026
    - 2026-08-20
    - Excel / Google serial dates

    Invalid dates -> NaT
    """

    if value is None:
        return pd.NaT

    # --------------------------------------------------------
    # Handle pandas missing values
    # --------------------------------------------------------

    try:
        if pd.isna(value):
            return pd.NaT
    except Exception:
        pass

    # --------------------------------------------------------
    # Existing Timestamp
    # --------------------------------------------------------

    if isinstance(value, pd.Timestamp):

        try:

            if (
                value < pd.Timestamp("2000-01-01")
                or value > pd.Timestamp("2100-12-31")
            ):
                return pd.NaT

            return value.normalize()

        except Exception:
            return pd.NaT

    # ========================================================
    # NUMERIC VALUE
    # ========================================================

    if isinstance(
        value,
        (
            int,
            float,
            np.integer,
            np.floating,
        ),
    ):

        try:

            number = float(value)

            # Google / Excel serial date
            if 20000 <= number <= 80000:

                # Calculate using Python datetime-like
                # conversion and immediately validate.
                parsed = pd.Timestamp(
                    "1899-12-30"
                ) + pd.to_timedelta(
                    number,
                    unit="D",
                )

                if (
                    parsed < pd.Timestamp("2000-01-01")
                    or parsed > pd.Timestamp("2100-12-31")
                ):
                    return pd.NaT

                return parsed.normalize()

            return pd.NaT

        except Exception:
            return pd.NaT

    # ========================================================
    # TEXT VALUE
    # ========================================================

    text = str(value).strip()

    if not text:
        return pd.NaT

    if text.lower() in {
        "nan",
        "nat",
        "none",
        "null",
        "na",
        "n/a",
    }:
        return pd.NaT

    # --------------------------------------------------------
    # Remove time portion where applicable
    # --------------------------------------------------------

    text = re.sub(
        r"\s+\d{1,2}:\d{2}(:\d{2})?.*$",
        "",
        text,
    ).strip()

    # ========================================================
    # EXPLICIT DATE FORMATS
    # ========================================================

    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]

    for fmt in formats:

        try:

            parsed = pd.to_datetime(
                text,
                format=fmt,
                errors="coerce",
            )

            if pd.isna(parsed):
                continue

            if (
                parsed < pd.Timestamp("2000-01-01")
                or parsed > pd.Timestamp("2100-12-31")
            ):
                return pd.NaT

            return parsed.normalize()

        except Exception:
            continue

    # ========================================================
    # FINAL FALLBACK
    # ========================================================

    try:

        parsed = pd.to_datetime(
            text,
            errors="coerce",
            dayfirst=True,
        )

        if pd.isna(parsed):
            return pd.NaT

        if (
            parsed < pd.Timestamp("2000-01-01")
            or parsed > pd.Timestamp("2100-12-31")
        ):
            return pd.NaT

        return parsed.normalize()

    except Exception:
        return pd.NaT


# ============================================================
# SAFE DATE SERIES PARSER
# ============================================================

def parse_google_date(
    series: pd.Series,
) -> pd.Series:

    # --------------------------------------------------------
    # Parse independently.
    #
    # IMPORTANT:
    # No .loc assignment into datetime64 Series.
    # This avoids the Pandas assertion error.
    # --------------------------------------------------------

    parsed_values = series.map(
        _safe_parse_one_date
    )

    # --------------------------------------------------------
    # Create a NEW Series
    # --------------------------------------------------------

    result = pd.Series(
        parsed_values.to_numpy(
            dtype=object
        ),
        index=series.index,
    )

    # --------------------------------------------------------
    # Final conversion
    # --------------------------------------------------------

    result = pd.to_datetime(
        result,
        errors="coerce",
    )

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

    # ========================================================
    # TEXT CLEANING
    # ========================================================

    text_columns = df.select_dtypes(
        include="object"
    ).columns

    for column in text_columns:

        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "nan": pd.NA,
                    "NaN": pd.NA,
                    "None": pd.NA,
                    "none": pd.NA,
                    "NULL": pd.NA,
                    "null": pd.NA,
                    "": pd.NA,
                }
            )
        )

    # ========================================================
    # REPORTING DATE
    # ========================================================

    if "Reporting Date" in df.columns:

        df["Reporting Date"] = (
            parse_google_date(
                df["Reporting Date"]
            )
        )

    # ========================================================
    # DATE OF ONSET
    # ========================================================

    if "Date Of Onset" in df.columns:

        df["Date Of Onset"] = (
            parse_google_date(
                df["Date Of Onset"]
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
            .replace(
                {
                    "nan": pd.NA,
                    "NaN": pd.NA,
                    "None": pd.NA,
                    "": pd.NA,
                }
            )
        )

    # ========================================================
    # WEEK
    # ========================================================

    if "Week" in df.columns:

        df["Week"] = (
            df["Week"]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "nan": pd.NA,
                    "NaN": pd.NA,
                    "None": pd.NA,
                    "": pd.NA,
                }
            )
        )

    # ========================================================
    # WEEK RANGE
    # ========================================================

    if "Week range" in df.columns:

        df["Week range"] = (
            df["Week range"]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "nan": pd.NA,
                    "NaN": pd.NA,
                    "None": pd.NA,
                    "": pd.NA,
                }
            )
        )

    # ========================================================
    # REPAIR YEAR FROM REPORTING DATE
    # ========================================================

    if "Reporting Date" in df.columns:

        if "Year" not in df.columns:

            df["Year"] = pd.Series(
                pd.NA,
                index=df.index,
                dtype="Int64",
            )

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

        df["Year"] = (
            df["Year"]
            .astype("Int64")
        )

    return df


# ============================================================
# VALIDATE COLUMNS
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
            "⚠️ No valid Reporting Date values were found."
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
