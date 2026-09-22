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
# DISEASE COLOUR PALETTES
# ============================================================

DISEASE_COLOUR_PALETTES = [
    {
        "name": "Blue",
        "low": [219, 234, 254, 190],
        "high": [30, 64, 175, 235],
        "point": [37, 99, 235, 225],
        "line": [30, 64, 175, 255],
    },
    {
        "name": "Green",
        "low": [220, 252, 231, 190],
        "high": [21, 128, 61, 235],
        "point": [22, 163, 74, 225],
        "line": [21, 128, 61, 255],
    },
    {
        "name": "Purple",
        "low": [243, 232, 255, 190],
        "high": [126, 34, 206, 235],
        "point": [147, 51, 234, 225],
        "line": [107, 33, 168, 255],
    },
    {
        "name": "Orange",
        "low": [255, 237, 213, 190],
        "high": [194, 65, 12, 235],
        "point": [234, 88, 12, 225],
        "line": [154, 52, 18, 255],
    },
    {
        "name": "Teal",
        "low": [204, 251, 241, 190],
        "high": [15, 118, 110, 235],
        "point": [13, 148, 136, 225],
        "line": [15, 118, 110, 255],
    },
    {
        "name": "Pink",
        "low": [252, 231, 243, 190],
        "high": [190, 24, 93, 235],
        "point": [219, 39, 119, 225],
        "line": [157, 23, 77, 255],
    },
    {
        "name": "Brown",
        "low": [245, 236, 220, 190],
        "high": [120, 53, 15, 235],
        "point": [146, 64, 14, 225],
        "line": [101, 45, 10, 255],
    },
    {
        "name": "Cyan",
        "low": [207, 250, 254, 190],
        "high": [8, 145, 178, 235],
        "point": [8, 145, 178, 225],
        "line": [14, 116, 144, 255],
    },
]


def get_disease_palette(disease, diseases):
    if not diseases:
        return DISEASE_COLOUR_PALETTES[0]

    try:
        index = diseases.index(disease)
    except ValueError:
        index = 0

    return DISEASE_COLOUR_PALETTES[
        index % len(DISEASE_COLOUR_PALETTES)
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
# FACILITY COLUMN
# ============================================================

def get_facility_column(df):
    return find_column(
        df,
        [
            "Facility",
            "Facility Name",
            "Facility_Name",
            "FacilityName",
            "Health Facility",
            "Health_Facility",
        ],
    )


# ============================================================
# COORDINATE PREPARATION
# ============================================================

def prepare_coordinates(df):

    if df is None or df.empty:
        return pd.DataFrame(), 0, 0

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame(), len(df), 0

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

    valid_df = work.loc[valid].copy()

    invalid_count = int((~valid).sum())
    valid_count = int(valid.sum())

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
# WARD-WISE HOTSPOT CREATION
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

    disease_col = get_disease_column(work)
    ward_col = get_ward_column(work)

    if "_Report_Ward" in work.columns:
        work["_Hotspot_Ward"] = (
            work["_Report_Ward"]
            .apply(normalise_ward)
        )
    elif ward_col is not None:
        work["_Hotspot_Ward"] = (
            work[ward_col]
            .apply(normalise_ward)
        )
    else:
        work["_Hotspot_Ward"] = "Unknown"

    if disease_col is not None:
        work["_Hotspot_Disease"] = (
            work[disease_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        work["_Hotspot_Disease"] = ""

    group_columns = [
        "_Hotspot_Ward",
        "_Hotspot_Disease",
    ]

    summary = (
        work
        .groupby(
            group_columns,
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

    summary = summary.rename(
        columns={
            "_Hotspot_Ward": "Ward",
            "_Hotspot_Disease": "Disease",
        }
    )

    summary["Cluster ID"] = (
        summary["Ward"].astype(str)
        + "_"
        + summary["Disease"].astype(str)
    )

    def classify(cases):
        if cases >= 10:
            return "High"

        if cases >= 5:
            return "Moderate"

        return "Low"

    summary["Hotspot Classification"] = (
        summary["Cluster_Cases"]
        .apply(classify)
    )

    max_cases = (
        summary["Cluster_Cases"].max()
        if not summary.empty
        else 0
    )

    if max_cases and max_cases > 0:
        summary["Burden_Ratio"] = (
            summary["Cluster_Cases"]
            / float(max_cases)
        )
    else:
        summary["Burden_Ratio"] = 0.0

    summary["Display_Radius"] = (
        35
        + summary["Burden_Ratio"]
        * 75
    )

    summary["Display_Radius"] = (
        summary["Display_Radius"]
        .clip(
            lower=35,
            upper=110,
        )
        .astype(float)
    )

    summary["Ward_Rank"] = (
        summary["Cluster_Cases"]
        .rank(
            method="dense",
            ascending=False,
        )
        .astype(int)
    )

    return summary


# ============================================================
# CASE POINT PREPARATION
# ============================================================

def create_case_points(
    df,
    hotspot_df=None,
):

    if df is None or df.empty:
        return pd.DataFrame()

    if (
        "_lat" not in df.columns
        or "_lon" not in df.columns
    ):
        return pd.DataFrame()

    work = df.copy()

    disease_col = get_disease_column(work)
    ward_col = get_ward_column(work)
    facility_col = get_facility_column(work)

    if "_Report_Ward" in work.columns:
        work["Ward"] = (
            work["_Report_Ward"]
            .apply(normalise_ward)
        )
    elif ward_col is not None:
        work["Ward"] = (
            work[ward_col]
            .apply(normalise_ward)
        )
    else:
        work["Ward"] = "Unknown"

    if disease_col is not None:
        work["Disease"] = (
            work[disease_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        work["Disease"] = ""

    if facility_col is not None:
        work["Facility"] = (
            work[facility_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        work["Facility"] = ""

    case_id_col = find_column(
        work,
        [
            "Case ID",
            "Case_ID",
            "CaseID",
            "Patient ID",
            "Patient_ID",
            "ID",
        ],
    )

    if case_id_col is not None:
        work["CaseID"] = (
            work[case_id_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        work["CaseID"] = (
            work.index.astype(str)
        )

    if (
        hotspot_df is not None
        and not hotspot_df.empty
        and "Cluster ID" in hotspot_df.columns
    ):
        hotspot_lookup = (
            hotspot_df[
                [
                    "Ward",
                    "Disease",
                    "Cluster Cases",
                ]
            ].copy()
            if (
                "Ward" in hotspot_df.columns
                and "Disease" in hotspot_df.columns
                and "Cluster Cases" in hotspot_df.columns
            )
            else pd.DataFrame()
        )

        if not hotspot_lookup.empty:
            hotspot_lookup["Hotspot_Key"] = (
                hotspot_lookup["Ward"].astype(str)
                + "||"
                + hotspot_lookup["Disease"].astype(str)
            )

            hotspot_case_map = dict(
                zip(
                    hotspot_lookup["Hotspot_Key"],
                    hotspot_lookup["Cluster Cases"],
                )
            )
        else:
            hotspot_case_map = {}
    else:
        hotspot_case_map = {}

    work["Hotspot_Key"] = (
        work["Ward"].astype(str)
        + "||"
        + work["Disease"].astype(str)
    )

    work["Cluster Cases"] = (
        work["Hotspot_Key"]
        .map(hotspot_case_map)
        .fillna(0)
        .astype(int)
    )

    work["PN_Hotspot"] = (
        (work["Ward"] == "PN")
        & (work["Cluster Cases"] > 0)
    )

    work["Hotspot Classification"] = (
        work["Cluster Cases"]
        .apply(
            lambda x:
            "High" if x >= 10
            else (
                "Moderate"
                if x >= 5
                else (
                    "Low"
                    if x > 0
                    else ""
                )
            )
        )
    )

    work["Point_Radius"] = 28.0
    work["Highlight_Radius"] = 65.0

    work["Ward Display"] = (
        work["Ward"]
    )

    work["Hotspot Status"] = (
        work["PN_Hotspot"]
        .map(
            {
                True: "PN case inside hotspot",
                False: "",
            }
        )
    )

    return work[
        [
            "_lat",
            "_lon",
            "Ward",
            "Ward Display",
            "Disease",
            "Facility",
            "CaseID",
            "Cluster Cases",
            "Hotspot Classification",
            "PN_Hotspot",
            "Hotspot Status",
            "Point_Radius",
            "Highlight_Radius",
        ]
    ].copy()


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):

    summary = pd.DataFrame(
        {
            "Ward": PROGRAMME_WARDS
        }
    )

    if df is None or df.empty:
        summary["Cases"] = 0
        return summary

    if "_Report_Ward" in df.columns:
        work = df.copy()
        work["_Programme_Ward"] = (
            work["_Report_Ward"]
            .apply(normalise_ward)
        )
    else:
        ward_col = get_ward_column(df)

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
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    return summary


# ============================================================
# PE + PN COMBINED CHOROPLETH SUMMARY
# ============================================================

def create_map_ward_summary(df):

    summary = create_ward_summary(df)

    if summary.empty:
        return summary

    pe_cases = int(
        summary.loc[
            summary["Ward"] == "PE",
            "Cases",
        ].sum()
    )

    pn_cases = int(
        summary.loc[
            summary["Ward"] == "PN",
            "Cases",
        ].sum()
    )

    other = summary[
        ~summary["Ward"].isin(
            ["PE", "PN"]
        )
    ].copy()

    combined_p = pd.DataFrame(
        {
            "Ward": ["P"],
            "Cases": [
                pe_cases + pn_cases
            ],
        }
    )

    result = pd.concat(
        [
            other,
            combined_p,
        ],
        ignore_index=True,
    )

    return result


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
# DISEASE-SPECIFIC CHOROPLETH COLOR
# ============================================================

def get_choropleth_color(
    cases,
    max_cases,
    palette,
):

    try:
        cases = float(cases)
        max_cases = float(max_cases)

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
        return palette["low"]

    ratio = min(
        max(
            cases / max_cases,
            0,
        ),
        1,
    )

    low = palette["low"]
    high = palette["high"]

    return [
        int(
            low[i]
            + (
                high[i]
                - low[i]
            )
            * ratio
        )
        for i in range(4)
    ]


# ============================================================
# PREPARE CHOROPLETH
# ============================================================

def prepare_bmc_choropleth(
    geojson,
    ward_summary,
    disease=None,
    diseases=None,
):

    if not geojson:
        return None

    if "features" not in geojson:
        return None

    if ward_summary is None:
        return None

    if diseases is None:
        diseases = []

    palette = get_disease_palette(
        disease,
        diseases,
    )

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

    features = geojson["features"]

    canonical_p_index = None

    for idx, feature in enumerate(
        features
    ):
        properties = (
            feature.get("properties")
            or {}
        )

        ward = get_geojson_ward_name(
            properties
        )

        if ward == "P":
            canonical_p_index = idx
            break

    if canonical_p_index is None:
        for preferred in [
            "PN",
            "PE",
        ]:
            for idx, feature in enumerate(
                features
            ):
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

                if ward == preferred:
                    canonical_p_index = idx
                    break

            if canonical_p_index is not None:
                break

    new_features = []

    for idx, feature in enumerate(
        features
    ):

        properties = (
            feature.get("properties")
            or {}
        )

        ward = get_geojson_ward_name(
            properties
        )

        map_ward = (
            "P"
            if ward in ["PE", "PN"]
            else ward
        )

        if map_ward == "P":
            if (
                canonical_p_index is not None
                and idx != canonical_p_index
            ):
                cases = 0
            else:
                cases = int(
                    ward_cases.get(
                        "P",
                        0,
                    )
                )
        else:
            cases = int(
                ward_cases.get(
                    map_ward,
                    0,
                )
            )

        properties["ProgrammeCases"] = (
            cases
        )

        if map_ward == "P":
            properties["WardDisplay"] = (
                "P (PE + PN)"
            )
        else:
            properties["WardDisplay"] = (
                ward or "Unknown"
            )

        properties["DiseaseDisplay"] = (
            disease
            if disease
            else "Selected Disease(s)"
        )

        properties["fill_color"] = (
            get_choropleth_color(
                cases,
                max_cases,
                palette,
            )
        )

        properties["line_color"] = [
            20,
            20,
            20,
            255,
        ]

        feature["properties"] = (
            properties
        )

        new_features.append(
            feature
        )

    return {
        "type": "FeatureCollection",
        "features": new_features,
    }


# ============================================================
# DISEASE SELECTION
# ============================================================

def get_selected_diseases(
    diseases
):

    if not diseases:
        return []

    current = st.session_state.get(
        "geo_disease_selection",
        [],
    )

    current = [
        disease
        for disease in current
        if disease in diseases
    ]

    if (
        "geo_disease_signature"
        not in st.session_state
        or st.session_state[
            "geo_disease_signature"
        ]
        != "||".join(diseases)
    ):

        st.session_state[
            "geo_disease_signature"
        ] = "||".join(diseases)

        current = list(diseases)

    st.session_state[
        "geo_disease_selection"
    ] = current

    return current


def render_disease_selector(
    diseases
):

    selected = get_selected_diseases(
        diseases
    )

    left, middle, right = st.columns(
        [1.55, 0.25, 0.20],
        gap="small",
    )

    with left:

        selected = st.multiselect(
            "Disease Selection",
            options=diseases,
            default=selected,
            key="geo_disease_multiselect",
            placeholder="Select disease(s)",
        )

        st.session_state[
            "geo_disease_selection"
        ] = selected

    with middle:

        select_all = st.checkbox(
            "All",
            value=(
                len(selected)
                == len(diseases)
                and len(diseases) > 0
            ),
            key="geo_select_all_compact",
        )

        if select_all:
            selected = list(diseases)
            st.session_state[
                "geo_disease_selection"
            ] = selected
            st.session_state[
                "geo_disease_multiselect"
            ] = selected

    with right:

        reset_clicked = st.button(
            "Reset",
            key="geo_disease_reset_compact",
            help="Reset disease selection",
        )

        if reset_clicked:
            selected = list(diseases)
            st.session_state[
                "geo_disease_selection"
            ] = selected
            st.session_state[
                "geo_disease_multiselect"
            ] = selected
            st.session_state[
                "geo_select_all_compact"
            ] = True
            st.rerun()

    return selected


# ============================================================
# BUILD MAP
# ============================================================

def build_map(
    choropleth_geojson=None,
    hotspot_df=None,
    case_points=None,
    extent="BMC / Mumbai Focus",
    show_hotspots=True,
    diseases=None,
):

    layers = []

    if diseases is None:
        diseases = []

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
            get_line_width=4,
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
    # WARD-WISE HOTSPOT POINTS
    # --------------------------------------------------------

    if (
        show_hotspots
        and hotspot_df is not None
        and not hotspot_df.empty
    ):

        hotspot_plot = (
            hotspot_df.copy()
        )

        hotspot_layers = []

        for disease in (
            hotspot_plot["Disease"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
            if "Disease" in hotspot_plot.columns
            else [""]
        ):

            disease_hotspots = (
                hotspot_plot[
                    hotspot_plot[
                        "Disease"
                    ].astype(str)
                    == str(disease)
                ].copy()
            )

            if disease_hotspots.empty:
                continue

            palette = get_disease_palette(
                disease,
                diseases,
            )

            hotspot_layer = pdk.Layer(
                "ScatterplotLayer",
                data=disease_hotspots,
                get_position=[
                    "Cluster_Longitude",
                    "Cluster_Latitude",
                ],
                get_radius=(
                    "Display_Radius"
                ),
                get_fill_color=(
                    palette["point"]
                ),
                get_line_color=(
                    palette["line"]
                ),
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
                radius_min_pixels=2,
                radius_max_pixels=10,
                auto_highlight=True,
            )

            layers.append(
                hotspot_layer
            )

    # --------------------------------------------------------
    # PN HOTSPOT HIGHLIGHT
    # --------------------------------------------------------

    if (
        case_points is not None
        and not case_points.empty
        and "PN_Hotspot" in case_points.columns
    ):

        pn_hotspot_points = (
            case_points[
                case_points[
                    "PN_Hotspot"
                ]
                == True
            ]
            .copy()
        )

        if not pn_hotspot_points.empty:

            pn_highlight_layer = (
                pdk.Layer(
                    "ScatterplotLayer",
                    data=(
                        pn_hotspot_points
                    ),
                    get_position=[
                        "_lon",
                        "_lat",
                    ],
                    get_radius=(
                        "Highlight_Radius"
                    ),
                    get_fill_color=[
                        255,
                        165,
                        0,
                        30,
                    ],
                    get_line_color=[
                        255,
                        140,
                        0,
                        255,
                    ],
                    line_width_min_pixels=2,
                    stroked=True,
                    filled=True,
                    pickable=True,
                    radius_min_pixels=2,
                    radius_max_pixels=8,
                )
            )

            layers.append(
                pn_highlight_layer
            )

    # --------------------------------------------------------
    # CASE POINTS
    # --------------------------------------------------------

    if (
        case_points is not None
        and not case_points.empty
    ):

        point_diseases = sorted(
            case_points[
                "Disease"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        for disease in point_diseases:

            disease_points = (
                case_points[
                    case_points[
                        "Disease"
                    ].astype(str)
                    == str(disease)
                ].copy()
            )

            if disease_points.empty:
                continue

            palette = get_disease_palette(
                disease,
                diseases,
            )

            disease_layer = pdk.Layer(
                "ScatterplotLayer",
                data=disease_points,
                get_position=[
                    "_lon",
                    "_lat",
                ],
                get_radius=(
                    "Point_Radius"
                ),
                get_fill_color=(
                    palette["point"]
                ),
                get_line_color=(
                    palette["line"]
                ),
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
                radius_min_pixels=2,
                radius_max_pixels=6,
            )

            layers.append(
                disease_layer
            )

    # --------------------------------------------------------
    # MAP VIEW
    # --------------------------------------------------------

    if (
        extent
        == "All Coordinates"
    ):

        if (
            case_points is not None
            and not case_points.empty
        ):

            center_lat = float(
                case_points[
                    "_lat"
                ].mean()
            )

            center_lon = float(
                case_points[
                    "_lon"
                ].mean()
            )

            zoom = 5.5

        elif (
            hotspot_df is not None
            and not hotspot_df.empty
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
            zoom = 5.5

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
            <b>Ward:</b> {WardDisplay}<br/>
            <b>Cases:</b> {ProgrammeCases}<br/>
            <b>Case ID:</b> {CaseID}<br/>
            <b>Disease:</b> {Disease}<br/>
            <b>Facility:</b> {Facility}<br/>
            <b>Cluster Cases:</b> {Cluster Cases}<br/>
            <b>Hotspot:</b> {Hotspot Classification}<br/>
            <b>PN Hotspot:</b> {Hotspot Status}
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
                "Disease": disease,
                "Cases": cases,
                "Valid Coordinates": cases,
                "Hotspot Clusters": len(
                    hotspots
                ),
                "High Hotspots": (
                    high_hotspots
                ),
                "Top Ward": top_ward,
                "Top Ward Cases": (
                    top_ward_cases
                ),
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
    all_diseases=None,
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

        map_ward_summary = (
            create_map_ward_summary(
                disease_df
            )
        )

        choropleth = (
            prepare_bmc_choropleth(
                bmc_geojson,
                map_ward_summary,
                disease=disease,
                diseases=(
                    all_diseases
                    if all_diseases
                    else [disease]
                ),
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
        and disease_col in source_df.columns
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

        if len(disease_values) == 1:

            result["Disease"] = (
                disease_values[0]
            )

    preferred = [
        "Disease",
        "Ward",
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

    st.markdown(
        "### Map Controls"
    )

    control_extent, control_disease, control_reset = (
        st.columns(
            [0.95, 1.55, 0.20],
            gap="small",
        )
    )

    with control_extent:

        extent = st.radio(
            "Map Extent",
            [
                "BMC / Mumbai Focus",
                "All Coordinates",
            ],
            horizontal=True,
            key="geo_extent",
        )

    with control_disease:

        selected_diseases = (
            st.multiselect(
                "Disease Selection",
                options=diseases,
                default=(
                    st.session_state.get(
                        "geo_disease_selection",
                        diseases,
                    )
                ),
                key="geo_disease_multiselect",
                placeholder="Select disease(s)",
            )
        )

        st.session_state[
            "geo_disease_selection"
        ] = selected_diseases

    with control_reset:

        st.write("")

        if st.button(
            "Reset",
            key="geo_disease_reset_compact",
            help="Reset disease selection",
        ):

            st.session_state[
                "geo_disease_selection"
            ] = list(diseases)

            st.session_state[
                "geo_disease_multiselect"
            ] = list(diseases)

            st.rerun()

    # ========================================================
    # SELECT ALL
    # ========================================================

    select_all_col, select_all_spacer = st.columns(
        [0.18, 0.82]
    )

    with select_all_col:

        select_all = st.checkbox(
            "Select All",
            value=(
                len(selected_diseases)
                == len(diseases)
                and len(diseases) > 0
            ),
            key="geo_select_all_inline",
        )

    if select_all:

        if set(selected_diseases) != set(diseases):

            selected_diseases = list(
                diseases
            )

            st.session_state[
                "geo_disease_selection"
            ] = selected_diseases

            st.session_state[
                "geo_disease_multiselect"
            ] = selected_diseases

            st.rerun()

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

        disease_status = ", ".join(
            selected_diseases
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
    # OVERALL WARD-WISE HOTSPOTS
    # ========================================================

    overall_hotspots = (
        create_hotspots(
            map_df
        )
    )

    # ========================================================
    # OVERALL CASE POINTS
    # ========================================================

    overall_case_points = (
        create_case_points(
            map_df,
            overall_hotspots,
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

        map_ward_summary = (
            create_map_ward_summary(
                map_df
            )
        )

        overall_choropleth = (
            prepare_bmc_choropleth(
                bmc_geojson,
                map_ward_summary,
                disease=(
                    selected_diseases[0]
                    if len(selected_diseases) == 1
                    else None
                ),
                diseases=diseases,
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
            "Ward Hotspots",
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
            and "Hotspot Classification"
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
            "High Ward Hotspots",
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
            "Ward shading represents ward-wise case "
            "burden. Darker shades indicate higher "
            "burden. PE + PN are combined as P "
            "for choropleth display."
        )

    # ========================================================
    # TABS
    # ========================================================

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Hotspots",
            "Disease Comparison",
            "Choropleth Comparison",
            "Combined Geographic View",
        ]
    )

    # ========================================================
    # TAB 1 - HOTSPOTS
    # ========================================================

    with tab1:

        st.subheader(
            "Disease Hotspot Map"
        )

        if overall_hotspots.empty:

            st.info(
                "No ward-wise hotspot clusters "
                "could be created."
            )

        else:

            deck = build_map(
                choropleth_geojson=None,
                hotspot_df=overall_hotspots,
                case_points=overall_case_points,
                extent=extent,
                show_hotspots=True,
                diseases=diseases,
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
            )

            pe_cases = int(
                overall_ward_summary.loc[
                    overall_ward_summary[
                        "Ward"
                    ] == "PE",
                    "Cases",
                ].sum()
            )

            pn_cases = int(
                overall_ward_summary.loc[
                    overall_ward_summary[
                        "Ward"
                    ] == "PN",
                    "Cases",
                ].sum()
            )

            other_cases = int(
                overall_ward_summary.loc[
                    ~overall_ward_summary[
                        "Ward"
                    ].isin(
                        [
                            "PE",
                            "PN",
                        ]
                    ),
                    "Cases",
                ].sum()
            )

            pn_hotspot_count = 0

            if (
                not overall_case_points.empty
                and "PN_Hotspot"
                in overall_case_points.columns
            ):

                pn_hotspot_count = int(
                    overall_case_points[
                        "PN_Hotspot"
                    ].sum()
                )

            st.markdown(
                f"""
                <div style="
                    padding:10px 14px;
                    border:1px solid #ddd;
                    border-radius:8px;
                    background:#fafafa;
                    margin-top:8px;
                    margin-bottom:12px;
                    font-size:13px;
                ">
                    <b>Map Legend</b><br/>
                    Disease colours are separate.
                    Darker shade = higher ward burden.
                    Lighter shade = lower ward burden.
                    <br/>
                    PE Cases: <b>{pe_cases:,}</b>
                    &nbsp;&nbsp;
                    PN Cases: <b>{pn_cases:,}</b>
                    &nbsp;&nbsp;
                    Other Wards: <b>{other_cases:,}</b>
                    &nbsp;&nbsp;
                    Ward Hotspots:
                    <b>{len(overall_hotspots):,}</b>
                    <br/>
                    P = PE + PN for choropleth:
                    <b>{pe_cases + pn_cases:,}</b>
                    &nbsp;&nbsp;
                    PN cases inside hotspot wards:
                    <b>{pn_hotspot_count:,}</b>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.subheader(
                "Ward-wise Hotspot Summary"
            )

            hotspot_display = (
                overall_hotspots[
                    [
                        "Disease",
                        "Ward",
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
                            "Ward Cases",
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
                    "Download Hotspot Data (Excel)",
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
    # TAB 2 - DISEASE COMPARISON
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

            st.dataframe(
                comparison_df,
                use_container_width=True,
                hide_index=True,
            )

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
                comparison_df.iterrows()
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
                        - Ward Hotspots: **{int(row['Hotspot Clusters']):,}**
                        - High Ward Hotspots: **{int(row['High Hotspots']):,}**
                        - Top Ward: **{row['Top Ward']}**
                        - Top Ward Cases: **{int(row['Top Ward Cases']):,}**
                        """
                    )

            st.markdown(
                "### Disease-wise Ward Burden Comparison"
            )

            selected_for_table = (
                selected_diseases
                if selected_diseases
                else diseases
            )

            ward_comparison = pd.DataFrame(
                {
                    "Ward":
                        PROGRAMME_WARDS
                }
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
                "Download Disease Comparison (Excel)",
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
    # TAB 3 - CHOROPLETH COMPARISON
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

            if len(
                selected_for_maps
            ) > 6:

                st.info(
                    "For performance, the choropleth "
                    "comparison displays the first 6 "
                    "selected diseases."
                )

                map_diseases = (
                    selected_for_maps[:6]
                )

            else:

                map_diseases = (
                    selected_for_maps
                )

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
                                diseases,
                            )
                        )

                        disease_points = (
                            create_case_points(
                                disease_df,
                                disease_hotspots,
                            )
                        )

                        st.markdown(
                            f"**{disease}**"
                        )

                        st.caption(
                            f"Cases: "
                            f"{len(disease_df):,} | "
                            f"Ward Hotspots: "
                            f"{len(disease_hotspots):,}"
                        )

                        disease_deck = (
                            build_map(
                                choropleth_geojson=(
                                    disease_choropleth
                                ),
                                hotspot_df=None,
                                case_points=(
                                    disease_points
                                ),
                                extent=(
                                    "BMC / Mumbai Focus"
                                ),
                                show_hotspots=False,
                                diseases=diseases,
                            )
                        )

                        st.pydeck_chart(
                            disease_deck,
                            use_container_width=True,
                        )

                        top5 = (
                            disease_ward
                            .sort_values(
                                "Cases",
                                ascending=False,
                            )
                            .head(5)
                            .copy()
                        )

                        top5 = top5[
                            [
                                "Ward",
                                "Cases",
                            ]
                        ]

                        st.dataframe(
                            top5,
                            use_container_width=True,
                            hide_index=True,
                        )

            st.caption(
                "Each disease uses a separate colour family. "
                "Within each disease, darker shading indicates "
                "higher ward-wise burden and lighter shading "
                "indicates lower burden. PE + PN are treated "
                "together as P for choropleth display."
            )

    # ========================================================
    # TAB 4 - COMBINED VIEW
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
            case_points=(
                overall_case_points
            ),
            extent=extent,
            show_hotspots=True,
            diseases=diseases,
        )

        st.pydeck_chart(
            combined_deck,
            use_container_width=True,
        )

        st.caption(
            "Every valid geographic coordinate is plotted "
            "as a case point. Ward hotspot size and shading "
            "are based on ward-wise disease burden. "
            "Disease colours are kept separate to reduce "
            "visual confusion."
        )

        pe_cases = int(
            overall_ward_summary.loc[
                overall_ward_summary[
                    "Ward"
                ] == "PE",
                "Cases",
            ].sum()
        )

        pn_cases = int(
            overall_ward_summary.loc[
                overall_ward_summary[
                    "Ward"
                ] == "PN",
                "Cases",
            ].sum()
        )

        other_cases = int(
            overall_ward_summary.loc[
                ~overall_ward_summary[
                    "Ward"
                ].isin(
                    [
                        "PE",
                        "PN",
                    ]
                ),
                "Cases",
            ].sum()
        )

        pn_hotspot_count = 0

        if (
            not overall_case_points.empty
            and "PN_Hotspot"
            in overall_case_points.columns
        ):

            pn_hotspot_count = int(
                overall_case_points[
                    "PN_Hotspot"
                ].sum()
            )

        st.markdown(
            f"""
            <div style="
                padding:10px 14px;
                border:1px solid #ddd;
                border-radius:8px;
                background:#fafafa;
                margin-top:8px;
                margin-bottom:12px;
                font-size:13px;
            ">
                <b>Map Legend</b><br/>
                Disease colours are separate.
                Darker = higher ward burden.
                Lighter = lower ward burden.
                <br/>
                PE: <b>{pe_cases:,}</b>
                &nbsp;&nbsp;
                PN: <b>{pn_cases:,}</b>
                &nbsp;&nbsp;
                Other Wards: <b>{other_cases:,}</b>
                &nbsp;&nbsp;
                Ward Hotspots:
                <b>{len(overall_hotspots):,}</b>
                <br/>
                P = PE + PN:
                <b>{pe_cases + pn_cases:,}</b>
                &nbsp;&nbsp;
                PN cases inside hotspot wards:
                <b>{pn_hotspot_count:,}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

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

        total_cases = int(
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
            "Download Ward-wise Burden (Excel)",
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
        "Geographic Data Export"
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
            "Download Current Geographic Data (CSV)",
            data=csv_data,
            file_name=(
                "current_geographic_data.csv"
            ),
            mime="text/csv",
            key="geo_current_csv",
        )
