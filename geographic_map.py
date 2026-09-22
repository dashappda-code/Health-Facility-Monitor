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
                str(candidate)
                .strip()
                .lower()
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

    cleaned = re.sub(
        r"\bWARD\b",
        " ",
        text,
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()

    compact_cleaned = cleaned.replace(
        " ",
        "",
    )

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

    if (
        LAT_COL not in df.columns
        or LON_COL not in df.columns
    ):
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
        subset=[
            LAT_COL,
            LON_COL,
        ]
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

    if disease_col:
        work["Disease"] = (
            work[disease_col].map(clean_text)
        )
    else:
        work["Disease"] = "Unknown"

    if ward_col:
        work["Ward"] = (
            work[ward_col].map(normalise_ward)
        )
    else:
        work["Ward"] = ""

    if facility_col:
        work["Facility"] = (
            work[facility_col].map(clean_text)
        )
    else:
        work["Facility"] = ""

    if case_id_col:
        work["Case_ID"] = (
            work[case_id_col].map(clean_text)
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

    if (
        hotspots is not None
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
                int(
                    counts.get(
                        ward,
                        0,
                    )
                )
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
        or ward_summary.empty
    ):
        return pd.DataFrame(
            columns=[
                "Ward",
                "Cases",
            ]
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
        ~summary["Ward"].isin(
            [
                "PE",
                "PN",
            ]
        )
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
        "returnM": "false",
        "returnZ": "false",
        "outSR": "4326",
        "f": "geojson",
    }

    try:
        response = requests.get(
            BMC_WARD_URL + "/query",
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(
            data,
            dict,
        ):
            return None

        if data.get("type") != "FeatureCollection":
            return None

        lightweight_features = []

        for feature in data.get(
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

            ward = get_geojson_ward_name(
                properties
            )

            if geometry is None:
                continue

            lightweight_features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "Ward": ward
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "features": lightweight_features,
        }

    except Exception:
        return None


# ============================================================
# GEOJSON WARD NAME
# ============================================================

def get_geojson_ward_name(properties):
    if not isinstance(
        properties,
        dict,
    ):
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


def get_disease_palette(
    disease_name=None
):
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

    if (
        cases <= 0
        or max_cases <= 0
    ):
        return [
            245,
            245,
            245,
            100,
        ]

    ratio = cases / max_cases

    ratio = max(
        0.0,
        min(
            1.0,
            ratio,
        ),
    )

    light = palette["light"]
    mid = palette["mid"]
    dark = palette["dark"]

    if ratio <= 0.5:

        local_ratio = (
            ratio / 0.5
        )

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
        200,
    ]


# ============================================================
# CHOROPLETH PREPARATION
# ============================================================

def prepare_bmc_choropleth(
    geojson,
    ward_summary,
    disease_name=None,
):
    if not geojson:
        return None

    if (
        ward_summary is None
        or ward_summary.empty
    ):
        return None

    map_summary = (
        create_map_ward_summary(
            ward_summary
        )
    )

    ward_cases = dict(
        zip(
            map_summary["Ward"],
            map_summary["Cases"],
        )
    )

    if map_summary.empty:
        max_cases = 0
    else:
        max_cases = int(
            map_summary["Cases"].max()
        )

    palette = get_disease_palette(
        disease_name
    )

    features = []

    for feature in geojson.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry"
        )

        if geometry is None:
            continue

        source_properties = (
            feature.get(
                "properties",
                {},
            )
        )

        detected_ward = (
            get_geojson_ward_name(
                source_properties
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

        new_properties = {
            "ProgrammeWard": (
                detected_ward
                if detected_ward
                else "Unmatched"
            ),
            "MapWard": map_ward,
            "ProgrammeCases": cases,
            "Disease": (
                clean_text(
                    disease_name
                )
                if disease_name
                else "Combined"
            ),
            "fill_color": (
                get_choropleth_color(
                    cases,
                    max_cases,
                    palette,
                )
            ),
            "line_color": [
                80,
                80,
                80,
                220,
            ],
        }

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": new_properties,
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


# ============================================================
# DISEASE SELECTION
# ============================================================

def reset_geo_disease_selection():
    st.session_state[
        "geo_disease_selection"
    ] = []


def disease_selection_control(
    diseases
):
    diseases = [
        clean_text(disease)
        for disease in diseases
        if clean_text(disease)
    ]

    diseases = list(
        dict.fromkeys(diseases)
    )

    if not diseases:
        return []

    signature = "|".join(
        diseases
    )

    previous_signature = (
        st.session_state.get(
            "geo_disease_options_signature"
        )
    )

    if (
        previous_signature
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
        placeholder="All diseases (default)",
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
# PYDECK CREATION
# ============================================================

def create_deck(
    layers,
    latitude=19.0760,
    longitude=72.8777,
    zoom=10.3,
    tooltip=None,
):
    view_state = pdk.ViewState(
        latitude=float(latitude),
        longitude=float(longitude),
        zoom=float(zoom),
        pitch=0,
        bearing=0,
    )

    deck_kwargs = {
        "layers": layers,
        "initial_view_state": view_state,
    }

    if tooltip:
        deck_kwargs["tooltip"] = tooltip

    # Preferred configuration
    try:
        return pdk.Deck(
            map_provider="carto",
            map_style="light",
            **deck_kwargs,
        )

    except TypeError:

        # Compatibility fallback
        return pdk.Deck(
            map_style="light",
            **deck_kwargs,
        )


# ============================================================
# HOTSPOT MAP
# ============================================================

def build_hotspot_map(
    hotspots,
    ward_geojson=None,
    extent="BMC / Mumbai Focus",
):
    layers = []

    # Ward boundaries only
    if ward_geojson:

        boundary_layer = pdk.Layer(
            "GeoJsonLayer",
            data=ward_geojson,
            pickable=False,
            stroked=True,
            filled=False,
            get_line_color=[
                90,
                90,
                90,
                200,
            ],
            line_width_min_pixels=1,
        )

        layers.append(
            boundary_layer
        )

    # Hotspot clusters only
    if (
        hotspots is not None
        and not hotspots.empty
    ):

        hotspot_layer = pdk.Layer(
            "ScatterplotLayer",
            data=hotspots,
            get_position=[
                "Longitude",
                "Latitude",
            ],
            get_radius="Display_Radius",
            get_fill_color=[
                210,
                40,
                40,
                90,
            ],
            get_line_color=[
                160,
                0,
                0,
                210,
            ],
            stroked=True,
            filled=True,
            pickable=True,
            radius_min_pixels=5,
            radius_max_pixels=35,
        )

        layers.append(
            hotspot_layer
        )

    center_lat = 19.0760
    center_lon = 72.8777
    zoom = 10.3

    if (
        extent == "All Coordinates"
        and hotspots is not None
        and not hotspots.empty
    ):

        center_lat = float(
            hotspots["Latitude"].mean()
        )

        center_lon = float(
            hotspots["Longitude"].mean()
        )

    tooltip = {
        "html": """
        <b>Cluster Cases:</b> {Cluster_Cases}<br/>
        <b>Hotspot Level:</b> {Hotspot_Level}<br/>
        <b>Latitude:</b> {Latitude}<br/>
        <b>Longitude:</b> {Longitude}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black",
        },
    }

    return create_deck(
        layers=layers,
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
        tooltip=tooltip,
    )


# ============================================================
# CHOROPLETH MAP
# ============================================================

def build_choropleth_map(
    choropleth_geojson,
):
    if not choropleth_geojson:
        return None

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=choropleth_geojson,
        pickable=True,
        stroked=True,
        filled=True,
        get_fill_color=(
            "properties.fill_color"
        ),
        get_line_color=(
            "properties.line_color"
        ),
        line_width_min_pixels=1,
        opacity=0.86,
        auto_highlight=True,
    )

    tooltip = {
        "html": """
        <b>Ward:</b> {ProgrammeWard}<br/>
        <b>Cases:</b> {ProgrammeCases}<br/>
        <b>Disease:</b> {Disease}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black",
        },
    }

    return create_deck(
        layers=[layer],
        latitude=19.0760,
        longitude=72.8777,
        zoom=10.3,
        tooltip=tooltip,
    )


# ============================================================
# COMBINED MAP
# ============================================================

def build_combined_map(
    choropleth_geojson=None,
    hotspots=None,
):
    layers = []

    if choropleth_geojson:

        choropleth_layer = pdk.Layer(
            "GeoJsonLayer",
            data=choropleth_geojson,
            pickable=True,
            stroked=True,
            filled=True,
            get_fill_color=(
                "properties.fill_color"
            ),
            get_line_color=(
                "properties.line_color"
            ),
            line_width_min_pixels=1,
            opacity=0.74,
            auto_highlight=True,
        )

        layers.append(
            choropleth_layer
        )

    if (
        hotspots is not None
        and not hotspots.empty
    ):

        hotspot_layer = pdk.Layer(
            "ScatterplotLayer",
            data=hotspots,
            get_position=[
                "Longitude",
                "Latitude",
            ],
            get_radius="Display_Radius",
            get_fill_color=[
                220,
                30,
                30,
                75,
            ],
            get_line_color=[
                170,
                0,
                0,
                190,
            ],
            stroked=True,
            filled=True,
            pickable=True,
            radius_min_pixels=5,
            radius_max_pixels=30,
        )

        layers.append(
            hotspot_layer
        )

    tooltip = {
        "html": """
        <b>Ward:</b> {ProgrammeWard}<br/>
        <b>Cases:</b> {ProgrammeCases}<br/>
        <b>Disease:</b> {Disease}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black",
        },
    }

    return create_deck(
        layers=layers,
        latitude=19.0760,
        longitude=72.8777,
        zoom=10.3,
        tooltip=tooltip,
    )


# ============================================================
# DISEASE COMPARISON
# ============================================================

def create_disease_comparison(df):
    disease_col = get_disease_column(
        df
    )

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


def get_disease_map_data(
    df,
    disease,
):
    disease_col = get_disease_column(
        df
    )

    if disease_col is None:
        return pd.DataFrame()

    mask = (
        df[disease_col]
        .map(clean_text)
        == clean_text(disease)
    )

    return df.loc[
        mask
    ].copy()


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

    # ========================================================
    # LOAD BMC GEOJSON
    # ========================================================

    bmc_geojson = load_bmc_wards()

    if bmc_geojson is None:

        st.warning(
            "BMC ward boundary data could not be loaded. "
            "Maps will continue without ward boundaries."
        )

    # ========================================================
    # CONTROLS
    # ========================================================

    st.markdown(
        "### Map Controls"
    )

    control1, control2, control3 = st.columns(
        [
            1.3,
            2.5,
            0.55,
        ]
    )

    with control1:

        extent = st.radio(
            "Map Extent",
            [
                "BMC / Mumbai Focus",
                "All Coordinates",
            ],
            horizontal=True,
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
            on_click=(
                reset_geo_disease_selection
            ),
            help=(
                "Reset disease selection "
                "to all diseases"
            ),
        )

    # ========================================================
    # FILTER DATA
    # ========================================================

    if selected_diseases:

        map_df = coordinate_df[
            coordinate_df[
                disease_col
            ]
            .map(clean_text)
            .isin(
                selected_diseases
            )
        ].copy()

    else:

        map_df = coordinate_df.copy()

    # ========================================================
    # CREATE ANALYSIS DATA
    # ========================================================

    hotspots = create_hotspots(
        map_df
    )

    # Case points are still prepared for Excel export,
    # but NOT rendered automatically on the map.
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

    # ========================================================
    # KPI
    # ========================================================

    total_cases = len(
        map_df
    )

    total_diseases = (
        map_df[disease_col]
        .map(clean_text)
        .nunique()
    )

    total_wards = (
        ward_summary.loc[
            ward_summary["Cases"] > 0,
            "Ward",
        ]
        .nunique()
    )

    total_hotspots = (
        len(hotspots)
        if hotspots is not None
        else 0
    )

    k1, k2, k3, k4 = st.columns(
        4
    )

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
    # TAB 1 — HOTSPOTS
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

            hotspot_map = (
                build_hotspot_map(
                    hotspots=hotspots,
                    ward_geojson=bmc_geojson,
                    extent=extent,
                )
            )

            st.pydeck_chart(
                hotspot_map,
                use_container_width=True,
                height=430,
                key="geo_hotspot_map_v2",
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

    # ========================================================
    # TAB 2 — DISEASE COMPARISON
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
    # TAB 3 — CHOROPLETH COMPARISON
    # ========================================================

    with tab3:

        st.markdown(
            "### Disease-wise Ward Choropleth"
        )

        st.caption(
            "Two lightweight ward-level maps are displayed "
            "per row. Each map contains only the ward polygon "
            "layer to minimise browser rendering load."
        )

        if not bmc_geojson:

            st.warning(
                "BMC ward boundary data is unavailable."
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

            # ------------------------------------------------
            # TWO MAPS PER ROW
            # ------------------------------------------------

            for row_start in range(
                0,
                len(
                    comparison_diseases
                ),
                2,
            ):

                row_diseases = (
                    comparison_diseases[
                        row_start:
                        row_start + 2
                    ]
                )

                columns = st.columns(
                    2,
                    gap="medium",
                )

                for index, disease in enumerate(
                    row_diseases
                ):

                    with columns[index]:

                        disease_df = (
                            get_disease_map_data(
                                map_df,
                                disease,
                            )
                        )

                        if disease_df.empty:

                            st.info(
                                f"No data available for {disease}."
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

                        disease_cases = (
                            len(
                                disease_df
                            )
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
                            f"{palette['name']} palette"
                        )

                        if disease_choropleth:

                            disease_map = (
                                build_choropleth_map(
                                    disease_choropleth
                                )
                            )

                            safe_disease = (
                                re.sub(
                                    r"[^A-Za-z0-9]+",
                                    "_",
                                    disease,
                                )
                            )

                            st.pydeck_chart(
                                disease_map,
                                use_container_width=True,
                                height=330,
                                key=(
                                    "geo_choro_v2_"
                                    + str(row_start)
                                    + "_"
                                    + str(index)
                                    + "_"
                                    + safe_disease
                                ),
                            )

                        else:

                            st.warning(
                                "Ward map could not be prepared."
                            )

                        # Data immediately below map
                        display_summary = (
                            disease_ward_summary[
                                disease_ward_summary[
                                    "Cases"
                                ] > 0
                            ]
                            .sort_values(
                                "Cases",
                                ascending=False,
                            )
                            .copy()
                        )

                        if display_summary.empty:

                            st.info(
                                "No ward-level cases available."
                            )

                        else:

                            st.dataframe(
                                display_summary,
                                use_container_width=True,
                                hide_index=True,
                                height=190,
                            )

                if (
                    row_start + 2
                    < len(
                        comparison_diseases
                    )
                ):

                    st.markdown(
                        "<hr>",
                        unsafe_allow_html=True,
                    )

    # ========================================================
    # TAB 4 — COMBINED VIEW
    # ========================================================

    with tab4:

        st.markdown(
            "### Combined Geographic Management View"
        )

        if bmc_geojson:

            combined_disease_name = (
                selected_diseases[0]
                if len(
                    selected_diseases
                ) == 1
                else "Combined"
            )

            combined_choropleth = (
                prepare_bmc_choropleth(
                    bmc_geojson,
                    ward_summary,
                    disease_name=(
                        combined_disease_name
                    ),
                )
            )

        else:

            combined_choropleth = None

        combined_map = (
            build_combined_map(
                choropleth_geojson=(
                    combined_choropleth
                ),
                hotspots=hotspots,
            )
        )

        st.pydeck_chart(
            combined_map,
            use_container_width=True,
            height=460,
            key="geo_combined_map_v2",
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

    # ========================================================
    # EXPORT
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
        key="geo_export_excel_v2",
    )
