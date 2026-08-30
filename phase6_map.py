import pandas as pd
import plotly.express as px
import streamlit as st

from phase2_overview import (
    apply_filters,
    create_filters,
)


# ============================================================
# MAP PAGE
# ============================================================

def render_map(df):

    filters = create_filters(df)

    filtered_df = apply_filters(
        df,
        **filters,
    )

    st.title(
        "🗺️ Map View"
    )

    st.caption(
        "Ward-level geographic visualization"
    )

    # ========================================================
    # CHECK FOR COORDINATES
    # ========================================================

    latitude_candidates = [
        "Latitude",
        "latitude",
        "Lat",
        "lat",
    ]

    longitude_candidates = [
        "Longitude",
        "longitude",
        "Long",
        "Lon",
        "long",
        "lon",
    ]

    latitude_column = next(
        (
            column
            for column in latitude_candidates
            if column in df.columns
        ),
        None,
    )

    longitude_column = next(
        (
            column
            for column in longitude_candidates
            if column in df.columns
        ),
        None,
    )

    # ========================================================
    # NO COORDINATES
    # ========================================================

    if (
        latitude_column is None
        or longitude_column is None
    ):

        st.warning(
            "The current Google Sheet does not contain "
            "latitude/longitude fields."
        )

        st.info(
            "For the final interactive map, we should connect "
            "the Ward field with an official ward boundary or "
            "coordinate dataset. No artificial coordinates "
            "are being used."
        )

        st.subheader(
            "Current Ward Case Distribution"
        )

        ward_data = (
            filtered_df[
                "Ward"
            ]
            .dropna()
            .value_counts()
            .reset_index()
        )

        ward_data.columns = [
            "Ward",
            "Cases",
        ]

        fig = px.bar(
            ward_data.sort_values(
                "Cases"
            ),
            x="Cases",
            y="Ward",
            orientation="h",
            text="Cases",
            title="Ward-wise Cases",
        )

        fig.update_layout(
            height=650
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

        return

    # ========================================================
    # REAL COORDINATE MAP
    # ========================================================

    map_df = filtered_df.dropna(
        subset=[
            latitude_column,
            longitude_column,
        ]
    ).copy()

    if map_df.empty:

        st.warning(
            "No valid geographic records are available "
            "for the selected filters."
        )

        return

    # ========================================================
    # MAP
    # ========================================================

    fig = px.scatter_map(
        map_df,
        lat=latitude_column,
        lon=longitude_column,
        color="Confirmed Diagnosis",
        hover_name="Ward",
        hover_data=[
            "Confirmed Diagnosis",
            "Facility Name Lform",
            "Facility Type",
        ],
        zoom=10,
        height=700,
        title="Health Facility / Case Map",
    )

    fig.update_layout(
        map_style="open-street-map",
        margin={
            "r": 0,
            "t": 50,
            "l": 0,
            "b": 0,
        },
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )
