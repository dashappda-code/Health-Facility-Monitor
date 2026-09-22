import io
import re

import pandas as pd
import requests
import streamlit as st
import pydeck as pdk


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

# PE + PN are temporarily combined only for choropleth display.
MAP_COMBINED_WARD = "P"

# Geographic grid size used for hotspot detection.
GRID_SIZE = 0.01

# Public BMC ward boundary source.
BMC_GEOJSON_URL = (
    "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/"
    "master/Mumbai/MCGM/MCGM_Wards.geojson"
)


# ============================================================
# BASIC HELPERS
# ============================================================

def find_column(df, candidates):
    """
    Return the first matching column from candidates.
    Matching is case-insensitive and whitespace-insensitive.
    """
    if df is None or df.empty:
        return None

    normalized = {}

    for col in df.columns:
        key = str(col).strip().lower()
        normalized[key] = col

    for candidate in candidates:
        key = str(candidate).strip().lower()

        if key in normalized:
            return normalized[key]

    return None


def clean_text(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


def normalise_ward(value):
    """
    Normalize ward labels while preserving the programme ward master.
    """
    text = clean_text(value)

    if not text:
        return "Unknown"

    text = (
        text.replace("-", " ")
        .replace("_", " ")
        .replace(".", " ")
        .strip()
        .upper()
    )

    compact = re.sub(r"[^A-Z0-9]", "", text)

    mapping = {
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
        "P": "P",
    }

    if compact in mapping:
        return mapping[compact]

    return text


def get_disease_column(df):
    return find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "Disease_Name",
            "DiseaseName",
            "Condition",
            "Diagnosis",
        ],
    )


def get_ward_column(df):
    return find_column(
        df,
        [
            "_Report_Ward",
            "Report Ward",
            "Report_Ward",
            "Ward",
            "Ward Name",
            "Ward_Name",
            "Administrative Ward",
            "Administrative_Ward",
            "Programme Ward",
            "Programme_Ward",
        ],
    )


def get_facility_column(df):
    return find_column(
        df,
        [
            "Facility",
            "Facility Name",
            "Facility_Name",
            "Health Facility",
            "Health_Facility",
            "Hospital",
            "Hospital Name",
            "Hospital_Name",
        ],
    )


def get_case_id_column(df):
    return find_column(
        df,
        [
            "Case ID",
            "Case_ID",
            "CaseID",
            "Patient ID",
            "Patient_ID",
            "PatientID",
            "ID",
        ],
    )


# ============================================================
# COORDINATE PREPARATION
# ============================================================

def prepare_coordinates(df):
    """
    Prepare latitude and longitude columns.

    Important:
    Coordinates are NOT artificially restricted to BMC/Mumbai.
    All valid coordinates are retained.
    """
    if df is None:
        return pd.DataFrame(), 0

    work = df.copy()

    lat_col = find_column(
        work,
        [
            "Address Latitude",
            "Address_Latitude",
            "Latitude",
            "Lat",
            "address latitude",
        ],
    )

    lon_col = find_column(
        work,
        [
            "Address Longitude",
            "Address_Longitude",
            "Longitude",
            "Long",
            "Lon",
            "address longitude",
        ],
    )

    if lat_col is None or lon_col is None:
        work["_lat"] = pd.NA
        work["_lon"] = pd.NA
        return work, len(work)

    work["_lat"] = pd.to_numeric(
        work[lat_col],
        errors="coerce",
    )

    work["_lon"] = pd.to_numeric(
        work[lon_col],
        errors="coerce",
    )

    invalid_mask = (
        work["_lat"].isna()
        | work["_lon"].isna()
        | ~work["_lat"].between(-90, 90)
        | ~work["_lon"].between(-180, 180)
    )

    invalid_count = int(invalid_mask.sum())

    return work, invalid_count


# ============================================================
# WARD PREPARATION
# ============================================================

def ensure_report_ward(df):
    """
    Ensure _Report_Ward exists.
    """
    work = df.copy()

    if "_Report_Ward" in work.columns:
        work["_Report_Ward"] = work["_Report_Ward"].apply(
            normalise_ward
        )
        return work

    ward_col = get_ward_column(work)

    if ward_col is None:
        work["_Report_Ward"] = "Unknown"
    else:
        work["_Report_Ward"] = work[ward_col].apply(
            normalise_ward
        )

    return work


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):
    """
    Create programme ward summary.

    PE and PN remain separate here.
    """
    if df is None or df.empty:
        return pd.DataFrame(
            {
                "Ward": PROGRAMME_WARDS,
                "Cases": [0] * len(PROGRAMME_WARDS),
            }
        )

    work = ensure_report_ward(df)

    counts = (
        work["_Report_Ward"]
        .value_counts(dropna=False)
        .rename_axis("Ward")
        .reset_index(name="Cases")
    )

    counts["Ward"] = counts["Ward"].apply(normalise_ward)

    master = pd.DataFrame(
        {
            "Ward": PROGRAMME_WARDS,
        }
    )

    summary = master.merge(
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


def create_map_ward_summary(df):
    """
    Choropleth summary.

    PE + PN are combined into temporary map ward P.
    PE and PN remain separate in the management summary.
    """
    summary = create_ward_summary(df)

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
        ~summary["Ward"].isin(["PE", "PN"])
    ].copy()

    combined = pd.DataFrame(
        {
            "Ward": [MAP_COMBINED_WARD],
            "Cases": [pe_cases + pn_cases],
        }
    )

    result = pd.concat(
        [other, combined],
        ignore_index=True,
    )

    return result


# ============================================================
# HOTSPOT CREATION
# ============================================================

def create_hotspots(df):
    """
    Create geographic hotspots from valid coordinates.

    Hotspots are calculated from actual latitude/longitude.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    work, _ = prepare_coordinates(df)

    work = work[
        work["_lat"].notna()
        & work["_lon"].notna()
    ].copy()

    if work.empty:
        return pd.DataFrame()

    disease_col = get_disease_column(work)

    if disease_col is None:
        work["Disease"] = "Unknown"
    else:
        work["Disease"] = (
            work[disease_col]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
        )

    ward_col = "_Report_Ward"

    if ward_col not in work.columns:
        work = ensure_report_ward(work)

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

    grouped = (
        work.groupby(
            [
                "Cluster ID",
                "_grid_lat",
                "_grid_lon",
            ],
            dropna=False,
        )
        .agg(
            Cluster_Cases=("_lat", "size"),
            Disease_Count=("Disease", "nunique"),
            Ward_Count=(ward_col, "nunique"),
        )
        .reset_index()
    )

    grouped["Cluster_Latitude"] = grouped["_grid_lat"]
    grouped["Cluster_Longitude"] = grouped["_grid_lon"]

    # Keep clusters with at least 2 cases.
    hotspots = grouped[
        grouped["Cluster_Cases"] >= 2
    ].copy()

    if hotspots.empty:
        return hotspots

    hotspots = hotspots.sort_values(
        "Cluster_Cases",
        ascending=False,
    ).reset_index(drop=True)

    hotspots["Hotspot Rank"] = (
        hotspots.index + 1
    )

    hotspots["Hotspot Classification"] = "Hotspot"

    return hotspots


# ============================================================
# CASE POINT PREPARATION
# ============================================================

def create_case_points(df, hotspot_df=None):
    """
    Prepare individual geographic case points.

    PE and PN remain separate as actual point layers.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    work, _ = prepare_coordinates(df)

    work = work[
        work["_lat"].notna()
        & work["_lon"].notna()
    ].copy()

    if work.empty:
        return pd.DataFrame()

    work = ensure_report_ward(work)

    disease_col = get_disease_column(work)

    if disease_col is None:
        work["Disease"] = "Unknown"
    else:
        work["Disease"] = (
            work[disease_col]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
        )

    case_id_col = get_case_id_column(work)

    if case_id_col is None:
        work["CaseID"] = (
            work.index.astype(str)
        )
    else:
        work["CaseID"] = (
            work[case_id_col]
            .fillna("")
            .astype(str)
        )

    facility_col = get_facility_column(work)

    if facility_col is None:
        work["Facility"] = ""
    else:
        work["Facility"] = (
            work[facility_col]
            .fillna("")
            .astype(str)
        )

    work["_grid_lat"] = (
        work["_lat"] / GRID_SIZE
    ).round() * GRID_SIZE

    work["_grid_lon"] = (
        work["_lon"] / GRID_SIZE
    ).round() * GRID_SIZE

    work["ClusterID"] = (
        work["_grid_lat"].round(6).astype(str)
        + "_"
        + work["_grid_lon"].round(6).astype(str)
    )

    cluster_cases = (
        work["ClusterID"]
        .value_counts()
        .to_dict()
    )

    work["ClusterCases"] = (
        work["ClusterID"]
        .map(cluster_cases)
        .fillna(1)
        .astype(int)
    )

    hotspot_ids = set()

    if (
        hotspot_df is not None
        and not hotspot_df.empty
        and "Cluster ID" in hotspot_df.columns
    ):
        hotspot_ids = set(
            hotspot_df["Cluster ID"]
            .astype(str)
            .tolist()
        )

    work["PNHotspot"] = (
        (work["_Report_Ward"] == "PN")
        & work["ClusterID"].isin(hotspot_ids)
    )

    work["Ward"] = work["_Report_Ward"]

    work["WardDisplay"] = work["_Report_Ward"]

    work["Point_Radius"] = 28
    work["Highlight_Radius"] = 60

    work["HotspotClassification"] = work[
        "ClusterID"
    ].isin(hotspot_ids).map(
        {
            True: "Hotspot",
            False: "Regular Area",
        }
    )

    return work[
        [
            "_lat",
            "_lon",
            "Ward",
            "WardDisplay",
            "Disease",
            "CaseID",
            "Facility",
            "ClusterID",
            "ClusterCases",
            "PNHotspot",
            "HotspotClassification",
            "Point_Radius",
            "Highlight_Radius",
        ]
    ].copy()


# ============================================================
# BMC GEOJSON
# ============================================================

@st.cache_data(ttl=86400, show_spinner=False)
def load_bmc_wards():
    """
    Download and cache BMC ward boundaries.
    """
    try:
        response = requests.get(
            BMC_GEOJSON_URL,
            timeout=20,
        )

        response.raise_for_status()

        return response.json()

    except Exception:
        return None


def get_geojson_ward_name(feature):
    """
    Extract ward name from common GeoJSON property names.
    """
    if not isinstance(feature, dict):
        return ""

    properties = feature.get(
        "properties",
        {},
    )

    if not isinstance(properties, dict):
        return ""

    candidates = [
        "ward",
        "Ward",
        "WARD",
        "name",
        "Name",
        "NAME",
        "ward_name",
        "Ward_Name",
        "WARDS",
        "MCGM_WARD",
        "MCGM_Ward",
    ]

    for candidate in candidates:
        if candidate in properties:
            value = clean_text(
                properties[candidate]
            )

            if value:
                return normalise_ward(value)

    return ""


def get_fill_values(cases, max_cases):
    """
    Generate choropleth fill values as simple numeric columns.
    """
    try:
        cases = float(cases)
    except Exception:
        cases = 0.0

    try:
        max_cases = float(max_cases)
    except Exception:
        max_cases = 0.0

    if max_cases <= 0:
        intensity = 0.0
    else:
        intensity = cases / max_cases

    intensity = max(
        0.0,
        min(
            1.0,
            intensity,
        ),
    )

    red = int(
        245 - (intensity * 80)
    )

    green = int(
        245 - (intensity * 190)
    )

    blue = int(
        245 - (intensity * 220)
    )

    alpha = 150

    return (
        red,
        green,
        blue,
        alpha,
    )


def prepare_bmc_choropleth(
    geojson,
    ward_summary,
):
    """
    Prepare BMC ward GeoJSON.

    PE + PN are temporarily represented by P.

    No artificial PE/PN polygon is created.
    If the boundary source has PE/PN polygons, only one
    canonical polygon is used for the combined P display.
    """
    if geojson is None:
        return None

    if not isinstance(
        geojson,
        dict,
    ):
        return None

    features = geojson.get(
        "features",
        [],
    )

    if not features:
        return None

    summary = ward_summary.copy()

    summary["Ward"] = summary[
        "Ward"
    ].apply(normalise_ward)

    summary["Cases"] = pd.to_numeric(
        summary["Cases"],
        errors="coerce",
    ).fillna(0)

    lookup = dict(
        zip(
            summary["Ward"],
            summary["Cases"],
        )
    )

    max_cases = float(
        summary["Cases"].max()
    ) if not summary.empty else 0.0

    # Find canonical polygon for combined P.
    canonical_p_index = None

    for index, feature in enumerate(features):
        ward = get_geojson_ward_name(
            feature
        )

        if ward == "P":
            canonical_p_index = index
            break

    if canonical_p_index is None:
        for preferred in [
            "PN",
            "PE",
        ]:
            for index, feature in enumerate(features):
                ward = get_geojson_ward_name(
                    feature
                )

                if ward == preferred:
                    canonical_p_index = index
                    break

            if canonical_p_index is not None:
                break

    new_features = []

    for index, feature in enumerate(features):
        new_feature = dict(feature)

        properties = dict(
            feature.get(
                "properties",
                {},
            )
        )

        source_ward = get_geojson_ward_name(
            feature
        )

        if source_ward in [
            "PE",
            "PN",
        ]:
            map_ward = "P"
        else:
            map_ward = source_ward

        if (
            map_ward == "P"
            and canonical_p_index is not None
            and index != canonical_p_index
        ):
            cases = 0
        else:
            cases = float(
                lookup.get(
                    map_ward,
                    0,
                )
            )

        (
            fill_r,
            fill_g,
            fill_b,
            fill_a,
        ) = get_fill_values(
            cases,
            max_cases,
        )

        if map_ward == "P":
            ward_display = "P (PE + PN)"
        else:
            ward_display = (
                source_ward
                if source_ward
                else "Unknown"
            )

        properties[
            "WardDisplay"
        ] = ward_display

        properties[
            "MapWard"
        ] = map_ward

        properties[
            "ProgrammeCases"
        ] = int(cases)

        properties[
            "Fill_R"
        ] = fill_r

        properties[
            "Fill_G"
        ] = fill_g

        properties[
            "Fill_B"
        ] = fill_b

        properties[
            "Fill_A"
        ] = fill_a

        new_feature[
            "properties"
        ] = properties

        new_features.append(
            new_feature
        )

    return {
        "type": "FeatureCollection",
        "features": new_features,
    }


# ============================================================
# PYDECK MAP
# ============================================================

def build_map(
    choropleth_geojson=None,
    hotspot_df=None,
    case_points=None,
    extent="BMC + All Valid Coordinates",
    show_hotspots=True,
):
    """
    Build the geographic map.

    Important:
    All pydeck properties use simple values or dataframe fields.
    No Python callbacks, lambdas or unsupported JSON expressions.
    """

    layers = []

    # --------------------------------------------------------
    # Ward boundary layer
    # --------------------------------------------------------

    if choropleth_geojson is not None:

        boundary_layer = pdk.Layer(
            "GeoJsonLayer",
            data=choropleth_geojson,
            pickable=True,
            stroked=True,
            filled=True,
            get_fill_color=[
                "properties.Fill_R",
                "properties.Fill_G",
                "properties.Fill_B",
                "properties.Fill_A",
            ],
            get_line_color=[
                70,
                70,
                70,
                220,
            ],
            get_line_width=1,
            line_width_min_pixels=1,
        )

        layers.append(
            boundary_layer
        )

    # --------------------------------------------------------
    # Hotspot layer
    # --------------------------------------------------------

    if (
        show_hotspots
        and hotspot_df is not None
        and not hotspot_df.empty
    ):

        hotspot_plot = hotspot_df.copy()

        if "Cluster_Cases" not in hotspot_plot.columns:
            hotspot_plot[
                "Cluster_Cases"
            ] = 1

        hotspot_plot[
            "Cluster_Cases"
        ] = pd.to_numeric(
            hotspot_plot[
                "Cluster_Cases"
            ],
            errors="coerce",
        ).fillna(1)

        hotspot_plot[
            "Display_Radius"
        ] = (
            45
            + hotspot_plot[
                "Cluster_Cases"
            ]
            .clip(
                lower=1,
                upper=20,
            )
            * 4
        ).clip(
            lower=45,
            upper=125,
        )

        hotspot_plot[
            "Hotspot_R"
        ] = 220

        hotspot_plot[
            "Hotspot_G"
        ] = 40

        hotspot_plot[
            "Hotspot_B"
        ] = 40

        hotspot_plot[
            "Hotspot_A"
        ] = 65

        hotspot_layer = pdk.Layer(
            "ScatterplotLayer",
            data=hotspot_plot,
            get_position=[
                "Cluster_Longitude",
                "Cluster_Latitude",
            ],
            get_radius="Display_Radius",
            get_fill_color=[
                "Hotspot_R",
                "Hotspot_G",
                "Hotspot_B",
                "Hotspot_A",
            ],
            get_line_color=[
                180,
                0,
                0,
                180,
            ],
            get_line_width=1,
            stroked=True,
            filled=True,
            radius_min_pixels=2,
            radius_max_pixels=9,
            pickable=True,
        )

        layers.append(
            hotspot_layer
        )

    # --------------------------------------------------------
    # Case point layers
    # --------------------------------------------------------

    if (
        case_points is not None
        and not case_points.empty
    ):

        points = case_points.copy()

        if "Point_Radius" not in points.columns:
            points[
                "Point_Radius"
            ] = 28

        if "Highlight_Radius" not in points.columns:
            points[
                "Highlight_Radius"
            ] = 60

        # ----------------------------------------------------
        # PN hotspot highlight
        # ----------------------------------------------------

        if "PNHotspot" in points.columns:

            pn_hotspot = points[
                (
                    points["Ward"]
                    == "PN"
                )
                & (
                    points["PNHotspot"]
                    == True
                )
            ].copy()

            if not pn_hotspot.empty:

                pn_hotspot[
                    "Highlight_R"
                ] = 255

                pn_hotspot[
                    "Highlight_G"
                ] = 165

                pn_hotspot[
                    "Highlight_B"
                ] = 0

                pn_hotspot[
                    "Highlight_A"
                ] = 35

                pn_highlight_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=pn_hotspot,
                    get_position=[
                        "_lon",
                        "_lat",
                    ],
                    get_radius="Highlight_Radius",
                    get_fill_color=[
                        "Highlight_R",
                        "Highlight_G",
                        "Highlight_B",
                        "Highlight_A",
                    ],
                    get_line_color=[
                        255,
                        140,
                        0,
                        255,
                    ],
                    get_line_width=2,
                    stroked=True,
                    filled=True,
                    radius_min_pixels=2,
                    radius_max_pixels=8,
                    pickable=True,
                )

                layers.append(
                    pn_highlight_layer
                )

        # ----------------------------------------------------
        # PE points
        # ----------------------------------------------------

        pe_points = points[
            points["Ward"] == "PE"
        ].copy()

        if not pe_points.empty:

            pe_points[
                "Point_Radius"
            ] = 28

            pe_layer = pdk.Layer(
                "ScatterplotLayer",
                data=pe_points,
                get_position=[
                    "_lon",
                    "_lat",
                ],
                get_radius="Point_Radius",
                get_fill_color=[
                    0,
                    110,
                    220,
                    220,
                ],
                get_line_color=[
                    0,
                    55,
                    120,
                    255,
                ],
                get_line_width=1,
                stroked=True,
                filled=True,
                radius_min_pixels=2,
                radius_max_pixels=6,
                pickable=True,
            )

            layers.append(
                pe_layer
            )

        # ----------------------------------------------------
        # PN points
        # ----------------------------------------------------

        pn_points = points[
            points["Ward"] == "PN"
        ].copy()

        if not pn_points.empty:

            pn_points[
                "Point_Radius"
            ] = 28

            pn_layer = pdk.Layer(
                "ScatterplotLayer",
                data=pn_points,
                get_position=[
                    "_lon",
                    "_lat",
                ],
                get_radius="Point_Radius",
                get_fill_color=[
                    0,
                    170,
                    90,
                    230,
                ],
                get_line_color=[
                    0,
                    90,
                    45,
                    255,
                ],
                get_line_width=1,
                stroked=True,
                filled=True,
                radius_min_pixels=2,
                radius_max_pixels=6,
                pickable=True,
            )

            layers.append(
                pn_layer
            )

        # ----------------------------------------------------
        # Other ward points
        # ----------------------------------------------------

        other_points = points[
            ~points["Ward"].isin(
                [
                    "PE",
                    "PN",
                ]
            )
        ].copy()

        if not other_points.empty:

            other_points[
                "Point_Radius"
            ] = 25

            other_layer = pdk.Layer(
                "ScatterplotLayer",
                data=other_points,
                get_position=[
                    "_lon",
                    "_lat",
                ],
                get_radius="Point_Radius",
                get_fill_color=[
                    90,
                    90,
                    90,
                    190,
                ],
                get_line_color=[
                    40,
                    40,
                    40,
                    220,
                ],
                get_line_width=1,
                stroked=True,
                filled=True,
                radius_min_pixels=2,
                radius_max_pixels=5,
                pickable=True,
            )

            layers.append(
                other_layer
            )

    # --------------------------------------------------------
    # Map centre
    # --------------------------------------------------------

    center_lat = 19.0760
    center_lon = 72.8777

    if (
        case_points is not None
        and not case_points.empty
    ):

        valid_points = case_points[
            case_points["_lat"].notna()
            & case_points["_lon"].notna()
        ].copy()

        if not valid_points.empty:

            center_lat = float(
                valid_points[
                    "_lat"
                ].mean()
            )

            center_lon = float(
                valid_points[
                    "_lon"
                ].mean()
            )

    elif (
        hotspot_df is not None
        and not hotspot_df.empty
    ):

        valid_hotspots = hotspot_df[
            hotspot_df[
                "Cluster_Latitude"
            ].notna()
            & hotspot_df[
                "Cluster_Longitude"
            ].notna()
        ].copy()

        if not valid_hotspots.empty:

            center_lat = float(
                valid_hotspots[
                    "Cluster_Latitude"
                ].mean()
            )

            center_lon = float(
                valid_hotspots[
                    "Cluster_Longitude"
                ].mean()
            )

    if extent == "BMC Focus":
        zoom = 10.5
    else:
        zoom = 5.5

    # --------------------------------------------------------
    # Tooltip
    # --------------------------------------------------------

    tooltip = {
        "html": """
        <div style="font-family:Arial;font-size:12px;">
            <b>Ward:</b> {WardDisplay}<br/>
            <b>Disease:</b> {Disease}<br/>
            <b>Case ID:</b> {CaseID}<br/>
            <b>Facility:</b> {Facility}<br/>
            <b>Cluster:</b> {ClusterID}<br/>
            <b>Cluster Cases:</b> {ClusterCases}<br/>
            <b>PN Hotspot:</b> {PNHotspot}
        </div>
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black",
        },
    }

    # --------------------------------------------------------
    # Deck
    # --------------------------------------------------------

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=zoom,
            pitch=0,
            bearing=0,
        ),
        tooltip=tooltip,
        map_style=None,
    )

    return deck

# ============================================================
# MAP LEGEND
# ============================================================

def render_map_legend(
    ward_summary,
    hotspot_df=None,
    case_points=None,
):
    """
    Render map legend and PE/PN summary.
    """

    if ward_summary is None:
        return

    summary = ward_summary.copy()

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

    total_cases = int(
        summary["Cases"].sum()
    )

    other_cases = max(
        0,
        total_cases
        - pe_cases
        - pn_cases,
    )

    combined_p = (
        pe_cases
        + pn_cases
    )

    hotspot_count = 0

    if (
        hotspot_df is not None
        and not hotspot_df.empty
    ):
        hotspot_count = len(
            hotspot_df
        )

    pn_hotspot_cases = 0

    if (
        case_points is not None
        and not case_points.empty
        and "PNHotspot" in case_points.columns
    ):
        pn_hotspot_cases = int(
            (
                (
                    case_points["Ward"]
                    == "PN"
                )
                & (
                    case_points[
                        "PNHotspot"
                    ]
                    == True
                )
            ).sum()
        )

    st.markdown(
        f"""
        <div style="
            border:1px solid #d9d9d9;
            border-radius:8px;
            padding:10px 14px;
            margin-top:8px;
            margin-bottom:12px;
            background:#fafafa;
            font-size:13px;
        ">
            <b>Map Legend</b>
            <span style="margin-left:18px;">
                <span style="
                    display:inline-block;
                    width:12px;
                    height:12px;
                    border-radius:50%;
                    background:#006edc;
                    margin-right:5px;
                "></span>
                PE: {pe_cases:,}
            </span>

            <span style="margin-left:16px;">
                <span style="
                    display:inline-block;
                    width:12px;
                    height:12px;
                    border-radius:50%;
                    background:#00aa5a;
                    margin-right:5px;
                "></span>
                PN: {pn_cases:,}
            </span>

            <span style="margin-left:16px;">
                <span style="
                    display:inline-block;
                    width:12px;
                    height:12px;
                    border-radius:50%;
                    background:#5a5a5a;
                    margin-right:5px;
                "></span>
                Other Wards: {other_cases:,}
            </span>

            <span style="margin-left:16px;">
                <span style="
                    display:inline-block;
                    width:12px;
                    height:12px;
                    border-radius:50%;
                    background:#dc2828;
                    margin-right:5px;
                "></span>
                Hotspots: {hotspot_count:,}
            </span>

            <span style="margin-left:16px;">
                <b>P = PE + PN: {combined_p:,}</b>
            </span>

            <span style="margin-left:16px;">
                <b>PN cases in hotspot areas: {pn_hotspot_cases:,}</b>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# DISEASE CHECKBOX CALLBACKS
# ============================================================

def _geo_select_all_changed(diseases):
    """
    Select or clear all disease checkboxes.
    """
    value = st.session_state.get(
        "geo_select_all",
        False,
    )

    for i in range(
        len(diseases)
    ):
        st.session_state[
            f"geo_disease_{i}"
        ] = value


def _geo_disease_changed():
    """
    Individual disease selection clears Select All.
    Other selected diseases remain unchanged.
    """
    st.session_state[
        "geo_select_all"
    ] = False


def _geo_reset_diseases(diseases):
    """
    Reset all disease selections.
    """
    st.session_state[
        "geo_select_all"
    ] = False

    for i in range(
        len(diseases)
    ):
        st.session_state[
            f"geo_disease_{i}"
        ] = False


# ============================================================
# DISEASE CHECKBOX SELECTOR
# ============================================================

def disease_checkbox_selector(
    diseases,
):
    """
    Inline disease checkbox selector.

    Features:
    - Select All
    - Individual disease checkboxes
    - Reset
    - Multiple disease selection
    """

    if not diseases:
        return []

    diseases = [
        clean_text(disease)
        for disease in diseases
        if clean_text(disease)
    ]

    diseases = list(
        dict.fromkeys(diseases)
    )

    if not diseases:
        return []

    signature = "||".join(
        diseases
    )

    previous_signature = (
        st.session_state.get(
            "geo_disease_signature"
        )
    )

    if (
        previous_signature
        != signature
    ):
        st.session_state[
            "geo_disease_signature"
        ] = signature

        st.session_state[
            "geo_select_all"
        ] = False

        for i in range(
            len(diseases)
        ):
            st.session_state[
                f"geo_disease_{i}"
            ] = False

    st.markdown(
        "### Disease Selection"
    )

    control_col1, control_col2, control_col3 = (
        st.columns(
            [1.2, 1.0, 5.8]
        )
    )

    with control_col1:

        st.checkbox(
            "Select All",
            key="geo_select_all",
            on_change=_geo_select_all_changed,
            args=(diseases,),
        )

    with control_col2:

        st.button(
            "Reset",
            key="geo_disease_reset",
            on_click=_geo_reset_diseases,
            args=(diseases,),
            use_container_width=True,
        )

    with control_col3:

        selected_count = sum(
            1
            for i in range(
                len(diseases)
            )
            if st.session_state.get(
                f"geo_disease_{i}",
                False,
            )
        )

        st.caption(
            f"{selected_count} of {len(diseases)} diseases selected"
        )

    # --------------------------------------------------------
    # Inline checkbox grid
    # --------------------------------------------------------

    columns_per_row = 4

    columns = st.columns(
        columns_per_row
    )

    for i, disease in enumerate(
        diseases
    ):

        with columns[
            i % columns_per_row
        ]:

            st.checkbox(
                disease,
                key=f"geo_disease_{i}",
                on_change=_geo_disease_changed,
            )

    selected = []

    for i, disease in enumerate(
        diseases
    ):

        if st.session_state.get(
            f"geo_disease_{i}",
            False,
        ):
            selected.append(
                disease
            )

    return selected


# ============================================================
# DISEASE-SPECIFIC DATA
# ============================================================

def filter_by_selected_diseases(
    df,
    selected_diseases,
):
    """
    Filter data according to selected diseases.
    """
    if (
        df is None
        or df.empty
    ):
        return pd.DataFrame()

    disease_col = get_disease_column(
        df
    )

    if disease_col is None:
        return df.copy()

    if not selected_diseases:
        return df.copy()

    selected = {
        clean_text(x).lower()
        for x in selected_diseases
    }

    mask = (
        df[disease_col]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(selected)
    )

    return df.loc[
        mask
    ].copy()


def create_disease_comparison(
    df,
    selected_diseases,
):
    """
    Create disease-wise geographic comparison.
    """
    if (
        df is None
        or df.empty
    ):
        return pd.DataFrame()

    disease_col = get_disease_column(
        df
    )

    if disease_col is None:
        return pd.DataFrame()

    diseases = selected_diseases

    if not diseases:
        diseases = sorted(
            [
                clean_text(x)
                for x in df[
                    disease_col
                ]
                .dropna()
                .unique()
                if clean_text(x)
            ]
        )

    records = []

    for disease in diseases:

        disease_df = filter_by_selected_diseases(
            df,
            [disease],
        )

        if disease_df.empty:
            continue

        disease_coordinates, invalid = (
            prepare_coordinates(
                disease_df
            )
        )

        valid = disease_coordinates[
            disease_coordinates[
                "_lat"
            ].notna()
            & disease_coordinates[
                "_lon"
            ].notna()
        ].copy()

        disease_ward = create_ward_summary(
            disease_df
        )

        top_ward_row = (
            disease_ward.sort_values(
                "Cases",
                ascending=False,
            )
            .head(1)
        )

        if top_ward_row.empty:
            top_ward = "N/A"
            top_ward_cases = 0
        else:
            top_ward = str(
                top_ward_row.iloc[
                    0
                ]["Ward"]
            )
            top_ward_cases = int(
                top_ward_row.iloc[
                    0
                ]["Cases"]
            )

        hotspots = create_hotspots(
            disease_df
        )

        records.append(
            {
                "Disease": disease,
                "Cases": int(
                    len(
                        disease_df
                    )
                ),
                "Valid Coordinates": int(
                    len(valid)
                ),
                "Invalid Coordinates": int(
                    invalid
                ),
                "Top Ward": top_ward,
                "Top Ward Cases": top_ward_cases,
                "Hotspot Clusters": int(
                    len(hotspots)
                ),
            }
        )

    if not records:
        return pd.DataFrame()

    result = pd.DataFrame(
        records
    )

    return result.sort_values(
        "Cases",
        ascending=False,
    ).reset_index(
        drop=True
    )


# ============================================================
# DISEASE MAP DATA
# ============================================================

def get_disease_map_data(
    df,
    disease,
):
    """
    Prepare one disease's map data.
    """
    disease_df = filter_by_selected_diseases(
        df,
        [disease],
    )

    if disease_df.empty:
        return {
            "data": disease_df,
            "hotspots": pd.DataFrame(),
            "case_points": pd.DataFrame(),
            "ward_summary": pd.DataFrame(),
            "map_ward_summary": pd.DataFrame(),
        }

    hotspots = create_hotspots(
        disease_df
    )

    case_points = create_case_points(
        disease_df,
        hotspots,
    )

    ward_summary = create_ward_summary(
        disease_df
    )

    map_ward_summary = create_map_ward_summary(
        disease_df
    )

    return {
        "data": disease_df,
        "hotspots": hotspots,
        "case_points": case_points,
        "ward_summary": ward_summary,
        "map_ward_summary": map_ward_summary,
    }


# ============================================================
# MAP KPI BLOCK
# ============================================================

def render_geographic_kpis(
    df,
    coordinate_df,
    hotspots,
):
    """
    Render geographic map KPIs.
    """

    total_cases = (
        len(df)
        if df is not None
        else 0
    )

    valid_coordinates = 0

    if (
        coordinate_df is not None
        and not coordinate_df.empty
    ):
        valid_coordinates = int(
            (
                coordinate_df[
                    "_lat"
                ].notna()
                & coordinate_df[
                    "_lon"
                ].notna()
            ).sum()
        )

    invalid_coordinates = max(
        0,
        total_cases
        - valid_coordinates,
    )

    hotspot_count = (
        len(hotspots)
        if hotspots is not None
        else 0
    )

    if hotspots is not None and not hotspots.empty:
        highest_cluster = int(
            pd.to_numeric(
                hotspots[
                    "Cluster_Cases"
                ],
                errors="coerce",
            )
            .fillna(0)
            .max()
        )
    else:
        highest_cluster = 0

    col1, col2, col3, col4 = st.columns(
        4
    )

    with col1:
        st.metric(
            "Total Cases",
            f"{total_cases:,}",
        )

    with col2:
        st.metric(
            "Valid Coordinates",
            f"{valid_coordinates:,}",
        )

    with col3:
        st.metric(
            "Hotspot Clusters",
            f"{hotspot_count:,}",
        )

    with col4:
        st.metric(
            "Largest Cluster",
            f"{highest_cluster:,}",
        )

    if invalid_coordinates > 0:

        st.warning(
            f"{invalid_coordinates:,} records do not have valid latitude/longitude and are not plotted on the geographic map."
        )


# ============================================================
# WARD TABLE
# ============================================================

def render_ward_summary_table(
    ward_summary,
):
    """
    Render ward summary with PE and PN separately.
    """
    if (
        ward_summary is None
        or ward_summary.empty
    ):
        st.info(
            "Ward summary is not available."
        )
        return

    display = ward_summary.copy()

    display["Cases"] = pd.to_numeric(
        display["Cases"],
        errors="coerce",
    ).fillna(0).astype(int)

    display = display.sort_values(
        "Cases",
        ascending=False,
    ).reset_index(
        drop=True
    )

    display.insert(
        0,
        "Rank",
        display.index + 1,
    )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# HOTSPOT TABLE
# ============================================================

def render_hotspot_table(
    hotspots,
):
    """
    Render hotspot table.
    """
    if (
        hotspots is None
        or hotspots.empty
    ):
        st.info(
            "No hotspot clusters were identified for the selected data."
        )
        return

    columns = [
        "Hotspot Rank",
        "Cluster ID",
        "Cluster_Cases",
        "Disease_Count",
        "Ward_Count",
        "Cluster_Latitude",
        "Cluster_Longitude",
    ]

    available = [
        col
        for col in columns
        if col in hotspots.columns
    ]

    display = hotspots[
        available
    ].copy()

    if "Cluster_Cases" in display.columns:
        display["Cluster_Cases"] = (
            pd.to_numeric(
                display[
                    "Cluster_Cases"
                ],
                errors="coerce",
            )
            .fillna(0)
            .astype(int)
        )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# DISEASE COMPARISON TABLE
# ============================================================

def render_disease_comparison_table(
    comparison_df,
):
    """
    Render disease comparison table.
    """
    if (
        comparison_df is None
        or comparison_df.empty
    ):
        st.info(
            "Disease comparison is not available."
        )
        return

    display = comparison_df.copy()

    numeric_columns = [
        "Cases",
        "Valid Coordinates",
        "Invalid Coordinates",
        "Top Ward Cases",
        "Hotspot Clusters",
    ]

    for col in numeric_columns:
        if col in display.columns:
            display[col] = pd.to_numeric(
                display[col],
                errors="coerce",
            ).fillna(0).astype(int)

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# HOTSPOT EXPORT
# ============================================================

def create_hotspot_download(
    hotspots,
):
    """
    Create Excel download for hotspot data.
    """
    if (
        hotspots is None
        or hotspots.empty
    ):
        return None

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        hotspots.to_excel(
            writer,
            index=False,
            sheet_name="Geographic Hotspots",
        )

    output.seek(0)

    return output.getvalue()


# ============================================================
# MAIN GEOGRAPHIC MAP RENDER
# ============================================================

def render_geographic_map(
    filtered_df,
    full_df=None,
):
    """
    Main Geographic Map section.

    Uses filtered_df from the main application.
    No duplicate global filters are created here.
    """

    st.title(
        "Geographic Disease Hotspot Map"
    )

    st.caption(
        "Facility-wise, ward-wise and disease-wise geographic analysis using available latitude and longitude."
    )

    if (
        filtered_df is None
        or filtered_df.empty
    ):
        st.warning(
            "No data available for the selected filters."
        )
        return

    # --------------------------------------------------------
    # Coordinate preparation
    # --------------------------------------------------------

    coordinate_df, invalid_count = (
        prepare_coordinates(
            filtered_df
        )
    )

    valid_coordinate_df = coordinate_df[
        coordinate_df["_lat"].notna()
        & coordinate_df["_lon"].notna()
    ].copy()

    # --------------------------------------------------------
    # Disease list
    # --------------------------------------------------------

    disease_col = get_disease_column(
        filtered_df
    )

    if disease_col is None:

        diseases = []

    else:

        diseases = sorted(
            [
                clean_text(value)
                for value in filtered_df[
                    disease_col
                ]
                .dropna()
                .unique()
                if clean_text(value)
            ]
        )

    # --------------------------------------------------------
    # Map extent
    # --------------------------------------------------------

    extent_col1, extent_col2 = (
        st.columns(
            [2.5, 7.5]
        )
    )

    with extent_col1:

        extent = st.radio(
            "Map Extent",
            [
                "BMC Focus",
                "BMC + All Valid Coordinates",
            ],
            index=1,
            horizontal=False,
            key="geo_map_extent",
        )

    with extent_col2:

        st.markdown(
            "### Geographic Analysis"
        )

        st.caption(
            "All valid latitude/longitude records are retained. The map is not artificially restricted to BMC."
        )

    # --------------------------------------------------------
    # Disease selector
    # --------------------------------------------------------

    selected_diseases = (
        disease_checkbox_selector(
            diseases
        )
    )

    # If nothing is selected, use all diseases.
    if selected_diseases:

        map_df = filter_by_selected_diseases(
            filtered_df,
            selected_diseases,
        )

    else:

        map_df = filtered_df.copy()

    # --------------------------------------------------------
    # Prepare overall map data
    # --------------------------------------------------------

    map_coordinate_df, map_invalid_count = (
        prepare_coordinates(
            map_df
        )
    )

    hotspots = create_hotspots(
        map_df
    )

    case_points = create_case_points(
        map_df,
        hotspots,
    )

    ward_summary = create_ward_summary(
        map_df
    )

    map_ward_summary = create_map_ward_summary(
        map_df
    )

    # --------------------------------------------------------
    # Load BMC boundaries
    # --------------------------------------------------------

    bmc_geojson = load_bmc_wards()

    choropleth_geojson = (
        prepare_bmc_choropleth(
            bmc_geojson,
            map_ward_summary,
        )
        if bmc_geojson is not None
        else None
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    render_geographic_kpis(
        map_df,
        map_coordinate_df,
        hotspots,
    )

    # --------------------------------------------------------
    # Boundary status
    # --------------------------------------------------------

    if choropleth_geojson is None:

        st.info(
            "BMC ward boundary layer could not be loaded. Geographic case points and hotspot clusters are still available."
        )

    else:

        st.success(
            "BMC ward boundary layer loaded successfully."
        )

    # --------------------------------------------------------
    # Legend
    # --------------------------------------------------------

    render_map_legend(
        ward_summary,
        hotspots,
        case_points,
    )

    # --------------------------------------------------------
    # Main tabs
    # --------------------------------------------------------

    tab_map, tab_disease, tab_ward, tab_hotspot = st.tabs(
        [
            "🗺️ Geographic Map",
            "🦠 Disease Comparison",
            "🏘️ Ward Analysis",
            "🔥 Hotspot Analysis",
        ]
    )

    # ========================================================
    # TAB 1 - MAIN GEOGRAPHIC MAP
    # ========================================================

    with tab_map:

        st.subheader(
            "Geographic Disease Distribution"
        )

        if case_points.empty:

            st.warning(
                "No valid geographic case points are available for the selected data."
            )

        else:

            deck = build_map(
                choropleth_geojson=choropleth_geojson,
                hotspot_df=hotspots,
                case_points=case_points,
                extent=extent,
                show_hotspots=True,
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
            )

        st.markdown(
            "#### Ward-wise Burden"
        )

        render_ward_summary_table(
            ward_summary
        )

    # ========================================================
    # TAB 2 - DISEASE COMPARISON
    # ========================================================

    with tab_disease:

        st.subheader(
            "Disease-wise Geographic Comparison"
        )

        comparison_df = (
            create_disease_comparison(
                map_df,
                selected_diseases,
            )
        )

        render_disease_comparison_table(
            comparison_df
        )

        if diseases:

            selected_for_maps = (
                selected_diseases
                if selected_diseases
                else diseases
            )

            st.markdown(
                "#### Disease-specific Maps"
            )

            # Limit simultaneous maps for performance.
            display_diseases = (
                selected_for_maps[:6]
            )

            if len(
                selected_for_maps
            ) > 6:

                st.info(
                    "The comparison table includes all selected diseases. Up to 6 disease-specific maps are displayed at once for performance."
                )

            for disease in display_diseases:

                disease_map_data = (
                    get_disease_map_data(
                        map_df,
                        disease,
                    )
                )

                st.markdown(
                    f"##### {disease}"
                )

                disease_case_points = (
                    disease_map_data[
                        "case_points"
                    ]
                )

                disease_hotspots = (
                    disease_map_data[
                        "hotspots"
                    ]
                )

                disease_map_summary = (
                    disease_map_data[
                        "map_ward_summary"
                    ]
                )

                disease_choropleth = (
                    prepare_bmc_choropleth(
                        bmc_geojson,
                        disease_map_summary,
                    )
                    if bmc_geojson is not None
                    else None
                )

                if (
                    disease_case_points.empty
                    and disease_choropleth is None
                ):

                    st.info(
                        f"No geographic data available for {disease}."
                    )

                else:

                    disease_deck = build_map(
                        choropleth_geojson=disease_choropleth,
                        hotspot_df=disease_hotspots,
                        case_points=disease_case_points,
                        extent=extent,
                        show_hotspots=True,
                    )

                    st.pydeck_chart(
                        disease_deck,
                        use_container_width=True,
                    )

    # ========================================================
    # TAB 3 - WARD ANALYSIS
    # ========================================================

    with tab_ward:

        st.subheader(
            "Ward-wise Geographic Management Analysis"
        )

        render_ward_summary_table(
            ward_summary
        )

        st.markdown(
            "#### Choropleth Interpretation"
        )

        st.write(
            "Ward shading represents the selected disease burden. PE and PN are temporarily combined as P for choropleth mapping, while management tables retain PE and PN separately."
        )

        if choropleth_geojson is not None:

            ward_deck = build_map(
                choropleth_geojson=choropleth_geojson,
                hotspot_df=None,
                case_points=None,
                extent=extent,
                show_hotspots=False,
            )

            st.pydeck_chart(
                ward_deck,
                use_container_width=True,
            )

        else:

            st.info(
                "Ward boundary data is not available."
            )

    # ========================================================
    # TAB 4 - HOTSPOT ANALYSIS
    # ========================================================

    with tab_hotspot:

        st.subheader(
            "Geographic Hotspot Analysis"
        )

        if hotspots.empty:

            st.info(
                "No hotspot clusters were identified for the selected data."
            )

        else:

            render_hotspot_table(
                hotspots
            )

            st.markdown(
                "#### Hotspot Map"
            )

            hotspot_deck = build_map(
                choropleth_geojson=choropleth_geojson,
                hotspot_df=hotspots,
                case_points=case_points,
                extent=extent,
                show_hotspots=True,
            )

            st.pydeck_chart(
                hotspot_deck,
                use_container_width=True,
            )

            download_data = (
                create_hotspot_download(
                    hotspots
                )
            )

            if download_data is not None:

                st.download_button(
                    label="Download Hotspot Data",
                    data=download_data,
                    file_name="geographic_hotspots.xlsx",
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    key="geo_hotspot_download",
                )

    # --------------------------------------------------------
    # Data quality note
    # --------------------------------------------------------

    if invalid_count > 0:

        st.caption(
            f"Data quality note: {invalid_count:,} records in the selected dataset do not contain valid geographic coordinates and therefore cannot be plotted."
        )
