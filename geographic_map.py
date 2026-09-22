# geographic_map.py

import io
import json
import os
import re

import numpy as np
import pandas as pd
import streamlit as st

try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except Exception:
    GEOPANDAS_AVAILABLE = False

try:
    import pydeck as pdk
    PYDECK_AVAILABLE = True
except Exception:
    PYDECK_AVAILABLE = False


# ============================================================
# SETTINGS
# ============================================================

WARD_GEOJSON_PATHS = [
    "data/BMC_Wards.geojson",
    "data/BMC_Wards.json",
    "BMC_Wards.geojson",
    "BMC_admin_wards.geojson",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def _norm(value):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(value).strip().lower(),
    )


def _find_column(df, candidates):

    if df is None or df.empty:
        return None

    normalized = {
        _norm(c): c
        for c in df.columns
    }

    for candidate in candidates:

        key = _norm(candidate)

        if key in normalized:
            return normalized[key]

    for c in df.columns:

        nc = _norm(c)

        for candidate in candidates:

            key = _norm(candidate)

            if key in nc or nc in key:
                return c

    return None


def _detect_columns(df):

    return {
        "disease": _find_column(
            df,
            [
                "Disease",
                "Disease Name",
                "DiseaseName",
                "Diagnosis",
                "Disease/Condition",
            ],
        ),

        "ward": _find_column(
            df,
            [
                "Ward",
                "Ward Name",
                "WardName",
                "BMC Ward",
                "Administrative Ward",
            ],
        ),

        "facility": _find_column(
            df,
            [
                "Facility",
                "Facility Name",
                "FacilityName",
                "Health Facility",
            ],
        ),

        "lat": _find_column(
            df,
            [
                "Address Latitude",
                "Address Lat",
                "Latitude",
                "Lat",
            ],
        ),

        "lon": _find_column(
            df,
            [
                "Address Longitude",
                "Address Long",
                "Longitude",
                "Lon",
                "Lng",
            ],
        ),

        "address": _find_column(
            df,
            [
                "Address",
                "Patient Address",
                "PatientAddress",
                "Residential Address",
                "Residence",
            ],
        ),

        "area": _find_column(
            df,
            [
                "Area",
                "Area Name",
                "Locality",
                "Locality Name",
            ],
        ),

        "date": _find_column(
            df,
            [
                "Date",
                "Date of Reporting",
                "Reporting Date",
                "Case Date",
                "Registration Date",
                "Month",
            ],
        ),
    }


# ============================================================
# GLOBAL LABEL TOGGLE
# ============================================================

def _get_show_labels():

    keys = [
        "show_data_labels",
        "show_labels",
        "global_show_data_labels",
        "🏷️ Show Data Labels",
    ]

    for key in keys:

        if key in st.session_state:
            return bool(st.session_state[key])

    return False


# ============================================================
# LOAD BMC WARDS
# ============================================================

@st.cache_data(show_spinner=False)
def load_bmc_wards():

    if not GEOPANDAS_AVAILABLE:
        return None

    geojson_path = None

    for path in WARD_GEOJSON_PATHS:

        if os.path.exists(path):
            geojson_path = path
            break

    if geojson_path is None:
        return None

    try:

        gdf = gpd.read_file(
            geojson_path
        )

        if gdf.empty:
            return None

        # Standard web map projection
        if gdf.crs is not None:
            try:
                gdf = gdf.to_crs(
                    epsg=4326
                )
            except Exception:
                pass

        return gdf

    except Exception:
        return None


# ============================================================
# FIND WARD NAME COLUMN IN GEOJSON
# ============================================================

def _detect_geojson_ward_column(gdf):

    candidates = [
        "NAME",
        "Ward",
        "WARD",
        "WARD_NAME",
        "WARDNAME",
        "WardName",
        "Name",
        "name",
        "ward_name",
        "admin_ward",
    ]

    return _find_column(
        gdf,
        candidates,
    )


# ============================================================
# STANDARDIZE WARD VALUES
# ============================================================

def _standardize_ward(value):

    if pd.isna(value):
        return ""

    value = str(value).strip().upper()

    value = value.replace(
        "WARD",
        "",
    )

    value = value.replace(
        "BMC",
        "",
    )

    value = re.sub(
        r"[^A-Z0-9]+",
        "",
        value,
    )

    return value


# ============================================================
# PREPARE DATA
# ============================================================

def _prepare_data(df, selected_disease=None):

    if df is None or df.empty:
        return df, _detect_columns(df)

    cols = _detect_columns(df)

    work = df.copy()

    if (
        selected_disease
        and cols["disease"]
    ):

        work = work[
            work[cols["disease"]]
            .astype(str)
            .str.strip()
            == str(selected_disease).strip()
        ].copy()

    # Coordinates
    if (
        cols["lat"]
        and cols["lon"]
    ):

        work["_lat"] = pd.to_numeric(
            work[cols["lat"]],
            errors="coerce",
        )

        work["_lon"] = pd.to_numeric(
            work[cols["lon"]],
            errors="coerce",
        )

        work = work[
            work["_lat"].between(
                17.0,
                20.5,
            )
            &
            work["_lon"].between(
                70.0,
                74.5,
            )
        ].copy()

    return work, cols


# ============================================================
# WARD CASE SUMMARY
# ============================================================

def _ward_summary(
    df,
    ward_col,
):

    if (
        df is None
        or df.empty
        or ward_col is None
    ):
        return pd.DataFrame()

    summary = (
        df.groupby(
            ward_col,
            dropna=False,
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    summary["Ward_Key"] = (
        summary[ward_col]
        .apply(_standardize_ward)
    )

    return summary


# ============================================================
# MERGE CASES WITH WARD POLYGONS
# ============================================================

def _merge_ward_data(
    wards_gdf,
    summary,
):

    if (
        wards_gdf is None
        or wards_gdf.empty
        or summary.empty
    ):
        return None

    geo_col = _detect_geojson_ward_column(
        wards_gdf
    )

    if geo_col is None:
        return None

    geo = wards_gdf.copy()

    geo["Ward_Key"] = (
        geo[geo_col]
        .apply(_standardize_ward)
    )

    merged = geo.merge(
        summary[
            [
                "Ward_Key",
                "Cases",
            ]
        ],
        on="Ward_Key",
        how="left",
    )

    merged["Cases"] = (
        merged["Cases"]
        .fillna(0)
        .astype(int)
    )

    return merged


# ============================================================
# CHOROPLETH COLOR
# ============================================================

def _case_color(cases, maximum):

    if maximum <= 0:
        return [230, 230, 230, 120]

    ratio = min(
        float(cases) / float(maximum),
        1.0,
    )

    # Sequential red intensity
    r = 255
    g = int(
        235 - 180 * ratio
    )
    b = int(
        235 - 180 * ratio
    )

    return [
        r,
        max(g, 50),
        max(b, 50),
        170,
    ]


# ============================================================
# GEOJSON MAP
# ============================================================

def _build_ward_map(
    merged_gdf,
    show_labels=False,
):

    if not PYDECK_AVAILABLE:
        st.error(
            "PyDeck is not installed."
        )
        return

    if merged_gdf is None or merged_gdf.empty:
        st.info(
            "Ward boundary data could not be prepared."
        )
        return

    max_cases = int(
        merged_gdf["Cases"].max()
    )

    features = []

    for _, row in merged_gdf.iterrows():

        geometry = row.geometry.__geo_interface__

        properties = {
            "Ward": str(
                row.get(
                    _detect_geojson_ward_column(
                        merged_gdf
                    ),
                    "",
                )
            ),

            "Cases": int(
                row["Cases"]
            ),
        }

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": properties,
            }
        )

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        pickable=True,
        stroked=True,
        filled=True,
        auto_highlight=True,
        get_fill_color=(
            "[255, max(50, 235 - properties.Cases * 180 / "
            f"{max(max_cases, 1)}), "
            "max(50, 235 - properties.Cases * 180 / "
            f"{max(max_cases, 1)}), 170]"
        ),
        get_line_color=[
            70,
            70,
            70,
            220,
        ],
        line_width_min_pixels=1,
    )

    layers = [layer]

    if show_labels:

        # Use polygon centroids
        label_records = []

        for _, row in merged_gdf.iterrows():

            try:

                centroid = row.geometry.centroid

                label_records.append(
                    {
                        "longitude": centroid.x,
                        "latitude": centroid.y,
                        "text": (
                            f"{row.get(_detect_geojson_ward_column(merged_gdf), '')}"
                            f"\n{int(row['Cases'])}"
                        ),
                    }
                )

            except Exception:
                pass

        if label_records:

            label_layer = pdk.Layer(
                "TextLayer",
                data=label_records,
                get_position=[
                    "longitude",
                    "latitude",
                ],
                get_text="text",
                get_size=13,
                get_color=[
                    0,
                    0,
                    0,
                    255,
                ],
                get_text_anchor="'middle'",
                get_alignment_baseline="'center'",
                billboard=True,
            )

            layers.append(
                label_layer
            )

    # Calculate center
    try:

        centroid = merged_gdf.geometry.unary_union.centroid

        center_lon = centroid.x
        center_lat = centroid.y

    except Exception:

        center_lon = 72.8777
        center_lat = 19.0760

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=10.3,
            pitch=0,
            bearing=0,
        ),
        tooltip={
            "html": """
            <b>Ward:</b> {Ward}<br/>
            <b>Cases:</b> {Cases}
            """,
            "style": {
                "backgroundColor": "white",
                "color": "black",
            },
        },
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
    )


# ============================================================
# HOTSPOT CLUSTERS
# ============================================================

def _create_hotspots(
    df,
    cluster_size=500,
):

    if (
        df is None
        or df.empty
        or "_lat" not in df.columns
        or "_lon" not in df.columns
    ):
        return pd.DataFrame()

    work = df.copy()

    lat_degree = (
        cluster_size / 111000.0
    )

    mean_lat = (
        work["_lat"].mean()
    )

    lon_degree = cluster_size / (
        111000.0
        *
        max(
            np.cos(
                np.radians(
                    mean_lat
                )
            ),
            0.1,
        )
    )

    work["_gx"] = np.floor(
        work["_lat"]
        / lat_degree
    ).astype(int)

    work["_gy"] = np.floor(
        work["_lon"]
        / lon_degree
    ).astype(int)

    work["Cluster ID"] = (
        work["_gx"].astype(str)
        + "_"
        + work["_gy"].astype(str)
    )

    summary = (
        work.groupby(
            "Cluster ID"
        )
        .agg(
            Cases=("Cluster ID", "size"),
            Latitude=("_lat", "mean"),
            Longitude=("_lon", "mean"),
        )
        .reset_index()
    )

    return summary


# ============================================================
# OVERLAY MAP
# ============================================================

def _build_combined_map(
    merged_gdf,
    hotspot_df,
    show_labels=False,
):

    if not PYDECK_AVAILABLE:
        st.error(
            "PyDeck is not installed."
        )
        return

    layers = []

    # --------------------------------------------------------
    # Ward polygons
    # --------------------------------------------------------

    if (
        merged_gdf is not None
        and not merged_gdf.empty
    ):

        max_cases = max(
            int(
                merged_gdf["Cases"].max()
            ),
            1,
        )

        geo_col = _detect_geojson_ward_column(
            merged_gdf
        )

        features = []

        for _, row in merged_gdf.iterrows():

            try:

                features.append(
                    {
                        "type": "Feature",
                        "geometry": row.geometry.__geo_interface__,
                        "properties": {
                            "Ward": str(
                                row[geo_col]
                            ),
                            "Cases": int(
                                row["Cases"]
                            ),
                        },
                    }
                )

            except Exception:
                continue

        geojson = {
            "type": "FeatureCollection",
            "features": features,
        }

        ward_layer = pdk.Layer(
            "GeoJsonLayer",
            data=geojson,
            pickable=True,
            stroked=True,
            filled=True,
            auto_highlight=True,
            opacity=0.45,
            get_fill_color=(
                "[255, max(70, 235 - properties.Cases * 165 / "
                f"{max_cases}), "
                "max(70, 235 - properties.Cases * 165 / "
                f"{max_cases}), 120]"
            ),
            get_line_color=[
                50,
                50,
                50,
                230,
            ],
            line_width_min_pixels=1,
        )

        layers.append(
            ward_layer
        )

    # --------------------------------------------------------
    # Hotspot layer
    # --------------------------------------------------------

    if (
        hotspot_df is not None
        and not hotspot_df.empty
    ):

        hotspot_layer = pdk.Layer(
            "ScatterplotLayer",
            data=hotspot_df,
            get_position=[
                "Longitude",
                "Latitude",
            ],
            get_radius="Cases * 40",
            radius_min_pixels=8,
            radius_max_pixels=40,
            filled=True,
            stroked=True,
            pickable=True,
            opacity=0.75,
            get_fill_color=[
                220,
                40,
                40,
                190,
            ],
            get_line_color=[
                80,
                20,
                20,
                255,
            ],
        )

        layers.append(
            hotspot_layer
        )

        if show_labels:

            label_layer = pdk.Layer(
                "TextLayer",
                data=hotspot_df,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_text="Cases",
                get_size=14,
                get_color=[
                    0,
                    0,
                    0,
                    255,
                ],
                billboard=True,
            )

            layers.append(
                label_layer
            )

    # --------------------------------------------------------
    # Center
    # --------------------------------------------------------

    if (
        hotspot_df is not None
        and not hotspot_df.empty
    ):

        center_lat = float(
            hotspot_df["Latitude"].mean()
        )

        center_lon = float(
            hotspot_df["Longitude"].mean()
        )

    else:

        center_lat = 19.0760
        center_lon = 72.8777

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=10.2,
            pitch=0,
            bearing=0,
        ),
        tooltip={
            "html": """
            <b>Ward:</b> {Ward}<br/>
            <b>Cases:</b> {Cases}
            """,
            "style": {
                "backgroundColor": "white",
                "color": "black",
            },
        },
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
    )


# ============================================================
# MAIN PAGE
# ============================================================

def render_geographic_map(
    df,
    selected_disease=None,
):

    st.markdown(
        "# 🗺️ Geographic Disease Mapping"
    )

    st.caption(
        "Mumbai ward-wise choropleth and patient-address hotspot analysis"
    )

    if df is None or df.empty:

        st.info(
            "No data available for geographic analysis."
        )

        return

    if not GEOPANDAS_AVAILABLE:

        st.error(
            "GeoPandas is required for the Mumbai ward boundary map."
        )

        st.info(
            "Please add geopandas to requirements.txt."
        )

        return

    if not PYDECK_AVAILABLE:

        st.error(
            "PyDeck is required for the geographic dashboard."
        )

        st.info(
            "Please add pydeck to requirements.txt."
        )

        return

    cols = _detect_columns(
        df
    )

    # --------------------------------------------------------
    # Disease selection
    # --------------------------------------------------------

    working = df.copy()

    disease_options = []

    if cols["disease"]:

        disease_options = sorted(
            working[
                cols["disease"]
            ]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

    # If multiple diseases selected globally,
    # user can select one to display.
    if len(disease_options) > 1:

        default_index = 0

        if (
            selected_disease
            and selected_disease in disease_options
        ):

            default_index = (
                disease_options.index(
                    selected_disease
                )
            )

        selected_map_disease = st.selectbox(
            "🦠 Select Disease to Display on Map",
            disease_options,
            index=default_index,
            key="geographic_map_disease",
        )

        working = working[
            working[cols["disease"]]
            .astype(str)
            .str.strip()
            == selected_map_disease
        ].copy()

    elif len(disease_options) == 1:

        selected_map_disease = disease_options[0]

        st.info(
            f"Disease displayed on map: {selected_map_disease}"
        )

        working = working[
            working[cols["disease"]]
            .astype(str)
            .str.strip()
            == selected_map_disease
        ].copy()

    else:

        selected_map_disease = (
            selected_disease
            or "All Diseases"
        )

    # --------------------------------------------------------
    # Load ward boundaries
    # --------------------------------------------------------

    wards = load_bmc_wards()

    if wards is None:

        st.error(
            "Mumbai BMC ward boundary GeoJSON was not found."
        )

        st.markdown(
            """
            Please place the Mumbai BMC ward GeoJSON file here:

            `data/BMC_Wards.geojson`
            """
        )

        st.info(
            "The map cannot create the ward choropleth until the boundary file is available."
        )

        return

    # --------------------------------------------------------
    # Ward summary
    # --------------------------------------------------------

    ward_summary = _ward_summary(
        working,
        cols["ward"],
    )

    merged = _merge_ward_data(
        wards,
        ward_summary,
    )

    # --------------------------------------------------------
    # Tabs
    # --------------------------------------------------------

    tab1, tab2, tab3 = st.tabs(
        [
            "🔥 Hotspot Map",
            "🎨 Ward Choropleth",
            "🗺️ Ward + Hotspots",
        ]
    )

    # --------------------------------------------------------
    # TAB 1
    # --------------------------------------------------------

    with tab1:

        st.markdown(
            "### 🔥 Geographic Hotspot Map"
        )

        if (
            cols["lat"] is None
            or cols["lon"] is None
        ):

            st.warning(
                "Address Latitude / Address Longitude columns are not available."
            )

        else:

            if "_lat" not in working.columns:

                working["_lat"] = pd.to_numeric(
                    working[cols["lat"]],
                    errors="coerce",
                )

                working["_lon"] = pd.to_numeric(
                    working[cols["lon"]],
                    errors="coerce",
                )

            working = working[
                working["_lat"].between(
                    17.0,
                    20.5,
                )
                &
                working["_lon"].between(
                    70.0,
                    74.5,
                )
            ].copy()

            cluster_size = st.select_slider(
                "Hotspot Cluster Size",
                options=[
                    200,
                    500,
                    1000,
                    1500,
                ],
                value=500,
                format_func=lambda x:
                    f"{x} metres",
                key="geographic_cluster_size",
            )

            hotspots = _create_hotspots(
                working,
                cluster_size,
            )

            if hotspots.empty:

                st.info(
                    "No valid geographic hotspot records are available."
                )

            else:

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Mapped Cases",
                    f"{len(working):,}",
                )

                c2.metric(
                    "Hotspot Clusters",
                    f"{len(hotspots):,}",
                )

                c3.metric(
                    "Highest Cluster",
                    f"{int(hotspots['Cases'].max()):,}",
                )

                # Hotspot map
                hotspot_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=hotspots,
                    get_position=[
                        "Longitude",
                        "Latitude",
                    ],
                    get_radius="Cases * 40",
                    radius_min_pixels=8,
                    radius_max_pixels=45,
                    filled=True,
                    stroked=True,
                    pickable=True,
                    opacity=0.70,
                    get_fill_color=[
                        220,
                        40,
                        40,
                        180,
                    ],
                    get_line_color=[
                        80,
                        20,
                        20,
                        255,
                    ],
                )

                layers = [
                    hotspot_layer
                ]

                if _get_show_labels():

                    labels = pdk.Layer(
                        "TextLayer",
                        data=hotspots,
                        get_position=[
                            "Longitude",
                            "Latitude",
                        ],
                        get_text="Cases",
                        get_size=14,
                        get_color=[
                            0,
                            0,
                            0,
                            255,
                        ],
                        billboard=True,
                    )

                    layers.append(
                        labels
                    )

                deck = pdk.Deck(
                    layers=layers,
                    initial_view_state=pdk.ViewState(
                        latitude=float(
                            hotspots[
                                "Latitude"
                            ].mean()
                        ),
                        longitude=float(
                            hotspots[
                                "Longitude"
                            ].mean()
                        ),
                        zoom=10.3,
                    ),
                    tooltip={
                        "html": """
                        <b>Cluster:</b> {Cluster ID}<br/>
                        <b>Cases:</b> {Cases}<br/>
                        <b>Latitude:</b> {Latitude}<br/>
                        <b>Longitude:</b> {Longitude}
                        """,
                    },
                )

                st.pydeck_chart(
                    deck,
                    use_container_width=True,
                )

                st.markdown(
                    "#### 🔥 Top Hotspot Clusters"
                )

                st.dataframe(
                    hotspots.sort_values(
                        "Cases",
                        ascending=False,
                    ).head(25),
                    use_container_width=True,
                )

                # Download
                csv = hotspots.to_csv(
                    index=False
                ).encode("utf-8")

                st.download_button(
                    "📄 Download Hotspot Data",
                    data=csv,
                    file_name=(
                        "mumbai_geographic_hotspots.csv"
                    ),
                    mime="text/csv",
                )

    # --------------------------------------------------------
    # TAB 2
    # --------------------------------------------------------

    with tab2:

        st.markdown(
            "### 🎨 Mumbai BMC Ward-wise Choropleth"
        )

        if merged is None:

            st.warning(
                "Ward field in the programme data could not be matched with the BMC ward boundary dataset."
            )

        else:

            _build_ward_map(
                merged,
                show_labels=_get_show_labels(),
            )

            st.markdown(
                "#### Ward-wise Case Summary"
            )

            ward_display = (
                ward_summary
                .sort_values(
                    "Cases",
                    ascending=False,
                )
                .reset_index(drop=True)
            )

            ward_display.index = (
                ward_display.index + 1
            )

            st.dataframe(
                ward_display,
                use_container_width=True,
            )

            # Excel
            buffer = io.BytesIO()

            try:

                with pd.ExcelWriter(
                    buffer,
                    engine="openpyxl",
                ) as writer:

                    ward_display.to_excel(
                        writer,
                        index=False,
                        sheet_name="Ward Summary",
                    )

                buffer.seek(0)

                st.download_button(
                    "📊 Download Ward-wise Excel",
                    data=buffer.getvalue(),
                    file_name=(
                        "mumbai_ward_case_summary.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                )

            except Exception as e:

                st.warning(
                    f"Excel export unavailable: {e}"
                )

    # --------------------------------------------------------
    # TAB 3
    # --------------------------------------------------------

    with tab3:

        st.markdown(
            "### 🗺️ Ward Boundary + Geographic Hotspots"
        )

        if (
            cols["lat"] is None
            or cols["lon"] is None
        ):

            st.warning(
                "Address coordinates are required for hotspot overlay."
            )

        else:

            if "_lat" not in working.columns:

                working["_lat"] = pd.to_numeric(
                    working[cols["lat"]],
                    errors="coerce",
                )

                working["_lon"] = pd.to_numeric(
                    working[cols["lon"]],
                    errors="coerce",
                )

            working = working[
                working["_lat"].between(
                    17.0,
                    20.5,
                )
                &
                working["_lon"].between(
                    70.0,
                    74.5,
                )
            ].copy()

            cluster_size = st.select_slider(
                "Overlay Cluster Size",
                options=[
                    200,
                    500,
                    1000,
                    1500,
                ],
                value=500,
                format_func=lambda x:
                    f"{x} metres",
                key="combined_cluster_size",
            )

            hotspots = _create_hotspots(
                working,
                cluster_size,
            )

            if merged is None:

                st.warning(
                    "Ward boundaries could not be matched with your ward data."
                )

            else:

                _build_combined_map(
                    merged,
                    hotspots,
                    show_labels=_get_show_labels(),
                )

                st.markdown(
                    "### 📊 Management Interpretation"
                )

                st.write(
                    "The shaded polygons represent ward-level case burden. "
                    "The circular markers represent geographic clusters based "
                    "on patient/address coordinates."
                )

                st.info(
                    "For programme management, this view helps identify whether "
                    "geographic clusters are concentrated within particular BMC wards."
                )

    # --------------------------------------------------------
    # DATA QUALITY NOTE
    # --------------------------------------------------------

    st.divider()

    st.markdown(
        "### ℹ️ Geographic Data Quality"
    )

    if cols["lat"] and cols["lon"]:

        total = len(
            df
        )

        valid = 0

        lat = pd.to_numeric(
            df[cols["lat"]],
            errors="coerce",
        )

        lon = pd.to_numeric(
            df[cols["lon"]],
            errors="coerce",
        )

        valid = (
            lat.between(
                17.0,
                20.5,
            )
            &
            lon.between(
                70.0,
                74.5,
            )
        ).sum()

        c1, c2 = st.columns(2)

        c1.metric(
            "Total Records",
            f"{total:,}",
        )

        c2.metric(
            "Valid Mumbai-area Coordinates",
            f"{int(valid):,}",
        )

        st.caption(
            "Records with missing or invalid address coordinates are excluded from geographic hotspot mapping."
        )
