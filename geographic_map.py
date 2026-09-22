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
    "https://services8.arcgis.com/"
    "r6MmJtuWAzMawmJ8/arcgis/rest/services/"
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
    "S", "T"
]


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(value):

    if pd.isna(value):
        return ""

    text = str(value).strip().upper()

    text = text.replace("&", " AND ")
    text = text.replace("-", " ")
    text = text.replace("_", " ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def find_column(df, candidates):

    if df is None or df.empty:
        return None

    columns = list(df.columns)

    for candidate in candidates:

        for col in columns:

            if (
                str(col).strip().lower()
                ==
                candidate.strip().lower()
            ):
                return col

    for candidate in candidates:

        candidate_clean = candidate.strip().lower()

        for col in columns:

            if candidate_clean in str(col).strip().lower():
                return col

    return None


# ============================================================
# WARD NORMALISATION
# ============================================================

WARD_MAP = {

    "A": "A",
    "B": "B",
    "C": "C",
    "D": "D",
    "E": "E",

    "F NORTH": "FN",
    "FN": "FN",

    "F SOUTH": "FS",
    "FS": "FS",

    "G NORTH": "GN",
    "GN": "GN",

    "G SOUTH": "GS",
    "GS": "GS",

    "H EAST": "HE",
    "HE": "HE",

    "H WEST": "HW",
    "HW": "HW",

    "K EAST": "KE",
    "KE": "KE",

    "K WEST": "KW",
    "KW": "KW",

    "L": "L",

    "M EAST": "ME",
    "ME": "ME",

    "M WEST": "MW",
    "MW": "MW",

    "P EAST": "PE",
    "P E": "PE",
    "PE": "PE",

    "P NORTH": "PN",
    "P N": "PN",
    "PN": "PN",

    "P SOUTH": "PS",
    "P S": "PS",
    "PS": "PS",

    "R CENTRAL": "RC",
    "R C": "RC",
    "RC": "RC",

    "R NORTH": "RN",
    "R N": "RN",
    "RN": "RN",

    "R SOUTH": "RS",
    "R S": "RS",
    "RS": "RS",

    "N": "N",
    "S": "S",
    "T": "T",
}


def normalise_ward(value):

    text = clean_text(value)

    if not text:
        return ""

    text = re.sub(
        r"\bWARD\b",
        "",
        text
    )

    text = re.sub(
        r"\bBMC\b",
        "",
        text
    )

    text = re.sub(
        r"\bMCGM\b",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    if text in WARD_MAP:
        return WARD_MAP[text]

    patterns = [

        (r"\bF\s*NORTH\b", "FN"),
        (r"\bF\s*SOUTH\b", "FS"),

        (r"\bG\s*NORTH\b", "GN"),
        (r"\bG\s*SOUTH\b", "GS"),

        (r"\bH\s*EAST\b", "HE"),
        (r"\bH\s*WEST\b", "HW"),

        (r"\bK\s*EAST\b", "KE"),
        (r"\bK\s*WEST\b", "KW"),

        (r"\bM\s*EAST\b", "ME"),
        (r"\bM\s*WEST\b", "MW"),

        (r"\bP\s*EAST\b", "PE"),
        (r"\bP\s*NORTH\b", "PN"),
        (r"\bP\s*SOUTH\b", "PS"),

        (r"\bR\s*CENTRAL\b", "RC"),
        (r"\bR\s*NORTH\b", "RN"),
        (r"\bR\s*SOUTH\b", "RS"),
    ]

    for pattern, code in patterns:

        if re.search(pattern, text):
            return code

    compact = text.replace(" ", "")

    if compact in PROGRAMME_WARDS:
        return compact

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
            "Disease name",
            "DiseaseName",
            "disease",
            "disease_name",
        ]
    )


def get_ward_column(df):

    return find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "Ward_Name",
            "Wardname",
            "ward",
            "ward_name",
            "Administrative Ward",
            "Administrative_Ward",
            "Programme Ward",
            "Programme_Ward",
        ]
    )


# ============================================================
# COORDINATE PREPARATION
# ============================================================

def prepare_coordinates(df):

    if df is None or df.empty:
        return pd.DataFrame(), 0, 0

    if (
        LAT_COL not in df.columns
        or
        LON_COL not in df.columns
    ):
        return (
            pd.DataFrame(),
            len(df),
            0
        )

    out = df.copy()

    out[LAT_COL] = pd.to_numeric(
        out[LAT_COL],
        errors="coerce"
    )

    out[LON_COL] = pd.to_numeric(
        out[LON_COL],
        errors="coerce"
    )

    valid_mask = (
        out[LAT_COL].notna()
        &
        out[LON_COL].notna()
        &
        out[LAT_COL].between(-90, 90)
        &
        out[LON_COL].between(-180, 180)
    )

    valid_df = out.loc[
        valid_mask
    ].copy()

    invalid_count = int(
        (~valid_mask).sum()
    )

    valid_count = int(
        valid_mask.sum()
    )

    return (
        valid_df,
        invalid_count,
        valid_count
    )


# ============================================================
# BOUNDARY
# ============================================================

@st.cache_data(
    ttl=86400,
    show_spinner=False
)
def load_bmc_wards():

    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }

    try:

        response = requests.get(
            BMC_WARD_URL + "/query",
            params=params,
            timeout=8
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("features"):
            return None

        return data

    except Exception:

        return None


def get_geojson_ward_name(properties):

    if not properties:
        return ""

    candidates = [
        "NAME",
        "WARD_NAME",
        "Ward",
        "WARD",
        "ward",
        "Name",
        "Ward_Name",
        "WARDNAME",
        "WardName",
        "WARD_NO",
        "WARD_CODE",
        "WARDCODE",
        "WARD_ID",
        "WNO",
    ]

    for key in candidates:

        if key in properties:

            ward = normalise_ward(
                properties.get(key)
            )

            if ward:
                return ward

    return ""


# ============================================================
# POINT IN POLYGON
# ============================================================

def point_in_ring(
    lon,
    lat,
    ring
):

    inside = False

    if not ring:
        return False

    j = len(ring) - 1

    for i in range(len(ring)):

        try:

            xi = float(ring[i][0])
            yi = float(ring[i][1])

            xj = float(ring[j][0])
            yj = float(ring[j][1])

        except Exception:

            j = i
            continue

        if (
            (yi > lat)
            !=
            (yj > lat)
        ):

            x_intersection = (
                (xj - xi)
                *
                (lat - yi)
                /
                (
                    (yj - yi)
                    if (yj - yi) != 0
                    else 1e-12
                )
                + xi
            )

            if lon < x_intersection:

                inside = not inside

        j = i

    return inside


def point_in_polygon(
    lon,
    lat,
    coordinates
):

    if not coordinates:
        return False

    try:

        if isinstance(
            coordinates[0][0][0],
            (int, float)
        ):

            outer = coordinates[0]

            if not point_in_ring(
                lon,
                lat,
                outer
            ):
                return False

            for hole in coordinates[1:]:

                if point_in_ring(
                    lon,
                    lat,
                    hole
                ):
                    return False

            return True

    except Exception:
        pass

    for polygon in coordinates:

        if point_in_polygon(
            lon,
            lat,
            polygon
        ):
            return True

    return False


def assign_boundary_ward(
    lon,
    lat,
    geojson
):

    if not geojson:
        return ""

    for feature in geojson.get(
        "features",
        []
    ):

        geometry = feature.get(
            "geometry"
        ) or {}

        geom_type = geometry.get(
            "type"
        )

        coordinates = geometry.get(
            "coordinates"
        )

        if not coordinates:
            continue

        inside = False

        try:

            if geom_type == "Polygon":

                inside = point_in_polygon(
                    lon,
                    lat,
                    coordinates
                )

            elif geom_type == "MultiPolygon":

                for polygon in coordinates:

                    if point_in_polygon(
                        lon,
                        lat,
                        polygon
                    ):

                        inside = True
                        break

        except Exception:

            inside = False

        if inside:

            return get_geojson_ward_name(
                feature.get(
                    "properties",
                    {}
                )
            )

    return ""


def spatially_resolve_wards(
    df,
    geojson
):

    if df is None or df.empty:
        return df

    out = df.copy()

    ward_col = get_ward_column(
        out
    )

    if ward_col:

        out["_Report_Ward"] = (
            out[ward_col]
            .apply(normalise_ward)
        )

    else:

        out["_Report_Ward"] = ""

    out["_Map_Ward"] = (
        out["_Report_Ward"]
        .copy()
    )

    if geojson is None:
        return out

    mask = (
        out["_Map_Ward"].isin(
            ["PS", ""]
        )
    )

    if LAT_COL not in out.columns:
        return out

    if LON_COL not in out.columns:
        return out

    for idx in out.index[mask]:

        try:

            lat = float(
                out.at[
                    idx,
                    LAT_COL
                ]
            )

            lon = float(
                out.at[
                    idx,
                    LON_COL
                ]
            )

        except Exception:

            continue

        spatial_ward = (
            assign_boundary_ward(
                lon,
                lat,
                geojson
            )
        )

        if spatial_ward:

            out.at[
                idx,
                "_Map_Ward"
            ] = spatial_ward

    return out


# ============================================================
# MAP WARD
# PE + PN COMBINED ONLY FOR CHOROPLETH
# ============================================================

def map_ward(value):

    ward = normalise_ward(value)

    if ward in [
        "PE",
        "PN"
    ]:

        return "P"

    return ward


# ============================================================
# INDIVIDUAL CASE POINTS
# ============================================================

def create_case_points(
    df
):

    if df is None or df.empty:
        return pd.DataFrame()

    if (
        LAT_COL not in df.columns
        or
        LON_COL not in df.columns
    ):
        return pd.DataFrame()

    points = df.copy()

    points[LAT_COL] = pd.to_numeric(
        points[LAT_COL],
        errors="coerce"
    )

    points[LON_COL] = pd.to_numeric(
        points[LON_COL],
        errors="coerce"
    )

    points = points.dropna(
        subset=[
            LAT_COL,
            LON_COL
        ]
    ).copy()

    if points.empty:
        return pd.DataFrame()

    disease_col = get_disease_column(
        points
    )

    ward_col = get_ward_column(
        points
    )

    output = pd.DataFrame()

    output["Latitude"] = points[
        LAT_COL
    ].astype(float)

    output["Longitude"] = points[
        LON_COL
    ].astype(float)

    if disease_col:

        output["Disease"] = (
            points[disease_col]
            .astype(str)
            .str.strip()
        )

    else:

        output["Disease"] = "Unknown"

    if "_Report_Ward" in points.columns:

        output["Ward"] = (
            points["_Report_Ward"]
            .apply(normalise_ward)
        )

    elif ward_col:

        output["Ward"] = (
            points[ward_col]
            .apply(normalise_ward)
        )

    else:

        output["Ward"] = ""

    output["Map_Ward"] = (
        output["Ward"]
        .apply(map_ward)
    )

    output["Case_ID"] = range(
        1,
        len(output) + 1
    )

    return output


# ============================================================
# HOTSPOTS
# ============================================================

def create_hotspots(df):

    if df is None or df.empty:
        return pd.DataFrame()

    if (
        LAT_COL not in df.columns
        or
        LON_COL not in df.columns
    ):
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
        subset=[
            LAT_COL,
            LON_COL
        ]
    )

    if work.empty:
        return pd.DataFrame()

    work["_grid_lat"] = (
        work[LAT_COL]
        / GRID_SIZE
    ).round() * GRID_SIZE

    work["_grid_lon"] = (
        work[LON_COL]
        / GRID_SIZE
    ).round() * GRID_SIZE

    grouped = (
        work
        .groupby(
            [
                "_grid_lat",
                "_grid_lon"
            ],
            as_index=False
        )
        .size()
        .rename(
            columns={
                "size": "Cluster_Cases"
            }
        )
    )

    grouped["Cluster_ID"] = (
        grouped[
            "_grid_lat"
        ].round(4).astype(str)
        +
        "_"
        +
        grouped[
            "_grid_lon"
        ].round(4).astype(str)
    )

    grouped["Hotspot"] = grouped[
        "Cluster_Cases"
    ].apply(
        lambda x:
            "High"
            if x >= 10
            else (
                "Moderate"
                if x >= 5
                else "Low"
            )
    )

    grouped["Latitude"] = (
        grouped["_grid_lat"]
    )

    grouped["Longitude"] = (
        grouped["_grid_lon"]
    )

    return grouped[
        [
            "Cluster_ID",
            "Latitude",
            "Longitude",
            "Cluster_Cases",
            "Hotspot",
        ]
    ]


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):

    summary = pd.DataFrame(
        {
            "Ward": PROGRAMME_WARDS,
            "Cases": [0] * len(
                PROGRAMME_WARDS
            ),
        }
    )

    if df is None or df.empty:
        return summary

    if "_Report_Ward" in df.columns:

        ward_series = (
            df["_Report_Ward"]
            .apply(normalise_ward)
        )

    else:

        ward_col = get_ward_column(
            df
        )

        if not ward_col:
            return summary

        ward_series = (
            df[ward_col]
            .apply(normalise_ward)
        )

    counts = ward_series.value_counts()

    summary["Cases"] = (
        summary["Ward"]
        .map(counts)
        .fillna(0)
        .astype(int)
    )

    return summary


# ============================================================
# MAP WARD SUMMARY
# PE + PN COMBINED
# ============================================================

def create_map_ward_summary(df):

    map_wards = [
        x
        for x in PROGRAMME_WARDS
        if x not in [
            "PE",
            "PN"
        ]
    ]

    map_wards.append("P")

    summary = pd.DataFrame(
        {
            "Ward": map_wards,
            "Cases": [0] * len(
                map_wards
            ),
        }
    )

    if df is None or df.empty:
        return summary

    if "_Report_Ward" in df.columns:

        ward_series = (
            df["_Report_Ward"]
            .apply(normalise_ward)
            .apply(map_ward)
        )

    elif "_Map_Ward" in df.columns:

        ward_series = (
            df["_Map_Ward"]
            .apply(normalise_ward)
            .apply(map_ward)
        )

    else:

        ward_col = get_ward_column(
            df
        )

        if not ward_col:
            return summary

        ward_series = (
            df[ward_col]
            .apply(normalise_ward)
            .apply(map_ward)
        )

    counts = ward_series.value_counts()

    summary["Cases"] = (
        summary["Ward"]
        .map(counts)
        .fillna(0)
        .astype(int)
    )

    return summary


# ============================================================
# CHOROPLETH
# ============================================================

def get_choropleth_color(
    cases,
    max_cases
):

    cases = float(cases)

    if cases <= 0:

        return [
            245,
            245,
            245,
            80
        ]

    if max_cases <= 0:

        return [
            255,
            225,
            90,
            160
        ]

    ratio = (
        cases
        /
        max_cases
    )

    if ratio >= 0.75:

        return [
            180,
            0,
            0,
            190
        ]

    if ratio >= 0.50:

        return [
            235,
            90,
            20,
            180
        ]

    if ratio >= 0.25:

        return [
            255,
            170,
            40,
            170
        ]

    return [
        255,
        225,
        90,
        150
    ]


def prepare_bmc_choropleth(
    geojson,
    ward_summary
):

    if not geojson:
        return None

    result = {
        "type": "FeatureCollection",
        "features": [],
    }

    case_map = dict(
        zip(
            ward_summary["Ward"],
            ward_summary["Cases"]
        )
    )

    max_cases = float(
        ward_summary["Cases"].max()
    ) if not ward_summary.empty else 0

    for feature in geojson.get(
        "features",
        []
    ):

        properties = dict(
            feature.get(
                "properties",
                {}
            )
        )

        ward = get_geojson_ward_name(
            properties
        )

        choropleth_ward = map_ward(
            ward
        )

        cases = int(
            case_map.get(
                choropleth_ward,
                0
            )
        )

        properties[
            "Programme_Cases"
        ] = cases

        properties[
            "Ward_Display"
        ] = (
            ward
            if ward
            else "Unknown"
        )

        properties[
            "fill_color"
        ] = get_choropleth_color(
            cases,
            max_cases
        )

        properties[
            "line_color"
        ] = [
            20,
            20,
            20,
            220
        ]

        properties[
            "line_width"
        ] = 2

        new_feature = dict(
            feature
        )

        new_feature[
            "properties"
        ] = properties

        result[
            "features"
        ].append(
            new_feature
        )

    return result


# ============================================================
# MAP BUILDER
# ============================================================

def build_map(
    geojson=None,
    hotspots=None,
    case_points=None,
    center_mode="BMC / Mumbai Focus",
):

    layers = []

    # --------------------------------------------------------
    # WARD POLYGONS
    # --------------------------------------------------------

    if geojson:

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",

                data=geojson,

                pickable=True,

                stroked=True,

                filled=True,

                get_fill_color=(
                    "properties.fill_color"
                ),

                get_line_color=(
                    "properties.line_color"
                ),

                get_line_width=(
                    "properties.line_width"
                ),

                line_width_min_pixels=1,

                opacity=0.48,
            )
        )

    # --------------------------------------------------------
    # HOTSPOTS
    # --------------------------------------------------------

    if (
        hotspots is not None
        and
        not hotspots.empty
    ):

        layers.append(
            pdk.Layer(

                "ScatterplotLayer",

                data=hotspots,

                pickable=True,

                get_position=[
                    "Longitude",
                    "Latitude"
                ],

                get_radius=(
                    "35 + "
                    "min("
                    "Cluster_Cases * 4,"
                    "80)"
                ),

                radius_min_pixels=2,

                radius_max_pixels=8,

                get_fill_color=[
                    220,
                    40,
                    40,
                    65
                ],

                get_line_color=[
                    150,
                    0,
                    0,
                    120
                ],

                stroked=True,

                filled=True,
            )
        )

    # --------------------------------------------------------
    # CASE POINTS
    # --------------------------------------------------------

    if (
        case_points is not None
        and
        not case_points.empty
    ):

        pe_points = case_points[
            case_points["Ward"] == "PE"
        ].copy()

        pn_points = case_points[
            case_points["Ward"] == "PN"
        ].copy()

        other_points = case_points[
            ~case_points["Ward"].isin(
                [
                    "PE",
                    "PN"
                ]
            )
        ].copy()

        # ----------------------------------------------------
        # PE
        # ----------------------------------------------------

        if not pe_points.empty:

            layers.append(
                pdk.Layer(

                    "ScatterplotLayer",

                    data=pe_points,

                    pickable=True,

                    get_position=[
                        "Longitude",
                        "Latitude"
                    ],

                    get_radius=24,

                    radius_min_pixels=2,

                    radius_max_pixels=6,

                    get_fill_color=[
                        20,
                        100,
                        220,
                        235
                    ],

                    get_line_color=[
                        0,
                        40,
                        100,
                        240
                    ],

                    stroked=True,

                    filled=True,
                )
            )

        # ----------------------------------------------------
        # PN
        # ----------------------------------------------------

        if not pn_points.empty:

            layers.append(
                pdk.Layer(

                    "ScatterplotLayer",

                    data=pn_points,

                    pickable=True,

                    get_position=[
                        "Longitude",
                        "Latitude"
                    ],

                    get_radius=24,

                    radius_min_pixels=2,

                    radius_max_pixels=6,

                    get_fill_color=[
                        130,
                        60,
                        200,
                        235
                    ],

                    get_line_color=[
                        70,
                        20,
                        120,
                        245
                    ],

                    stroked=True,

                    filled=True,
                )
            )

        # ----------------------------------------------------
        # OTHER WARDS
        # ----------------------------------------------------

        if not other_points.empty:

            layers.append(
                pdk.Layer(

                    "ScatterplotLayer",

                    data=other_points,

                    pickable=True,

                    get_position=[
                        "Longitude",
                        "Latitude"
                    ],

                    get_radius=24,

                    radius_min_pixels=2,

                    radius_max_pixels=6,

                    get_fill_color=[
                        40,
                        120,
                        180,
                        190
                    ],

                    get_line_color=[
                        20,
                        60,
                        100,
                        210
                    ],

                    stroked=True,

                    filled=True,
                )
            )

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    if (
        case_points is not None
        and
        not case_points.empty
        and
        center_mode == "All Coordinates"
    ):

        center_lat = float(
            case_points[
                "Latitude"
            ].mean()
        )

        center_lon = float(
            case_points[
                "Longitude"
            ].mean()
        )

        zoom = 5.5

    else:

        center_lat = 19.0760
        center_lon = 72.8777
        zoom = 10.2

    tooltip = {
        "html": """
        <b>Case ID:</b> {Case_ID}<br/>
        <b>Disease:</b> {Disease}<br/>
        <b>Ward:</b> {Ward}<br/>
        <b>Map Ward:</b> {Map_Ward}<br/>
        <b>Latitude:</b> {Latitude}<br/>
        <b>Longitude:</b> {Longitude}
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

        tooltip=tooltip,

        map_style=None,
    )


# ============================================================
# DISEASE COMPARISON
# ============================================================

def create_disease_comparison(
    df,
    diseases
):

    disease_col = get_disease_column(
        df
    )

    if not disease_col:
        return pd.DataFrame()

    rows = []

    for disease in diseases:

        disease_df = df[
            df[disease_col]
            .astype(str)
            .str.strip()
            .eq(
                str(disease).strip()
            )
        ].copy()

        if disease_df.empty:
            continue

        valid_df, _, valid_count = (
            prepare_coordinates(
                disease_df
            )
        )

        hotspots = create_hotspots(
            valid_df
        )

        ward_summary = create_ward_summary(
            valid_df
        )

        top_row = (
            ward_summary
            .sort_values(
                "Cases",
                ascending=False
            )
            .iloc[0]
        )

        rows.append(
            {
                "Disease": disease,
                "Cases": len(
                    disease_df
                ),
                "Valid Coordinates": (
                    valid_count
                ),
                "Hotspot Clusters": len(
                    hotspots
                ),
                "High Hotspots": int(
                    (
                        hotspots[
                            "Hotspot"
                        ]
                        ==
                        "High"
                    ).sum()
                )
                if not hotspots.empty
                else 0,
                "Top Ward": (
                    top_row["Ward"]
                ),
                "Top Ward Cases": int(
                    top_row["Cases"]
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# DISEASE CHECKBOX SELECTOR
# ============================================================

def disease_checkbox_selector(
    diseases
):

    if not diseases:
        return []

    diseases = list(diseases)

    select_all_key = "geo_select_all"
    selected_key = "geo_selected_diseases"

    if select_all_key not in st.session_state:
        st.session_state[
            select_all_key
        ] = False

    if selected_key not in st.session_state:
        st.session_state[
            selected_key
        ] = []

    # --------------------------------------------------------
    # CALLBACKS
    # --------------------------------------------------------

    def select_all_callback():

        if st.session_state.get(
            select_all_key,
            False
        ):

            st.session_state[
                selected_key
            ] = list(diseases)

            for i in range(
                len(diseases)
            ):

                st.session_state[
                    f"geo_disease_{i}"
                ] = True

    def individual_callback():

        selected_now = []

        for i, disease in enumerate(
            diseases
        ):

            if st.session_state.get(
                f"geo_disease_{i}",
                False
            ):

                selected_now.append(
                    disease
                )

        st.session_state[
            selected_key
        ] = selected_now

        if len(selected_now) != len(diseases):

            st.session_state[
                select_all_key
            ] = False

        elif len(diseases) > 0:

            st.session_state[
                select_all_key
            ] = True

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    st.markdown(
        "### Disease Selection"
    )

    # --------------------------------------------------------
    # SELECT ALL / RESET
    # --------------------------------------------------------

    control_cols = st.columns(
        [2, 1, 1]
    )

    with control_cols[0]:

        st.checkbox(
            "Select All Diseases",
            key=select_all_key,
            on_change=select_all_callback
        )

    with control_cols[1]:

        if st.button(
            "Reset",
            key="geo_reset_diseases"
        ):

            st.session_state[
                select_all_key
            ] = False

            st.session_state[
                selected_key
            ] = []

            for i in range(
                len(diseases)
            ):

                st.session_state[
                    f"geo_disease_{i}"
                ] = False

            st.rerun()

    # --------------------------------------------------------
    # INDIVIDUAL DISEASE CHECKBOXES
    # --------------------------------------------------------

    cols = st.columns(4)

    for i, disease in enumerate(
        diseases
    ):

        key = f"geo_disease_{i}"

        if key not in st.session_state:

            st.session_state[
                key
            ] = (
                disease
                in st.session_state[
                    selected_key
                ]
            )

        with cols[
            i % 4
        ]:

            st.checkbox(
                str(disease),
                key=key,
                on_change=individual_callback
            )

    selected = [
        disease
        for i, disease in enumerate(
            diseases
        )
        if st.session_state.get(
            f"geo_disease_{i}",
            False
        )
    ]

    st.session_state[
        selected_key
    ] = selected

    return selected


# ============================================================
# MAP LEGEND
# ============================================================

def render_map_legend(
    ward_summary,
    case_points,
    hotspots=None
):

    pe_cases = int(
        ward_summary.loc[
            ward_summary["Ward"] == "PE",
            "Cases"
        ].sum()
    )

    pn_cases = int(
        ward_summary.loc[
            ward_summary["Ward"] == "PN",
            "Cases"
        ].sum()
    )

    other_cases = int(
        ward_summary.loc[
            ~ward_summary["Ward"].isin(
                [
                    "PE",
                    "PN"
                ]
            ),
            "Cases"
        ].sum()
    )

    p_combined = (
        pe_cases
        +
        pn_cases
    )

    hotspot_count = (
        len(hotspots)
        if hotspots is not None
        else 0
    )

    st.markdown(
        "### Map Legend"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:

        st.markdown(
            f"🔵 **PE**  \n"
            f"{pe_cases:,} cases"
        )

    with c2:

        st.markdown(
            f"🟣 **PN**  \n"
            f"{pn_cases:,} cases"
        )

    with c3:

        st.markdown(
            f"🔷 **Other Wards**  \n"
            f"{other_cases:,} cases"
        )

    with c4:

        st.markdown(
            f"🔴 **Hotspot**  \n"
            f"{hotspot_count:,} clusters"
        )

    with c5:

        st.markdown(
            f"**P = PE + PN**  \n"
            f"{p_combined:,} cases"
        )


# ============================================================
# MAIN RENDER
# ============================================================

def render_geographic_map(
    filtered_df,
    total_df=None
):

    st.markdown(
        "## Geographic Disease Hotspot & Ward Analysis"
    )

    st.caption(
        "Actual recorded Latitude / Longitude based "
        "case mapping with disease-wise and ward-wise analysis."
    )

    # --------------------------------------------------------
    # VALID COORDINATES
    # --------------------------------------------------------

    valid_df, invalid_count, valid_count = (
        prepare_coordinates(
            filtered_df
        )
    )

    total = (
        valid_count
        +
        invalid_count
    )

    if total > 0:

        percentage = round(
            valid_count
            /
            total
            *
            100,
            1
        )

        st.info(
            f"Coordinates available: "
            f"**{valid_count:,} / {total:,} "
            f"({percentage}%)**"
        )

    if valid_df.empty:

        st.warning(
            "No valid Latitude / Longitude records are available."
        )

        return

    # --------------------------------------------------------
    # DISEASE
    # --------------------------------------------------------

    disease_col = get_disease_column(
        valid_df
    )

    if not disease_col:

        st.warning(
            "Disease column not found."
        )

        return

    diseases = sorted(
        [
            x
            for x in
            valid_df[
                disease_col
            ]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            if x
        ]
    )

    if not diseases:

        st.warning(
            "No disease records are available."
        )

        return

    # --------------------------------------------------------
    # BOUNDARY
    # --------------------------------------------------------

    geojson = load_bmc_wards()

    # --------------------------------------------------------
    # WARD SPATIAL RESOLUTION
    # --------------------------------------------------------

    valid_df = spatially_resolve_wards(
        valid_df,
        geojson
    )

    # --------------------------------------------------------
    # CONTROLS
    # --------------------------------------------------------

    st.markdown("---")

    left, right = st.columns(
        [1.25, 1.0]
    )

    with left:

        extent = st.radio(
            "Map Extent",

            [
                "BMC / Mumbai Focus",
                "All Coordinates"
            ],

            horizontal=True,

            key="geo_extent"
        )

    with right:

        selected_diseases = (
            disease_checkbox_selector(
                diseases
            )
        )

    # --------------------------------------------------------
    # SELECTED DATA
    # --------------------------------------------------------

    if selected_diseases:

        map_df = valid_df[
            valid_df[
                disease_col
            ]
            .astype(str)
            .str.strip()
            .isin(
                [
                    str(x).strip()
                    for x in
                    selected_diseases
                ]
            )
        ].copy()

        selected_label = (
            ", ".join(
                selected_diseases
            )
        )

    else:

        map_df = valid_df.copy()

        selected_label = (
            "All Diseases"
        )

    if map_df.empty:

        st.warning(
            "Selected disease has no valid Latitude / Longitude records."
        )

        return

    # --------------------------------------------------------
    # CASE POINTS
    # --------------------------------------------------------

    case_points = create_case_points(
        map_df
    )

    # --------------------------------------------------------
    # HOTSPOTS
    # --------------------------------------------------------

    hotspots = create_hotspots(
        map_df
    )

    # --------------------------------------------------------
    # WARD SUMMARY
    # --------------------------------------------------------

    ward_summary = create_ward_summary(
        map_df
    )

    map_ward_summary = (
        create_map_ward_summary(
            map_df
        )
    )

    choropleth = (
        prepare_bmc_choropleth(
            geojson,
            map_ward_summary
        )
        if geojson
        else None
    )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric(
        "Total Cases",
        f"{len(map_df):,}"
    )

    k2.metric(
        "Mapped Cases",
        f"{len(case_points):,}"
    )

    k3.metric(
        "Hotspot Clusters",
        f"{len(hotspots):,}"
    )

    high_hotspots = (
        int(
            (
                hotspots[
                    "Hotspot"
                ]
                ==
                "High"
            ).sum()
        )
        if not hotspots.empty
        else 0
    )

    k4.metric(
        "High Hotspots",
        f"{high_hotspots:,}"
    )

    top_ward = (
        ward_summary
        .sort_values(
            "Cases",
            ascending=False
        )
        .iloc[0]
    )

    k5.metric(
        "Top Ward",
        f"{top_ward['Ward']} "
        f"({int(top_ward['Cases']):,})"
    )

    st.caption(
        f"Current selection: "
        f"**{selected_label}**"
    )

    # ========================================================
    # TABS
    # ========================================================

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Case Locations",
            "Disease Comparison",
            "Choropleth Comparison",
            "Combined Geographic View",
        ]
    )

    # ========================================================
    # TAB 1
    # ========================================================

    with tab1:

        st.subheader(
            "Actual Case Locations"
        )

        st.caption(
            "Each valid Latitude/Longitude record is "
            "displayed as an individual case point."
        )

        render_map_legend(
            ward_summary,
            case_points,
            hotspots
        )

        if case_points.empty:

            st.warning(
                "No mapped case points are available."
            )

        else:

            case_map = build_map(
                geojson=None,
                hotspots=None,
                case_points=case_points,
                center_mode=extent,
            )

            st.pydeck_chart(
                case_map,
                use_container_width=True
            )

            st.markdown(
                "### Mapped Case Records"
            )

            st.dataframe(
                case_points[
                    [
                        "Case_ID",
                        "Disease",
                        "Ward",
                        "Map_Ward",
                        "Latitude",
                        "Longitude",
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

    # ========================================================
    # TAB 2
    # ========================================================

    with tab2:

        st.subheader(
            "Disease-wise Geographic Comparison"
        )

        comparison_diseases = (
            selected_diseases
            if selected_diseases
            else diseases
        )

        comparison_df = (
            create_disease_comparison(
                valid_df,
                comparison_diseases
            )
        )

        if not comparison_df.empty:

            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True
            )

        st.markdown(
            "### Disease-wise Ward Cases"
        )

        rows = []

        for disease in comparison_diseases:

            subset = valid_df[
                valid_df[
                    disease_col
                ]
                .astype(str)
                .str.strip()
                .eq(
                    str(disease).strip()
                )
            ]

            summary = create_ward_summary(
                subset
            )

            for _, row in summary.iterrows():

                rows.append(
                    {
                        "Disease": disease,
                        "Ward": row["Ward"],
                        "Cases": int(
                            row["Cases"]
                        ),
                    }
                )

        if rows:

            ward_compare = (
                pd.DataFrame(rows)
                .pivot(
                    index="Ward",
                    columns="Disease",
                    values="Cases"
                )
                .fillna(0)
                .astype(int)
            )

            st.dataframe(
                ward_compare,
                use_container_width=True
            )

    # ========================================================
    # TAB 3
    # ========================================================

    with tab3:

        st.subheader(
            "Disease-wise Ward Choropleth"
        )

        if geojson is None:

            st.warning(
                "Ward boundary load failed."
            )

        else:

            comparison_diseases = (
                selected_diseases
                if selected_diseases
                else diseases
            )

            max_maps = 6

            for start in range(
                0,
                min(
                    len(comparison_diseases),
                    max_maps
                ),
                2
            ):

                cols = st.columns(2)

                for j in range(2):

                    idx = start + j

                    if idx >= len(
                        comparison_diseases
                    ):
                        continue

                    disease = (
                        comparison_diseases[
                            idx
                        ]
                    )

                    subset = valid_df[
                        valid_df[
                            disease_col
                        ]
                        .astype(str)
                        .str.strip()
                        .eq(
                            str(
                                disease
                            ).strip()
                        )
                    ].copy()

                    summary = (
                        create_map_ward_summary(
                            subset
                        )
                    )

                    disease_geojson = (
                        prepare_bmc_choropleth(
                            geojson,
                            summary
                        )
                    )

                    disease_points = (
                        create_case_points(
                            subset
                        )
                    )

                    with cols[j]:

                        st.markdown(
                            f"**{disease}**"
                        )

                        disease_map = (
                            build_map(
                                geojson=(
                                    disease_geojson
                                ),
                                hotspots=None,
                                case_points=(
                                    disease_points
                                ),
                                center_mode=(
                                    "BMC / Mumbai Focus"
                                ),
                            )
                        )

                        st.pydeck_chart(
                            disease_map,
                            use_container_width=True
                        )

    # ========================================================
    # TAB 4
    # ========================================================

    with tab4:

        st.subheader(
            "Combined Geographic Management View"
        )

        render_map_legend(
            ward_summary,
            case_points,
            hotspots
        )

        combined_map = build_map(
            geojson=choropleth,
            hotspots=hotspots,
            case_points=case_points,
            center_mode=extent,
        )

        st.pydeck_chart(
            combined_map,
            use_container_width=True
        )

        st.markdown(
            "### Ward-wise Summary"
        )

        st.dataframe(
            ward_summary.sort_values(
                "Cases",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # PE / PN SUMMARY
        # ----------------------------------------------------

        pe_cases = int(
            ward_summary.loc[
                ward_summary[
                    "Ward"
                ] == "PE",
                "Cases"
            ].sum()
        )

        pn_cases = int(
            ward_summary.loc[
                ward_summary[
                    "Ward"
                ] == "PN",
                "Cases"
            ].sum()
        )

        st.info(
            f"PE: **{pe_cases:,} cases** | "
            f"PN: **{pn_cases:,} cases** | "
            f"PE + PN combined for map: "
            f"**{pe_cases + pn_cases:,} cases**"
        )

        st.markdown(
            "### Disease Summary"
        )

        disease_summary = (
            create_disease_comparison(
                valid_df,
                (
                    selected_diseases
                    if selected_diseases
                    else diseases
                )
            )
        )

        if not disease_summary.empty:

            st.dataframe(
                disease_summary,
                use_container_width=True,
                hide_index=True
            )
