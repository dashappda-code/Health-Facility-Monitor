# phase6_map.py

import io
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st

# Optional map libraries
try:
    import pydeck as pdk
    PYDECK_AVAILABLE = True
except Exception:
    PYDECK_AVAILABLE = False

# Optional PDF / static map libraries
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.patches import PathPatch, Patch
    from matplotlib.path import Path
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
    "https://basemaps.cartocdn.com/gl/"
    "dark-matter-gl-style/style.json"
)


# ============================================================
# COLUMN HELPERS
# ============================================================

def _norm_col(x):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(x).strip().lower(),
    )


def _find_column(df, candidates):

    if df is None or df.empty:
        return None

    normalized = {
        _norm_col(c): c
        for c in df.columns
    }

    for candidate in candidates:

        key = _norm_col(candidate)

        if key in normalized:
            return normalized[key]

    # Partial matching
    for c in df.columns:

        nc = _norm_col(c)

        for candidate in candidates:

            key = _norm_col(candidate)

            if key in nc or nc in key:
                return c

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
            return bool(
                st.session_state[key]
            )

    return False


# ============================================================
# CLEAN COORDINATES
# ============================================================

def _clean_coordinates(
    df,
    lat_col,
    lon_col,
):

    work = df.copy()

    if lat_col is None or lon_col is None:
        return pd.DataFrame()

    work["_lat"] = pd.to_numeric(
        work[lat_col],
        errors="coerce",
    )

    work["_lon"] = pd.to_numeric(
        work[lon_col],
        errors="coerce",
    )

    work = work[
        work["_lat"].between(-90, 90)
        & work["_lon"].between(-180, 180)
    ].copy()

    # Mumbai geographic sanity check
    work = work[
        work["_lat"].between(17.0, 20.5)
        & work["_lon"].between(70.0, 74.5)
    ].copy()

    return work


# ============================================================
# CLUSTER CREATION
# ============================================================

def _create_clusters(
    df,
    cluster_size_m=500,
):

    if df.empty:
        return df.copy()

    work = df.copy()

    lat_deg = cluster_size_m / 111000.0

    mean_lat = float(
        work["_lat"].mean()
    )

    lon_deg = cluster_size_m / (
        111000.0
        * max(
            math.cos(
                math.radians(mean_lat)
            ),
            0.1,
        )
    )

    work["_grid_lat"] = np.floor(
        work["_lat"] / lat_deg
    ).astype(int)

    work["_grid_lon"] = np.floor(
        work["_lon"] / lon_deg
    ).astype(int)

    work["Cluster ID"] = (
        work["_grid_lat"].astype(str)
        + "_"
        + work["_grid_lon"].astype(str)
    )

    cluster_summary = (
        work.groupby("Cluster ID")
        .agg(
            Cluster_Cases=(
                "Cluster ID",
                "size",
            ),
            Cluster_Latitude=(
                "_lat",
                "mean",
            ),
            Cluster_Longitude=(
                "_lon",
                "mean",
            ),
        )
        .reset_index()
    )

    work = work.merge(
        cluster_summary,
        on="Cluster ID",
        how="left",
    )

    return work


# ============================================================
# HOTSPOT CLASSIFICATION
# ============================================================

def _classify_hotspots(
    cluster_df,
):

    if cluster_df.empty:
        return cluster_df

    work = cluster_df.copy()

    values = work[
        "Cluster_Cases"
    ].astype(float)

    if len(values) == 1:

        work["Hotspot"] = "High"

    else:

        q25 = values.quantile(0.25)
        q50 = values.quantile(0.50)
        q75 = values.quantile(0.75)

        def classify(x):

            if x >= q75:
                return "Very High"

            elif x >= q50:
                return "High"

            elif x >= q25:
                return "Moderate"

            return "Low"

        work["Hotspot"] = values.apply(
            classify
        )

    return work


# ============================================================
# BMC WARD GEOJSON
# ============================================================

@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
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
            isinstance(data, dict)
            and data.get("features")
        ):
            return data

    except Exception:
        pass

    return None


# ============================================================
# GEOJSON GEOMETRY HELPERS
# ============================================================

def _iter_geojson_positions(
    geometry,
):

    if not isinstance(
        geometry,
        dict,
    ):
        return

    coordinates = geometry.get(
        "coordinates"
    )

    if coordinates is None:
        return

    geometry_type = geometry.get(
        "type",
        "",
    )

    def walk(value):

        if (
            isinstance(value, list)
            and len(value) >= 2
            and isinstance(value[0], (int, float))
            and isinstance(value[1], (int, float))
        ):
            yield (
                float(value[0]),
                float(value[1]),
            )
            return

        if isinstance(value, list):

            for item in value:

                yield from walk(item)

    if geometry_type in [
        "Point",
        "MultiPoint",
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon",
    ]:

        yield from walk(
            coordinates
        )


def _geojson_bounds(
    geojson,
):

    if not isinstance(
        geojson,
        dict,
    ):
        return None

    lons = []
    lats = []

    for feature in geojson.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry"
        )

        for lon, lat in _iter_geojson_positions(
            geometry
        ):

            lons.append(lon)
            lats.append(lat)

    if not lons or not lats:
        return None

    return (
        min(lons),
        max(lons),
        min(lats),
        max(lats),
    )


# ============================================================
# PYDECK MAP
# ============================================================

def _build_map(
    cluster_df,
    show_labels=False,
    ward_geojson=None,
):

    if not PYDECK_AVAILABLE:

        st.error(
            "PyDeck is not installed. "
            "Please add pydeck to requirements.txt."
        )

        return

    if cluster_df.empty:

        st.info(
            "No valid geographic records are available "
            "for the selected filters."
        )

        return

    map_df = cluster_df.copy()

    point_columns = [
        "Cluster_Latitude",
        "Cluster_Longitude",
        "Cluster_Cases",
        "Hotspot",
        "Cluster ID",
    ]

    point_data = map_df[
        [
            c
            for c in point_columns
            if c in map_df.columns
        ]
    ].drop_duplicates()

    layers = []

    # --------------------------------------------------------
    # BMC Ward Boundaries
    # --------------------------------------------------------

    if isinstance(
        ward_geojson,
        dict,
    ):

        try:

            boundary_layer = pdk.Layer(
                "GeoJsonLayer",
                data=ward_geojson,
                stroked=True,
                filled=False,
                pickable=True,
                get_line_color=[
                    220,
                    220,
                    220,
                    210,
                ],
                get_line_width=2,
                line_width_min_pixels=1,
            )

            layers.append(
                boundary_layer
            )

        except Exception:
            pass

    # --------------------------------------------------------
    # Hotspot colors
    # --------------------------------------------------------

    def hotspot_color(value):

        if value == "Very High":
            return [255, 0, 0, 190]

        if value == "High":
            return [255, 110, 0, 180]

        if value == "Moderate":
            return [255, 200, 0, 170]

        return [80, 160, 255, 150]

    point_data = point_data.copy()

    point_data["_fill_color"] = (
        point_data["Hotspot"]
        .apply(hotspot_color)
    )

    # --------------------------------------------------------
    # Hotspot layer
    # --------------------------------------------------------

    hotspot_layer = pdk.Layer(
        "ScatterplotLayer",
        data=point_data,
        get_position=[
            "Cluster_Longitude",
            "Cluster_Latitude",
        ],
        get_radius="Cluster_Cases * 35",
        radius_min_pixels=8,
        radius_max_pixels=45,
        pickable=True,
        stroked=True,
        filled=True,
        opacity=0.72,
        get_fill_color="_fill_color",
        get_line_color=[
            255,
            255,
            255,
            220,
        ],
        line_width_min_pixels=1,
    )

    layers.append(
        hotspot_layer
    )

    # --------------------------------------------------------
    # Labels
    # --------------------------------------------------------

    if show_labels:

        text_layer = pdk.Layer(
            "TextLayer",
            data=point_data,
            get_position=[
                "Cluster_Longitude",
                "Cluster_Latitude",
            ],
            get_text="Cluster_Cases",
            get_size=15,
            get_color=[
                255,
                255,
                255,
                255,
            ],
            get_angle=0,
            get_text_anchor="'middle'",
            get_alignment_baseline="'center'",
            billboard=True,
            pickable=False,
        )

        layers.append(
            text_layer
        )

    # --------------------------------------------------------
    # View
    # --------------------------------------------------------

    center_lat = float(
        map_df[
            "Cluster_Latitude"
        ].mean()
    )

    center_lon = float(
        map_df[
            "Cluster_Longitude"
        ].mean()
    )

    view_zoom = 10.5

    geo_bounds = _geojson_bounds(
        ward_geojson
    )

    if geo_bounds:

        min_lon, max_lon, min_lat, max_lat = (
            geo_bounds
        )

        center_lat = (
            min_lat + max_lat
        ) / 2

        center_lon = (
            min_lon + max_lon
        ) / 2

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=view_zoom,
            pitch=0,
            bearing=0,
        ),
        map_style=BMC_MAP_STYLE,
        tooltip={
            "html": """
            <b>Hotspot:</b> {Hotspot}<br/>
            <b>Cases:</b> {Cluster_Cases}<br/>
            <b>Cluster ID:</b> {Cluster ID}
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
# DOWNLOAD DATA
# ============================================================

def _prepare_download_dataframe(
    df,
    cols,
):

    output = pd.DataFrame(
        index=df.index
    )

    if cols["disease"]:
        output["Disease"] = df[
            cols["disease"]
        ]

    if cols["date"]:
        output["Date"] = df[
            cols["date"]
        ]

    if cols["ward"]:
        output["Ward"] = df[
            cols["ward"]
        ]

    if cols["facility"]:
        output["Facility"] = df[
            cols["facility"]
        ]

    if cols["area"]:
        output["Area"] = df[
            cols["area"]
        ]

    if cols["address"]:
        output["Address"] = df[
            cols["address"]
        ]

    output["Latitude"] = df[
        "_lat"
    ]

    output["Longitude"] = df[
        "_lon"
    ]

    output["Cluster ID"] = df[
        "Cluster ID"
    ]

    output["Cluster Cases"] = df[
        "Cluster_Cases"
    ]

    output["Hotspot Classification"] = df[
        "Hotspot"
    ]

    return output


# ============================================================
# STATIC MAP HELPERS
# ============================================================

def _geometry_to_path(
    geometry,
):

    if not isinstance(
        geometry,
        dict,
    ):
        return None

    geometry_type = geometry.get(
        "type"
    )

    coordinates = geometry.get(
        "coordinates"
    )

    if coordinates is None:
        return None

    vertices = []
    codes = []

    def add_ring(
        ring,
    ):

        if not ring:
            return

        first = True

        for point in ring:

            if (
                not isinstance(
                    point,
                    (list, tuple),
                )
                or len(point) < 2
            ):
                continue

            try:

                x = float(point[0])
                y = float(point[1])

            except Exception:
                continue

            vertices.append(
                (x, y)
            )

            if first:
                codes.append(
                    Path.MOVETO
                )
                first = False

            else:
                codes.append(
                    Path.LINETO
                )

        if not first:

            codes.append(
                Path.CLOSEPOLY
            )

            vertices.append(
                vertices[-1]
            )

    try:

        if geometry_type == "Polygon":

            for ring in coordinates:
                add_ring(ring)

        elif geometry_type == "MultiPolygon":

            for polygon in coordinates:

                for ring in polygon:
                    add_ring(ring)

        else:
            return None

        if not vertices:
            return None

        return Path(
            vertices,
            codes,
        )

    except Exception:
        return None


def _add_bmc_boundaries_to_axis(
    ax,
    ward_geojson,
):

    if not isinstance(
        ward_geojson,
        dict,
    ):
        return

    if not MATPLOTLIB_AVAILABLE:
        return

    for feature in ward_geojson.get(
        "features",
        [],
    ):

        if not isinstance(
            feature,
            dict,
        ):
            continue

        geometry = feature.get(
            "geometry"
        )

        path = _geometry_to_path(
            geometry
        )

        if path is None:
            continue

        try:

            patch = PathPatch(
                path,
                facecolor=(
                    0.12,
                    0.12,
                    0.12,
                    0.18,
                ),
                edgecolor=(
                    0.75,
                    0.75,
                    0.75,
                    1.0,
                ),
                linewidth=0.8,
                zorder=2,
            )

            ax.add_patch(
                patch
            )

        except Exception:
            continue


def _set_static_extent(
    ax,
    ward_geojson,
    hotspot_df,
):

    bounds = _geojson_bounds(
        ward_geojson
    )

    if bounds:

        min_lon, max_lon, min_lat, max_lat = (
            bounds
        )

    else:

        if (
            hotspot_df is None
            or hotspot_df.empty
        ):
            return

        lat = pd.to_numeric(
            hotspot_df[
                "Cluster_Latitude"
            ],
            errors="coerce",
        )

        lon = pd.to_numeric(
            hotspot_df[
                "Cluster_Longitude"
            ],
            errors="coerce",
        )

        valid = (
            lat.notna()
            & lon.notna()
        )

        if not valid.any():
            return

        min_lat = float(
            lat[valid].min()
        )

        max_lat = float(
            lat[valid].max()
        )

        min_lon = float(
            lon[valid].min()
        )

        max_lon = float(
            lon[valid].max()
        )

    lon_padding = max(
        (max_lon - min_lon) * 0.05,
        0.01,
    )

    lat_padding = max(
        (max_lat - min_lat) * 0.05,
        0.01,
    )

    ax.set_xlim(
        min_lon - lon_padding,
        max_lon + lon_padding,
    )

    ax.set_ylim(
        min_lat - lat_padding,
        max_lat + lat_padding,
    )


def _create_static_hotspot_map(
    cluster_df,
    ward_geojson,
    selected_disease,
    cluster_size,
):

    if not MATPLOTLIB_AVAILABLE:
        return None

    try:

        fig, ax = plt.subplots(
            figsize=(12, 8),
            dpi=160,
        )

        fig.patch.set_facecolor(
            "#101010"
        )

        ax.set_facecolor(
            "#101010"
        )

        # BMC ward boundaries
        _add_bmc_boundaries_to_axis(
            ax,
            ward_geojson,
        )

        if (
            cluster_df is not None
            and not cluster_df.empty
        ):

            plot_df = cluster_df.copy()

            lat = pd.to_numeric(
                plot_df[
                    "Cluster_Latitude"
                ],
                errors="coerce",
            )

            lon = pd.to_numeric(
                plot_df[
                    "Cluster_Longitude"
                ],
                errors="coerce",
            )

            valid = (
                lat.notna()
                & lon.notna()
            )

            plot_df = plot_df.loc[
                valid
            ].copy()

            plot_df["_lat"] = lat.loc[
                valid
            ].values

            plot_df["_lon"] = lon.loc[
                valid
            ].values

            color_map = {
                "Very High": "#ff0000",
                "High": "#ff6b00",
                "Moderate": "#ffd000",
                "Low": "#4fa3ff",
            }

            for classification, group in plot_df.groupby(
                "Hotspot"
            ):

                cases = pd.to_numeric(
                    group[
                        "Cluster_Cases"
                    ],
                    errors="coerce",
                ).fillna(1)

                sizes = (
                    cases.clip(
                        lower=1
                    ).pow(0.5)
                    * 55
                )

                ax.scatter(
                    group["_lon"],
                    group["_lat"],
                    s=sizes,
                    c=color_map.get(
                        classification,
                        "#4fa3ff",
                    ),
                    alpha=0.75,
                    edgecolors="white",
                    linewidths=0.7,
                    zorder=5,
                    label=classification,
                )

        _set_static_extent(
            ax,
            ward_geojson,
            cluster_df,
        )

        ax.set_title(
            "Geographic Hotspot Map",
            fontsize=18,
            fontweight="bold",
            color="white",
            pad=18,
        )

        subtitle = (
            f"Disease: {selected_disease or 'All Diseases'}"
            f"   |   Cluster size: {cluster_size} metres"
        )

        ax.text(
            0.5,
            1.01,
            subtitle,
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=10,
            color="#dddddd",
        )

        ax.set_xlabel(
            "Longitude",
            color="white",
        )

        ax.set_ylabel(
            "Latitude",
            color="white",
        )

        ax.tick_params(
            colors="white"
        )

        for spine in ax.spines.values():

            spine.set_color(
                "#555555"
            )

        legend_handles = [
            Patch(
                facecolor=(
                    0.12,
                    0.12,
                    0.12,
                    0.18,
                ),
                edgecolor=(
                    0.75,
                    0.75,
                    0.75,
                    1.0,
                ),
                label="BMC Ward Boundary",
            ),
        ]

        for label, color in [
            ("Very High", "#ff0000"),
            ("High", "#ff6b00"),
            ("Moderate", "#ffd000"),
            ("Low", "#4fa3ff"),
        ]:

            legend_handles.append(
                Patch(
                    facecolor=color,
                    edgecolor="white",
                    label=label,
                )
            )

        legend = ax.legend(
            handles=legend_handles,
            loc="lower left",
            frameon=True,
            facecolor="#151515",
            edgecolor="#555555",
        )

        for text_item in legend.get_texts():

            text_item.set_color(
                "white"
            )

        fig.tight_layout()

        return fig

    except Exception:

        try:
            plt.close(fig)
        except Exception:
            pass

        return None


def _create_displayed_map_files(
    cluster_df,
    ward_geojson,
    selected_disease,
    cluster_size,
):

    if not MATPLOTLIB_AVAILABLE:
        return None, None

    fig = _create_static_hotspot_map(
        cluster_df=cluster_df,
        ward_geojson=ward_geojson,
        selected_disease=selected_disease,
        cluster_size=cluster_size,
    )

    if fig is None:
        return None, None

    png_buffer = io.BytesIO()

    fig.savefig(
        png_buffer,
        format="png",
        dpi=180,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
    )

    png_buffer.seek(0)

    pdf_buffer = io.BytesIO()

    with PdfPages(
        pdf_buffer
    ) as pdf:

        pdf.savefig(
            fig,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )

    pdf_buffer.seek(0)

    plt.close(fig)

    return (
        png_buffer.getvalue(),
        pdf_buffer.getvalue(),
    )


# ============================================================
# REPORT PDF
# ============================================================

def _create_pdf(
    cluster_df,
    selected_disease,
    filter_info,
):

    if not MATPLOTLIB_AVAILABLE:
        return None

    buffer = io.BytesIO()

    with PdfPages(buffer) as pdf:

        # ----------------------------------------------------
        # Cover / information page
        # ----------------------------------------------------

        fig = plt.figure(
            figsize=(11.69, 8.27)
        )

        ax = fig.add_subplot(111)

        ax.axis("off")

        ax.text(
            0.05,
            0.92,
            "GEOGRAPHIC HOTSPOT ANALYSIS",
            fontsize=18,
            fontweight="bold",
        )

        ax.text(
            0.05,
            0.86,
            f"Disease: {selected_disease}",
            fontsize=12,
        )

        y = 0.81

        for key, value in filter_info.items():

            ax.text(
                0.05,
                y,
                f"{key}: {value}",
                fontsize=10,
            )

            y -= 0.035

        ax.text(
            0.05,
            y - 0.02,
            f"Total clusters: {len(cluster_df)}",
            fontsize=11,
            fontweight="bold",
        )

        ax.text(
            0.05,
            y - 0.07,
            f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
            fontsize=9,
        )

        pdf.savefig(fig)

        plt.close(fig)

        # ----------------------------------------------------
        # Cluster summary
        # ----------------------------------------------------

        fig = plt.figure(
            figsize=(11.69, 8.27)
        )

        ax = fig.add_subplot(111)

        ax.axis("off")

        summary = (
            cluster_df[
                [
                    "Cluster ID",
                    "Cluster_Cases",
                    "Hotspot",
                ]
            ]
            .drop_duplicates()
            .sort_values(
                "Cluster_Cases",
                ascending=False,
            )
            .head(25)
        )

        table_data = [
            [
                "Cluster",
                "Cases",
                "Classification",
            ]
        ]

        for _, row in summary.iterrows():

            table_data.append(
                [
                    str(
                        row[
                            "Cluster ID"
                        ]
                    ),
                    str(
                        int(
                            row[
                                "Cluster_Cases"
                            ]
                        )
                    ),
                    str(
                        row[
                            "Hotspot"
                        ]
                    ),
                ]
            )

        table = ax.table(
            cellText=table_data,
            loc="center",
            cellLoc="center",
        )

        table.auto_set_font_size(
            False
        )

        table.set_fontsize(9)

        table.scale(
            1,
            1.5,
        )

        ax.set_title(
            "Top Geographic Hotspots",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )

        pdf.savefig(fig)

        plt.close(fig)

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# MAIN RENDER
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

    if df is None or df.empty:

        st.info(
            "No data available."
        )

        return

    cols = _detect_columns(
        df
    )

    if (
        cols["lat"] is None
        or cols["lon"] is None
    ):

        st.warning(
            "Address Latitude / Address Longitude columns were not found."
        )

        st.info(
            "Hotspot mapping requires valid patient/address geographic coordinates."
        )

        return

    # --------------------------------------------------------
    # Disease selection
    # --------------------------------------------------------

    working = df.copy()

    diseases = []

    if cols["disease"]:

        diseases = (
            working[
                cols["disease"]
            ]
            .dropna()
            .astype(str)
            .str.strip()
        )

        diseases = sorted(
            [
                x
                for x in diseases.unique()
                if x
            ]
        )

        if selected_disease is not None:

            selected_disease = str(
                selected_disease
            )

            if (
                selected_disease
                in diseases
            ):

                working = working[
                    working[
                        cols["disease"]
                    ]
                    .astype(str)
                    .str.strip()
                    == selected_disease
                ].copy()

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    working = _clean_coordinates(
        working,
        cols["lat"],
        cols["lon"],
    )

    if working.empty:

        st.warning(
            "No valid address coordinates are available "
            "for the selected filters."
        )

        return

    # --------------------------------------------------------
    # Cluster size
    # --------------------------------------------------------

    cluster_size = st.select_slider(
        "Hotspot Cluster Size",
        options=[
            200,
            500,
            1000,
            1500,
        ],
        value=500,
        format_func=lambda x: (
            f"{x} metres"
        ),
        key="phase6_cluster_size",
    )

    # --------------------------------------------------------
    # Create clusters
    # --------------------------------------------------------

    working = _create_clusters(
        working,
        cluster_size_m=cluster_size,
    )

    cluster_df = (
        working[
            [
                "Cluster ID",
                "Cluster_Cases",
                "Cluster_Latitude",
                "Cluster_Longitude",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    cluster_df = _classify_hotspots(
        cluster_df
    )

    working = working.drop(
        columns=[
            "Cluster_Cases",
            "Cluster_Latitude",
            "Cluster_Longitude",
        ],
        errors="ignore",
    )

    working = working.merge(
        cluster_df,
        on="Cluster ID",
        how="left",
    )

    # --------------------------------------------------------
    # BMC Ward Boundaries
    # --------------------------------------------------------

    with st.spinner(
        "Loading BMC ward boundaries..."
    ):

        bmc_geojson = _load_bmc_wards()

    if bmc_geojson is None:

        st.caption(
            "BMC ward boundary layer could not be loaded. "
            "Hotspot map will still be available."
        )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Mapped Records",
        f"{len(working):,}",
    )

    c2.metric(
        "Geographic Clusters",
        f"{len(cluster_df):,}",
    )

    c3.metric(
        "Highest Cluster",
        (
            f"{int(cluster_df['Cluster_Cases'].max()):,}"
            if not cluster_df.empty
            else "0"
        ),
    )

    c4.metric(
        "Very High Hotspots",
        f"{(cluster_df['Hotspot'] == 'Very High').sum():,}",
    )

    st.divider()

    # --------------------------------------------------------
    # MAP
    # --------------------------------------------------------

    show_labels = _get_show_labels()

    _build_map(
        cluster_df,
        show_labels=show_labels,
        ward_geojson=bmc_geojson,
    )

    st.caption(
        "Each hotspot represents a geographic cluster of "
        "patient/address records. Cluster size is controlled above. "
        "BMC ward boundaries are shown where available."
    )

    # --------------------------------------------------------
    # DISPLAYED MAP DOWNLOAD
    # --------------------------------------------------------

    st.markdown(
        "### 🖼️ Download Displayed Map"
    )

    if MATPLOTLIB_AVAILABLE:

        png_data, displayed_pdf_data = (
            _create_displayed_map_files(
                cluster_df=cluster_df,
                ward_geojson=bmc_geojson,
                selected_disease=(
                    selected_disease
                    or "All Diseases"
                ),
                cluster_size=cluster_size,
            )
        )

        d1, d2 = st.columns(2)

        with d1:

            if png_data:

                st.download_button(
                    "🖼️ Download Displayed Map PNG",
                    data=png_data,
                    file_name=(
                        "geographic_hotspot_displayed_map.png"
                    ),
                    mime="image/png",
                    use_container_width=True,
                    key="phase6_displayed_map_png",
                )

        with d2:

            if displayed_pdf_data:

                st.download_button(
                    "📕 Download Displayed Map PDF",
                    data=displayed_pdf_data,
                    file_name=(
                        "geographic_hotspot_displayed_map.pdf"
                    ),
                    mime="application/pdf",
                    use_container_width=True,
                    key="phase6_displayed_map_pdf",
                )

    else:

        st.info(
            "Static map download requires matplotlib."
        )

    # --------------------------------------------------------
    # TABLE
    # --------------------------------------------------------

    st.markdown(
        "### 🔥 Hotspot Summary"
    )

    hotspot_summary = (
        cluster_df[
            [
                "Cluster ID",
                "Cluster_Cases",
                "Hotspot",
                "Cluster_Latitude",
                "Cluster_Longitude",
            ]
        ]
        .sort_values(
            "Cluster_Cases",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    hotspot_summary.index = (
        hotspot_summary.index + 1
    )

    st.dataframe(
        hotspot_summary,
        use_container_width=True,
        height=350,
    )

    # --------------------------------------------------------
    # DOWNLOADS
    # --------------------------------------------------------

    st.markdown(
        "### ⬇️ Download Hotspot Data"
    )

    download_df = _prepare_download_dataframe(
        working,
        cols,
    )

    excel_buffer = io.BytesIO()

    try:

        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl",
        ) as writer:

            download_df.to_excel(
                writer,
                index=False,
                sheet_name="Hotspot Data",
            )

            hotspot_summary.to_excel(
                writer,
                index=False,
                sheet_name="Hotspot Summary",
            )

        excel_buffer.seek(0)

        col1, col2, col3 = st.columns(3)

        with col1:

            st.download_button(
                "📊 Download Hotspot Excel",
                data=excel_buffer.getvalue(),
                file_name=(
                    "geographic_hotspot_data.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
                key="phase6_hotspot_excel",
            )

        with col2:

            csv_data = download_df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "📄 Download Hotspot CSV",
                data=csv_data,
                file_name=(
                    "geographic_hotspot_data.csv"
                ),
                mime="text/csv",
                use_container_width=True,
                key="phase6_hotspot_csv",
            )

        with col3:

            if filter_info is None:
                filter_info = {}

            pdf_data = _create_pdf(
                cluster_df,
                selected_disease or "All",
                filter_info,
            )

            if pdf_data:

                st.download_button(
                    "📕 Download Hotspot Report PDF",
                    data=pdf_data,
                    file_name=(
                        "geographic_hotspot_report.pdf"
                    ),
                    mime="application/pdf",
                    use_container_width=True,
                    key="phase6_hotspot_report_pdf",
                )

    except Exception as e:

        st.warning(
            f"Download preparation issue: {e}"
        )

    # --------------------------------------------------------
    # WARD SUMMARY
    # --------------------------------------------------------

    if cols["ward"]:

        st.markdown(
            "### 🏢 Ward-wise Geographic Summary"
        )

        ward_summary = (
            working.groupby(
                cols["ward"],
                dropna=False,
            )
            .agg(
                Cases=(
                    "Cluster ID",
                    "size",
                ),
                Geographic_Clusters=(
                    "Cluster ID",
                    "nunique",
                ),
            )
            .reset_index()
        )

        ward_summary = ward_summary.sort_values(
            "Cases",
            ascending=False,
        )

        st.dataframe(
            ward_summary,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # FACILITY SUMMARY
    # --------------------------------------------------------

    if cols["facility"]:

        st.markdown(
            "### 🏥 Facility-wise Geographic Summary"
        )

        facility_summary = (
            working.groupby(
                cols["facility"],
                dropna=False,
            )
            .agg(
                Cases=(
                    "Cluster ID",
                    "size",
                ),
                Geographic_Clusters=(
                    "Cluster ID",
                    "nunique",
                ),
            )
            .reset_index()
        )

        facility_summary = facility_summary.sort_values(
            "Cases",
            ascending=False,
        )

        st.dataframe(
            facility_summary,
            use_container_width=True,
        )
