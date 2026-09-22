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
    text = text.replace("&", "AND")
    text = text.replace("-", " ")
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)

    return text


def find_column(df, candidates):
    if df is None or df.empty:
        return None

    columns = list(df.columns)

    for candidate in candidates:
        for col in columns:
            if str(col).strip().lower() == candidate.strip().lower():
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

    text = re.sub(r"\bWARD\b", "", text)
    text = re.sub(r"\bMUNICIPAL\b", "", text)
    text = re.sub(r"\bMCGM\b", "", text)
    text = re.sub(r"\bBMC\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()

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
    candidates = [
        "Disease",
        "Disease Name",
        "Disease_Name",
        "Disease name",
        "DiseaseName",
        "disease",
        "disease_name",
    ]

    return find_column(df, candidates)


def get_ward_column(df):
    candidates = [
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

    return find_column(df, candidates)


# ============================================================
# COORDINATES
# ============================================================

def prepare_coordinates(df):
    if df is None or df.empty:
        return pd.DataFrame(), 0, 0

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame(), len(df), 0

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
        & out[LON_COL].notna()
        & out[LAT_COL].between(-90, 90)
        & out[LON_COL].between(-180, 180)
    )

    valid_df = out.loc[valid_mask].copy()

    invalid_count = int((~valid_mask).sum())
    valid_count = int(valid_mask.sum())

    return valid_df, invalid_count, valid_count


def coordinate_availability_text(valid_count, invalid_count):
    total = valid_count + invalid_count

    if total == 0:
        return "Coordinates available: 0 / 0"

    pct = round((valid_count / total) * 100, 1)

    return (
        f"Coordinates available: **{valid_count:,} / {total:,} "
        f"({pct}%)**"
    )


# ============================================================
# BMC WARD GEOJSON
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


# ============================================================
# GEOJSON WARD NAME
# ============================================================

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
        "WARD_NO_",
        "WARD_CODE",
        "WARDCODE",
        "WARD_ID",
        "WNO",
        "WARDS",
    ]

    for key in candidates:
        if key in properties:
            value = properties.get(key)
            normalized = normalise_ward(value)

            if normalized:
                return normalized

    for value in properties.values():
        normalized = normalise_ward(value)

        if normalized:
            return normalized

    return ""


# ============================================================
# POINT IN POLYGON
# ============================================================

def point_in_ring(lon, lat, ring):
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

        intersects = (
            ((yi > lat) != (yj > lat))
            and (
                lon
                <
                (xj - xi)
                * (lat - yi)
                / ((yj - yi) if (yj - yi) != 0 else 1e-12)
                + xi
            )
        )

        if intersects:
            inside = not inside

        j = i

    return inside


def point_in_polygon(lon, lat, coordinates):
    if not coordinates:
        return False

    try:
        if isinstance(coordinates[0][0][0], (int, float)):
            outer = coordinates[0]

            if not point_in_ring(lon, lat, outer):
                return False

            for hole in coordinates[1:]:
                if point_in_ring(lon, lat, hole):
                    return False

            return True

    except Exception:
        pass

    for polygon in coordinates:
        if point_in_polygon(lon, lat, polygon):
            return True

    return False


def assign_boundary_ward(lon, lat, geojson):
    if not geojson:
        return ""

    features = geojson.get("features", [])

    for feature in features:
        geometry = feature.get("geometry") or {}
        geom_type = geometry.get("type")
        coordinates = geometry.get("coordinates")

        if not coordinates:
            continue

        try:
            if geom_type == "Polygon":
                inside = point_in_polygon(
                    lon,
                    lat,
                    coordinates
                )

            elif geom_type == "MultiPolygon":
                inside = False

                for polygon in coordinates:
                    if point_in_polygon(
                        lon,
                        lat,
                        polygon
                    ):
                        inside = True
                        break
            else:
                inside = False

            if inside:
                ward = get_geojson_ward_name(
                    feature.get("properties", {})
                )

                if ward:
                    return ward

        except Exception:
            continue

    return ""


# ============================================================
# WARD SPATIAL RESOLUTION
# ============================================================

def spatially_resolve_wards(df, geojson):
    if df is None or df.empty:
        return df

    out = df.copy()

    existing_ward_col = get_ward_column(out)

    if existing_ward_col:
        out["_Original_Ward"] = out[
            existing_ward_col
        ].apply(normalise_ward)
    else:
        out["_Original_Ward"] = ""

    # Preserve the original programme ward.
    # This is important for separate PE and PN reporting.
    out["_Map_Ward"] = out["_Original_Ward"]

    if not geojson:
        return out

    needs_spatial = (
        out["_Original_Ward"].isin(
            ["", "PS"]
        )
    )

    candidate_indices = out.index[needs_spatial]

    for idx in candidate_indices:
        try:
            lat = float(out.at[idx, LAT_COL])
            lon = float(out.at[idx, LON_COL])
        except Exception:
            continue

        boundary_ward = assign_boundary_ward(
            lon,
            lat,
            geojson
        )

        if boundary_ward:
            out.at[idx, "_Map_Ward"] = boundary_ward

    return out


# ============================================================
# CHOROPLETH MAP WARD
# ============================================================

def map_ward(value):
    ward = normalise_ward(value)

    # PE and PN are intentionally combined for choropleth.
    if ward in ("PE", "PN"):
        return "P"

    return ward


# ============================================================
# CASE POINT DATA
# ============================================================

def create_case_points(df):
    if df is None or df.empty:
        return pd.DataFrame()

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame()

    disease_col = get_disease_column(df)

    if disease_col:
        disease_values = (
            df[disease_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        disease_values = pd.Series(
            [""] * len(df),
            index=df.index
        )

    if "_Original_Ward" in df.columns:
        report_ward = (
            df["_Original_Ward"]
            .apply(normalise_ward)
        )
    else:
        ward_col = get_ward_column(df)

        if ward_col:
            report_ward = (
                df[ward_col]
                .apply(normalise_ward)
            )
        else:
            report_ward = pd.Series(
                [""] * len(df),
                index=df.index
            )

    out = pd.DataFrame(
        {
            "Latitude": pd.to_numeric(
                df[LAT_COL],
                errors="coerce"
            ),
            "Longitude": pd.to_numeric(
                df[LON_COL],
                errors="coerce"
            ),
            "Disease": disease_values.values,
            "Ward": report_ward.values,
        },
        index=df.index
    )

    out = out.dropna(
        subset=["Latitude", "Longitude"]
    ).copy()

    out["Map_Ward"] = out["Ward"].apply(map_ward)

    if "Case ID" in df.columns:
        out["Case ID"] = (
            df.loc[out.index, "Case ID"]
            .astype(str)
            .values
        )
    else:
        out["Case ID"] = [
            str(x)
            for x in out.index
        ]

    return out.reset_index(drop=True)


# ============================================================
# HOTSPOTS
# ============================================================

def create_hotspots(df):
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
    )

    if work.empty:
        return pd.DataFrame()

    work["_grid_lat"] = (
        work[LAT_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    work["_grid_lon"] = (
        work[LON_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    grouped = (
        work
        .groupby(
            ["_grid_lat", "_grid_lon"],
            as_index=False
        )
        .size()
        .rename(
            columns={"size": "Cluster_Cases"}
        )
    )

    grouped["Cluster_ID"] = (
        grouped["_grid_lat"]
        .round(4)
        .astype(str)
        + "_"
        + grouped["_grid_lon"]
        .round(4)
        .astype(str)
    )

    def hotspot_class(cases):
        if cases >= 10:
            return "High"

        if cases >= 5:
            return "Moderate"

        return "Low"

    grouped["Hotspot"] = (
        grouped["Cluster_Cases"]
        .apply(hotspot_class)
    )

    grouped["Latitude"] = grouped["_grid_lat"]
    grouped["Longitude"] = grouped["_grid_lon"]

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
            "Cases": [0] * len(PROGRAMME_WARDS),
        }
    )

    if df is None or df.empty:
        return summary

    # Use original programme ward for reporting.
    # This keeps PE and PN separate.
    if "_Original_Ward" in df.columns:
        ward_series = df[
            "_Original_Ward"
        ].apply(normalise_ward)

    else:
        ward_col = get_ward_column(df)

        if not ward_col:
            return summary

        ward_series = df[
            ward_col
        ].apply(normalise_ward)

    counts = ward_series.value_counts()

    summary["Cases"] = (
        summary["Ward"]
        .map(counts)
        .fillna(0)
        .astype(int)
    )

    return summary


def create_map_ward_summary(df):
    wards = list(PROGRAMME_WARDS)

    map_wards = []

    for ward in wards:
        if ward not in ("PE", "PN"):
            map_wards.append(ward)

    map_wards.append("P")

    summary = pd.DataFrame(
        {
            "Ward": map_wards,
            "Cases": [0] * len(map_wards),
        }
    )

    if df is None or df.empty:
        return summary

    if "_Original_Ward" in df.columns:
        ward_series = (
            df["_Original_Ward"]
            .apply(normalise_ward)
        )
    else:
        ward_col = get_ward_column(df)

        if not ward_col:
            return summary

        ward_series = (
            df[ward_col]
            .apply(normalise_ward)
        )

    mapped_series = ward_series.apply(map_ward)

    counts = mapped_series.value_counts()

    summary["Cases"] = (
        summary["Ward"]
        .map(counts)
        .fillna(0)
        .astype(int)
    )

    return summary


# ============================================================
# CHOROPLETH COLORS
# ============================================================

def get_choropleth_color(cases, max_cases):
    try:
        cases = float(cases)
        max_cases = float(max_cases)
    except Exception:
        return [245, 245, 245, 120]

    if cases <= 0:
        return [245, 245, 245, 80]

    if max_cases <= 0:
        return [255, 230, 150, 170]

    ratio = cases / max_cases

    if ratio >= 0.75:
        return [180, 0, 0, 190]

    if ratio >= 0.50:
        return [235, 90, 20, 180]

    if ratio >= 0.25:
        return [255, 170, 40, 170]

    return [255, 225, 90, 150]


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

    max_cases = (
        float(ward_summary["Cases"].max())
        if not ward_summary.empty
        else 0
    )

    for feature in geojson.get("features", []):
        properties = dict(
            feature.get("properties", {})
        )

        ward = get_geojson_ward_name(
            properties
        )

        cases = int(
            case_map.get(ward, 0)
        )

        properties["Programme_Cases"] = cases

        properties["Ward_Display"] = (
            ward if ward else "Unknown"
        )

        properties["fill_color"] = (
            get_choropleth_color(
                cases,
                max_cases
            )
        )

        properties["line_color"] = [
            20,
            20,
            20,
            220
        ]

        properties["line_width"] = 2

        new_feature = dict(feature)
        new_feature["properties"] = properties

        result["features"].append(
            new_feature
        )

    return result


# ============================================================
# MAP BUILDER
# ============================================================

def build_map(
    geojson,
    hotspots,
    case_points=None,
    title="Geographic Disease Map",
    center_mode="BMC / Mumbai Focus",
):
    layers = []

    # --------------------------------------------------------
    # Ward polygons
    # --------------------------------------------------------

    if geojson:
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=geojson,
                pickable=True,
                stroked=True,
                filled=True,
                get_fill_color="properties.fill_color",
                get_line_color="properties.line_color",
                get_line_width="properties.line_width",
                line_width_min_pixels=1,
                opacity=0.55,
            )
        )

    # --------------------------------------------------------
    # Hotspots
    # Hotspots are intentionally drawn BEFORE case points.
    # This prevents hotspot circles from hiding PN / PE points.
    # --------------------------------------------------------

    if hotspots is not None and not hotspots.empty:
        hotspot_data = hotspots.copy()

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=hotspot_data,
                pickable=True,
                get_position=[
                    "Longitude",
                    "Latitude"
                ],
                get_radius=(
                    "45 + min(Cluster_Cases * 5, 100)"
                ),
                radius_min_pixels=2,
                radius_max_pixels=9,
                get_fill_color=[
                    220,
                    40,
                    40,
                    120
                ],
                get_line_color=[
                    120,
                    0,
                    0,
                    160
                ],
                stroked=True,
                filled=True,
            )
        )

    # --------------------------------------------------------
    # Case points
    # These are actual recorded Latitude/Longitude locations.
    # --------------------------------------------------------

    if case_points is not None and not case_points.empty:

        # PE points
        pe_points = case_points[
            case_points["Ward"] == "PE"
        ].copy()

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
                    get_radius=35,
                    radius_min_pixels=3,
                    radius_max_pixels=7,
                    get_fill_color=[
                        40,
                        120,
                        220,
                        230
                    ],
                    get_line_color=[
                        255,
                        255,
                        255,
                        220
                    ],
                    line_width_min_pixels=1,
                    stroked=True,
                    filled=True,
                )
            )

        # PN points
        pn_points = case_points[
            case_points["Ward"] == "PN"
        ].copy()

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
                    get_radius=35,
                    radius_min_pixels=3,
                    radius_max_pixels=7,
                    get_fill_color=[
                        130,
                        60,
                        200,
                        235
                    ],
                    get_line_color=[
                        255,
                        255,
                        255,
                        230
                    ],
                    line_width_min_pixels=1,
                    stroked=True,
                    filled=True,
                )
            )

        # All other wards
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
                    pickable=True,
                    get_position=[
                        "Longitude",
                        "Latitude"
                    ],
                    get_radius=28,
                    radius_min_pixels=2,
                    radius_max_pixels=6,
                    get_fill_color=[
                        40,
                        120,
                        180,
                        210
                    ],
                    get_line_color=[
                        255,
                        255,
                        255,
                        210
                    ],
                    line_width_min_pixels=1,
                    stroked=True,
                    filled=True,
                )
            )

    # --------------------------------------------------------
    # View
    # --------------------------------------------------------

    if (
        case_points is not None
        and not case_points.empty
        and center_mode == "All Coordinates"
    ):
        center_lat = float(
            case_points["Latitude"].mean()
        )

        center_lon = float(
            case_points["Longitude"].mean()
        )

        zoom = 5.5

    elif (
        hotspots is not None
        and not hotspots.empty
        and center_mode == "All Coordinates"
    ):
        center_lat = float(
            hotspots["Latitude"].mean()
        )

        center_lon = float(
            hotspots["Longitude"].mean()
        )

        zoom = 5.5

    else:
        center_lat = 19.0760
        center_lon = 72.8777
        zoom = 10.2

    # --------------------------------------------------------
    # Tooltip
    # --------------------------------------------------------

    tooltip = {
        "html": """
            <b>Case ID:</b> {Case ID}<br/>
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

    if (
        case_points is None
        or case_points.empty
    ) and (
        hotspots is not None
        and not hotspots.empty
    ):
        tooltip = {
            "html": """
                <b>Cluster:</b> {Cluster_ID}<br/>
                <b>Cases:</b> {Cluster_Cases}<br/>
                <b>Hotspot:</b> {Hotspot}
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
    disease_col = get_disease_column(df)

    if not disease_col:
        return pd.DataFrame()

    rows = []

    for disease in diseases:
        disease_df = df[
            df[disease_col]
            .astype(str)
            .str.strip()
            .eq(str(disease).strip())
        ].copy()

        if disease_df.empty:
            continue

        valid_df, _, valid_count = (
            prepare_coordinates(disease_df)
        )

        hotspots = create_hotspots(
            valid_df
        )

        ward_summary = create_ward_summary(
            valid_df
        )

        if not ward_summary.empty:
            top_row = (
                ward_summary
                .sort_values(
                    "Cases",
                    ascending=False
                )
                .iloc[0]
            )

            top_ward = top_row["Ward"]

            top_ward_cases = int(
                top_row["Cases"]
            )

        else:
            top_ward = ""
            top_ward_cases = 0

        rows.append(
            {
                "Disease": disease,
                "Cases": len(disease_df),
                "Valid Coordinates": valid_count,
                "Hotspot Clusters": len(hotspots),
                "High Hotspots": int(
                    (
                        hotspots["Hotspot"]
                        == "High"
                    ).sum()
                )
                if not hotspots.empty
                else 0,
                "Top Ward": top_ward,
                "Top Ward Cases": top_ward_cases,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# DISEASE MAP DATA
# ============================================================

def get_disease_map_data(
    df,
    disease
):
    disease_col = get_disease_column(df)

    if not disease_col:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            None
        )

    disease_df = df[
        df[disease_col]
        .astype(str)
        .str.strip()
        .eq(str(disease).strip())
    ].copy()

    valid_df, _, _ = prepare_coordinates(
        disease_df
    )

    hotspots = create_hotspots(
        valid_df
    )

    ward_summary = create_ward_summary(
        valid_df
    )

    return (
        disease_df,
        ward_summary,
        hotspots,
        None
    )


# ============================================================
# DOWNLOAD
# ============================================================

def download_hotspot_data(hotspots):
    if hotspots is None or hotspots.empty:
        return None

    return hotspots.to_csv(
        index=False
    ).encode("utf-8")


# ============================================================
# DISEASE CHECKBOX UI
# ============================================================

def reset_geo_disease_selection(diseases):
    st.session_state["geo_select_all"] = False

    for i in range(len(diseases)):
        st.session_state[
            f"geo_disease_checkbox_{i}"
        ] = False


def select_all_geo_diseases(diseases):
    if st.session_state.get(
        "geo_select_all",
        False
    ):
        for i in range(len(diseases)):
            st.session_state[
                f"geo_disease_checkbox_{i}"
            ] = True


def individual_geo_disease_changed():
    st.session_state["geo_select_all"] = False


def disease_checkbox_selector(diseases):
    if not diseases:
        return []

    if "geo_select_all" not in st.session_state:
        st.session_state["geo_select_all"] = False

    st.markdown(
        "**Disease Selection**"
    )

    top_col1, top_col2 = st.columns(
        [1, 1]
    )

    with top_col1:
        st.checkbox(
            "Select All Diseases",
            key="geo_select_all",
            on_change=select_all_geo_diseases,
            args=(diseases,),
        )

    with top_col2:
        if st.button(
            "Reset Diseases",
            key="geo_reset_diseases"
        ):
            reset_geo_disease_selection(
                diseases
            )
            st.rerun()

    selected_diseases = []

    cols = st.columns(4)

    for i, disease in enumerate(diseases):
        key = (
            f"geo_disease_checkbox_{i}"
        )

        if key not in st.session_state:
            st.session_state[key] = False

        with cols[i % 4]:
            checked = st.checkbox(
                str(disease),
                key=key,
                on_change=individual_geo_disease_changed,
            )

        if checked:
            selected_diseases.append(
                disease
            )

    return selected_diseases


# ============================================================
# MAP LEGEND
# ============================================================

def render_map_legend(
    pe_cases=0,
    pn_cases=0,
    hotspot_cases=0
):
    combined_cases = int(
        pe_cases + pn_cases
    )

    st.markdown(
        f"""
        <div style="
            display:flex;
            flex-wrap:wrap;
            gap:18px;
            align-items:center;
            margin-top:6px;
            margin-bottom:8px;
            font-size:14px;
        ">

            <div>
                <span style="
                    display:inline-block;
                    width:11px;
                    height:11px;
                    border-radius:50%;
                    background:#2878b4;
                    margin-right:6px;
                "></span>
                <b>PE</b> ({pe_cases:,})
            </div>

            <div>
                <span style="
                    display:inline-block;
                    width:11px;
                    height:11px;
                    border-radius:50%;
                    background:#823cc8;
                    margin-right:6px;
                "></span>
                <b>PN</b> ({pn_cases:,})
            </div>

            <div>
                <span style="
                    display:inline-block;
                    width:11px;
                    height:11px;
                    border-radius:50%;
                    background:#2878b4;
                    margin-right:6px;
                "></span>
                <b>Other Wards</b>
            </div>

            <div>
                <span style="
                    display:inline-block;
                    width:13px;
                    height:13px;
                    border-radius:50%;
                    background:rgba(220,40,40,0.55);
                    margin-right:6px;
                "></span>
                <b>Hotspot</b>
            </div>

            <div>
                <b>P = PE + PN:</b> {combined_cases:,}
            </div>

        </div>
        """,
        unsafe_allow_html=True
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
        "Facility-wise, ward-wise and disease-wise "
        "geographic analysis using recorded latitude "
        "and longitude coordinates."
    )

    # --------------------------------------------------------
    # Coordinate preparation
    # --------------------------------------------------------

    valid_df, invalid_count, valid_count = (
        prepare_coordinates(
            filtered_df
        )
    )

    st.info(
        coordinate_availability_text(
            valid_count,
            invalid_count
        )
    )

    if valid_df.empty:
        st.warning(
            "Valid latitude/longitude records are not available."
        )
        return

    # --------------------------------------------------------
    # Disease detection
    # --------------------------------------------------------

    disease_col = get_disease_column(
        valid_df
    )

    if not disease_col:
        st.warning(
            "Disease column was not detected."
        )
        return

    diseases = sorted(
        [
            x
            for x in (
                valid_df[disease_col]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
            )
            if x
        ]
    )

    if not diseases:
        st.warning(
            "No diseases available for geographic analysis."
        )
        return

    # --------------------------------------------------------
    # Boundary
    # --------------------------------------------------------

    geojson = load_bmc_wards()

    if geojson is None:
        st.warning(
            "BMC ward boundary could not be loaded. "
            "Disease points and hotspot analysis will still be shown."
        )

    # --------------------------------------------------------
    # Ward resolution
    # --------------------------------------------------------

    valid_df = spatially_resolve_wards(
        valid_df,
        geojson
    )

    # --------------------------------------------------------
    # Controls
    # --------------------------------------------------------

    st.markdown("---")

    extent = st.radio(
        "Map Extent",
        [
            "BMC / Mumbai Focus",
            "All Coordinates"
        ],
        horizontal=True,
        key="geo_extent"
    )

    selected_diseases = (
        disease_checkbox_selector(
            diseases
        )
    )

    if selected_diseases:
        st.caption(
            f"{len(selected_diseases)} disease(s) selected"
        )
    else:
        st.caption(
            "No disease selected: all diseases will be shown."
        )

    # --------------------------------------------------------
    # Map disease filter
    # --------------------------------------------------------

    if not selected_diseases:
        map_df = valid_df.copy()
        selected_label = "All Diseases"

    else:
        selected_clean = [
            str(x).strip()
            for x in selected_diseases
        ]

        map_df = valid_df[
            valid_df[disease_col]
            .astype(str)
            .str.strip()
            .isin(selected_clean)
        ].copy()

        selected_label = ", ".join(
            selected_clean
        )

    if map_df.empty:
        st.warning(
            "No geographic records are available "
            "for the selected disease(s)."
        )
        return

    # --------------------------------------------------------
    # Overall map data
    # --------------------------------------------------------

    hotspots = create_hotspots(
        map_df
    )

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

    case_points = create_case_points(
        map_df
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
        "Valid Coordinates",
        f"{len(case_points):,}"
    )

    k3.metric(
        "Hotspot Clusters",
        f"{len(hotspots):,}"
    )

    high_hotspots = (
        int(
            (
                hotspots["Hotspot"]
                == "High"
            ).sum()
        )
        if not hotspots.empty
        else 0
    )

    k4.metric(
        "High Hotspots",
        f"{high_hotspots:,}"
    )

    if not ward_summary.empty:
        top_ward_row = (
            ward_summary
            .sort_values(
                "Cases",
                ascending=False
            )
            .iloc[0]
        )

        top_ward_name = top_ward_row["Ward"]
        top_ward_cases = int(
            top_ward_row["Cases"]
        )

    else:
        top_ward_name = "-"
        top_ward_cases = 0

    k5.metric(
        "Top Ward",
        f"{top_ward_name} ({top_ward_cases:,})"
    )

    st.caption(
        f"Current map selection: **{selected_label}**"
    )

    # --------------------------------------------------------
    # PE / PN counts
    # --------------------------------------------------------

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

    render_map_legend(
        pe_cases=pe_cases,
        pn_cases=pn_cases,
        hotspot_cases=len(hotspots)
    )

    # --------------------------------------------------------
    # Tabs
    # --------------------------------------------------------

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
        st.subheader(
            "Geographic Hotspot Clusters"
        )

        hotspot_map = build_map(
            None,
            hotspots,
            case_points=case_points,
            title="Hotspots",
            center_mode=extent,
        )

        st.pydeck_chart(
            hotspot_map,
            use_container_width=True
        )

        if hotspots.empty:
            st.info(
                "No hotspot clusters are available."
            )

        else:
            display_hotspots = (
                hotspots
                .sort_values(
                    "Cluster_Cases",
                    ascending=False
                )
                .copy()
            )

            display_hotspots = (
                display_hotspots[
                    [
                        "Cluster_ID",
                        "Latitude",
                        "Longitude",
                        "Cluster_Cases",
                        "Hotspot",
                    ]
                ]
            )

            st.dataframe(
                display_hotspots,
                use_container_width=True,
                hide_index=True
            )

            csv_data = download_hotspot_data(
                display_hotspots
            )

            if csv_data:
                st.download_button(
                    "Download Hotspot Data",
                    data=csv_data,
                    file_name=(
                        "geographic_hotspots.csv"
                    ),
                    mime="text/csv",
                )

    # ========================================================
    # TAB 2 - DISEASE COMPARISON
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

        if comparison_df.empty:
            st.info(
                "Disease comparison data is not available."
            )

        else:
            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True
            )

            st.markdown(
                "### Ward-wise Cases"
            )

            disease_ward_rows = []

            for disease in comparison_diseases:
                disease_subset = valid_df[
                    valid_df[disease_col]
                    .astype(str)
                    .str.strip()
                    .eq(
                        str(disease).strip()
                    )
                ]

                summary = create_ward_summary(
                    disease_subset
                )

                for _, row in summary.iterrows():
                    disease_ward_rows.append(
                        {
                            "Disease": disease,
                            "Ward": row["Ward"],
                            "Cases": int(
                                row["Cases"]
                            ),
                        }
                    )

            if disease_ward_rows:
                disease_ward_df = pd.DataFrame(
                    disease_ward_rows
                )

                pivot = (
                    disease_ward_df
                    .pivot(
                        index="Ward",
                        columns="Disease",
                        values="Cases"
                    )
                    .fillna(0)
                    .astype(int)
                )

                st.dataframe(
                    pivot,
                    use_container_width=True
                )

    # ========================================================
    # TAB 3 - CHOROPLETH COMPARISON
    # ========================================================

    with tab3:
        st.subheader(
            "Disease-wise Ward Choropleth Comparison"
        )

        comparison_diseases = (
            selected_diseases
            if selected_diseases
            else diseases
        )

        if not geojson:
            st.warning(
                "Ward boundary is unavailable."
            )

        else:
            max_maps = 6

            map_diseases = (
                comparison_diseases[:max_maps]
            )

            if len(comparison_diseases) > max_maps:
                st.info(
                    f"{len(comparison_diseases)} diseases selected. "
                    f"First {max_maps} choropleths are displayed "
                    f"for performance."
                )

            for start in range(
                0,
                len(map_diseases),
                2
            ):
                cols = st.columns(2)

                for col_index in range(2):
                    index = (
                        start
                        + col_index
                    )

                    if index >= len(map_diseases):
                        continue

                    disease = map_diseases[
                        index
                    ]

                    with cols[col_index]:
                        disease_subset = valid_df[
                            valid_df[disease_col]
                            .astype(str)
                            .str.strip()
                            .eq(
                                str(disease).strip()
                            )
                        ].copy()

                        disease_summary = (
                            create_ward_summary(
                                disease_subset
                            )
                        )

                        disease_map_summary = (
                            create_map_ward_summary(
                                disease_subset
                            )
                        )

                        disease_choropleth = (
                            prepare_bmc_choropleth(
                                geojson,
                                disease_map_summary
                            )
                        )

                        disease_hotspots = (
                            create_hotspots(
                                disease_subset
                            )
                        )

                        disease_case_points = (
                            create_case_points(
                                disease_subset
                            )
                        )

                        st.markdown(
                            f"**{disease}**"
                        )

                        disease_map = build_map(
                            disease_choropleth,
                            disease_hotspots,
                            case_points=disease_case_points,
                            title=str(disease),
                            center_mode=(
                                "BMC / Mumbai Focus"
                            ),
                        )

                        st.pydeck_chart(
                            disease_map,
                            use_container_width=True
                        )

                        top_row = (
                            disease_summary
                            .sort_values(
                                "Cases",
                                ascending=False
                            )
                            .iloc[0]
                        )

                        st.caption(
                            f"Top Ward: **{top_row['Ward']}** "
                            f"({int(top_row['Cases']):,} cases)"
                        )

    # ========================================================
    # TAB 4 - COMBINED
    # ========================================================

    with tab4:
        st.subheader(
            "Combined Geographic Management View"
        )

        combined_map = build_map(
            choropleth,
            hotspots,
            case_points=case_points,
            title="Combined Geographic View",
            center_mode=extent,
        )

        st.pydeck_chart(
            combined_map,
            use_container_width=True
        )

        st.markdown(
            "### Ward-wise Summary"
        )

        ward_display = (
            ward_summary
            .sort_values(
                "Cases",
                ascending=False
            )
            .copy()
        )

        ward_display["Cases"] = (
            ward_display["Cases"]
            .astype(int)
        )

        st.dataframe(
            ward_display,
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # PE / PN diagnostic
        # ----------------------------------------------------

        if pe_cases > 0 or pn_cases > 0:
            st.info(
                f"PE cases: **{pe_cases:,}** | "
                f"PN cases: **{pn_cases:,}** | "
                f"P = PE + PN for choropleth: "
                f"**{pe_cases + pn_cases:,}**"
            )

        # ----------------------------------------------------
        # Selected disease summary
        # ----------------------------------------------------

        st.markdown(
            "### Selected Disease Summary"
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
