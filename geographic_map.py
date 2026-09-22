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

PROGRAMME_WARDS = [
    "A", "B", "C", "D", "E",
    "FN", "FS",
    "GN", "GS",
    "HE", "HW",
    "KE", "KW",
    "L",
    "ME", "MW",
    "N",
    "PE", "PN", "PS",
    "RC", "RN", "RS",
    "S", "T",
]


# ============================================================
# HELPERS
# ============================================================

def _safe_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def _find_column(df, candidates):
    if df is None or df.empty:
        return None

    lookup = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower()
        if key in lookup:
            return lookup[key]

    return None


def _detect_disease_column(df):
    return _find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
            "Diagnosis",
            "Condition",
            "Disease/Condition",
        ],
    )


def _detect_ward_column(df):
    return _find_column(
        df,
        [
            "Ward",
            "Ward No",
            "Ward Number",
            "BMC Ward",
            "BMC_Ward",
            "Ward Name",
            "Ward_Name",
        ],
    )


def _detect_facility_column(df):
    return _find_column(
        df,
        [
            "Facility",
            "Facility Name",
            "Facility_Name",
            "Health Facility",
            "Health Facility Name",
            "Hospital",
            "Hospital Name",
            "Institution",
            "Institution Name",
        ],
    )


def _detect_case_id_column(df):
    return _find_column(
        df,
        [
            "Case ID",
            "Case_ID",
            "CaseID",
            "ID",
            "Patient ID",
            "Patient_ID",
        ],
    )


def normalize_ward(value):
    text = _safe_text(value).upper()

    if not text:
        return ""

    text = text.replace("WARD", "")
    text = text.replace("BMC", "")
    text = text.replace("MUNICIPAL", "")
    text = text.replace(" ", "")
    text = text.replace("-", "")
    text = text.replace("_", "")

    replacements = {
        "F/N": "FN",
        "F/S": "FS",
        "G/N": "GN",
        "G/S": "GS",
        "H/E": "HE",
        "H/W": "HW",
        "K/E": "KE",
        "K/W": "KW",
        "M/E": "ME",
        "M/W": "MW",
        "P/N": "PN",
        "P/S": "PS",
        "R/C": "RC",
        "R/N": "RN",
        "R/S": "RS",
    }

    if text in replacements:
        text = replacements[text]

    if text in PROGRAMME_WARDS:
        return text

    return text


def display_ward(value):
    ward = normalize_ward(value)

    if ward in ("PE", "PN"):
        return "P"

    return ward


# ============================================================
# COORDINATES
# ============================================================

def prepare_coordinates(df):

    if df is None:
        return pd.DataFrame()

    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    if df.empty:
        return df.copy()

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame()

    out = df.copy()

    out[LAT_COL] = pd.to_numeric(
        out[LAT_COL],
        errors="coerce",
    )

    out[LON_COL] = pd.to_numeric(
        out[LON_COL],
        errors="coerce",
    )

    out = out.dropna(
        subset=[LAT_COL, LON_COL]
    ).copy()

    out = out[
        out[LAT_COL].between(-90, 90)
        & out[LON_COL].between(-180, 180)
    ].copy()

    return out


# ============================================================
# HOTSPOTS
# ============================================================

def create_hotspots(df):

    if df is None or df.empty:
        return pd.DataFrame()

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame()

    work = df[
        [LAT_COL, LON_COL]
    ].copy()

    work[LAT_COL] = pd.to_numeric(
        work[LAT_COL],
        errors="coerce",
    )

    work[LON_COL] = pd.to_numeric(
        work[LON_COL],
        errors="coerce",
    )

    work = work.dropna(
        subset=[LAT_COL, LON_COL]
    ).copy()

    if work.empty:
        return pd.DataFrame()

    work["_grid_lat"] = (
        work[LAT_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    work["_grid_lon"] = (
        work[LON_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    hotspots = (
        work.groupby(
            ["_grid_lat", "_grid_lon"],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "Cases"})
    )

    if hotspots.empty:
        return pd.DataFrame()

    hotspots["Latitude"] = hotspots["_grid_lat"]
    hotspots["Longitude"] = hotspots["_grid_lon"]

    hotspots["_Cluster_ID"] = (
        hotspots["_grid_lat"].astype(str)
        + "_"
        + hotspots["_grid_lon"].astype(str)
    )

    hotspots["Hotspot Level"] = "Low"

    hotspots.loc[
        hotspots["Cases"] >= 5,
        "Hotspot Level",
    ] = "Moderate"

    hotspots.loc[
        hotspots["Cases"] >= 10,
        "Hotspot Level",
    ] = "High"

    hotspots["Radius"] = (
        45 + hotspots["Cases"] * 4
    ).clip(
        lower=45,
        upper=125,
    )

    return hotspots[
        [
            "Latitude",
            "Longitude",
            "Cases",
            "Hotspot Level",
            "Radius",
            "_Cluster_ID",
        ]
    ].copy()


# ============================================================
# CASE POINTS
# ============================================================

def create_case_points(df):

    if df is None or df.empty:
        return pd.DataFrame()

    if LAT_COL not in df.columns or LON_COL not in df.columns:
        return pd.DataFrame()

    out = df.copy()

    out[LAT_COL] = pd.to_numeric(
        out[LAT_COL],
        errors="coerce",
    )

    out[LON_COL] = pd.to_numeric(
        out[LON_COL],
        errors="coerce",
    )

    out = out.dropna(
        subset=[LAT_COL, LON_COL]
    ).copy()

    if out.empty:
        return pd.DataFrame()

    disease_col = _detect_disease_column(out)
    ward_col = _detect_ward_column(out)
    facility_col = _detect_facility_column(out)
    case_id_col = _detect_case_id_column(out)

    result = pd.DataFrame()

    result["Latitude"] = out[LAT_COL]
    result["Longitude"] = out[LON_COL]

    if disease_col:
        result["Disease"] = (
            out[disease_col]
            .fillna("Unknown")
            .astype(str)
        )
    else:
        result["Disease"] = "Unknown"

    if ward_col:
        result["Ward"] = (
            out[ward_col]
            .apply(display_ward)
        )
    else:
        result["Ward"] = ""

    if facility_col:
        result["Facility"] = (
            out[facility_col]
            .fillna("Unknown")
            .astype(str)
        )
    else:
        result["Facility"] = "Unknown"

    if case_id_col:
        result["Case ID"] = (
            out[case_id_col]
            .fillna("")
            .astype(str)
        )
    else:
        result["Case ID"] = ""

    return result


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):

    if df is None or df.empty:
        return pd.DataFrame(
            columns=["Ward", "Cases"]
        )

    ward_col = _detect_ward_column(df)

    if not ward_col:
        return pd.DataFrame(
            columns=["Ward", "Cases"]
        )

    work = df[[ward_col]].copy()

    work["Ward"] = work[ward_col].apply(
        display_ward
    )

    work = work[
        work["Ward"].astype(str).str.strip() != ""
    ].copy()

    if work.empty:
        return pd.DataFrame(
            columns=["Ward", "Cases"]
        )

    result = (
        work.groupby(
            "Ward",
            as_index=False,
        )
        .size()
        .rename(columns={"size": "Cases"})
        .sort_values(
            "Cases",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    return result


# ============================================================
# MAP WARD SUMMARY
# ============================================================

def create_map_ward_summary(df):

    summary = create_ward_summary(df)

    if summary.empty:
        return summary

    result = summary.copy()

    # PE + PN are represented by P on the BMC map
    if "Ward" in result.columns:

        p_mask = result["Ward"].isin(
            ["PE", "PN", "P"]
        )

        if bool(p_mask.any()):

            p_cases = int(
                result.loc[
                    p_mask,
                    "Cases"
                ].sum()
            )

            result = result.loc[
                ~p_mask
            ].copy()

            result = pd.concat(
                [
                    result,
                    pd.DataFrame(
                        {
                            "Ward": ["P"],
                            "Cases": [p_cases],
                        }
                    ),
                ],
                ignore_index=True,
            )

    return result.sort_values(
        "Cases",
        ascending=False,
    ).reset_index(drop=True)


# ============================================================
# BMC WARD GEOJSON
# ============================================================

@st.cache_data(
    ttl=86400,
    show_spinner=False,
)
def load_bmc_wards():

    params = {
        "where": "1=1",
        "outFields": "NAME",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }

    try:

        response = requests.get(
            BMC_WARD_URL + "/query",
            params=params,
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            return None

        if data.get("type") != "FeatureCollection":
            return None

        features = data.get(
            "features",
            [],
        )

        if not isinstance(features, list):
            return None

        clean_features = []

        for feature in features:

            if not isinstance(feature, dict):
                continue

            geometry = feature.get(
                "geometry"
            )

            if not geometry:
                continue

            properties = feature.get(
                "properties",
                {},
            )

            if not isinstance(properties, dict):
                properties = {}

            name = properties.get(
                "NAME",
                "",
            )

            clean_features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "NAME": _safe_text(name),
                    },
                }
            )

        return {
            "type": "FeatureCollection",
            "features": clean_features,
        }

    except Exception:
        return None


# ============================================================
# BMC GEOJSON PREPARATION
# ============================================================

def _bmc_property_ward(properties):

    if not isinstance(properties, dict):
        return ""

    name = properties.get(
        "NAME",
        "",
    )

    return normalize_ward(name)


def prepare_bmc_choropleth(
    geojson,
    ward_summary,
    disease_name="",
):

    if not isinstance(
        geojson,
        dict,
    ):
        return None

    features = geojson.get(
        "features",
        [],
    )

    if not isinstance(features, list):
        return None

    if ward_summary is None:
        ward_summary = pd.DataFrame()

    case_lookup = {}

    if (
        isinstance(ward_summary, pd.DataFrame)
        and not ward_summary.empty
        and "Ward" in ward_summary.columns
        and "Cases" in ward_summary.columns
    ):

        for _, row in ward_summary.iterrows():

            ward = display_ward(
                row["Ward"]
            )

            try:
                cases = int(
                    row["Cases"]
                )
            except Exception:
                cases = 0

            if ward:
                case_lookup[ward] = cases

    clean_features = []

    max_cases = max(
        case_lookup.values()
    ) if case_lookup else 0

    for feature in features:

        if not isinstance(feature, dict):
            continue

        geometry = feature.get(
            "geometry"
        )

        if not geometry:
            continue

        old_properties = feature.get(
            "properties",
            {},
        )

        ward = _bmc_property_ward(
            old_properties
        )

        # PE and PN are displayed as P
        display = display_ward(
            ward
        )

        cases = int(
            case_lookup.get(
                display,
                0,
            )
        )

        # Lightweight colour classification
        if cases <= 0:
            fill = [
                245, 245, 245, 180
            ]
        elif max_cases > 0 and cases >= max_cases * 0.75:
            fill = [
                170, 55, 55, 190
            ]
        elif max_cases > 0 and cases >= max_cases * 0.40:
            fill = [
                225, 135, 55, 190
            ]
        else:
            fill = [
                245, 205, 80, 190
            ]

        properties = {
            "NAME": _safe_text(
                old_properties.get(
                    "NAME",
                    ""
                )
            ),
            "WardDisplay": display,
            "Cases": cases,
            "Disease": disease_name,
            "fill_color": fill,
            "line_color": [
                90, 90, 90, 180
            ],
        }

        clean_features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": properties,
            }
        )

    return {
        "type": "FeatureCollection",
        "features": clean_features,
    }


# ============================================================
# MAP CENTER
# ============================================================

def calculate_view_state(df):

    if df is None or df.empty:
        return pdk.ViewState(
            latitude=19.0760,
            longitude=72.8777,
            zoom=10.2,
            pitch=0,
            bearing=0,
        )

    if (
        LAT_COL not in df.columns
        or LON_COL not in df.columns
    ):
        return pdk.ViewState(
            latitude=19.0760,
            longitude=72.8777,
            zoom=10.2,
            pitch=0,
            bearing=0,
        )

    lat = pd.to_numeric(
        df[LAT_COL],
        errors="coerce",
    )

    lon = pd.to_numeric(
        df[LON_COL],
        errors="coerce",
    )

    valid = pd.DataFrame(
        {
            "lat": lat,
            "lon": lon,
        }
    ).dropna()

    if valid.empty:
        return pdk.ViewState(
            latitude=19.0760,
            longitude=72.8777,
            zoom=10.2,
            pitch=0,
            bearing=0,
        )

    latitude = float(
        valid["lat"].mean()
    )

    longitude = float(
        valid["lon"].mean()
    )

    return pdk.ViewState(
        latitude=latitude,
        longitude=longitude,
        zoom=10.5,
        pitch=0,
        bearing=0,
    )


# ============================================================
# DECK BUILDER
# ============================================================

def _make_deck(
    layers,
    view_state,
    tooltip=None,
):

    return pdk.Deck(
        map_provider="carto",
        map_style="light",
        initial_view_state=view_state,
        layers=layers,
        tooltip=tooltip,
    )


# ============================================================
# HOTSPOT MAP
# ============================================================

def build_hotspot_map(
    hotspots,
    ward_geojson=None,
    view_state=None,
):

    layers = []

    if (
        isinstance(ward_geojson, dict)
        and ward_geojson.get("features")
    ):

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=ward_geojson,
                pickable=False,
                stroked=True,
                filled=False,
                get_line_color=[
                    110, 110, 110, 150
                ],
                line_width_min_pixels=1,
            )
        )

    if (
        hotspots is not None
        and not hotspots.empty
    ):

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=hotspots,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius="Radius",
                get_fill_color=[
                    220, 70, 70, 150
                ],
                get_line_color=[
                    120, 30, 30, 180
                ],
                stroked=True,
                filled=True,
                pickable=True,
                radius_min_pixels=5,
                radius_max_pixels=25,
            )
        )

    return _make_deck(
        layers=layers,
        view_state=view_state,
        tooltip={
            "html": (
                "<b>Hotspot:</b> {Hotspot Level}<br/>"
                "<b>Cases:</b> {Cases}"
            )
        },
    )


# ============================================================
# CHOROPLETH MAP
# ============================================================

def build_choropleth_map(
    ward_geojson,
    view_state=None,
):

    layers = []

    if (
        isinstance(ward_geojson, dict)
        and ward_geojson.get("features")
    ):

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=ward_geojson,
                pickable=True,
                stroked=True,
                filled=True,
                get_fill_color=(
                    "properties.fill_color"
                ),
                get_line_color=(
                    "properties.line_color"
                ),
                line_width_min_pixels=1,
                auto_highlight=True,
            )
        )

    return _make_deck(
        layers=layers,
        view_state=view_state,
        tooltip={
            "html": (
                "<b>Ward:</b> "
                "{properties.WardDisplay}<br/>"
                "<b>Cases:</b> "
                "{properties.Cases}<br/>"
                "<b>Disease:</b> "
                "{properties.Disease}"
            )
        },
    )


# ============================================================
# COMBINED MAP
# ============================================================

def build_combined_map(
    ward_geojson,
    hotspots,
    view_state=None,
):

    layers = []

    if (
        isinstance(ward_geojson, dict)
        and ward_geojson.get("features")
    ):

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=ward_geojson,
                pickable=True,
                stroked=True,
                filled=True,
                get_fill_color=(
                    "properties.fill_color"
                ),
                get_line_color=(
                    "properties.line_color"
                ),
                line_width_min_pixels=1,
                auto_highlight=True,
            )
        )

    if (
        hotspots is not None
        and not hotspots.empty
    ):

        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=hotspots,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius="Radius",
                get_fill_color=[
                    220, 70, 70, 150
                ],
                get_line_color=[
                    120, 30, 30, 180
                ],
                stroked=True,
                filled=True,
                pickable=True,
                radius_min_pixels=5,
                radius_max_pixels=22,
            )
        )

    return _make_deck(
        layers=layers,
        view_state=view_state,
        tooltip={
            "html": (
                "<b>Ward:</b> "
                "{properties.WardDisplay}<br/>"
                "<b>Cases:</b> "
                "{properties.Cases}"
            )
        },
    )


# ============================================================
# DISEASE SUMMARY
# ============================================================

def create_disease_summary(df):

    disease_col = _detect_disease_column(df)

    if not disease_col:
        return pd.DataFrame(
            columns=[
                "Disease",
                "Cases",
            ]
        )

    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "Disease",
                "Cases",
            ]
        )

    result = df.copy()

    result["Disease"] = (
        result[disease_col]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    result = result[
        result["Disease"] != ""
    ].copy()

    if result.empty:
        return pd.DataFrame(
            columns=[
                "Disease",
                "Cases",
            ]
        )

    return (
        result.groupby(
            "Disease",
            as_index=False,
        )
        .size()
        .rename(columns={"size": "Cases"})
        .sort_values(
            "Cases",
            ascending=False,
        )
        .reset_index(drop=True)
    )


# ============================================================
# EXCEL EXPORT
# ============================================================

def create_excel_export(
    ward_summary,
    disease_summary,
    hotspots,
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        if ward_summary is None:
            ward_summary = pd.DataFrame()

        if disease_summary is None:
            disease_summary = pd.DataFrame()

        if hotspots is None:
            hotspots = pd.DataFrame()

        ward_summary.to_excel(
            writer,
            index=False,
            sheet_name="Ward Summary",
        )

        disease_summary.to_excel(
            writer,
            index=False,
            sheet_name="Disease Summary",
        )

        hotspots.to_excel(
            writer,
            index=False,
            sheet_name="Hotspots",
        )

    output.seek(0)

    return output.getvalue()


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_geographic_map(
    filtered_df,
    *args,
    **kwargs,
):

    st.markdown(
        "### Geographic Disease Distribution"
    )

    # --------------------------------------------------------
    # Validate data
    # --------------------------------------------------------

    if filtered_df is None:
        st.warning(
            "No data available for geographic analysis."
        )
        return

    if not isinstance(
        filtered_df,
        pd.DataFrame,
    ):
        st.warning(
            "Geographic data is not available in table format."
        )
        return

    if filtered_df.empty:
        st.info(
            "No records available for the selected filters."
        )
        return

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    map_df = prepare_coordinates(
        filtered_df
    )

    if map_df.empty:
        st.warning(
            "No valid latitude/longitude records are available."
        )
        return

    # --------------------------------------------------------
    # Disease list
    # --------------------------------------------------------

    disease_col = _detect_disease_column(
        map_df
    )

    diseases = []

    if disease_col:

        diseases = sorted(
            map_df[disease_col]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[
                lambda x: x != ""
            ]
            .unique()
            .tolist()
        )

    # --------------------------------------------------------
    # BMC Wards
    # --------------------------------------------------------

    ward_geojson = load_bmc_wards()

    # --------------------------------------------------------
    # Controls
    # --------------------------------------------------------

    st.markdown(
        "#### Geographic Filters"
    )

    col1, col2 = st.columns(
        [3, 1]
    )

    with col1:

        selected = st.multiselect(
            "Disease Selection",
            options=diseases,
            default=[],
            key="geo_disease_selection",
            placeholder="All diseases",
        )

    def reset_geo_disease_selection():

        st.session_state[
            "geo_disease_selection"
        ] = []

    with col2:

        st.write("")

        st.button(
            "Reset",
            key="geo_disease_reset",
            on_click=reset_geo_disease_selection,
        )

    # --------------------------------------------------------
    # Apply disease filter
    # --------------------------------------------------------

    if selected:

        map_df = map_df[
            map_df[disease_col]
            .astype(str)
            .isin(selected)
        ].copy()

    if map_df.empty:

        st.info(
            "No geographic records match the selected disease filter."
        )
        return

    # --------------------------------------------------------
    # Prepare summaries
    # --------------------------------------------------------

    hotspots = create_hotspots(
        map_df
    )

    ward_summary = create_ward_summary(
        map_df
    )

    map_ward_summary = create_map_ward_summary(
        map_df
    )

    disease_summary = create_disease_summary(
        map_df
    )

    view_state = calculate_view_state(
        map_df
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    total_cases = len(
        map_df
    )

    mapped_cases = len(
        prepare_coordinates(map_df)
    )

    hotspot_cells = (
        len(hotspots)
        if isinstance(
            hotspots,
            pd.DataFrame,
        )
        else 0
    )

    wards_with_cases = (
        len(ward_summary)
        if isinstance(
            ward_summary,
            pd.DataFrame,
        )
        else 0
    )

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Total Cases",
        f"{total_cases:,}",
    )

    k2.metric(
        "Mapped Cases",
        f"{mapped_cases:,}",
    )

    k3.metric(
        "Hotspot Areas",
        f"{hotspot_cells:,}",
    )

    k4.metric(
        "Wards with Cases",
        f"{wards_with_cases:,}",
    )

    st.divider()

    # ========================================================
    # IMPORTANT:
    # DO NOT USE st.tabs HERE.
    #
    # Streamlit can keep all tab contents mounted.
    # Multiple pydeck canvases = multiple WebGL contexts.
    # ========================================================

    view_options = [
        "Hotspots",
        "Disease Comparison",
        "Choropleth Comparison",
        "Combined Geographic View",
    ]

    selected_view = st.radio(
        "Map View",
        view_options,
        horizontal=True,
        key="geo_map_view",
    )

    # ========================================================
    # 1. HOTSPOTS
    # ========================================================

    if selected_view == "Hotspots":

        st.markdown(
            "#### Geographic Hotspots"
        )

        if hotspots.empty:

            st.info(
                "No hotspot areas available."
            )

        else:

            deck = build_hotspot_map(
                hotspots=hotspots,
                ward_geojson=ward_geojson,
                view_state=view_state,
            )

            # ONLY ONE MAP INSTANCE
            st.pydeck_chart(
                deck,
                use_container_width=True,
                height=430,
                key="geo_hotspot_map",
            )

            st.markdown(
                "##### Hotspot Summary"
            )

            display_hotspots = hotspots[
                [
                    "Latitude",
                    "Longitude",
                    "Cases",
                    "Hotspot Level",
                ]
            ].sort_values(
                "Cases",
                ascending=False,
            )

            st.dataframe(
                display_hotspots,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 2. DISEASE COMPARISON
    # ========================================================

    elif selected_view == "Disease Comparison":

        st.markdown(
            "#### Disease-wise Geographic Summary"
        )

        if disease_summary.empty:

            st.info(
                "No disease information is available."
            )

        else:

            st.dataframe(
                disease_summary,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 3. CHOROPLETH COMPARISON
    # ========================================================

    elif selected_view == "Choropleth Comparison":

        st.markdown(
            "#### Ward-wise Disease Choropleth"
        )

        if not diseases:

            st.info(
                "No disease categories are available."
            )

        elif ward_geojson is None:

            st.warning(
                "BMC ward boundary data could not be loaded."
            )

        else:

            # ------------------------------------------------
            # IMPORTANT PERFORMANCE FIX
            #
            # Only TWO maps are mounted at one time.
            # ------------------------------------------------

            pair_count = (
                (len(diseases) + 1) // 2
            )

            pair_labels = []

            for i in range(
                pair_count
            ):

                start = i * 2
                pair = diseases[
                    start:start + 2
                ]

                pair_labels.append(
                    f"{start + 1}-{start + len(pair)}: "
                    + " / ".join(pair)
                )

            selected_pair = st.selectbox(
                "Disease Map Pair",
                options=range(
                    len(pair_labels)
                ),
                format_func=lambda x: pair_labels[x],
                key="geo_disease_pair",
            )

            start_index = (
                selected_pair * 2
            )

            pair_diseases = diseases[
                start_index:start_index + 2
            ]

            map_cols = st.columns(2)

            for idx, disease in enumerate(
                pair_diseases
            ):

                with map_cols[idx]:

                    st.markdown(
                        f"**{disease}**"
                    )

                    disease_df = map_df[
                        map_df[disease_col]
                        .astype(str)
                        .str.strip()
                        == disease
                    ].copy()

                    disease_ward_summary = (
                        create_map_ward_summary(
                            disease_df
                        )
                    )

                    disease_geojson = (
                        prepare_bmc_choropleth(
                            ward_geojson,
                            disease_ward_summary,
                            disease_name=disease,
                        )
                    )

                    disease_view_state = (
                        calculate_view_state(
                            disease_df
                        )
                    )

                    deck = (
                        build_choropleth_map(
                            disease_geojson,
                            view_state=disease_view_state,
                        )
                    )

                    # Only 2 WebGL contexts
                    st.pydeck_chart(
                        deck,
                        use_container_width=True,
                        height=330,
                        key=(
                            "geo_choropleth_"
                            + str(selected_pair)
                            + "_"
                            + str(idx)
                        ),
                    )

                    st.markdown(
                        "Ward-wise Data"
                    )

                    if disease_ward_summary.empty:

                        st.info(
                            "No ward-wise data available."
                        )

                    else:

                        st.dataframe(
                            disease_ward_summary,
                            use_container_width=True,
                            hide_index=True,
                        )

    # ========================================================
    # 4. COMBINED VIEW
    # ========================================================

    elif selected_view == "Combined Geographic View":

        st.markdown(
            "#### Combined Geographic View"
        )

        if ward_geojson is None:

            st.warning(
                "BMC ward boundary data could not be loaded."
            )

        else:

            combined_geojson = (
                prepare_bmc_choropleth(
                    ward_geojson,
                    map_ward_summary,
                    disease_name=(
                        "All Selected Diseases"
                        if selected
                        else "All Diseases"
                    ),
                )
            )

            deck = build_combined_map(
                ward_geojson=combined_geojson,
                hotspots=hotspots,
                view_state=view_state,
            )

            # ONLY ONE MAP INSTANCE
            st.pydeck_chart(
                deck,
                use_container_width=True,
                height=450,
                key="geo_combined_map",
            )

            st.markdown(
                "##### Ward-wise Summary"
            )

            if map_ward_summary.empty:

                st.info(
                    "No ward-wise information available."
                )

            else:

                st.dataframe(
                    map_ward_summary,
                    use_container_width=True,
                    hide_index=True,
                )

    # ========================================================
    # DOWNLOAD
    # ========================================================

    st.divider()

    export_data = create_excel_export(
        ward_summary=ward_summary,
        disease_summary=disease_summary,
        hotspots=hotspots,
    )

    st.download_button(
        "Download Geographic Analysis",
        data=export_data,
        file_name="geographic_analysis.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        key="geo_download_excel",
    )
