import io
import re

import pandas as pd
import requests
import streamlit as st
import pydeck as pdk


# ============================================================
# CONFIGURATION
# ============================================================

LAT_COL = "Address Latitude"
LON_COL = "Address Longitude"

GRID_SIZE = 0.005

BMC_WARD_URL = (
    "https://services8.arcgis.com/r6MmJtuWAzMawmJ8/arcgis/rest/services/"
    "BMConMaps_Nov26gdb/FeatureServer/24"
)

PROGRAMME_WARDS = [
    "A", "B", "C", "D", "E",
    "FN", "FS",
    "GN", "GS",
    "HE", "HW",
    "KE", "KW",
    "L",
    "ME", "MW",
    "N",
    "PE", "PN", "PS",
    "RC", "RN", "RS",
    "S",
    "T",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def _safe_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def _find_column(df, candidates):
    if df is None or df.empty:
        return None

    lookup = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower()
        if key in lookup:
            return lookup[key]

    return None


def _detect_disease_column(df):
    return _find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
            "Diagnosis",
            "Condition",
            "Disease/Condition",
        ],
    )


def _detect_ward_column(df):
    return _find_column(
        df,
        [
            "Ward",
            "Ward No",
            "Ward Number",
            "BMC Ward",
            "BMC_Ward",
            "Ward Name",
            "Ward_Name",
        ],
    )


def _detect_facility_column(df):
    return _find_column(
        df,
        [
            "Facility",
            "Facility Name",
            "Facility_Name",
            "Health Facility",
            "Health Facility Name",
            "Hospital",
            "Hospital Name",
            "Institution",
            "Institution Name",
        ],
    )


def _detect_case_id_column(df):
    return _find_column(
        df,
        [
            "Case ID",
            "Case_ID",
            "CaseID",
            "ID",
            "Patient ID",
            "Patient_ID",
        ],
    )


def normalize_ward(value):
    """
    Standardise BMC ward names.

    PE + PN are retained separately in the source data.
    For map display / BMC polygon matching they are combined as P.
    """

    text = _safe_text(value).upper()

    if not text:
        return ""

    text = text.replace("WARD", "")
    text = text.replace("BMC", "")
    text = text.replace("MUNICIPAL", "")
    text = text.replace(" ", "")
    text = text.replace("-", "")
    text = text.replace("_", "")

    # Common variations
    replacements = {
        "F/N": "FN",
        "F/S": "FS",
        "G/N": "GN",
        "G/S": "GS",
        "H/E": "HE",
        "H/W": "HW",
        "K/E": "KE",
        "K/W": "KW",
        "M/E": "ME",
        "M/W": "MW",
        "P/N": "PN",
        "P/S": "PS",
        "R/C": "RC",
        "R/N": "RN",
        "R/S": "RS",
    }

    if text in replacements:
        text = replacements[text]

    # Keep only known programme wards
    if text in PROGRAMME_WARDS:
        return text

    # Try regex extraction
    match = re.search(
        r"\b(FN|FS|GN|GS|HE|HW|KE|KW|ME|MW|PE|PN|PS|RC|RN|RS|A|B|C|D|E|L|N|S|T)\b",
        text,
    )

    if match:
        return match.group(1)

    return text


def display_ward(value):
    ward = normalize_ward(value)

    if ward in ("PE", "PN"):
        return "P"

    return ward


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_coordinates(df):
    """
    Prepare only valid latitude/longitude records.
    """

    if df is None:
        return pd.DataFrame()

    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    if df.empty:
        return df.copy()

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame()

    out = df.copy()

    out[LAT_COL] = pd.to_numeric(
        out[LAT_COL],
        errors="coerce",
    )

    out[LON_COL] = pd.to_numeric(
        out[LON_COL],
        errors="coerce",
    )

    out = out.dropna(
        subset=[LAT_COL, LON_COL]
    ).copy()

    out = out[
        out[LAT_COL].between(-90, 90)
        & out[LON_COL].between(-180, 180)
    ].copy()

    return out


def create_hotspots(df):
    """
    Create lightweight grid-based hotspots.

    This intentionally aggregates records before sending
    anything to the browser.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame()

    work = df[
        [LAT_COL, LON_COL]
    ].copy()

    work[LAT_COL] = pd.to_numeric(
        work[LAT_COL],
        errors="coerce",
    )

    work[LON_COL] = pd.to_numeric(
        work[LON_COL],
        errors="coerce",
    )

    work = work.dropna(
        subset=[LAT_COL, LON_COL]
    ).copy()

    if work.empty:
        return pd.DataFrame()

    work["_grid_lat"] = (
        work[LAT_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    work["_grid_lon"] = (
        work[LON_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    hotspots = (
        work.groupby(
            ["_grid_lat", "_grid_lon"],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "Cases"})
    )

    if hotspots.empty:
        return hotspots

    hotspots["Latitude"] = hotspots["_grid_lat"]
    hotspots["Longitude"] = hotspots["_grid_lon"]

    hotspots["_Cluster_ID"] = (
        hotspots["_grid_lat"].astype(str)
        + "_"
        + hotspots["_grid_lon"].astype(str)
    )

    hotspots["Hotspot Level"] = "Low"

    hotspots.loc[
        hotspots["Cases"] >= 5,
        "Hotspot Level",
    ] = "Moderate"

    hotspots.loc[
        hotspots["Cases"] >= 10,
        "Hotspot Level",
    ] = "High"

    hotspots["Radius"] = (
        45 + hotspots["Cases"] * 4
    ).clip(
        lower=45,
        upper=125,
    )

    return hotspots[
        [
            "Latitude",
            "Longitude",
            "Cases",
            "Hotspot Level",
            "Radius",
            "_Cluster_ID",
        ]
    ].copy()


def create_case_points(df):
    """
    Kept only for data compatibility / export.
    Individual points are NOT rendered on the map,
    because thousands of points create unnecessary WebGL load.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    required = [
        LAT_COL,
        LON_COL,
    ]

    for col in required:
        if col not in df.columns:
            return pd.DataFrame()

    out = df.copy()

    out[LAT_COL] = pd.to_numeric(
        out[LAT_COL],
        errors="coerce",
    )

    out[LON_COL] = pd.to_numeric(
        out[LON_COL],
        errors="coerce",
    )

    out = out.dropna(
        subset=[LAT_COL, LON_COL]
    ).copy()

    if out.empty:
        return pd.DataFrame()

    disease_col = _detect_disease_column(out)
    ward_col = _detect_ward_column(out)
    facility_col = _detect_facility_column()
