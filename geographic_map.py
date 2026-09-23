import io
import re

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

BMC_WARD_URL = (
    "https://services8.arcgis.com/r6MmJtuWAzMawmJ8/arcgis/rest/services/"
    "BMConMaps_Nov26gdb/FeatureServer/24"
)

CARTO_DARK_STYLE = (
    "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
)

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


def find_column(
    df,
    candidates,
):
    if df is None or df.empty:
        return None

    normalized_columns = {
        re.sub(
            r"[^a-z0-9]+",
            "",
            str(column).lower(),
        ): column
        for column in df.columns
    }

    for candidate in candidates:
        normalized_candidate = re.sub(
            r"[^a-z0-9]+",
            "",
            str(candidate).lower(),
        )

        if normalized_candidate in normalized_columns:
            return normalized_columns[
                normalized_candidate
            ]

    return None


def normalise_ward(value):
    value = clean_text(value).upper()

    value = re.sub(
        r"\bWARD\b",
        "",
        value,
    )

    value = re.sub(
        r"[^A-Z0-9]+",
        "",
        value,
    )

    if value == "":
        return ""

    aliases = {
        "A": "A",
        "B": "B",
        "C": "C",
        "D": "D",
        "E": "E",
        "FN": "FN",
        "FS": "FS",
        "GN": "GN",
        "GS": "GS",
        "HE": "HE",
        "HW": "HW",
        "KE": "KE",
        "KW": "KW",
        "L": "L",
        "ME": "ME",
        "MW": "MW",
        "N": "N",
        "PE": "PE",
        "PN": "PN",
        "PS": "PS",
        "RC": "RC",
        "RN": "RN",
        "RS": "RS",
        "S": "S",
        "T": "T",
    }

    return aliases.get(
        value,
        value,
    )


def get_disease_column(df):
    return find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "DiseaseName",
            "Diagnosis",
            "Disease / Condition",
            "Disease/Condition",
        ],
    )


def get_ward_column(df):
    return find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "WardName",
            "BMC Ward",
            "BMC_Ward",
            "MCGM Ward",
            "Administrative Ward",
        ],
    )


def get_facility_column(df):
    return find_column(
        df,
        [
            "Facility",
            "Facility Name",
            "FacilityName",
            "Health Facility",
            "Health Facility Name",
            "Reporting Facility",
        ],
    )


def get_case_id_column(df):
    return find_column(
        df,
        [
            "Case ID",
            "CaseID",
            "ID",
            "Sr No",
            "Sr. No.",
            "Serial No",
            "Serial Number",
        ],
    )


# ============================================================
# GEOGRAPHIC DATA PREPARATION
# ============================================================

def prepare_coordinates(
    df,
):
    data = df.copy()

    if LAT_COL not in data.columns:
        data[LAT_COL] = pd.NA

    if LON_COL not in data.columns:
        data[LON_COL] = pd.NA

    data[LAT_COL] = pd.to_numeric(
        data[LAT_COL],
        errors="coerce",
    )

    data[LON_COL] = pd.to_numeric(
        data[LON_COL],
        errors="coerce",
    )

    data = data[
        data[LAT_COL].between(
            -90,
            90,
        )
        & data[LON_COL].between(
            -180,
            180,
        )
    ].copy()

    return data


def coordinate_availability_text(
    df,
):
    if df is None or df.empty:
        return "No records available."

    if (
        LAT_COL not in df.columns
        or LON_COL not in df.columns
    ):
        return "Latitude/Longitude columns are not available."

    lat = pd.to_numeric(
        df[LAT_COL],
        errors="coerce",
    )

    lon = pd.to_numeric(
        df[LON_COL],
        errors="coerce",
    )

    valid = (
        lat.notna()
        & lon.notna()
        & lat.between(
            -90,
            90,
        )
        & lon.between(
            -180,
            180,
        )
    )

    valid_count = int(valid.sum())
    total_count = len(df)

    if total_count == 0:
        return "No records available."

    percentage = (
        valid_count
        / total_count
        * 100
    )

    return (
        f"{valid_count:,} of {total_count:,} "
        f"records have valid coordinates "
        f"({percentage:.1f}%)."
    )


# ============================================================
# HOTSPOT DATA
# ============================================================

def create_hotspots(
    df,
):
    data = prepare_coordinates(
        df,
    )

    if data.empty:
        return pd.DataFrame()

    data["_grid_lat"] = (
        data[LAT_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    data["_grid_lon"] = (
        data[LON_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    hotspot = (
        data.groupby(
            [
                "_grid_lat",
                "_grid_lon",
            ],
            dropna=False,
        )
        .size()
        .reset_index(
            name="Cases",
        )
    )

    hotspot = hotspot.rename(
        columns={
            "_grid_lat": "Latitude",
            "_grid_lon": "Longitude",
        }
    )

    hotspot["Radius"] = (
        hotspot["Cases"]
        .clip(
            lower=1,
        )
        * 30
        + 50
    )

    return hotspot.sort_values(
        "Cases",
        ascending=False,
    ).reset_index(
        drop=True,
    )


def create_case_points(
    df,
):
    data = prepare_coordinates(
        df,
    )

    if data.empty:
        return pd.DataFrame()

    disease_column = get_disease_column(
        data,
    )

    ward_column = get_ward_column(
        data,
    )

    facility_column = get_facility_column(
        data,
    )

    result = data[
        [
            LAT_COL,
            LON_COL,
        ]
    ].copy()

    if disease_column:
        result["Disease"] = (
            data[disease_column]
            .astype(str)
        )
    else:
        result["Disease"] = "Unknown"

    if ward_column:
        result["Ward"] = (
            data[ward_column]
            .apply(
                normalise_ward,
            )
        )
    else:
        result["Ward"] = ""

    if facility_column:
        result["Facility"] = (
            data[facility_column]
            .astype(str)
        )
    else:
        result["Facility"] = ""

    return result


# ============================================================
# WARD SUMMARIES
# ============================================================

def create_ward_summary(
    df,
):
    ward_column = get_ward_column(
        df,
    )

    if not ward_column:
        return pd.DataFrame(
            columns=[
                "Ward",
                "Cases",
            ]
        )

    data = df.copy()

    data["_Ward"] = (
        data[ward_column]
        .apply(
            normalise_ward,
        )
    )

    data = data[
        data["_Ward"] != ""
    ]

    summary = (
        data.groupby(
            "_Ward",
            dropna=False,
        )
        .size()
        .reset_index(
            name="Cases",
        )
    )

    summary = summary.rename(
        columns={
            "_Ward": "Ward",
        }
    )

    return summary.sort_values(
        "Cases",
        ascending=False,
    ).reset_index(
        drop=True,
    )


def create_map_ward_summary(
    df,
):
    summary = create_ward_summary(
        df,
    )

    if summary.empty:
        return summary

    summary = summary.copy()

    summary["Map Ward"] = (
        summary["Ward"]
        .replace(
            {
                "PE": "P",
                "PN": "P",
            }
        )
    )

    summary = (
        summary.groupby(
            "Map Ward",
            as_index=False,
        )["Cases"]
        .sum()
    )

    summary = summary.rename(
        columns={
            "Map Ward": "Ward",
        }
    )

    return summary.sort_values(
        "Cases",
        ascending=False,
    ).reset_index(
        drop=True,
    )


# ============================================================
# BMC WARD GEOJSON
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
            "f": "geojson",
        }

        response = requests.get(
            BMC_WARD_URL + "/query",
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    except Exception:
        return None


def get_geojson_ward_name(
    properties,
):
    if not properties:
        return ""

    possible_columns = [
        "ward",
        "Ward",
        "WARD",
        "ward_name",
        "Ward_Name",
        "WardName",
        "name",
        "Name",
        "NAME",
    ]

    for column in possible_columns:
        if column in properties:
            value = normalise_ward(
                properties[column]
            )

            if value:
                return value

    for key, value in properties.items():
        key_normalized = re.sub(
            r"[^a-z0-9]+",
            "",
            str(key).lower(),
        )

        if (
            "ward" in key_normalized
            or key_normalized == "name"
        ):
            ward = normalise_ward(
                value,
            )

            if ward:
                return ward

    return ""


# ============================================================
# DISEASE PALETTES
# ============================================================

DISEASE_PALETTES = {
    "Malaria": [
        [255, 245, 235],
        [254, 230, 206],
        [253, 208, 162],
        [253, 174, 107],
        [230, 85, 13],
    ],
    "Dengue": [
        [240, 249, 232],
        [217, 240, 163],
        [166, 217, 106],
        [116, 196, 118],
        [35, 139, 69],
    ],
    "Chikungunya": [
        [239, 237, 245],
        [218, 218, 235],
        [188, 189, 220],
        [158, 154, 200],
        [117, 107, 177],
    ],
    "Typhoid": [
        [237, 248, 251],
        [204, 236, 230],
        [153, 216, 201],
        [65, 174, 118],
        [0, 109, 44],
    ],
}


def get_disease_palette(
    disease,
):
    disease = clean_text(
        disease,
    )

    if disease in DISEASE_PALETTES:
        return DISEASE_PALETTES[
            disease
        ]

    return [
        [239, 246, 255],
        [191, 219, 254],
        [147, 197, 253],
        [96, 165, 250],
        [37, 99, 235],
    ]


def get_choropleth_color(
    value,
    max_value,
    palette,
):
    if (
        value is None
        or pd.isna(value)
        or value <= 0
    ):
        return [
            230,
            230,
            230,
            80,
        ]

    if (
        max_value is None
        or max_value <= 0
    ):
        return [
            *palette[0],
            190,
        ]

    ratio = min(
        float(value)
        / float(max_value),
        1,
    )

    index = int(
        ratio
        * (
            len(palette)
            - 1
        )
    )

    index = max(
        0,
        min(
            index,
            len(palette) - 1,
        ),
    )

    return [
        *palette[index],
        210,
    ]


# ============================================================
# CHOROPLETH PREPARATION
# ============================================================

def prepare_bmc_choropleth(
    df,
    disease,
):
    ward_column = get_ward_column(
        df,
    )

    disease_column = get_disease_column(
        df,
    )

    if (
        not ward_column
        or not disease_column
    ):
        return None

    data = df.copy()

    data["_Ward"] = (
        data[ward_column]
        .apply(
            normalise_ward,
        )
    )

    data["_Disease"] = (
        data[disease_column]
        .apply(
            clean_text,
        )
    )

    selected_disease = clean_text(
        disease,
    )

    data = data[
        data["_Disease"].str.lower()
        == selected_disease.lower()
    ].copy()

    if data.empty:
        return None

    summary = (
        data.groupby(
            "_Ward",
            dropna=False,
        )
        .size()
        .reset_index(
            name="Cases",
        )
    )

    summary = summary.rename(
        columns={
            "_Ward": "Ward",
        }
    )

    return summary


# ============================================================
# DISEASE SELECTION
# ============================================================

def reset_geo_disease_selection():
    st.session_state[
        "geo_disease_selection"
    ] = []


def disease_selection_control(
    available_diseases,
):
    available_diseases = [
        clean_text(
            disease,
        )
        for disease in available_diseases
        if clean_text(
            disease,
        )
    ]

    available_diseases = list(
        dict.fromkeys(
            available_diseases
        )
    )

    if (
        "geo_disease_selection"
        not in st.session_state
    ):
        st.session_state[
            "geo_disease_selection"
        ] = []

    current_selection = (
        st.session_state[
            "geo_disease_selection"
        ]
    )

    current_selection = [
        disease
        for disease in current_selection
        if disease in available_diseases
    ]

    st.session_state[
        "geo_disease_selection"
    ] = current_selection

    return current_selection


# ============================================================
# WARD CHOROPLETH CHECKBOX CONTROL
# ============================================================

def reset_choropleth_selection():
    st.session_state[
        "geo_choropleth_selection"
    ] = []

    available_diseases = st.session_state.get(
        "geo_choropleth_available_diseases",
        [],
    )

    for disease in available_diseases:
        checkbox_key = (
            "geo_choro_checkbox_"
            + re.sub(
                r"[^A-Za-z0-9]+",
                "_",
                disease,
            )
        )

        st.session_state[
            checkbox_key
        ] = False


def choropleth_checkbox_callback(
    disease,
):
    checkbox_key = (
        "geo_choro_checkbox_"
        + re.sub(
            r"[^A-Za-z0-9]+",
            "_",
            disease,
        )
    )

    checked = st.session_state.get(
        checkbox_key,
        False,
    )

    current_selection = (
        st.session_state.get(
            "geo_choropleth_selection",
            [],
        )
    )

    current_selection = list(
        current_selection
    )

    if checked:
        if disease not in current_selection:
            if len(current_selection) >= 6:
                st.session_state[
                    checkbox_key
                ] = False

                st.session_state[
                    "geo_choropleth_limit_message"
                ] = (
                    "Maximum 6 diseases can be "
                    "selected at a time."
                )

                return

            current_selection.append(
                disease
            )

    else:
        if disease in current_selection:
            current_selection.remove(
                disease
            )

    st.session_state[
        "geo_choropleth_selection"
    ] = current_selection

    if (
        len(current_selection)
        <= 6
    ):
        st.session_state[
            "geo_choropleth_limit_message"
        ] = ""


def render_choropleth_disease_checkboxes(
    available_diseases,
):
    available_diseases = [
        clean_text(
            disease
        )
        for disease in available_diseases
        if clean_text(
            disease
        )
    ]

    available_diseases = list(
        dict.fromkeys(
            available_diseases
        )
    )

    st.session_state[
        "geo_choropleth_available_diseases"
    ] = available_diseases

    if (
        "geo_choropleth_selection"
        not in st.session_state
    ):
        st.session_state[
            "geo_choropleth_selection"
        ] = []

    current_selection = (
        st.session_state[
            "geo_choropleth_selection"
        ]
    )

    current_selection = [
        disease
        for disease in current_selection
        if disease in available_diseases
    ]

    st.session_state[
        "geo_choropleth_selection"
    ] = current_selection

    st.markdown(
        "#### Select Diseases to Display"
    )

    st.caption(
        "Select up to 6 diseases. "
        "Each selected disease will be displayed "
        "as a ward choropleth map with its ward-wise table."
    )

    # --------------------------------------------------------
    # CREATE CHECKBOXES IN SINGLE HORIZONTAL ROW
    # --------------------------------------------------------

    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"]:has(
            div[data-testid="stCheckbox"]
        ) {
            flex-wrap: nowrap !important;
            overflow-x: auto !important;
            gap: 8px !important;
            padding-bottom: 6px !important;
        }

        div[data-testid="stHorizontalBlock"]:has(
            div[data-testid="stCheckbox"]
        ) > div {
            min-width: max-content !important;
            flex: 0 0 auto !important;
        }

        div[data-testid="stCheckbox"] label {
            white-space: nowrap !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    checkbox_columns = st.columns(
        len(available_diseases),
        gap="small",
    )

    for column, disease in zip(
        checkbox_columns,
        available_diseases,
    ):
        checkbox_key = (
            "geo_choro_checkbox_"
            + re.sub(
                r"[^A-Za-z0-9]+",
                "_",
                disease,
            )
        )

        if checkbox_key not in st.session_state:
            st.session_state[
                checkbox_key
            ] = (
                disease
                in current_selection
            )

        with column:
            st.checkbox(
                disease,
                key=checkbox_key,
                on_change=(
                    choropleth_checkbox_callback
                ),
                args=(disease,),
            )

    selected = []

    for disease in available_diseases:
        checkbox_key = (
            "geo_choro_checkbox_"
            + re.sub(
                r"[^A-Za-z0-9]+",
                "_",
                disease,
            )
        )

        if st.session_state.get(
            checkbox_key,
            False,
        ):
            selected.append(
                disease
            )

    # Safety limit
    if len(selected) > 6:
        selected = selected[:6]

        for disease in available_diseases:
            checkbox_key = (
                "geo_choro_checkbox_"
                + re.sub(
                    r"[^A-Za-z0-9]+",
                    "_",
                    disease,
                )
            )

            st.session_state[
                checkbox_key
            ] = disease in selected

    st.session_state[
        "geo_choropleth_selection"
    ] = selected

    if st.session_state.get(
        "geo_choropleth_limit_message",
        "",
    ):
        st.warning(
            st.session_state[
                "geo_choropleth_limit_message"
            ]
        )

    st.markdown(
        f"**Selected: {len(selected)} / 6**"
    )

    return selected


# ============================================================
# MAP VIEW
# ============================================================

def calculate_view(
    df,
):
    data = prepare_coordinates(
        df,
    )

    if data.empty:
        return {
            "latitude": 19.0760,
            "longitude": 72.8777,
            "zoom": 10,
        }

    latitude = data[
        LAT_COL
    ].mean()

    longitude = data[
        LON_COL
    ].mean()

    return {
        "latitude": float(
            latitude
        ),
        "longitude": float(
            longitude
        ),
        "zoom": 10,
    }


def build_hotspot_map(
    hotspot_df,
    view_state,
):
    if (
        hotspot_df is None
        or hotspot_df.empty
    ):
        return None

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=hotspot_df,
        get_position=[
            "Longitude",
            "Latitude",
        ],
        get_radius="Radius",
        get_fill_color=[
            255,
            80,
            80,
            160,
        ],
        pickable=True,
        auto_highlight=True,
    )

    return pdk.Deck(
        map_style=CARTO_DARK_STYLE,
        initial_view_state=pdk.ViewState(
            latitude=view_state[
                "latitude"
            ],
            longitude=view_state[
                "longitude"
            ],
            zoom=view_state[
                "zoom"
            ],
        ),
        layers=[
            layer
        ],
        tooltip={
            "html": (
                "<b>Cases:</b> {Cases}"
            )
        },
    )


def build_choropleth_map(
    geojson,
    ward_summary,
    disease,
    view_state,
):
    if geojson is None:
        return None

    if (
        ward_summary is None
        or ward_summary.empty
    ):
        return None

    summary_lookup = dict(
        zip(
            ward_summary[
                "Ward"
            ],
            ward_summary[
                "Cases"
            ],
        )
    )

    max_value = (
        ward_summary[
            "Cases"
        ].max()
        if not ward_summary.empty
        else 0
    )

    palette = get_disease_palette(
        disease,
    )

    features = []

    for feature in geojson.get(
        "features",
        [],
    ):
        properties = feature.get(
            "properties",
            {},
        )

        ward_name = (
            get_geojson_ward_name(
                properties,
            )
        )

        map_ward = ward_name

        if ward_name in [
            "PE",
            "PN",
        ]:
            map_ward = "P"

        cases = summary_lookup.get(
            map_ward,
            0,
        )

        properties = dict(
            properties
        )

        properties[
            "Programme_Ward"
        ] = ward_name

        properties[
            "Cases"
        ] = cases

        properties[
            "Disease"
        ] = disease

        properties[
            "FillColor"
        ] = get_choropleth_color(
            cases,
            max_value,
            palette,
        )

        features.append(
            {
                "type": "Feature",
                "geometry": feature.get(
                    "geometry"
                ),
                "properties": properties,
            }
        )

    enriched_geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=enriched_geojson,
        pickable=True,
        stroked=True,
        filled=True,
        get_fill_color=(
            "properties.FillColor"
        ),
        get_line_color=[
            255,
            255,
            255,
            100,
        ],
        line_width_min_pixels=1,
        auto_highlight=True,
    )

    return pdk.Deck(
        map_style=CARTO_DARK_STYLE,
        initial_view_state=pdk.ViewState(
            latitude=view_state[
                "latitude"
            ],
            longitude=view_state[
                "longitude"
            ],
            zoom=view_state[
                "zoom"
            ],
        ),
        layers=[
            layer
        ],
        tooltip={
            "html": (
                "<b>Ward:</b> "
                "{Programme_Ward}<br/>"
                "<b>Disease:</b> "
                "{Disease}<br/>"
                "<b>Cases:</b> "
                "{Cases}"
            )
        },
    )


def build_combined_map(
    case_points,
    geojson,
    ward_summary,
    view_state,
):
    layers = []

    if (
        geojson is not None
        and ward_summary is not None
        and not ward_summary.empty
    ):
        summary_lookup = dict(
            zip(
                ward_summary[
                    "Ward"
                ],
                ward_summary[
                    "Cases"
                ],
            )
        )

        max_value = (
            ward_summary[
                "Cases"
            ].max()
        )

        features = []

        for feature in geojson.get(
            "features",
            [],
        ):
            properties = feature.get(
                "properties",
                {},
            )

            ward_name = (
                get_geojson_ward_name(
                    properties,
                )
            )

            map_ward = ward_name

            if ward_name in [
                "PE",
                "PN",
            ]:
                map_ward = "P"

            cases = summary_lookup.get(
                map_ward,
                0,
            )

            properties = dict(
                properties
            )

            properties[
                "Programme_Ward"
            ] = ward_name

            properties[
                "Cases"
            ] = cases

            ratio = (
                cases / max_value
                if max_value
                else 0
            )

            properties[
                "FillColor"
            ] = [
                int(
                    255
                    * ratio
                ),
                int(
                    180
                    * (
                        1
                        - ratio
                    )
                ),
                80,
                120,
            ]

            features.append(
                {
                    "type": "Feature",
                    "geometry": feature.get(
                        "geometry"
                    ),
                    "properties": properties,
                }
            )

        combined_geojson = {
            "type": "FeatureCollection",
            "features": features,
        }

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=combined_geojson,
                pickable=True,
                stroked=True,
                filled=True,
                get_fill_color=(
                    "properties.FillColor"
                ),
                get_line_color=[
                    255,
                    255,
                    255,
                    100,
                ],
                line_width_min_pixels=1,
            )
        )

    if (
        case_points is not None
        and not case_points.empty
    ):
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=case_points,
                get_position=[
                    LON_COL,
                    LAT_COL,
                ],
                get_radius=45,
                get_fill_color=[
                    255,
                    255,
                    255,
                    180,
                ],
                pickable=True,
                auto_highlight=True,
            )
        )

    if not layers:
        return None

    return pdk.Deck(
        map_style=CARTO_DARK_STYLE,
        initial_view_state=pdk.ViewState(
            latitude=view_state[
                "latitude"
            ],
            longitude=view_state[
                "longitude"
            ],
            zoom=view_state[
                "zoom"
            ],
        ),
        layers=layers,
        tooltip={
            "html": (
                "<b>Ward:</b> "
                "{Programme_Ward}<br/>"
                "<b>Cases:</b> "
                "{Cases}"
            )
        },
    )


# ============================================================
# DISEASE COMPARISON
# ============================================================

def create_disease_comparison(
    df,
):
    disease_column = get_disease_column(
        df,
    )

    if not disease_column:
        return pd.DataFrame()

    comparison = (
        df[disease_column]
        .apply(
            clean_text,
        )
        .replace(
            "",
            pd.NA,
        )
        .dropna()
        .value_counts()
        .reset_index()
    )

    comparison.columns = [
        "Disease",
        "Cases",
    ]

    return comparison


def get_disease_map_data(
    df,
    disease,
):
    disease_column = get_disease_column(
        df,
    )

    ward_column = get_ward_column(
        df,
    )

    if (
        not disease_column
        or not ward_column
    ):
        return pd.DataFrame()

    data = df.copy()

    data["_Disease"] = (
        data[disease_column]
        .apply(
            clean_text,
        )
    )

    data["_Ward"] = (
        data[ward_column]
        .apply(
            normalise_ward,
        )
    )

    selected_disease = clean_text(
        disease,
    )

    data = data[
        data["_Disease"].str.lower()
        == selected_disease.lower()
    ]

    if data.empty:
        return pd.DataFrame()

    return (
        data.groupby(
            "_Ward",
            dropna=False,
        )
        .size()
        .reset_index(
            name="Cases",
        )
        .rename(
            columns={
                "_Ward": "Ward",
            }
        )
        .sort_values(
            "Cases",
            ascending=False,
        )
        .reset_index(
            drop=True,
        )
    )


# ============================================================
# EXPORTS
# ============================================================

def download_hotspot_data(
    hotspot_df,
):
    if (
        hotspot_df is None
        or hotspot_df.empty
    ):
        return

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        hotspot_df.to_excel(
            writer,
            index=False,
            sheet_name="Hotspots",
        )

    output.seek(0)

    st.download_button(
        label="Download Hotspot Data",
        data=output,
        file_name="geographic_hotspots.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


def download_choropleth_data(
    choropleth_data,
    disease,
):
    if (
        choropleth_data is None
        or choropleth_data.empty
    ):
        return

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        choropleth_data.to_excel(
            writer,
            index=False,
            sheet_name="Ward_Choropleth",
        )

    output.seek(0)

    safe_disease = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        clean_text(
            disease
        ),
    ).strip(
        "_"
    )

    st.download_button(
        label=(
            f"Download {disease} Ward Data"
        ),
        data=output,
        file_name=(
            f"{safe_disease}_ward_choropleth.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_geographic_map(
    filtered_df,
    df,
):
    st.markdown(
        "## Geographic Programme Analysis"
    )

    st.caption(
        "Facility-wise, ward-wise and disease-wise "
        "geographic distribution of reported cases."
    )

    if (
        filtered_df is None
        or filtered_df.empty
    ):
        st.info(
            "No data available for the selected filters."
        )
        return

    data = filtered_df.copy()

    disease_column = get_disease_column(
        data,
    )

    ward_column = get_ward_column(
        data,
    )

    facility_column = get_facility_column(
        data,
    )

    if disease_column:
        available_diseases = sorted(
            [
                disease
                for disease in (
                    data[disease_column]
                    .apply(
                        clean_text,
                    )
                    .unique()
                )
                if disease
            ]
        )
    else:
        available_diseases = []

    ward_summary = create_ward_summary(
        data,
    )

    map_ward_summary = (
        create_map_ward_summary(
            data,
        )
    )

    case_points = create_case_points(
        data,
    )

    hotspot_df = create_hotspots(
        data,
    )

    view_state = calculate_view(
        data,
    )

    geojson = load_bmc_wards()

    # ========================================================
    # KPI ROW
    # ========================================================

    total_cases = len(data)

    total_wards = (
        ward_summary[
            "Ward"
        ].nunique()
        if not ward_summary.empty
        else 0
    )

    total_facilities = (
        data[
            facility_column
        ]
        .apply(
            clean_text,
        )
        .replace(
            "",
            pd.NA,
        )
        .dropna()
        .nunique()
        if facility_column
        else 0
    )

    top_ward = (
        ward_summary.iloc[0]["Ward"]
        if not ward_summary.empty
        else "N/A"
    )

    top_ward_cases = (
        int(
            ward_summary.iloc[0][
                "Cases"
            ]
        )
        if not ward_summary.empty
        else 0
    )

    kpi1, kpi2, kpi3, kpi4 = st.columns(
        4
    )

    with kpi1:
        st.metric(
            "Total Cases",
            f"{total_cases:,}",
        )

    with kpi2:
        st.metric(
            "Wards Covered",
            f"{total_wards:,}",
        )

    with kpi3:
        st.metric(
            "Facilities Covered",
            f"{total_facilities:,}",
        )

    with kpi4:
        st.metric(
            "Top Ward",
            (
                f"{top_ward} "
                f"({top_ward_cases:,})"
            ),
        )

    st.info(
        coordinate_availability_text(
            data
        )
    )

    # ========================================================
    # VIEW SELECTION
    # ========================================================

    active_view = st.radio(
        "Select Geographic View",
        [
            "Hotspots",
            "Disease Comparison",
            "Ward Choropleth",
            "Combined Geographic View",
        ],
        horizontal=True,
        key="geo_active_view",
    )

    # ========================================================
    # HOTSPOTS
    # ========================================================

    if active_view == "Hotspots":
        st.markdown(
            "### Geographic Hotspots"
        )

        if hotspot_df.empty:
            st.warning(
                "No valid coordinate data available "
                "for hotspot mapping."
            )
        else:
            hotspot_map = build_hotspot_map(
                hotspot_df,
                view_state,
            )

            if hotspot_map:
                st.pydeck_chart(
                    hotspot_map,
                    use_container_width=True,
                )

            st.markdown(
                "#### Hotspot Summary"
            )

            display_hotspot = hotspot_df.copy()

            display_hotspot[
                "Latitude"
            ] = display_hotspot[
                "Latitude"
            ].round(5)

            display_hotspot[
                "Longitude"
            ] = display_hotspot[
                "Longitude"
            ].round(5)

            st.dataframe(
                display_hotspot,
                use_container_width=True,
                hide_index=True,
            )

            download_hotspot_data(
                hotspot_df
            )

    # ========================================================
    # DISEASE COMPARISON
    # ========================================================

    elif active_view == "Disease Comparison":
        st.markdown(
            "### Disease-wise Geographic Comparison"
        )

        comparison = (
            create_disease_comparison(
                data
            )
        )

        if comparison.empty:
            st.warning(
                "Disease information is not available."
            )
        else:
            st.dataframe(
                comparison,
                use_container_width=True,
                hide_index=True,
            )

            selected_disease = st.selectbox(
                "Select Disease",
                comparison[
                    "Disease"
                ].tolist(),
                key="geo_comparison_disease",
            )

            disease_map_data = (
                get_disease_map_data(
                    data,
                    selected_disease,
                )
            )

            if (
                not disease_map_data.empty
                and geojson is not None
            ):
                choropleth_map = (
                    build_choropleth_map(
                        geojson,
                        disease_map_data,
                        selected_disease,
                        view_state,
                    )
                )

                if choropleth_map:
                    st.pydeck_chart(
                        choropleth_map,
                        use_container_width=True,
                    )

            st.markdown(
                f"#### {selected_disease} Ward-wise Summary"
            )

            st.dataframe(
                disease_map_data,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # WARD CHOROPLETH
    # ========================================================

    elif active_view == "Ward Choropleth":
        st.markdown(
            "### Ward-wise Disease Choropleth"
        )

        if not available_diseases:
            st.warning(
                "No disease information is available."
            )
            return

        selected_diseases = (
            render_choropleth_disease_checkboxes(
                available_diseases
            )
        )

        if not selected_diseases:
            st.info(
                "Select one or more diseases to display "
                "ward-wise choropleth maps."
            )
            return

        if geojson is None:
            st.warning(
                "BMC ward boundary data could not be loaded."
            )
            return

        # ----------------------------------------------------
        # DISPLAY SELECTED DISEASE MAPS
        # ----------------------------------------------------

        for row_start in range(
            0,
            len(selected_diseases),
            2,
        ):
            row_diseases = (
                selected_diseases[
                    row_start:row_start + 2
                ]
            )

            columns = st.columns(
                2
            )

            for column, disease in zip(
                columns,
                row_diseases,
            ):
                disease_data = (
                    prepare_bmc_choropleth(
                        data,
                        disease,
                    )
                )

                with column:
                    st.markdown(
                        f"#### {disease}"
                    )

                    if (
                        disease_data is None
                        or disease_data.empty
                    ):
                        st.info(
                            "No data available "
                            "for this disease."
                        )
                        continue

                    disease_map = (
                        build_choropleth_map(
                            geojson,
                            disease_data,
                            disease,
                            view_state,
                        )
                    )

                    if disease_map:
                        st.pydeck_chart(
                            disease_map,
                            use_container_width=True,
                        )

                    st.dataframe(
                        disease_data,
                        use_container_width=True,
                        hide_index=True,
                    )

                    download_choropleth_data(
                        disease_data,
                        disease,
                    )

    # ========================================================
    # COMBINED GEOGRAPHIC VIEW
    # ========================================================

    elif active_view == "Combined Geographic View":
        st.markdown(
            "### Combined Geographic View"
        )

        if (
            geojson is None
            and case_points.empty
        ):
            st.warning(
                "No geographic data available."
            )
            return

        combined_map = build_combined_map(
            case_points,
            geojson,
            map_ward_summary,
            view_state,
        )

        if combined_map:
            st.pydeck_chart(
                combined_map,
                use_container_width=True,
            )

        st.markdown(
            "#### Ward-wise Case Summary"
        )

        if map_ward_summary.empty:
            st.info(
                "No ward-wise summary available."
            )
        else:
            st.dataframe(
                map_ward_summary,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # FOOTNOTE
    # ========================================================

    st.caption(
        "Geographic visualisations are based on the "
        "available ward, facility, disease and coordinate "
        "information in the selected dataset."
    )
