
import re
from io import StringIO

import numpy as np
import pandas as pd
import requests
import streamlit as st


# ============================================================
# GOOGLE SHEET URL
# ============================================================

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/18qfha01Czh10i4PDRUpuumtRVwbQv7Pn09jFxGSbXHg/edit?gid=1910295094#gid=1910295094"


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

def convert_to_csv_url(url):

    if "export?format=csv" in url:
        return url

    match = re.search(
        r"/spreadsheets/d/([a-zA-Z0-9-_]+)",
        url
    )

    if match:

        sheet_id = match.group(1)

        gid_match = re.search(r"[?#&]gid=(\d+)", url)
        gid = gid_match.group(1) if gid_match else None

        base = (
            f"https://docs.google.com/spreadsheets/d/"
            f"{sheet_id}/export?format=csv"
        )

        if gid:
            base += f"&gid={gid}"

        return base

    return url


# ============================================================
# LOAD GOOGLE SHEET
# ============================================================

@st.cache_data(
    ttl=60,
    show_spinner=False
)
def load_google_sheet():

    csv_url = convert_to_csv_url(
        GOOGLE_SHEET_URL
    )

    response = requests.get(
        csv_url,
        timeout=(10, 30),
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )

    response.raise_for_status()

    return pd.read_csv(
        StringIO(response.text),
        low_memory=False,
    )


# ============================================================
# FAST REPORTING DATE CLEANING
# ============================================================

def clean_reporting_date(series):

    # Keep original as string/object
    s = (
        series
        .astype("string")
        .str.strip()
    )

    result = pd.Series(
        pd.NaT,
        index=series.index,
        dtype="datetime64[ns]"
    )

    # --------------------------------------------------------
    # 1. Numeric Excel / Google serial dates
    # --------------------------------------------------------

    numeric = pd.to_numeric(
        s,
        errors="coerce"
    )

    numeric_mask = (
        numeric.notna()
        & numeric.between(
            20000,
            80000
        )
    )

    if numeric_mask.any():

        result.loc[numeric_mask] = pd.to_datetime(
            numeric.loc[numeric_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce"
        )

    # --------------------------------------------------------
    # 2. Non-numeric dates
    # --------------------------------------------------------

    text_mask = (
        s.notna()
        & ~numeric_mask
        & s.ne("")
    )

    if text_mask.any():

        text_values = s.loc[text_mask]

        # Reject obviously invalid years
        year_values = pd.to_numeric(
            text_values.str.extract(
                r"^(\d{4})[-/]",
                expand=False
            ),
            errors="coerce"
        )

        valid_text_mask = (
            year_values.isna()
            | year_values.between(
                2000,
                2100
            )
        )

        valid_index = text_values.index[
            valid_text_mask
        ]

        if len(valid_index) > 0:

            parsed = pd.to_datetime(
                text_values.loc[valid_index],
                format="mixed",
                dayfirst=True,
                errors="coerce"
            )

            # Final safety check
            valid_dates = (
                parsed.notna()
                & parsed.dt.year.between(
                    2000,
                    2100
                )
            )

            if valid_dates.any():

                result.loc[
                    parsed.index[valid_dates]
                ] = parsed.loc[
                    valid_dates
                ]

    return result


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

    age = pd.to_numeric(
        series,
        errors="coerce"
    )

    return age.where(
        age.between(
            0,
            120
        )
    )


# ============================================================
# AGE GROUP
# ============================================================

def create_age_group(age):

    if pd.isna(age):
        return "Unknown"

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
    # Column names
    # --------------------------------------------------------

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # Missing expected columns
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

        df[column] = clean_text_column(
            df[column]
        )

    # --------------------------------------------------------
    # Canonical facility / ward aliases
    # --------------------------------------------------------
    # The live sheet uses names such as "Facility Name Lform" and
    # "Ward".  Create the canonical columns expected by the dashboard
    # without destroying the original fields.

    # Live sheet -> dashboard canonical mappings
    if "Confirmed Diagnosis" in df.columns:
        disease_source = (
            df["Confirmed Diagnosis"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        current_disease = (
            df["Disease"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        df.loc[current_disease.eq(""), "Disease"] = disease_source[current_disease.eq("")]

    if "Opd Ipd" in df.columns:
        opd_source = (
            df["Opd Ipd"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        current_opd = (
            df["OPD/IPD"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        df.loc[current_opd.eq(""), "OPD/IPD"] = opd_source[current_opd.eq("")]

    if "Facility Name Lform" in df.columns:
        facility_source = (
            df["Facility Name Lform"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        current_facility = (
            df["Facility Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        df.loc[current_facility.eq(""), "Facility Name"] = facility_source[
            current_facility.eq("")
        ]

    if "Ward" in df.columns:
        ward_source = (
            df["Ward"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        current_ward = (
            df["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )
        df.loc[current_ward.eq(""), "Ward Name"] = ward_source[
            current_ward.eq("")
        ]

    # --------------------------------------------------------
    # Reporting Date
    # --------------------------------------------------------

    df["Reporting Date"] = clean_reporting_date(
        df["Reporting Date"]
    )

    # --------------------------------------------------------
    # Age
    # --------------------------------------------------------

    df["Age"] = clean_age(
        df["Age"]
    )

    # --------------------------------------------------------
    # Age Group
    # --------------------------------------------------------

    calculated_age_group = df["Age"].map(
        create_age_group
    )

    existing_age_group = (
        df["Age Group"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    empty_age_group = (
        existing_age_group == ""
    )

    df.loc[
        empty_age_group,
        "Age Group"
    ] = calculated_age_group.loc[
        empty_age_group
    ]

    # --------------------------------------------------------
    # Repair Year from Reporting Date
    # --------------------------------------------------------

    missing_year = (
        df["Year"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
    )

    if missing_year.any():

        years = (
            df.loc[
                missing_year,
                "Reporting Date"
            ]
            .dt.year
            .astype("Int64")
            .astype(str)
        )

        df.loc[
            missing_year,
            "Year"
        ] = years

    # --------------------------------------------------------
    # Remove fully empty rows
    # --------------------------------------------------------

    df = (
        df
        .dropna(how="all")
        .reset_index(drop=True)
    )

    return df


# ============================================================
# VALIDATE DATES
# ============================================================

def validate_reporting_dates(df):

    if (
        "Reporting Date" not in df.columns
        or df.empty
    ):
        return None, None

    dates = df[
        "Reporting Date"
    ].dropna()

    if dates.empty:
        return None, None

    return (
        dates.min(),
        dates.max()
    )


# ============================================================
# MAIN DATA LOADER
# ============================================================

@st.cache_data(
    ttl=60,
    show_spinner=False
)
def load_data():

    raw_df = load_google_sheet()

    if raw_df is None:
        return pd.DataFrame()

    if raw_df.empty:
        return raw_df

    return clean_data(
        raw_df
    )


# ============================================================
# REFRESH
# ============================================================

def refresh_data():

    load_google_sheet.clear()
    load_data.clear()

    return load_data()

