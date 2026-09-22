import io
import math

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

# ArcGIS-hosted BMC ward boundary layer
BMC_WARD_URL = (
    "https://services8.arcgis.com/"
    "r6MmJtuWAzMawmJ8/arcgis/rest/services/"
    "BMConMaps_Nov26gdb/FeatureServer/24"
)

# Programme/data master ward list supplied for this dashboard
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
    """
    Find a column using case-insensitive matching.
    """
    if df is None or df.empty:
        return None

    columns = {str(c).strip().lower(): c for c in df.columns}

    for name in possible_names:
        key = str(name).strip().lower()
        if key in columns:
            return columns[key]

    return None


def normalise_ward(value):
    """
    Convert common ward spellings into the programme ward codes.
    """

    value = clean_text(value).upper()

    if not value:
        return ""

    value = (
        value.replace("-", " ")
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

    # Remove spaces for direct programme codes
    compact = value.replace(" ", "")

    if compact in PROGRAMME_WARDS:
        return compact

    # Direct single-letter wards
    if value in PROGRAMME_WARDS:
        return value

    return value


# ============================================================
# COORDINATE PREPARATION
# ============================================================

def prepare_coordinates(df):
    """
    Keep ALL valid coordinates.

    IMPORTANT:
    No artificial Mumbai/BMC restriction is applied.
    """

    if df is None or df.empty:
        return pd.DataFrame(), 0, 0

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame(), len(df), 0

    work = df.copy()

    work["_lat"] = pd.to_numeric(
        work[LAT_COL],
        errors="coerce"
    )

    work["_lon"] = pd.to_numeric(
        work[LON_COL],
        errors="coerce"
    )

    valid = (
        work["_lat"].notna()
        & work["_lon"].notna()
        & work["_lat"].between(-90, 90)
        & work["_lon"].between(-180, 180)
    )

    valid_df = work.loc[valid].copy()

    invalid_count = int((~valid).sum())
    valid_count = int(valid.sum())

    return valid_df, invalid_count, valid_count


def coordinate_availability_text(
    total_records,
    valid_records,
    label="Selected Data"
):
    if total_records <= 0:
        return f"{label}: 0"

    percentage = (valid_records / total_records) * 100

    return (
        f"{label}: {total_records:,} | "
        f"Valid Address Coordinates: "
        f"{valid_records:,} ({percentage:.1f}%)"
    )


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
# HOTSPOT CREATION
# ============================================================

def create_hotspots(df):
    """
    Grid-based hotspot clustering.

    GRID_SIZE:
        approximately 0.005 degree cells.

    Classification:
        High      >= 10
        Moderate  >= 5
        Low       < 5
    """

    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    if "_lat" not in work.columns or "_lon" not in work.columns:
        return pd.DataFrame()

    work["_grid_lat"] = (
        work["_lat"] / GRID_SIZE
    ).round() * GRID_SIZE

    work["_grid_lon"] = (
        work["_lon"] / GRID_SIZE
    ).round() * GRID_SIZE

    work["Cluster ID"] = (
        work["_grid_lat"].round(6).astype(str)
        + "_"
        + work["_grid_lon"].round(6).astype(str)
    )

    summary = (
        work.groupby("Cluster ID", dropna=False)
        .agg(
            Cluster_Latitude=("_lat", "mean"),
            Cluster_Longitude=("_lon", "mean"),
            Cluster_Cases=("_lat", "size"),
        )
        .reset_index()
    )

    def classify(cases):
        if cases >= 10:
            return "High"
        elif cases >= 5:
            return "Moderate"
        return "Low"

    summary["Hotspot Classification"] = (
        summary["Cluster_Cases"]
        .apply(classify)
    )

    return summary


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):
    """
    Always show all 25 programme wards.
    Zero-case wards are retained.
    """

    summary = pd.DataFrame(
        {"Ward": PROGRAMME_WARDS}
    )

    if df is None or df.empty:
        summary["Cases"] = 0
        return summary

    ward_col = find_column(
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

    if ward_col is None:
        summary["Cases"] = 0
        return summary

    work = df.copy()

    work["_Programme_Ward"] = (
        work[ward_col]
        .apply(normalise_ward)
    )

    counts = (
        work["_Programme_Ward"]
        .value_counts()
        .rename_axis("Ward")
        .reset_index(name="Cases")
    )

    summary = summary.merge(
        counts,
        on="Ward",
        how="left",
    )

    summary["Cases"] = (
        pd.to_numeric(
            summary["Cases"],
            errors="coerce"
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
            timeout=8,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            return None

        if "features" not in data:
            return None

        return data

    except Exception:
        return None


def get_geojson_ward_name(properties):

    if not isinstance(properties, dict):
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
            value = clean_text(properties.get(key))

            if value:
                return normalise_ward(value)

    return ""


# ============================================================
# CHOROPLETH
# ============================================================

def get_choropleth_color(cases, max_cases):

    try:
        cases = float(cases)
        max_cases = float(max_cases)
    except Exception:
        return [245, 245, 245, 150]

    if cases <= 0:
        return [245, 245, 245, 110]

    if max_cases <= 0:
        return [255, 235, 150, 190]

    ratio = min(
        max(cases / max_cases, 0),
        1,
    )

    # Yellow -> orange -> red
    if ratio < 0.33:

        return [
            255,
            235,
            int(150 - ratio * 100),
            190,
        ]

    elif ratio < 0.66:

        return [
            255,
            int(220 - (ratio - 0.33) * 170),
            60,
            205,
        ]

    else:

        return [
            int(255 - (ratio - 0.66) * 80),
            55,
            45,
            220,
        ]


def prepare_bmc_choropleth(
    geojson,
    ward_summary
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

    for feature in geojson["features"]:

        properties = (
            feature.get("properties")
            or {}
        )

        ward = get_geojson_ward_name(
            properties
        )

        cases = int(
            ward_cases.get(
                ward,
                0
            )
        )

        properties["Programme Cases"] = cases
        properties["Ward Display"] = ward or "Unknown"

        properties["fill_color"] = (
            get_choropleth_color(
                cases,
                max_cases,
            )
        )

        # Strong ward boundary
        properties["line_color"] = [
            20,
            20,
            20,
            255,
        ]

        feature["properties"] = properties

        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


# ============================================================
# DOWNLOAD DATA
# ============================================================

def download_hotspot_data(
    hotspot_df,
    source_df,
    disease_col,
):

    if hotspot_df is None or hotspot_df.empty:
        return pd.DataFrame()

    result = hotspot_df.copy()

    # Standard columns
    result["Latitude"] = result[
        "Cluster_Latitude"
    ]

    result["Longitude"] = result[
        "Cluster_Longitude"
    ]

    # Disease
    if (
        disease_col
        and source_df is not None
        and not source_df.empty
    ):
        if disease_col in source_df.columns:
            disease_values = (
                source_df[disease_col]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
            )

            if len(disease_values) == 1:
                result["Disease"] = (
                    disease_values[0]
                )

    # Required output order
    preferred_columns = [
        "Disease",
        "Cluster ID",
        "Cluster_Cases",
        "Hotspot Classification",
        "Latitude",
        "Longitude",
    ]

    available = [
        c for c in preferred_columns
        if c in result.columns
    ]

    return result[available]


# ============================================================
# MAP LAYERS
# ============================================================

def build_map(
    choropleth_geojson,
    hotspot_df,
    extent
):

    layers = []

    # --------------------------------------------------------
    # Ward polygons
    # --------------------------------------------------------

    if choropleth_geojson:

        ward_layer = pdk.Layer(
            "GeoJsonLayer",

            data=choropleth_geojson,

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
    # Hotspot points
    # --------------------------------------------------------

    if (
        hotspot_df is not None
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
                "100 + Cluster_Cases * 25"
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
    # View
    # --------------------------------------------------------

    if (
        hotspot_df is not None
        and not hotspot_df.empty
    ):

        if extent == "All Coordinates":

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
            "backgroundColor": "white",
            "color": "black",
        },
    }

    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style=None,
    )


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_geographic_map(
    filtered_df,
    total_df=None,
):

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
            Disease-wise hotspot mapping, ward burden and
            geographic distribution based on valid address coordinates.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # DATA
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
        selected_records != total_records
    )

    # ========================================================
    # COORDINATES
    # ========================================================

    coordinate_df, invalid_count, valid_count = (
        prepare_coordinates(
            filtered_df
        )
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
            "No valid Address Latitude / Address Longitude "
            "records are available for the selected data."
        )

        if invalid_count > 0:

            st.info(
                f"{invalid_count:,} records do not have "
                "valid geographic coordinates."
            )

        return

    # ========================================================
    # DISEASE COLUMN
    # ========================================================

    disease_col = get_disease_column(
        filtered_df
    )

    diseases = []

    if disease_col:

        diseases = sorted(
            filtered_df[disease_col]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[
                lambda x: x != ""
            ]
            .unique()
            .tolist()
        )

    # ========================================================
    # WARD DATA
    # ========================================================

    ward_summary_all = create_ward_summary(
        filtered_df
    )

    # ========================================================
    # BMC BOUNDARY
    # ========================================================

    bmc_geojson = load_bmc_wards()

    # ========================================================
    # MAP CONTROLS
    #
    # IMPORTANT:
    # Disease selector is now beside Map Extent.
    # Disease dropdown intentionally made narrow.
    # ========================================================

    st.markdown(
        "<div style='height:2px;'></div>",
        unsafe_allow_html=True,
    )

    control_left, control_right = st.columns(
        [1.45, 0.65],
        gap="small",
        vertical_alignment="bottom",
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

        if diseases:

            disease_options = [
                "All Diseases"
            ] + diseases

            previous_disease = st.session_state.get(
                "geo_map_disease",
                "All Diseases",
            )

            if previous_disease not in disease_options:

                st.session_state[
                    "geo_map_disease"
                ] = "All Diseases"

            selected_disease = st.selectbox(
                "🦠 Disease on Map",
                disease_options,
                key="geo_map_disease",
            )

        else:

            selected_disease = (
                "All Diseases"
            )

            st.selectbox(
                "🦠 Disease on Map",
                ["All Diseases"],
                key="geo_map_disease",
                disabled=True,
            )

    # ========================================================
    # APPLY MAP-SPECIFIC DISEASE FILTER
    # ========================================================

    map_df = coordinate_df.copy()

    if (
        selected_disease != "All Diseases"
        and disease_col
    ):

        map_df = coordinate_df[
            coordinate_df[disease_col]
            .astype(str)
            .str.strip()
            == selected_disease
        ].copy()

    # ========================================================
    # STATUS
    # ========================================================

    if selected_disease == "All Diseases":

        disease_status = (
            "All Diseases"
        )

    else:

        disease_status = (
            selected_disease
        )

    st.caption(
        f"Map Disease: **{disease_status}** | "
        f"Mapped Records: **{len(map_df):,}**"
    )

    # ========================================================
    # NO DATA AFTER DISEASE SELECTION
    # ========================================================

    if map_df.empty:

        st.info(
            f"No coordinate records are available "
            f"for **{selected_disease}** under the current "
            "global filters."
        )

        return

    # ========================================================
    # HOTSPOTS
    # ========================================================

    hotspot_df = create_hotspots(
        map_df
    )

    # ========================================================
    # WARD SUMMARY FOR SELECTED DISEASE
    # ========================================================

    ward_summary = create_ward_summary(
        map_df
    )

    # ========================================================
    # CHOROPLETH
    # ========================================================

    choropleth_geojson = (
        prepare_bmc_choropleth(
            bmc_geojson,
            ward_summary,
        )
        if bmc_geojson
        else None
    )

    # ========================================================
    # KPI ROW
    # ========================================================

    k1, k2, k3, k4 = st.columns(
        4,
        gap="small",
    )

    with k1:
        st.metric(
            "Mapped Records",
            f"{len(map_df):,}",
        )

    with k2:
        st.metric(
            "Hotspot Clusters",
            f"{len(hotspot_df):,}",
        )

    with k3:

        if not ward_summary.empty:

            top_row = (
                ward_summary
                .sort_values(
                    "Cases",
                    ascending=False,
                )
                .iloc[0]
            )

            top_ward = top_row["Ward"]
            top_cases = int(
                top_row["Cases"]
            )

            st.metric(
                "Top Burden Ward",
                f"{top_ward} ({top_cases:,})",
            )

        else:

            st.metric(
                "Top Burden Ward",
                "—",
            )

    with k4:

        high_hotspots = 0

        if (
            not hotspot_df.empty
            and "Hotspot Classification"
            in hotspot_df.columns
        ):

            high_hotspots = int(
                (
                    hotspot_df[
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

    if choropleth_geojson is None:

        st.info(
            "BMC ward boundary layer is currently "
            "not available. Hotspot coordinates will "
            "still be displayed."
        )

    else:

        st.caption(
            "BMC ward boundaries are highlighted on the map. "
            "Ward shading represents the selected disease's "
            "case burden."
        )

    # ========================================================
    # MAIN TABS
    # ========================================================

    tab1, tab2, tab3 = st.tabs(
        [
            "🔥 Disease Hotspots",
            "🏘️ Disease-wise BMC Choropleth",
            "🗺️ BMC + All Coordinates",
        ]
    )

    # ========================================================
    # TAB 1 — HOTSPOTS
    # ========================================================

    with tab1:

        st.subheader(
            "Disease Hotspot Map"
        )

        if hotspot_df.empty:

            st.info(
                "No hotspot clusters could be created."
            )

        else:

            deck = build_map(
                choropleth_geojson=None,
                hotspot_df=hotspot_df,
                extent=extent,
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
            )

            # ----------------------------------------------
            # HOTSPOT SUMMARY
            # ----------------------------------------------

            st.subheader(
                "Hotspot Summary"
            )

            display_hotspots = (
                hotspot_df[
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

            display_hotspots = (
                display_hotspots.rename(
                    columns={
                        "Cluster ID":
                            "Cluster ID",

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
                display_hotspots,
                use_container_width=True,
                hide_index=True,
            )

            # ----------------------------------------------
            # DOWNLOAD
            # ----------------------------------------------

            export_df = download_hotspot_data(
                hotspot_df,
                map_df,
                disease_col,
            )

            if not export_df.empty:

                excel_buffer = io.BytesIO()

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
                    data=excel_buffer.getvalue(),
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
    # TAB 2 — CHOROPLETH
    # ========================================================

    with tab2:

        st.subheader(
            f"BMC Ward-wise Burden — {disease_status}"
        )

        if choropleth_geojson is None:

            st.warning(
                "BMC ward boundary data is not available "
                "right now. Ward-wise burden table is "
                "still available below."
            )

        else:

            # ----------------------------------------------
            # Choropleth map
            # ----------------------------------------------

            deck = build_map(
                choropleth_geojson=
                    choropleth_geojson,

                hotspot_df=None,

                extent="BMC / Mumbai Focus",
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
            )

        # ----------------------------------------------
        # WARD TABLE
        # ----------------------------------------------

        st.subheader(
            "25 Programme Ward-wise Case Burden"
        )

        ward_display = (
            ward_summary.copy()
        )

        ward_display[
            "Percentage"
        ] = 0.0

        total_ward_cases = (
            ward_display["Cases"].sum()
        )

        if total_ward_cases > 0:

            ward_display[
                "Percentage"
            ] = (
                ward_display["Cases"]
                / total_ward_cases
                * 100
            )

        ward_display = (
            ward_display.sort_values(
                "Cases",
                ascending=False,
            )
        )

        ward_display[
            "Percentage"
        ] = ward_display[
            "Percentage"
        ].round(1)

        st.dataframe(
            ward_display,
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------
        # WARD EXCEL
        # ----------------------------------------------

        ward_buffer = io.BytesIO()

        with pd.ExcelWriter(
            ward_buffer,
            engine="openpyxl",
        ) as writer:

            ward_display.to_excel(
                writer,
                index=False,
                sheet_name="Ward Burden",
            )

        st.download_button(
            "⬇️ Download Ward-wise Burden (Excel)",
            data=ward_buffer.getvalue(),
            file_name=(
                "ward_wise_disease_burden.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            key="geo_ward_excel",
        )

    # ========================================================
    # TAB 3 — BMC + ALL COORDINATES
    # ========================================================

    with tab3:

        st.subheader(
            "BMC Ward Boundary + All Valid Coordinates"
        )

        combined_deck = build_map(
            choropleth_geojson=
                choropleth_geojson,

            hotspot_df=hotspot_df,

            extent=extent,
        )

        st.pydeck_chart(
            combined_deck,
            use_container_width=True,
        )

        st.caption(
            "This view displays valid geographic coordinates "
            "without artificially restricting records to BMC. "
            "The BMC ward layer is shown where boundary data "
            "is available."
        )

    # ========================================================
    # CSV EXPORT
    # ========================================================

    st.divider()

    st.subheader(
        "📥 Geographic Data Export"
    )

    export_df = map_df.copy()

    export_columns = []

    possible_columns = [
        disease_col,
        "Ward",
        "Ward Name",
        "Facility",
        "Facility Name",
        "Address",
        LAT_COL,
        LON_COL,
    ]

    for col in possible_columns:

        if (
            col
            and col in export_df.columns
            and col not in export_columns
        ):

            export_columns.append(
                col
            )

    if export_columns:

        csv_df = (
            export_df[
                export_columns
            ]
            .copy()
        )

        csv_data = csv_df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            "⬇️ Download Current Geographic Data (CSV)",
            data=csv_data,
            file_name=(
                "current_geographic_data.csv"
            ),
            mime="text/csv",
            key="geo_current_csv",
        )
