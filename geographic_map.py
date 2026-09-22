# geographic_map.py
# ============================================================
# GEOGRAPHIC MANAGEMENT MAP
# BMC WARD + ALL VALID COORDINATES
# ============================================================

import io
import json
import math
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import pydeck as pdk
except Exception:
    pdk = None


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
BMC_GEOJSON = BASE_DIR / "data" / "BMC_Wards.geojson"

LAT_COLUMN = "Address Latitude"
LON_COLUMN = "Address Longitude"

# Approximate hotspot grid
# 0.005 degree ~= ~500 metres around Mumbai
GRID_DEGREE = 0.005


# ============================================================
# HELPERS
# ============================================================

def _clean_text(value):
    if pd.isna(value):
        return ""

    value = str(value).strip()

    if value.lower() in {
        "nan",
        "none",
        "null",
        "nat",
        "na",
        "n/a",
    }:
        return ""

    return value


def _find_column(df, candidates):
    if df is None or df.empty:
        return None

    lookup = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower()

        if key in lookup:
            return lookup[key]

    return None


def _normalise_ward(value):
    """
    Converts common BMC ward formats into a consistent form.

    Examples:
        F North -> F/N
        F-N     -> F/N
        F/N     -> F/N
        K East  -> K/E
    """

    value = _clean_text(value).upper()

    if not value:
        return ""

    value = value.replace("_", " ")
    value = value.replace("-", "/")
    value = value.replace("\\", "/")

    replacements = {
        "F NORTH": "F/N",
        "F SOUTH": "F/S",
        "G NORTH": "G/N",
        "G SOUTH": "G/S",
        "H EAST": "H/E",
        "H WEST": "H/W",
        "K EAST": "K/E",
        "K WEST": "K/W",
        "M EAST": "M/E",
        "M WEST": "M/W",
        "P NORTH": "P/N",
        "P SOUTH": "P/S",
        "R CENTRAL": "R/C",
        "R NORTH": "R/N",
        "R SOUTH": "R/S",
    }

    if value in replacements:
        return replacements[value]

    value = " ".join(value.split())

    if value in replacements:
        return replacements[value]

    # Handle strings such as "Ward F North"
    value = value.replace("WARD ", "")

    if value in replacements:
        return replacements[value]

    return value


def _ward_field_from_geojson(geojson):
    """
    Detect ward-name field from GeoJSON properties.
    """

    features = geojson.get("features", [])

    if not features:
        return None

    props = features[0].get("properties", {}) or {}

    candidates = [
        "NAME",
        "WARD_NAME",
        "Ward",
        "WARD",
        "ward",
        "Name",
    ]

    for candidate in candidates:
        if candidate in props:
            return candidate

    # fallback: look for anything containing ward/name
    for key in props.keys():
        key_l = str(key).lower()

        if "ward" in key_l or key_l == "name":
            return key

    return None


# ============================================================
# LOAD LOCAL BMC GEOJSON
# ============================================================

@st.cache_data(show_spinner=False)
def load_bmc_wards():
    """
    Loads local BMC ward GeoJSON.

    No external HTTP request is made here.
    """

    if not BMC_GEOJSON.exists():
        return None, (
            f"BMC ward boundary file not found: "
            f"{BMC_GEOJSON.as_posix()}"
        )

    try:
        with open(BMC_GEOJSON, "r", encoding="utf-8") as f:
            geojson = json.load(f)

        if not isinstance(geojson, dict):
            return None, "BMC ward GeoJSON is not a valid object."

        if geojson.get("type") != "FeatureCollection":
            return None, "BMC ward GeoJSON must be a FeatureCollection."

        features = geojson.get("features", [])

        if not features:
            return None, "BMC ward GeoJSON contains no features."

        return geojson, None

    except Exception as e:
        return None, f"Could not read BMC ward GeoJSON: {e}"


# ============================================================
# COORDINATE PREPARATION
# ============================================================

def prepare_coordinates(df):
    """
    Prepare ALL valid coordinates.

    IMPORTANT:
    No Mumbai/BMC geographic bounding-box filtering is performed.
    Therefore valid coordinates outside BMC are retained.
    """

    if df is None or df.empty:
        return pd.DataFrame(), 0

    if LAT_COLUMN not in df.columns or LON_COLUMN not in df.columns:
        return pd.DataFrame(), 0

    work = df.copy()

    work["_lat"] = pd.to_numeric(
        work[LAT_COLUMN],
        errors="coerce",
    )

    work["_lon"] = pd.to_numeric(
        work[LON_COLUMN],
        errors="coerce",
    )

    # Count all rows with unusable coordinates
    invalid_count = int(
        (
            work["_lat"].isna()
            | work["_lon"].isna()
            | ~work["_lat"].between(-90, 90)
            | ~work["_lon"].between(-180, 180)
        ).sum()
    )

    # Keep every globally valid coordinate
    work = work[
        work["_lat"].between(-90, 90)
        & work["_lon"].between(-180, 180)
    ].copy()

    work.reset_index(drop=True, inplace=True)

    return work, invalid_count


# ============================================================
# HOTSPOT CLUSTERING
# ============================================================

def create_hotspots(df):
    """
    Grid-based hotspot clustering.

    All valid coordinates are included.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    if "_lat" not in work.columns or "_lon" not in work.columns:
        return pd.DataFrame()

    # Grid cells
    work["_grid_lat"] = (
        work["_lat"] / GRID_DEGREE
    ).apply(math.floor)

    work["_grid_lon"] = (
        work["_lon"] / GRID_DEGREE
    ).apply(math.floor)

    # Cluster ID
    work["Cluster ID"] = (
        "C_"
        + work["_grid_lat"].astype(str)
        + "_"
        + work["_grid_lon"].astype(str)
    )

    # Cluster case count
    cluster_counts = (
        work.groupby("Cluster ID")
        .size()
        .rename("Cluster Cases")
        .reset_index()
    )

    work = work.merge(
        cluster_counts,
        on="Cluster ID",
        how="left",
    )

    # Hotspot classification
    def classify(n):
        if n >= 10:
            return "High"
        elif n >= 5:
            return "Moderate"
        else:
            return "Low"

    work["Hotspot Classification"] = (
        work["Cluster Cases"]
        .fillna(0)
        .astype(int)
        .apply(classify)
    )

    return work


def create_cluster_summary(hotspot_df):
    """
    One row per geographic hotspot cluster.
    """

    if hotspot_df is None or hotspot_df.empty:
        return pd.DataFrame()

    summary = (
        hotspot_df
        .groupby(
            "Cluster ID",
            as_index=False,
        )
        .agg(
            Latitude=("_lat", "mean"),
            Longitude=("_lon", "mean"),
            Cluster_Cases=("Cluster Cases", "max"),
            Hotspot_Classification=(
                "Hotspot Classification",
                "first",
            ),
        )
    )

    summary.rename(
        columns={
            "Cluster_Cases": "Cluster Cases",
            "Hotspot_Classification": "Hotspot Classification",
        },
        inplace=True,
    )

    return summary


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):
    if df is None or df.empty:
        return pd.DataFrame()

    ward_col = _find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "Ward_Name",
            "WARD",
            "WARD NAME",
            "BMC Ward",
            "Administrative Ward",
        ],
    )

    if ward_col is None:
        return pd.DataFrame()

    temp = df.copy()

    temp["_ward_clean"] = (
        temp[ward_col]
        .apply(_normalise_ward)
    )

    temp = temp[
        temp["_ward_clean"] != ""
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    summary = (
        temp.groupby("_ward_clean")
        .size()
        .reset_index(name="Cases")
    )

    summary.rename(
        columns={
            "_ward_clean": "Ward"
        },
        inplace=True,
    )

    summary.sort_values(
        "Cases",
        ascending=False,
        inplace=True,
    )

    summary.reset_index(drop=True, inplace=True)

    return summary


# ============================================================
# ADD WARD CASE COUNT TO GEOJSON
# ============================================================

def merge_ward_counts_into_geojson(
    geojson,
    ward_summary,
):
    if geojson is None:
        return None

    output = json.loads(
        json.dumps(geojson)
    )

    if ward_summary is None or ward_summary.empty:
        return output

    counts = dict(
        zip(
            ward_summary["Ward"],
            ward_summary["Cases"],
        )
    )

    ward_field = _ward_field_from_geojson(output)

    if ward_field is None:
        return output

    for feature in output.get("features", []):
        props = feature.setdefault(
            "properties",
            {},
        )

        ward_value = _normalise_ward(
            props.get(ward_field, "")
        )

        props["Programme Cases"] = int(
            counts.get(ward_value, 0)
        )

    return output


# ============================================================
# MAP CENTER
# ============================================================

def _default_center():
    return {
        "latitude": 19.0760,
        "longitude": 72.8777,
        "zoom": 10.2,
        "pitch": 0,
        "bearing": 0,
    }


def _all_coordinate_center(df):
    if df is None or df.empty:
        return _default_center()

    lat = df["_lat"].mean()
    lon = df["_lon"].mean()

    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "zoom": 5.5,
        "pitch": 0,
        "bearing": 0,
    }


# ============================================================
# PYDECK MAP
# ============================================================

def render_pydeck_map(
    hotspot_df,
    bmc_geojson=None,
    ward_map=False,
    all_extent=False,
):
    if pdk is None:
        st.error(
            "PyDeck is not available in this environment."
        )
        return

    layers = []

    # --------------------------------------------------------
    # BMC WARD POLYGON
    # --------------------------------------------------------

    if ward_map and bmc_geojson is not None:

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=bmc_geojson,
                pickable=True,
                stroked=True,
                filled=True,
                extruded=False,
                get_fill_color=[
                    230,
                    230,
                    230,
                    70,
                ],
                get_line_color=[
                    60,
                    60,
                    60,
                    200,
                ],
                line_width_min_pixels=1,
            )
        )

    # --------------------------------------------------------
    # ALL COORDINATE POINTS
    # --------------------------------------------------------

    if hotspot_df is not None and not hotspot_df.empty:

        point_data = hotspot_df[
            [
                "_lat",
                "_lon",
                "Cluster ID",
                "Cluster Cases",
                "Hotspot Classification",
            ]
        ].copy()

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=point_data,
                get_position=[
                    "_lon",
                    "_lat",
                ],
                get_radius=80,
                get_fill_color=[
                    220,
                    50,
                    50,
                    170,
                ],
                get_line_color=[
                    80,
                    20,
                    20,
                    220,
                ],
                line_width_min_pixels=1,
                pickable=True,
            )
        )

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    if all_extent:
        view_state = _all_coordinate_center(
            hotspot_df
        )
    else:
        view_state = _default_center()

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=view_state["latitude"],
            longitude=view_state["longitude"],
            zoom=view_state["zoom"],
            pitch=view_state["pitch"],
            bearing=view_state["bearing"],
        ),
        tooltip={
            "html": """
                <b>Cluster:</b> {Cluster ID}<br/>
                <b>Cases:</b> {Cluster Cases}<br/>
                <b>Hotspot:</b> {Hotspot Classification}
            """,
            "style": {
                "backgroundColor": "white",
                "color": "black",
            },
        },
        map_style=None,
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
    )


# ============================================================
# DOWNLOAD HELPERS
# ============================================================

def hotspot_download_dataframe(hotspot_df):
    if hotspot_df is None or hotspot_df.empty:
        return pd.DataFrame()

    preferred = [
        "Cluster ID",
        "Cluster Cases",
        "Hotspot Classification",
        "_lat",
        "_lon",
        "Disease",
        "Date",
        "Month",
        "Ward",
        "Ward Name",
        "Facility",
        "Facility Name",
        "Address",
    ]

    available = [
        c
        for c in preferred
        if c in hotspot_df.columns
    ]

    result = hotspot_df[
        available
    ].copy()

    if "_lat" in result.columns:
        result.rename(
            columns={
                "_lat": "Latitude",
                "_lon": "Longitude",
            },
            inplace=True,
        )

    return result


def ward_excel_bytes(ward_summary):
    if ward_summary is None or ward_summary.empty:
        return None

    buffer = io.BytesIO()

    with pd.ExcelWriter(
        buffer,
        engine="openpyxl",
    ) as writer:

        ward_summary.to_excel(
            writer,
            index=False,
            sheet_name="Ward Summary",
        )

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# MAIN RENDER
# ============================================================

def render_geographic_map(filtered_df):
    st.header(
        "🗺️ Geographic Disease Management Map"
    )

    st.caption(
        "BMC ward boundaries are used as the primary "
        "management geography. All valid coordinates "
        "outside BMC are also retained and plotted."
    )

    # --------------------------------------------------------
    # LOAD BMC BOUNDARY
    # --------------------------------------------------------

    bmc_geojson, geo_error = load_bmc_wards()

    if geo_error:
        st.warning(
            "BMC ward boundary layer is not available."
        )

        st.caption(
            "The disease coordinate map will continue "
            "to work without the BMC polygon layer."
        )

    # --------------------------------------------------------
    # PREPARE COORDINATES
    # --------------------------------------------------------

    coordinate_df, invalid_count = (
        prepare_coordinates(
            filtered_df
        )
    )

    # --------------------------------------------------------
    # DATA AVAILABILITY
    # --------------------------------------------------------

    if coordinate_df.empty:

        st.info(
            "No valid Address Latitude / Address Longitude "
            "records are available for the current filters."
        )

        if invalid_count:
            st.caption(
                f"{invalid_count:,} records have missing "
                "or invalid coordinates."
            )

        return

    # --------------------------------------------------------
    # DISEASE SELECTION
    # --------------------------------------------------------

    disease_col = _find_column(
        coordinate_df,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
            "Disease Type",
        ],
    )

    map_df = coordinate_df.copy()

    if disease_col:

        diseases = sorted(
            [
                _clean_text(x)
                for x in map_df[disease_col].dropna().unique()
                if _clean_text(x)
            ]
        )

        if len(diseases) > 1:

            selected_disease = st.selectbox(
                "🦠 Select Disease to Display on Map",
                diseases,
                key="geo_disease_selection",
            )

            map_df = map_df[
                map_df[disease_col]
                .astype(str)
                .str.strip()
                == selected_disease
            ].copy()

        elif len(diseases) == 1:

            st.info(
                f"Selected disease: {diseases[0]}"
            )

    # --------------------------------------------------------
    # HOTSPOTS
    # --------------------------------------------------------

    hotspot_df = create_hotspots(
        map_df
    )

    cluster_summary = create_cluster_summary(
        hotspot_df
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Valid Coordinates",
            f"{len(map_df):,}",
        )

    with col2:
        st.metric(
            "Hotspot Clusters",
            f"{len(cluster_summary):,}",
        )

    with col3:
        if not cluster_summary.empty:
            st.metric(
                "Highest Cluster",
                f"{int(cluster_summary['Cluster Cases'].max()):,}",
            )
        else:
            st.metric(
                "Highest Cluster",
                "0",
            )

    with col4:
        st.metric(
            "Invalid Coordinates",
            f"{invalid_count:,}",
        )

    st.divider()

    # --------------------------------------------------------
    # MAP EXTENT
    # --------------------------------------------------------

    extent_option = st.radio(
        "Map Extent",
        [
            "BMC / Mumbai Focus",
            "All Coordinates",
        ],
        horizontal=True,
        key="geo_map_extent",
    )

    all_extent = (
        extent_option == "All Coordinates"
    )

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    tab1, tab2, tab3 = st.tabs(
        [
            "🔥 Hotspot Map",
            "🏘️ BMC Ward Map",
            "🗺️ BMC + All Coordinates",
        ]
    )

    # --------------------------------------------------------
    # TAB 1
    # --------------------------------------------------------

    with tab1:

        st.subheader(
            "Disease Hotspots"
        )

        st.caption(
            "All valid geographic coordinates are plotted. "
            "Points are not restricted to BMC limits."
        )

        render_pydeck_map(
            hotspot_df=hotspot_df,
            bmc_geojson=None,
            ward_map=False,
            all_extent=all_extent,
        )

        if not cluster_summary.empty:

            st.subheader(
                "Hotspot Summary"
            )

            display_summary = (
                cluster_summary
                .sort_values(
                    "Cluster Cases",
                    ascending=False,
                )
                .reset_index(drop=True)
            )

            st.dataframe(
                display_summary,
                use_container_width=True,
                hide_index=True,
            )

    # --------------------------------------------------------
    # TAB 2
    # --------------------------------------------------------

    with tab2:

        st.subheader(
            "BMC Administrative Ward Burden"
        )

        ward_summary = create_ward_summary(
            filtered_df
        )

        if (
            bmc_geojson is not None
            and not ward_summary.empty
        ):

            ward_geojson = (
                merge_ward_counts_into_geojson(
                    bmc_geojson,
                    ward_summary,
                )
            )

            render_pydeck_map(
                hotspot_df=None,
                bmc_geojson=ward_geojson,
                ward_map=True,
                all_extent=False,
            )

        elif bmc_geojson is None:

            st.info(
                "BMC_Wards.geojson is required "
                "for the ward boundary map."
            )

        else:

            st.info(
                "Ward information is not available "
                "in the current filtered data."
            )

        if not ward_summary.empty:

            st.subheader(
                "Ward-wise Programme Burden"
            )

            st.dataframe(
                ward_summary,
                use_container_width=True,
                hide_index=True,
            )

            excel_data = ward_excel_bytes(
                ward_summary
            )

            if excel_data:

                st.download_button(
                    "⬇️ Download Ward Summary Excel",
                    data=excel_data,
                    file_name=(
                        "BMC_Ward_Programme_Summary.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-"
                        "officedocument.spreadsheetml.sheet"
                    ),
                )

    # --------------------------------------------------------
    # TAB 3
    # --------------------------------------------------------

    with tab3:

        st.subheader(
            "BMC Ward Boundary + All Valid Coordinates"
        )

        st.caption(
            "BMC wards are shown as the primary management "
            "reference. Coordinates outside BMC are "
            "retained and plotted."
        )

        if bmc_geojson is not None:

            render_pydeck_map(
                hotspot_df=hotspot_df,
                bmc_geojson=bmc_geojson,
                ward_map=True,
                all_extent=all_extent,
            )

        else:

            render_pydeck_map(
                hotspot_df=hotspot_df,
                bmc_geojson=None,
                ward_map=False,
                all_extent=all_extent,
            )

    # --------------------------------------------------------
    # DOWNLOAD HOTSPOT DATA
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "📥 Geographic Data Export"
    )

    download_df = hotspot_download_dataframe(
        hotspot_df
    )

    if not download_df.empty:

        csv_data = download_df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Download Hotspot Coordinate Data",
            data=csv_data,
            file_name=(
                "Disease_Hotspot_Coordinate_Data.csv"
            ),
            mime="text/csv",
        )

        st.caption(
            "Export includes disease/facility/ward/address "
            "fields where available, coordinates, cluster ID, "
            "cluster case count and hotspot classification."
        )

    else:

        st.info(
            "No hotspot data available for download."
        )
