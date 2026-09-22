# geographic_map.py

import io
import json
import math

import pandas as pd
import requests
import streamlit as st
import pydeck as pdk


LAT_COL = "Address Latitude"
LON_COL = "Address Longitude"

# BMC ward GIS layer
BMC_WARD_URL = (
    "https://services8.arcgis.com/"
    "r6MmJtuWAzMawmJ8/arcgis/rest/services/"
    "BMConMaps_Nov26gdb/FeatureServer/24"
)

GRID_SIZE = 0.005


# =========================================================
# BASIC HELPERS
# =========================================================

def clean_text(x):
    if pd.isna(x):
        return ""
    return str(x).strip()


def find_column(df, candidates):
    lookup = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for c in candidates:
        if str(c).strip().lower() in lookup:
            return lookup[str(c).strip().lower()]

    return None


def normalise_ward(x):
    x = clean_text(x).upper()

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

    x = x.replace("-", "/")
    x = " ".join(x.split())

    return replacements.get(x, x)


# =========================================================
# LOAD BMC WARDS
# =========================================================

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

        r = requests.get(
            BMC_WARD_URL + "/query",
            params=params,
            timeout=12,
        )

        r.raise_for_status()

        data = r.json()

        if (
            isinstance(data, dict)
            and data.get("type") == "FeatureCollection"
            and data.get("features")
        ):
            return data, None

        return None, "BMC ward layer returned no features."

    except Exception as e:

        return None, str(e)


# =========================================================
# COORDINATES
# =========================================================

def prepare_coordinates(df):

    if df is None or df.empty:
        return pd.DataFrame(), 0

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame(), 0

    work = df.copy()

    work["_lat"] = pd.to_numeric(
        work[LAT_COL],
        errors="coerce",
    )

    work["_lon"] = pd.to_numeric(
        work[LON_COL],
        errors="coerce",
    )

    invalid = (
        work["_lat"].isna()
        | work["_lon"].isna()
        | ~work["_lat"].between(-90, 90)
        | ~work["_lon"].between(-180, 180)
    )

    invalid_count = int(invalid.sum())

    # IMPORTANT:
    # No BMC / Mumbai bounding-box filtering.
    work = work[~invalid].copy()

    work.reset_index(drop=True, inplace=True)

    return work, invalid_count


# =========================================================
# HOTSPOT CLUSTERING
# =========================================================

def create_hotspots(df):

    if df.empty:
        return pd.DataFrame()

    work = df.copy()

    work["_grid_lat"] = (
        work["_lat"] / GRID_SIZE
    ).apply(math.floor)

    work["_grid_lon"] = (
        work["_lon"] / GRID_SIZE
    ).apply(math.floor)

    work["Cluster ID"] = (
        "C_"
        + work["_grid_lat"].astype(str)
        + "_"
        + work["_grid_lon"].astype(str)
    )

    counts = (
        work.groupby("Cluster ID")
        .size()
        .rename("Cluster Cases")
        .reset_index()
    )

    work = work.merge(
        counts,
        on="Cluster ID",
        how="left",
    )

    def classify(n):

        if n >= 10:
            return "High"

        if n >= 5:
            return "Moderate"

        return "Low"

    work["Hotspot Classification"] = (
        work["Cluster Cases"]
        .astype(int)
        .apply(classify)
    )

    return work


def cluster_summary(df):

    if df.empty:
        return pd.DataFrame()

    result = (
        df.groupby("Cluster ID")
        .agg(
            Latitude=("_lat", "mean"),
            Longitude=("_lon", "mean"),
            Cases=("Cluster Cases", "max"),
            Hotspot=("Hotspot Classification", "first"),
        )
        .reset_index()
    )

    return result.sort_values(
        "Cases",
        ascending=False,
    )


# =========================================================
# WARD SUMMARY
# =========================================================

def create_ward_summary(df):

    ward_col = find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "Ward_Name",
            "WARD",
            "BMC Ward",
            "Administrative Ward",
        ],
    )

    if ward_col is None:
        return pd.DataFrame()

    temp = df.copy()

    temp["_ward"] = (
        temp[ward_col]
        .apply(normalise_ward)
    )

    temp = temp[
        temp["_ward"] != ""
    ]

    if temp.empty:
        return pd.DataFrame()

    result = (
        temp.groupby("_ward")
        .size()
        .reset_index(name="Cases")
    )

    result.rename(
        columns={"_ward": "Ward"},
        inplace=True,
    )

    return result.sort_values(
        "Cases",
        ascending=False,
    )


# =========================================================
# MAP
# =========================================================

def show_map(
    hotspot_df,
    bmc_geojson=None,
    show_boundary=True,
    all_extent=False,
):

    layers = []

    # BMC boundary
    if (
        show_boundary
        and bmc_geojson is not None
    ):

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=bmc_geojson,
                pickable=True,
                stroked=True,
                filled=True,
                get_fill_color=[
                    210, 210, 210, 45
                ],
                get_line_color=[
                    50, 50, 50, 220
                ],
                line_width_min_pixels=1,
            )
        )

    # All coordinates
    if (
        hotspot_df is not None
        and not hotspot_df.empty
    ):

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=hotspot_df,
                get_position=[
                    "_lon",
                    "_lat",
                ],
                get_radius=100,
                get_fill_color=[
                    220, 40, 40, 180
                ],
                get_line_color=[
                    90, 20, 20, 220
                ],
                pickable=True,
            )
        )

    if (
        hotspot_df is not None
        and not hotspot_df.empty
    ):

        if all_extent:

            lat = hotspot_df["_lat"].mean()
            lon = hotspot_df["_lon"].mean()
            zoom = 5.5

        else:

            # Main focus = Mumbai/BMC
            lat = 19.0760
            lon = 72.8777
            zoom = 10

    else:

        lat = 19.0760
        lon = 72.8777
        zoom = 10

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=float(lat),
            longitude=float(lon),
            zoom=zoom,
            pitch=0,
            bearing=0,
        ),
        tooltip={
            "html": """
            <b>Cluster:</b> {Cluster ID}<br/>
            <b>Cases:</b> {Cluster Cases}<br/>
            <b>Hotspot:</b> {Hotspot Classification}
            """,
        },
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
    )


# =========================================================
# DOWNLOAD
# =========================================================

def download_hotspot_data(df):

    if df.empty:
        return None

    preferred = [
        "Cluster ID",
        "Cluster Cases",
        "Hotspot Classification",
        "Disease",
        "Date",
        "Month",
        "Ward",
        "Ward Name",
        "Facility",
        "Facility Name",
        "Address",
        "_lat",
        "_lon",
    ]

    cols = [
        c for c in preferred
        if c in df.columns
    ]

    out = df[cols].copy()

    if "_lat" in out.columns:
        out.rename(
            columns={
                "_lat": "Latitude",
                "_lon": "Longitude",
            },
            inplace=True,
        )

    return out


# =========================================================
# MAIN
# =========================================================

def render_geographic_map(filtered_df):

    st.header(
        "🗺️ Geographic Disease Management Map"
    )

    st.caption(
        "BMC is the primary management geography. "
        "All valid coordinates outside BMC are also plotted."
    )

    # -----------------------------------------------------
    # Coordinates
    # -----------------------------------------------------

    coordinate_df, invalid_count = (
        prepare_coordinates(
            filtered_df
        )
    )

    if coordinate_df.empty:

        st.info(
            "Current filters contain no valid "
            "latitude / longitude records."
        )

        if invalid_count:
            st.caption(
                f"{invalid_count:,} records have "
                "missing or invalid coordinates."
            )

        return

    # -----------------------------------------------------
    # Disease
    # -----------------------------------------------------

    disease_col = find_column(
        coordinate_df,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
        ],
    )

    map_df = coordinate_df.copy()

    if disease_col:

        diseases = sorted(
            [
                clean_text(x)
                for x in coordinate_df[
                    disease_col
                ].dropna().unique()
                if clean_text(x)
            ]
        )

        if len(diseases) > 1:

            selected = st.selectbox(
                "🦠 Select Disease to Display",
                diseases,
                key="geo_disease",
            )

            map_df = map_df[
                map_df[disease_col]
                .astype(str)
                .str.strip()
                == selected
            ].copy()

    # -----------------------------------------------------
    # Hotspots
    # -----------------------------------------------------

    hotspot_df = create_hotspots(
        map_df
    )

    summary = cluster_summary(
        hotspot_df
    )

    # -----------------------------------------------------
    # KPI
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Valid Coordinates",
        f"{len(map_df):,}",
    )

    c2.metric(
        "Hotspot Clusters",
        f"{len(summary):,}",
    )

    c3.metric(
        "Highest Cluster",
        (
            f"{int(summary['Cases'].max()):,}"
            if not summary.empty
            else "0"
        ),
    )

    c4.metric(
        "Invalid Coordinates",
        f"{invalid_count:,}",
    )

    st.divider()

    # -----------------------------------------------------
    # Map extent
    # -----------------------------------------------------

    extent = st.radio(
        "Map View",
        [
            "BMC / Mumbai Focus",
            "All Coordinates",
        ],
        horizontal=True,
        key="geo_extent",
    )

    all_extent = (
        extent == "All Coordinates"
    )

    # -----------------------------------------------------
    # Load BMC boundary
    # -----------------------------------------------------

    bmc_geojson, bmc_error = (
        load_bmc_wards()
    )

    if bmc_error:

        st.warning(
            "BMC ward boundary could not be loaded. "
            "The coordinate hotspot map will still work."
        )

    # -----------------------------------------------------
    # Tabs
    # -----------------------------------------------------

    tab1, tab2, tab3 = st.tabs(
        [
            "🔥 Hotspots",
            "🏘️ BMC Ward",
            "🗺️ BMC + All Coordinates",
        ]
    )

    # -----------------------------------------------------
    # Hotspot
    # -----------------------------------------------------

    with tab1:

        show_map(
            hotspot_df,
            None,
            False,
            all_extent,
        )

        if not summary.empty:

            st.subheader(
                "Hotspot Summary"
            )

            st.dataframe(
                summary,
                use_container_width=True,
                hide_index=True,
            )

    # -----------------------------------------------------
    # BMC Ward
    # -----------------------------------------------------

    with tab2:

        ward_summary = (
            create_ward_summary(
                filtered_df
            )
        )

        if bmc_geojson is not None:

            show_map(
                None,
                bmc_geojson,
                True,
                False,
            )

        else:

            st.info(
                "BMC ward boundary is temporarily "
                "unavailable."
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

            st.download_button(
                "⬇️ Download Ward Summary",
                data=buffer.getvalue(),
                file_name="BMC_Ward_Summary.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
            )

    # -----------------------------------------------------
    # Combined
    # -----------------------------------------------------

    with tab3:

        show_map(
            hotspot_df,
            bmc_geojson,
            True,
            all_extent,
        )

    # -----------------------------------------------------
    # Export
    # -----------------------------------------------------

    st.divider()

    export_df = download_hotspot_data(
        hotspot_df
    )

    if export_df is not None:

        st.download_button(
            "⬇️ Download Hotspot Coordinate Data",
            data=export_df.to_csv(
                index=False
            ).encode("utf-8"),
            file_name=(
                "Disease_Hotspot_Coordinate_Data.csv"
            ),
            mime="text/csv",
        )
