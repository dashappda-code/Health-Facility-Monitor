# geographic_map.py

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

BMC_WARD_URL = (
    "https://services8.arcgis.com/"
    "r6MmJtuWAzMawmJ8/arcgis/rest/services/"
    "BMConMaps_Nov26gdb/FeatureServer/24"
)

GRID_SIZE = 0.005


# ============================================================
# PROGRAMME MASTER WARDS
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
# HELPERS
# ============================================================

def clean_text(x):

    if pd.isna(x):
        return ""

    return str(x).strip()


def find_column(df, candidates):

    lookup = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for candidate in candidates:

        key = str(candidate).strip().lower()

        if key in lookup:
            return lookup[key]

    return None


def normalise_ward(x):

    x = clean_text(x).upper()

    if not x:
        return ""

    x = (
        x.replace("-", "/")
        .replace("_", "/")
        .replace(".", "")
    )

    x = " ".join(x.split())

    replacements = {

        "F NORTH": "FN",
        "F/NORTH": "FN",
        "F N": "FN",
        "FN": "FN",

        "F SOUTH": "FS",
        "F/SOUTH": "FS",
        "F S": "FS",
        "FS": "FS",

        "G NORTH": "GN",
        "G/NORTH": "GN",
        "G N": "GN",
        "GN": "GN",

        "G SOUTH": "GS",
        "G/SOUTH": "GS",
        "G S": "GS",
        "GS": "GS",

        "H EAST": "HE",
        "H/EAST": "HE",
        "H E": "HE",
        "HE": "HE",

        "H WEST": "HW",
        "H/WEST": "HW",
        "H W": "HW",
        "HW": "HW",

        "K EAST": "KE",
        "K/EAST": "KE",
        "K E": "KE",
        "KE": "KE",

        "K WEST": "KW",
        "K/WEST": "KW",
        "K W": "KW",
        "KW": "KW",

        "M EAST": "ME",
        "M/EAST": "ME",
        "M E": "ME",
        "ME": "ME",

        "M WEST": "MW",
        "M/WEST": "MW",
        "M W": "MW",
        "MW": "MW",

        "P EAST": "PE",
        "P/EAST": "PE",
        "P E": "PE",
        "PE": "PE",

        "P NORTH": "PN",
        "P/NORTH": "PN",
        "P N": "PN",
        "PN": "PN",

        "P SOUTH": "PS",
        "P/SOUTH": "PS",
        "P S": "PS",
        "PS": "PS",

        "R CENTRAL": "RC",
        "R/CENTRAL": "RC",
        "R C": "RC",
        "RC": "RC",

        "R NORTH": "RN",
        "R/NORTH": "RN",
        "R N": "RN",
        "RN": "RN",

        "R SOUTH": "RS",
        "R/SOUTH": "RS",
        "R S": "RS",
        "RS": "RS",
    }

    if x in replacements:
        return replacements[x]

    return x


# ============================================================
# LOAD BMC WARD BOUNDARIES
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

        if (
            isinstance(data, dict)
            and data.get("type") == "FeatureCollection"
            and data.get("features")
        ):

            return data, None

        return (
            None,
            "Ward boundary layer returned no features.",
        )

    except Exception as e:

        return None, str(e)


# ============================================================
# COORDINATES
# ============================================================

def prepare_coordinates(df):

    if df is None or df.empty:

        return (
            pd.DataFrame(),
            0,
            0,
        )

    if LAT_COL not in df.columns:

        return (
            pd.DataFrame(),
            len(df),
            0,
        )

    if LON_COL not in df.columns:

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

    invalid = (
        work["_lat"].isna()
        | work["_lon"].isna()
        | ~work["_lat"].between(-90, 90)
        | ~work["_lon"].between(-180, 180)
    )

    invalid_count = int(
        invalid.sum()
    )

    valid_count = int(
        (~invalid).sum()
    )

    # IMPORTANT:
    # No BMC/Mumbai restriction.
    # Every valid coordinate is retained.
    work = work[
        ~invalid
    ].copy()

    work.reset_index(
        drop=True,
        inplace=True,
    )

    return (
        work,
        invalid_count,
        valid_count,
    )


# ============================================================
# COORDINATE AVAILABILITY
# ============================================================

def coordinate_availability_text(
    total_records,
    valid_records,
    label,
):

    if total_records <= 0:

        return (
            f"{label}: 0 | "
            "Valid Address Coordinates: 0 (0.0%)"
        )

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
# HOTSPOTS
# ============================================================

def create_hotspots(df):

    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    work["_grid_lat"] = (
        work["_lat"]
        / GRID_SIZE
    ).apply(math.floor)

    work["_grid_lon"] = (
        work["_lon"]
        / GRID_SIZE
    ).apply(math.floor)

    work["Cluster ID"] = (
        "C_"
        + work["_grid_lat"].astype(str)
        + "_"
        + work["_grid_lon"].astype(str)
    )

    counts = (
        work.groupby(
            "Cluster ID"
        )
        .size()
        .rename(
            "Cluster Cases"
        )
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

    work[
        "Hotspot Classification"
    ] = (
        work["Cluster Cases"]
        .astype(int)
        .apply(classify)
    )

    return work


def cluster_summary(df):

    if df is None or df.empty:
        return pd.DataFrame()

    result = (
        df.groupby(
            "Cluster ID"
        )
        .agg(
            Latitude=(
                "_lat",
                "mean",
            ),
            Longitude=(
                "_lon",
                "mean",
            ),
            Cases=(
                "Cluster Cases",
                "max",
            ),
            Hotspot=(
                "Hotspot Classification",
                "first",
            ),
        )
        .reset_index()
    )

    return result.sort_values(
        "Cases",
        ascending=False,
    )


# ============================================================
# WARD SUMMARY — ALL 25 PROGRAMME WARDS
# ============================================================

def create_ward_summary(df):

    result = pd.DataFrame(
        {
            "Ward": PROGRAMME_WARDS,
            "Cases": 0,
        }
    )

    if df is None or df.empty:
        return result

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
        return result

    temp = df.copy()

    temp["_ward"] = (
        temp[ward_col]
        .apply(normalise_ward)
    )

    temp = temp[
        temp["_ward"] != ""
    ].copy()

    if temp.empty:
        return result

    counts = (
        temp.groupby(
            "_ward"
        )
        .size()
        .to_dict()
    )

    result["Cases"] = (
        result["Ward"]
        .map(counts)
        .fillna(0)
        .astype(int)
    )

    return result.sort_values(
        "Cases",
        ascending=False,
        kind="stable",
    ).reset_index(
        drop=True
    )


# ============================================================
# CHOROPLETH COLOUR
# ============================================================

def get_choropleth_color(
    value,
    maximum,
):

    if maximum <= 0:
        return [
            235,
            235,
            235,
            150,
        ]

    ratio = (
        value
        / maximum
    )

    if ratio >= 0.80:
        return [
            120,
            0,
            0,
            220,
        ]

    if ratio >= 0.60:
        return [
            190,
            30,
            30,
            210,
        ]

    if ratio >= 0.40:
        return [
            230,
            80,
            50,
            200,
        ]

    if ratio >= 0.20:
        return [
            250,
            170,
            50,
            190,
        ]

    if ratio > 0:
        return [
            255,
            225,
            100,
            180,
        ]

    return [
        235,
        235,
        235,
        130,
    ]


# ============================================================
# FIND WARD VALUE FROM BOUNDARY
# ============================================================

def get_geojson_ward_name(
    properties,
):

    possible_fields = [
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

    for key in possible_fields:

        if key in properties:

            value = properties[key]

            if clean_text(value):

                return normalise_ward(
                    value
                )

    return ""


# ============================================================
# PREPARE CHOROPLETH
# ============================================================

def prepare_bmc_choropleth(
    geojson,
    ward_summary,
):

    if geojson is None:
        return None

    output = {
        "type": "FeatureCollection",
        "features": [],
    }

    counts = {}

    if (
        ward_summary is not None
        and not ward_summary.empty
    ):

        counts = dict(
            zip(
                ward_summary["Ward"],
                ward_summary["Cases"],
            )
        )

    maximum = (
        max(counts.values())
        if counts
        else 0
    )

    for feature in geojson.get(
        "features",
        [],
    ):

        feature_copy = dict(
            feature
        )

        properties = dict(
            feature_copy.get(
                "properties",
                {},
            )
        )

        ward = get_geojson_ward_name(
            properties
        )

        cases = int(
            counts.get(
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
            if ward
            else "BMC Ward"
        )

        properties[
            "fill_color"
        ] = get_choropleth_color(
            cases,
            maximum,
        )

        # Strong black ward boundary
        properties[
            "line_color"
        ] = [
            20,
            20,
            20,
            255,
        ]

        feature_copy[
            "properties"
        ] = properties

        output[
            "features"
        ].append(
            feature_copy
        )

    return output


# ============================================================
# HOTSPOT MAP DATA
# ============================================================

def prepare_hotspot_display(
    hotspot_df,
):

    if (
        hotspot_df is None
        or hotspot_df.empty
    ):
        return pd.DataFrame()

    work = hotspot_df.copy()

    # Ward
    ward_col = find_column(
        work,
        [
            "Ward",
            "Ward Name",
            "Ward_Name",
            "WARD",
            "BMC Ward",
            "Administrative Ward",
        ],
    )

    if ward_col:

        work[
            "Map Ward"
        ] = work[
            ward_col
        ].apply(
            normalise_ward
        )

    else:

        work["Map Ward"] = ""

    # Disease
    disease_col = find_column(
        work,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
            "Disease Type",
        ],
    )

    if disease_col:

        work[
            "Map Disease"
        ] = work[
            disease_col
        ].astype(str)

    else:

        work["Map Disease"] = ""

    return work


# ============================================================
# MAP
# ============================================================

def show_map(
    hotspot_df=None,
    bmc_geojson=None,
    show_boundary=True,
    all_extent=False,
):

    layers = []

    # --------------------------------------------------------
    # BMC CHOROPLETH
    # --------------------------------------------------------

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
                    255,
                    0,
                    220,
                ],
            )
        )

    # --------------------------------------------------------
    # HOTSPOT POINTS
    # --------------------------------------------------------

    if (
        hotspot_df is not None
        and not hotspot_df.empty
    ):

        display_df = prepare_hotspot_display(
            hotspot_df
        )

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=display_df,

                get_position=[
                    "_lon",
                    "_lat",
                ],

                get_radius=90,

                get_fill_color=[
                    220,
                    30,
                    30,
                    190,
                ],

                get_line_color=[
                    70,
                    10,
                    10,
                    230,
                ],

                line_width_min_pixels=1,

                pickable=True,

                auto_highlight=True,
            )
        )

    # --------------------------------------------------------
    # VIEW
    # --------------------------------------------------------

    if (
        all_extent
        and hotspot_df is not None
        and not hotspot_df.empty
    ):

        latitude = float(
            hotspot_df[
                "_lat"
            ].mean()
        )

        longitude = float(
            hotspot_df[
                "_lon"
            ].mean()
        )

        zoom = 5.5

    else:

        latitude = 19.0760
        longitude = 72.8777
        zoom = 10

    deck = pdk.Deck(

        layers=layers,

        initial_view_state=pdk.ViewState(
            latitude=latitude,
            longitude=longitude,
            zoom=zoom,
            pitch=0,
            bearing=0,
        ),

        tooltip={
            "html": """
                <b>Ward:</b>
                {Map Ward}<br/>
                <b>Disease:</b>
                {Map Disease}<br/>
                <b>Cluster:</b>
                {Cluster ID}<br/>
                <b>Cluster Cases:</b>
                {Cluster Cases}<br/>
                <b>Hotspot:</b>
                {Hotspot Classification}
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
# EXPORT
# ============================================================

def download_hotspot_data(
    df,
):

    if df is None or df.empty:
        return None

    preferred = [
        "Cluster ID",
        "Cluster Cases",
        "Hotspot Classification",
        "Disease",
        "Disease Name",
        "Date",
        "Month",
        "Ward",
        "Ward Name",
        "Facility",
        "Facility Name",
        "Address",
        LAT_COL,
        LON_COL,
        "_lat",
        "_lon",
    ]

    columns = [
        c
        for c in preferred
        if c in df.columns
    ]

    output = df[
        columns
    ].copy()

    output.rename(
        columns={
            "_lat": "Latitude",
            "_lon": "Longitude",
            LAT_COL: "Latitude",
            LON_COL: "Longitude",
        },
        inplace=True,
    )

    return output


# ============================================================
# MAIN
# ============================================================

def render_geographic_map(
    filtered_df,
    total_df=None,
):

    st.header(
        "🗺️ Geographic Disease Management Map"
    )

    st.caption(
        "Global filters are applied first. "
        "The disease selector below controls only "
        "the geographic map, hotspots and choropleth."
    )

    # ========================================================
    # DATA
    # ========================================================

    if filtered_df is None:

        filtered_df = pd.DataFrame()

    if total_df is None:

        total_df = filtered_df.copy()

    total_records = len(
        total_df
    )

    selected_records = len(
        filtered_df
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
        valid_coordinate_count,
    ) = prepare_coordinates(
        filtered_df
    )

    # ========================================================
    # COORDINATE NOTE
    # ========================================================

    if global_filter_active:

        st.info(
            "📍 "
            + coordinate_availability_text(
                selected_records,
                valid_coordinate_count,
                "Selected Data",
            )
        )

    else:

        (
            total_coordinate_df,
            total_invalid_count,
            total_valid_coordinate_count,
        ) = prepare_coordinates(
            total_df
        )

        st.info(
            "📍 "
            + coordinate_availability_text(
                total_records,
                total_valid_coordinate_count,
                "Total Data",
            )
        )

    # ========================================================
    # NO COORDINATES
    # ========================================================

    if coordinate_df.empty:

        st.warning(
            "No valid latitude/longitude records "
            "are available for the current filters."
        )

        return

    # ========================================================
    # DISEASE COLUMN
    # ========================================================

    disease_col = find_column(
        coordinate_df,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
            "Disease Type",
        ],
    )

    # ========================================================
    # MAP-SPECIFIC DISEASE FILTER
    # ========================================================

    map_df = coordinate_df.copy()

    selected_disease = (
        "All Diseases"
    )

    diseases = []

    if disease_col:

        diseases = sorted(
            [
                clean_text(x)
                for x in coordinate_df[
                    disease_col
                ]
                .dropna()
                .unique()
                if clean_text(x)
            ]
        )

    if disease_col and diseases:

        disease_options = [
            "All Diseases"
        ] + diseases

        previous = st.session_state.get(
            "geo_map_disease",
            "All Diseases",
        )

        if previous not in disease_options:

            st.session_state[
                "geo_map_disease"
            ] = "All Diseases"

        selected_disease = st.selectbox(
            "🦠 Select Disease to Display on Map",
            disease_options,
            key="geo_map_disease",
            help=(
                "This selector affects only the "
                "geographic map. Global filters "
                "remain active."
            ),
        )

        if (
            selected_disease
            != "All Diseases"
        ):

            map_df = coordinate_df[
                coordinate_df[
                    disease_col
                ]
                .astype(str)
                .str.strip()
                == selected_disease
            ].copy()

    else:

        st.warning(
            "Disease column was not found "
            "in the selected data."
        )

    # ========================================================
    # MAP DATA STATUS
    # ========================================================

    st.caption(
        f"🌍 Map displaying: **{selected_disease}** "
        f"| Coordinate records: **{len(map_df):,}**"
    )

    if map_df.empty:

        st.info(
            "No coordinate records are available "
            "for the selected map disease."
        )

        return

    # ========================================================
    # HOTSPOTS
    # ========================================================

    hotspot_df = create_hotspots(
        map_df
    )

    summary = cluster_summary(
        hotspot_df
    )

    # ========================================================
    # WARD SUMMARY
    # ========================================================

    ward_summary = create_ward_summary(
        map_df
    )

    # ========================================================
    # BMC BOUNDARY
    # ========================================================

    bmc_geojson, bmc_error = (
        load_bmc_wards()
    )

    if bmc_error:

        st.warning(
            "BMC ward boundaries could not be loaded. "
            "Hotspot coordinates will still be displayed."
        )

    # ========================================================
    # CHOROPLETH
    # ========================================================

    choropleth_geojson = (
        prepare_bmc_choropleth(
            bmc_geojson,
            ward_summary,
        )
        if bmc_geojson is not None
        else None
    )

    # ========================================================
    # KPI
    # ========================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Map Disease Records",
        f"{len(map_df):,}",
    )

    c2.metric(
        "Programme Wards",
        "25",
    )

    c3.metric(
        "Hotspot Clusters",
        f"{len(summary):,}",
    )

    c4.metric(
        "Valid Coordinates",
        f"{len(map_df):,}",
    )

    # ========================================================
    # WARD COVERAGE
    # ========================================================

    wards_with_data = int(
        (ward_summary["Cases"] > 0)
        .sum()
    )

    wards_without_data = (
        25 - wards_with_data
    )

    st.caption(
        f"🏘️ Programme Ward Coverage: "
        f"**{wards_with_data}/25 wards** with data | "
        f"**{wards_without_data} wards** with no records "
        f"for current map selection."
    )

    st.divider()

    # ========================================================
    # MAP EXTENT
    # ========================================================

    extent = st.radio(
        "Map Extent",
        [
            "BMC / Mumbai Focus",
            "All Coordinates",
        ],
        horizontal=True,
        key="geo_extent",
    )

    all_extent = (
        extent
        == "All Coordinates"
    )

    # ========================================================
    # TABS
    # ========================================================

    tab1, tab2, tab3 = st.tabs(
        [
            "🔥 Disease Hotspots",
            "🏘️ Disease-wise BMC Choropleth",
            "🗺️ BMC + All Coordinates",
        ]
    )

    # ========================================================
    # TAB 1
    # ========================================================

    with tab1:

        st.subheader(
            f"🔥 {selected_disease} Geographic Hotspots"
        )

        show_map(
            hotspot_df=hotspot_df,
            bmc_geojson=None,
            show_boundary=False,
            all_extent=all_extent,
        )

        if summary.empty:

            st.info(
                "No hotspot clusters available."
            )

        else:

            st.subheader(
                "Hotspot Summary"
            )

            st.dataframe(
                summary,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # TAB 2
    # ========================================================

    with tab2:

        st.subheader(
            f"🏘️ Ward-wise Burden — "
            f"{selected_disease}"
        )

        st.caption(
            "Darker colour indicates higher case burden "
            "for the selected disease after applying "
            "global filters."
        )

        if choropleth_geojson is not None:

            show_map(
                hotspot_df=None,
                bmc_geojson=choropleth_geojson,
                show_boundary=True,
                all_extent=False,
            )

        else:

            st.info(
                "BMC ward boundary layer is unavailable."
            )

        # ----------------------------------------------------
        # 25 WARD TABLE
        # ----------------------------------------------------

        st.subheader(
            "📊 25-Ward Disease Burden"
        )

        st.dataframe(
            ward_summary,
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # PE NOTE
        # ----------------------------------------------------

        if (
            "PE" in ward_summary["Ward"].values
        ):

            pe_cases = int(
                ward_summary.loc[
                    ward_summary["Ward"]
                    == "PE",
                    "Cases",
                ].iloc[0]
            )

            if pe_cases > 0:

                st.info(
                    f"ℹ️ PE ward has {pe_cases:,} "
                    "records in the programme data. "
                    "PE is retained as a separate data ward. "
                    "If the geographic boundary source does "
                    "not contain a matching PE polygon, "
                    "no artificial polygon is created."
                )

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

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
            "⬇️ Download 25-Ward Disease Summary",
            data=buffer.getvalue(),
            file_name=(
                "25_Ward_Disease_Summary.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
        )

    # ========================================================
    # TAB 3
    # ========================================================

    with tab3:

        st.subheader(
            "🗺️ BMC Boundaries + All Valid Coordinates"
        )

        show_map(
            hotspot_df=hotspot_df,
            bmc_geojson=choropleth_geojson,
            show_boundary=True,
            all_extent=all_extent,
        )

        st.caption(
            "All valid latitude/longitude records are retained, "
            "including records outside BMC/Mumbai."
        )

    # ========================================================
    # EXPORT
    # ========================================================

    st.divider()

    st.subheader(
        "⬇️ Geographic Data Export"
    )

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
