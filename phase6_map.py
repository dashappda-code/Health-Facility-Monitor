# phase6_map.py

import io
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import requests


# ============================================================
# OPTIONAL MAP LIBRARY
# ============================================================

try:
    import pydeck as pdk

    PYDECK_AVAILABLE = True
except Exception:
    PYDECK_AVAILABLE = False


# ============================================================
# OPTIONAL PDF / STATIC MAP LIBRARIES
# ============================================================

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import Polygon as MplPolygon

    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False


# ============================================================
# CONFIGURATION
# ============================================================

BMC_WARD_URL = (
    "https://services8.arcgis.com/r6MmJtuWAzMawmJ8/arcgis/rest/services/"
    "BMConMaps_Nov26gdb/FeatureServer/24/query"
)

BMC_WARD_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "f": "geojson",
}

BMC_MAP_STYLE = (
    "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
)


# ============================================================
# COLUMN HELPERS
# ============================================================

def _norm_col(x):
    return re.sub(r"[^a-z0-9]+", "", str(x).lower())


def _find_column(df, candidates):
    if df is None or df.empty:
        return None

    normalized = {_norm_col(c): c for c in df.columns}

    for candidate in candidates:
        key = _norm_col(candidate)

        if key in normalized:
            return normalized[key]

    # Partial matching
    for candidate in candidates:
        key = _norm_col(candidate)

        for norm_name, original_name in normalized.items():
            if key and (key in norm_name or norm_name in key):
                return original_name

    return None


def _detect_columns(df):

    disease_col = _find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "DiseaseName",
            "Diagnosis",
            "Disease/Condition",
            "Disease Condition",
        ],
    )

    ward_col = _find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "WardName",
            "BMC Ward",
            "Administrative Ward",
        ],
    )

    facility_col = _find_column(
        df,
        [
            "Facility",
            "Facility Name",
            "FacilityName",
            "Health Facility",
            "Institution",
        ],
    )

    lat_col = _find_column(
        df,
        [
            "Address Latitude",
            "Address Lat",
            "Latitude",
            "Lat",
        ],
    )

    lon_col = _find_column(
        df,
        [
            "Address Longitude",
            "Address Long",
            "Longitude",
            "Lon",
            "Lng",
        ],
    )

    address_col = _find_column(
        df,
        [
            "Address",
            "Patient Address",
            "PatientAddress",
            "Residential Address",
            "Residence",
            "Location",
        ],
    )

    date_col = _find_column(
        df,
        [
            "Date",
            "Date of Reporting",
            "Reporting Date",
            "Case Date",
            "Registration Date",
            "Month",
        ],
    )

    area_col = _find_column(
        df,
        [
            "Area",
            "Area Name",
            "Locality",
            "Locality Name",
            "Location Area",
        ],
    )

    return {
        "disease": disease_col,
        "ward": ward_col,
        "facility": facility_col,
        "lat": lat_col,
        "lon": lon_col,
        "address": address_col,
        "date": date_col,
        "area": area_col,
    }


# ============================================================
# GLOBAL LABEL STATE
# ============================================================

def _get_show_labels():

    possible_keys = [
        "show_data_labels",
        "show_labels",
        "global_show_data_labels",
        "🏷️ Show Data Labels",
    ]

    for key in possible_keys:
        if key in st.session_state:
            try:
                return bool(st.session_state[key])
            except Exception:
                pass

    return False


# ============================================================
# COORDINATE CLEANING
# ============================================================

def _clean_coordinates(df, lat_col, lon_col):

    if df is None or df.empty:
        return pd.DataFrame()

    if not lat_col or not lon_col:
        return pd.DataFrame()

    work = df.copy()

    work[lat_col] = pd.to_numeric(
        work[lat_col],
        errors="coerce",
    )

    work[lon_col] = pd.to_numeric(
        work[lon_col],
        errors="coerce",
    )

    work = work.dropna(
        subset=[lat_col, lon_col]
    ).copy()

    work = work[
        work[lat_col].between(-90, 90)
        & work[lon_col].between(-180, 180)
    ].copy()

    # Mumbai-region sanity check
    work = work[
        work[lat_col].between(17.0, 20.5)
        & work[lon_col].between(70.0, 74.5)
    ].copy()

    return work


# ============================================================
# CLUSTER CREATION
# ============================================================

def _create_clusters(
    df,
    lat_col,
    lon_col,
    cluster_size_m=500,
    columns=None,
):

    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    metres_per_degree_lat = 111_000

    lat_reference = work[lat_col].mean()

    metres_per_degree_lon = (
        111_000
        * max(
            math.cos(
                math.radians(float(lat_reference))
            ),
            0.1,
        )
    )

    lat_step = cluster_size_m / metres_per_degree_lat
    lon_step = cluster_size_m / metres_per_degree_lon

    work["_grid_lat"] = (
        np.floor(
            work[lat_col] / lat_step
        )
        * lat_step
    )

    work["_grid_lon"] = (
        np.floor(
            work[lon_col] / lon_step
        )
        * lon_step
    )

    work["Cluster_ID"] = (
        "C_"
        + work["_grid_lat"]
        .round(5)
        .astype(str)
        + "_"
        + work["_grid_lon"]
        .round(5)
        .astype(str)
    )

    grouped = (
        work.groupby("Cluster_ID", dropna=False)
        .agg(
            Cluster_Cases=(lat_col, "size"),
            Cluster_Latitude=(lat_col, "mean"),
            Cluster_Longitude=(lon_col, "mean"),
        )
        .reset_index()
    )

    work = work.merge(
        grouped,
        on="Cluster_ID",
        how="left",
    )

    # --------------------------------------------------------
    # Cluster-level ward
    # --------------------------------------------------------

    if columns and columns.get("ward"):

        ward_col = columns["ward"]

        def _primary_value(series):

            values = (
                series.dropna()
                .astype(str)
                .str.strip()
            )

            values = values[values != ""]

            if values.empty:
                return "Not Available"

            return values.value_counts().index[0]

        ward_summary = (
            work.groupby("Cluster_ID")[ward_col]
            .apply(_primary_value)
            .rename("Cluster_Ward")
            .reset_index()
        )

        work = work.merge(
            ward_summary,
            on="Cluster_ID",
            how="left",
        )

    else:

        work["Cluster_Ward"] = "Not Available"

    # --------------------------------------------------------
    # Cluster-level facility
    # --------------------------------------------------------

    if columns and columns.get("facility"):

        facility_col = columns["facility"]

        def _primary_facility(series):

            values = (
                series.dropna()
                .astype(str)
                .str.strip()
            )

            values = values[values != ""]

            if values.empty:
                return "Not Available"

            return values.value_counts().index[0]

        facility_summary = (
            work.groupby("Cluster_ID")[facility_col]
            .apply(_primary_facility)
            .rename("Cluster_Facility")
            .reset_index()
        )

        work = work.merge(
            facility_summary,
            on="Cluster_ID",
            how="left",
        )

    else:

        work["Cluster_Facility"] = "Not Available"

    # --------------------------------------------------------
    # Cluster-level disease
    # --------------------------------------------------------

    if columns and columns.get("disease"):

        disease_col = columns["disease"]

        def _primary_disease(series):

            values = (
                series.dropna()
                .astype(str)
                .str.strip()
            )

            values = values[values != ""]

            if values.empty:
                return "Not Available"

            return values.value_counts().index[0]

        disease_summary = (
            work.groupby("Cluster_ID")[disease_col]
            .apply(_primary_disease)
            .rename("Cluster_Disease")
            .reset_index()
        )

        work = work.merge(
            disease_summary,
            on="Cluster_ID",
            how="left",
        )

    else:

        work["Cluster_Disease"] = "All Diseases"

    return work


# ============================================================
# HOTSPOT CLASSIFICATION
# ============================================================

def _classify_hotspots(cluster_df):

    if cluster_df is None or cluster_df.empty:
        return cluster_df

    work = cluster_df.copy()

    if "Cluster_Cases" not in work.columns:
        return work

    values = pd.to_numeric(
        work["Cluster_Cases"],
        errors="coerce",
    ).dropna()

    if values.empty:
        work["Hotspot_Classification"] = "Low"
        return work

    if len(values) == 1:

        work["Hotspot_Classification"] = "High"

        return work

    q25 = values.quantile(0.25)
    q50 = values.quantile(0.50)
    q75 = values.quantile(0.75)

    def classify(value):

        if pd.isna(value):
            return "Low"

        if value >= q75:
            return "Very High"

        if value >= q50:
            return "High"

        if value >= q25:
            return "Moderate"

        return "Low"

    work["Hotspot_Classification"] = (
        work["Cluster_Cases"]
        .apply(classify)
    )

    return work


# ============================================================
# BMC WARD GEOJSON
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def _load_bmc_wards():

    try:

        response = requests.get(
            BMC_WARD_URL,
            params=BMC_WARD_PARAMS,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        if (
            not isinstance(data, dict)
            or data.get("type") != "FeatureCollection"
        ):
            return None

        return data

    except Exception:

        return None


# ============================================================
# GEOJSON HELPERS
# ============================================================

def _iter_geojson_positions(geometry):

    if not geometry:
        return

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if not coordinates:
        return

    if geometry_type == "Polygon":

        for ring in coordinates:

            yield ring

    elif geometry_type == "MultiPolygon":

        for polygon in coordinates:

            for ring in polygon:

                yield ring


def _geojson_bounds(geojson):

    if not geojson:
        return None

    lats = []
    lons = []

    for feature in geojson.get("features", []):

        geometry = feature.get("geometry")

        if not geometry:
            continue

        for ring in _iter_geojson_positions(
            geometry
        ):

            for point in ring:

                if len(point) >= 2:

                    lon = point[0]
                    lat = point[1]

                    try:
                        lons.append(float(lon))
                        lats.append(float(lat))
                    except Exception:
                        pass

    if not lats or not lons:
        return None

    return (
        min(lons),
        min(lats),
        max(lons),
        max(lats),
    )


# ============================================================
# PYDECK MAP
# ============================================================

def _build_map(
    cluster_df,
    show_labels=False,
    ward_geojson=None,
    map_view="Overall",
):

    if not PYDECK_AVAILABLE:
        return None

    if cluster_df is None or cluster_df.empty:
        return None

    plot_df = cluster_df.copy()

    plot_df["Cases"] = pd.to_numeric(
        plot_df["Cluster_Cases"],
        errors="coerce",
    ).fillna(0)

    # --------------------------------------------------------
    # Hotspot colours
    # --------------------------------------------------------

    hotspot_colors = {
        "Very High": [255, 0, 0, 200],
        "High": [255, 110, 0, 190],
        "Moderate": [255, 200, 0, 175],
        "Low": [80, 160, 255, 155],
    }

    plot_df["Color"] = (
        plot_df["Hotspot_Classification"]
        .map(hotspot_colors)
        .apply(
            lambda x: x
            if isinstance(x, list)
            else [80, 160, 255, 155]
        )
    )

    # --------------------------------------------------------
    # Map layers
    # --------------------------------------------------------

    layers = []

    if (
        ward_geojson
        and map_view != "Top Hotspots"
    ):

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=ward_geojson,
                pickable=False,
                stroked=True,
                filled=False,
                line_width_min_pixels=1,
                get_line_color=[
                    220,
                    220,
                    220,
                    190,
                ],
            )
        )

    # --------------------------------------------------------
    # Radius
    # --------------------------------------------------------

    plot_df["Map_Radius"] = (
        np.sqrt(
            np.maximum(
                plot_df["Cases"],
                1,
            )
        )
        * 80
    )

    plot_df["Map_Radius"] = plot_df[
        "Map_Radius"
    ].clip(
        lower=30,
        upper=1400,
    )

    # --------------------------------------------------------
    # Hotspot layer
    # --------------------------------------------------------

    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=plot_df,
            get_position=[
                "Cluster_Longitude",
                "Cluster_Latitude",
            ],
            get_radius="Map_Radius",
            get_fill_color="Color",
            get_line_color=[
                255,
                255,
                255,
                160,
            ],
            line_width_min_pixels=1,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
        )
    )

    # --------------------------------------------------------
    # Labels
    # --------------------------------------------------------

    if show_labels:

        label_df = plot_df.copy()

        label_df["Label"] = (
            label_df["Cases"]
            .astype(int)
            .astype(str)
            + " cases"
        )

        layers.append(
            pdk.Layer(
                "TextLayer",
                data=label_df,
                get_position=[
                    "Cluster_Longitude",
                    "Cluster_Latitude",
                ],
                get_text="Label",
                get_size=14,
                get_color=[
                    255,
                    255,
                    255,
                    255,
                ],
                get_alignment_baseline="bottom",
                get_pixel_offset=[
                    0,
                    -10,
                ],
            )
        )

    # --------------------------------------------------------
    # View state
    # --------------------------------------------------------

    bounds = _geojson_bounds(
        ward_geojson
    )

    if bounds:

        min_lon, min_lat, max_lon, max_lat = bounds

        center_lon = (
            min_lon + max_lon
        ) / 2

        center_lat = (
            min_lat + max_lat
        ) / 2

        view_state = pdk.ViewState(
            longitude=center_lon,
            latitude=center_lat,
            zoom=10.4,
            pitch=0,
            bearing=0,
        )

    else:

        center_lat = plot_df[
            "Cluster_Latitude"
        ].mean()

        center_lon = plot_df[
            "Cluster_Longitude"
        ].mean()

        view_state = pdk.ViewState(
            longitude=float(center_lon),
            latitude=float(center_lat),
            zoom=10.5,
            pitch=0,
            bearing=0,
        )

    tooltip = {
        "html": """
        <div style="font-size:13px;">
            <b>Hotspot:</b> {Hotspot_Classification}<br/>
            <b>Cases:</b> {Cases}<br/>
            <b>Cluster ID:</b> {Cluster_ID}<br/>
            <b>Ward:</b> {Cluster_Ward}<br/>
            <b>Facility:</b> {Cluster_Facility}<br/>
            <b>Disease:</b> {Cluster_Disease}<br/>
            <b>Latitude:</b> {Cluster_Latitude}<br/>
            <b>Longitude:</b> {Cluster_Longitude}
        </div>
        """,
        "style": {
            "backgroundColor": "rgba(0,0,0,0.85)",
            "color": "white",
        },
    }

    deck = pdk.Deck(
        map_style=BMC_MAP_STYLE,
        initial_view_state=view_state,
        layers=layers,
        tooltip=tooltip,
    )

    return deck


# ============================================================
# DOWNLOAD DATA PREPARATION
# ============================================================

def _prepare_download_dataframe(
    df,
    columns,
):

    if df is None or df.empty:
        return pd.DataFrame()

    output = pd.DataFrame()

    mapping = [
        ("Disease", columns.get("disease")),
        ("Date", columns.get("date")),
        ("Ward", columns.get("ward")),
        ("Facility", columns.get("facility")),
        ("Area", columns.get("area")),
        ("Address", columns.get("address")),
        ("Latitude", columns.get("lat")),
        ("Longitude", columns.get("lon")),
    ]

    for output_name, source_name in mapping:

        if source_name and source_name in df.columns:

            output[output_name] = df[
                source_name
            ]

    additional_columns = [
        "Cluster_ID",
        "Cluster_Cases",
        "Hotspot_Classification",
        "Cluster_Ward",
        "Cluster_Facility",
        "Cluster_Disease",
    ]

    for col in additional_columns:

        if col in df.columns:

            output[col] = df[col]

    return output


# ============================================================
# STATIC MAP HELPERS
# ============================================================

def _geometry_to_path(geometry):

    paths = []

    if not geometry:
        return paths

    for ring in _iter_geojson_positions(
        geometry
    ):

        path = []

        for point in ring:

            if len(point) >= 2:

                path.append(
                    (
                        float(point[0]),
                        float(point[1]),
                    )
                )

        if len(path) >= 2:

            paths.append(path)

    return paths


def _add_bmc_boundaries_to_axis(
    ax,
    ward_geojson,
):

    if not ward_geojson:
        return

    for feature in ward_geojson.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry"
        )

        if not geometry:
            continue

        paths = _geometry_to_path(
            geometry
        )

        for path in paths:

            xs = [
                point[0]
                for point in path
            ]

            ys = [
                point[1]
                for point in path
            ]

            ax.plot(
                xs,
                ys,
                linewidth=0.7,
                alpha=0.8,
            )


def _set_static_extent(
    ax,
    cluster_df,
    ward_geojson=None,
):

    bounds = _geojson_bounds(
        ward_geojson
    )

    if bounds:

        min_lon, min_lat, max_lon, max_lat = bounds

    elif (
        cluster_df is not None
        and not cluster_df.empty
    ):

        min_lon = cluster_df[
            "Cluster_Longitude"
        ].min()

        max_lon = cluster_df[
            "Cluster_Longitude"
        ].max()

        min_lat = cluster_df[
            "Cluster_Latitude"
        ].min()

        max_lat = cluster_df[
            "Cluster_Latitude"
        ].max()

    else:

        return

    lon_pad = max(
        (max_lon - min_lon) * 0.05,
        0.01,
    )

    lat_pad = max(
        (max_lat - min_lat) * 0.05,
        0.01,
    )

    ax.set_xlim(
        min_lon - lon_pad,
        max_lon + lon_pad,
    )

    ax.set_ylim(
        min_lat - lat_pad,
        max_lat + lat_pad,
    )


# ============================================================
# STATIC HOTSPOT MAP
# ============================================================

def _create_static_hotspot_map(
    cluster_df,
    disease_name,
    cluster_size_m,
    ward_geojson=None,
    map_view="Overall",
    show_labels=False,
):

    if not MATPLOTLIB_AVAILABLE:
        return None

    if cluster_df is None or cluster_df.empty:
        return None

    work = cluster_df.copy()

    hotspot_colors = {
        "Very High": "red",
        "High": "orange",
        "Moderate": "gold",
        "Low": "cornflowerblue",
    }

    fig, ax = plt.subplots(
        figsize=(14, 10)
    )

    fig.patch.set_facecolor(
        "#101010"
    )

    ax.set_facecolor(
        "#101010"
    )

    # --------------------------------------------------------
    # BMC boundaries
    # --------------------------------------------------------

    if ward_geojson:

        _add_bmc_boundaries_to_axis(
            ax,
            ward_geojson,
        )

    # --------------------------------------------------------
    # Hotspots
    # --------------------------------------------------------

    for _, row in work.iterrows():

        classification = row.get(
            "Hotspot_Classification",
            "Low",
        )

        color = hotspot_colors.get(
            classification,
            "cornflowerblue",
        )

        cases = float(
            row.get(
                "Cluster_Cases",
                0,
            )
        )

        size = (
            math.sqrt(
                max(cases, 1)
            )
            * 55
        )

        ax.scatter(
            row["Cluster_Longitude"],
            row["Cluster_Latitude"],
            s=size,
            c=color,
            alpha=0.70,
            edgecolors="white",
            linewidths=0.5,
        )

        if show_labels:

            label_text = (
                f"{int(cases)} cases"
            )

            ax.annotate(
                label_text,
                (
                    row[
                        "Cluster_Longitude"
                    ],
                    row[
                        "Cluster_Latitude"
                    ],
                ),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color="white",
            )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    disease_text = (
        disease_name
        if disease_name
        else "All Diseases"
    )

    ax.set_title(
        "GEOGRAPHIC HOTSPOT ANALYSIS",
        fontsize=18,
        fontweight="bold",
        color="white",
        pad=16,
    )

    ax.text(
        0.5,
        1.01,
        (
            f"View: {map_view} | "
            f"Disease: {disease_text} | "
            f"Cluster Radius: {cluster_size_m} m"
        ),
        transform=ax.transAxes,
        ha="center",
        fontsize=10,
        color="white",
    )

    # --------------------------------------------------------
    # Legend
    # --------------------------------------------------------

    legend_items = [
        ("BMC Ward Boundary", "white"),
        ("Very High", "red"),
        ("High", "orange"),
        ("Moderate", "gold"),
        ("Low", "cornflowerblue"),
    ]

    for label, color in legend_items:

        if label == "BMC Ward Boundary":

            ax.plot(
                [],
                [],
                color=color,
                linewidth=1,
                label=label,
            )

        else:

            ax.scatter(
                [],
                [],
                s=80,
                c=color,
                label=label,
            )

    legend = ax.legend(
        loc="upper right",
        framealpha=0.85,
    )

    for text_item in legend.get_texts():

        text_item.set_color(
            "white"
        )

    # --------------------------------------------------------
    # Axis
    # --------------------------------------------------------

    ax.tick_params(
        colors="white"
    )

    for spine in ax.spines.values():

        spine.set_color(
            "#777777"
        )

    ax.set_xlabel(
        "Longitude",
        color="white",
    )

    ax.set_ylabel(
        "Latitude",
        color="white",
    )

    _set_static_extent(
        ax,
        work,
        ward_geojson,
    )

    fig.tight_layout()

    return fig


# ============================================================
# DISPLAYED MAP FILE CREATION
# ============================================================

def _create_displayed_map_files(
    cluster_df,
    disease_name,
    cluster_size_m,
    ward_geojson,
    map_view,
    show_labels,
):

    png_bytes = None
    pdf_bytes = None

    fig = _create_static_hotspot_map(
        cluster_df=cluster_df,
        disease_name=disease_name,
        cluster_size_m=cluster_size_m,
        ward_geojson=ward_geojson,
        map_view=map_view,
        show_labels=show_labels,
    )

    if fig is None:
        return None, None

    # --------------------------------------------------------
    # PNG
    # --------------------------------------------------------

    png_buffer = io.BytesIO()

    fig.savefig(
        png_buffer,
        format="png",
        dpi=180,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )

    png_buffer.seek(0)

    png_bytes = png_buffer.getvalue()

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    pdf_buffer = io.BytesIO()

    with PdfPages(pdf_buffer) as pdf:

        pdf.savefig(
            fig,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )

    pdf_buffer.seek(0)

    pdf_bytes = pdf_buffer.getvalue()

    plt.close(fig)

    return (
        png_bytes,
        pdf_bytes,
    )


# ============================================================
# PDF REPORT
# ============================================================

def _create_pdf(
    cluster_df,
    disease_name,
    filter_info,
    map_view,
):

    if not MATPLOTLIB_AVAILABLE:
        return None

    if cluster_df is None or cluster_df.empty:
        return None

    pdf_buffer = io.BytesIO()

    with PdfPages(pdf_buffer) as pdf:

        # ----------------------------------------------------
        # Cover / summary page
        # ----------------------------------------------------

        fig, ax = plt.subplots(
            figsize=(11.69, 8.27)
        )

        ax.axis("off")

        ax.text(
            0.5,
            0.78,
            "GEOGRAPHIC HOTSPOT ANALYSIS",
            ha="center",
            va="center",
            fontsize=22,
            fontweight="bold",
        )

        ax.text(
            0.5,
            0.68,
            f"Map View: {map_view}",
            ha="center",
            fontsize=14,
        )

        ax.text(
            0.5,
            0.62,
            f"Disease: {disease_name or 'All Diseases'}",
            ha="center",
            fontsize=13,
        )

        if filter_info:

            ax.text(
                0.5,
                0.55,
                str(filter_info),
                ha="center",
                fontsize=11,
            )

        total_clusters = len(
            cluster_df
        )

        total_cases = int(
            pd.to_numeric(
                cluster_df[
                    "Cluster_Cases"
                ],
                errors="coerce",
            )
            .fillna(0)
            .sum()
        )

        ax.text(
            0.5,
            0.46,
            f"Geographic Clusters: {total_clusters}",
            ha="center",
            fontsize=12,
        )

        ax.text(
            0.5,
            0.41,
            f"Mapped Cases: {total_cases}",
            ha="center",
            fontsize=12,
        )

        ax.text(
            0.5,
            0.30,
            (
                "Hotspot classification is based on "
                "relative geographic cluster distribution."
            ),
            ha="center",
            fontsize=10,
        )

        pdf.savefig(
            fig,
            bbox_inches="tight",
        )

        plt.close(fig)

        # ----------------------------------------------------
        # Top cluster table
        # ----------------------------------------------------

        summary = (
            cluster_df[
                [
                    "Cluster_ID",
                    "Cluster_Cases",
                    "Hotspot_Classification",
                    "Cluster_Ward",
                    "Cluster_Facility",
                    "Cluster_Latitude",
                    "Cluster_Longitude",
                ]
            ]
            .copy()
            .sort_values(
                "Cluster_Cases",
                ascending=False,
            )
            .head(25)
        )

        summary = summary.rename(
            columns={
                "Cluster_ID": "Cluster ID",
                "Cluster_Cases": "Cases",
                "Hotspot_Classification": "Hotspot",
                "Cluster_Ward": "Ward",
                "Cluster_Facility": "Facility",
                "Cluster_Latitude": "Latitude",
                "Cluster_Longitude": "Longitude",
            }
        )

        fig, ax = plt.subplots(
            figsize=(16, 10)
        )

        ax.axis("off")

        ax.set_title(
            "Top Geographic Hotspots",
            fontsize=16,
            fontweight="bold",
            pad=15,
        )

        table = ax.table(
            cellText=summary.values,
            colLabels=summary.columns,
            loc="center",
            cellLoc="center",
        )

        table.auto_set_font_size(False)

        table.set_fontsize(8)

        table.scale(
            1,
            1.6,
        )

        pdf.savefig(
            fig,
            bbox_inches="tight",
        )

        plt.close(fig)

    pdf_buffer.seek(0)

    return pdf_buffer.getvalue()


# ============================================================
# WARD SUMMARY
# ============================================================

def _create_ward_summary(
    cluster_df,
    columns,
):

    if cluster_df is None or cluster_df.empty:
        return pd.DataFrame()

    ward_col = (
        columns.get("ward")
        if columns
        else None
    )

    if not ward_col or ward_col not in cluster_df.columns:

        if "Cluster_Ward" in cluster_df.columns:

            temp = cluster_df.copy()

            summary = (
                temp.groupby(
                    "Cluster_Ward",
                    dropna=False,
                )
                .agg(
                    Cases=(
                        "Cluster_Cases",
                        "sum",
                    ),
                    Geographic_Clusters=(
                        "Cluster_ID",
                        "nunique",
                    ),
                    Very_High_Hotspots=(
                        "Hotspot_Classification",
                        lambda x: (
                            x == "Very High"
                        ).sum(),
                    ),
                    High_Hotspots=(
                        "Hotspot_Classification",
                        lambda x: (
                            x == "High"
                        ).sum(),
                    ),
                )
                .reset_index()
                .rename(
                    columns={
                        "Cluster_Ward": "Ward"
                    }
                )
            )

            return summary.sort_values(
                "Cases",
                ascending=False,
            )

        return pd.DataFrame()

    temp = cluster_df.copy()

    summary = (
        temp.groupby(
            ward_col,
            dropna=False,
        )
        .agg(
            Cases=(
                "Cluster_Cases",
                "sum",
            ),
            Geographic_Clusters=(
                "Cluster_ID",
                "nunique",
            ),
            Very_High_Hotspots=(
                "Hotspot_Classification",
                lambda x: (
                    x == "Very High"
                ).sum(),
            ),
            High_Hotspots=(
                "Hotspot_Classification",
                lambda x: (
                    x == "High"
                ).sum(),
            ),
        )
        .reset_index()
        .rename(
            columns={
                ward_col: "Ward"
            }
        )
    )

    return summary.sort_values(
        "Cases",
        ascending=False,
    )


# ============================================================
# FACILITY SUMMARY
# ============================================================

def _create_facility_summary(
    cluster_df,
    columns,
):

    if cluster_df is None or cluster_df.empty:
        return pd.DataFrame()

    facility_col = (
        columns.get("facility")
        if columns
        else None
    )

    if not facility_col or facility_col not in cluster_df.columns:

        if "Cluster_Facility" in cluster_df.columns:

            temp = cluster_df.copy()

            summary = (
                temp.groupby(
                    "Cluster_Facility",
                    dropna=False,
                )
                .agg(
                    Cases=(
                        "Cluster_Cases",
                        "sum",
                    ),
                    Geographic_Clusters=(
                        "Cluster_ID",
                        "nunique",
                    ),
                    Very_High_Hotspots=(
                        "Hotspot_Classification",
                        lambda x: (
                            x == "Very High"
                        ).sum(),
                    ),
                    High_Hotspots=(
                        "Hotspot_Classification",
                        lambda x: (
                            x == "High"
                        ).sum(),
                    ),
                )
                .reset_index()
                .rename(
                    columns={
                        "Cluster_Facility": "Facility"
                    }
                )
            )

            return summary.sort_values(
                "Cases",
                ascending=False,
            )

        return pd.DataFrame()

    temp = cluster_df.copy()

    summary = (
        temp.groupby(
            facility_col,
            dropna=False,
        )
        .agg(
            Cases=(
                "Cluster_Cases",
                "sum",
            ),
            Geographic_Clusters=(
                "Cluster_ID",
                "nunique",
            ),
            Very_High_Hotspots=(
                "Hotspot_Classification",
                lambda x: (
                    x == "Very High"
                ).sum(),
            ),
            High_Hotspots=(
                "Hotspot_Classification",
                lambda x: (
                    x == "High"
                ).sum(),
            ),
        )
        .reset_index()
        .rename(
            columns={
                facility_col: "Facility"
            }
        )
    )

    return summary.sort_values(
        "Cases",
        ascending=False,
    )


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_map(
    df,
    selected_disease=None,
    filter_info=None,
):

    st.markdown(
        "## 🗺️ Geographic Hotspot Map"
    )

    st.caption(
        "Patient/address geographic coordinates based hotspot analysis"
    )

    # --------------------------------------------------------
    # Validate data
    # --------------------------------------------------------

    if df is None or df.empty:

        st.warning(
            "No data available for geographic analysis."
        )

        return

    columns = _detect_columns(df)

    lat_col = columns.get("lat")
    lon_col = columns.get("lon")

    if not lat_col or not lon_col:

        st.error(
            "Latitude and Longitude columns were not found in the data."
        )

        return

    # --------------------------------------------------------
    # Disease handling
    # --------------------------------------------------------

    working_df = df.copy()

    disease_col = columns.get(
        "disease"
    )

    disease_options = [
        "All Diseases"
    ]

    if disease_col:

        disease_values = (
            working_df[disease_col]
            .dropna()
            .astype(str)
            .str.strip()
        )

        disease_values = sorted(
            [
                x
                for x in disease_values.unique()
                if x
            ]
        )

        disease_options.extend(
            disease_values
        )

    # Global disease
    global_disease = (
        selected_disease
        if selected_disease
        and str(selected_disease).strip()
        else None
    )

    # --------------------------------------------------------
    # Local disease selector
    # --------------------------------------------------------

    st.markdown(
        "### Map Filters"
    )

    col1, col2, col3 = st.columns(
        [1.4, 1.2, 1.2]
    )

    with col1:

        if global_disease:

            st.info(
                f"Global Disease Selection: {global_disease}"
            )

            local_disease = global_disease

        else:

            current_local = st.session_state.get(
                "phase6_local_disease",
                "All Diseases",
            )

            if (
                current_local
                not in disease_options
            ):
                current_local = "All Diseases"

            local_disease = st.selectbox(
                "Disease",
                disease_options,
                index=disease_options.index(
                    current_local
                ),
                key="phase6_local_disease",
            )

    with col2:

        cluster_size_m = st.select_slider(
            "Cluster Radius",
            options=[
                200,
                500,
                1000,
                1500,
            ],
            value=st.session_state.get(
                "phase6_cluster_size",
                500,
            ),
            format_func=lambda x: (
                f"{x} m"
                if x < 1000
                else f"{x / 1000:g} km"
            ),
            key="phase6_cluster_size",
        )

    with col3:

        default_labels = _get_show_labels()

        show_labels = st.checkbox(
            "🏷️ Show Data Labels",
            value=default_labels,
            key="phase6_map_show_labels",
        )

    # --------------------------------------------------------
    # Map view selector
    # --------------------------------------------------------

    map_view = st.radio(
        "Map View",
        [
            "Overall",
            "Ward-wise",
            "Top Hotspots",
            "BMC Boundary",
        ],
        horizontal=True,
        key="phase6_map_view",
    )

    # --------------------------------------------------------
    # Top N selector
    # --------------------------------------------------------

    top_n = 10

    if map_view == "Top Hotspots":

        top_n = st.select_slider(
            "Number of Top Hotspots",
            options=[
                5,
                10,
                15,
                20,
            ],
            value=st.session_state.get(
                "phase6_top_n",
                10,
            ),
            key="phase6_top_n",
        )

    # --------------------------------------------------------
    # Apply disease filter
    # --------------------------------------------------------

    if (
        local_disease
        and local_disease != "All Diseases"
        and disease_col
    ):

        working_df = working_df[
            working_df[
                disease_col
            ]
            .astype(str)
            .str.strip()
            == str(local_disease).strip()
        ].copy()

    if working_df.empty:

        st.warning(
            "No records available for the selected disease."
        )

        return

    # --------------------------------------------------------
    # Clean coordinates
    # --------------------------------------------------------

    geo_df = _clean_coordinates(
        working_df,
        lat_col,
        lon_col,
    )

    if geo_df.empty:

        st.warning(
            "No valid geographic coordinates are available for the selected data."
        )

        return

    # --------------------------------------------------------
    # Create clusters
    # --------------------------------------------------------

    clustered_df = _create_clusters(
        geo_df,
        lat_col=lat_col,
        lon_col=lon_col,
        cluster_size_m=cluster_size_m,
        columns=columns,
    )

    if clustered_df.empty:

        st.warning(
            "Geographic clustering could not be completed."
        )

        return

    clustered_df = _classify_hotspots(
        clustered_df
    )

    # --------------------------------------------------------
    # Cluster-level data
    # --------------------------------------------------------

    cluster_df = (
        clustered_df[
            [
                "Cluster_ID",
                "Cluster_Cases",
                "Cluster_Latitude",
                "Cluster_Longitude",
                "Cluster_Ward",
                "Cluster_Facility",
                "Cluster_Disease",
                "Hotspot_Classification",
            ]
        ]
        .drop_duplicates(
            subset=["Cluster_ID"]
        )
        .copy()
    )

    # --------------------------------------------------------
    # Load BMC boundaries
    # --------------------------------------------------------

    bmc_geojson = _load_bmc_wards()

    # --------------------------------------------------------
    # View-specific processing
    # --------------------------------------------------------

    display_cluster_df = cluster_df.copy()

    if map_view == "Top Hotspots":

        display_cluster_df = (
            display_cluster_df
            .sort_values(
                "Cluster_Cases",
                ascending=False,
            )
            .head(top_n)
            .copy()
        )

    elif map_view == "BMC Boundary":

        display_cluster_df = pd.DataFrame()

    # --------------------------------------------------------
    # KPI calculations
    # --------------------------------------------------------

    mapped_records = len(
        geo_df
    )

    geographic_clusters = len(
        cluster_df
    )

    highest_cluster = 0

    if not cluster_df.empty:

        highest_cluster = int(
            cluster_df[
                "Cluster_Cases"
            ].max()
        )

    very_high_count = int(
        (
            cluster_df[
                "Hotspot_Classification"
            ]
            == "Very High"
        ).sum()
    )

    wards_covered = 0

    if "Cluster_Ward" in cluster_df.columns:

        wards_covered = (
            cluster_df[
                "Cluster_Ward"
            ]
            .replace(
                "Not Available",
                np.nan,
            )
            .dropna()
            .nunique()
        )

    # --------------------------------------------------------
    # KPI display
    # --------------------------------------------------------

    st.markdown(
        "### Geographic Summary"
    )

    k1, k2, k3, k4, k5 = st.columns(
        5
    )

    with k1:

        st.metric(
            "Mapped Records",
            f"{mapped_records:,}",
        )

    with k2:

        st.metric(
            "Geographic Clusters",
            f"{geographic_clusters:,}",
        )

    with k3:

        st.metric(
            "Highest Cluster",
            f"{highest_cluster:,}",
        )

    with k4:

        st.metric(
            "Very High Hotspots",
            f"{very_high_count:,}",
        )

    with k5:

        st.metric(
            "Wards Covered",
            f"{wards_covered:,}",
        )

    # --------------------------------------------------------
    # Map
    # --------------------------------------------------------

    if map_view == "BMC Boundary":

        if bmc_geojson:

            # Create an empty layer just to display boundary.
            if PYDECK_AVAILABLE:

                bounds = _geojson_bounds(
                    bmc_geojson
                )

                if bounds:

                    min_lon, min_lat, max_lon, max_lat = bounds

                    view_state = pdk.ViewState(
                        longitude=(
                            min_lon + max_lon
                        )
                        / 2,
                        latitude=(
                            min_lat + max_lat
                        )
                        / 2,
                        zoom=10.4,
                    )

                else:

                    view_state = pdk.ViewState(
                        longitude=72.8777,
                        latitude=19.0760,
                        zoom=10.5,
                    )

                boundary_layer = pdk.Layer(
                    "GeoJsonLayer",
                    data=bmc_geojson,
                    pickable=True,
                    stroked=True,
                    filled=False,
                    line_width_min_pixels=2,
                    get_line_color=[
                        255,
                        255,
                        255,
                        230,
                    ],
                )

                boundary_deck = pdk.Deck(
                    map_style=BMC_MAP_STYLE,
                    initial_view_state=view_state,
                    layers=[
                        boundary_layer
                    ],
                    tooltip={
                        "html": """
                        <b>BMC Ward Boundary</b>
                        """
                    },
                )

                st.pydeck_chart(
                    boundary_deck,
                    use_container_width=True,
                )

            else:

                st.warning(
                    "PyDeck is not installed. BMC boundary map cannot be displayed."
                )

        else:

            st.warning(
                "BMC ward boundary data could not be loaded."
            )

    else:

        if PYDECK_AVAILABLE:

            deck = _build_map(
                display_cluster_df,
                show_labels=show_labels,
                ward_geojson=bmc_geojson,
                map_view=map_view,
            )

            if deck:

                st.pydeck_chart(
                    deck,
                    use_container_width=True,
                )

            else:

                st.warning(
                    "Map could not be generated."
                )

        else:

            st.error(
                "PyDeck is not installed. Please install pydeck."
            )

    # --------------------------------------------------------
    # Map interpretation
    # --------------------------------------------------------

    if map_view == "Overall":

        st.caption(
            "Overall view displays geographic clusters across all mapped records."
        )

    elif map_view == "Ward-wise":

        st.caption(
            "Ward-wise view displays geographic clusters together with BMC ward boundaries."
        )

    elif map_view == "Top Hotspots":

        st.caption(
            f"Top {top_n} geographic clusters by mapped case count are displayed."
        )

    elif map_view == "BMC Boundary":

        st.caption(
            "BMC Boundary view displays the administrative ward reference map."
        )

    # --------------------------------------------------------
    # Displayed map download
    # --------------------------------------------------------

    if map_view != "BMC Boundary":

        st.markdown(
            "### 🖼️ Download Displayed Map"
        )

        display_disease_name = (
            local_disease
            if local_disease != "All Diseases"
            else "All Diseases"
        )

        png_bytes, displayed_pdf_bytes = (
            _create_displayed_map_files(
                cluster_df=display_cluster_df,
                disease_name=display_disease_name,
                cluster_size_m=cluster_size_m,
                ward_geojson=bmc_geojson,
                map_view=map_view,
                show_labels=show_labels,
            )
        )

        d1, d2 = st.columns(2)

        with d1:

            if png_bytes:

                st.download_button(
                    label="🖼️ Download Displayed Map PNG",
                    data=png_bytes,
                    file_name=(
                        "geographic_hotspot_map.png"
                    ),
                    mime="image/png",
                    key="phase6_displayed_map_png",
                )

        with d2:

            if displayed_pdf_bytes:

                st.download_button(
                    label="📕 Download Displayed Map PDF",
                    data=displayed_pdf_bytes,
                    file_name=(
                        "geographic_hotspot_map.pdf"
                    ),
                    mime="application/pdf",
                    key="phase6_displayed_map_pdf",
                )

    # --------------------------------------------------------
    # Hotspot summary
    # --------------------------------------------------------

    if map_view != "BMC Boundary":

        st.markdown(
            "### 🔥 Hotspot Summary"
        )

        hotspot_summary = (
            cluster_df[
                [
                    "Cluster_ID",
                    "Cluster_Cases",
                    "Hotspot_Classification",
                    "Cluster_Ward",
                    "Cluster_Facility",
                ]
            ]
            .sort_values(
                "Cluster_Cases",
                ascending=False,
            )
            .copy()
        )

        hotspot_summary = (
            hotspot_summary.rename(
                columns={
                    "Cluster_ID": "Cluster ID",
                    "Cluster_Cases": "Cases",
                    "Hotspot_Classification": "Hotspot",
                    "Cluster_Ward": "Ward",
                    "Cluster_Facility": "Facility",
                }
            )
        )

        st.dataframe(
            hotspot_summary,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # Ward-wise geographic summary
    # --------------------------------------------------------

    st.markdown(
        "### 🏘️ Ward-wise Geographic Summary"
    )

    ward_summary = _create_ward_summary(
        cluster_df,
        columns,
    )

    if not ward_summary.empty:

        st.dataframe(
            ward_summary,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Ward information is not available for geographic summary."
        )

    # --------------------------------------------------------
    # Facility-wise geographic summary
    # --------------------------------------------------------

    st.markdown(
        "### 🏥 Facility-wise Geographic Summary"
    )

    st.caption(
        "This summary describes geographic distribution of mapped records associated with each facility. Facility locations are not plotted because facility coordinates are not being used in this module."
    )

    facility_summary = _create_facility_summary(
        cluster_df,
        columns,
    )

    if not facility_summary.empty:

        st.dataframe(
            facility_summary,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Facility information is not available for geographic summary."
        )

    # --------------------------------------------------------
    # Downloads
    # --------------------------------------------------------

    st.markdown(
        "### 📥 Download Geographic Data"
    )

    download_df = _prepare_download_dataframe(
        clustered_df,
        columns,
    )

    if not download_df.empty:

        # ----------------------------------------------------
        # Excel
        # ----------------------------------------------------

        excel_buffer = io.BytesIO()

        try:

            with pd.ExcelWriter(
                excel_buffer,
                engine="openpyxl",
            ) as writer:

                download_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Geographic Data",
                )

                hotspot_summary.to_excel(
                    writer,
                    index=False,
                    sheet_name="Hotspot Summary",
                )

                if not ward_summary.empty:

                    ward_summary.to_excel(
                        writer,
                        index=False,
                        sheet_name="Ward Summary",
                    )

                if not facility_summary.empty:

                    facility_summary.to_excel(
                        writer,
                        index=False,
                        sheet_name="Facility Summary",
                    )

            excel_buffer.seek(0)

            excel_bytes = (
                excel_buffer.getvalue()
            )

        except Exception:

            excel_bytes = None

        # ----------------------------------------------------
        # CSV
        # ----------------------------------------------------

        csv_bytes = download_df.to_csv(
            index=False
        ).encode(
            "utf-8-sig"
        )

        # ----------------------------------------------------
        # PDF report
        # ----------------------------------------------------

        report_pdf_bytes = _create_pdf(
            cluster_df=cluster_df,
            disease_name=(
                local_disease
                if local_disease != "All Diseases"
                else "All Diseases"
            ),
            filter_info=filter_info,
            map_view=map_view,
        )

        d1, d2, d3 = st.columns(3)

        with d1:

            if excel_bytes:

                st.download_button(
                    label="📊 Download Excel",
                    data=excel_bytes,
                    file_name=(
                        "geographic_analysis.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    ),
                    key="phase6_geo_excel",
                )

        with d2:

            st.download_button(
                label="📄 Download CSV",
                data=csv_bytes,
                file_name=(
                    "geographic_analysis.csv"
                ),
                mime="text/csv",
                key="phase6_geo_csv",
            )

        with d3:

            if report_pdf_bytes:

                st.download_button(
                    label="📕 Download Geographic Report PDF",
                    data=report_pdf_bytes,
                    file_name=(
                        "geographic_analysis_report.pdf"
                    ),
                    mime="application/pdf",
                    key="phase6_geo_report_pdf",
                )
