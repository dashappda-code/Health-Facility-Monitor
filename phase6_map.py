# phase6_map.py

import io
import math
import re
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

# Optional map libraries
try:
    import pydeck as pdk
    PYDECK_AVAILABLE = True
except Exception:
    PYDECK_AVAILABLE = False

# Optional PDF libraries
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False


# ============================================================
# COLUMN HELPERS
# ============================================================

def _norm_col(x):
    return re.sub(r"[^a-z0-9]+", "", str(x).strip().lower())


def _find_column(df, candidates):
    if df is None or df.empty:
        return None

    normalized = {_norm_col(c): c for c in df.columns}

    for candidate in candidates:
        key = _norm_col(candidate)

        if key in normalized:
            return normalized[key]

    # partial matching
    for c in df.columns:
        nc = _norm_col(c)

        for candidate in candidates:
            key = _norm_col(candidate)

            if key in nc or nc in key:
                return c

    return None


def _detect_columns(df):

    disease_col = _find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "DiseaseName",
            "Diagnosis",
            "Disease/Condition",
            "Disease Condition",
        ],
    )

    ward_col = _find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "WardName",
            "BMC Ward",
            "Administrative Ward",
        ],
    )

    facility_col = _find_column(
        df,
        [
            "Facility",
            "Facility Name",
            "FacilityName",
            "Health Facility",
            "Institution",
        ],
    )

    lat_col = _find_column(
        df,
        [
            "Address Latitude",
            "Address Lat",
            "Latitude",
            "Lat",
        ],
    )

    lon_col = _find_column(
        df,
        [
            "Address Longitude",
            "Address Long",
            "Longitude",
            "Lon",
            "Lng",
        ],
    )

    address_col = _find_column(
        df,
        [
            "Address",
            "Patient Address",
            "PatientAddress",
            "Residential Address",
            "Residence",
            "Location",
        ],
    )

    date_col = _find_column(
        df,
        [
            "Date",
            "Date of Reporting",
            "Reporting Date",
            "Case Date",
            "Registration Date",
            "Month",
        ],
    )

    area_col = _find_column(
        df,
        [
            "Area",
            "Area Name",
            "Locality",
            "Locality Name",
            "Location Area",
        ],
    )

    return {
        "disease": disease_col,
        "ward": ward_col,
        "facility": facility_col,
        "lat": lat_col,
        "lon": lon_col,
        "address": address_col,
        "date": date_col,
        "area": area_col,
    }


# ============================================================
# GLOBAL LABEL STATE
# ============================================================

def _get_show_labels():

    possible_keys = [
        "show_data_labels",
        "show_labels",
        "global_show_data_labels",
        "🏷️ Show Data Labels",
    ]

    for key in possible_keys:
        if key in st.session_state:
            return bool(st.session_state[key])

    return False


# ============================================================
# CLEAN COORDINATES
# ============================================================

def _clean_coordinates(df, lat_col, lon_col):

    work = df.copy()

    if lat_col is None or lon_col is None:
        return pd.DataFrame()

    work["_lat"] = pd.to_numeric(
        work[lat_col],
        errors="coerce"
    )

    work["_lon"] = pd.to_numeric(
        work[lon_col],
        errors="coerce"
    )

    work = work[
        work["_lat"].between(-90, 90)
        & work["_lon"].between(-180, 180)
    ].copy()

    # Mumbai bounding sanity check
    # Keeps accidental GPS errors out of map
    work = work[
        work["_lat"].between(17.0, 20.5)
        & work["_lon"].between(70.0, 74.5)
    ].copy()

    return work


# ============================================================
# CLUSTER CREATION
# ============================================================

def _create_clusters(df, cluster_size_m=500):

    if df.empty:
        return df.copy()

    work = df.copy()

    # Approximate metres -> degrees
    lat_deg = cluster_size_m / 111000.0

    mean_lat = float(work["_lat"].mean())

    lon_deg = cluster_size_m / (
        111000.0 * max(math.cos(math.radians(mean_lat)), 0.1)
    )

    work["_grid_lat"] = np.floor(
        work["_lat"] / lat_deg
    ).astype(int)

    work["_grid_lon"] = np.floor(
        work["_lon"] / lon_deg
    ).astype(int)

    work["Cluster ID"] = (
        work["_grid_lat"].astype(str)
        + "_"
        + work["_grid_lon"].astype(str)
    )

    cluster_summary = (
        work.groupby("Cluster ID")
        .agg(
            Cluster_Cases=("Cluster ID", "size"),
            Cluster_Latitude=("_lat", "mean"),
            Cluster_Longitude=("_lon", "mean"),
        )
        .reset_index()
    )

    work = work.merge(
        cluster_summary,
        on="Cluster ID",
        how="left",
    )

    return work


# ============================================================
# HOTSPOT CLASSIFICATION
# ============================================================

def _classify_hotspots(cluster_df):

    if cluster_df.empty:
        return cluster_df

    work = cluster_df.copy()

    values = work["Cluster_Cases"].astype(float)

    if len(values) == 1:
        work["Hotspot"] = "High"

    else:
        q25 = values.quantile(0.25)
        q50 = values.quantile(0.50)
        q75 = values.quantile(0.75)

        def classify(x):
            if x >= q75:
                return "Very High"
            elif x >= q50:
                return "High"
            elif x >= q25:
                return "Moderate"
            return "Low"

        work["Hotspot"] = values.apply(classify)

    return work


# ============================================================
# MAP
# ============================================================

def _build_map(cluster_df, show_labels=False):

    if not PYDECK_AVAILABLE:
        st.error(
            "PyDeck is not installed. Please add pydeck to requirements.txt."
        )
        return

    if cluster_df.empty:
        st.info(
            "No valid geographic records are available for the selected filters."
        )
        return

    map_df = cluster_df.copy()

    # Base points
    point_data = map_df[
        [
            "Cluster_Latitude",
            "Cluster_Longitude",
            "Cluster_Cases",
            "Hotspot",
            "Cluster ID",
        ]
    ].drop_duplicates()

    hotspot_layer = pdk.Layer(
        "ScatterplotLayer",
        data=point_data,
        get_position=[
            "Cluster_Longitude",
            "Cluster_Latitude",
        ],
        get_radius="Cluster_Cases * 35",
        radius_min_pixels=8,
        radius_max_pixels=45,
        pickable=True,
        stroked=True,
        filled=True,
        opacity=0.65,
        get_fill_color="[220, 50, 47, 150]",
        get_line_color="[80, 20, 20, 220]",
        line_width_min_pixels=1,
    )

    layers = [hotspot_layer]

    if show_labels:

        text_layer = pdk.Layer(
            "TextLayer",
            data=point_data,
            get_position=[
                "Cluster_Longitude",
                "Cluster_Latitude",
            ],
            get_text="Cluster_Cases",
            get_size=15,
            get_color="[0, 0, 0, 255]",
            get_angle=0,
            get_text_anchor="'middle'",
            get_alignment_baseline="'center'",
            billboard=True,
            pickable=False,
        )

        layers.append(text_layer)

    center_lat = float(map_df["Cluster_Latitude"].mean())
    center_lon = float(map_df["Cluster_Longitude"].mean())

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=10.5,
            pitch=0,
            bearing=0,
        ),
        tooltip={
            "html": """
            <b>Hotspot</b>: {Hotspot}<br/>
            <b>Cases</b>: {Cluster_Cases}<br/>
            <b>Cluster ID</b>: {Cluster ID}
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
# DOWNLOAD DATA
# ============================================================

def _prepare_download_dataframe(
    df,
    cols,
):

    output = pd.DataFrame(index=df.index)

    if cols["disease"]:
        output["Disease"] = df[cols["disease"]]

    if cols["date"]:
        output["Date"] = df[cols["date"]]

    if cols["ward"]:
        output["Ward"] = df[cols["ward"]]

    if cols["facility"]:
        output["Facility"] = df[cols["facility"]]

    if cols["area"]:
        output["Area"] = df[cols["area"]]

    if cols["address"]:
        output["Address"] = df[cols["address"]]

    output["Latitude"] = df["_lat"]
    output["Longitude"] = df["_lon"]
    output["Cluster ID"] = df["Cluster ID"]
    output["Cluster Cases"] = df["Cluster_Cases"]
    output["Hotspot Classification"] = df["Hotspot"]

    return output


# ============================================================
# PDF
# ============================================================

def _create_pdf(cluster_df, selected_disease, filter_info):

    if not MATPLOTLIB_AVAILABLE:
        return None

    buffer = io.BytesIO()

    with PdfPages(buffer) as pdf:

        fig = plt.figure(figsize=(11.69, 8.27))
        ax = fig.add_subplot(111)

        ax.axis("off")

        ax.text(
            0.05,
            0.92,
            "GEOGRAPHIC HOTSPOT ANALYSIS",
            fontsize=18,
            fontweight="bold",
        )

        ax.text(
            0.05,
            0.86,
            f"Disease: {selected_disease}",
            fontsize=12,
        )

        y = 0.81

        for key, value in filter_info.items():

            ax.text(
                0.05,
                y,
                f"{key}: {value}",
                fontsize=10,
            )

            y -= 0.035

        ax.text(
            0.05,
            y - 0.02,
            f"Total clusters: {len(cluster_df)}",
            fontsize=11,
            fontweight="bold",
        )

        pdf.savefig(fig)
        plt.close(fig)

        # Cluster summary
        fig = plt.figure(figsize=(11.69, 8.27))
        ax = fig.add_subplot(111)
        ax.axis("off")

        summary = (
            cluster_df[
                [
                    "Cluster ID",
                    "Cluster_Cases",
                    "Hotspot",
                ]
            ]
            .drop_duplicates()
            .sort_values(
                "Cluster_Cases",
                ascending=False,
            )
            .head(25)
        )

        table_data = [
            [
                "Cluster",
                "Cases",
                "Classification",
            ]
        ]

        for _, row in summary.iterrows():

            table_data.append(
                [
                    str(row["Cluster ID"]),
                    str(int(row["Cluster_Cases"])),
                    str(row["Hotspot"]),
                ]
            )

        table = ax.table(
            cellText=table_data,
            loc="center",
            cellLoc="center",
        )

        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)

        ax.set_title(
            "Top Geographic Hotspots",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )

        pdf.savefig(fig)
        plt.close(fig)

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# MAIN RENDER
# ============================================================

def render_map(
    df,
    selected_disease=None,
    filter_info=None,
):

    st.markdown(
        "## 🗺️ Geographic Hotspot Map"
    )

    st.caption(
        "Patient/address geographic coordinates based hotspot analysis"
    )

    if df is None or df.empty:
        st.info("No data available.")
        return

    cols = _detect_columns(df)

    if cols["lat"] is None or cols["lon"] is None:

        st.warning(
            "Address Latitude / Address Longitude columns were not found."
        )

        st.info(
            "Hotspot mapping requires valid patient/address geographic coordinates."
        )

        return

    # --------------------------------------------------------
    # Disease selection
    # --------------------------------------------------------

    working = df.copy()

    if cols["disease"]:

        diseases = (
            working[cols["disease"]]
            .dropna()
            .astype(str)
            .str.strip()
        )

        diseases = sorted(
            [x for x in diseases.unique() if x]
        )

        if selected_disease is not None:

            selected_disease = str(selected_disease)

            if selected_disease in diseases:

                working = working[
                    working[cols["disease"]]
                    .astype(str)
                    .str.strip()
                    == selected_disease
                ].copy()

    # --------------------------------------------------------
    # Coordinates
    # --------------------------------------------------------

    working = _clean_coordinates(
        working,
        cols["lat"],
        cols["lon"],
    )

    if working.empty:

        st.warning(
            "No valid address coordinates are available for the selected filters."
        )

        return

    # --------------------------------------------------------
    # Cluster size
    # --------------------------------------------------------

    cluster_size = st.select_slider(
        "Hotspot Cluster Size",
        options=[
            200,
            500,
            1000,
            1500,
        ],
        value=500,
        format_func=lambda x: f"{x} metres",
        key="phase6_cluster_size",
    )

    # --------------------------------------------------------
    # Create clusters
    # --------------------------------------------------------

    working = _create_clusters(
        working,
        cluster_size_m=cluster_size,
    )

    cluster_df = (
        working[
            [
                "Cluster ID",
                "Cluster_Cases",
                "Cluster_Latitude",
                "Cluster_Longitude",
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    cluster_df = _classify_hotspots(
        cluster_df
    )

    working = working.drop(
        columns=[
            "Cluster_Cases",
            "Cluster_Latitude",
            "Cluster_Longitude",
        ],
        errors="ignore",
    )

    working = working.merge(
        cluster_df,
        on="Cluster ID",
        how="left",
    )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Mapped Records",
        f"{len(working):,}",
    )

    c2.metric(
        "Geographic Clusters",
        f"{len(cluster_df):,}",
    )

    c3.metric(
        "Highest Cluster",
        f"{int(cluster_df['Cluster_Cases'].max()):,}"
        if not cluster_df.empty
        else "0",
    )

    c4.metric(
        "Very High Hotspots",
        f"{(cluster_df['Hotspot'] == 'Very High').sum():,}",
    )

    st.divider()

    # --------------------------------------------------------
    # MAP
    # --------------------------------------------------------

    show_labels = _get_show_labels()

    _build_map(
        cluster_df,
        show_labels=show_labels,
    )

    st.caption(
        "Each hotspot represents a geographic cluster of patient/address records. "
        "Cluster size is controlled above."
    )

    # --------------------------------------------------------
    # TABLE
    # --------------------------------------------------------

    st.markdown(
        "### 🔥 Hotspot Summary"
    )

    hotspot_summary = (
        cluster_df[
            [
                "Cluster ID",
                "Cluster_Cases",
                "Hotspot",
                "Cluster_Latitude",
                "Cluster_Longitude",
            ]
        ]
        .sort_values(
            "Cluster_Cases",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    hotspot_summary.index = hotspot_summary.index + 1

    st.dataframe(
        hotspot_summary,
        use_container_width=True,
        height=350,
    )

    # --------------------------------------------------------
    # DOWNLOADS
    # --------------------------------------------------------

    st.markdown(
        "### ⬇️ Download Hotspot Data"
    )

    download_df = _prepare_download_dataframe(
        working,
        cols,
    )

    excel_buffer = io.BytesIO()

    try:

        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl",
        ) as writer:

            download_df.to_excel(
                writer,
                index=False,
                sheet_name="Hotspot Data",
            )

            hotspot_summary.to_excel(
                writer,
                index=False,
                sheet_name="Hotspot Summary",
            )

        excel_buffer.seek(0)

        col1, col2, col3 = st.columns(3)

        with col1:

            st.download_button(
                "📊 Download Hotspot Excel",
                data=excel_buffer.getvalue(),
                file_name="geographic_hotspot_data.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

        with col2:

            csv_data = download_df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "📄 Download Hotspot CSV",
                data=csv_data,
                file_name="geographic_hotspot_data.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col3:

            if filter_info is None:
                filter_info = {}

            pdf_data = _create_pdf(
                cluster_df,
                selected_disease or "All",
                filter_info,
            )

            if pdf_data:

                st.download_button(
                    "📕 Download Hotspot PDF",
                    data=pdf_data,
                    file_name="geographic_hotspot_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

    except Exception as e:

        st.warning(
            f"Download preparation issue: {e}"
        )

    # --------------------------------------------------------
    # WARD SUMMARY
    # --------------------------------------------------------

    if cols["ward"]:

        st.markdown(
            "### 🏢 Ward-wise Geographic Summary"
        )

        ward_summary = (
            working.groupby(
                cols["ward"],
                dropna=False,
            )
            .agg(
                Cases=("Cluster ID", "size"),
                Geographic_Clusters=("Cluster ID", "nunique"),
            )
            .reset_index()
        )

        ward_summary = ward_summary.sort_values(
            "Cases",
            ascending=False,
        )

        st.dataframe(
            ward_summary,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # FACILITY SUMMARY
    # --------------------------------------------------------

    if cols["facility"]:

        st.markdown(
            "### 🏥 Facility-wise Geographic Summary"
        )

        facility_summary = (
            working.groupby(
                cols["facility"],
                dropna=False,
            )
            .agg(
                Cases=("Cluster ID", "size"),
                Geographic_Clusters=("Cluster ID", "nunique"),
            )
            .reset_index()
        )

        facility_summary = facility_summary.sort_values(
            "Cases",
            ascending=False,
        )

        st.dataframe(
            facility_summary,
            use_container_width=True,
        )
