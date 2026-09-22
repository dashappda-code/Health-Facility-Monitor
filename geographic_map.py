import re
import pandas as pd
import requests
import streamlit as st
import pydeck as pdk


# ============================================================
# CONFIGURATION
# ============================================================

BMC_WARD_URL = (
    "https://services8.arcgis.com/"
    "r6MmJtuWAzMawmJ8/arcgis/rest/services/"
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
    return str(value).strip()


def find_column(df, candidates):
    """
    Finds a dataframe column using flexible matching.
    """
    if df is None or df.empty:
        return None

    cols = list(df.columns)

    # Exact match
    for candidate in candidates:
        for col in cols:
            if str(col).strip().lower() == candidate.strip().lower():
                return col

    # Partial match
    for candidate in candidates:
        c = candidate.strip().lower()
        for col in cols:
            if c in str(col).strip().lower():
                return col

    return None


def normalise_ward(value):
    """
    Converts ward names into a compact standard form.
    """

    text = clean_text(value).upper()

    if not text:
        return ""

    text = text.replace("-", " ")
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()

    # Remove common words
    text = text.replace("WARD", "")
    text = re.sub(r"\s+", " ", text).strip()

    # Common formats
    aliases = {
        "A WARD": "A",
        "B WARD": "B",
        "C WARD": "C",
        "D WARD": "D",
        "E WARD": "E",
        "F N": "FN",
        "F S": "FS",
        "G N": "GN",
        "G S": "GS",
        "H E": "HE",
        "H W": "HW",
        "K E": "KE",
        "K W": "KW",
        "M E": "ME",
        "M W": "MW",
        "P N": "PN",
        "P E": "PE",
        "P S": "PS",
        "R C": "RC",
        "R N": "RN",
        "R S": "RS",
    }

    if text in aliases:
        return aliases[text]

    # Remove remaining spaces for short ward codes
    compact = text.replace(" ", "")

    if compact in PROGRAMME_WARDS:
        return compact

    return compact


def get_disease_column(df):
    return find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
            "Diagnosis",
            "Condition",
            "Disease Type",
        ],
    )


def get_ward_column(df):
    return find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "Ward_Name",
            "Administrative Ward",
            "Admin Ward",
            "Programme Ward",
        ],
    )


# ============================================================
# COORDINATE PREPARATION
# ============================================================

def prepare_coordinates(df):
    """
    Keeps all valid latitude/longitude records.

    IMPORTANT:
    No artificial BMC/Mumbai geographic restriction is applied.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    lat_col = find_column(
        df,
        [
            "Address Latitude",
            "Latitude",
            "Lat",
            "address latitude",
        ],
    )

    lon_col = find_column(
        df,
        [
            "Address Longitude",
            "Longitude",
            "Long",
            "Lng",
            "Lon",
            "address longitude",
        ],
    )

    if not lat_col or not lon_col:
        return pd.DataFrame()

    work = df.copy()

    work["_Latitude"] = pd.to_numeric(
        work[lat_col],
        errors="coerce"
    )

    work["_Longitude"] = pd.to_numeric(
        work[lon_col],
        errors="coerce"
    )

    work = work.dropna(
        subset=["_Latitude", "_Longitude"]
    ).copy()

    # Geographic sanity check only.
    # This is NOT a Mumbai/BMC restriction.
    work = work[
        work["_Latitude"].between(-90, 90)
        & work["_Longitude"].between(-180, 180)
    ].copy()

    return work


# ============================================================
# BMC WARD BOUNDARIES
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
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
            timeout=8,
        )

        response.raise_for_status()

        data = response.json()

        if not data:
            return None

        return data

    except Exception:
        return None


def get_geojson_ward_name(feature):

    properties = feature.get("properties", {})

    possible_fields = [
        "NAME",
        "Name",
        "name",
        "WARD",
        "Ward",
        "WARD_NAME",
        "Ward_Name",
        "ward_name",
        "W_NAME",
    ]

    for field in possible_fields:
        if field in properties:
            value = normalise_ward(properties[field])
            if value:
                return value

    # fallback
    for key, value in properties.items():
        key_text = str(key).upper()

        if "WARD" in key_text or key_text == "NAME":
            normalized = normalise_ward(value)
            if normalized:
                return normalized

    return ""


# ============================================================
# POINT-IN-POLYGON HELPERS
# ============================================================

def point_in_ring(point, ring):
    """
    Ray casting algorithm.
    """

    x, y = point

    inside = False

    if not ring:
        return False

    j = len(ring) - 1

    for i in range(len(ring)):

        xi, yi = ring[i]
        xj, yj = ring[j]

        intersects = (
            ((yi > y) != (yj > y))
            and
            (
                x
                <
                (xj - xi)
                * (y - yi)
                / ((yj - yi) if (yj - yi) != 0 else 1e-12)
                + xi
            )
        )

        if intersects:
            inside = not inside

        j = i

    return inside


def point_in_polygon(point, polygon):

    if not polygon:
        return False

    outer = polygon[0]

    if point_in_ring(point, outer):
        # Hole handling
        for hole in polygon[1:]:
            if point_in_ring(point, hole):
                return False

        return True

    return False


def point_in_geometry(point, geometry):

    if not geometry:
        return False

    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if geom_type == "Polygon":
        return point_in_polygon(point, coordinates)

    if geom_type == "MultiPolygon":

        for polygon in coordinates:
            if point_in_polygon(point, polygon):
                return True

    return False


def spatially_resolve_wards(df, geojson):

    """
    Spatial ward assignment.

    IMPORTANT CURRENT LOGIC:
    PE and PN are NOT forced into separate geographic polygons.

    We preserve the original PE / PN values.

    For mapping aggregation, they can later be treated as P-combined.
    """

    if df is None or df.empty:
        return df

    result = df.copy()

    ward_col = get_ward_column(result)

    if ward_col:
        result["_Original_Ward"] = (
            result[ward_col]
            .apply(normalise_ward)
        )
    else:
        result["_Original_Ward"] = ""

    result["_Map_Ward"] = result["_Original_Ward"]

    # --------------------------------------------------------
    # TEMPORARY PE + PN COMBINATION FOR MAP AGGREGATION
    # --------------------------------------------------------

    result.loc[
        result["_Original_Ward"].isin(["PE", "PN"]),
        "_Map_Ward"
    ] = "P"

    # If boundary is available, resolve only cases that do not
    # already have a usable programme ward.
    if geojson and isinstance(geojson, dict):

        features = geojson.get("features", [])

        unresolved_mask = (
            result["_Original_Ward"]
            .fillna("")
            .astype(str)
            .eq("")
        )

        if unresolved_mask.any():

            for idx in result[unresolved_mask].index:

                lat = result.loc[idx, "_Latitude"]
                lon = result.loc[idx, "_Longitude"]

                found_ward = ""

                for feature in features:

                    geometry = feature.get("geometry")

                    if not geometry:
                        continue

                    if point_in_geometry(
                        (lon, lat),
                        geometry
                    ):

                        found_ward = get_geojson_ward_name(
                            feature
                        )

                        if found_ward:
                            break

                if found_ward:
                    result.loc[idx, "_Original_Ward"] = found_ward
                    result.loc[idx, "_Map_Ward"] = found_ward

    return result


# ============================================================
# CASE POINTS
# ============================================================

def create_case_points(df):

    if df is None or df.empty:
        return pd.DataFrame()

    disease_col = get_disease_column(df)

    work = df.copy()

    if disease_col:
        work["_Disease"] = (
            work[disease_col]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
        )
    else:
        work["_Disease"] = "Unknown"

    if "_Original_Ward" not in work.columns:

        ward_col = get_ward_column(work)

        if ward_col:
            work["_Original_Ward"] = (
                work[ward_col]
                .apply(normalise_ward)
            )
        else:
            work["_Original_Ward"] = ""

    # Case ID
    work["_Case_ID"] = range(1, len(work) + 1)

    points = pd.DataFrame(
        {
            "Case_ID": work["_Case_ID"],
            "Disease": work["_Disease"],
            "Ward": work["_Original_Ward"],
            "Latitude": work["_Latitude"],
            "Longitude": work["_Longitude"],
        }
    )

    # --------------------------------------------------------
    # PE / PN MAP COLORS
    # --------------------------------------------------------

    def point_color(ward):

        ward = normalise_ward(ward)

        if ward == "PE":
            return [30, 100, 220, 190]

        if ward == "PN":
            return [130, 70, 200, 190]

        return [70, 120, 180, 160]

    points["Point_Color"] = points["Ward"].apply(
        point_color
    )

    return points


# ============================================================
# HOTSPOT CLUSTERS
# ============================================================

def create_hotspots(df):

    if df is None or df.empty:
        return pd.DataFrame()

    if len(df) == 0:
        return pd.DataFrame()

    work = df.copy()

    # Rounded geographic cells.
    # Keeps hotspot calculation lightweight.
    work["_Lat_Cell"] = (
        work["_Latitude"]
        .round(3)
    )

    work["_Lon_Cell"] = (
        work["_Longitude"]
        .round(3)
    )

    group_cols = [
        "_Lat_Cell",
        "_Lon_Cell",
    ]

    hotspot = (
        work.groupby(group_cols)
        .size()
        .reset_index(name="Cluster_Cases")
    )

    hotspot = hotspot[
        hotspot["Cluster_Cases"] >= 2
    ].copy()

    if hotspot.empty:
        return hotspot

    hotspot["Latitude"] = hotspot["_Lat_Cell"]
    hotspot["Longitude"] = hotspot["_Lon_Cell"]

    return hotspot[
        [
            "Latitude",
            "Longitude",
            "Cluster_Cases",
        ]
    ]


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):

    if df is None or df.empty:
        return pd.DataFrame()

    if "_Original_Ward" not in df.columns:
        return pd.DataFrame()

    summary = (
        df.groupby("_Original_Ward")
        .size()
        .reset_index(name="Cases")
        .rename(
            columns={
                "_Original_Ward": "Ward"
            }
        )
    )

    # Ensure all programme wards remain visible
    master = pd.DataFrame(
        {
            "Ward": PROGRAMME_WARDS
        }
    )

    summary = master.merge(
        summary,
        on="Ward",
        how="left"
    )

    summary["Cases"] = (
        summary["Cases"]
        .fillna(0)
        .astype(int)
    )

    # Explicit PE / PN rows remain separate.
    return summary.sort_values(
        "Cases",
        ascending=False
    ).reset_index(drop=True)


def create_map_ward_summary(df):

    """
    Mapping-only ward summary.

    PE + PN are combined into P.

    This DOES NOT change the reporting summary.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    if "_Map_Ward" not in df.columns:
        return pd.DataFrame()

    summary = (
        df.groupby("_Map_Ward")
        .size()
        .reset_index(name="Cases")
        .rename(
            columns={
                "_Map_Ward": "Ward"
            }
        )
    )

    return summary.sort_values(
        "Cases",
        ascending=False
    ).reset_index(drop=True)


# ============================================================
# CHOROPLETH
# ============================================================

def get_choropleth_color(value, max_value):

    if max_value <= 0:
        return [230, 230, 230, 80]

    ratio = value / max_value

    ratio = max(
        0,
        min(1, ratio)
    )

    # Light -> dark red
    r = 255

    g = int(
        245
        - (ratio * 180)
    )

    b = int(
        245
        - (ratio * 180)
    )

    return [
        r,
        g,
        b,
        150
    ]


def prepare_bmc_choropleth(
    geojson,
    df,
    selected_diseases=None
):

    if not geojson:
        return None

    features = geojson.get(
        "features",
        []
    )

    if not features:
        return None

    work = df.copy()

    # Disease filtering
    if selected_diseases:

        disease_col = get_disease_column(work)

        if disease_col:

            work = work[
                work[disease_col]
                .fillna("")
                .astype(str)
                .str.strip()
                .isin(selected_diseases)
            ].copy()

    if work.empty:

        counts = {}

    else:

        if "_Map_Ward" not in work.columns:
            work["_Map_Ward"] = ""

        counts = (
            work.groupby("_Map_Ward")
            .size()
            .to_dict()
        )

    max_value = max(
        counts.values()
    ) if counts else 0

    new_features = []

    for feature in features:

        feature_copy = {
            "type": "Feature",
            "geometry": feature.get("geometry"),
            "properties": dict(
                feature.get("properties", {})
            ),
        }

        ward_name = get_geojson_ward_name(
            feature
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # Do NOT separately paint PE and PN polygons.
        #
        # We only accept a combined P polygon if the source
        # actually contains one.
        # ----------------------------------------------------

        normalized_boundary = normalise_ward(
            ward_name
        )

        if normalized_boundary in [
            "PE",
            "PN"
        ]:

            # Keep boundary neutral.
            # PE/PN are represented by actual case points and
            # separate legend entries.
            case_count = 0

        else:

            case_count = int(
                counts.get(
                    normalized_boundary,
                    0
                )
            )

            # Support an actual P polygon if the boundary
            # source provides one.
            if normalized_boundary == "P":
                case_count = int(
                    counts.get(
                        "P",
                        0
                    )
                )

        feature_copy["properties"][
            "_MapWard"
        ] = normalized_boundary

        feature_copy["properties"][
            "_Cases"
        ] = case_count

        feature_copy["properties"][
            "_FillColor"
        ] = get_choropleth_color(
            case_count,
            max_value
        )

        new_features.append(
            feature_copy
        )

    return {
        "type": "FeatureCollection",
        "features": new_features,
    }


# ============================================================
# DISEASE SELECTION
# ============================================================

def get_available_diseases(df):

    if df is None or df.empty:
        return []

    disease_col = get_disease_column(df)

    if not disease_col:
        return []

    diseases = (
        df[disease_col]
        .dropna()
        .astype(str)
        .str.strip()
    )

    diseases = [
        d for d in diseases.unique()
        if d
    ]

    diseases = sorted(
        diseases,
        key=lambda x: x.lower()
    )

    return diseases


def disease_checkbox_selector(
    df,
    key_prefix="geo"
):

    diseases = get_available_diseases(df)

    if not diseases:
        st.warning(
            "Disease column / disease data उपलब्ध नाही."
        )
        return []

    select_all_key = (
        f"{key_prefix}_select_all"
    )

    reset_key = (
        f"{key_prefix}_reset"
    )

    # --------------------------------------------------------
    # INITIAL STATE
    # --------------------------------------------------------

    if (
        f"{key_prefix}_initialized"
        not in st.session_state
    ):

        st.session_state[
            f"{key_prefix}_initialized"
        ] = True

        st.session_state[
            select_all_key
        ] = True

        for disease in diseases:

            st.session_state[
                f"{key_prefix}_disease_{disease}"
            ] = True

    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------

    if st.button(
        "🔄 Reset Disease Selection",
        key=reset_key,
        use_container_width=False,
    ):

        st.session_state[
            select_all_key
        ] = True

        for disease in diseases:

            st.session_state[
                f"{key_prefix}_disease_{disease}"
            ] = True

        st.rerun()

    # --------------------------------------------------------
    # SELECT ALL
    # --------------------------------------------------------

    select_all = st.checkbox(
        "☑️ Select All",
        key=select_all_key,
    )

    # --------------------------------------------------------
    # INDIVIDUAL DISEASE CHECKBOXES
    # --------------------------------------------------------

    selected = []

    st.markdown(
        """
        <div style="
            font-size:13px;
            color:#666;
            margin-bottom:6px;
        ">
        Tick one or more diseases for comparison.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # If Select All is ON, show all as checked.
    if select_all:

        for disease in diseases:

            disease_key = (
                f"{key_prefix}_disease_{disease}"
            )

            # Keep state synchronized
            st.session_state[
                disease_key
            ] = True

            checked = st.checkbox(
                disease,
                key=disease_key,
            )

            if checked:
                selected.append(disease)

        return selected

    # --------------------------------------------------------
    # INDIVIDUAL MODE
    # --------------------------------------------------------

    for disease in diseases:

        disease_key = (
            f"{key_prefix}_disease_{disease}"
        )

        # Callback:
        # If any individual selection is changed,
        # Select All should turn OFF.
        def turn_off_select_all(
            key=select_all_key
        ):
            st.session_state[key] = False

        checked = st.checkbox(
            disease,
            key=disease_key,
            on_change=turn_off_select_all,
        )

        if checked:
            selected.append(disease)

    return selected


# ============================================================
# MAP LEGEND
# ============================================================

def render_map_legend(df):

    if df is None or df.empty:
        return

    ward_series = (
        df["_Original_Ward"]
        if "_Original_Ward" in df.columns
        else pd.Series(dtype=str)
    )

    pe_count = int(
        (ward_series == "PE").sum()
    )

    pn_count = int(
        (ward_series == "PN").sum()
    )

    total = len(df)

    st.markdown(
        f"""
        <div style="
            display:flex;
            flex-wrap:wrap;
            gap:18px;
            align-items:center;
            padding:10px 14px;
            margin:8px 0 12px 0;
            border:1px solid #ddd;
            border-radius:8px;
            background:#fafafa;
            font-size:13px;
        ">

            <div>
                <span style="
                    display:inline-block;
                    width:12px;
                    height:12px;
                    border-radius:50%;
                    background:rgb(30,100,220);
                    margin-right:6px;
                "></span>
                <b>PE</b> — {pe_count}
            </div>

            <div>
                <span style="
                    display:inline-block;
                    width:12px;
                    height:12px;
                    border-radius:50%;
                    background:rgb(130,70,200);
                    margin-right:6px;
                "></span>
                <b>PN</b> — {pn_count}
            </div>

            <div>
                <span style="
                    display:inline-block;
                    width:12px;
                    height:12px;
                    border-radius:50%;
                    background:rgb(70,120,180);
                    margin-right:6px;
                "></span>
                Other Cases
            </div>

            <div>
                <span style="
                    display:inline-block;
                    width:12px;
                    height:12px;
                    border-radius:50%;
                    background:rgb(220,60,60);
                    margin-right:6px;
                "></span>
                Hotspot
            </div>

            <div style="margin-left:auto;">
                <b>Total mapped cases:</b> {total}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PYDECK MAP
# ============================================================

def build_map(
    case_points,
    hotspots=None,
    choropleth=None,
    show_choropleth=True,
):

    layers = []

    # --------------------------------------------------------
    # CHOROPLETH
    # --------------------------------------------------------

    if show_choropleth and choropleth:

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=choropleth,
                pickable=True,
                stroked=True,
                filled=True,
                get_fill_color="properties._FillColor",
                get_line_color=[
                    70,
                    70,
                    70,
                    180
                ],
                line_width_min_pixels=1,
                opacity=0.55,
                auto_highlight=True,
            )
        )

    # --------------------------------------------------------
    # CASE POINTS
    # --------------------------------------------------------

    if (
        case_points is not None
        and not case_points.empty
    ):

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=case_points,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_fill_color="Point_Color",
                get_radius=45,
                radius_min_pixels=2,
                radius_max_pixels=7,
                pickable=True,
                stroked=False,
            )
        )

    # --------------------------------------------------------
    # HOTSPOTS
    # --------------------------------------------------------

    if (
        hotspots is not None
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
                get_fill_color=[
                    220,
                    50,
                    50,
                    120
                ],
                get_radius=(
                    "60 + "
                    "min("
                    "Cluster_Cases * 8,"
                    "160)"
                ),
                radius_min_pixels=3,
                radius_max_pixels=16,
                pickable=True,
                stroked=False,
            )
        )

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    if (
        case_points is not None
        and not case_points.empty
    ):

        center_lat = float(
            case_points["Latitude"].median()
        )

        center_lon = float(
            case_points["Longitude"].median()
        )

    else:

        center_lat = 19.0760
        center_lon = 72.8777

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=10.5,
        pitch=0,
        bearing=0,
    )

    tooltip = {
        "html": """
        <b>Case ID:</b> {Case_ID}<br/>
        <b>Disease:</b> {Disease}<br/>
        <b>Ward:</b> {Ward}<br/>
        <b>Latitude:</b> {Latitude}<br/>
        <b>Longitude:</b> {Longitude}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black",
        },
    }

    if hotspots is not None and not hotspots.empty:

        tooltip = {
            "html": """
            <b>Hotspot</b><br/>
            <b>Cluster Cases:</b> {Cluster_Cases}<br/>
            <b>Latitude:</b> {Latitude}<br/>
            <b>Longitude:</b> {Longitude}
            """,
            "style": {
                "backgroundColor": "white",
                "color": "black",
            },
        }

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style=None,
    )

    return deck


# ============================================================
# DISEASE COMPARISON
# ============================================================

def create_disease_comparison(
    df,
    selected_diseases=None
):

    if df is None or df.empty:
        return pd.DataFrame()

    disease_col = get_disease_column(df)

    if not disease_col:
        return pd.DataFrame()

    work = df.copy()

    work["_Disease"] = (
        work[disease_col]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    if selected_diseases:
        work = work[
            work["_Disease"].isin(
                selected_diseases
            )
        ].copy()

    if work.empty:
        return pd.DataFrame()

    comparison = (
        work.groupby("_Disease")
        .size()
        .reset_index(
            name="Cases"
        )
        .rename(
            columns={
                "_Disease": "Disease"
            }
        )
    )

    comparison = comparison.sort_values(
        "Cases",
        ascending=False
    ).reset_index(drop=True)

    return comparison


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_geographic_map(
    filtered_df,
    full_df=None
):

    st.title(
        "🗺️ Geographic Disease Hotspot & Ward Analysis"
    )

    st.caption(
        "Facility-wise, ward-wise, disease-wise and "
        "geographic case distribution"
    )

    if filtered_df is None or filtered_df.empty:

        st.warning(
            "Current filter नुसार geographic data उपलब्ध नाही."
        )

        return

    # --------------------------------------------------------
    # COORDINATES
    # --------------------------------------------------------

    geo_df = prepare_coordinates(
        filtered_df
    )

    if geo_df.empty:

        st.warning(
            "Address Latitude / Address Longitude मध्ये "
            "valid geographic coordinates उपलब्ध नाहीत."
        )

        return

    # --------------------------------------------------------
    # WARD RESOLUTION
    # --------------------------------------------------------

    wards_geojson = load_bmc_wards()

    geo_df = spatially_resolve_wards(
        geo_df,
        wards_geojson
    )

    # --------------------------------------------------------
    # DISEASE SELECTION
    # --------------------------------------------------------

    st.subheader(
        "🦠 Disease Selection"
    )

    selected_diseases = disease_checkbox_selector(
        geo_df,
        key_prefix="geographic_disease"
    )

    if not selected_diseases:

        st.info(
            "किमान एक disease select करा."
        )

        return

    st.markdown(
        f"""
        **Selected diseases:** {len(selected_diseases)}
        """
    )

    # --------------------------------------------------------
    # FILTER BY SELECTED DISEASES
    # --------------------------------------------------------

    disease_col = get_disease_column(
        geo_df
    )

    map_df = geo_df.copy()

    if disease_col:

        map_df["_Disease"] = (
            map_df[disease_col]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
        )

        map_df = map_df[
            map_df["_Disease"].isin(
                selected_diseases
            )
        ].copy()

    if map_df.empty:

        st.warning(
            "Selected disease साठी coordinates उपलब्ध नाहीत."
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

    # --------------------------------------------------------
    # MAP SUMMARY
    # --------------------------------------------------------

    map_ward_summary = create_map_ward_summary(
        map_df
    )

    # --------------------------------------------------------
    # CHOROPLETH
    # --------------------------------------------------------

    choropleth = prepare_bmc_choropleth(
        wards_geojson,
        map_df,
        selected_diseases=selected_diseases,
    )

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📍 Case Locations",
            "📊 Disease Comparison",
            "🏘️ Choropleth Comparison",
            "🗺️ Combined Geographic View",
        ]
    )

    # ========================================================
    # TAB 1
    # ========================================================

    with tab1:

        st.subheader(
            "📍 Geographic Case Locations"
        )

        render_map_legend(
            map_df
        )

        deck = build_map(
            case_points=case_points,
            hotspots=None,
            choropleth=None,
            show_choropleth=False,
        )

        st.pydeck_chart(
            deck,
            use_container_width=True,
        )

        st.markdown(
            f"""
            **Mapped cases:** {len(case_points):,}
            """
        )

        if not ward_summary.empty:

            st.markdown(
                "### Ward-wise mapped cases"
            )

            st.dataframe(
                ward_summary,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # TAB 2
    # ========================================================

    with tab2:

        st.subheader(
            "📊 Disease-wise Geographic Comparison"
        )

        disease_comparison = (
            create_disease_comparison(
                map_df,
                selected_diseases,
            )
        )

        if not disease_comparison.empty:

            st.dataframe(
                disease_comparison,
                use_container_width=True,
                hide_index=True,
            )

            st.bar_chart(
                disease_comparison.set_index(
                    "Disease"
                )["Cases"]
            )

        else:

            st.info(
                "Disease comparison साठी data उपलब्ध नाही."
            )

    # ========================================================
    # TAB 3
    # ========================================================

    with tab3:

        st.subheader(
            "🏘️ Ward-wise Disease Choropleth"
        )

        st.info(
            "PE आणि PN सध्या geographic mapping साठी "
            "एकत्र P-area logic मध्ये हाताळले जात आहेत. "
            "त्यांचे reporting counts मात्र स्वतंत्र ठेवले आहेत."
        )

        if choropleth:

            deck = build_map(
                case_points=None,
                hotspots=None,
                choropleth=choropleth,
                show_choropleth=True,
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
            )

        else:

            st.warning(
                "Ward boundary data उपलब्ध नाही."
            )

        if not ward_summary.empty:

            st.markdown(
                "### 📋 Ward-wise Summary"
            )

            st.dataframe(
                ward_summary,
                use_container_width=True,
                hide_index=True,
            )

        # PE / PN separate summary
        pe_cases = int(
            (
                map_df["_Original_Ward"]
                == "PE"
            ).sum()
        )

        pn_cases = int(
            (
                map_df["_Original_Ward"]
                == "PN"
            ).sum()
        )

        st.markdown(
            f"""
            ### PE / PN Separate Reporting

            - **PE:** {pe_cases:,} cases
            - **PN:** {pn_cases:,} cases
            - **PE + PN combined mapping burden:** {pe_cases + pn_cases:,} cases
            """
        )

    # ========================================================
    # TAB 4
    # ========================================================

    with tab4:

        st.subheader(
            "🗺️ Combined Geographic Management View"
        )

        # Legend FIRST
        render_map_legend(
            map_df
        )

        deck = build_map(
            case_points=case_points,
            hotspots=hotspots,
            choropleth=choropleth,
            show_choropleth=True,
        )

        st.pydeck_chart(
            deck,
            use_container_width=True,
        )

        # ----------------------------------------------------
        # MANAGEMENT SUMMARY
        # ----------------------------------------------------

        st.markdown(
            "### 📊 Geographic Management Summary"
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Mapped Cases",
            f"{len(case_points):,}"
        )

        col2.metric(
            "Hotspot Clusters",
            f"{len(hotspots):,}"
        )

        pe_cases = int(
            (
                map_df["_Original_Ward"]
                == "PE"
            ).sum()
        )

        pn_cases = int(
            (
                map_df["_Original_Ward"]
                == "PN"
            ).sum()
        )

        col3.metric(
            "PE Cases",
            f"{pe_cases:,}"
        )

        col4.metric(
            "PN Cases",
            f"{pn_cases:,}"
        )

        # ----------------------------------------------------
        # SEPARATE PE / PN SUMMARY
        # ----------------------------------------------------

        st.markdown(
            "### 🏘️ PE / PN Separate Summary"
        )

        pe_pn_summary = pd.DataFrame(
            {
                "Ward": [
                    "PE",
                    "PN",
                    "PE + PN Combined",
                ],
                "Cases": [
                    pe_cases,
                    pn_cases,
                    pe_cases + pn_cases,
                ],
            }
        )

        st.dataframe(
            pe_pn_summary,
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # WARD SUMMARY
        # ----------------------------------------------------

        st.markdown(
            "### 🏘️ Ward-wise Summary"
        )

        if not ward_summary.empty:

            st.dataframe(
                ward_summary,
                use_container_width=True,
                hide_index=True,
            )

        # ----------------------------------------------------
        # MAP AGGREGATION SUMMARY
        # ----------------------------------------------------

        st.markdown(
            "### 🗺️ Mapping Aggregation"
        )

        if not map_ward_summary.empty:

            st.dataframe(
                map_ward_summary,
                use_container_width=True,
                hide_index=True,
            )
