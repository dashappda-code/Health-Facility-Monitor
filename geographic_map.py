import io
import re
import math
import urllib.parse

import pandas as pd
import streamlit as st
import pydeck as pdk


# ============================================================
# BMC GIS CONFIGURATION
# ============================================================

BMC_WARD_LAYER_URL = (
    "https://prsrvgisapp.mcgm.gov.in/server/rest/services/"
    "mcgm/MCGMGIS_Departments_Master_All_Layers_WGS/"
    "MapServer/238"
)

BMC_WARD_QUERY_URL = (
    BMC_WARD_LAYER_URL + "/query"
)


# ============================================================
# BASIC HELPERS
# ============================================================

def _clean_text(value):
    if pd.isna(value):
        return ""

    text = str(value).strip()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def _normalise_ward(value):
    text = _clean_text(value).upper()

    text = text.replace(
        "WARD",
        "",
    )

    text = text.replace(
        "M-WARD",
        "M",
    )

    text = text.replace(
        "MCGM",
        "",
    )

    text = text.replace(
        "BMC",
        "",
    )

    text = re.sub(
        r"[^A-Z0-9]",
        "",
        text,
    )

    return text


def _find_column(
    df,
    candidates,
):
    if df is None or df.empty:
        return None

    exact = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:

        key = str(
            candidate
        ).strip().lower()

        if key in exact:
            return exact[key]

    for column in df.columns:

        col = str(
            column
        ).strip().lower()

        for candidate in candidates:

            candidate_text = str(
                candidate
            ).strip().lower()

            if (
                candidate_text in col
                or col in candidate_text
            ):
                return column

    return None


# ============================================================
# LOAD BMC WARD BOUNDARIES
# ============================================================

@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def load_bmc_wards():

    try:

        params = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        }

        query_string = urllib.parse.urlencode(
            params
        )

        url = (
            BMC_WARD_QUERY_URL
            + "?"
            + query_string
        )

        import requests

        response = requests.get(
            url,
            timeout=30,
        )

        response.raise_for_status()

        geojson = response.json()

        if not geojson:
            return None, "Empty response from BMC GIS."

        if (
            "features" not in geojson
            or not geojson["features"]
        ):
            return (
                None,
                "BMC GIS returned no ward polygons.",
            )

        return geojson, None

    except Exception as e:

        return (
            None,
            f"BMC ward boundary could not be loaded: {e}",
        )


# ============================================================
# GET WARD FIELD
# ============================================================

def get_geojson_ward_field(
    geojson,
):

    if not geojson:
        return None

    features = geojson.get(
        "features",
        [],
    )

    if not features:
        return None

    properties = features[0].get(
        "properties",
        {},
    )

    candidates = [
        "WARD_NO",
        "WARD",
        "WARDNAME",
        "WARD_NAME",
        "NAME",
        "Name",
    ]

    for candidate in candidates:

        if candidate in properties:
            return candidate

    property_names = list(
        properties.keys()
    )

    for prop in property_names:

        normalized = (
            str(prop)
            .strip()
            .upper()
        )

        if normalized in {
            "WARD_NO",
            "WARD",
            "WARDNAME",
            "WARD_NAME",
            "NAME",
        }:

            return prop

    return None


# ============================================================
# PREPARE WARD CASE COUNTS
# ============================================================

def prepare_ward_summary(
    df,
):

    if df is None or df.empty:
        return pd.DataFrame()

    ward_column = _find_column(
        df,
        [
            "Ward Name",
            "Ward",
            "WARD",
            "WARD_NAME",
            "WardName",
            "Ward No",
        ],
    )

    if ward_column is None:
        return pd.DataFrame()

    work = df.copy()

    work["_ward_original"] = (
        work[ward_column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    work["_ward_normalized"] = (
        work["_ward_original"]
        .map(_normalise_ward)
    )

    work = work[
        work["_ward_normalized"].ne("")
    ]

    if work.empty:
        return pd.DataFrame()

    summary = (
        work
        .groupby(
            "_ward_normalized",
            dropna=False,
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    return summary


# ============================================================
# MERGE CASES INTO GEOJSON
# ============================================================

def merge_ward_cases(
    geojson,
    df,
):

    if not geojson:
        return geojson

    summary = prepare_ward_summary(
        df
    )

    summary_lookup = {}

    if not summary.empty:

        summary_lookup = dict(
            zip(
                summary[
                    "_ward_normalized"
                ],
                summary["Cases"],
            )
        )

    ward_field = get_geojson_ward_field(
        geojson
    )

    if ward_field is None:
        return geojson

    features = geojson.get(
        "features",
        [],
    )

    for feature in features:

        properties = feature.setdefault(
            "properties",
            {},
        )

        ward_value = properties.get(
            ward_field,
            "",
        )

        normalized = _normalise_ward(
            ward_value
        )

        cases = summary_lookup.get(
            normalized,
            0,
        )

        properties[
            "Programme_Cases"
        ] = int(cases)

    return geojson


# ============================================================
# WARD CASE TABLE
# ============================================================

def create_ward_case_table(
    geojson,
):

    if not geojson:
        return pd.DataFrame()

    ward_field = get_geojson_ward_field(
        geojson
    )

    if ward_field is None:
        return pd.DataFrame()

    rows = []

    for feature in geojson.get(
        "features",
        [],
    ):

        properties = feature.get(
            "properties",
            {},
        )

        ward = properties.get(
            ward_field,
            "",
        )

        cases = properties.get(
            "Programme_Cases",
            0,
        )

        rows.append(
            {
                "Ward": _clean_text(ward),
                "Cases": int(
                    cases or 0
                ),
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    result = (
        result
        .sort_values(
            "Cases",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )

    return result


# ============================================================
# COORDINATE CLEANING
# ============================================================

def prepare_coordinates(
    df,
):

    if df is None or df.empty:
        return pd.DataFrame()

    lat_col = _find_column(
        df,
        [
            "Address Latitude",
            "Latitude",
            "Lat",
            "LAT",
            "latitude",
        ],
    )

    lon_col = _find_column(
        df,
        [
            "Address Longitude",
            "Longitude",
            "Lon",
            "Lng",
            "LONG",
            "longitude",
        ],
    )

    if lat_col is None or lon_col is None:
        return pd.DataFrame()

    work = df.copy()

    work["_lat"] = pd.to_numeric(
        work[lat_col],
        errors="coerce",
    )

    work["_lon"] = pd.to_numeric(
        work[lon_col],
        errors="coerce",
    )

    work = work.dropna(
        subset=[
            "_lat",
            "_lon",
        ]
    )

    if work.empty:
        return pd.DataFrame()

    # Mumbai broad geographic bounds
    work = work[
        work["_lat"].between(
            18.80,
            19.35,
        )
        &
        work["_lon"].between(
            72.70,
            73.20,
        )
    ]

    if work.empty:
        return pd.DataFrame()

    return work


# ============================================================
# GRID HOTSPOT CLUSTERING
# ============================================================

def create_hotspots(
    df,
    grid_size_m=500,
):

    work = prepare_coordinates(
        df
    )

    if work.empty:
        return pd.DataFrame()

    lat_factor = 111320.0

    lon_factor = (
        111320.0
        * math.cos(
            math.radians(19.08)
        )
    )

    work["_x_m"] = (
        work["_lon"]
        * lon_factor
    )

    work["_y_m"] = (
        work["_lat"]
        * lat_factor
    )

    work["_grid_x"] = (
        work["_x_m"]
        / grid_size_m
    ).astype(int)

    work["_grid_y"] = (
        work["_y_m"]
        / grid_size_m
    ).astype(int)

    cluster_counts = (
        work
        .groupby(
            [
                "_grid_x",
                "_grid_y",
            ],
            dropna=False,
        )
        .size()
        .reset_index(
            name="Cluster Cases"
        )
    )

    cluster_counts[
        "Cluster ID"
    ] = (
        "C-"
        + (
            cluster_counts.index
            + 1
        ).astype(str)
    )

    work = work.merge(
        cluster_counts[
            [
                "_grid_x",
                "_grid_y",
                "Cluster Cases",
                "Cluster ID",
            ]
        ],
        on=[
            "_grid_x",
            "_grid_y",
        ],
        how="left",
    )

    # Keep one point per cluster for display
    hotspot_points = (
        work
        .groupby(
            "Cluster ID",
            as_index=False,
        )
        .agg(
            {
                "_lat": "mean",
                "_lon": "mean",
                "Cluster Cases": "first",
            }
        )
    )

    if hotspot_points.empty:
        return hotspot_points

    max_cases = hotspot_points[
        "Cluster Cases"
    ].max()

    if max_cases <= 1:

        hotspot_points[
            "Hotspot Level"
        ] = "Low"

    else:

        def classify(value):

            ratio = (
                value
                / max_cases
            )

            if ratio >= 0.75:
                return "Very High"

            if ratio >= 0.50:
                return "High"

            if ratio >= 0.25:
                return "Moderate"

            return "Low"

        hotspot_points[
            "Hotspot Level"
        ] = hotspot_points[
            "Cluster Cases"
        ].apply(
            classify
        )

    return hotspot_points


# ============================================================
# HOTSPOT MAP
# ============================================================

def render_hotspot_map(
    df,
    title="Geographic Disease Hotspots",
):

    hotspots = create_hotspots(
        df,
        grid_size_m=500,
    )

    if hotspots.empty:

        st.info(
            "No valid Mumbai-area latitude/longitude "
            "records are available for hotspot mapping."
        )

        return

    show_labels = st.session_state.get(
        "show_data_labels",
        False,
    )

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=hotspots,
        get_position=[
            "_lon",
            "_lat",
        ],
        get_radius=350,
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

    text_layer = None

    if show_labels:

        text_layer = pdk.Layer(
            "TextLayer",
            data=hotspots,
            get_position=[
                "_lon",
                "_lat",
            ],
            get_text="Cluster Cases",
            get_size=16,
            get_color=[
                20,
                20,
                20,
            ],
            get_text_anchor="middle",
            get_alignment_baseline="center",
        )

    layers = [layer]

    if text_layer is not None:
        layers.append(
            text_layer
        )

    view_state = pdk.ViewState(
        latitude=19.0760,
        longitude=72.8777,
        zoom=10.5,
        pitch=0,
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip={
            "html": (
                "<b>Cluster:</b> {Cluster ID}"
                "<br/>"
                "<b>Cases:</b> {Cluster Cases}"
                "<br/>"
                "<b>Level:</b> {Hotspot Level}"
            )
        },
    )

    st.subheader(
        "🔥 Hotspot Map"
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
    )

    st.caption(
        f"Hotspot clusters identified: "
        f"{len(hotspots):,}"
    )

    return hotspots


# ============================================================
# WARD CHOROPLETH
# ============================================================

def render_ward_choropleth(
    geojson,
):

    if not geojson:

        st.warning(
            "BMC ward boundary data is unavailable."
        )

        return

    ward_table = create_ward_case_table(
        geojson
    )

    if ward_table.empty:

        st.info(
            "Ward-wise programme data could not "
            "be matched with BMC ward boundaries."
        )

        return

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        pickable=True,
        stroked=True,
        filled=True,
        extruded=False,
        get_fill_color=[
            200,
            200,
            200,
            130,
        ],
        get_line_color=[
            80,
            80,
            80,
            220,
        ],
        line_width_min_pixels=1,
        auto_highlight=True,
    )

    view_state = pdk.ViewState(
        latitude=19.0760,
        longitude=72.8777,
        zoom=10.5,
        pitch=0,
    )

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "html": (
                "<b>Ward:</b> {WARD_NO}"
                "<br/>"
                "<b>Programme Cases:</b> "
                "{Programme_Cases}"
            )
        },
    )

    st.subheader(
        "🎨 Ward-wise Programme Burden"
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
    )

    st.dataframe(
        ward_table,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# COMBINED MAP
# ============================================================

def render_combined_map(
    geojson,
    df,
):

    if not geojson:
        return

    hotspots = create_hotspots(
        df,
        grid_size_m=500,
    )

    ward_layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        pickable=True,
        stroked=True,
        filled=True,
        get_fill_color=[
            180,
            180,
            180,
            80,
        ],
        get_line_color=[
            70,
            70,
            70,
            220,
        ],
        line_width_min_pixels=1,
        auto_highlight=True,
    )

    layers = [
        ward_layer
    ]

    if not hotspots.empty:

        hotspot_layer = pdk.Layer(
            "ScatterplotLayer",
            data=hotspots,
            get_position=[
                "_lon",
                "_lat",
            ],
            get_radius=350,
            get_fill_color=[
                220,
                50,
                50,
                190,
            ],
            get_line_color=[
                70,
                20,
                20,
                230,
            ],
            line_width_min_pixels=1,
            pickable=True,
        )

        layers.append(
            hotspot_layer
        )

    view_state = pdk.ViewState(
        latitude=19.0760,
        longitude=72.8777,
        zoom=10.5,
        pitch=0,
    )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip={
            "html": (
                "<b>Ward:</b> {WARD_NO}"
                "<br/>"
                "<b>Programme Cases:</b> "
                "{Programme_Cases}"
                "<br/>"
                "<hr/>"
                "<b>Cluster Cases:</b> "
                "{Cluster Cases}"
                "<br/>"
                "<b>Hotspot Level:</b> "
                "{Hotspot Level}"
            )
        },
    )

    st.subheader(
        "🗺️ BMC Ward + Geographic Hotspots"
    )

    st.pydeck_chart(
        deck,
        use_container_width=True,
    )


# ============================================================
# DOWNLOAD HOTSPOT DATA
# ============================================================

def download_hotspot_data(
    df,
):

    hotspots = create_hotspots(
        df,
        grid_size_m=500,
    )

    if hotspots.empty:
        return

    export_df = hotspots.rename(
        columns={
            "_lat": "Latitude",
            "_lon": "Longitude",
        }
    )

    csv_bytes = export_df.to_csv(
        index=False
    ).encode(
        "utf-8"
    )

    st.download_button(
        label="⬇️ Download Hotspot Data",
        data=csv_bytes,
        file_name=(
            "Mumbai_Geographic_Hotspots.csv"
        ),
        mime="text/csv",
        use_container_width=False,
        key="download_geographic_hotspots",
    )


# ============================================================
# DOWNLOAD WARD DATA
# ============================================================

def download_ward_data(
    geojson,
):

    ward_table = create_ward_case_table(
        geojson
    )

    if ward_table.empty:
        return

    excel_buffer = io.BytesIO()

    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl",
    ) as writer:

        ward_table.to_excel(
            writer,
            index=False,
            sheet_name="Ward Summary",
        )

    excel_buffer.seek(0)

    st.download_button(
        label="⬇️ Download Ward Summary Excel",
        data=excel_buffer,
        file_name=(
            "Mumbai_Ward_Programme_Burden.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=False,
        key="download_geographic_ward_excel",
    )


# ============================================================
# MAIN GEOGRAPHIC MAP
# ============================================================

def render_geographic_map(
    df,
    selected_disease=None,
):

    st.header(
        "🗺️ Geographic Disease & Ward Analysis"
    )

    st.caption(
        "BMC administrative ward boundaries + "
        "programme disease hotspot analysis"
    )


    # --------------------------------------------------------
    # LOAD BMC WARDS
    # --------------------------------------------------------

    with st.spinner(
        "Loading BMC ward boundaries..."
    ):

        geojson, error = load_bmc_wards()


    if geojson is None:

        st.error(
            "BMC ward boundaries could not be loaded."
        )

        if error:
            st.caption(error)

        st.info(
            "The programme data and other dashboard "
            "sections are not affected."
        )

        return


    # --------------------------------------------------------
    # CHECK WARD COUNT
    # --------------------------------------------------------

    feature_count = len(
        geojson.get(
            "features",
            [],
        )
    )

    st.success(
        f"BMC GIS ward polygons loaded: "
        f"{feature_count}"
    )


    # --------------------------------------------------------
    # DISEASE SELECTION
    # --------------------------------------------------------

    disease_column = _find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
        ],
    )

    map_df = df.copy()


    if disease_column is not None:

        diseases = (
            map_df[disease_column]
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


        if len(diseases) > 1:

            disease_options = [
                "All Diseases"
            ] + diseases

            default_index = 0

            if (
                selected_disease
                and selected_disease in diseases
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


            if (
                selected_map_disease
                != "All Diseases"
            ):

                map_df = map_df[
                    map_df[disease_column]
                    .astype(str)
                    .str.strip()
                    == selected_map_disease
                ]

        elif len(diseases) == 1:

            selected_map_disease = diseases[0]

            st.info(
                f"Disease selected: "
                f"**{selected_map_disease}**"
            )


    if map_df.empty:

        st.warning(
            "No records available for the selected "
            "geographic map filters."
        )

        return


    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    ward_summary = prepare_ward_summary(
        map_df
    )

    hotspot_summary = create_hotspots(
        map_df,
        grid_size_m=500,
    )


    c1, c2, c3 = st.columns(3)


    with c1:

        st.metric(
            "Records for Map",
            f"{len(map_df):,}",
        )


    with c2:

        st.metric(
            "Wards with Records",
            f"{len(ward_summary):,}",
        )


    with c3:

        st.metric(
            "Hotspot Clusters",
            f"{len(hotspot_summary):,}",
        )


    st.divider()


    # --------------------------------------------------------
    # MAP TABS
    # --------------------------------------------------------

    tab1, tab2, tab3 = st.tabs(
        [
            "🔥 Hotspot Map",
            "🎨 Ward Choropleth",
            "🗺️ Ward + Hotspots",
        ]
    )


    # --------------------------------------------------------
    # HOTSPOT MAP
    # --------------------------------------------------------

    with tab1:

        render_hotspot_map(
            map_df
        )


    # --------------------------------------------------------
    # WARD MAP
    # --------------------------------------------------------

    with tab2:

        merged_geojson = merge_ward_cases(
            geojson,
            map_df,
        )

        render_ward_choropleth(
            merged_geojson
        )


    # --------------------------------------------------------
    # COMBINED MAP
    # --------------------------------------------------------

    with tab3:

        merged_geojson = merge_ward_cases(
            geojson,
            map_df,
        )

        render_combined_map(
            merged_geojson,
            map_df,
        )


    # --------------------------------------------------------
    # DOWNLOADS
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "⬇️ Geographic Analysis Downloads"
    )

    d1, d2 = st.columns(2)


    with d1:

        download_hotspot_data(
            map_df
        )


    with d2:

        merged_geojson = merge_ward_cases(
            geojson,
            map_df,
        )

        download_ward_data(
            merged_geojson
        )


    # --------------------------------------------------------
    # WARD SUMMARY
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "📊 Ward-wise Geographic Summary"
    )

    merged_geojson = merge_ward_cases(
        geojson,
        map_df,
    )

    ward_table = create_ward_case_table(
        merged_geojson
    )

    if not ward_table.empty:

        st.dataframe(
            ward_table,
            use_container_width=True,
            hide_index=True,
        )


    # --------------------------------------------------------
    # DATA QUALITY NOTE
    # --------------------------------------------------------

    valid_coordinates = prepare_coordinates(
        map_df
    )

    st.divider()

    st.info(
        f"Geographic mapping uses valid address "
        f"coordinates only. "
        f"Valid mapped records: "
        f"{len(valid_coordinates):,} / "
        f"{len(map_df):,}."
    )
