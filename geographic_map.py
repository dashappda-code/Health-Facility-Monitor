import io
import requests
import pandas as pd
import streamlit as st
import pydeck as pdk


# ============================================================
# CONFIG
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
    "FN", "FS", "GN", "GS",
    "HE", "HW", "KE", "KW",
    "L", "ME", "MW", "N",
    "PE", "PN", "PS",
    "RC", "RN", "RS",
    "S", "T",
]


# Disease colour families
DISEASE_COLORS = [
    [220, 55, 55],     # Red
    [55, 105, 210],    # Blue
    [45, 155, 85],     # Green
    [230, 135, 35],    # Orange
    [145, 75, 190],    # Purple
    [205, 170, 35],    # Yellow
    [25, 160, 165],    # Teal
    [210, 85, 145],    # Pink
]


# ============================================================
# COLUMN HELPERS
# ============================================================

def _find_column(df, candidates):

    if df is None or df.empty:
        return None

    lookup = {
        str(c).strip().lower(): c
        for c in df.columns
    }

    for candidate in candidates:

        key = str(candidate).strip().lower()

        if key in lookup:
            return lookup[key]

    return None


def _disease_col(df):
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


def _ward_col(df):
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


def _facility_col(df):
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


# ============================================================
# WARD NORMALISATION
# ============================================================

def normalize_ward(value):

    if pd.isna(value):
        return ""

    text = str(value).strip().upper()

    if not text:
        return ""

    text = (
        text.replace("WARD", "")
        .replace("BMC", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
    )

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

    return replacements.get(text, text)


def map_ward(value):

    ward = normalize_ward(value)

    if ward in ["PE", "PN"]:
        return "P"

    return ward


# ============================================================
# DATA PREPARATION
# ============================================================

def prepare_coordinates(df):

    if df is None:
        return pd.DataFrame()

    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    if df.empty:
        return df.copy()

    if LAT_COL not in df.columns:
        return pd.DataFrame()

    if LON_COL not in df.columns:
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
    )

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

    work = prepare_coordinates(df)

    if work.empty:
        return pd.DataFrame()

    work = work[
        [LAT_COL, LON_COL]
    ].copy()

    work["_lat_grid"] = (
        work[LAT_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    work["_lon_grid"] = (
        work[LON_COL] / GRID_SIZE
    ).round() * GRID_SIZE

    result = (
        work.groupby(
            ["_lat_grid", "_lon_grid"],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "Cases"})
    )

    if result.empty:
        return pd.DataFrame()

    result["Latitude"] = result["_lat_grid"]
    result["Longitude"] = result["_lon_grid"]

    result["Hotspot Level"] = "Low"

    result.loc[
        result["Cases"] >= 5,
        "Hotspot Level",
    ] = "Moderate"

    result.loc[
        result["Cases"] >= 10,
        "Hotspot Level",
    ] = "High"

    result["Radius"] = (
        45 + result["Cases"] * 4
    ).clip(
        45,
        125,
    )

    return result[
        [
            "Latitude",
            "Longitude",
            "Cases",
            "Hotspot Level",
            "Radius",
        ]
    ].copy()


# ============================================================
# WARD SUMMARY
# ============================================================

def create_ward_summary(df):

    if df is None or df.empty:
        return pd.DataFrame(
            columns=["Ward", "Cases"]
        )

    wc = _ward_col(df)

    if not wc:
        return pd.DataFrame(
            columns=["Ward", "Cases"]
        )

    result = pd.DataFrame()

    result["Ward"] = df[wc].apply(
        map_ward
    )

    result = result[
        result["Ward"].astype(str).str.strip() != ""
    ]

    if result.empty:
        return pd.DataFrame(
            columns=["Ward", "Cases"]
        )

    result = (
        result.groupby(
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
# BMC WARD DATA
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
            timeout=12,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            return None

        if data.get("type") != "FeatureCollection":
            return None

        clean_features = []

        for feature in data.get(
            "features",
            [],
        ):

            geometry = feature.get(
                "geometry"
            )

            if not geometry:
                continue

            props = feature.get(
                "properties",
                {},
            )

            name = ""

            if isinstance(props, dict):
                name = props.get(
                    "NAME",
                    "",
                )

            clean_features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "NAME": str(name),
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
# COLOUR LOGIC
# ============================================================

def disease_color(disease, diseases):

    if disease in diseases:

        index = diseases.index(
            disease
        )

    else:

        index = 0

    return DISEASE_COLORS[
        index % len(DISEASE_COLORS)
    ]


def get_burden_color(
    cases,
    max_cases,
    base_color,
):

    r, g, b = base_color

    try:
        cases = float(cases)
    except Exception:
        cases = 0

    try:
        max_cases = float(max_cases)
    except Exception:
        max_cases = 0

    # No cases = dark/black
    if cases <= 0:

        return [
            25,
            25,
            25,
            210,
        ]

    if max_cases <= 0:

        intensity = 0.25

    else:

        intensity = cases / max_cases

    # Keep visible but make high burden much stronger
    intensity = max(
        0.20,
        min(
            1.0,
            intensity,
        ),
    )

    # Blend toward white for low values
    blend = 0.72 * (
        1 - intensity
    )

    rr = int(
        r + (255 - r) * blend
    )

    gg = int(
        g + (255 - g) * blend
    )

    bb = int(
        b + (255 - b) * blend
    )

    return [
        rr,
        gg,
        bb,
        225,
    ]


# ============================================================
# CHOROPLETH GEOJSON
# ============================================================

def prepare_choropleth(
    geojson,
    ward_summary,
    disease,
    all_diseases,
):

    if not isinstance(
        geojson,
        dict,
    ):
        return None

    lookup = {}

    if (
        ward_summary is not None
        and not ward_summary.empty
    ):

        for _, row in ward_summary.iterrows():

            ward = map_ward(
                row["Ward"]
            )

            try:
                cases = int(
                    row["Cases"]
                )
            except Exception:
                cases = 0

            lookup[ward] = cases

    max_cases = max(
        lookup.values()
    ) if lookup else 0

    base = disease_color(
        disease,
        all_diseases,
    )

    output = []

    for feature in geojson.get(
        "features",
        [],
    ):

        geometry = feature.get(
            "geometry"
        )

        if not geometry:
            continue

        props = feature.get(
            "properties",
            {},
        )

        name = ""

        if isinstance(props, dict):
            name = props.get(
                "NAME",
                "",
            )

        ward = map_ward(
            name
        )

        cases = lookup.get(
            ward,
            0,
        )

        if cases <= 0:

            burden = "No reported cases"

        elif max_cases > 0 and cases >= (
            max_cases * 0.75
        ):

            burden = "High"

        elif max_cases > 0 and cases >= (
            max_cases * 0.40
        ):

            burden = "Moderate"

        else:

            burden = "Low"

        fill = get_burden_color(
            cases,
            max_cases,
            base,
        )

        output.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "Ward": ward,
                    "Cases": cases,
                    "Disease": disease,
                    "Burden": burden,
                    "fill": fill,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": output,
    }


# ============================================================
# VIEW STATE
# ============================================================

def get_view_state(df):

    if df is None or df.empty:

        return pdk.ViewState(
            latitude=19.0760,
            longitude=72.8777,
            zoom=10.5,
            pitch=0,
            bearing=0,
        )

    work = prepare_coordinates(
        df
    )

    if work.empty:

        return pdk.ViewState(
            latitude=19.0760,
            longitude=72.8777,
            zoom=10.5,
            pitch=0,
            bearing=0,
        )

    lat = float(
        work[LAT_COL].mean()
    )

    lon = float(
        work[LON_COL].mean()
    )

    return pdk.ViewState(
        latitude=lat,
        longitude=lon,
        zoom=10.5,
        pitch=0,
        bearing=0,
    )


# ============================================================
# BMC FOCUS MAP
# ============================================================

def build_bmc_focus_map(
    geojson,
    view_state,
):

    layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson,
        pickable=True,
        stroked=True,
        filled=True,
        get_fill_color="properties.fill",
        get_line_color=[
            210,
            210,
            210,
            190,
        ],
        line_width_min_pixels=1,
        auto_highlight=True,
    )

    return pdk.Deck(
        map_provider="carto",
        map_style="light",
        initial_view_state=view_state,
        layers=[layer],
        tooltip={
            "html": (
                "<div style='font-size:14px'>"
                "<b>Ward:</b> {properties.Ward}<br/>"
                "<b>Cases:</b> {properties.Cases}<br/>"
                "<b>Burden:</b> {properties.Burden}<br/>"
                "<b>Disease:</b> {properties.Disease}"
                "</div>"
            )
        },
    )


# ============================================================
# ALL POINTS / HOTSPOT MAP
# ============================================================

def build_points_map(
    df,
    ward_geojson,
    view_state,
):

    hotspots = create_hotspots(
        df
    )

    layers = []

    if (
        isinstance(
            ward_geojson,
            dict,
        )
        and ward_geojson.get(
            "features"
        )
    ):

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=ward_geojson,
                pickable=False,
                stroked=True,
                filled=False,
                get_line_color=[
                    100,
                    100,
                    100,
                    150,
                ],
                line_width_min_pixels=1,
            )
        )

    if not hotspots.empty:

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
                    220,
                    55,
                    55,
                    160,
                ],
                get_line_color=[
                    120,
                    30,
                    30,
                    190,
                ],
                radius_min_pixels=5,
                radius_max_pixels=24,
                pickable=True,
            )
        )

    return pdk.Deck(
        map_provider="carto",
        map_style="light",
        initial_view_state=view_state,
        layers=layers,
        tooltip={
            "html": (
                "<b>Cases:</b> {Cases}<br/>"
                "<b>Hotspot:</b> {Hotspot Level}"
            )
        },
    )


# ============================================================
# COMBINED MAP
# ============================================================

def build_combined_map(
    geojson,
    hotspots,
    view_state,
):

    layers = []

    if (
        isinstance(
            geojson,
            dict,
        )
        and geojson.get(
            "features"
        )
    ):

        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                data=geojson,
                pickable=True,
                stroked=True,
                filled=True,
                get_fill_color="properties.fill",
                get_line_color=[
                    210,
                    210,
                    210,
                    180,
                ],
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
                    220,
                    55,
                    55,
                    150,
                ],
                get_line_color=[
                    100,
                    30,
                    30,
                    180,
                ],
                radius_min_pixels=5,
                radius_max_pixels=22,
                pickable=True,
            )
        )

    return pdk.Deck(
        map_provider="carto",
        map_style="light",
        initial_view_state=view_state,
        layers=layers,
        tooltip={
            "html": (
                "<b>Ward:</b> "
                "{properties.Ward}<br/>"
                "<b>Cases:</b> "
                "{properties.Cases}<br/>"
                "<b>Burden:</b> "
                "{properties.Burden}"
            )
        },
    )


# ============================================================
# EXCEL
# ============================================================

def create_excel(
    ward_summary,
    disease_summary,
    hotspots,
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

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
    # VALIDATION
    # --------------------------------------------------------

    if filtered_df is None:
        st.info(
            "No geographic data available."
        )
        return

    if not isinstance(
        filtered_df,
        pd.DataFrame,
    ):
        st.info(
            "Geographic data is not available."
        )
        return

    if filtered_df.empty:
        st.info(
            "No records available for the selected filters."
        )
        return

    map_df = prepare_coordinates(
        filtered_df
    )

    if map_df.empty:
        st.warning(
            "No valid latitude/longitude records are available."
        )
        return

    disease_col = _disease_col(
        map_df
    )

    if not disease_col:
        st.warning(
            "Disease column could not be identified."
        )
        return

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

    if not diseases:
        st.info(
            "No disease categories available."
        )
        return

    # --------------------------------------------------------
    # LOAD BMC DATA ONCE
    # --------------------------------------------------------

    ward_geojson = load_bmc_wards()

    # --------------------------------------------------------
    # COMPACT DISEASE FILTER
    # --------------------------------------------------------

    control1, control2 = st.columns(
        [5, 1]
    )

    with control1:

        selected_disease = st.selectbox(
            "Disease",
            options=[
                "All Diseases"
            ] + diseases,
            index=0,
            key="geo_selected_disease",
        )

    with control2:

        st.write("")

        reset = st.button(
            "Reset",
            key="geo_reset",
        )

        if reset:

            st.session_state[
                "geo_selected_disease"
            ] = "All Diseases"

            st.rerun()

    # --------------------------------------------------------
    # FILTER
    # --------------------------------------------------------

    if selected_disease != "All Diseases":

        map_df = map_df[
            map_df[disease_col]
            .astype(str)
            .str.strip()
            == selected_disease
        ].copy()

    if map_df.empty:

        st.info(
            "No geographic records match the selected disease."
        )
        return

    # --------------------------------------------------------
    # SUMMARIES
    # --------------------------------------------------------

    ward_summary = create_ward_summary(
        map_df
    )

    disease_summary = (
        map_df[disease_col]
        .astype(str)
        .value_counts()
        .rename_axis("Disease")
        .reset_index(name="Cases")
    )

    hotspots = create_hotspots(
        map_df
    )

    view_state = get_view_state(
        map_df
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    total_cases = len(
        map_df
    )

    mapped_cases = len(
        prepare_coordinates(
            map_df
        )
    )

    hotspot_count = len(
        hotspots
    )

    ward_count = len(
        ward_summary
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Cases",
        f"{total_cases:,}",
    )

    c2.metric(
        "Mapped Cases",
        f"{mapped_cases:,}",
    )

    c3.metric(
        "Hotspot Areas",
        f"{hotspot_count:,}",
    )

    c4.metric(
        "Wards with Cases",
        f"{ward_count:,}",
    )

    st.divider()

    # ========================================================
    # FOCUS SELECTION
    # ========================================================

    focus = st.radio(
        "Geographic Focus",
        [
            "BMC Focus",
            "All Points Focus",
            "Disease-wise Ward Maps",
            "Combined View",
        ],
        horizontal=True,
        key="geo_focus",
    )

    # ========================================================
    # BMC FOCUS
    # ========================================================

    if focus == "BMC Focus":

        st.markdown(
            "#### BMC Ward Burden Map"
        )

        if ward_geojson is None:

            st.warning(
                "BMC ward boundary data could not be loaded."
            )

        else:

            disease_for_map = (
                selected_disease
                if selected_disease != "All Diseases"
                else (
                    diseases[0]
                    if diseases
                    else ""
                )
            )

            if selected_disease == "All Diseases":

                map_summary = create_ward_summary(
                    map_df
                )

            else:

                map_summary = create_ward_summary(
                    map_df
                )

            geo = prepare_choropleth(
                ward_geojson,
                map_summary,
                disease_for_map,
                diseases,
            )

            deck = build_bmc_focus_map(
                geo,
                view_state,
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
                height=470,
                key="geo_bmc_focus",
            )

            # Legend
            st.markdown(
                "**Burden intensity:** "
                "⬛ No reported cases  →  "
                "Faint = Low  →  "
                "Medium = Moderate  →  "
                "Dark = High"
            )

            st.markdown(
                "##### Ward-wise Burden"
            )

            st.dataframe(
                ward_summary,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # ALL POINTS
    # ========================================================

    elif focus == "All Points Focus":

        st.markdown(
            "#### All Points / Hotspot View"
        )

        deck = build_points_map(
            map_df,
            ward_geojson,
            view_state,
        )

        st.pydeck_chart(
            deck,
            use_container_width=True,
            height=470,
            key="geo_all_points",
        )

        if hotspots.empty:

            st.info(
                "No hotspot areas identified."
            )

        else:

            st.markdown(
                "##### Hotspot Summary"
            )

            st.dataframe(
                hotspots[
                    [
                        "Latitude",
                        "Longitude",
                        "Cases",
                        "Hotspot Level",
                    ]
                ].sort_values(
                    "Cases",
                    ascending=False,
                ),
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # DISEASE-WISE MAPS
    # ========================================================

    elif focus == "Disease-wise Ward Maps":

        st.markdown(
            "#### Disease-wise Ward Burden"
        )

        st.caption(
            "Maps are displayed vertically to preserve "
            "browser performance and avoid multiple active "
            "WebGL contexts."
        )

        # One disease at a time selector
        selected_map_disease = st.selectbox(
            "Select Disease Map",
            diseases,
            key="geo_vertical_disease",
        )

        disease_df = map_df[
            map_df[disease_col]
            .astype(str)
            .str.strip()
            == selected_map_disease
        ].copy()

        disease_summary_ward = (
            create_ward_summary(
                disease_df
            )
        )

        disease_geo = prepare_choropleth(
            ward_geojson,
            disease_summary_ward,
            selected_map_disease,
            diseases,
        )

        if disease_geo is None:

            st.warning(
                "Ward map is not available."
            )

        else:

            disease_view = get_view_state(
                disease_df
            )

            deck = build_bmc_focus_map(
                disease_geo,
                disease_view,
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
                height=470,
                key=(
                    "geo_disease_map_"
                    + selected_map_disease
                ),
            )

            st.markdown(
                f"##### {selected_map_disease} — Ward-wise Data"
            )

            st.dataframe(
                disease_summary_ward,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # COMBINED VIEW
    # ========================================================

    elif focus == "Combined View":

        st.markdown(
            "#### Combined BMC + Hotspot View"
        )

        disease_for_map = (
            selected_disease
            if selected_disease != "All Diseases"
            else (
                diseases[0]
                if diseases
                else ""
            )
        )

        map_summary = create_ward_summary(
            map_df
        )

        combined_geo = prepare_choropleth(
            ward_geojson,
            map_summary,
            disease_for_map,
            diseases,
        )

        deck = build_combined_map(
            combined_geo,
            hotspots,
            view_state,
        )

        st.pydeck_chart(
            deck,
            use_container_width=True,
            height=470,
            key="geo_combined_view",
        )

        st.markdown(
            "##### Ward-wise Summary"
        )

        st.dataframe(
            ward_summary,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # EXPORT
    # ========================================================

    st.divider()

    excel_bytes = create_excel(
        ward_summary,
        disease_summary,
        hotspots,
    )

    st.download_button(
        "Download Geographic Analysis",
        data=excel_bytes,
        file_name="geographic_analysis.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        key="geo_download",
    )
