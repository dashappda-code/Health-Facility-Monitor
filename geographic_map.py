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

    return valid_df, invalid_count, valid_count


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

def add_report_ward(df):
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    work = df.copy()

    if "_Report_Ward" in work.columns:
        work["_Report_Ward"] = (
            work["_Report_Ward"]
            .fillna("")
            .astype(str)
            .apply(normalise_ward)
        )
        return work

    ward_col = get_ward_column(work)

    if ward_col is None:
        work["_Report_Ward"] = ""
        return work

    work["_Report_Ward"] = (
        work[ward_col]
        .apply(normalise_ward)
    )

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

    return summary


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):
    summary = pd.DataFrame(
        {
            "Ward": PROGRAMME_WARDS
        }
    )

    summary["Cases"] = 0

    if df is None or df.empty:
        return summary

    work = add_report_ward(df)

    if "_Report_Ward" not in work.columns:
        return summary

    counts = (
        work["_Report_Ward"]
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .rename_axis("Ward")
        .reset_index(name="Cases")
    )

    summary = summary.merge(
        counts,
        on="Ward",
        how="left",
        suffixes=("_base", ""),
    )

    if "Cases_base" in summary.columns:
        summary["Cases"] = summary["Cases"].fillna(
            summary["Cases_base"]
        )
        summary = summary.drop(
            columns=["Cases_base"]
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
# PE + PN COMBINED MAP SUMMARY
# ============================================================

def create_map_ward_summary(df):
    """
    PE and PN are combined as P only for choropleth mapping.
    PE and PN remain separate everywhere else.
    """

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

    combined_p = pe_cases + pn_cases

    summary = summary[
        ~summary["Ward"].isin(["PE", "PN"])
    ].copy()

    p_row = pd.DataFrame(
        [
            {
                "Ward": "P",
                "Cases": combined_p,
            }
        ]
    )

    summary = pd.concat(
        [summary, p_row],
        ignore_index=True,
    )

    return summary


# ============================================================
# CASE POINT DATA
# ============================================================

def create_case_points(df):
    if df is None or df.empty:
        return pd.DataFrame()

    work = add_report_ward(df)

    required = [
        "_lat",
        "_lon",
    ]

    if any(
        col not in work.columns
        for col in required
    ):
        return pd.DataFrame()

    disease_col = get_disease_column(work)

    if disease_col is not None:
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

    if "_Report_Ward" in work.columns:
        ward_values = (
            work["_Report_Ward"]
            .fillna("")
            .astype(str)
            .apply(normalise_ward)
        )
    else:
        ward_values = pd.Series(
            [""] * len(work),
            index=work.index,
        )

    case_id_col = find_column(
        work,
        [
            "Case ID",
            "Case_ID",
            "CaseID",
            "ID",
            "Sr No",
            "Sr. No",
            "Serial No",
        ],
    )

    if case_id_col is not None:
        case_ids = (
            work[case_id_col]
            .fillna("")
            .astype(str)
        )
    else:
        case_ids = pd.Series(
            work.index.astype(str),
            index=work.index,
        )

    result = pd.DataFrame(
        {
            "Case_ID": case_ids.values,
            "Disease": disease_values.values,
            "Ward": ward_values.values,
            "Latitude": work["_lat"].values,
            "Longitude": work["_lon"].values,
        }
    )

    result["Map_Ward"] = result["Ward"]

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
                )
                * 170
            ),
            60,
            205,
        ]

    return [
        int(
            255
            - (
                ratio - 0.66
            )
            * 80
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

    for original_feature in geojson["features"]:
        feature = dict(original_feature)

        properties = dict(
            feature.get("properties")
            or {}
        )

        source_ward = get_geojson_ward_name(
            properties
        )

        # PE and PN are intentionally combined as P
        # for choropleth mapping only.
        if source_ward in ["PE", "PN"]:
            map_ward = "P"
        else:
            map_ward = source_ward

        cases = int(
            ward_cases.get(
                map_ward,
                0,
            )
        )

        properties["Programme Cases"] = cases
        properties["Ward Display"] = (
            source_ward
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
# MAP LEGEND
# ============================================================

def render_map_legend(
    ward_summary=None,
    hotspot_df=None,
):
    pe_cases = 0
    pn_cases = 0
    other_cases = 0
    hotspot_count = 0

    if (
        ward_summary is not None
        and not ward_summary.empty
    ):
        pe_cases = int(
            ward_summary.loc[
                ward_summary["Ward"] == "PE",
                "Cases",
            ].sum()
        )

        pn_cases = int(
            ward_summary.loc[
                ward_summary["Ward"] == "PN",
                "Cases",
            ].sum()
        )

        other_cases = int(
            ward_summary.loc[
                ~ward_summary["Ward"].isin(
                    ["PE", "PN"]
                ),
                "Cases",
            ].sum()
        )

    if (
        hotspot_df is not None
        and not hotspot_df.empty
    ):
        hotspot_count = len(
            hotspot_df
        )

    st.markdown(
        f"""
        <div style="
            display:flex;
            flex-wrap:wrap;
            gap:14px;
            align-items:center;
            margin:8px 0 12px 0;
            padding:9px 12px;
            border:1px solid #ddd;
            border-radius:8px;
            background:#fafafa;
            font-size:13px;
        ">
            <span>
                <b style="color:#8e44ad;">●</b>
                PE: {pe_cases:,}
            </span>

            <span>
                <b style="color:#1f77b4;">●</b>
                PN: {pn_cases:,}
            </span>

            <span>
                <b style="color:#555;">●</b>
                Other Wards: {other_cases:,}
            </span>

            <span>
                <b style="color:#d62728;">●</b>
                Hotspots: {hotspot_count:,}
            </span>

            <span>
                <b>P = PE + PN</b>
                for choropleth
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# BUILD MAP
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
    # HOTSPOT CIRCLES
    # --------------------------------------------------------
    # Hotspots are intentionally added before case points
    # so individual PE/PN cases remain visible on top.

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
                "45 + min(Cluster_Cases * 5, 100)"
            ),
            radius_min_pixels=2,
            radius_max_pixels=9,
            get_fill_color=[
                220,
                40,
                40,
                125,
            ],
            get_line_color=[
                120,
                0,
                0,
                220,
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
    # CASE POINTS
    # --------------------------------------------------------

    if (
        case_points is not None
        and not case_points.empty
    ):
        pe_points = case_points[
            case_points["Ward"] == "PE"
        ].copy()

        pn_points = case_points[
            case_points["Ward"] == "PN"
        ].copy()

        other_points = case_points[
            ~case_points["Ward"].isin(
                ["PE", "PN"]
            )
        ].copy()

        # PE points
        if not pe_points.empty:
            pe_layer = pdk.Layer(
                "ScatterplotLayer",
                data=pe_points,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius=35,
                radius_min_pixels=2,
                radius_max_pixels=7,
                get_fill_color=[
                    142,
                    68,
                    173,
                    235,
                ],
                get_line_color=[
                    80,
                    30,
                    100,
                    255,
                ],
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
            )

            layers.append(
                pe_layer
            )

        # PN points
        if not pn_points.empty:
            pn_layer = pdk.Layer(
                "ScatterplotLayer",
                data=pn_points,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius=35,
                radius_min_pixels=2,
                radius_max_pixels=7,
                get_fill_color=[
                    31,
                    119,
                    180,
                    245,
                ],
                get_line_color=[
                    10,
                    60,
                    110,
                    255,
                ],
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
            )

            layers.append(
                pn_layer
            )

        # Other ward points
        if not other_points.empty:
            other_layer = pdk.Layer(
                "ScatterplotLayer",
                data=other_points,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_radius=28,
                radius_min_pixels=1,
                radius_max_pixels=5,
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
                line_width_min_pixels=1,
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
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
            <b>Programme Cases:</b> {Programme Cases}<br/>
            <b>Cluster:</b> {Cluster ID}<br/>
            <b>Cluster Cases:</b> {Cluster_Cases}<br/>
            <b>Hotspot:</b> {Hotspot Classification}
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
# DISEASE CHECKBOX SELECTOR
# ============================================================

def _geo_select_all_changed(diseases):
    if st.session_state.get(
        "geo_select_all",
        False,
    ):
        for idx in range(len(diseases)):
            st.session_state[
                f"geo_disease_{idx}"
            ] = True


def _geo_disease_changed():
    st.session_state[
        "geo_select_all"
    ] = False


def _geo_reset_diseases(diseases):
    st.session_state[
        "geo_select_all"
    ] = False

    for idx in range(len(diseases)):
        st.session_state[
            f"geo_disease_{idx}"
        ] = False


def disease_checkbox_selector(diseases):
    if not diseases:
        return []

    if "geo_select_all" not in st.session_state:
        st.session_state[
            "geo_select_all"
        ] = False

    top_left, top_right = st.columns(
        [0.2, 0.8],
        gap="small",
    )

    with top_left:
        st.checkbox(
            "Select All",
            key="geo_select_all",
            on_change=_geo_select_all_changed,
            args=(diseases,),
        )

    with top_right:
        if st.button(
            "Reset",
            key="geo_reset_diseases",
        ):
            _geo_reset_diseases(
                diseases
            )
            st.rerun()

    checkbox_columns = st.columns(
        4,
        gap="small",
    )

    for idx, disease in enumerate(diseases):
        key = f"geo_disease_{idx}"

        if key not in st.session_state:
            st.session_state[key] = False

        with checkbox_columns[
            idx % 4
        ]:
            st.checkbox(
                disease,
                key=key,
                on_change=_geo_disease_changed,
            )

    selected = []

    for idx, disease in enumerate(diseases):
        if st.session_state.get(
            f"geo_disease_{idx}",
            False,
        ):
            selected.append(disease)

    return selected


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
            and ward_summary["Cases"].sum() > 0
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

        rows.append(
            {
                "Disease": disease,
                "Cases": cases,
                "Valid Coordinates": cases,
                "Hotspot Clusters": len(
                    hotspots
                ),
                "High Hotspots": high_hotspots,
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

    disease_df = add_report_ward(
        disease_df
    )

    ward_summary = create_ward_summary(
        disease_df
    )

    map_ward_summary = create_map_ward_summary(
        disease_df
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
        selected_records != total_records
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
            [1.45, 0.65],
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
        st.markdown(
            "<div style='height:4px;'></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "### Disease Selection"
    )

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
            .isin(
                selected_diseases
            )
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
    # PREPARE DATA
    # ========================================================

    map_df = add_report_ward(
        map_df
    )

    overall_hotspots = create_hotspots(
        map_df
    )

    overall_ward_summary = create_ward_summary(
        map_df
    )

    map_ward_summary = create_map_ward_summary(
        map_df
    )

    case_points = create_case_points(
        map_df
    )

    overall_choropleth = None

    if bmc_geojson:
        overall_choropleth = (
            prepare_bmc_choropleth(
                bmc_geojson,
                map_ward_summary,
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
    # LEGEND
    # ========================================================

    render_map_legend(
        overall_ward_summary,
        overall_hotspots,
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
            "PE and PN are displayed separately as "
            "points; their choropleth burden is combined "
            "as P = PE + PN."
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
                choropleth_geojson=(
                    overall_choropleth
                ),
                hotspot_df=(
                    overall_hotspots
                ),
                case_points=case_points,
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
                    idx % len(
                        comparison_cols
                    )
                ]

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
                )

                disease_ward = (
                    create_ward_summary(
                        disease_df
                    )
                )

                disease_ward = (
                    disease_ward.rename(
                        columns={
                            "Cases": disease
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
                    "diseases."
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
                            f"Cases: {len(disease_df):,} | "
                            f"Hotspots: "
                            f"{len(disease_hotspots):,}"
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
                "Each disease map uses the same BMC "
                "ward boundary framework. Darker shading "
                "indicates higher ward-wise burden for "
                "that disease. PE and PN are combined "
                "as P for choropleth mapping."
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
            case_points=case_points,
            extent=extent,
            show_hotspots=True,
        )

        st.pydeck_chart(
            combined_deck,
            use_container_width=True,
        )

        render_map_legend(
            overall_ward_summary,
            overall_hotspots,
        )

        st.caption(
            "Ward polygons show disease burden. "
            "PE and PN case points remain separate. "
            "Red circles show geographic hotspot clusters. "
            "P in the choropleth represents PE + PN."
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

        total_cases = (
            combined_ward["Cases"].sum()
        )

        if total_cases > 0:
            combined_ward[
                "Percentage"
            ] = (
                combined_ward["Cases"]
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
            ].copy()
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
