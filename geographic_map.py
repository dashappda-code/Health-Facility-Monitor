import io
import re

import pandas as pd
import requests
import streamlit as st
import pydeck as pdk


# ============================================================
# CONFIG
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
    "FN", "FS", "GN", "GS",
    "HE", "HW",
    "KE", "KW",
    "L",
    "ME", "MW",
    "N",
    "PE", "PN", "PS",
    "RC", "RN", "RS",
    "S", "T"
]


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()

    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = re.sub(r"\s+", " ", text)

    return text


def find_column(df, candidates):
    if df is None or df.empty:
        return None

    columns = {str(c).strip().lower(): c for c in df.columns}

    for candidate in candidates:
        key = str(candidate).strip().lower()

        if key in columns:
            return columns[key]

    for column in df.columns:
        column_text = str(column).strip().lower()

        for candidate in candidates:
            candidate_text = str(candidate).strip().lower()

            if candidate_text in column_text:
                return column

    return None


# ============================================================
# WARD NORMALISATION
# ============================================================

def normalise_ward(value):
    text = clean_text(value).upper()

    if not text:
        return ""

    text = text.replace("&", "AND")
    text = text.replace("-", " ")
    text = text.replace("_", " ")
    text = text.replace("/", " ")
    text = text.replace("\\", " ")
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = re.sub(r"\s+", " ", text).strip()

    compact = text.replace(" ", "")

    # Exact programme ward
    if compact in PROGRAMME_WARDS:
        return compact

    # Common direct forms
    direct_map = {
        "A WARD": "A",
        "B WARD": "B",
        "C WARD": "C",
        "D WARD": "D",
        "E WARD": "E",

        "F NORTH": "FN",
        "F NORTH WARD": "FN",
        "FNORTH": "FN",
        "FNORTHWARD": "FN",

        "F SOUTH": "FS",
        "F SOUTH WARD": "FS",
        "FSOUTH": "FS",
        "FSOUTHWARD": "FS",

        "G NORTH": "GN",
        "G NORTH WARD": "GN",
        "GNORTH": "GN",
        "GNORTHWARD": "GN",

        "G SOUTH": "GS",
        "G SOUTH WARD": "GS",
        "GSOUTH": "GS",
        "GSOUTHWARD": "GS",

        "H EAST": "HE",
        "H EAST WARD": "HE",
        "HEAST": "HE",
        "HEASTWARD": "HE",

        "H WEST": "HW",
        "H WEST WARD": "HW",
        "HWEST": "HW",
        "HWESTWARD": "HW",

        "K EAST": "KE",
        "K EAST WARD": "KE",
        "KEAST": "KE",
        "KEASTWARD": "KE",

        "K WEST": "KW",
        "K WEST WARD": "KW",
        "KWEST": "KW",
        "KWESTWARD": "KW",

        "M EAST": "ME",
        "M EAST WARD": "ME",
        "MEAST": "ME",
        "MEASTWARD": "ME",

        "M WEST": "MW",
        "M WEST WARD": "MW",
        "MWEST": "MW",
        "MWESTWARD": "MW",

        "P EAST": "PE",
        "P EAST WARD": "PE",
        "PEAST": "PE",
        "PEASTWARD": "PE",

        "P NORTH": "PN",
        "P NORTH WARD": "PN",
        "PNORTH": "PN",
        "PNORTHWARD": "PN",

        "P SOUTH": "PS",
        "P SOUTH WARD": "PS",
        "PSOUTH": "PS",
        "PSOUTHWARD": "PS",

        "R CENTRAL": "RC",
        "R CENTRAL WARD": "RC",
        "RCENTRAL": "RC",
        "RCENTRALWARD": "RC",

        "R NORTH": "RN",
        "R NORTH WARD": "RN",
        "RNORTH": "RN",
        "RNORTHWARD": "RN",

        "R SOUTH": "RS",
        "R SOUTH WARD": "RS",
        "RSOUTH": "RS",
        "RSOUTHWARD": "RS",
    }

    if text in direct_map:
        return direct_map[text]

    if compact in direct_map:
        return direct_map[compact]

    # Remove generic words and retry
    cleaned = re.sub(r"\bWARD\b", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    compact_cleaned = cleaned.replace(" ", "")

    if compact_cleaned in PROGRAMME_WARDS:
        return compact_cleaned

    if cleaned in direct_map:
        return direct_map[cleaned]

    if compact_cleaned in direct_map:
        return direct_map[compact_cleaned]

    # Token based matching
    tokens = cleaned.split()

    if len(tokens) >= 2:
        first = tokens[0]
        second = tokens[1]

        pair = f"{first}{second}"

        if pair in PROGRAMME_WARDS:
            return pair

    # Explicit pattern matching
    patterns = [
        (r"\bF\s*N(?:ORTH)?\b", "FN"),
        (r"\bF\s*S(?:OUTH)?\b", "FS"),
        (r"\bG\s*N(?:ORTH)?\b", "GN"),
        (r"\bG\s*S(?:OUTH)?\b", "GS"),
        (r"\bH\s*E(?:AST)?\b", "HE"),
        (r"\bH\s*W(?:EST)?\b", "HW"),
        (r"\bK\s*E(?:AST)?\b", "KE"),
        (r"\bK\s*W(?:EST)?\b", "KW"),
        (r"\bM\s*E(?:AST)?\b", "ME"),
        (r"\bM\s*W(?:EST)?\b", "MW"),
        (r"\bP\s*E(?:AST)?\b", "PE"),
        (r"\bP\s*N(?:ORTH)?\b", "PN"),
        (r"\bP\s*S(?:OUTH)?\b", "PS"),
        (r"\bR\s*C(?:ENTRAL)?\b", "RC"),
        (r"\bR\s*N(?:ORTH)?\b", "RN"),
        (r"\bR\s*S(?:OUTH)?\b", "RS"),
    ]

    for pattern, ward in patterns:
        if re.search(pattern, text):
            return ward

    # Single letter wards
    if compact_cleaned in ["A", "B", "C", "D", "E"]:
        return compact_cleaned

    # Direct compact fallback
    if compact in PROGRAMME_WARDS:
        return compact

    return ""


# ============================================================
# COLUMN HELPERS
# ============================================================

def get_disease_column(df):
    return find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
            "DiseaseName",
            "Diagnosis",
            "Disease Type",
        ],
    )


def get_ward_column(df):
    return find_column(
        df,
        [
            "_Report_Ward",
            "Report Ward",
            "Ward",
            "Ward Name",
            "Ward_Name",
            "BMC Ward",
            "BMC_Ward",
        ],
    )


def get_facility_column(df):
    return find_column(
        df,
        [
            "Facility",
            "Facility Name",
            "Facility_Name",
            "Health Facility",
            "Health Facility Name",
            "Hospital",
            "Hospital Name",
        ],
    )


def get_case_id_column(df):
    return find_column(
        df,
        [
            "Case ID",
            "Case_ID",
            "CaseID",
            "ID",
            "Sr No",
            "Sr. No",
        ],
    )


# ============================================================
# COORDINATES
# ============================================================

def prepare_coordinates(df):
    if df is None or df.empty:
        return pd.DataFrame()

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame()

    work = df.copy()

    work[LAT_COL] = pd.to_numeric(
        work[LAT_COL],
        errors="coerce"
    )

    work[LON_COL] = pd.to_numeric(
        work[LON_COL],
        errors="coerce"
    )

    work = work.dropna(
        subset=[LAT_COL, LON_COL]
    ).copy()

    work = work[
        work[LAT_COL].between(-90, 90)
        & work[LON_COL].between(-180, 180)
    ].copy()

    return work


def coordinate_availability_text(df):
    coordinate_df = prepare_coordinates(df)

    if coordinate_df.empty:
        return "No valid latitude/longitude coordinates available."

    return (
        f"{len(coordinate_df):,} records have valid coordinates "
        f"and are available for geographic mapping."
    )


# ============================================================
# HOTSPOTS
# ============================================================

def create_hotspots(df):
    coordinate_df = prepare_coordinates(df)

    if coordinate_df.empty:
        return pd.DataFrame()

    work = coordinate_df.copy()

    work["_grid_lat"] = (
        work[LAT_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    work["_grid_lon"] = (
        work[LON_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    work["_Cluster_ID"] = (
        work["_grid_lat"].round(5).astype(str)
        + "_"
        + work["_grid_lon"].round(5).astype(str)
    )

    hotspots = (
        work.groupby("_Cluster_ID", as_index=False)
        .agg(
            Latitude=(LAT_COL, "mean"),
            Longitude=(LON_COL, "mean"),
            Cluster_Cases=(LAT_COL, "size"),
        )
    )

    hotspots["Hotspot_Level"] = "Low"

    hotspots.loc[
        hotspots["Cluster_Cases"] >= 5,
        "Hotspot_Level"
    ] = "Moderate"

    hotspots.loc[
        hotspots["Cluster_Cases"] >= 10,
        "Hotspot_Level"
    ] = "High"

    hotspots["Display_Radius"] = (
        45 + hotspots["Cluster_Cases"] * 4
    )

    hotspots["Display_Radius"] = (
        hotspots["Display_Radius"]
        .clip(lower=45, upper=125)
        .astype(float)
    )

    return hotspots


# ============================================================
# CASE POINTS
# ============================================================

def create_case_points(df, hotspots=None):
    coordinate_df = prepare_coordinates(df)

    if coordinate_df.empty:
        return pd.DataFrame()

    disease_col = get_disease_column(coordinate_df)
    ward_col = get_ward_column(coordinate_df)
    facility_col = get_facility_column(coordinate_df)
    case_id_col = get_case_id_column(coordinate_df)

    work = coordinate_df.copy()

    if disease_col:
        work["Disease"] = (
            work[disease_col]
            .map(clean_text)
        )
    else:
        work["Disease"] = "Unknown"

    if ward_col:
        work["Ward"] = (
            work[ward_col]
            .map(normalise_ward)
        )
    else:
        work["Ward"] = ""

    if facility_col:
        work["Facility"] = (
            work[facility_col]
            .map(clean_text)
        )
    else:
        work["Facility"] = ""

    if case_id_col:
        work["Case_ID"] = (
            work[case_id_col]
            .map(clean_text)
        )
    else:
        work["Case_ID"] = (
            work.index.astype(str)
        )

    work["_grid_lat"] = (
        work[LAT_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    work["_grid_lon"] = (
        work[LON_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    work["Cluster_ID"] = (
        work["_grid_lat"].round(5).astype(str)
        + "_"
        + work["_grid_lon"].round(5).astype(str)
    )

    if hotspots is not None and not hotspots.empty:
        hotspot_lookup = dict(
            zip(
                hotspots["_Cluster_ID"],
                hotspots["Cluster_Cases"]
            )
        )

        work["Cluster_Cases"] = (
            work["Cluster_ID"]
            .map(hotspot_lookup)
            .fillna(0)
            .astype(int)
        )
    else:
        work["Cluster_Cases"] = 0

    work["PN_Hotspot"] = (
        (work["Ward"] == "PN")
        & (work["Cluster_Cases"] >= 5)
    )

    work["Point_Radius"] = 28.0

    work.loc[
        work["PN_Hotspot"],
        "Point_Radius"
    ] = 65.0

    result = work[
        [
            LAT_COL,
            LON_COL,
            "Ward",
            "Disease",
            "Facility",
            "Case_ID",
            "Cluster_ID",
            "Cluster_Cases",
            "Hotspot_Level"
            if "Hotspot_Level" in work.columns
            else "Cluster_Cases",
            "PN_Hotspot",
            "Point_Radius",
        ]
    ].copy()

    if "Hotspot_Level" not in result.columns:
        result["Hotspot_Level"] = result["Cluster_Cases"].apply(
            lambda x: (
                "High"
                if x >= 10
                else "Moderate"
                if x >= 5
                else "Low"
            )
        )

    return result


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):
    if df is None or df.empty:
        return pd.DataFrame(
            {
                "Ward": PROGRAMME_WARDS,
                "Cases": [0] * len(PROGRAMME_WARDS),
            }
        )

    work = df.copy()

    ward_col = get_ward_column(work)

    if ward_col is None:
        return pd.DataFrame(
            {
                "Ward": PROGRAMME_WARDS,
                "Cases": [0] * len(PROGRAMME_WARDS),
            }
        )

    work["_Mapped_Ward"] = (
        work[ward_col]
        .map(normalise_ward)
    )

    counts = (
        work["_Mapped_Ward"]
        .value_counts()
        .to_dict()
    )

    summary = pd.DataFrame(
        {
            "Ward": PROGRAMME_WARDS,
            "Cases": [
                int(counts.get(ward, 0))
                for ward in PROGRAMME_WARDS
            ],
        }
    )

    return summary


# ============================================================
# MAP WARD SUMMARY
# PE + PN = P FOR CHOROPLETH
# ============================================================

def create_map_ward_summary(ward_summary):
    if ward_summary is None or ward_summary.empty:
        return pd.DataFrame(
            {
                "Ward": [],
                "Cases": [],
            }
        )

    summary = ward_summary.copy()

    pe_cases = int(
        summary.loc[
            summary["Ward"] == "PE",
            "Cases"
        ].sum()
    )

    pn_cases = int(
        summary.loc[
            summary["Ward"] == "PN",
            "Cases"
        ].sum()
    )

    summary = summary[
        ~summary["Ward"].isin(["PE", "PN"])
    ].copy()

    p_cases = pe_cases + pn_cases

    p_row = pd.DataFrame(
        {
            "Ward": ["P"],
            "Cases": [p_cases],
        }
    )

    summary = pd.concat(
        [
            summary,
            p_row,
        ],
        ignore_index=True,
    )

    return summary


# ============================================================
# BMC GEOJSON
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def load_bmc_wards():
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "geojson",
    }

    try:
        response = requests.get(
            BMC_WARD_URL + "/query",
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        if (
            isinstance(data, dict)
            and data.get("type") == "FeatureCollection"
        ):
            return data

    except Exception:
        return None

    return None


# ============================================================
# ROBUST GEOJSON WARD DETECTION
# ============================================================

def get_geojson_ward_name(properties):
    if not isinstance(properties, dict):
        return ""

    preferred_keys = [
        "WARD",
        "Ward",
        "ward",
        "WARD_NAME",
        "Ward_Name",
        "WardName",
        "WARDNAME",
        "NAME",
        "Name",
        "name",
        "M_WARD",
        "M_WARD_NAME",
        "WARD_NO",
        "Ward_No",
        "WARDNUMBER",
        "WardNumber",
    ]

    # First check preferred fields
    for key in preferred_keys:
        if key in properties:
            value = properties.get(key)

            ward = normalise_ward(value)

            if ward:
                return ward

    # Then inspect other likely ward/name fields
    for key, value in properties.items():
        key_text = str(key).upper()

        if (
            "WARD" in key_text
            or "NAME" in key_text
            or "ZONE" in key_text
        ):
            ward = normalise_ward(value)

            if ward:
                return ward

    # Last controlled fallback:
    # only inspect short text values
    for value in properties.values():
        text = clean_text(value)

        if not text:
            continue

        if len(text) > 50:
            continue

        ward = normalise_ward(text)

        if ward:
            return ward

    return ""


def prepare_bmc_choropleth(geojson, ward_summary, disease_name=None):
    if not geojson:
        return None

    if ward_summary is None or ward_summary.empty:
        return None

    work = ward_summary.copy()

    # PE + PN are combined only for choropleth
    map_summary = create_map_ward_summary(work)

    ward_cases = dict(
        zip(
            map_summary["Ward"],
            map_summary["Cases"]
        )
    )

    max_cases = (
        int(map_summary["Cases"].max())
        if not map_summary.empty
        else 0
    )

    # --------------------------------------------------------
    # Disease-specific palette
    # --------------------------------------------------------

    palette = get_disease_palette(disease_name)

    features = []

    canonical_p_feature = None
    canonical_pn_feature = None
    canonical_pe_feature = None

    for feature in geojson.get("features", []):
        properties = feature.get("properties", {})

        ward = get_geojson_ward_name(
            properties
        )

        if ward == "P":
            canonical_p_feature = feature

        elif ward == "PN":
            canonical_pn_feature = feature

        elif ward == "PE":
            canonical_pe_feature = feature

    # --------------------------------------------------------
    # Process every feature
    # --------------------------------------------------------

    for feature in geojson.get("features", []):
        new_feature = dict(feature)

        properties = dict(
            feature.get("properties", {})
        )

        detected_ward = get_geojson_ward_name(
            properties
        )

        # ----------------------------------------------------
        # PE / PN temporary combined choropleth handling
        # ----------------------------------------------------

        map_ward = detected_ward

        if detected_ward in ["PE", "PN"]:
            map_ward = "P"

        # If actual P boundary exists, use P.
        # PE/PN polygons remain neutral because P is represented
        # by the canonical P polygon.
        if detected_ward in ["PE", "PN"]:
            if canonical_p_feature is not None:
                map_ward = detected_ward
            else:
                map_ward = "P"

        cases = int(
            ward_cases.get(map_ward, 0)
        )

        # If this is PE/PN and there is no canonical P boundary,
        # allow one of them to represent the combined P area.
        if (
            detected_ward in ["PE", "PN"]
            and canonical_p_feature is None
        ):
            cases = int(
                ward_cases.get("P", 0)
            )

        # If canonical P exists, PE/PN polygons should not
        # duplicate the P burden.
        if (
            detected_ward in ["PE", "PN"]
            and canonical_p_feature is not None
        ):
            cases = 0

        properties["ProgrammeWard"] = (
            detected_ward
            if detected_ward
            else "Unmatched"
        )

        properties["MapWard"] = map_ward
        properties["ProgrammeCases"] = cases

        properties["WardDisplay"] = (
            f"{detected_ward or 'Unmatched'}"
            f" | Cases: {cases:,}"
        )

        properties["Disease"] = (
            clean_text(disease_name)
            if disease_name
            else "Combined"
        )

        properties["fill_color"] = get_choropleth_color(
            cases,
            max_cases,
            palette,
        )

        properties["line_color"] = [
            70,
            70,
            70,
            220,
        ]

        new_feature["properties"] = properties

        features.append(new_feature)

    # --------------------------------------------------------
    # If there is no P polygon, make the PN/PE representation
    # carry the combined P burden.
    # --------------------------------------------------------

    if canonical_p_feature is None:
        p_represented = False

        for feature in features:
            properties = feature.get(
                "properties",
                {}
            )

            ward = properties.get(
                "ProgrammeWard",
                ""
            )

            if ward in ["PN", "PE"]:
                properties["ProgrammeCases"] = int(
                    ward_cases.get("P", 0)
                )

                properties["WardDisplay"] = (
                    f"{ward} / P"
                    f" | Cases: "
                    f"{int(ward_cases.get('P', 0)):,}"
                )

                properties["fill_color"] = (
                    get_choropleth_color(
                        int(ward_cases.get("P", 0)),
                        max_cases,
                        palette,
                    )
                )

                p_represented = True

                if p_represented:
                    break

    return {
        "type": "FeatureCollection",
        "features": features,
    }


# ============================================================
# DISEASE PALETTES
# ============================================================

DISEASE_PALETTES = [
    {
        "name": "Blue",
        "light": [222, 235, 247],
        "mid": [107, 174, 214],
        "dark": [8, 48, 107],
    },
    {
        "name": "Green",
        "light": [229, 245, 224],
        "mid": [116, 196, 118],
        "dark": [0, 68, 27],
    },
    {
        "name": "Purple",
        "light": [239, 237, 245],
        "mid": [158, 154, 200],
        "dark": [63, 0, 125],
    },
    {
        "name": "Orange",
        "light": [254, 230, 206],
        "mid": [253, 141, 60],
        "dark": [127, 39, 4],
    },
    {
        "name": "Teal",
        "light": [224, 243, 219],
        "mid": [102, 194, 165],
        "dark": [0, 77, 64],
    },
    {
        "name": "Red",
        "light": [254, 224, 210],
        "mid": [239, 138, 98],
        "dark": [103, 0, 13],
    },
    {
        "name": "Magenta",
        "light": [241, 238, 246],
        "mid": [175, 141, 195],
        "dark": [80, 3, 102],
    },
    {
        "name": "Olive",
        "light": [247, 247, 187],
        "mid": [189, 189, 0],
        "dark": [85, 85, 0],
    },
]


def get_disease_palette(disease_name=None):
    if not disease_name:
        return DISEASE_PALETTES[0]

    text = clean_text(
        disease_name
    ).lower()

    total = 0

    for char in text:
        total += ord(char)

    index = total % len(
        DISEASE_PALETTES
    )

    return DISEASE_PALETTES[index]


def get_choropleth_color(
    cases,
    max_cases,
    palette=None,
):
    if palette is None:
        palette = DISEASE_PALETTES[0]

    cases = int(cases or 0)
    max_cases = int(max_cases or 0)

    if cases <= 0:
        return [
            245,
            245,
            245,
            80,
        ]

    if max_cases <= 0:
        return [
            245,
            245,
            245,
            80,
        ]

    ratio = cases / max_cases

    ratio = max(
        0.0,
        min(1.0, ratio)
    )

    light = palette["light"]
    mid = palette["mid"]
    dark = palette["dark"]

    if ratio <= 0.5:
        local_ratio = ratio / 0.5

        rgb = [
            int(
                light[i]
                + (mid[i] - light[i])
                * local_ratio
            )
            for i in range(3)
        ]

    else:
        local_ratio = (
            ratio - 0.5
        ) / 0.5

        rgb = [
            int(
                mid[i]
                + (dark[i] - mid[i])
                * local_ratio
            )
            for i in range(3)
        ]

    return [
        rgb[0],
        rgb[1],
        rgb[2],
        170,
    ]


# ============================================================
# DISEASE SELECTION
# ============================================================

def disease_selection_control(diseases):
    diseases = [
        clean_text(d)
        for d in diseases
        if clean_text(d)
    ]

    diseases = list(
        dict.fromkeys(diseases)
    )

    if not diseases:
        return []

    current_options_signature = "|".join(
        diseases
    )

    previous_signature = st.session_state.get(
        "geo_disease_options_signature"
    )

    if (
        previous_signature
        != current_options_signature
    ):
        st.session_state[
            "geo_disease_options_signature"
        ] = current_options_signature

        st.session_state[
            "geo_disease_selection"
        ] = []

    selection_options = [
        "Select All"
    ] + diseases

    current_selection = st.session_state.get(
        "geo_disease_selection",
        []
    )

    current_selection = [
        item
        for item in current_selection
        if item in selection_options
    ]

    st.session_state[
        "geo_disease_selection"
    ] = current_selection

    selected = st.multiselect(
        "Disease Selection",
        options=selection_options,
        key="geo_disease_selection",
        placeholder="All diseases (default)",
        help=(
            "Leave empty for all diseases. "
            "Use Select All or select one or more diseases."
        ),
    )

    if "Select All" in selected:
        return diseases

    if not selected:
        return diseases

    return selected


# ============================================================
# MAP BUILD
# ============================================================

def build_map(
    case_points=None,
    hotspots=None,
    ward_geojson=None,
    extent="BMC / Mumbai Focus",
    choropleth_geojson=None,
):
    layers = []

    # --------------------------------------------------------
    # Choropleth polygons
    # --------------------------------------------------------

    if choropleth_geojson:
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=choropleth_geojson,
                pickable=True,
                stroked=True,
                filled=True,
                get_fill_color="properties.fill_color",
                get_line_color="properties.line_color",
                line_width_min_pixels=1,
                opacity=0.65,
                auto_highlight=True,
            )
        )

    elif ward_geojson:
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=ward_geojson,
                pickable=True,
                stroked=True,
                filled=False,
                get_line_color=[
                    50,
                    50,
                    50,
                    230,
                ],
                line_width_min_pixels=2,
            )
        )

    # --------------------------------------------------------
    # Hotspots first
    # --------------------------------------------------------

    if hotspots is not None and not hotspots.empty:
        hotspot_data = hotspots.copy()

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=hotspot_data,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius="Display_Radius",
                get_fill_color=[
                    220,
                    30,
                    30,
                    80,
                ],
                get_line_color=[
                    180,
                    0,
                    0,
                    180,
                ],
                stroked=True,
                filled=True,
                pickable=True,
            )
        )

    # --------------------------------------------------------
    # Case points
    # --------------------------------------------------------

    if case_points is not None and not case_points.empty:

        # PE
        pe_points = case_points[
            case_points["Ward"] == "PE"
        ].copy()

        if not pe_points.empty:
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=pe_points,
                    get_position=[
                        LON_COL,
                        LAT_COL,
                    ],
                    get_radius="Point_Radius",
                    get_fill_color=[
                        30,
                        120,
                        220,
                        220,
                    ],
                    get_line_color=[
                        20,
                        60,
                        120,
                        240,
                    ],
                    stroked=True,
                    filled=True,
                    pickable=True,
                )
            )

        # PN
        pn_points = case_points[
            case_points["Ward"] == "PN"
        ].copy()

        if not pn_points.empty:
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=pn_points,
                    get_position=[
                        LON_COL,
                        LAT_COL,
                    ],
                    get_radius="Point_Radius",
                    get_fill_color=[
                        30,
                        170,
                        90,
                        225,
                    ],
                    get_line_color=[
                        0,
                        90,
                        45,
                        240,
                    ],
                    stroked=True,
                    filled=True,
                    pickable=True,
                )
            )

        # Other wards
        other_points = case_points[
            ~case_points["Ward"].isin(
                ["PE", "PN"]
            )
        ].copy()

        if not other_points.empty:
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=other_points,
                    get_position=[
                        LON_COL,
                        LAT_COL,
                    ],
                    get_radius="Point_Radius",
                    get_fill_color=[
                        110,
                        110,
                        110,
                        190,
                    ],
                    get_line_color=[
                        60,
                        60,
                        60,
                        220,
                    ],
                    stroked=True,
                    filled=True,
                    pickable=True,
                )
            )

    # --------------------------------------------------------
    # Map view
    # --------------------------------------------------------

    all_lat = []
    all_lon = []

    if (
        case_points is not None
        and not case_points.empty
    ):
        all_lat.extend(
            case_points[LAT_COL]
            .dropna()
            .tolist()
        )

        all_lon.extend(
            case_points[LON_COL]
            .dropna()
            .tolist()
        )

    if all_lat and all_lon:
        center_lat = sum(all_lat) / len(all_lat)
        center_lon = sum(all_lon) / len(all_lon)

        min_lat = min(all_lat)
        max_lat = max(all_lat)
        min_lon = min(all_lon)
        max_lon = max(all_lon)

        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon

        max_range = max(
            lat_range,
            lon_range,
        )

        if extent == "BMC / Mumbai Focus":
            center_lat = 19.0760
            center_lon = 72.8777
            zoom = 10.3

        else:
            if max_range < 0.02:
                zoom = 13
            elif max_range < 0.05:
                zoom = 11.5
            elif max_range < 0.15:
                zoom = 10
            elif max_range < 0.5:
                zoom = 8
            else:
                zoom = 5.5

    else:
        center_lat = 19.0760
        center_lon = 72.8777
        zoom = 10.3

    tooltip = {
        "html": """
        <b>Ward:</b> {Ward}<br/>
        <b>Disease:</b> {Disease}<br/>
        <b>Facility:</b> {Facility}<br/>
        <b>Case ID:</b> {Case_ID}<br/>
        <b>Cluster Cases:</b> {Cluster_Cases}<br/>
        <b>Hotspot:</b> {Hotspot_Level}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black",
        },
    }

    if choropleth_geojson:
        tooltip = {
            "html": """
            <b>Ward:</b> {ProgrammeWard}<br/>
            <b>Mapped Ward:</b> {MapWard}<br/>
            <b>Cases:</b> {ProgrammeCases}<br/>
            <b>Disease:</b> {Disease}
            """,
            "style": {
                "backgroundColor": "white",
                "color": "black",
            },
        }

    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=zoom,
            pitch=0,
            bearing=0,
        ),
        map_style=None,
        tooltip=tooltip,
    )


# ============================================================
# DISEASE COMPARISON
# ============================================================

def create_disease_comparison(df):
    disease_col = get_disease_column(df)

    if disease_col is None:
        return pd.DataFrame()

    comparison = (
        df[disease_col]
        .map(clean_text)
        .value_counts()
        .reset_index()
    )

    comparison.columns = [
        "Disease",
        "Cases",
    ]

    return comparison


def get_disease_map_data(df, disease):
    disease_col = get_disease_column(df)

    if disease_col is None:
        return pd.DataFrame()

    mask = (
        df[disease_col]
        .map(clean_text)
        == clean_text(disease)
    )

    return df.loc[mask].copy()


# ============================================================
# EXPORT
# ============================================================

def download_hotspot_data(
    case_points,
    hotspots,
):
    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        if (
            hotspots is not None
            and not hotspots.empty
        ):
            hotspots.to_excel(
                writer,
                index=False,
                sheet_name="Hotspots",
            )

        if (
            case_points is not None
            and not case_points.empty
        ):
            case_points.to_excel(
                writer,
                index=False,
                sheet_name="Case_Points",
            )

    output.seek(0)

    return output


# ============================================================
# MAIN RENDER
# ============================================================

def render_geographic_map(
    filtered_df,
    df,
):
    st.markdown(
        "# Geographic Disease Map"
    )

    st.caption(
        "Geographic distribution, disease burden, "
        "facility and ward hotspot analysis."
    )

    if filtered_df is None or filtered_df.empty:
        st.warning(
            "No data available for the selected filters."
        )
        return

    coordinate_df = prepare_coordinates(
        filtered_df
    )

    if coordinate_df.empty:
        st.warning(
            "No valid latitude/longitude coordinates "
            "are available in the filtered data."
        )
        return

    disease_col = get_disease_column(
        coordinate_df
    )

    if disease_col is None:
        st.error(
            "Disease column could not be identified."
        )
        return

    diseases = sorted(
        [
            clean_text(x)
            for x in coordinate_df[disease_col]
            .dropna()
            .unique()
            if clean_text(x)
        ]
    )

    if not diseases:
        st.warning(
            "No diseases are available for geographic mapping."
        )
        return

    st.info(
        coordinate_availability_text(
            coordinate_df
        )
    )

    bmc_geojson = load_bmc_wards()

    # ========================================================
    # MAP CONTROLS
    # ========================================================

    st.markdown(
        "### Map Controls"
    )

    extent_col, disease_col_ui, reset_col = st.columns(
        [1.0, 2.6, 0.35]
    )

    with extent_col:
        extent = st.radio(
            "Map Extent",
            [
                "BMC / Mumbai Focus",
                "All Coordinates",
            ],
            horizontal=True,
            key="geo_extent",
        )

    with disease_col_ui:
        selected_diseases = disease_selection_control(
            diseases
        )

    with reset_col:
        st.markdown(
            "<div style='height:28px'></div>",
            unsafe_allow_html=True,
        )

        if st.button(
            "↺",
            key="geo_disease_reset",
            help="Reset disease selection to default",
        ):
            st.session_state[
                "geo_disease_selection"
            ] = []

            st.rerun()

    # ========================================================
    # APPLY DISEASE SELECTION
    # ========================================================

    if selected_diseases:
        map_df = coordinate_df[
            coordinate_df[disease_col]
            .map(clean_text)
            .isin(selected_diseases)
        ].copy()

    else:
        map_df = coordinate_df.copy()

    # ========================================================
    # MAIN DATA OBJECTS
    # ========================================================

    hotspots = create_hotspots(
        map_df
    )

    case_points = create_case_points(
        map_df,
        hotspots,
    )

    ward_summary = create_ward_summary(
        map_df
    )

    disease_comparison = create_disease_comparison(
        map_df
    )

    # ========================================================
    # KPI
    # ========================================================

    total_cases = len(map_df)

    total_diseases = (
        map_df[disease_col]
        .map(clean_text)
        .nunique()
    )

    total_wards = (
        ward_summary.loc[
            ward_summary["Cases"] > 0,
            "Ward"
        ].nunique()
    )

    total_hotspots = len(
        hotspots
    ) if hotspots is not None else 0

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric(
            "Mapped Cases",
            f"{total_cases:,}",
        )

    with k2:
        st.metric(
            "Diseases",
            f"{total_diseases:,}",
        )

    with k3:
        st.metric(
            "Wards with Cases",
            f"{total_wards:,}",
        )

    with k4:
        st.metric(
            "Geographic Clusters",
            f"{total_hotspots:,}",
        )

    # ========================================================
    # TABS
    # ========================================================

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Hotspots",
            "Disease Comparison",
            "Choropleth Comparison",
            "Combined Geographic View",
        ]
    )

    # ========================================================
    # TAB 1 - HOTSPOTS
    # ========================================================

    with tab1:
        st.markdown(
            "### Geographic Hotspots"
        )

        if (
            hotspots is None
            or hotspots.empty
        ):
            st.info(
                "No geographic hotspots identified."
            )
        else:
            hotspot_map = build_map(
                case_points=case_points,
                hotspots=hotspots,
                ward_geojson=bmc_geojson,
                extent=extent,
            )

            st.pydeck_chart(
                hotspot_map,
                use_container_width=True,
            )

            st.markdown(
                "### Hotspot Summary"
            )

            hotspot_display = hotspots.copy()

            hotspot_display["Cases"] = (
                hotspot_display["Cluster_Cases"]
            )

            hotspot_display = hotspot_display[
                [
                    "Latitude",
                    "Longitude",
                    "Cases",
                    "Hotspot_Level",
                ]
            ].sort_values(
                "Cases",
                ascending=False,
            )

            st.dataframe(
                hotspot_display,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # TAB 2 - DISEASE COMPARISON
    # ========================================================

    with tab2:
        st.markdown(
            "### Disease-wise Geographic Comparison"
        )

        if disease_comparison.empty:
            st.info(
                "No disease comparison data available."
            )
        else:
            st.dataframe(
                disease_comparison,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # TAB 3 - CHOROPLETH COMPARISON
    # ========================================================

    with tab3:
        st.markdown(
            "### Disease-wise Ward Choropleth"
        )

        if not bmc_geojson:
            st.warning(
                "BMC ward boundary data could not be loaded."
            )
        elif disease_comparison.empty:
            st.info(
                "No disease data available."
            )
        else:
            comparison_diseases = (
                selected_diseases
                if selected_diseases
                else diseases
            )

            for disease in comparison_diseases:
                disease_df = get_disease_map_data(
                    map_df,
                    disease,
                )

                if disease_df.empty:
                    continue

                disease_ward_summary = (
                    create_ward_summary(
                        disease_df
                    )
                )

                disease_choropleth = (
                    prepare_bmc_choropleth(
                        bmc_geojson,
                        disease_ward_summary,
                        disease_name=disease,
                    )
                )

                disease_points = (
                    create_case_points(
                        disease_df,
                        create_hotspots(
                            disease_df
                        ),
                    )
                )

                st.markdown(
                    f"#### {disease}"
                )

                total_disease_cases = len(
                    disease_df
                )

                palette = get_disease_palette(
                    disease
                )

                st.caption(
                    f"{total_disease_cases:,} cases | "
                    f"{palette['name']} disease palette | "
                    "Dark = higher burden, "
                    "light = lower burden"
                )

                disease_map = build_map(
                    case_points=disease_points,
                    hotspots=create_hotspots(
                        disease_df
                    ),
                    extent=extent,
                    choropleth_geojson=(
                        disease_choropleth
                    ),
                )

                st.pydeck_chart(
                    disease_map,
                    use_container_width=True,
                )

                display_summary = (
                    disease_ward_summary
                    .sort_values(
                        "Cases",
                        ascending=False,
                    )
                )

                st.dataframe(
                    display_summary,
                    use_container_width=True,
                    hide_index=True,
                )

    # ========================================================
    # TAB 4 - COMBINED GEOGRAPHIC VIEW
    # ========================================================

    with tab4:
        st.markdown(
            "### Combined Geographic Management View"
        )

        if bmc_geojson:
            combined_choropleth = (
                prepare_bmc_choropleth(
                    bmc_geojson,
                    ward_summary,
                    disease_name=(
                        selected_diseases[0]
                        if len(selected_diseases) == 1
                        else "Combined"
                    ),
                )
            )
        else:
            combined_choropleth = None

        combined_map = build_map(
            case_points=case_points,
            hotspots=hotspots,
            extent=extent,
            choropleth_geojson=(
                combined_choropleth
            ),
        )

        st.pydeck_chart(
            combined_map,
            use_container_width=True,
        )

        st.markdown(
            "### Ward-wise Burden"
        )

        ward_display = ward_summary.sort_values(
            "Cases",
            ascending=False,
        )

        st.dataframe(
            ward_display,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown(
            "### Disease-wise Burden"
        )

        st.dataframe(
            disease_comparison,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # EXPORT
    # ========================================================

    st.markdown(
        "### Geographic Data Export"
    )

    export_file = download_hotspot_data(
        case_points,
        hotspots,
    )

    st.download_button(
        "Download Geographic Analysis Excel",
        data=export_file,
        file_name="geographic_disease_analysis.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )
