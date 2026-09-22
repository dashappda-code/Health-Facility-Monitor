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


def get_case_id_column(df):
    return find_column(
        df,
        [
            "Case ID",
            "Case_ID",
            "CaseID",
            "ID",
            "Id",
            "Record ID",
            "Record_ID",
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
        valid_records / total_records * 100
    )

    return (
        f"{label}: {total_records:,} | "
        f"Valid Address Coordinates: "
        f"{valid_records:,} "
        f"({percentage:.1f}%)"
    )


# ============================================================
# WARD PREPARATION
# ============================================================

def prepare_report_wards(df):
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    work = df.copy()

    ward_col = get_ward_column(work)

    if ward_col is None:
        work["_Report_Ward"] = ""
        work["_Map_Ward"] = ""
        return work

    work["_Report_Ward"] = (
        work[ward_col]
        .apply(normalise_ward)
    )

    work["_Map_Ward"] = work["_Report_Ward"]

    return work


# ============================================================
# HOTSPOT CREATION
# ============================================================

def create_hotspots(df):
    if df is None or df.empty:
        return pd.DataFrame()

    if "_lat" not in df.columns or "_lon" not in df.columns:
        return pd.DataFrame()

    work = df.copy()

    if "_Report_Ward" not in work.columns:
        work = prepare_report_wards(work)

    work["_grid_lat"] = (
        work["_lat"] / GRID_SIZE
    ).round() * GRID_SIZE

    work["_grid_lon"] = (
        work["_lon"] / GRID_SIZE
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

    summary["Hotspot Classification"] = (
        summary["Cluster_Cases"]
        .apply(classify)
    )

    summary["Radius"] = (
        45
        + summary["Cluster_Cases"]
        .clip(lower=1, upper=20)
        * 5
    )

    summary["Radius"] = (
        summary["Radius"]
        .clip(lower=50, upper=140)
        .astype(float)
    )

    # Determine whether each hotspot contains PE or PN cases.
    ward_cluster = (
        work.groupby("Cluster ID")["_Report_Ward"]
        .agg(
            lambda x: set(
                v for v in x
                if v
            )
        )
        .reset_index()
    )

    ward_cluster["Has_PE"] = (
        ward_cluster["_Report_Ward"]
        .apply(lambda x: "PE" in x)
    )

    ward_cluster["Has_PN"] = (
        ward_cluster["_Report_Ward"]
        .apply(lambda x: "PN" in x)
    )

    ward_cluster["Has_PE_PN"] = (
        ward_cluster["Has_PE"]
        | ward_cluster["Has_PN"]
    )

    summary = summary.merge(
        ward_cluster[
            [
                "Cluster ID",
                "Has_PE",
                "Has_PN",
                "Has_PE_PN",
            ]
        ],
        on="Cluster ID",
        how="left",
    )

    summary["Has_PE"] = (
        summary["Has_PE"]
        .fillna(False)
        .astype(bool)
    )

    summary["Has_PN"] = (
        summary["Has_PN"]
        .fillna(False)
        .astype(bool)
    )

    summary["Has_PE_PN"] = (
        summary["Has_PE_PN"]
        .fillna(False)
        .astype(bool)
    )

    return summary


# ============================================================
# CASE POINT DATA
# ============================================================

def create_case_points(df):
    if df is None or df.empty:
        return pd.DataFrame()

    if "_lat" not in df.columns or "_lon" not in df.columns:
        return pd.DataFrame()

    work = df.copy()

    if "_Report_Ward" not in work.columns:
        work = prepare_report_wards(work)

    disease_col = get_disease_column(work)

    case_id_col = get_case_id_column(work)

    if disease_col:
        disease_values = (
            work[disease_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        disease_values = pd.Series(
            [""] * len(work),
            index=work.index,
        )

    if case_id_col:
        case_ids = (
            work[case_id_col]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    else:
        case_ids = pd.Series(
            [
                str(idx)
                for idx in work.index
            ],
            index=work.index,
        )

    points = pd.DataFrame(
        {
            "Case_ID": case_ids.values,
            "Disease": disease_values.values,
            "Ward": work["_Report_Ward"].values,
            "Map_Ward": work["_Map_Ward"].values,
            "Latitude": work["_lat"].values,
            "Longitude": work["_lon"].values,
        }
    )

    points["Is_PE"] = (
        points["Ward"] == "PE"
    )

    points["Is_PN"] = (
        points["Ward"] == "PN"
    )

    # Assign cluster ID to every case point.
    points["_grid_lat"] = (
        points["Latitude"] / GRID_SIZE
    ).round() * GRID_SIZE

    points["_grid_lon"] = (
        points["Longitude"] / GRID_SIZE
    ).round() * GRID_SIZE

    points["Cluster ID"] = (
        points["_grid_lat"]
        .round(6)
        .astype(str)
        + "_"
        + points["_grid_lon"]
        .round(6)
        .astype(str)
    )

    return points


def add_hotspot_flags_to_case_points(
    case_points,
    hotspot_df,
):
    if case_points is None or case_points.empty:
        return pd.DataFrame()

    result = case_points.copy()

    result["Is_Hotspot"] = False
    result["PN_Hotspot"] = False
    result["PE_Hotspot"] = False

    if hotspot_df is None or hotspot_df.empty:
        return result

    hotspot_ids = set(
        hotspot_df["Cluster ID"]
        .astype(str)
        .tolist()
    )

    pn_hotspot_ids = set(
        hotspot_df.loc[
            hotspot_df["Has_PN"] == True,
            "Cluster ID",
        ]
        .astype(str)
        .tolist()
    )

    pe_hotspot_ids = set(
        hotspot_df.loc[
            hotspot_df["Has_PE"] == True,
            "Cluster ID",
        ]
        .astype(str)
        .tolist()
    )

    result["Cluster ID"] = (
        result["Cluster ID"]
        .astype(str)
    )

    result["Is_Hotspot"] = (
        result["Cluster ID"]
        .isin(hotspot_ids)
    )

    result["PN_Hotspot"] = (
        result["Is_PN"]
        & result["Cluster ID"].isin(
            pn_hotspot_ids
        )
    )

    result["PE_Hotspot"] = (
        result["Is_PE"]
        & result["Cluster ID"].isin(
            pe_hotspot_ids
        )
    )

    # Small point radius for ordinary points.
    result["Point_Radius"] = 28.0

    # PN hotspot points are slightly larger.
    result.loc[
        result["PN_Hotspot"],
        "Point_Radius",
    ] = 65.0

    # PE hotspot points are slightly larger.
    result.loc[
        result["PE_Hotspot"],
        "Point_Radius",
    ] = 55.0

    return result


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
        ward_series = df["_Report_Ward"]
    else:
        ward_col = get_ward_column(df)

        if ward_col is None:
            summary["Cases"] = 0
            return summary

        ward_series = (
            df[ward_col]
            .apply(normalise_ward)
        )

    counts = (
        ward_series
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
# CHOROPLETH SUMMARY
# PE + PN ARE COMBINED ONLY HERE
# ============================================================

def create_map_ward_summary(df):
    summary = pd.DataFrame(
        {
            "Ward": PROGRAMME_WARDS
        }
    )

    if df is None or df.empty:
        summary["Cases"] = 0
        summary["Map_Ward"] = summary["Ward"]
        return summary

    if "_Report_Ward" in df.columns:
        ward_series = df["_Report_Ward"]
    else:
        ward_col = get_ward_column(df)

        if ward_col is None:
            summary["Cases"] = 0
            summary["Map_Ward"] = summary["Ward"]
            return summary

        ward_series = (
            df[ward_col]
            .apply(normalise_ward)
        )

    temp = pd.DataFrame(
        {
            "Ward": ward_series
        }
    )

    # PE and PN are combined into P only for choropleth mapping.
    temp["Map_Ward"] = temp["Ward"].replace(
        {
            "PE": "P",
            "PN": "P",
        }
    )

    counts = (
        temp["Map_Ward"]
        .value_counts()
        .rename_axis("Map_Ward")
        .reset_index(name="Cases")
    )

    # Keep programme wards and add combined P.
    output_wards = [
        ward
        for ward in PROGRAMME_WARDS
        if ward not in ["PE", "PN"]
    ]

    output_wards.append("P")

    summary = pd.DataFrame(
        {
            "Ward": output_wards,
            "Map_Ward": output_wards,
        }
    )

    summary = summary.merge(
        counts,
        on="Map_Ward",
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
            value = clean_text(
                properties.get(key)
            )

            if value:
                return normalise_ward(value)

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
                150 - ratio * 100
            ),
            190,
        ]

    if ratio < 0.66:
        return [
            255,
            int(
                220
                - (
                    ratio - 0.33
                ) * 170
            ),
            60,
            205,
        ]

    return [
        int(
            255
            - (
                ratio - 0.66
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

    if ward_summary is None or ward_summary.empty:
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

        original_ward = (
            get_geojson_ward_name(
                properties
            )
        )

        # The authoritative boundary may contain PN but not PE.
        # For choropleth only, both are represented as P.
        map_ward = original_ward

        if original_ward in ["PE", "PN"]:
            map_ward = "P"

        cases = int(
            ward_cases.get(
                map_ward,
                0,
            )
        )

        properties["Programme Cases"] = cases

        properties["Ward Display"] = (
            original_ward
            or "Unknown"
        )

        properties["Map Ward"] = (
            map_ward
            or "Unknown"
        )

        properties["fill_color"] = (
            get_choropleth_color(
                cases,
                max_cases,
            )
        )

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
# MAP LAYERS
# ============================================================

def build_map(
    choropleth_geojson=None,
    hotspot_df=None,
    case_points=None,
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
            data=choropleth_geojson,
            pickable=True,
            stroked=True,
            filled=True,
            get_fill_color="properties.fill_color",
            get_line_color="properties.line_color",
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

        layers.append(ward_layer)

    # --------------------------------------------------------
    # HOTSPOT LAYERS
    # Drawn before case points so case points stay visible.
    # --------------------------------------------------------

    if (
        show_hotspots
        and hotspot_df is not None
        and not hotspot_df.empty
    ):
        all_hotspot_layer = pdk.Layer(
            "ScatterplotLayer",
            data=hotspot_df,
            get_position=[
                "Cluster_Longitude",
                "Cluster_Latitude",
            ],
            get_radius="Radius",
            get_fill_color=[
                220,
                40,
                40,
                105,
            ],
            get_line_color=[
                130,
                0,
                0,
                180,
            ],
            line_width_min_pixels=1,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
            radius_min_pixels=2,
            radius_max_pixels=9,
        )

        layers.append(
            all_hotspot_layer
        )

        # Separate PN hotspot highlight layer.
        pn_hotspots = hotspot_df.loc[
            hotspot_df["Has_PN"] == True
        ].copy()

        if not pn_hotspots.empty:
            pn_hotspots["PN_Radius"] = (
                pn_hotspots["Radius"]
                .clip(lower=65, upper=150)
            )

            pn_hotspot_layer = pdk.Layer(
                "ScatterplotLayer",
                data=pn_hotspots,
                get_position=[
                    "Cluster_Longitude",
                    "Cluster_Latitude",
                ],
                get_radius="PN_Radius",
                get_fill_color=[
                    255,
                    140,
                    0,
                    115,
                ],
                get_line_color=[
                    255,
                    80,
                    0,
                    255,
                ],
                line_width_min_pixels=2,
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
                radius_min_pixels=3,
                radius_max_pixels=11,
            )

            layers.append(
                pn_hotspot_layer
            )

    # --------------------------------------------------------
    # CASE POINTS
    # --------------------------------------------------------

    if (
        case_points is not None
        and not case_points.empty
    ):
        pe_points = case_points.loc[
            case_points["Is_PE"] == True
        ].copy()

        pn_points = case_points.loc[
            case_points["Is_PN"] == True
        ].copy()

        other_points = case_points.loc[
            ~case_points["Is_PE"]
            & ~case_points["Is_PN"]
        ].copy()

        # PE points.
        if not pe_points.empty:
            pe_layer = pdk.Layer(
                "ScatterplotLayer",
                data=pe_points,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius="Point_Radius",
                get_fill_color=[
                    30,
                    100,
                    255,
                    220,
                ],
                get_line_color=[
                    0,
                    45,
                    150,
                    255,
                ],
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
                radius_min_pixels=2,
                radius_max_pixels=8,
            )

            layers.append(pe_layer)

        # PN points.
        if not pn_points.empty:
            pn_layer = pdk.Layer(
                "ScatterplotLayer",
                data=pn_points,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius="Point_Radius",
                get_fill_color=[
                    255,
                    145,
                    0,
                    245,
                ],
                get_line_color=[
                    160,
                    70,
                    0,
                    255,
                ],
                line_width_min_pixels=2,
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
                radius_min_pixels=3,
                radius_max_pixels=9,
            )

            layers.append(pn_layer)

        # Other ward points.
        if not other_points.empty:
            other_layer = pdk.Layer(
                "ScatterplotLayer",
                data=other_points,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius="Point_Radius",
                get_fill_color=[
                    60,
                    150,
                    80,
                    190,
                ],
                get_line_color=[
                    30,
                    80,
                    40,
                    230,
                ],
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
                radius_min_pixels=2,
                radius_max_pixels=7,
            )

            layers.append(
                other_layer
            )

    # --------------------------------------------------------
    # MAP VIEW
    # --------------------------------------------------------

    if (
        case_points is not None
        and not case_points.empty
    ):
        if extent == "All Coordinates":
            center_lat = float(
                case_points["Latitude"].mean()
            )

            center_lon = float(
                case_points["Longitude"].mean()
            )

            zoom = 5.5

        else:
            center_lat = 19.0760
            center_lon = 72.8777
            zoom = 10

    elif (
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
            <b>Ward:</b> {Ward}<br/>
            <b>Map Ward:</b> {Map Ward}<br/>
            <b>Disease:</b> {Disease}<br/>
            <b>Case ID:</b> {Case_ID}<br/>
            <b>Cluster:</b> {Cluster ID}<br/>
            <b>Cluster Cases:</b> {Cluster_Cases}<br/>
            <b>Hotspot:</b> {Hotspot Classification}<br/>
            <b>Programme Cases:</b> {Programme Cases}
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

        disease_df = prepare_report_wards(
            disease_df
        )

        cases = len(disease_df)

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

        ward_summary = create_ward_summary(
            disease_df
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

            top_ward = top_row["Ward"]
            top_ward_cases = int(
                top_row["Cases"]
            )

        else:
            top_ward = "—"
            top_ward_cases = 0

        pe_cases = int(
            (
                disease_df[
                    "_Report_Ward"
                ]
                == "PE"
            ).sum()
        )

        pn_cases = int(
            (
                disease_df[
                    "_Report_Ward"
                ]
                == "PN"
            ).sum()
        )

        rows.append(
            {
                "Disease": disease,
                "Cases": cases,
                "Valid Coordinates": cases,
                "Hotspot Clusters": len(
                    hotspots
                ),
                "High Hotspots": high_hotspots,
                "PE Cases": pe_cases,
                "PN Cases": pn_cases,
                "Top Ward": top_ward,
                "Top Ward Cases": top_ward_cases,
            }
        )

    return pd.DataFrame(rows)


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

    disease_df = prepare_report_wards(
        disease_df
    )

    ward_summary = create_ward_summary(
        disease_df
    )

    map_ward_summary = (
        create_map_ward_summary(
            disease_df
        )
    )

    choropleth = None

    if bmc_geojson:
        choropleth = (
            prepare_bmc_choropleth(
                bmc_geojson,
                map_ward_summary,
            )
        )

    hotspots = create_hotspots(
        disease_df
    )

    case_points = create_case_points(
        disease_df
    )

    case_points = (
        add_hotspot_flags_to_case_points(
            case_points,
            hotspots,
        )
    )

    return (
        disease_df,
        ward_summary,
        hotspots,
        choropleth,
        case_points,
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
        result["Cluster_Latitude"]
    )

    result["Longitude"] = (
        result["Cluster_Longitude"]
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
        "Cluster ID",
        "Cluster_Cases",
        "Hotspot Classification",
        "Has_PE",
        "Has_PN",
        "Latitude",
        "Longitude",
    ]

    available = [
        c
        for c in preferred
        if c in result.columns
    ]

    return result[available]


# ============================================================
# DISEASE CHECKBOX SELECTOR
# ============================================================

def _geo_select_all_changed(diseases):
    if st.session_state.get(
        "geo_select_all",
        False,
    ):
        for i in range(len(diseases)):
            st.session_state[
                f"geo_disease_{i}"
            ] = True


def _geo_disease_changed():
    st.session_state[
        "geo_select_all"
    ] = False


def _geo_reset_diseases(diseases):
    st.session_state[
        "geo_select_all"
    ] = False

    for i in range(len(diseases)):
        st.session_state[
            f"geo_disease_{i}"
        ] = False


def disease_checkbox_selector(
    diseases,
):
    if not diseases:
        return []

    if (
        "geo_select_all"
        not in st.session_state
    ):
        st.session_state[
            "geo_select_all"
        ] = False

    for i in range(len(diseases)):
        key = f"geo_disease_{i}"

        if key not in st.session_state:
            st.session_state[key] = False

    control_col1, control_col2 = st.columns(
        [0.18, 0.82],
        gap="small",
    )

    with control_col1:
        st.checkbox(
            "Select All",
            key="geo_select_all",
            on_change=(
                _geo_select_all_changed,
                diseases,
            ),
        )

        if st.button(
            "Reset",
            key="geo_disease_reset",
            use_container_width=True,
        ):
            _geo_reset_diseases(
                diseases
            )
            st.rerun()

    with control_col2:
        st.caption(
            "Select one or more diseases for geographic comparison."
        )

        selected = []

        disease_columns = st.columns(
            min(4, max(1, len(diseases))),
            gap="small",
        )

        for i, disease in enumerate(
            diseases
        ):
            col = disease_columns[
                i % len(disease_columns)
            ]

            with col:
                checked = st.checkbox(
                    disease,
                    key=f"geo_disease_{i}",
                    on_change=(
                        _geo_disease_changed
                    ),
                )

                if checked:
                    selected.append(
                        disease
                    )

    return selected


# ============================================================
# LEGEND
# ============================================================

def render_map_legend(
    ward_summary,
    case_points=None,
    hotspot_df=None,
):
    pe_cases = 0
    pn_cases = 0

    if (
        case_points is not None
        and not case_points.empty
    ):
        pe_cases = int(
            case_points[
                "Is_PE"
            ].sum()
        )

        pn_cases = int(
            case_points[
                "Is_PN"
            ].sum()
        )

    other_cases = 0

    if (
        ward_summary is not None
        and not ward_summary.empty
    ):
        other_cases = int(
            ward_summary.loc[
                ~ward_summary["Ward"].isin(
                    ["PE", "PN"]
                ),
                "Cases",
            ].sum()
        )

    hotspot_count = (
        len(hotspot_df)
        if hotspot_df is not None
        else 0
    )

    pn_hotspot_count = 0

    if (
        hotspot_df is not None
        and not hotspot_df.empty
        and "Has_PN" in hotspot_df.columns
    ):
        pn_hotspot_count = int(
            hotspot_df["Has_PN"].sum()
        )

    p_cases = pe_cases + pn_cases

    st.markdown(
        f"""
        <div style="
            border:1px solid #d9d9d9;
            border-radius:8px;
            padding:10px 14px;
            margin-top:8px;
            margin-bottom:10px;
            background:#fafafa;
            font-size:13px;
        ">
            <b>Map Legend</b>
            &nbsp;&nbsp;
            <span>● PE: {pe_cases:,}</span>
            &nbsp;&nbsp;
            <span>● PN: {pn_cases:,}</span>
            &nbsp;&nbsp;
            <span>● Other Wards: {other_cases:,}</span>
            &nbsp;&nbsp;
            <span>● Hotspots: {hotspot_count:,}</span>
            &nbsp;&nbsp;
            <span>● PN Hotspots: {pn_hotspot_count:,}</span>
            &nbsp;&nbsp;
            <span><b>P = PE + PN: {p_cases:,}</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

    coordinate_df = prepare_report_wards(
        coordinate_df
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

    disease_col = get_disease_column(
        filtered_df
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

    bmc_geojson = load_bmc_wards()

    # ========================================================
    # MAP CONTROLS
    # ========================================================

    control_left, control_right = (
        st.columns(
            [0.35, 0.65],
            gap="small",
        )
    )

    with control_left:
        extent = st.radio(
            "Map Extent",
            [
                "BMC / Mumbai Focus",
                "All Coordinates",
            ],
            horizontal=True,
            key="geo_extent",
        )

    with control_right:
        selected_diseases = (
            disease_checkbox_selector(
                diseases
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
            .isin(selected_diseases)
        ].copy()

        disease_status = ", ".join(
            selected_diseases
        )

    else:
        map_df = coordinate_df.copy()
        disease_status = "All Diseases"

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

    overall_hotspots = create_hotspots(
        map_df
    )

    # ========================================================
    # OVERALL CASE POINTS
    # ========================================================

    overall_case_points = create_case_points(
        map_df
    )

    overall_case_points = (
        add_hotspot_flags_to_case_points(
            overall_case_points,
            overall_hotspots,
        )
    )

    # ========================================================
    # OVERALL WARD SUMMARY
    # PE AND PN REMAIN SEPARATE
    # ========================================================

    overall_ward_summary = (
        create_ward_summary(
            map_df
        )
    )

    # ========================================================
    # OVERALL MAP WARD SUMMARY
    # PE + PN COMBINED AS P ONLY FOR CHOROPLETH
    # ========================================================

    overall_map_ward_summary = (
        create_map_ward_summary(
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
                overall_map_ward_summary,
            )
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
            "High Hotspots",
            f"{high_hotspots:,}",
        )

    # ========================================================
    # PE / PN SUMMARY
    # ========================================================

    pe_count = int(
        (
            overall_case_points["Is_PE"]
        ).sum()
    )

    pn_count = int(
        (
            overall_case_points["Is_PN"]
        ).sum()
    )

    pn_hotspot_points = int(
        (
            overall_case_points[
                "PN_Hotspot"
            ]
        ).sum()
    )

    st.caption(
        f"PE Cases: **{pe_count:,}** | "
        f"PN Cases: **{pn_count:,}** | "
        f"PN Cases Located in Hotspot Clusters: "
        f"**{pn_hotspot_points:,}**"
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
            "case burden. PE and PN are combined as "
            "P only for choropleth mapping."
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
                case_points=overall_case_points,
                extent=extent,
                show_hotspots=True,
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
            )

            render_map_legend(
                overall_ward_summary,
                overall_case_points,
                overall_hotspots,
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
                        "Has_PE",
                        "Has_PN",
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
                        "Has_PE":
                            "PE Present",
                        "Has_PN":
                            "PN Present",
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

            # ------------------------------------------------
            # PN HOTSPOT SUMMARY
            # ------------------------------------------------

            pn_hotspots = overall_hotspots.loc[
                overall_hotspots["Has_PN"] == True
            ].copy()

            if not pn_hotspots.empty:
                st.subheader(
                    "PN Hotspot Locations"
                )

                pn_display = (
                    pn_hotspots[
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
                    .rename(
                        columns={
                            "Cluster_Cases":
                                "Cluster Cases",
                            "Cluster_Latitude":
                                "Latitude",
                            "Cluster_Longitude":
                                "Longitude",
                        }
                    )
                )

                st.dataframe(
                    pn_display,
                    use_container_width=True,
                    hide_index=True,
                )

            # ------------------------------------------------
            # HOTSPOT EXCEL
            # ------------------------------------------------

            export_df = (
                download_hotspot_data(
                    overall_hotspots,
                    map_df,
                    disease_col,
                )
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
                    "Download Hotspot Data (Excel)",
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
                col = comparison_cols[
                    idx % len(comparison_cols)
                ]

                with col:
                    st.markdown(
                        f"""
                        **{row['Disease']}**

                        - Cases: **{int(row['Cases']):,}**
                        - Coordinates: **{int(row['Valid Coordinates']):,}**
                        - Hotspots: **{int(row['Hotspot Clusters']):,}**
                        - High Hotspots: **{int(row['High Hotspots']):,}**
                        - PE Cases: **{int(row['PE Cases']):,}**
                        - PN Cases: **{int(row['PN Cases']):,}**
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

            for disease in selected_for_table:
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

                disease_df = (
                    prepare_report_wards(
                        disease_df
                    )
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

            for disease in selected_for_table:
                if disease in ward_comparison.columns:
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

            comparison_buffer = io.BytesIO()

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
                data=comparison_buffer.getvalue(),
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

            if len(selected_for_maps) > 6:
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
                    len(row_diseases),
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
                            disease_case_points,
                        ) = get_disease_map_data(
                            coordinate_df,
                            disease_col,
                            disease,
                            bmc_geojson,
                        )

                        st.markdown(
                            f"**{disease}**"
                        )

                        st.caption(
                            f"Cases: "
                            f"{len(disease_df):,} | "
                            f"Hotspots: "
                            f"{len(disease_hotspots):,} | "
                            f"PN Cases: "
                            f"{int(disease_case_points['Is_PN'].sum()):,}"
                        )

                        disease_deck = build_map(
                            choropleth_geojson=(
                                disease_choropleth
                            ),
                            hotspot_df=(
                                disease_hotspots
                            ),
                            case_points=(
                                disease_case_points
                            ),
                            extent=(
                                "BMC / Mumbai Focus"
                            ),
                            show_hotspots=True,
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
                            [
                                [
                                    "Ward",
                                    "Cases",
                                ]
                            ]
                            .copy()
                        )

                        st.dataframe(
                            top5,
                            use_container_width=True,
                            hide_index=True,
                        )

            st.caption(
                "Each disease map uses the same BMC ward "
                "boundary framework. Higher ward-wise burden "
                "is shown with stronger choropleth shading. "
                "PE and PN are combined as P only for "
                "choropleth calculation."
            )

    # ========================================================
    # TAB 4 — COMBINED GEOGRAPHIC VIEW
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
        )

        st.pydeck_chart(
            combined_deck,
            use_container_width=True,
        )

        render_map_legend(
            overall_ward_summary,
            overall_case_points,
            overall_hotspots,
        )

        st.caption(
            "Ward polygons show combined burden of the "
            "currently selected disease(s). Red circles "
            "represent hotspot clusters. PE and PN case "
            "points remain separately visible. PN cases "
            "inside hotspot clusters are highlighted."
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
        # PE / PN SUMMARY
        # ----------------------------------------------------

        st.subheader(
            "PE and PN Geographic Summary"
        )

        pe_pn_summary = pd.DataFrame(
            {
                "Category": [
                    "PE",
                    "PN",
                    "P = PE + PN",
                ],
                "Cases": [
                    pe_count,
                    pn_count,
                    pe_count + pn_count,
                ],
                "Cases in Hotspot Clusters": [
                    int(
                        overall_case_points.loc[
                            overall_case_points[
                                "PE_Hotspot"
                            ],
                            "PE_Hotspot",
                        ].sum()
                    ),
                    pn_hotspot_points,
                    int(
                        overall_case_points.loc[
                            overall_case_points[
                                "Is_PE"
                            ]
                            | overall_case_points[
                                "Is_PN"
                            ],
                            "Is_Hotspot",
                        ].sum()
                    ),
                ],
            }
        )

        st.dataframe(
            pe_pn_summary,
            use_container_width=True,
            hide_index=True,
        )

        # ----------------------------------------------------
        # WARD EXCEL
        # ----------------------------------------------------

        ward_buffer = io.BytesIO()

        with pd.ExcelWriter(
            ward_buffer,
            engine="openpyxl",
        ) as writer:
            combined_ward.to_excel(
                writer,
                index=False,
                sheet_name="Ward Burden",
            )

            pe_pn_summary.to_excel(
                writer,
                index=False,
                sheet_name="PE PN Summary",
            )

        st.download_button(
            "Download Ward-wise Burden (Excel)",
            data=ward_buffer.getvalue(),
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
        get_ward_column(map_df),
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
            export_columns.append(col)

    if export_columns:
        csv_df = (
            map_df[
                export_columns
            ]
            .copy()
        )

        csv_data = (
            csv_df
            .to_csv(index=False)
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
