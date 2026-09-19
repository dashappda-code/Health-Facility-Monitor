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
# FAST + SAFE DATE PARSER
# ============================================================

def parse_google_date(
    series: pd.Series,
) -> pd.Series:

    # --------------------------------------------------------
    # Preserve original series index
    # --------------------------------------------------------

    original_index = series.index

    # --------------------------------------------------------
    # Convert values to string
    # --------------------------------------------------------

    text = (
        series.astype("string")
        .str.strip()
    )

    # --------------------------------------------------------
    # Normalize empty values
    # --------------------------------------------------------

    text = text.replace(
        {
            "": pd.NA,
            "nan": pd.NA,
            "NaN": pd.NA,
            "None": pd.NA,
            "none": pd.NA,
            "NULL": pd.NA,
            "null": pd.NA,
            "NaT": pd.NA,
        }
    )

    # --------------------------------------------------------
    # Empty result
    # --------------------------------------------------------

    result = pd.Series(
        pd.NaT,
        index=original_index,
        dtype="datetime64[ns]",
    )

    # ========================================================
    # 1. NUMERIC / GOOGLE SHEETS SERIAL DATES
    # ========================================================

    numeric = pd.to_numeric(
        text,
        errors="coerce",
    )

    serial_mask = (
        numeric.notna()
        & (numeric >= 20000)
        & (numeric <= 80000)
    )

    if serial_mask.any():

        serial_dates = pd.to_datetime(
            numeric.loc[serial_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

        result.loc[
            serial_dates.index
        ] = serial_dates

    # ========================================================
    # 2. TEXT DATE VALUES
    # ========================================================

    text_mask = (
        text.notna()
        & ~serial_mask
    )

    if text_mask.any():

        text_values = text.loc[
            text_mask
        ]

        parsed = pd.Series(
            pd.NaT,
            index=text_values.index,
            dtype="datetime64[ns]",
        )

        # ----------------------------------------------------
        # DD-MM-YYYY
        # ----------------------------------------------------

        mask = text_values.str.match(
            r"^\d{1,2}-\d{1,2}-\d{4}$",
            na=False,
        )

        if mask.any():

            parsed.loc[mask] = pd.to_datetime(
                text_values.loc[mask],
                format="%d-%m-%Y",
                errors="coerce",
            )

        # ----------------------------------------------------
        # DD/MM/YYYY
        # ----------------------------------------------------

        mask = (
            parsed.isna()
            & text_values.str.match(
                r"^\d{1,2}/\d{1,2}/\d{4}$",
                na=False,
            )
        )

        if mask.any():

            parsed.loc[mask] = pd.to_datetime(
                text_values.loc[mask],
                format="%d/%m/%Y",
                errors="coerce",
            )

        # ----------------------------------------------------
        # YYYY-MM-DD
        # ----------------------------------------------------

        mask = (
            parsed.isna()
            & text_values.str.match(
                r"^\d{4}-\d{1,2}-\d{1,2}$",
                na=False,
            )
        )

        if mask.any():

            parsed.loc[mask] = pd.to_datetime(
                text_values.loc[mask],
                format="%Y-%m-%d",
                errors="coerce",
            )

        # ----------------------------------------------------
        # DD-Mon-YYYY
        # Example: 20-Aug-2026
        # ----------------------------------------------------

        mask = (
            parsed.isna()
            & text_values.str.match(
                r"^\d{1,2}-[A-Za-z]{3}-\d{4}$",
                na=False,
            )
        )

        if mask.any():

            parsed.loc[mask] = pd.to_datetime(
                text_values.loc[mask],
                format="%d-%b-%Y",
                errors="coerce",
            )

        # ----------------------------------------------------
        # DD-Month-YYYY
        # Example: 20-August-2026
        # ----------------------------------------------------

        mask = (
            parsed.isna()
            & text_values.str.match(
                r"^\d{1,2}-[A-Za-z]+-\d{4}$",
                na=False,
            )
        )

        if mask.any():

            parsed.loc[mask] = pd.to_datetime(
                text_values.loc[mask],
                format="%d-%B-%Y",
                errors="coerce",
            )

        # ----------------------------------------------------
        # FINAL FALLBACK
        # ----------------------------------------------------

        remaining = parsed.isna()

        if remaining.any():

            fallback = pd.to_datetime(
                text_values.loc[remaining],
                errors="coerce",
                dayfirst=True,
            )

            parsed.loc[
                fallback.index
            ] = fallback

        # ----------------------------------------------------
        # Put parsed values into result
        # ----------------------------------------------------

        result.loc[
            parsed.index
        ] = parsed

    # ========================================================
    # 3. REMOVE UNREALISTIC DATES
    # ========================================================

    invalid_mask = (
        result.notna()
        & (
            (result < pd.Timestamp("2000-01-01"))
            | (
                result
                > pd.Timestamp("2100-12-31")
            )
        )
    )

    result.loc[
        invalid_mask
    ] = pd.NaT

    # --------------------------------------------------------
    # Final datetime conversion
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
    # CLEAN TEXT COLUMNS
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

        valid_dates = (
            df["Reporting Date"].notna()
        )

        # Create Year if missing
        if "Year" not in df.columns:

            df["Year"] = pd.Series(
                pd.NA,
                index=df.index,
                dtype="Int64",
            )

        # Fill only missing Year
        missing_year = (
            df["Year"].isna()
            & valid_dates
        )

        if missing_year.any():

            derived_year = (
                df.loc[
                    missing_year,
                    "Reporting Date"
                ]
                .dt.year
                .astype("Int64")
            )

            df.loc[
                missing_year,
                "Year"
            ] = derived_year

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

    # --------------------------------------------------------
    # Validate Reporting Date
    # --------------------------------------------------------

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
