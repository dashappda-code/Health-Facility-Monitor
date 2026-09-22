# geographic_map.py

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

    # Exact
    for candidate in candidates:
        for col in columns:
            if str(col).strip().lower() == candidate.strip().lower():
                return col

    # Contains
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

    # Remove common suffix/prefix words
    text = re.sub(r"\bWARD\b", "", text)
    text = re.sub(r"\bMUNICIPAL\b", "", text)
    text = re.sub(r"\bMCGM\b", "", text)
    text = re.sub(r"\bBMC\b", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Direct match
    if text in WARD_MAP:
        return WARD_MAP[text]

    # Specific patterns first
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

    # Compact codes
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
        return "📍 No records available."

    pct = round((valid_count / total) * 100, 1)

    return (
        f"📍 Coordinates available: **{valid_count:,} / {total:,} "
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

    # Last fallback:
    # search through every property value
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
            and
            (
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

    # Polygon
    if isinstance(coordinates[0][0][0], (int, float)):

        outer = coordinates[0]

        if not point_in_ring(lon, lat, outer):
            return False

        # Holes
        for hole in coordinates[1:]:

            if point_in_ring(lon, lat, hole):
                return False

        return True

    # Multi-level fallback
    for polygon in coordinates:

        if point_in_polygon(lon, lat, polygon):
            return True

    return False


def assign_boundary_ward(
    lon,
    lat,
    geojson
):

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


def spatially_resolve_wards(
    df,
    geojson
):

    if df is None or df.empty or not geojson:
        return df

    out = df.copy()

    existing_ward_col = get_ward_column(out)

    if existing_ward_col:
        out["_Original_Ward"] = out[existing_ward_col].apply(
            normalise_ward
        )
    else:
        out["_Original_Ward"] = ""

    # Start with existing ward
    out["_Map_Ward"] = out["_Original_Ward"]

    # Only spatially resolve PE / PN / combined / missing cases.
    # This prevents unnecessary point-in-polygon work for every record.
    needs_spatial = (
        out["_Original_Ward"].isin(
            ["PE", "PN", ""]
        )
        |
        out["_Original_Ward"].astype(str).str.contains(
            "P",
            na=False
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

            # If boundary says PN, use PN.
            # If PE polygon exists, PE will also be captured.
            out.at[idx, "_Map_Ward"] = boundary_ward

    return out


# ============================================================
# HOTSPOTS
# ============================================================

def create_hotspots(df):

    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    if LAT_COL not in work.columns or LON_COL not in work.columns:
        return pd.DataFrame()

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
        .rename(columns={"size": "Cluster_Cases"})
    )

    grouped["Cluster_ID"] = (
        grouped["_grid_lat"].round(4).astype(str)
        + "_"
        + grouped["_grid_lon"].round(4).astype(str)
    )

    def hotspot_class(cases):

        if cases >= 10:
            return "High"

        if cases >= 5:
            return "Moderate"

        return "Low"

    grouped["Hotspot"] = grouped[
        "Cluster_Cases"
    ].apply(hotspot_class)

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

    work = df.copy()

    # Prefer spatially resolved map ward
    if "_Map_Ward" in work.columns:

        ward_series = work["_Map_Ward"].apply(
            normalise_ward
        )

    else:

        ward_col = get_ward_column(work)

        if not ward_col:
            return summary

        ward_series = work[ward_col].apply(
            normalise_ward
        )

    counts = ward_series.value_counts()

    summary["Cases"] = summary["Ward"].map(
        counts
    ).fillna(0).astype(int)

    return summary


# ============================================================
# CHOROPLETH
# ============================================================

def get_choropleth_color(
    cases,
    max_cases
):

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

    matched_wards = set()

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

        if ward:
            matched_wards.add(ward)

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
            20, 20, 20, 220
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
    title="Geographic Disease Map",
    center_mode="BMC / Mumbai Focus",
):

    layers = []

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
                opacity=0.55,
            )
        )

    if hotspots is not None and not hotspots.empty:

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=hotspots,
                pickable=True,

                get_position=[
                    "Longitude",
                    "Latitude"
                ],

                # IMPORTANT:
                # previous large circles reduced
                get_radius=(
                    "80 + min("
                    "Cluster_Cases * 12, "
                    "220)"
                ),

                radius_min_pixels=3,
                radius_max_pixels=16,

                get_fill_color=[
                    220,
                    40,
                    40,
                    150
                ],

                get_line_color=[
                    120,
                    0,
                    0,
                    180
                ],

                stroked=True,
                filled=True,
            )
        )

    if (
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

    if geojson:

        tooltip = {
            "html": """
            <b>Ward:</b> {properties.Ward_Display}<br/>
            <b>Cases:</b> {properties.Programme_Cases}
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

        if not ward_summary.empty:

            top_row = ward_summary.sort_values(
                "Cases",
                ascending=False
            ).iloc[0]

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
        prepare_bmc_choropleth(
            None,
            ward_summary
        ),
    )


# ============================================================
# DOWNLOAD
# ============================================================

def download_hotspot_data(
    hotspots
):

    if hotspots is None or hotspots.empty:
        return None

    return hotspots.to_csv(
        index=False
    ).encode("utf-8")


# ============================================================
# DISEASE CHECKBOX UI
# ============================================================

def disease_checkbox_selector(
    diseases
):

    if not diseases:
        return []

    # Session-state initialisation
    if "geo_select_all" not in st.session_state:
        st.session_state[
            "geo_select_all"
        ] = False

    st.markdown(
        "**🦠 Disease Selection**"
    )

    select_all = st.checkbox(
        "☑ Select All Diseases",
        key="geo_select_all"
    )

    selected_diseases = []

    if select_all:

        # All diseases selected
        selected_diseases = list(diseases)

        # Show checked but disabled boxes
        cols = st.columns(3)

        for i, disease in enumerate(diseases):

            with cols[i % 3]:

                st.checkbox(
                    str(disease),
                    value=True,
                    disabled=True,
                    key=f"geo_disabled_{i}"
                )

    else:

        cols = st.columns(3)

        for i, disease in enumerate(diseases):

            key = (
                f"geo_disease_checkbox_{i}"
            )

            with cols[i % 3]:

                checked = st.checkbox(
                    str(disease),
                    key=key
                )

                if checked:
                    selected_diseases.append(
                        disease
                    )

    return selected_diseases


# ============================================================
# MAIN RENDER
# ============================================================

def render_geographic_map(
    filtered_df,
    total_df=None
):

    st.markdown(
        "## 🗺️ Geographic Disease Hotspot & Ward Analysis"
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
            for x in
            valid_df[disease_col]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
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
    # IMPORTANT:
    # Spatially resolve PE / PN / combined ward cases
    # --------------------------------------------------------

    valid_df = spatially_resolve_wards(
        valid_df,
        geojson
    )

    # --------------------------------------------------------
    # Controls
    # --------------------------------------------------------

    st.markdown("---")

    control_left, control_right = st.columns(
        [1.25, 1.0],
        gap="small"
    )

    with control_left:

        extent = st.radio(
            "🗺️ Map Extent",
            [
                "BMC / Mumbai Focus",
                "All Coordinates"
            ],
            horizontal=True,
            key="geo_extent"
        )

    with control_right:

        # Disease checkbox panel
        with st.expander(
            "🦠 Disease Selection",
            expanded=False
        ):

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
                    "No disease selected → all diseases will be shown."
                )

    # --------------------------------------------------------
    # If nothing selected = all diseases
    # --------------------------------------------------------

    if not selected_diseases:

        map_df = valid_df.copy()

        selected_label = "All Diseases"

    else:

        map_df = valid_df[
            valid_df[disease_col]
            .astype(str)
            .str.strip()
            .isin(
                [
                    str(x).strip()
                    for x in selected_diseases
                ]
            )
        ].copy()

        selected_label = ", ".join(
            selected_diseases
        )

    if map_df.empty:

        st.warning(
            "Selected disease(s) साठी geographic records available नाहीत."
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

    choropleth = (
        prepare_bmc_choropleth(
            geojson,
            ward_summary
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
        "Valid Coordinates",
        f"{len(map_df):,}"
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

    top_ward_row = (
        ward_summary
        .sort_values(
            "Cases",
            ascending=False
        )
        .iloc[0]
    )

    k5.metric(
        "Top Ward",
        f"{top_ward_row['Ward']} "
        f"({int(top_ward_row['Cases']):,})"
    )

    st.caption(
        f"🦠 Current map selection: **{selected_label}**"
    )

    # --------------------------------------------------------
    # Tabs
    # --------------------------------------------------------

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🔥 Hotspots",
            "📊 Disease Comparison",
            "🏘️ Choropleth Comparison",
            "🗺️ Combined Geographic View",
        ]
    )

    # ========================================================
    # TAB 1 — HOTSPOTS
    # ========================================================

    with tab1:

        st.subheader(
            "🔥 Geographic Hotspot Clusters"
        )

        if hotspots.empty:

            st.info(
                "Hotspot clusters उपलब्ध नाहीत."
            )

        else:

            hotspot_map = build_map(
                None,
                hotspots,
                title="Hotspots",
                center_mode=extent,
            )

            st.pydeck_chart(
                hotspot_map,
                use_container_width=True
            )

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
                    "⬇️ Download Hotspot Data",
                    data=csv_data,
                    file_name=(
                        "geographic_hotspots.csv"
                    ),
                    mime="text/csv",
                )

    # ========================================================
    # TAB 2 — DISEASE COMPARISON
    # ========================================================

    with tab2:

        st.subheader(
            "📊 Disease-wise Geographic Comparison"
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
                "Disease comparison data उपलब्ध नाही."
            )

        else:

            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True
            )

            st.markdown(
                "### 🏘️ Ward-wise Cases"
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

                summary = (
                    create_ward_summary(
                        disease_subset
                    )
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
    # TAB 3 — CHOROPLETH COMPARISON
    # ========================================================

    with tab3:

        st.subheader(
            "🏘️ Disease-wise Ward Choropleth Comparison"
        )

        comparison_diseases = (
            selected_diseases
            if selected_diseases
            else diseases
        )

        if not geojson:

            st.warning(
                "Ward boundary unavailable."
            )

        else:

            # Avoid rendering too many maps simultaneously
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

                    index = start + col_index

                    if index >= len(map_diseases):
                        continue

                    disease = map_diseases[index]

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

                        disease_choropleth = (
                            prepare_bmc_choropleth(
                                geojson,
                                disease_summary
                            )
                        )

                        disease_hotspots = (
                            create_hotspots(
                                disease_subset
                            )
                        )

                        st.markdown(
                            f"**🦠 {disease}**"
                        )

                        disease_map = build_map(
                            disease_choropleth,
                            disease_hotspots,
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
    # TAB 4 — COMBINED
    # ========================================================

    with tab4:

        st.subheader(
            "🗺️ Combined Geographic Management View"
        )

        if choropleth:

            combined_map = build_map(
                choropleth,
                hotspots,
                title="Combined Geographic View",
                center_mode=extent,
            )

            st.pydeck_chart(
                combined_map,
                use_container_width=True
            )

        else:

            hotspot_only_map = build_map(
                None,
                hotspots,
                title="Combined Geographic View",
                center_mode=extent,
            )

            st.pydeck_chart(
                hotspot_only_map,
                use_container_width=True
            )

        st.markdown(
            "### 🏘️ Ward-wise Summary"
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

        if pe_cases > 0 or pn_cases > 0:

            st.info(
                f"📍 PE cases: **{pe_cases:,}** | "
                f"PN cases: **{pn_cases:,}**. "
                "PE/PN records with valid Latitude/Longitude "
                "are spatially resolved wherever the available "
                "ward boundary geometry supports it."
            )

        # ----------------------------------------------------
        # Selected disease summary
        # ----------------------------------------------------

        st.markdown(
            "### 🦠 Selected Disease Summary"
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
