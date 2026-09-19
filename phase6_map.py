import pandas as pd
import plotly.express as px
import streamlit as st

from phase2_overview import apply_filters, create_filters


# ============================================================
# COMMON MAP LAYOUT
# ============================================================

def _map_layout(fig, height=650):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=60, b=10),
        legend_title_text="",
        hovermode="closest"
    )
    return fig


# ============================================================
# FIND COORDINATE COLUMNS
# ============================================================

def _find_coordinate_columns(df):
    """
    Automatically detects common latitude/longitude
    column names from the uploaded dataset.
    """

    lat_candidates = [
        "Latitude",
        "latitude",
        "LATITUDE",
        "Lat",
        "lat",
        "GPS Latitude",
        "Latitude GPS"
    ]

    lon_candidates = [
        "Longitude",
        "longitude",
        "LONGITUDE",
        "Long",
        "long",
        "GPS Longitude",
        "Longitude GPS"
    ]

    lat_col = None
    lon_col = None

    for col in lat_candidates:
        if col in df.columns:
            lat_col = col
            break

    for col in lon_candidates:
        if col in df.columns:
            lon_col = col
            break

    return lat_col, lon_col


# ============================================================
# PREPARE MAP DATA
# ============================================================

def _prepare_map_data(df, lat_col, lon_col):

    map_df = df.copy()

    map_df[lat_col] = pd.to_numeric(
        map_df[lat_col],
        errors="coerce"
    )

    map_df[lon_col] = pd.to_numeric(
        map_df[lon_col],
        errors="coerce"
    )

    map_df = map_df.dropna(
        subset=[lat_col, lon_col]
    )

    return map_df


# ============================================================
# FACILITY MAP
# ============================================================

def _facility_map(df, lat_col, lon_col):

    required_columns = [
        "Facility Name Lform",
        lat_col,
        lon_col
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        st.warning(
            "Facility map cannot be created because "
            f"these columns are missing: {', '.join(missing)}"
        )
        return

    map_df = _prepare_map_data(
        df,
        lat_col,
        lon_col
    )

    if map_df.empty:
        st.info(
            "No valid latitude/longitude records available "
            "for the selected filters."
        )
        return

    # --------------------------------------------------------
    # Facility-level aggregation
    # --------------------------------------------------------

    group_columns = [
        "Facility Name Lform"
    ]

    if "Ward" in map_df.columns:
        group_columns.append("Ward")

    facility_map = (
        map_df
        .groupby(group_columns, dropna=False)
        .agg(
            Cases=(group_columns[0], "size"),
            Latitude=(lat_col, "mean"),
            Longitude=(lon_col, "mean")
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # Optional disease count
    # --------------------------------------------------------

    if "Confirmed Diagnosis" in map_df.columns:

        disease_count = (
            map_df
            .groupby(group_columns, dropna=False)
            ["Confirmed Diagnosis"]
            .nunique()
            .reset_index(
                name="Diseases"
            )
        )

        facility_map = facility_map.merge(
            disease_count,
            on=group_columns,
            how="left"
        )

    # --------------------------------------------------------
    # Hover fields
    # --------------------------------------------------------

    hover_data = {
        "Cases": True,
        "Latitude": False,
        "Longitude": False
    }

    if "Ward" in facility_map.columns:
        hover_data["Ward"] = True

    if "Diseases" in facility_map.columns:
        hover_data["Diseases"] = True

    # --------------------------------------------------------
    # Map
    # --------------------------------------------------------

    fig = px.scatter_map(
        facility_map,
        lat="Latitude",
        lon="Longitude",
        size="Cases",
        color="Cases",
        hover_name="Facility Name Lform",
        hover_data=hover_data,
        zoom=10,
        height=650,
        title="Facility-wise Case Burden Map"
    )

    fig.update_layout(
        map_style="open-street-map"
    )

    st.plotly_chart(
        _map_layout(fig),
        use_container_width=True
    )

    # --------------------------------------------------------
    # Facility map table
    # --------------------------------------------------------

    display_columns = [
        col for col in [
            "Facility Name Lform",
            "Ward",
            "Cases",
            "Diseases",
            "Latitude",
            "Longitude"
        ]
        if col in facility_map.columns
    ]

    st.dataframe(
        facility_map[
            display_columns
        ].sort_values(
            "Cases",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# WARD MAP
# ============================================================

def _ward_map(df, lat_col, lon_col):

    if "Ward" not in df.columns:
        st.warning(
            "Ward column is not available in the dataset."
        )
        return

    map_df = _prepare_map_data(
        df,
        lat_col,
        lon_col
    )

    if map_df.empty:
        st.info(
            "No valid geographical records available."
        )
        return

    # --------------------------------------------------------
    # Ward aggregation
    # --------------------------------------------------------

    ward_map = (
        map_df
        .dropna(subset=["Ward"])
        .groupby("Ward")
        .agg(
            Cases=("Ward", "size"),
            Latitude=(lat_col, "mean"),
            Longitude=(lon_col, "mean")
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # Facility count
    # --------------------------------------------------------

    if "Facility Name Lform" in map_df.columns:

        facility_count = (
            map_df
            .dropna(subset=["Ward"])
            .groupby("Ward")
            ["Facility Name Lform"]
            .nunique()
            .reset_index(
                name="Facilities"
            )
        )

        ward_map = ward_map.merge(
            facility_count,
            on="Ward",
            how="left"
        )

    # --------------------------------------------------------
    # Disease count
    # --------------------------------------------------------

    if "Confirmed Diagnosis" in map_df.columns:

        disease_count = (
            map_df
            .dropna(subset=["Ward"])
            .groupby("Ward")
            ["Confirmed Diagnosis"]
            .nunique()
            .reset_index(
                name="Diseases"
            )
        )

        ward_map = ward_map.merge(
            disease_count,
            on="Ward",
            how="left"
        )

    # --------------------------------------------------------
    # Hover data
    # --------------------------------------------------------

    hover_data = {
        "Cases": True,
        "Latitude": False,
        "Longitude": False
    }

    if "Facilities" in ward_map.columns:
        hover_data["Facilities"] = True

    if "Diseases" in ward_map.columns:
        hover_data["Diseases"] = True

    # --------------------------------------------------------
    # Map
    # --------------------------------------------------------

    fig = px.scatter_map(
        ward_map,
        lat="Latitude",
        lon="Longitude",
        size="Cases",
        color="Cases",
        hover_name="Ward",
        hover_data=hover_data,
        zoom=10,
        height=650,
        title="Ward-wise Case Burden Map"
    )

    fig.update_layout(
        map_style="open-street-map"
    )

    st.plotly_chart(
        _map_layout(fig),
        use_container_width=True
    )

    # --------------------------------------------------------
    # Ward table
    # --------------------------------------------------------

    display_columns = [
        col for col in [
            "Ward",
            "Cases",
            "Facilities",
            "Diseases",
            "Latitude",
            "Longitude"
        ]
        if col in ward_map.columns
    ]

    st.dataframe(
        ward_map[
            display_columns
        ].sort_values(
            "Cases",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# MANAGEMENT MAP SUMMARY
# ============================================================

def _map_summary(df):

    st.subheader(
        "📊 Geographical Management Summary"
    )

    total_cases = len(df)

    total_wards = (
        df["Ward"].nunique(dropna=True)
        if "Ward" in df.columns
        else 0
    )

    total_facilities = (
        df["Facility Name Lform"]
        .nunique(dropna=True)
        if "Facility Name Lform" in df.columns
        else 0
    )

    lat_col, lon_col = _find_coordinate_columns(df)

    geo_records = 0

    if lat_col and lon_col:

        geo_df = _prepare_map_data(
            df,
            lat_col,
            lon_col
        )

        geo_records = len(geo_df)

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Cases",
        f"{total_cases:,}"
    )

    c2.metric(
        "Wards",
        f"{total_wards:,}"
    )

    c3.metric(
        "Facilities",
        f"{total_facilities:,}"
    )

    c4.metric(
        "Geo-tagged Records",
        f"{geo_records:,}"
    )


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_map_analysis(df):

    st.title(
        "🗺️ Geographical & Facility Map Analysis"
    )

    st.caption(
        "Geographical distribution of cases across "
        "wards and health facilities."
    )

    if df is None or df.empty:
        st.warning(
            "No data available for map analysis."
        )
        return

    # --------------------------------------------------------
    # APPLY GLOBAL FILTERS
    # --------------------------------------------------------

    try:

        filters = create_filters(df)

        filtered_df = apply_filters(
            df,
            **filters
        )

    except Exception as e:

        st.warning(
            "Filters could not be applied. "
            "Showing available data."
        )

        filtered_df = df.copy()

    if filtered_df.empty:

        st.warning(
            "No records match the selected filters."
        )

        return

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    _map_summary(
        filtered_df
    )

    st.divider()

    # --------------------------------------------------------
    # CHECK GEO COLUMNS
    # --------------------------------------------------------

    lat_col, lon_col = _find_coordinate_columns(
        filtered_df
    )

    if not lat_col or not lon_col:

        st.error(
            "Latitude and Longitude columns were not found "
            "in the dataset."
        )

        st.info(
            "Please ensure your data contains latitude and "
            "longitude columns such as 'Latitude' and "
            "'Longitude'."
        )

        st.subheader(
            "Available Columns"
        )

        st.write(
            list(filtered_df.columns)
        )

        return

    # --------------------------------------------------------
    # MAP TYPE
    # --------------------------------------------------------

    map_type = st.radio(
        "Select Map View",
        [
            "Facility-wise Map",
            "Ward-wise Map"
        ],
        horizontal=True
    )

    st.divider()

    # --------------------------------------------------------
    # FACILITY MAP
    # --------------------------------------------------------

    if map_type == "Facility-wise Map":

        st.subheader(
            "🏥 Facility-wise Geographical Distribution"
        )

        _facility_map(
            filtered_df,
            lat_col,
            lon_col
        )

    # --------------------------------------------------------
    # WARD MAP
    # --------------------------------------------------------

    else:

        st.subheader(
            "🏙️ Ward-wise Geographical Distribution"
        )

        _ward_map(
            filtered_df,
            lat_col,
            lon_col
        )

    # --------------------------------------------------------
    # TOP GEOGRAPHICAL BURDEN
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        "📍 Top Geographical Burden"
    )

    if "Ward" in filtered_df.columns:

        ward_burden = (
            filtered_df
            .dropna(subset=["Ward"])
            ["Ward"]
            .value_counts()
            .rename_axis("Ward")
            .reset_index(name="Cases")
        )

        if not ward_burden.empty:

            ward_burden.insert(
                0,
                "Rank",
                range(
                    1,
                    len(ward_burden) + 1
                )
            )

            total = ward_burden["Cases"].sum()

            ward_burden["Share (%)"] = (
                ward_burden["Cases"] /
                total * 100
            ).round(2)

            st.dataframe(
                ward_burden.head(20),
                use_container_width=True,
                hide_index=True
            )

    # --------------------------------------------------------
    # TOP FACILITIES
    # --------------------------------------------------------

    if "Facility Name Lform" in filtered_df.columns:

        st.subheader(
            "🏥 Top Facilities by Case Burden"
        )

        facility_burden = (
            filtered_df
            .dropna(
                subset=["Facility Name Lform"]
            )
            ["Facility Name Lform"]
            .value_counts()
            .rename_axis(
                "Facility Name Lform"
            )
            .reset_index(
                name="Cases"
            )
        )

        if not facility_burden.empty:

            facility_burden.insert(
                0,
                "Rank",
                range(
                    1,
                    len(facility_burden) + 1
                )
            )

            total = facility_burden["Cases"].sum()

            facility_burden["Share (%)"] = (
                facility_burden["Cases"] /
                total * 100
            ).round(2)

            st.dataframe(
                facility_burden.head(20),
                use_container_width=True,
                hide_index=True
            )
