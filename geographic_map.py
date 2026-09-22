import io

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

# ArcGIS-hosted ward boundary layer
BMC_WARD_URL = (
    "https://services8.arcgis.com/"
    "r6MmJtuWAzMawmJ8/arcgis/rest/services/"
    "BMConMaps_Nov26gdb/FeatureServer/24"
)

# ============================================================
# PROGRAMME WARD MASTER
# ============================================================

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
# BASIC HELPERS
# ============================================================

def clean_text(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


def find_column(df, possible_names):

    if df is None or df.empty:
        return None

    columns = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for name in possible_names:

        key = str(name).strip().lower()

        if key in columns:
            return columns[key]

    return None


def normalise_ward(value):

    value = clean_text(value).upper()

    if not value:
        return ""

    value = (
        value
        .replace("-", " ")
        .replace("_", " ")
        .replace(".", " ")
    )

    value = " ".join(value.split())

    mapping = {
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

        "M EAST": "ME",
        "ME": "ME",

        "M WEST": "MW",
        "MW": "MW",

        "P EAST": "PE",
        "PE": "PE",

        "P NORTH": "PN",
        "PN": "PN",

        "P SOUTH": "PS",
        "PS": "PS",

        "R CENTRAL": "RC",
        "RC": "RC",

        "R NORTH": "RN",
        "RN": "RN",

        "R SOUTH": "RS",
        "RS": "RS",
    }

    if value in mapping:
        return mapping[value]

    compact = value.replace(" ", "")

    if compact in PROGRAMME_WARDS:
        return compact

    if value in PROGRAMME_WARDS:
        return value

    return value


# ============================================================
# DISEASE COLUMN
# ============================================================

def get_disease_column(df):

    return find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
            "DiseaseName",
            "Disease Type",
            "Disease_Type",
        ],
    )


# ============================================================
# WARD COLUMN
# ============================================================

def get_ward_column(df):

    return find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "Ward_Name",
            "WardName",
            "Programme Ward",
            "Programme_Ward",
        ],
    )


# ============================================================
# COORDINATE PREPARATION
# ============================================================

def prepare_coordinates(df):

    if df is None or df.empty:
        return pd.DataFrame(), 0, 0

    if (
        LAT_COL not in df.columns
        or LON_COL not in df.columns
    ):
        return (
            pd.DataFrame(),
            len(df),
            0,
        )

    work = df.copy()

    work["_lat"] = pd.to_numeric(
        work[LAT_COL],
        errors="coerce",
    )

    work["_lon"] = pd.to_numeric(
        work[LON_COL],
        errors="coerce",
    )

    valid = (
        work["_lat"].notna()
        & work["_lon"].notna()
        & work["_lat"].between(-90, 90)
        & work["_lon"].between(-180, 180)
    )

    valid_df = work.loc[
        valid
    ].copy()

    invalid_count = int(
        (~valid).sum()
    )

    valid_count = int(
        valid.sum()
    )

    return (
        valid_df,
        invalid_count,
        valid_count,
    )


def coordinate_availability_text(
    total_records,
    valid_records,
    label="Selected Data",
):

    if total_records <= 0:
        return f"{label}: 0"

    percentage = (
        valid_records
        / total_records
        * 100
    )

    return (
        f"{label}: {total_records:,} | "
        f"Valid Address Coordinates: "
        f"{valid_records:,} "
        f"({percentage:.1f}%)"
    )


# ============================================================
# HOTSPOT CREATION
# ============================================================

def create_hotspots(df):

    if df is None or df.empty:
        return pd.DataFrame()

    if (
        "_lat" not in df.columns
        or "_lon" not in df.columns
    ):
        return pd.DataFrame()

    work = df.copy()

    work["_grid_lat"] = (
        work["_lat"]
        / GRID_SIZE
    ).round() * GRID_SIZE

    work["_grid_lon"] = (
        work["_lon"]
        / GRID_SIZE
    ).round() * GRID_SIZE

    work["Cluster ID"] = (
        work["_grid_lat"]
        .round(6)
        .astype(str)
        + "_"
        + work["_grid_lon"]
        .round(6)
        .astype(str)
    )

    summary = (
        work
        .groupby(
            "Cluster ID",
            dropna=False,
        )
        .agg(
            Cluster_Latitude=(
                "_lat",
                "mean",
            ),
            Cluster_Longitude=(
                "_lon",
                "mean",
            ),
            Cluster_Cases=(
                "_lat",
                "size",
            ),
        )
        .reset_index()
    )

    def classify(cases):

        if cases >= 10:
            return "High"

        if cases >= 5:
            return "Moderate"

        return "Low"

    summary[
        "Hotspot Classification"
    ] = (
        summary["Cluster_Cases"]
        .apply(classify)
    )

    return summary


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):

    summary = pd.DataFrame(
        {
            "Ward":
                PROGRAMME_WARDS
        }
    )

    if df is None or df.empty:

        summary["Cases"] = 0

        return summary

    ward_col = get_ward_column(
        df
    )

    if ward_col is None:

        summary["Cases"] = 0

        return summary

    work = df.copy()

    work["_Programme_Ward"] = (
        work[ward_col]
        .apply(normalise_ward)
    )

    counts = (
        work[
            "_Programme_Ward"
        ]
        .value_counts()
        .rename_axis("Ward")
        .reset_index(
            name="Cases"
        )
    )

    summary = summary.merge(
        counts,
        on="Ward",
        how="left",
    )

    summary["Cases"] = (
        pd.to_numeric(
            summary["Cases"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    return summary


# ============================================================
# BMC WARD BOUNDARY
# ============================================================

@st.cache_data(
    ttl=86400,
    show_spinner=False,
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
            timeout=8,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(
            data,
            dict,
        ):
            return None

        if "features" not in data:
            return None

        return data

    except Exception:

        return None


def get_geojson_ward_name(
    properties
):

    if not isinstance(
        properties,
        dict,
    ):
        return ""

    possible = [
        "NAME",
        "WARD_NAME",
        "Ward",
        "WARD",
        "ward",
        "Name",
        "Ward_Name",
        "WARDNAME",
        "WardName",
    ]

    for key in possible:

        if key in properties:

            value = clean_text(
                properties.get(key)
            )

            if value:

                return normalise_ward(
                    value
                )

    return ""


# ============================================================
# CHOROPLETH COLOR
# ============================================================

def get_choropleth_color(
    cases,
    max_cases,
):

    try:

        cases = float(cases)
        max_cases = float(
            max_cases
        )

    except Exception:

        return [
            245,
            245,
            245,
            120,
        ]

    if cases <= 0:

        return [
            245,
            245,
            245,
            100,
        ]

    if max_cases <= 0:

        return [
            255,
            235,
            150,
            190,
        ]

    ratio = min(
        max(
            cases / max_cases,
            0,
        ),
        1,
    )

    if ratio < 0.33:

        return [
            255,
            235,
            int(
                150
                - ratio * 100
            ),
            190,
        ]

    if ratio < 0.66:

        return [
            255,
            int(
                220
                - (
                    ratio
                    - 0.33
                ) * 170
            ),
            60,
            205,
        ]

    return [
        int(
            255
            - (
                ratio
                - 0.66
            ) * 80
        ),
        55,
        45,
        220,
    ]


# ============================================================
# PREPARE CHOROPLETH
# ============================================================

def prepare_bmc_choropleth(
    geojson,
    ward_summary,
):

    if not geojson:
        return None

    if "features" not in geojson:
        return None

    ward_cases = dict(
        zip(
            ward_summary["Ward"],
            ward_summary["Cases"],
        )
    )

    max_cases = (
        ward_summary["Cases"].max()
        if not ward_summary.empty
        else 0
    )

    features = []

    for feature in geojson[
        "features"
    ]:

        properties = (
            feature.get(
                "properties"
            )
            or {}
        )

        ward = (
            get_geojson_ward_name(
                properties
            )
        )

        cases = int(
            ward_cases.get(
                ward,
                0,
            )
        )

        properties[
            "Programme Cases"
        ] = cases

        properties[
            "Ward Display"
        ] = (
            ward
            or "Unknown"
        )

        properties[
            "fill_color"
        ] = get_choropleth_color(
            cases,
            max_cases,
        )

        properties[
            "line_color"
        ] = [
            20,
            20,
            20,
            255,
        ]

        feature[
            "properties"
        ] = properties

        features.append(
            feature
        )

    return {
        "type":
            "FeatureCollection",
        "features":
            features,
    }


# ============================================================
# BUILD MAP
# ============================================================

def build_map(
    choropleth_geojson=None,
    hotspot_df=None,
    extent="BMC / Mumbai Focus",
    show_hotspots=True,
):

    layers = []

    # --------------------------------------------------------
    # WARD POLYGONS
    # --------------------------------------------------------

    if choropleth_geojson:

        ward_layer = pdk.Layer(
            "GeoJsonLayer",

            data=(
                choropleth_geojson
            ),

            pickable=True,

            stroked=True,

            filled=True,

            get_fill_color=(
                "properties.fill_color"
            ),

            get_line_color=(
                "properties.line_color"
            ),

            get_line_width=5,

            line_width_min_pixels=2,

            auto_highlight=True,

            highlight_color=[
                255,
                215,
                0,
                255,
            ],
        )

        layers.append(
            ward_layer
        )

    # --------------------------------------------------------
    # HOTSPOT POINTS
    # --------------------------------------------------------

    if (
        show_hotspots
        and hotspot_df is not None
        and not hotspot_df.empty
    ):

        hotspot_layer = pdk.Layer(
            "ScatterplotLayer",

            data=hotspot_df,

            get_position=[
                "Cluster_Longitude",
                "Cluster_Latitude",
            ],

            get_radius=(
                "100 + "
                "Cluster_Cases * 25"
            ),

            get_fill_color=[
                220,
                40,
                40,
                180,
            ],

            get_line_color=[
                120,
                0,
                0,
                255,
            ],

            line_width_min_pixels=1,

            stroked=True,

            filled=True,

            pickable=True,

            auto_highlight=True,
        )

        layers.append(
            hotspot_layer
        )

    # --------------------------------------------------------
    # MAP VIEW
    # --------------------------------------------------------

    if (
        hotspot_df is not None
        and not hotspot_df.empty
    ):

        if (
            extent
            == "All Coordinates"
        ):

            center_lat = float(
                hotspot_df[
                    "Cluster_Latitude"
                ].mean()
            )

            center_lon = float(
                hotspot_df[
                    "Cluster_Longitude"
                ].mean()
            )

            zoom = 5.5

        else:

            center_lat = 19.0760
            center_lon = 72.8777
            zoom = 10

    else:

        center_lat = 19.0760
        center_lon = 72.8777
        zoom = 10

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
        pitch=0,
        bearing=0,
    )

    tooltip = {
        "html": """
        <div style="font-size:13px;">
            <b>Ward:</b>
            {Ward Display}<br/>
            <b>Cases:</b>
            {Programme Cases}<br/>
            <b>Cluster:</b>
            {Cluster ID}<br/>
            <b>Cluster Cases:</b>
            {Cluster_Cases}<br/>
            <b>Hotspot:</b>
            {Hotspot Classification}
        </div>
        """,
        "style": {
            "backgroundColor":
                "white",
            "color":
                "black",
        },
    }

    return pdk.Deck(
        layers=layers,
        initial_view_state=(
            view_state
        ),
        tooltip=tooltip,
        map_style=None,
    )


# ============================================================
# DISEASE COMPARISON
# ============================================================

def create_disease_comparison(
    coordinate_df,
    disease_col,
    selected_diseases,
):

    if (
        coordinate_df is None
        or coordinate_df.empty
        or not disease_col
    ):
        return pd.DataFrame()

    rows = []

    disease_list = (
        selected_diseases
        if selected_diseases
        else sorted(
            coordinate_df[
                disease_col
            ]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )
    )

    for disease in disease_list:

        disease_df = (
            coordinate_df[
                coordinate_df[
                    disease_col
                ]
                .astype(str)
                .str.strip()
                == disease
            ]
            .copy()
        )

        cases = len(
            disease_df
        )

        hotspots = create_hotspots(
            disease_df
        )

        high_hotspots = 0

        if not hotspots.empty:

            high_hotspots = int(
                (
                    hotspots[
                        "Hotspot Classification"
                    ]
                    == "High"
                ).sum()
            )

        ward_summary = (
            create_ward_summary(
                disease_df
            )
        )

        if (
            not ward_summary.empty
            and ward_summary[
                "Cases"
            ].sum() > 0
        ):

            top_row = (
                ward_summary
                .sort_values(
                    "Cases",
                    ascending=False,
                )
                .iloc[0]
            )

            top_ward = (
                top_row["Ward"]
            )

            top_ward_cases = int(
                top_row["Cases"]
            )

        else:

            top_ward = "—"
            top_ward_cases = 0

        rows.append(
            {
                "Disease":
                    disease,

                "Cases":
                    cases,

                "Valid Coordinates":
                    cases,

                "Hotspot Clusters":
                    len(hotspots),

                "High Hotspots":
                    high_hotspots,

                "Top Ward":
                    top_ward,

                "Top Ward Cases":
                    top_ward_cases,
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# DISEASE CHOROPLETH DATA
# ============================================================

def get_disease_map_data(
    coordinate_df,
    disease_col,
    disease,
    bmc_geojson,
):

    disease_df = (
        coordinate_df[
            coordinate_df[
                disease_col
            ]
            .astype(str)
            .str.strip()
            == disease
        ]
        .copy()
    )

    ward_summary = (
        create_ward_summary(
            disease_df
        )
    )

    choropleth = None

    if bmc_geojson:

        choropleth = (
            prepare_bmc_choropleth(
                bmc_geojson,
                ward_summary,
            )
        )

    hotspots = create_hotspots(
        disease_df
    )

    return (
        disease_df,
        ward_summary,
        hotspots,
        choropleth,
    )


# ============================================================
# DOWNLOAD HOTSPOTS
# ============================================================

def download_hotspot_data(
    hotspot_df,
    source_df,
    disease_col,
):

    if (
        hotspot_df is None
        or hotspot_df.empty
    ):
        return pd.DataFrame()

    result = hotspot_df.copy()

    result["Latitude"] = (
        result[
            "Cluster_Latitude"
        ]
    )

    result["Longitude"] = (
        result[
            "Cluster_Longitude"
        ]
    )

    if (
        disease_col
        and source_df is not None
        and not source_df.empty
    ):

        if (
            disease_col
            in source_df.columns
        ):

            disease_values = (
                source_df[
                    disease_col
                ]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
            )

            if len(
                disease_values
            ) == 1:

                result[
                    "Disease"
                ] = disease_values[0]

    preferred = [
        "Disease",
        "Cluster ID",
        "Cluster_Cases",
        "Hotspot Classification",
        "Latitude",
        "Longitude",
    ]

    available = [
        c
        for c in preferred
        if c in result.columns
    ]

    return result[
        available
    ]


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_geographic_map(
    filtered_df,
    total_df=None,
):

    # ========================================================
    # HEADER
    # ========================================================

    st.markdown(
        """
        <div style="
            font-size:26px;
            font-weight:700;
            margin-bottom:4px;
        ">
            Geographic Disease Hotspot & Ward Analysis
        </div>

        <div style="
            font-size:14px;
            color:#666;
            margin-bottom:14px;
        ">
            Disease-wise hotspot mapping, geographic
            distribution, ward burden and comparative
            choropleth analysis.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # BASIC DATA CHECK
    # ========================================================

    if filtered_df is None:

        st.info(
            "No filtered data available."
        )

        return

    selected_records = len(
        filtered_df
    )

    total_records = (
        len(total_df)
        if total_df is not None
        else selected_records
    )

    global_filter_active = (
        selected_records
        != total_records
    )

    # ========================================================
    # COORDINATES
    # ========================================================

    (
        coordinate_df,
        invalid_count,
        valid_count,
    ) = prepare_coordinates(
        filtered_df
    )

    if global_filter_active:

        st.caption(
            coordinate_availability_text(
                selected_records,
                valid_count,
                "Selected Data",
            )
        )

    else:

        st.caption(
            coordinate_availability_text(
                selected_records,
                valid_count,
                "Total Data",
            )
        )

    if valid_count == 0:

        st.warning(
            "No valid Address Latitude / "
            "Address Longitude records are "
            "available for the selected data."
        )

        if invalid_count > 0:

            st.info(
                f"{invalid_count:,} records "
                "do not have valid geographic "
                "coordinates."
            )

        return

    # ========================================================
    # DISEASE COLUMN
    # ========================================================

    disease_col = (
        get_disease_column(
            filtered_df
        )
    )

    if disease_col is None:

        st.error(
            "Disease column was not found "
            "in the selected dataset."
        )

        return

    diseases = sorted(
        coordinate_df[
            disease_col
        ]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[
            lambda x: x != ""
        ]
        .unique()
        .tolist()
    )

    if not diseases:

        st.warning(
            "No disease values are available "
            "for geographic analysis."
        )

        return

    # ========================================================
    # BMC WARD DATA
    # ========================================================

    bmc_geojson = (
        load_bmc_wards()
    )

    # ========================================================
    # MAP CONTROLS
    # ========================================================

    control_left, control_right = (
        st.columns(
            [1.45, 0.65],
            gap="small",
        )
    )

    with control_left:

        extent = st.radio(
            "🗺️ Map Extent",
            [
                "BMC / Mumbai Focus",
                "All Coordinates",
            ],
            horizontal=True,
            key="geo_extent",
        )

    with control_right:

        selected_diseases = (
            st.multiselect(
                "🦠 Disease on Map",
                diseases,
                default=[],
                key="geo_map_diseases",
                placeholder=(
                    "Select disease(s)..."
                ),
                max_selections=10,
            )
        )

    # ========================================================
    # APPLY DISEASE FILTER
    # ========================================================

    if selected_diseases:

        map_df = coordinate_df[
            coordinate_df[
                disease_col
            ]
            .astype(str)
            .str.strip()
            .isin(
                selected_diseases
            )
        ].copy()

        disease_status = (
            ", ".join(
                selected_diseases
            )
        )

    else:

        map_df = (
            coordinate_df.copy()
        )

        disease_status = (
            "All Diseases"
        )

    # ========================================================
    # MAP STATUS
    # ========================================================

    st.caption(
        f"Map Disease: **{disease_status}** | "
        f"Mapped Records: **{len(map_df):,}**"
    )

    if map_df.empty:

        st.info(
            "No valid coordinate records are "
            "available for the selected disease(s) "
            "under the current global filters."
        )

        return

    # ========================================================
    # OVERALL HOTSPOTS
    # ========================================================

    overall_hotspots = (
        create_hotspots(
            map_df
        )
    )

    # ========================================================
    # OVERALL WARD SUMMARY
    # ========================================================

    overall_ward_summary = (
        create_ward_summary(
            map_df
        )
    )

    # ========================================================
    # OVERALL CHOROPLETH
    # ========================================================

    overall_choropleth = None

    if bmc_geojson:

        overall_choropleth = (
            prepare_bmc_choropleth(
                bmc_geojson,
                overall_ward_summary,
            )
        )

    # ========================================================
    # KPI ROW
    # ========================================================

    k1, k2, k3, k4 = (
        st.columns(
            4,
            gap="small",
        )
    )

    with k1:

        st.metric(
            "Mapped Records",
            f"{len(map_df):,}",
        )

    with k2:

        st.metric(
            "Hotspot Clusters",
            f"{len(overall_hotspots):,}",
        )

    with k3:

        if (
            not overall_ward_summary.empty
            and overall_ward_summary[
                "Cases"
            ].sum() > 0
        ):

            top_row = (
                overall_ward_summary
                .sort_values(
                    "Cases",
                    ascending=False,
                )
                .iloc[0]
            )

            st.metric(
                "Top Burden Ward",
                (
                    f"{top_row['Ward']} "
                    f"({int(top_row['Cases']):,})"
                ),
            )

        else:

            st.metric(
                "Top Burden Ward",
                "—",
            )

    with k4:

        high_hotspots = 0

        if (
            not overall_hotspots.empty
            and
            "Hotspot Classification"
            in overall_hotspots.columns
        ):

            high_hotspots = int(
                (
                    overall_hotspots[
                        "Hotspot Classification"
                    ]
                    == "High"
                ).sum()
            )

        st.metric(
            "High Hotspots",
            f"{high_hotspots:,}",
        )

    # ========================================================
    # BOUNDARY STATUS
    # ========================================================

    if overall_choropleth is None:

        st.info(
            "BMC ward boundary layer is currently "
            "not available. Geographic points and "
            "ward tables will still be displayed."
        )

    else:

        st.caption(
            "BMC ward boundaries are highlighted. "
            "Choropleth shading represents ward-wise "
            "case burden."
        )

    # ========================================================
    # TABS
    # ========================================================

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
            "Disease Hotspot Map"
        )

        if overall_hotspots.empty:

            st.info(
                "No hotspot clusters could be created."
            )

        else:

            deck = build_map(
                choropleth_geojson=None,
                hotspot_df=overall_hotspots,
                extent=extent,
                show_hotspots=True,
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
            )

            st.subheader(
                "Hotspot Summary"
            )

            hotspot_display = (
                overall_hotspots[
                    [
                        "Cluster ID",
                        "Cluster_Cases",
                        "Hotspot Classification",
                        "Cluster_Latitude",
                        "Cluster_Longitude",
                    ]
                ]
                .sort_values(
                    "Cluster_Cases",
                    ascending=False,
                )
                .copy()
            )

            hotspot_display = (
                hotspot_display.rename(
                    columns={
                        "Cluster_Cases":
                            "Cluster Cases",

                        "Hotspot Classification":
                            "Hotspot Classification",

                        "Cluster_Latitude":
                            "Latitude",

                        "Cluster_Longitude":
                            "Longitude",
                    }
                )
            )

            st.dataframe(
                hotspot_display,
                use_container_width=True,
                hide_index=True,
            )

            # --------------------------------------------
            # HOTSPOT EXCEL
            # --------------------------------------------

            export_df = (
                download_hotspot_data(
                    overall_hotspots,
                    map_df,
                    disease_col,
                )
            )

            if not export_df.empty:

                excel_buffer = (
                    io.BytesIO()
                )

                with pd.ExcelWriter(
                    excel_buffer,
                    engine="openpyxl",
                ) as writer:

                    export_df.to_excel(
                        writer,
                        index=False,
                        sheet_name="Hotspots",
                    )

                st.download_button(
                    "⬇️ Download Hotspot Data (Excel)",
                    data=(
                        excel_buffer
                        .getvalue()
                    ),
                    file_name=(
                        "disease_hotspot_data.xlsx"
                    ),
                    mime=(
                        "application/vnd.openxmlformats-"
                        "officedocument.spreadsheetml.sheet"
                    ),
                    key="geo_hotspot_excel",
                )

    # ========================================================
    # TAB 2 — DISEASE COMPARISON
    # ========================================================

    with tab2:

        st.subheader(
            "Disease-wise Geographic Comparison"
        )

        comparison_df = (
            create_disease_comparison(
                coordinate_df=coordinate_df,
                disease_col=disease_col,
                selected_diseases=(
                    selected_diseases
                ),
            )
        )

        if comparison_df.empty:

            st.info(
                "No disease comparison data available."
            )

        else:

            # --------------------------------------------
            # SUMMARY TABLE
            # --------------------------------------------

            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True,
            )

            # --------------------------------------------
            # COMPARISON DETAILS
            # --------------------------------------------

            st.markdown(
                "### Disease-wise Summary"
            )

            comparison_cols = st.columns(
                min(
                    len(comparison_df),
                    4,
                ),
                gap="small",
            )

            for idx, row in (
                comparison_df
                .iterrows()
            ):

                col = (
                    comparison_cols[
                        idx
                        % len(
                            comparison_cols
                        )
                    ]
                )

                with col:

                    st.markdown(
                        f"""
                        **{row['Disease']}**

                        - Cases: **{int(row['Cases']):,}**
                        - Coordinates: **{int(row['Valid Coordinates']):,}**
                        - Hotspots: **{int(row['Hotspot Clusters']):,}**
                        - High Hotspots: **{int(row['High Hotspots']):,}**
                        - Top Ward: **{row['Top Ward']}**
                        - Top Ward Cases: **{int(row['Top Ward Cases']):,}**
                        """
                    )

            # --------------------------------------------
            # WARD COMPARISON TABLE
            # --------------------------------------------

            st.markdown(
                "### Disease-wise Ward Burden Comparison"
            )

            selected_for_table = (
                selected_diseases
                if selected_diseases
                else diseases
            )

            ward_comparison = (
                pd.DataFrame(
                    {
                        "Ward":
                            PROGRAMME_WARDS
                    }
                )
            )

            for disease in (
                selected_for_table
            ):

                disease_df = (
                    coordinate_df[
                        coordinate_df[
                            disease_col
                        ]
                        .astype(str)
                        .str.strip()
                        == disease
                    ]
                )

                disease_ward = (
                    create_ward_summary(
                        disease_df
                    )
                )

                disease_ward = (
                    disease_ward.rename(
                        columns={
                            "Cases":
                                disease
                        }
                    )
                )

                ward_comparison = (
                    ward_comparison.merge(
                        disease_ward[
                            [
                                "Ward",
                                disease,
                            ]
                        ],
                        on="Ward",
                        how="left",
                    )
                )

            for disease in (
                selected_for_table
            ):

                if disease in (
                    ward_comparison.columns
                ):

                    ward_comparison[
                        disease
                    ] = (
                        pd.to_numeric(
                            ward_comparison[
                                disease
                            ],
                            errors="coerce",
                        )
                        .fillna(0)
                        .astype(int)
                    )

            st.dataframe(
                ward_comparison,
                use_container_width=True,
                hide_index=True,
            )

            # --------------------------------------------
            # COMPARISON EXCEL
            # --------------------------------------------

            comparison_buffer = (
                io.BytesIO()
            )

            with pd.ExcelWriter(
                comparison_buffer,
                engine="openpyxl",
            ) as writer:

                comparison_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Disease Comparison",
                )

                ward_comparison.to_excel(
                    writer,
                    index=False,
                    sheet_name="Ward Comparison",
                )

            st.download_button(
                "⬇️ Download Disease Comparison (Excel)",
                data=(
                    comparison_buffer
                    .getvalue()
                ),
                file_name=(
                    "disease_geographic_comparison.xlsx"
                ),
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                key="geo_comparison_excel",
            )

    # ========================================================
    # TAB 3 — CHOROPLETH COMPARISON
    # ========================================================

    with tab3:

        st.subheader(
            "Disease-wise BMC Ward Choropleth Comparison"
        )

        if not bmc_geojson:

            st.warning(
                "BMC ward boundary data is not available "
                "right now."
            )

        else:

            selected_for_maps = (
                selected_diseases
                if selected_diseases
                else diseases
            )

            # Limit simultaneous maps for performance
            if len(
                selected_for_maps
            ) > 6:

                st.info(
                    "For performance, the choropleth "
                    "comparison displays the first 6 "
                    "selected diseases. The comparison "
                    "table can contain all selected diseases."
                )

                map_diseases = (
                    selected_for_maps[:6]
                )

            else:

                map_diseases = (
                    selected_for_maps
                )

            # --------------------------------------------
            # DISEASE MAPS
            # --------------------------------------------

            for start in range(
                0,
                len(map_diseases),
                2,
            ):

                row_diseases = (
                    map_diseases[
                        start:start + 2
                    ]
                )

                map_cols = st.columns(
                    len(
                        row_diseases
                    ),
                    gap="small",
                )

                for map_col, disease in zip(
                    map_cols,
                    row_diseases,
                ):

                    with map_col:

                        (
                            disease_df,
                            disease_ward,
                            disease_hotspots,
                            disease_choropleth,
                        ) = (
                            get_disease_map_data(
                                coordinate_df,
                                disease_col,
                                disease,
                                bmc_geojson,
                            )
                        )

                        st.markdown(
                            f"**{disease}**"
                        )

                        st.caption(
                            f"Cases: "
                            f"{len(disease_df):,} | "
                            f"Hotspots: "
                            f"{len(disease_hotspots):,}"
                        )

                        disease_deck = (
                            build_map(
                                choropleth_geojson=(
                                    disease_choropleth
                                ),
                                hotspot_df=None,
                                extent=(
                                    "BMC / Mumbai Focus"
                                ),
                                show_hotspots=False,
                            )
                        )

                        st.pydeck_chart(
                            disease_deck,
                            use_container_width=True,
                        )

                        # Top 5 wards
                        top5 = (
                            disease_ward
                            .sort_values(
                                "Cases",
                                ascending=False,
                            )
                            .head(5)
                            .copy()
                        )

                        top5 = (
                            top5[
                                [
                                    "Ward",
                                    "Cases",
                                ]
                            ]
                        )

                        st.dataframe(
                            top5,
                            use_container_width=True,
                            hide_index=True,
                        )

            st.caption(
                "Each disease map uses the same BMC ward "
                "boundary framework. Darker shading indicates "
                "higher ward-wise burden for that disease."
            )

    # ========================================================
    # TAB 4 — COMBINED VIEW
    # ========================================================

    with tab4:

        st.subheader(
            "BMC Ward Boundary + Selected Disease Hotspots"
        )

        combined_deck = build_map(
            choropleth_geojson=(
                overall_choropleth
            ),
            hotspot_df=(
                overall_hotspots
            ),
            extent=extent,
            show_hotspots=True,
        )

        st.pydeck_chart(
            combined_deck,
            use_container_width=True,
        )

        st.caption(
            "Ward polygons show combined burden of the "
            "currently selected disease(s). Red points "
            "represent geographic hotspot clusters."
        )

        # ----------------------------------------------------
        # COMBINED WARD TABLE
        # ----------------------------------------------------

        st.subheader(
            "Selected Disease(s) — Ward-wise Burden"
        )

        combined_ward = (
            overall_ward_summary
            .sort_values(
                "Cases",
                ascending=False,
            )
            .copy()
        )

        total_cases = (
            combined_ward[
                "Cases"
            ].sum()
        )

        if total_cases > 0:

            combined_ward[
                "Percentage"
            ] = (
                combined_ward[
                    "Cases"
                ]
                / total_cases
                * 100
            ).round(1)

        else:

            combined_ward[
                "Percentage"
            ] = 0.0

        st.dataframe(
            combined_ward,
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # WARD EXCEL
        # ----------------------------------------------------

        ward_buffer = (
            io.BytesIO()
        )

        with pd.ExcelWriter(
            ward_buffer,
            engine="openpyxl",
        ) as writer:

            combined_ward.to_excel(
                writer,
                index=False,
                sheet_name="Ward Burden",
            )

        st.download_button(
            "⬇️ Download Ward-wise Burden (Excel)",
            data=(
                ward_buffer
                .getvalue()
            ),
            file_name=(
                "selected_disease_ward_burden.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            key="geo_combined_ward_excel",
        )

    # ========================================================
    # CURRENT GEOGRAPHIC DATA EXPORT
    # ========================================================

    st.divider()

    st.subheader(
        "📥 Geographic Data Export"
    )

    export_columns = []

    possible_columns = [
        disease_col,
        get_ward_column(
            map_df
        ),
        "Facility",
        "Facility Name",
        "Address",
        LAT_COL,
        LON_COL,
    ]

    for col in possible_columns:

        if (
            col
            and col in map_df.columns
            and col not in export_columns
        ):

            export_columns.append(
                col
            )

    if export_columns:

        csv_df = (
            map_df[
                export_columns
            ]
            .copy()
        )

        csv_data = (
            csv_df
            .to_csv(
                index=False
            )
            .encode("utf-8")
        )

        st.download_button(
            "⬇️ Download Current Geographic Data (CSV)",
            data=csv_data,
            file_name=(
                "current_geographic_data.csv"
            ),
            mime="text/csv",
            key="geo_current_csv",
        )
