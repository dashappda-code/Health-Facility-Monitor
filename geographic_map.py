import io
import re
import zipfile

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

MAP_STYLE = (
    "https://basemaps.cartocdn.com/gl/"
    "dark-matter-gl-style/style.json"
)

PROGRAMME_WARDS = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "FN",
    "FS",
    "GN",
    "GS",
    "HE",
    "HW",
    "KE",
    "KW",
    "L",
    "ME",
    "MW",
    "N",
    "PE",
    "PN",
    "PS",
    "RC",
    "RN",
    "RS",
    "S",
    "T",
]


# ============================================================
# TEXT HELPERS
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

    column_map = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower()

        if key in column_map:
            return column_map[key]

    for column in df.columns:
        column_text = str(column).strip().lower()

        for candidate in candidates:
            candidate_text = (
                str(candidate).strip().lower()
            )

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

    if compact in PROGRAMME_WARDS:
        return compact

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

    cleaned = re.sub(r"\bWARD\b", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    compact_cleaned = cleaned.replace(" ", "")

    if compact_cleaned in PROGRAMME_WARDS:
        return compact_cleaned

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

    return ""


# ============================================================
# COLUMN DETECTION
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
        errors="coerce",
    )

    work[LON_COL] = pd.to_numeric(
        work[LON_COL],
        errors="coerce",
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
        return (
            "No valid latitude/longitude coordinates are available."
        )

    return (
        f"{len(coordinate_df):,} records have valid coordinates "
        "and are available for geographic mapping."
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
        work.groupby(
            "_Cluster_ID",
            as_index=False,
        )
        .agg(
            Latitude=(LAT_COL, "mean"),
            Longitude=(LON_COL, "mean"),
            Cluster_Cases=(LAT_COL, "size"),
        )
    )

    hotspots["Hotspot_Level"] = "Low"

    hotspots.loc[
        hotspots["Cluster_Cases"] >= 5,
        "Hotspot_Level",
    ] = "Moderate"

    hotspots.loc[
        hotspots["Cluster_Cases"] >= 10,
        "Hotspot_Level",
    ] = "High"

    hotspots["Display_Radius"] = (
        45 + hotspots["Cluster_Cases"] * 4
    )

    hotspots["Display_Radius"] = (
        hotspots["Display_Radius"]
        .clip(45, 125)
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

    disease_col = get_disease_column(
        coordinate_df
    )

    ward_col = get_ward_column(
        coordinate_df
    )

    facility_col = get_facility_column(
        coordinate_df
    )

    case_id_col = get_case_id_column(
        coordinate_df
    )

    work = coordinate_df.copy()

    if disease_col is not None:
        work["Disease"] = (
            work[disease_col].map(clean_text)
        )
    else:
        work["Disease"] = "Unknown"

    if ward_col is not None:
        work["Ward"] = (
            work[ward_col].map(normalise_ward)
        )
    else:
        work["Ward"] = ""

    if facility_col is not None:
        work["Facility"] = (
            work[facility_col].map(clean_text)
        )
    else:
        work["Facility"] = ""

    if case_id_col is not None:
        work["Case_ID"] = (
            work[case_id_col].map(clean_text)
        )
    else:
        work["Case_ID"] = work.index.astype(str)

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

    if (
        hotspots is not None
        and isinstance(hotspots, pd.DataFrame)
        and not hotspots.empty
    ):
        hotspot_lookup = dict(
            zip(
                hotspots["_Cluster_ID"],
                hotspots["Cluster_Cases"],
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

    work["Hotspot_Level"] = "Low"

    work.loc[
        work["Cluster_Cases"] >= 5,
        "Hotspot_Level",
    ] = "Moderate"

    work.loc[
        work["Cluster_Cases"] >= 10,
        "Hotspot_Level",
    ] = "High"

    work["PN_Hotspot"] = (
        (work["Ward"] == "PN")
        & (work["Cluster_Cases"] >= 5)
    )

    work["Point_Radius"] = 28.0

    work.loc[
        work["PN_Hotspot"],
        "Point_Radius",
    ] = 65.0

    return work[
        [
            LAT_COL,
            LON_COL,
            "Ward",
            "Disease",
            "Facility",
            "Case_ID",
            "Cluster_ID",
            "Cluster_Cases",
            "Hotspot_Level",
            "PN_Hotspot",
            "Point_Radius",
        ]
    ].copy()


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

    ward_col = get_ward_column(df)

    if ward_col is None:
        return pd.DataFrame(
            {
                "Ward": PROGRAMME_WARDS,
                "Cases": [0] * len(PROGRAMME_WARDS),
            }
        )

    work = df.copy()

    work["_Mapped_Ward"] = (
        work[ward_col].map(normalise_ward)
    )

    counts = (
        work["_Mapped_Ward"]
        .value_counts()
        .to_dict()
    )

    return pd.DataFrame(
        {
            "Ward": PROGRAMME_WARDS,
            "Cases": [
                int(counts.get(ward, 0))
                for ward in PROGRAMME_WARDS
            ],
        }
    )


# ============================================================
# MAP WARD SUMMARY
# PE + PN = P
# ============================================================

def create_map_ward_summary(ward_summary):
    if (
        ward_summary is None
        or not isinstance(ward_summary, pd.DataFrame)
        or ward_summary.empty
    ):
        return pd.DataFrame(
            columns=["Ward", "Cases"]
        )

    summary = ward_summary.copy()

    pe_cases = int(
        summary.loc[
            summary["Ward"] == "PE",
            "Cases",
        ].sum()
    )

    pn_cases = int(
        summary.loc[
            summary["Ward"] == "PN",
            "Cases",
        ].sum()
    )

    summary = summary[
        ~summary["Ward"].isin(["PE", "PN"])
    ].copy()

    p_row = pd.DataFrame(
        {
            "Ward": ["P"],
            "Cases": [
                pe_cases + pn_cases
            ],
        }
    )

    return pd.concat(
        [
            summary,
            p_row,
        ],
        ignore_index=True,
    )


# ============================================================
# BMC GEOJSON
# ============================================================

@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def load_bmc_wards():
    params = {
        "where": "1=1",
        "outFields": "NAME",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }

    try:
        response = requests.get(
            BMC_WARD_URL + "/query",
            params=params,
            timeout=15,
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
# GEOJSON WARD NAME
# ============================================================

def get_geojson_ward_name(properties):
    if not isinstance(properties, dict):
        return ""

    preferred_keys = [
        "NAME",
        "Ward",
        "WARD",
        "Name",
        "name",
        "WARD_NAME",
    ]

    for key in preferred_keys:
        if key in properties:
            ward = normalise_ward(
                properties.get(key)
            )

            if ward:
                return ward

    for value in properties.values():
        ward = normalise_ward(value)

        if ward:
            return ward

    return ""


# ============================================================
# DISEASE PALETTES
# ============================================================

DISEASE_PALETTES = [
    {
        "name": "Blue",
        "light": [65, 105, 150],
        "mid": [25, 100, 180],
        "dark": [0, 210, 255],
    },
    {
        "name": "Green",
        "light": [50, 100, 65],
        "mid": [20, 150, 75],
        "dark": [0, 255, 120],
    },
    {
        "name": "Purple",
        "light": [75, 55, 100],
        "mid": [120, 55, 180],
        "dark": [210, 80, 255],
    },
    {
        "name": "Orange",
        "light": [110, 65, 30],
        "mid": [200, 90, 20],
        "dark": [255, 175, 40],
    },
    {
        "name": "Teal",
        "light": [30, 90, 90],
        "mid": [20, 160, 160],
        "dark": [0, 255, 220],
    },
    {
        "name": "Red",
        "light": [100, 35, 35],
        "mid": [190, 35, 40],
        "dark": [255, 65, 65],
    },
    {
        "name": "Magenta",
        "light": [90, 35, 85],
        "mid": [170, 40, 150],
        "dark": [255, 80, 220],
    },
    {
        "name": "Olive",
        "light": [80, 80, 30],
        "mid": [150, 150, 30],
        "dark": [230, 230, 50],
    },
]


def get_disease_palette(disease_name=None):
    if not disease_name:
        return DISEASE_PALETTES[0]

    text = clean_text(
        disease_name
    ).lower()

    total = sum(
        ord(char)
        for char in text
    )

    return DISEASE_PALETTES[
        total % len(DISEASE_PALETTES)
    ]


def get_choropleth_color(
    cases,
    max_cases,
    palette,
):
    cases = int(cases or 0)
    max_cases = int(max_cases or 0)

    if cases <= 0 or max_cases <= 0:
        return [
            25,
            25,
            25,
            120,
        ]

    ratio = cases / max_cases

    ratio = max(
        0.0,
        min(1.0, ratio),
    )

    light = palette["light"]
    mid = palette["mid"]
    dark = palette["dark"]

    if ratio <= 0.5:
        local_ratio = ratio / 0.5

        rgb = [
            int(
                light[i]
                + (
                    mid[i]
                    - light[i]
                )
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
                + (
                    dark[i]
                    - mid[i]
                )
                * local_ratio
            )
            for i in range(3)
        ]

    return [
        rgb[0],
        rgb[1],
        rgb[2],
        215,
    ]


# ============================================================
# CHOROPLETH
# ============================================================

def prepare_bmc_choropleth(
    geojson,
    ward_summary,
    disease_name=None,
):
    if not isinstance(geojson, dict):
        return None

    if (
        ward_summary is None
        or not isinstance(ward_summary, pd.DataFrame)
        or ward_summary.empty
    ):
        return None

    map_summary = create_map_ward_summary(
        ward_summary
    )

    if map_summary.empty:
        return None

    ward_cases = dict(
        zip(
            map_summary["Ward"],
            map_summary["Cases"],
        )
    )

    max_cases = (
        int(map_summary["Cases"].max())
        if not map_summary.empty
        else 0
    )

    palette = get_disease_palette(
        disease_name
    )

    features = []

    for feature in geojson.get(
        "features",
        [],
    ):
        properties = dict(
            feature.get(
                "properties",
                {},
            )
        )

        detected_ward = (
            get_geojson_ward_name(
                properties
            )
        )

        map_ward = detected_ward

        if detected_ward in [
            "PE",
            "PN",
        ]:
            map_ward = "P"

        cases = int(
            ward_cases.get(
                map_ward,
                0,
            )
        )

        properties["ProgrammeWard"] = (
            detected_ward
            if detected_ward
            else "Unmatched"
        )

        properties["MapWard"] = map_ward

        properties["ProgrammeCases"] = cases

        if max_cases > 0:
            burden_ratio = (
                cases / max_cases
            )
        else:
            burden_ratio = 0

        if cases <= 0:
            burden_level = "No cases"
        elif burden_ratio >= 0.70:
            burden_level = "High"
        elif burden_ratio >= 0.35:
            burden_level = "Moderate"
        else:
            burden_level = "Low"

        properties["Burden"] = burden_level

        properties["WardDisplay"] = (
            f"{detected_ward or 'Unmatched'}"
            f" | Cases: {cases:,}"
        )

        properties["Disease"] = (
            clean_text(disease_name)
            if disease_name
            else "Combined"
        )

        properties["fill_color"] = (
            get_choropleth_color(
                cases,
                max_cases,
                palette,
            )
        )

        properties["line_color"] = [
            125,
            125,
            125,
            220,
        ]

        new_feature = {
            "type": "Feature",
            "geometry": feature.get(
                "geometry"
            ),
            "properties": properties,
        }

        features.append(
            new_feature
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


# ============================================================
# DISEASE SELECTION RESET
# ============================================================

def reset_geo_disease_selection():
    st.session_state[
        "geo_disease_selection"
    ] = []


# ============================================================
# DISEASE SELECTION
# ============================================================

def disease_selection_control(diseases):
    diseases = [
        clean_text(disease)
        for disease in diseases
        if clean_text(disease)
    ]

    diseases = list(
        dict.fromkeys(diseases)
    )

    if not diseases:
        return diseases

    signature = "|".join(diseases)

    if (
        st.session_state.get(
            "geo_disease_options_signature"
        )
        != signature
    ):
        st.session_state[
            "geo_disease_options_signature"
        ] = signature

        if (
            "geo_disease_selection"
            not in st.session_state
        ):
            st.session_state[
                "geo_disease_selection"
            ] = []

    selected = st.multiselect(
        "Disease Selection",
        options=[
            "Select All"
        ] + diseases,
        key="geo_disease_selection",
        placeholder="All diseases",
        help=(
            "Leave empty for all diseases. "
            "Select one or more diseases."
        ),
    )

    if "Select All" in selected:
        return diseases

    if not selected:
        return diseases

    return selected


# ============================================================
# WARD CHOROPLETH CHECKBOX CONTROL
# ============================================================

def reset_choropleth_selection():
    for disease in st.session_state.get(
        "geo_choropleth_available_diseases",
        [],
    ):
        key = (
            "geo_choro_checkbox_"
            + re.sub(
                r"[^A-Za-z0-9]+",
                "_",
                disease,
            )
        )

        if key in st.session_state:
            st.session_state[key] = False

    st.session_state[
        "geo_choropleth_selection"
    ] = []

    st.session_state[
        "geo_choropleth_limit_message"
    ] = ""


def choropleth_checkbox_callback(
    disease,
):
    checkbox_key = (
        "geo_choro_checkbox_"
        + re.sub(
            r"[^A-Za-z0-9]+",
            "_",
            disease,
        )
    )

    selected = []

    for available_disease in st.session_state.get(
        "geo_choropleth_available_diseases",
        [],
    ):
        key = (
            "geo_choro_checkbox_"
            + re.sub(
                r"[^A-Za-z0-9]+",
                "_",
                available_disease,
            )
        )

        if st.session_state.get(
            key,
            False,
        ):
            selected.append(
                available_disease
            )

    if len(selected) > 6:

        st.session_state[
            checkbox_key
        ] = False

        selected = [
            value
            for value in selected
            if value != disease
        ]

        st.session_state[
            "geo_choropleth_limit_message"
        ] = (
            "⚠️ Maximum 6 diseases can be selected "
            "at a time. Please deselect one disease "
            "before selecting another."
        )

    else:

        st.session_state[
            "geo_choropleth_limit_message"
        ] = ""

    st.session_state[
        "geo_choropleth_selection"
    ] = selected


def render_choropleth_disease_checkboxes(
    available_diseases,
):
    available_diseases = [
        clean_text(disease)
        for disease in available_diseases
        if clean_text(disease)
    ]

    available_diseases = list(
        dict.fromkeys(
            available_diseases
        )
    )

    st.session_state[
        "geo_choropleth_available_diseases"
    ] = available_diseases

    # --------------------------------------------------------
    # HANDLE CLEAR SELECTION REQUEST
    # BEFORE CHECKBOX WIDGETS ARE CREATED
    # --------------------------------------------------------

    if st.session_state.get(
        "geo_choropleth_clear_requested",
        False,
    ):

        st.session_state[
            "geo_choropleth_selection"
        ] = []

        for disease in available_diseases:

            checkbox_key = (
                "geo_choro_checkbox_"
                + re.sub(
                    r"[^A-Za-z0-9]+",
                    "_",
                    disease,
                )
            )

            st.session_state[
                checkbox_key
            ] = False

        st.session_state[
            "geo_choropleth_limit_message"
        ] = ""

        st.session_state[
            "geo_choropleth_clear_requested"
        ] = False

    if (
        "geo_choropleth_selection"
        not in st.session_state
    ):
        st.session_state[
            "geo_choropleth_selection"
        ] = []

    current_selection = (
        st.session_state[
            "geo_choropleth_selection"
        ]
    )

    current_selection = [
        disease
        for disease in current_selection
        if disease in available_diseases
    ]

    st.session_state[
        "geo_choropleth_selection"
    ] = current_selection

    st.markdown(
        "#### Select Diseases to Display"
    )

    st.caption(
        "Select up to 6 diseases. "
        "Each selected disease will be displayed "
        "as a ward choropleth map with its ward-wise table."
    )

    st.markdown(
        """
        <style>
        .geo-choro-checkbox-row {
            display: flex;
            flex-wrap: nowrap;
            overflow-x: auto;
            overflow-y: hidden;
            gap: 18px;
            width: 100%;
            padding: 4px 4px 10px 4px;
            box-sizing: border-box;
            white-space: nowrap;
        }

        .geo-choro-checkbox-item {
            flex: 0 0 auto;
            min-width: max-content;
            white-space: nowrap;
        }

        .geo-choro-checkbox-row
        div[data-testid="stCheckbox"] {
            width: max-content;
            min-width: max-content;
        }

        .geo-choro-checkbox-row
        div[data-testid="stCheckbox"] label {
            white-space: nowrap;
            min-width: max-content;
        }

        .geo-choro-checkbox-row
        div[data-testid="stCheckbox"] p {
            white-space: nowrap;
        }

        .geo-choro-checkbox-scroll {
            overflow-x: auto;
            overflow-y: hidden;
            width: 100%;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    checkbox_container = st.container()

    with checkbox_container:

        checkbox_columns = st.columns(
            len(available_diseases),
            gap="small",
        )

        for column, disease in zip(
            checkbox_columns,
            available_diseases,
        ):
            checkbox_key = (
                "geo_choro_checkbox_"
                + re.sub(
                    r"[^A-Za-z0-9]+",
                    "_",
                    disease,
                )
            )

            if checkbox_key not in st.session_state:
                st.session_state[
                    checkbox_key
                ] = (
                    disease
                    in current_selection
                )

            with column:
                st.checkbox(
                    disease,
                    key=checkbox_key,
                    on_change=(
                        choropleth_checkbox_callback
                    ),
                    args=(disease,),
                )

    selected = []

    for disease in available_diseases:
        checkbox_key = (
            "geo_choro_checkbox_"
            + re.sub(
                r"[^A-Za-z0-9]+",
                "_",
                disease,
            )
        )

        if st.session_state.get(
            checkbox_key,
            False,
        ):
            selected.append(disease)

    if len(selected) > 6:
        selected = selected[:6]

    st.session_state[
        "geo_choropleth_selection"
    ] = selected

    if st.session_state.get(
        "geo_choropleth_limit_message",
        "",
    ):
        st.warning(
            st.session_state[
                "geo_choropleth_limit_message"
            ]
        )

    st.markdown(
        f"**Selected: {len(selected)} / 6**"
    )

    return selected


# ============================================================
# MAP VIEW
# ============================================================

def calculate_view(
    case_points=None,
    extent="BMC Focus",
):
    if (
        case_points is None
        or not isinstance(
            case_points,
            pd.DataFrame,
        )
        or case_points.empty
    ):
        return (
            19.0760,
            72.8777,
            10.3,
        )

    if extent == "BMC Focus":
        return (
            19.0760,
            72.8777,
            10.3,
        )

    if (
        LAT_COL in case_points.columns
        and LON_COL in case_points.columns
    ):
        lat_column = LAT_COL
        lon_column = LON_COL

    elif (
        "Latitude" in case_points.columns
        and "Longitude" in case_points.columns
    ):
        lat_column = "Latitude"
        lon_column = "Longitude"

    else:
        return (
            19.0760,
            72.8777,
            10.3,
        )

    lat_values = (
        pd.to_numeric(
            case_points[lat_column],
            errors="coerce",
        )
        .dropna()
        .tolist()
    )

    lon_values = (
        pd.to_numeric(
            case_points[lon_column],
            errors="coerce",
        )
        .dropna()
        .tolist()
    )

    if not lat_values or not lon_values:
        return (
            19.0760,
            72.8777,
            10.3,
        )

    center_lat = (
        min(lat_values)
        + max(lat_values)
    ) / 2

    center_lon = (
        min(lon_values)
        + max(lon_values)
    ) / 2

    max_range = max(
        max(lat_values) - min(lat_values),
        max(lon_values) - min(lon_values),
    )

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

    return (
        center_lat,
        center_lon,
        zoom,
    )


# ============================================================
# BUILD HOTSPOT MAP
# ============================================================

def build_hotspot_map(
    hotspots,
    ward_geojson=None,
    extent="BMC Focus",
):
    layers = []

    if isinstance(ward_geojson, dict):
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=ward_geojson,
                pickable=False,
                stroked=True,
                filled=False,
                get_line_color=[
                    130,
                    130,
                    130,
                    190,
                ],
                line_width_min_pixels=1,
            )
        )

    if (
        hotspots is not None
        and isinstance(hotspots, pd.DataFrame)
        and not hotspots.empty
    ):
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=hotspots,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius="Display_Radius",
                get_fill_color=[
                    235,
                    50,
                    50,
                    105,
                ],
                get_line_color=[
                    255,
                    80,
                    80,
                    230,
                ],
                stroked=True,
                filled=True,
                pickable=True,
                radius_min_pixels=5,
                radius_max_pixels=35,
            )
        )

    center_lat, center_lon, zoom = (
        calculate_view(
            hotspots,
            extent,
        )
    )

    return pdk.Deck(
        map_style=MAP_STYLE,
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=zoom,
            pitch=0,
            bearing=0,
        ),
        tooltip={
            "html": """
            <div style="font-size:13px;">
            <b>Cluster Cases:</b> {Cluster_Cases}<br/>
            <b>Hotspot Level:</b> {Hotspot_Level}<br/>
            <b>Latitude:</b> {Latitude}<br/>
            <b>Longitude:</b> {Longitude}
            </div>
            """,
            "style": {
                "backgroundColor": "#111111",
                "color": "#ffffff",
            },
        },
    )


# ============================================================
# BUILD CHOROPLETH MAP
# ============================================================

def build_choropleth_map(
    choropleth_geojson,
):
    if not isinstance(
        choropleth_geojson,
        dict,
    ):
        return None

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=choropleth_geojson,
        pickable=True,
        stroked=True,
        filled=True,
        get_fill_color="properties.fill_color",
        get_line_color="properties.line_color",
        line_width_min_pixels=1,
        opacity=0.88,
        auto_highlight=True,
        highlight_color=[
            255,
            255,
            255,
            80,
        ],
    )

    return pdk.Deck(
        map_style=MAP_STYLE,
        layers=[layer],
        initial_view_state=pdk.ViewState(
            latitude=19.0760,
            longitude=72.8777,
            zoom=10.3,
            pitch=0,
            bearing=0,
        ),
        tooltip={
            "html": """
            <div style="font-size:13px;">
            <b>Ward:</b> {ProgrammeWard}<br/>
            <b>Cases:</b> {ProgrammeCases}<br/>
            <b>Disease:</b> {Disease}<br/>
            <b>Burden:</b> {Burden}
            </div>
            """,
            "style": {
                "backgroundColor": "#111111",
                "color": "#ffffff",
            },
        },
    )


# ============================================================
# BUILD COMBINED MAP
# ============================================================

def build_combined_map(
    choropleth_geojson=None,
    hotspots=None,
    extent="BMC Focus",
):
    layers = []

    if isinstance(
        choropleth_geojson,
        dict,
    ):
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
                opacity=0.78,
                auto_highlight=True,
                highlight_color=[
                    255,
                    255,
                    255,
                    70,
                ],
            )
        )

    if (
        hotspots is not None
        and isinstance(hotspots, pd.DataFrame)
        and not hotspots.empty
    ):
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=hotspots,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius="Display_Radius",
                get_fill_color=[
                    235,
                    35,
                    35,
                    100,
                ],
                get_line_color=[
                    255,
                    80,
                    80,
                    220,
                ],
                stroked=True,
                filled=True,
                pickable=True,
                radius_min_pixels=5,
                radius_max_pixels=30,
            )
        )

    center_lat, center_lon, zoom = (
        calculate_view(
            hotspots,
            extent,
        )
    )

    return pdk.Deck(
        map_style=MAP_STYLE,
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=zoom,
            pitch=0,
            bearing=0,
        ),
        tooltip={
            "html": """
            <div style="font-size:13px;">
            <b>Ward:</b> {ProgrammeWard}<br/>
            <b>Cases:</b> {ProgrammeCases}<br/>
            <b>Disease:</b> {Disease}<br/>
            <b>Burden:</b> {Burden}
            </div>
            """,
            "style": {
                "backgroundColor": "#111111",
                "color": "#ffffff",
            },
        },
    )


# ============================================================
# DISEASE COMPARISON
# ============================================================

def create_disease_comparison(df):
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "Disease",
                "Cases",
            ]
        )

    disease_col = get_disease_column(df)

    if disease_col is None:
        return pd.DataFrame(
            columns=[
                "Disease",
                "Cases",
            ]
        )

    comparison = (
        df[disease_col]
        .map(clean_text)
        .loc[lambda x: x != ""]
        .value_counts()
        .reset_index()
    )

    comparison.columns = [
        "Disease",
        "Cases",
    ]

    return comparison


def get_disease_map_data(
    df,
    disease,
):
    if df is None or df.empty:
        return pd.DataFrame()

    disease_col = get_disease_column(df)

    if disease_col is None:
        return pd.DataFrame()

    disease_text = clean_text(
        disease
    )

    mask = (
        df[disease_col]
        .map(clean_text)
        == disease_text
    )

    return df.loc[
        mask
    ].copy()


# ============================================================
# EXCEL EXPORT
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
            and isinstance(hotspots, pd.DataFrame)
            and not hotspots.empty
        ):
            hotspots.to_excel(
                writer,
                index=False,
                sheet_name="Hotspots",
            )

        if (
            case_points is not None
            and isinstance(case_points, pd.DataFrame)
            and not case_points.empty
        ):
            case_points.to_excel(
                writer,
                index=False,
                sheet_name="Case_Points",
            )

    output.seek(0)

    return output


def download_choropleth_data(
    map_df,
    selected_choropleth_diseases,
):
    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        if (
            map_df is not None
            and isinstance(map_df, pd.DataFrame)
            and not map_df.empty
            and selected_choropleth_diseases
        ):

            all_rows = []

            for disease in selected_choropleth_diseases:

                disease_df = (
                    get_disease_map_data(
                        map_df,
                        disease,
                    )
                )

                if disease_df.empty:
                    continue

                disease_ward_summary = (
                    create_ward_summary(
                        disease_df
                    )
                )

                disease_ward_summary[
                    "Disease"
                ] = disease

                disease_ward_summary[
                    "Burden"
                ] = "Low"

                max_cases = int(
                    disease_ward_summary[
                        "Cases"
                    ].max()
                )

                if max_cases > 0:

                    disease_ward_summary.loc[
                        disease_ward_summary[
                            "Cases"
                        ]
                        >= max_cases * 0.70,
                        "Burden",
                    ] = "High"

                    disease_ward_summary.loc[
                        (
                            disease_ward_summary[
                                "Cases"
                            ]
                            >= max_cases * 0.35
                        )
                        & (
                            disease_ward_summary[
                                "Cases"
                            ]
                            < max_cases * 0.70
                        ),
                        "Burden",
                    ] = "Moderate"

                all_rows.append(
                    disease_ward_summary[
                        [
                            "Disease",
                            "Ward",
                            "Cases",
                            "Burden",
                        ]
                    ]
                )

            if all_rows:

                export_df = pd.concat(
                    all_rows,
                    ignore_index=True,
                )

                export_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Ward_Choropleth",
                )

            else:

                pd.DataFrame(
                    columns=[
                        "Disease",
                        "Ward",
                        "Cases",
                        "Burden",
                    ]
                ).to_excel(
                    writer,
                    index=False,
                    sheet_name="Ward_Choropleth",
                )

        else:

            pd.DataFrame(
                columns=[
                    "Disease",
                    "Ward",
                    "Cases",
                    "Burden",
                ]
            ).to_excel(
                writer,
                index=False,
                sheet_name="Ward_Choropleth",
            )

    output.seek(0)

    return output


# ============================================================
# NEW — STATIC MAP EXPORT HELPERS
# PNG + PDF
# ============================================================

def get_matplotlib_modules():
    """
    Lazy-load matplotlib so the dashboard does not unnecessarily
    load matplotlib when geographic maps are not being exported.
    """

    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib.patches import PathPatch, Patch
        from matplotlib.path import Path

        return (
            plt,
            PdfPages,
            PathPatch,
            Patch,
            Path,
        )

    except Exception:
        return None


def safe_map_filename(value):
    text = clean_text(value)

    text = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        text,
    )

    text = text.strip("_")

    if not text:
        return "map"

    return text


def iter_geojson_positions(coords):
    if isinstance(
        coords,
        (list, tuple),
    ):

        if (
            len(coords) >= 2
            and isinstance(
                coords[0],
                (int, float),
            )
            and isinstance(
                coords[1],
                (int, float),
            )
        ):
            yield (
                float(coords[0]),
                float(coords[1]),
            )

        else:

            for item in coords:
                yield from iter_geojson_positions(
                    item
                )


def get_geojson_bounds(geojson):
    if not isinstance(
        geojson,
        dict,
    ):
        return None

    lons = []
    lats = []

    for feature in geojson.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry"
        )

        if not isinstance(
            geometry,
            dict,
        ):
            continue

        coords = geometry.get(
            "coordinates"
        )

        for lon, lat in iter_geojson_positions(
            coords
        ):
            lons.append(lon)
            lats.append(lat)

    if not lons or not lats:
        return None

    return (
        min(lons),
        max(lons),
        min(lats),
        max(lats),
    )


def get_dataframe_bounds(
    dataframe,
):
    if (
        dataframe is None
        or not isinstance(
            dataframe,
            pd.DataFrame,
        )
        or dataframe.empty
    ):
        return None

    if (
        LAT_COL in dataframe.columns
        and LON_COL in dataframe.columns
    ):
        lat_col = LAT_COL
        lon_col = LON_COL

    elif (
        "Latitude" in dataframe.columns
        and "Longitude" in dataframe.columns
    ):
        lat_col = "Latitude"
        lon_col = "Longitude"

    else:
        return None

    lat = pd.to_numeric(
        dataframe[lat_col],
        errors="coerce",
    ).dropna()

    lon = pd.to_numeric(
        dataframe[lon_col],
        errors="coerce",
    ).dropna()

    if lat.empty or lon.empty:
        return None

    return (
        float(lon.min()),
        float(lon.max()),
        float(lat.min()),
        float(lat.max()),
    )


def geometry_to_path(
    geometry,
    Path,
):
    if not isinstance(
        geometry,
        dict,
    ):
        return None

    geometry_type = geometry.get(
        "type"
    )

    coordinates = geometry.get(
        "coordinates"
    )

    if not coordinates:
        return None

    polygons = []

    if geometry_type == "Polygon":
        polygons = [
            coordinates
        ]

    elif geometry_type == "MultiPolygon":
        polygons = coordinates

    else:
        return None

    vertices = []
    codes = []

    for polygon in polygons:

        if not polygon:
            continue

        for ring in polygon:

            if not ring:
                continue

            first_point = ring[0]

            vertices.append(
                (
                    float(first_point[0]),
                    float(first_point[1]),
                )
            )

            codes.append(
                Path.MOVETO
            )

            for point in ring[1:]:

                vertices.append(
                    (
                        float(point[0]),
                        float(point[1]),
                    )
                )

                codes.append(
                    Path.LINETO
                )

            vertices.append(
                (
                    float(first_point[0]),
                    float(first_point[1]),
                )
            )

            codes.append(
                Path.CLOSEPOLY
            )

    if not vertices:
        return None

    return Path(
        vertices,
        codes,
    )


def rgba255_to_mpl(
    value,
    default=(0.15, 0.15, 0.15, 0.75),
):
    if not isinstance(
        value,
        (list, tuple),
    ):
        return default

    if len(value) < 4:
        return default

    return (
        max(
            0,
            min(255, int(value[0])),
        ) / 255,
        max(
            0,
            min(255, int(value[1])),
        ) / 255,
        max(
            0,
            min(255, int(value[2])),
        ) / 255,
        max(
            0,
            min(255, int(value[3])),
        ) / 255,
    )


def get_feature_center(
    geometry,
):
    if not isinstance(
        geometry,
        dict,
    ):
        return None

    positions = list(
        iter_geojson_positions(
            geometry.get(
                "coordinates"
            )
        )
    )

    if not positions:
        return None

    lon = sum(
        point[0]
        for point in positions
    ) / len(positions)

    lat = sum(
        point[1]
        for point in positions
    ) / len(positions)

    return (
        lon,
        lat,
    )


def draw_geojson_features(
    ax,
    geojson,
    PathPatch,
    Path,
    show_labels=False,
):
    if not isinstance(
        geojson,
        dict,
    ):
        return

    for feature in geojson.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry"
        )

        properties = feature.get(
            "properties",
            {},
        )

        path = geometry_to_path(
            geometry,
            Path,
        )

        if path is None:
            continue

        fill_color = rgba255_to_mpl(
            properties.get(
                "fill_color"
            ),
            default=(
                0.08,
                0.08,
                0.08,
                0.25,
            ),
        )

        line_color = rgba255_to_mpl(
            properties.get(
                "line_color"
            ),
            default=(
                0.45,
                0.45,
                0.45,
                0.80,
            ),
        )

        patch = PathPatch(
            path,
            facecolor=fill_color,
            edgecolor=line_color,
            linewidth=0.75,
        )

        ax.add_patch(patch)

        if show_labels:

            center = get_feature_center(
                geometry
            )

            if center is not None:

                ward = clean_text(
                    properties.get(
                        "ProgrammeWard",
                        "",
                    )
                )

                cases = int(
                    properties.get(
                        "ProgrammeCases",
                        0,
                    )
                    or 0
                )

                if ward:

                    ax.text(
                        center[0],
                        center[1],
                        f"{ward}\n{cases:,}",
                        ha="center",
                        va="center",
                        fontsize=7,
                        color="white",
                        fontweight="bold",
                        bbox={
                            "boxstyle": "round,pad=0.15",
                            "facecolor": "#111111",
                            "edgecolor": "none",
                            "alpha": 0.65,
                        },
                    )


def set_static_map_extent(
    ax,
    geojson=None,
    dataframe=None,
    extent="BMC Focus",
):
    geo_bounds = get_geojson_bounds(
        geojson
    )

    data_bounds = get_dataframe_bounds(
        dataframe
    )

    if (
        extent == "BMC Focus"
        and geo_bounds is not None
    ):
        bounds = geo_bounds

    elif data_bounds is not None:
        bounds = data_bounds

    elif geo_bounds is not None:
        bounds = geo_bounds

    else:
        bounds = (
            72.75,
            73.05,
            18.88,
            19.30,
        )

    min_lon, max_lon, min_lat, max_lat = bounds

    lon_range = max_lon - min_lon
    lat_range = max_lat - min_lat

    lon_padding = max(
        lon_range * 0.06,
        0.01,
    )

    lat_padding = max(
        lat_range * 0.06,
        0.01,
    )

    ax.set_xlim(
        min_lon - lon_padding,
        max_lon + lon_padding,
    )

    ax.set_ylim(
        min_lat - lat_padding,
        max_lat + lat_padding,
    )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )


def style_static_map_axis(
    ax,
):
    ax.set_facecolor(
        "#111111"
    )

    ax.tick_params(
        colors="#d0d0d0",
        labelsize=8,
    )

    for spine in ax.spines.values():
        spine.set_color(
            "#555555"
        )

    ax.grid(
        True,
        color="#444444",
        alpha=0.25,
        linewidth=0.5,
    )

    ax.set_xlabel(
        "Longitude",
        color="#d0d0d0",
    )

    ax.set_ylabel(
        "Latitude",
        color="#d0d0d0",
    )


def create_static_hotspot_figure(
    hotspots,
    ward_geojson,
    extent,
):
    modules = get_matplotlib_modules()

    if modules is None:
        return None

    (
        plt,
        _,
        PathPatch,
        _,
        Path,
    ) = modules

    fig, ax = plt.subplots(
        figsize=(11, 7),
        dpi=160,
    )

    fig.patch.set_facecolor(
        "#111111"
    )

    ax.set_facecolor(
        "#111111"
    )

    if isinstance(
        ward_geojson,
        dict,
    ):

        boundary_geojson = {
            "type": "FeatureCollection",
            "features": [],
        }

        for feature in ward_geojson.get(
            "features",
            [],
        ):

            boundary_geojson[
                "features"
            ].append(
                {
                    "type": "Feature",
                    "geometry": feature.get(
                        "geometry"
                    ),
                    "properties": {},
                }
            )

        draw_geojson_features(
            ax,
            boundary_geojson,
            PathPatch,
            Path,
            show_labels=False,
        )

    if (
        hotspots is not None
        and isinstance(
            hotspots,
            pd.DataFrame,
        )
        and not hotspots.empty
    ):

        plot_data = hotspots.copy()

        sizes = (
            pd.to_numeric(
                plot_data[
                    "Display_Radius"
                ],
                errors="coerce",
            )
            .fillna(50)
            * 2.2
        )

        ax.scatter(
            plot_data["Longitude"],
            plot_data["Latitude"],
            s=sizes,
            c="#eb3232",
            alpha=0.40,
            edgecolors="#ff6060",
            linewidths=0.8,
        )

    set_static_map_extent(
        ax,
        geojson=ward_geojson,
        dataframe=hotspots,
        extent=extent,
    )

    ax.set_title(
        "Geographic Hotspot Map",
        color="white",
        fontsize=16,
        fontweight="bold",
        pad=14,
    )

    total_clusters = (
        len(hotspots)
        if isinstance(
            hotspots,
            pd.DataFrame,
        )
        else 0
    )

    total_cases = (
        int(
            hotspots[
                "Cluster_Cases"
            ].sum()
        )
        if (
            isinstance(
                hotspots,
                pd.DataFrame,
            )
            and not hotspots.empty
        )
        else 0
    )

    ax.text(
        0.01,
        0.01,
        (
            f"Geographic clusters: {total_clusters:,} | "
            f"Cluster cases: {total_cases:,}"
        ),
        transform=ax.transAxes,
        color="#d0d0d0",
        fontsize=9,
    )

    style_static_map_axis(
        ax
    )

    fig.tight_layout()

    return fig


def create_static_choropleth_figure(
    choropleth_geojson,
    disease_name,
    total_cases=None,
):
    modules = get_matplotlib_modules()

    if modules is None:
        return None

    (
        plt,
        _,
        PathPatch,
        Patch,
        Path,
    ) = modules

    fig, ax = plt.subplots(
        figsize=(11, 7),
        dpi=160,
    )

    fig.patch.set_facecolor(
        "#111111"
    )

    ax.set_facecolor(
        "#111111"
    )

    draw_geojson_features(
        ax,
        choropleth_geojson,
        PathPatch,
        Path,
        show_labels=True,
    )

    set_static_map_extent(
        ax,
        geojson=choropleth_geojson,
        dataframe=None,
        extent="BMC Focus",
    )

    title = (
        f"Ward Choropleth — {clean_text(disease_name)}"
    )

    ax.set_title(
        title,
        color="white",
        fontsize=16,
        fontweight="bold",
        pad=14,
    )

    if total_cases is None:
        total_cases = 0

    ax.text(
        0.01,
        0.01,
        f"Total mapped cases: {int(total_cases):,}",
        transform=ax.transAxes,
        color="#d0d0d0",
        fontsize=9,
    )

    palette = get_disease_palette(
        disease_name
    )

    legend_handles = [
        Patch(
            facecolor=rgba255_to_mpl(
                [25, 25, 25, 215]
            ),
            edgecolor="none",
            label="No cases",
        ),
        Patch(
            facecolor=rgba255_to_mpl(
                palette["light"] + [215]
            ),
            edgecolor="none",
            label="Low",
        ),
        Patch(
            facecolor=rgba255_to_mpl(
                palette["mid"] + [215]
            ),
            edgecolor="none",
            label="Moderate",
        ),
        Patch(
            facecolor=rgba255_to_mpl(
                palette["dark"] + [215]
            ),
            edgecolor="none",
            label="High",
        ),
    ]

    legend = ax.legend(
        handles=legend_handles,
        loc="upper right",
        frameon=True,
        facecolor="#171717",
        edgecolor="#555555",
        fontsize=8,
    )

    for text in legend.get_texts():
        text.set_color("white")

    style_static_map_axis(
        ax
    )

    fig.tight_layout()

    return fig


def create_static_combined_figure(
    choropleth_geojson,
    hotspots,
    extent,
):
    modules = get_matplotlib_modules()

    if modules is None:
        return None

    (
        plt,
        _,
        PathPatch,
        _,
        Path,
    ) = modules

    fig, ax = plt.subplots(
        figsize=(11, 7),
        dpi=160,
    )

    fig.patch.set_facecolor(
        "#111111"
    )

    ax.set_facecolor(
        "#111111"
    )

    if isinstance(
        choropleth_geojson,
        dict,
    ):

        draw_geojson_features(
            ax,
            choropleth_geojson,
            PathPatch,
            Path,
            show_labels=True,
        )

    if (
        hotspots is not None
        and isinstance(
            hotspots,
            pd.DataFrame,
        )
        and not hotspots.empty
    ):

        plot_data = hotspots.copy()

        sizes = (
            pd.to_numeric(
                plot_data[
                    "Display_Radius"
                ],
                errors="coerce",
            )
            .fillna(50)
            * 2.0
        )

        ax.scatter(
            plot_data["Longitude"],
            plot_data["Latitude"],
            s=sizes,
            c="#eb3232",
            alpha=0.42,
            edgecolors="#ff6060",
            linewidths=0.8,
        )

    set_static_map_extent(
        ax,
        geojson=choropleth_geojson,
        dataframe=hotspots,
        extent=extent,
    )

    ax.set_title(
        "Combined Geographic Management View",
        color="white",
        fontsize=16,
        fontweight="bold",
        pad=14,
    )

    total_clusters = (
        len(hotspots)
        if isinstance(
            hotspots,
            pd.DataFrame,
        )
        else 0
    )

    ax.text(
        0.01,
        0.01,
        f"Geographic clusters: {total_clusters:,}",
        transform=ax.transAxes,
        color="#d0d0d0",
        fontsize=9,
    )

    style_static_map_axis(
        ax
    )

    fig.tight_layout()

    return fig


def create_map_export_files(
    map_items,
):
    """
    map_items:
        [
            (
                "filename_without_extension",
                matplotlib_figure
            ),
            ...
        ]

    Returns:
        pdf_bytes,
        zip_bytes
    """

    modules = get_matplotlib_modules()

    if modules is None:
        return None, None

    (
        plt,
        PdfPages,
        _,
        _,
        _,
    ) = modules

    if not map_items:
        return None, None

    pdf_output = io.BytesIO()
    zip_output = io.BytesIO()

    try:

        with PdfPages(
            pdf_output
        ) as pdf:

            with zipfile.ZipFile(
                zip_output,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as zip_file:

                for filename, figure in map_items:

                    if figure is None:
                        continue

                    safe_name = safe_map_filename(
                        filename
                    )

                    png_output = io.BytesIO()

                    figure.savefig(
                        png_output,
                        format="png",
                        dpi=180,
                        bbox_inches="tight",
                        facecolor=figure.get_facecolor(),
                    )

                    png_output.seek(0)

                    zip_file.writestr(
                        f"{safe_name}.png",
                        png_output.getvalue(),
                    )

                    pdf.savefig(
                        figure,
                        bbox_inches="tight",
                        facecolor=figure.get_facecolor(),
                    )

                    plt.close(
                        figure
                    )

        pdf_output.seek(0)
        zip_output.seek(0)

        return (
            pdf_output.getvalue(),
            zip_output.getvalue(),
        )

    except Exception:

        try:
            for _, figure in map_items:
                if figure is not None:
                    plt.close(figure)
        except Exception:
            pass

        return None, None


def render_map_download_controls(
    map_items,
    base_filename,
    key_prefix,
):
    """
    Displays PDF and PNG-ZIP download buttons
    for the maps currently displayed in the active view.
    """

    if not map_items:
        return

    modules = get_matplotlib_modules()

    if modules is None:

        st.warning(
            "Map image/PDF export requires matplotlib. "
            "Please add 'matplotlib' to requirements.txt "
            "and redeploy the application."
        )

        return

    st.markdown(
        "### Download Displayed Maps"
    )

    st.caption(
        "The PDF contains all maps currently displayed "
        "in this view. The ZIP contains one PNG image "
        "for each displayed map."
    )

    pdf_bytes, zip_bytes = (
        create_map_export_files(
            map_items
        )
    )

    if (
        pdf_bytes is None
        or zip_bytes is None
    ):

        st.warning(
            "Map export could not be generated."
        )

        return

    download_col1, download_col2 = (
        st.columns(2)
    )

    with download_col1:

        st.download_button(
            "Download Displayed Maps PDF",
            data=pdf_bytes,
            file_name=(
                f"{base_filename}.pdf"
            ),
            mime="application/pdf",
            key=(
                f"{key_prefix}_pdf"
            ),
        )

    with download_col2:

        st.download_button(
            "Download Displayed Maps PNG Images",
            data=zip_bytes,
            file_name=(
                f"{base_filename}_PNG.zip"
            ),
            mime="application/zip",
            key=(
                f"{key_prefix}_png"
            ),
        )


# ============================================================
# MAIN GEOGRAPHIC MAP
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

    if (
        filtered_df is None
        or not isinstance(filtered_df, pd.DataFrame)
        or filtered_df.empty
    ):
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
            clean_text(value)
            for value in coordinate_df[
                disease_col
            ]
            .dropna()
            .unique()
            if clean_text(value)
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

    # --------------------------------------------------------
    # LOAD BMC GEOJSON ONCE
    # --------------------------------------------------------

    bmc_geojson = load_bmc_wards()

    if bmc_geojson is None:
        st.warning(
            "BMC ward boundary data could not be loaded. "
            "Ward boundaries will not be displayed."
        )

    # --------------------------------------------------------
    # CONTROLS
    # --------------------------------------------------------

    st.markdown(
        "### Map Controls"
    )

    control1, control2, control3 = st.columns(
        [1.15, 2.7, 0.65]
    )

    with control1:
        extent = st.radio(
            "Map Focus",
            [
                "BMC Focus",
                "All Points Focus",
            ],
            horizontal=False,
            key="geo_extent",
        )

    with control2:
        selected_diseases = (
            disease_selection_control(
                diseases
            )
        )

    with control3:
        st.markdown(
            "<div style='height:28px'></div>",
            unsafe_allow_html=True,
        )

        st.button(
            "Reset",
            key="geo_disease_reset",
            on_click=reset_geo_disease_selection,
            help="Reset disease selection to all diseases",
        )

    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    if selected_diseases:
        map_df = coordinate_df[
            coordinate_df[
                disease_col
            ]
            .map(clean_text)
            .isin(selected_diseases)
        ].copy()
    else:
        map_df = coordinate_df.copy()

    if map_df.empty:
        st.warning(
            "No geographic records are available for the selected diseases."
        )
        return

    # --------------------------------------------------------
    # DATA
    # --------------------------------------------------------

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

    disease_comparison = (
        create_disease_comparison(
            map_df
        )
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    total_cases = len(map_df)

    total_diseases = (
        map_df[disease_col]
        .map(clean_text)
        .nunique()
    )

    total_wards = int(
        (
            ward_summary["Cases"] > 0
        ).sum()
    )

    total_hotspots = (
        len(hotspots)
        if isinstance(
            hotspots,
            pd.DataFrame,
        )
        else 0
    )

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
    # SINGLE ACTIVE VIEW
    # ========================================================

    st.markdown(
        "### Geographic Analysis View"
    )

    active_view = st.radio(
        "Select View",
        [
            "Hotspots",
            "Disease Comparison",
            "Ward Choropleth",
            "Combined Geographic View",
        ],
        horizontal=True,
        key="geo_active_view",
    )

    # ========================================================
    # VIEW 1 — HOTSPOTS
    # ========================================================

    if active_view == "Hotspots":

        st.markdown(
            "### Geographic Hotspots"
        )

        st.caption(
            "Cluster-based geographic hotspot analysis. "
            "Individual case points are not rendered to maintain map performance."
        )

        if (
            hotspots is None
            or not isinstance(
                hotspots,
                pd.DataFrame,
            )
            or hotspots.empty
        ):
            st.info(
                "No geographic hotspots identified."
            )

        else:

            hotspot_map = build_hotspot_map(
                hotspots=hotspots,
                ward_geojson=bmc_geojson,
                extent=extent,
            )

            st.pydeck_chart(
                hotspot_map,
                use_container_width=True,
                height=470,
                key="geo_hotspot_map",
            )

            st.markdown(
                "### Hotspot Summary"
            )

            hotspot_display = (
                hotspots.copy()
            )

            hotspot_display["Cases"] = (
                hotspot_display[
                    "Cluster_Cases"
                ]
            )

            hotspot_display = (
                hotspot_display[
                    [
                        "Latitude",
                        "Longitude",
                        "Cases",
                        "Hotspot_Level",
                    ]
                ]
                .sort_values(
                    "Cases",
                    ascending=False,
                )
            )

            st.dataframe(
                hotspot_display,
                use_container_width=True,
                hide_index=True,
            )

            # ------------------------------------------------
            # MAP IMAGE / PDF DOWNLOAD
            # ------------------------------------------------

            hotspot_static_figure = (
                create_static_hotspot_figure(
                    hotspots=hotspots,
                    ward_geojson=bmc_geojson,
                    extent=extent,
                )
            )

            render_map_download_controls(
                map_items=[
                    (
                        "geographic_hotspots",
                        hotspot_static_figure,
                    )
                ],
                base_filename=(
                    "geographic_hotspots_map"
                ),
                key_prefix=(
                    "geo_hotspot_map_download"
                ),
            )

    # ========================================================
    # VIEW 2 — DISEASE COMPARISON
    # ========================================================

    elif active_view == "Disease Comparison":

        st.markdown(
            "### Disease-wise Geographic Comparison"
        )

        if disease_comparison.empty:

            st.info(
                "No disease comparison data available."
            )

        else:

            comparison_display = (
                disease_comparison.copy()
            )

            comparison_display[
                "Share (%)"
            ] = (
                comparison_display["Cases"]
                / max(total_cases, 1)
                * 100
            ).round(1)

            st.dataframe(
                comparison_display,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # VIEW 3 — WARD CHOROPLETH
    # ========================================================

    elif active_view == "Ward Choropleth":

        st.markdown(
            "### Disease-wise Ward Choropleth"
        )

        st.caption(
            "Select up to 6 diseases. "
            "Selected diseases are displayed in a compact "
            "two-column map and table layout."
        )

        if not isinstance(
            bmc_geojson,
            dict,
        ):

            st.warning(
                "BMC ward boundary data is unavailable."
            )

        elif disease_comparison.empty:

            st.info(
                "No disease data available."
            )

        else:

            comparison_diseases = sorted(
                [
                    clean_text(value)
                    for value in (
                        map_df[disease_col]
                        .dropna()
                        .unique()
                    )
                    if clean_text(value)
                ]
            )

            if not comparison_diseases:

                st.info(
                    "No diseases are available for Ward Choropleth."
                )

            else:

                previous_available = st.session_state.get(
                    "geo_choropleth_last_available",
                    [],
                )

                if previous_available != comparison_diseases:

                    old_selection = (
                        st.session_state.get(
                            "geo_choropleth_selection",
                            [],
                        )
                    )

                    valid_selection = [
                        disease
                        for disease in old_selection
                        if disease in comparison_diseases
                    ]

                    st.session_state[
                        "geo_choropleth_selection"
                    ] = valid_selection

                    st.session_state[
                        "geo_choropleth_last_available"
                    ] = comparison_diseases

                    for old_disease in previous_available:

                        if (
                            old_disease
                            not in comparison_diseases
                        ):

                            old_key = (
                                "geo_choro_checkbox_"
                                + re.sub(
                                    r"[^A-Za-z0-9]+",
                                    "_",
                                    old_disease,
                                )
                            )

                            if old_key in st.session_state:
                                st.session_state[
                                    old_key
                                ] = False

                selected_choropleth_diseases = (
                    render_choropleth_disease_checkboxes(
                        comparison_diseases
                    )
                )

                reset_col, info_col = st.columns(
                    [1, 4]
                )

                with reset_col:

                    if st.button(
                        "Clear Selection",
                        key="geo_choropleth_clear",
                    ):

                        st.session_state[
                            "geo_choropleth_clear_requested"
                        ] = True

                        st.rerun()

                with info_col:

                    if selected_choropleth_diseases:

                        st.success(
                            f"{len(selected_choropleth_diseases)} "
                            "disease map(s) selected."
                        )

                    else:

                        st.info(
                            "Select one or more diseases above "
                            "to display ward choropleth maps."
                        )

                if selected_choropleth_diseases:

                    st.markdown(
                        "### Selected Disease Maps"
                    )

                    choropleth_download_items = []

                    for row_start in range(
                        0,
                        len(
                            selected_choropleth_diseases
                        ),
                        2,
                    ):

                        row_diseases = (
                            selected_choropleth_diseases[
                                row_start:row_start + 2
                            ]
                        )

                        map_columns = st.columns(
                            2,
                            gap="medium",
                        )

                        for column, disease in zip(
                            map_columns,
                            row_diseases,
                        ):

                            with column:

                                disease_df = (
                                    get_disease_map_data(
                                        map_df,
                                        disease,
                                    )
                                )

                                if disease_df.empty:

                                    st.info(
                                        f"No geographic data available "
                                        f"for {disease}."
                                    )

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

                                disease_cases = len(
                                    disease_df
                                )

                                palette = (
                                    get_disease_palette(
                                        disease
                                    )
                                )

                                st.markdown(
                                    f"#### {disease}"
                                )

                                st.caption(
                                    f"{disease_cases:,} cases | "
                                    f"{palette['name']} burden palette"
                                )

                                if disease_choropleth:

                                    disease_map = (
                                        build_choropleth_map(
                                            disease_choropleth
                                        )
                                    )

                                    safe_disease_key = re.sub(
                                        r"[^A-Za-z0-9]+",
                                        "_",
                                        disease,
                                    )

                                    st.pydeck_chart(
                                        disease_map,
                                        use_container_width=True,
                                        height=365,
                                        key=(
                                            "geo_choropleth_grid_"
                                            + str(row_start)
                                            + "_"
                                            + safe_disease_key
                                        ),
                                    )

                                    # --------------------------------
                                    # ADD CURRENT DISPLAYED MAP
                                    # TO IMAGE/PDF EXPORT
                                    # --------------------------------

                                    static_disease_figure = (
                                        create_static_choropleth_figure(
                                            choropleth_geojson=(
                                                disease_choropleth
                                            ),
                                            disease_name=disease,
                                            total_cases=disease_cases,
                                        )
                                    )

                                    choropleth_download_items.append(
                                        (
                                            (
                                                "ward_choropleth_"
                                                + safe_disease_key
                                            ),
                                            static_disease_figure,
                                        )
                                    )

                                else:

                                    st.warning(
                                        "Ward map could not be prepared."
                                    )

                                st.markdown(
                                    "**Ward-wise Burden**"
                                )

                                display_summary = (
                                    disease_ward_summary
                                    .sort_values(
                                        "Cases",
                                        ascending=False,
                                    )
                                    .copy()
                                )

                                display_summary[
                                    "Burden"
                                ] = "Low"

                                if not display_summary.empty:

                                    max_cases = int(
                                        display_summary[
                                            "Cases"
                                        ].max()
                                    )

                                    if max_cases > 0:

                                        display_summary.loc[
                                            display_summary[
                                                "Cases"
                                            ]
                                            >= max_cases * 0.70,
                                            "Burden",
                                        ] = "High"

                                        display_summary.loc[
                                            (
                                                display_summary[
                                                    "Cases"
                                                ]
                                                >= max_cases * 0.35
                                            )
                                            & (
                                                display_summary[
                                                    "Cases"
                                                ]
                                                < max_cases * 0.70
                                            ),
                                            "Burden",
                                        ] = "Moderate"

                                st.dataframe(
                                    display_summary[
                                        [
                                            "Ward",
                                            "Cases",
                                            "Burden",
                                        ]
                                    ],
                                    use_container_width=True,
                                    hide_index=True,
                                    height=260,
                                )

                                st.markdown(
                                    "<div style='height:12px'></div>",
                                    unsafe_allow_html=True,
                                )

                    # ------------------------------------------------
                    # MAP IMAGE / PDF DOWNLOAD
                    # ------------------------------------------------

                    render_map_download_controls(
                        map_items=(
                            choropleth_download_items
                        ),
                        base_filename=(
                            "selected_ward_choropleth_maps"
                        ),
                        key_prefix=(
                            "geo_choropleth_map_download"
                        ),
                    )

                # ------------------------------------------------
                # DISPLAYED DATA DOWNLOAD
                # ------------------------------------------------

                st.markdown(
                    "### Download Displayed Ward Choropleth Data"
                )

                if selected_choropleth_diseases:

                    choropleth_export = (
                        download_choropleth_data(
                            map_df,
                            selected_choropleth_diseases,
                        )
                    )

                    st.download_button(
                        "Download Displayed Disease Maps Data",
                        data=choropleth_export,
                        file_name=(
                            "ward_choropleth_selected_diseases.xlsx"
                        ),
                        mime=(
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                        key="geo_choropleth_export_excel",
                    )

                    st.caption(
                        "Download contains only the diseases currently "
                        "selected and displayed above."
                    )

    # ========================================================
    # VIEW 4 — COMBINED GEOGRAPHIC VIEW
    # ========================================================

    elif active_view == "Combined Geographic View":

        st.markdown(
            "### Combined Geographic Management View"
        )

        if isinstance(
            bmc_geojson,
            dict,
        ):

            combined_disease_name = (
                selected_diseases[0]
                if len(selected_diseases) == 1
                else "Combined"
            )

            combined_choropleth = (
                prepare_bmc_choropleth(
                    bmc_geojson,
                    ward_summary,
                    disease_name=combined_disease_name,
                )
            )

        else:

            combined_choropleth = None

        combined_map = build_combined_map(
            choropleth_geojson=(
                combined_choropleth
            ),
            hotspots=hotspots,
            extent=extent,
        )

        st.pydeck_chart(
            combined_map,
            use_container_width=True,
            height=500,
            key="geo_combined_map",
        )

        st.markdown(
            "### Ward-wise Burden"
        )

        ward_display = (
            ward_summary
            .sort_values(
                "Cases",
                ascending=False,
            )
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

        # --------------------------------------------------------
        # MAP IMAGE / PDF DOWNLOAD
        # --------------------------------------------------------

        combined_static_figure = (
            create_static_combined_figure(
                choropleth_geojson=(
                    combined_choropleth
                ),
                hotspots=hotspots,
                extent=extent,
            )
        )

        render_map_download_controls(
            map_items=[
                (
                    "combined_geographic_management_map",
                    combined_static_figure,
                )
            ],
            base_filename=(
                "combined_geographic_management_map"
            ),
            key_prefix=(
                "geo_combined_map_download"
            ),
        )

    # ========================================================
    # GENERAL GEOGRAPHIC DATA EXPORT
    # ========================================================

    st.markdown(
        "### Geographic Data Export"
    )

    export_file = (
        download_hotspot_data(
            case_points,
            hotspots,
        )
    )

    st.download_button(
        "Download Geographic Analysis Excel",
        data=export_file,
        file_name=(
            "geographic_disease_analysis.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        key="geo_export_excel",
    )
