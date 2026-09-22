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

# Dark / Black map background
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
# MAP VIEW
# ============================================================

def calculate_view(
    case_points=None,
    extent="BMC Focus",
):
    if (
        case_points is None
        or not isinstance(case_points, pd.DataFrame)
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

    lat_values = (
        pd.to_numeric(
            case_points[LAT_COL],
            errors="coerce",
        )
        .dropna()
        .tolist()
    )

    lon_values = (
        pd.to_numeric(
            case_points[LON_COL],
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
    #
    # IMPORTANT:
    # Only one PyDeck map is rendered at a time.
    # This prevents multiple WebGL contexts.
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
            "High burden areas are shown with stronger "
            "disease-specific colours. Low burden areas are shown faintly."
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

            comparison_diseases = (
                selected_diseases
                if selected_diseases
                else diseases
            )

            selected_map_disease = st.selectbox(
                "Disease Map",
                comparison_diseases,
                key="geo_choropleth_disease",
            )

            disease_df = (
                get_disease_map_data(
                    map_df,
                    selected_map_disease,
                )
            )

            if disease_df.empty:

                st.info(
                    f"No geographic data available for "
                    f"{selected_map_disease}."
                )

            else:

                disease_ward_summary = (
                    create_ward_summary(
                        disease_df
                    )
                )

                disease_choropleth = (
                    prepare_bmc_choropleth(
                        bmc_geojson,
                        disease_ward_summary,
                        disease_name=selected_map_disease,
                    )
                )

                disease_cases = len(
                    disease_df
                )

                palette = (
                    get_disease_palette(
                        selected_map_disease
                    )
                )

                st.markdown(
                    f"#### {selected_map_disease}"
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

                    st.pydeck_chart(
                        disease_map,
                        use_container_width=True,
                        height=500,
                        key=(
                            "geo_choropleth_active_"
                            + re.sub(
                                r"[^A-Za-z0-9]+",
                                "_",
                                selected_map_disease,
                            )
                        ),
                    )

                else:

                    st.warning(
                        "Ward map could not be prepared."
                    )

                st.markdown(
                    "### Ward-wise Burden"
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
                    display_summary,
                    use_container_width=True,
                    hide_index=True,
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

        # ----------------------------------------------------
        # WARD BURDEN
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # DISEASE BURDEN
        # ----------------------------------------------------

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
        key="geo_export_excel",
    )
