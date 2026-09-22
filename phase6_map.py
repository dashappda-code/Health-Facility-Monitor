import io
import math

import numpy as np
import pandas as pd
import streamlit as st
import pydeck as pdk


# ============================================================
# PHASE 6
# DISEASE HOTSPOT & GEOGRAPHIC ANALYSIS
# ============================================================


# ============================================================
# BASIC HELPERS
# ============================================================

def _clean_text(df, column):

    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="object")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _valid_values(series):

    if series is None:
        return pd.Series(dtype="object")

    values = (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return values[
        ~values.str.lower().isin(
            [
                "",
                "nan",
                "nat",
                "none",
                "null",
            ]
        )
    ]


def _find_column(df, candidates):

    if df is None or df.empty:
        return None

    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:

        key = str(candidate).strip().lower()

        if key in normalized:
            return normalized[key]

    return None


# ============================================================
# FIND DATA COLUMNS
# ============================================================

def _get_columns(df):

    disease_column = _find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "Disease/Diagnosis",
            "Diagnosis",
            "Diagnosis Name",
            "Condition",
            "Disease Type",
        ],
    )

    ward_column = _find_column(
        df,
        [
            "Ward Name",
            "Ward",
            "Ward No",
            "Ward Number",
        ],
    )

    facility_column = _find_column(
        df,
        [
            "Facility Name",
            "Facility",
            "Health Facility",
            "Health Facility Name",
        ],
    )

    address_column = _find_column(
        df,
        [
            "Patient Address",
            "Address",
            "Patient Location",
            "Location",
        ],
    )

    area_column = _find_column(
        df,
        [
            "Area Name",
            "Area",
            "Locality Name",
            "Locality",
            "Colony",
            "Mohalla",
            "Area/Locality",
        ],
    )

    latitude_column = _find_column(
        df,
        [
            "Address Latitude",
            "Address Lat",
        ],
    )

    longitude_column = _find_column(
        df,
        [
            "Address Longitude",
            "Address Long",
            "Address Lng",
        ],
    )

    date_column = _find_column(
        df,
        [
            "Date",
            "Case Date",
            "Visit Date",
            "Report Date",
            "Registration Date",
            "Date of Visit",
            "Month",
        ],
    )

    return {
        "disease": disease_column,
        "ward": ward_column,
        "facility": facility_column,
        "address": address_column,
        "area": area_column,
        "latitude": latitude_column,
        "longitude": longitude_column,
        "date": date_column,
    }


# ============================================================
# GLOBAL DATA LABEL TOGGLE
# ============================================================

def _global_data_labels_enabled():

    possible_keys = [
        "show_data_labels",
        "global_show_data_labels",
        "chart_show_data_labels",
        "show_labels",
        "data_labels",
    ]

    for key in possible_keys:

        if key in st.session_state:

            try:
                return bool(
                    st.session_state[key]
                )
            except Exception:
                return False

    return False


# ============================================================
# PREPARE VALID COORDINATES
# ============================================================

def _prepare_coordinates(
    df,
    latitude_column,
    longitude_column,
):

    if (
        latitude_column is None
        or longitude_column is None
    ):
        return pd.DataFrame()

    work = df.copy()

    work["__latitude"] = pd.to_numeric(
        work[latitude_column],
        errors="coerce",
    )

    work["__longitude"] = pd.to_numeric(
        work[longitude_column],
        errors="coerce",
    )

    work = work[
        work["__latitude"].between(
            -90,
            90,
        )
        & work["__longitude"].between(
            -180,
            180,
        )
    ].copy()

    work = work[
        work["__latitude"].notna()
        & work["__longitude"].notna()
    ].copy()

    return work


# ============================================================
# CREATE GEOGRAPHIC CLUSTERS
# ============================================================

def _create_clusters(
    df,
    grid_size,
):

    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    # --------------------------------------------------------
    # CREATE GRID BIN
    # --------------------------------------------------------

    work["__lat_bin"] = np.floor(
        work["__latitude"]
        / grid_size
    ).astype("int64")

    work["__lon_bin"] = np.floor(
        work["__longitude"]
        / grid_size
    ).astype("int64")

    # --------------------------------------------------------
    # CREATE CLUSTER ID
    # --------------------------------------------------------

    work["Cluster ID"] = (
        "C-"
        + work["__lat_bin"]
        .astype(str)
        + "-"
        + work["__lon_bin"]
        .astype(str)
    )

    # --------------------------------------------------------
    # CLUSTER SUMMARY
    # --------------------------------------------------------

    cluster_group = (
        work
        .groupby(
            "Cluster ID",
            dropna=False,
        )
        .agg(
            Latitude=(
                "__latitude",
                "mean",
            ),
            Longitude=(
                "__longitude",
                "mean",
            ),
            Cases=(
                "__latitude",
                "size",
            ),
        )
        .reset_index()
    )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    cluster_group = (
        cluster_group
        .sort_values(
            "Cases",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    cluster_group.insert(
        0,
        "Rank",
        range(
            1,
            len(cluster_group) + 1,
        ),
    )

    # --------------------------------------------------------
    # HOTSPOT CLASSIFICATION
    # --------------------------------------------------------

    if len(cluster_group) == 1:

        cluster_group[
            "Hotspot Level"
        ] = "Very High"

    else:

        q75 = cluster_group[
            "Cases"
        ].quantile(0.75)

        q50 = cluster_group[
            "Cases"
        ].quantile(0.50)

        q25 = cluster_group[
            "Cases"
        ].quantile(0.25)

        def classify(value):

            if value >= q75:
                return "Very High"

            if value >= q50:
                return "High"

            if value >= q25:
                return "Moderate"

            return "Low"

        cluster_group[
            "Hotspot Level"
        ] = (
            cluster_group[
                "Cases"
            ]
            .apply(classify)
        )

    # --------------------------------------------------------
    # LABEL
    # --------------------------------------------------------

    cluster_group[
        "Cluster Label"
    ] = (
        cluster_group[
            "Cluster ID"
        ].astype(str)
        + " | "
        + cluster_group[
            "Cases"
        ].astype(str)
        + " cases"
    )

    return cluster_group


# ============================================================
# HOTSPOT COLOUR
# ============================================================

def _hotspot_color(level):

    if level == "Very High":
        return [
            220,
            38,
            38,
            220,
        ]

    if level == "High":
        return [
            245,
            130,
            32,
            220,
        ]

    if level == "Moderate":
        return [
            245,
            200,
            55,
            210,
        ]

    return [
        80,
        150,
        100,
        180,
    ]


# ============================================================
# ATTACH CLUSTER INFORMATION
# ============================================================

def _attach_cluster_information(
    cluster_df,
    work_df,
    disease_column,
    ward_column,
    facility_column,
):

    if cluster_df is None or cluster_df.empty:
        return cluster_df

    if work_df is None or work_df.empty:
        return cluster_df

    result = cluster_df.copy()
    work = work_df.copy()

    # --------------------------------------------------------
    # IMPORTANT FIX:
    # ENSURE CLUSTER ID EXISTS IN RECORD DATA
    # --------------------------------------------------------

    if "Cluster ID" not in work.columns:

        if (
            "__lat_bin" in work.columns
            and "__lon_bin" in work.columns
        ):

            work["Cluster ID"] = (
                "C-"
                + work[
                    "__lat_bin"
                ].astype(str)
                + "-"
                + work[
                    "__lon_bin"
                ].astype(str)
            )

        else:

            # Fallback nearest cluster matching

            work["Cluster ID"] = ""

            cluster_coordinates = (
                cluster_df[
                    [
                        "Cluster ID",
                        "Latitude",
                        "Longitude",
                    ]
                ]
                .copy()
            )

            for idx, row in work.iterrows():

                distances = (
                    (
                        cluster_coordinates[
                            "Latitude"
                        ]
                        - row[
                            "__latitude"
                        ]
                    ) ** 2
                    +
                    (
                        cluster_coordinates[
                            "Longitude"
                        ]
                        - row[
                            "__longitude"
                        ]
                    ) ** 2
                )

                nearest_index = (
                    distances.idxmin()
                )

                work.at[
                    idx,
                    "Cluster ID",
                ] = (
                    cluster_coordinates.loc[
                        nearest_index,
                        "Cluster ID",
                    ]
                )

    # --------------------------------------------------------
    # WARD
    # --------------------------------------------------------

    if (
        ward_column is not None
        and ward_column in work.columns
    ):

        ward_temp = work[
            [
                "Cluster ID",
                ward_column,
            ]
        ].copy()

        ward_temp[
            ward_column
        ] = (
            ward_temp[
                ward_column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_temp = ward_temp[
            ward_temp[
                ward_column
            ].ne("")
            & ~ward_temp[
                ward_column
            ].str.lower().isin(
                [
                    "nan",
                    "none",
                    "null",
                    "nat",
                ]
            )
        ]

        if not ward_temp.empty:

            ward_summary = (
                ward_temp
                .groupby(
                    "Cluster ID",
                    dropna=False,
                )[ward_column]
                .agg(
                    lambda x:
                    ", ".join(
                        x.value_counts()
                        .head(3)
                        .index
                        .tolist()
                    )
                )
                .reset_index(
                    name="Ward"
                )
            )

            result = result.merge(
                ward_summary,
                on="Cluster ID",
                how="left",
            )

        else:

            result["Ward"] = ""

    else:

        result["Ward"] = ""

    # --------------------------------------------------------
    # FACILITY
    # --------------------------------------------------------

    if (
        facility_column is not None
        and facility_column in work.columns
    ):

        facility_temp = work[
            [
                "Cluster ID",
                facility_column,
            ]
        ].copy()

        facility_temp[
            facility_column
        ] = (
            facility_temp[
                facility_column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_temp = facility_temp[
            facility_temp[
                facility_column
            ].ne("")
            & ~facility_temp[
                facility_column
            ].str.lower().isin(
                [
                    "nan",
                    "none",
                    "null",
                    "nat",
                ]
            )
        ]

        if not facility_temp.empty:

            facility_summary = (
                facility_temp
                .groupby(
                    "Cluster ID",
                    dropna=False,
                )[facility_column]
                .agg(
                    lambda x:
                    ", ".join(
                        x.value_counts()
                        .head(3)
                        .index
                        .tolist()
                    )
                )
                .reset_index(
                    name="Facility"
                )
            )

            result = result.merge(
                facility_summary,
                on="Cluster ID",
                how="left",
            )

        else:

            result["Facility"] = ""

    else:

        result["Facility"] = ""

    # --------------------------------------------------------
    # DISEASE
    # --------------------------------------------------------

    if (
        disease_column is not None
        and disease_column in work.columns
    ):

        disease_temp = work[
            [
                "Cluster ID",
                disease_column,
            ]
        ].copy()

        disease_temp[
            disease_column
        ] = (
            disease_temp[
                disease_column
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_temp = disease_temp[
            disease_temp[
                disease_column
            ].ne("")
            & ~disease_temp[
                disease_column
            ].str.lower().isin(
                [
                    "nan",
                    "none",
                    "null",
                    "nat",
                ]
            )
        ]

        if not disease_temp.empty:

            disease_summary = (
                disease_temp
                .groupby(
                    "Cluster ID",
                    dropna=False,
                )[disease_column]
                .agg(
                    lambda x:
                    ", ".join(
                        x.value_counts()
                        .head(3)
                        .index
                        .tolist()
                    )
                )
                .reset_index(
                    name="Disease"
                )
            )

            result = result.merge(
                disease_summary,
                on="Cluster ID",
                how="left",
            )

        else:

            result["Disease"] = ""

    else:

        result["Disease"] = ""

    # --------------------------------------------------------
    # CLEAN
    # --------------------------------------------------------

    for column in [
        "Ward",
        "Facility",
        "Disease",
    ]:

        if column not in result.columns:
            result[column] = ""

        result[column] = (
            result[column]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    return result


# ============================================================
# CLUSTER MAP
# ============================================================

def _build_cluster_map(
    cluster_df,
    show_labels,
):

    if cluster_df is None or cluster_df.empty:
        return None

    plot_df = cluster_df.copy()

    plot_df[
        "fill_color"
    ] = (
        plot_df[
            "Hotspot Level"
        ]
        .apply(_hotspot_color)
    )

    plot_df[
        "radius"
    ] = (
        np.sqrt(
            plot_df[
                "Cases"
            ].clip(
                lower=1
            )
        )
        * 70
    )

    plot_df[
        "radius"
    ] = (
        plot_df[
            "radius"
        ]
        .clip(
            lower=100,
            upper=900,
        )
    )

    plot_df[
        "label"
    ] = (
        plot_df[
            "Cases"
        ].astype(str)
    )

    layers = []

    # --------------------------------------------------------
    # CLUSTER LAYER
    # --------------------------------------------------------

    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=plot_df,
            get_position=[
                "Longitude",
                "Latitude",
            ],
            get_radius="radius",
            get_fill_color="fill_color",
            get_line_color=[
                60,
                60,
                60,
                180,
            ],
            line_width_min_pixels=1,
            stroked=True,
            filled=True,
            pickable=True,
            auto_highlight=True,
        )
    )

    # --------------------------------------------------------
    # LABEL LAYER
    # --------------------------------------------------------

    if show_labels:

        layers.append(
            pdk.Layer(
                "TextLayer",
                data=plot_df,
                get_position=[
                    "Longitude",
                    "Latitude",
                ],
                get_text="label",
                get_size=16,
                get_color=[
                    20,
                    20,
                    20,
                    255,
                ],
                get_alignment_baseline=(
                    "middle"
                ),
                get_text_anchor=(
                    "middle"
                ),
                billboard=True,
            )
        )

    center_lat = float(
        plot_df[
            "Latitude"
        ].mean()
    )

    center_lon = float(
        plot_df[
            "Longitude"
        ].mean()
    )

    if math.isnan(center_lat):
        center_lat = 18.52

    if math.isnan(center_lon):
        center_lon = 73.85

    # --------------------------------------------------------
    # DYNAMIC ZOOM
    # --------------------------------------------------------

    if len(plot_df) <= 5:
        zoom = 13
    elif len(plot_df) <= 20:
        zoom = 11
    else:
        zoom = 10

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
        pitch=0,
    )

    tooltip = {
        "html": """
        <b>Cluster:</b> {Cluster ID}<br/>
        <b>Cases:</b> {Cases}<br/>
        <b>Hotspot:</b> {Hotspot Level}<br/>
        <b>Ward:</b> {Ward}<br/>
        <b>Facility:</b> {Facility}<br/>
        <b>Disease:</b> {Disease}
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
    )


# ============================================================
# WARD HOTSPOTS
# ============================================================

def _ward_hotspots(
    work_df,
    ward_column,
):

    if (
        ward_column is None
        or ward_column not in work_df.columns
        or work_df.empty
    ):
        return pd.DataFrame()

    temp = work_df.copy()

    temp["Ward"] = _valid_values(
        temp[ward_column]
    )

    temp = temp[
        temp["Ward"].ne("")
    ]

    if temp.empty:
        return pd.DataFrame()

    summary = (
        temp
        .groupby(
            "Ward",
            dropna=False,
        )
        .agg(
            Cases=(
                "__latitude",
                "size",
            ),
            Latitude=(
                "__latitude",
                "mean",
            ),
            Longitude=(
                "__longitude",
                "mean",
            ),
        )
        .reset_index()
    )

    summary = (
        summary
        .sort_values(
            "Cases",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    summary.insert(
        0,
        "Rank",
        range(
            1,
            len(summary) + 1,
        ),
    )

    total = summary[
        "Cases"
    ].sum()

    if total > 0:

        summary[
            "Percentage"
        ] = (
            summary[
                "Cases"
            ]
            / total
            * 100
        ).round(2)

    else:

        summary[
            "Percentage"
        ] = 0

    return summary


# ============================================================
# AREA SUMMARY
# ============================================================

def _area_summary(
    work_df,
    area_column,
    address_column,
):

    selected_column = area_column

    if selected_column is None:
        selected_column = address_column

    if (
        selected_column is None
        or selected_column not in work_df.columns
        or work_df.empty
    ):
        return pd.DataFrame()

    temp = work_df.copy()

    temp["Area"] = _valid_values(
        temp[selected_column]
    )

    temp = temp[
        temp["Area"].ne("")
    ]

    if temp.empty:
        return pd.DataFrame()

    summary = (
        temp
        .groupby(
            "Area",
            dropna=False,
        )
        .agg(
            Cases=(
                "__latitude",
                "size",
            ),
            Latitude=(
                "__latitude",
                "mean",
            ),
            Longitude=(
                "__longitude",
                "mean",
            ),
        )
        .reset_index()
    )

    summary = (
        summary
        .sort_values(
            "Cases",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    summary.insert(
        0,
        "Rank",
        range(
            1,
            len(summary) + 1,
        ),
    )

    return summary


# ============================================================
# FACILITY SUMMARY
# ============================================================

def _facility_summary(
    work_df,
    facility_column,
):

    if (
        facility_column is None
        or facility_column not in work_df.columns
        or work_df.empty
    ):
        return pd.DataFrame()

    temp = work_df.copy()

    temp["Facility"] = _valid_values(
        temp[facility_column]
    )

    temp = temp[
        temp["Facility"].ne("")
    ]

    if temp.empty:
        return pd.DataFrame()

    summary = (
        temp
        .groupby(
            "Facility",
            dropna=False,
        )
        .size()
        .reset_index(
            name="Cases"
        )
        .sort_values(
            "Cases",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    summary.insert(
        0,
        "Rank",
        range(
            1,
            len(summary) + 1,
        ),
    )

    return summary


# ============================================================
# EXCEL DOWNLOAD
# ============================================================

def _create_excel(
    cluster_df,
    ward_df,
    area_df,
    facility_df,
    records_df,
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        cluster_df.to_excel(
            writer,
            index=False,
            sheet_name="Hotspot Clusters",
        )

        ward_df.to_excel(
            writer,
            index=False,
            sheet_name="Ward Hotspots",
        )

        area_df.to_excel(
            writer,
            index=False,
            sheet_name="Area Summary",
        )

        facility_df.to_excel(
            writer,
            index=False,
            sheet_name="Facility Summary",
        )

        records_df.to_excel(
            writer,
            index=False,
            sheet_name="Hotspot Records",
        )

    output.seek(0)

    return output.getvalue()


# ============================================================
# CSV DOWNLOAD
# ============================================================

def _create_csv(cluster_df):

    return cluster_df.to_csv(
        index=False
    ).encode("utf-8")


# ============================================================
# PDF REPORT
# ============================================================

def _create_pdf_report(
    cluster_df,
    ward_df,
    area_df,
    disease_name,
):

    try:

        import matplotlib.pyplot as plt

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import (
            getSampleStyleSheet,
        )
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            Image,
        )

    except ImportError:

        return None

    pdf_buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=35,
    )

    styles = getSampleStyleSheet()

    story = []

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Disease Hotspot & Geographic Analysis Report",
            styles["Title"],
        )
    )

    story.append(
        Spacer(
            1,
            10,
        )
    )

    story.append(
        Paragraph(
            f"<b>Disease displayed on map:</b> "
            f"{disease_name}",
            styles["Normal"],
        )
    )

    story.append(
        Paragraph(
            f"<b>Total geographic clusters:</b> "
            f"{len(cluster_df):,}",
            styles["Normal"],
        )
    )

    if not cluster_df.empty:

        story.append(
            Paragraph(
                f"<b>Total mapped cases:</b> "
                f"{int(cluster_df['Cases'].sum()):,}",
                styles["Normal"],
            )
        )

    story.append(
        Spacer(
            1,
            15,
        )
    )

    # --------------------------------------------------------
    # STATIC MAP
    # --------------------------------------------------------

    if not cluster_df.empty:

        fig = plt.figure(
            figsize=(7, 5)
        )

        level_colors = {
            "Very High": "red",
            "High": "orange",
            "Moderate": "gold",
            "Low": "green",
        }

        level_sizes = {
            "Very High": 450,
            "High": 320,
            "Moderate": 220,
            "Low": 140,
        }

        for level in [
            "Low",
            "Moderate",
            "High",
            "Very High",
        ]:

            part = cluster_df[
                cluster_df[
                    "Hotspot Level"
                ] == level
            ]

            if part.empty:
                continue

            plt.scatter(
                part[
                    "Longitude"
                ],
                part[
                    "Latitude"
                ],
                s=part[
                    "Cases"
                ].apply(
                    lambda x:
                    level_sizes.get(
                        level,
                        150,
                    )
                    + x * 20
                ),
                alpha=0.55,
                label=level,
                c=level_colors.get(
                    level,
                    "blue",
                ),
            )

        for _, row in cluster_df.head(
            15
        ).iterrows():

            plt.annotate(
                str(
                    int(
                        row["Cases"]
                    )
                ),
                (
                    row["Longitude"],
                    row["Latitude"],
                ),
                fontsize=8,
            )

        plt.xlabel(
            "Longitude"
        )

        plt.ylabel(
            "Latitude"
        )

        plt.title(
            "Geographic Disease Hotspot Clusters"
        )

        plt.legend(
            fontsize=8
        )

        plt.tight_layout()

        image_buffer = io.BytesIO()

        plt.savefig(
            image_buffer,
            format="png",
            dpi=150,
            bbox_inches="tight",
        )

        plt.close(fig)

        image_buffer.seek(0)

        story.append(
            Image(
                image_buffer,
                width=6.5 * inch,
                height=4.5 * inch,
            )
        )

        story.append(
            Spacer(
                1,
                15,
            )
        )

    # --------------------------------------------------------
    # CLUSTER TABLE
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Hotspot Cluster Summary",
            styles["Heading2"],
        )
    )

    if not cluster_df.empty:

        table_data = [
            [
                "Rank",
                "Cluster",
                "Cases",
                "Hotspot",
                "Ward",
            ]
        ]

        for _, row in cluster_df.head(
            20
        ).iterrows():

            table_data.append(
                [
                    str(
                        row["Rank"]
                    ),
                    str(
                        row["Cluster ID"]
                    ),
                    str(
                        row["Cases"]
                    ),
                    str(
                        row["Hotspot Level"]
                    ),
                    str(
                        row.get(
                            "Ward",
                            "",
                        )
                    ),
                ]
            )

        table = Table(
            table_data,
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.lightgrey,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                ]
            )
        )

        story.append(
            table
        )

    # --------------------------------------------------------
    # WARD TABLE
    # --------------------------------------------------------

    story.append(
        Spacer(
            1,
            15,
        )
    )

    story.append(
        Paragraph(
            "Ward-wise Hotspot Summary",
            styles["Heading2"],
        )
    )

    if not ward_df.empty:

        ward_table = [
            [
                "Rank",
                "Ward",
                "Cases",
                "%",
            ]
        ]

        for _, row in ward_df.head(
            20
        ).iterrows():

            ward_table.append(
                [
                    str(
                        row["Rank"]
                    ),
                    str(
                        row["Ward"]
                    ),
                    str(
                        row["Cases"]
                    ),
                    str(
                        row["Percentage"]
                    ),
                ]
            )

        table = Table(
            ward_table,
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.lightgrey,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.grey,
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                ]
            )
        )

        story.append(
            table
        )

    # --------------------------------------------------------
    # NOTE
    # --------------------------------------------------------

    story.append(
        Spacer(
            1,
            15,
        )
    )

    story.append(
        Paragraph(
            "Note: Geographic clusters are generated from "
            "the available Address Latitude and Address "
            "Longitude values. Hotspot levels represent "
            "relative case concentration within the "
            "currently filtered dataset and are not a "
            "formal spatial statistical significance test.",
            styles["Normal"],
        )
    )

    doc.build(
        story
    )

    pdf_buffer.seek(0)

    return pdf_buffer.getvalue()


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_map(df):

    st.subheader(
        "🗺️ Disease Hotspot & Geographic Analysis"
    )

    # ========================================================
    # EMPTY DATA
    # ========================================================

    if df is None or df.empty:

        st.info(
            "No records are available for the "
            "selected Global Dashboard Filters."
        )

        return

    # ========================================================
    # COLUMN DETECTION
    # ========================================================

    columns = _get_columns(df)

    disease_column = columns[
        "disease"
    ]

    ward_column = columns[
        "ward"
    ]

    facility_column = columns[
        "facility"
    ]

    address_column = columns[
        "address"
    ]

    area_column = columns[
        "area"
    ]

    latitude_column = columns[
        "latitude"
    ]

    longitude_column = columns[
        "longitude"
    ]

    # ========================================================
    # ADDRESS COORDINATE CHECK
    # ========================================================

    if (
        latitude_column is None
        or longitude_column is None
    ):

        st.info(
            "🗺️ Address Latitude and Address Longitude "
            "columns are not available in the current "
            "Google Sheet data."
        )

        st.markdown(
            """
            **Required Google Sheet columns:**

            - `Address Latitude`
            - `Address Longitude`

            These coordinates should represent the
            patient's geographic/address location.

            No artificial coordinates are generated by
            this dashboard.
            """
        )

        return

    # ========================================================
    # PREPARE COORDINATES
    # ========================================================

    work = _prepare_coordinates(
        df,
        latitude_column,
        longitude_column,
    )

    if work.empty:

        st.info(
            "Address Latitude and Address Longitude "
            "columns are present, but no valid geographic "
            "coordinates are available for the currently "
            "filtered records."
        )

        return

    # ========================================================
    # HEADER
    # ========================================================

    st.caption(
        "The map uses the current Global Dashboard "
        "Filters. Disease selection below controls only "
        "which disease is displayed on the map."
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Filtered Records",
            f"{len(df):,}",
        )

    with c2:

        st.metric(
            "Valid Geographic Records",
            f"{len(work):,}",
        )

    with c3:

        st.metric(
            "Coordinates",
            "Available",
        )

    with c4:

        if disease_column is not None:

            disease_values = _valid_values(
                work[
                    disease_column
                ]
            )

            st.metric(
                "Diseases",
                f"{disease_values.nunique():,}",
            )

        else:

            st.metric(
                "Diseases",
                "N/A",
            )

    # ========================================================
    # DISEASE SELECTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 🦠 Disease Selection for Map"
    )

    if disease_column is not None:

        disease_values = sorted(
            _valid_values(
                work[
                    disease_column
                ]
            )
            .unique()
            .tolist()
        )

        if len(disease_values) == 0:

            st.info(
                "No valid disease information is "
                "available for the current filtered records."
            )

            return

        if len(disease_values) == 1:

            selected_disease = (
                disease_values[0]
            )

            st.info(
                f"Current disease: "
                f"**{selected_disease}**"
            )

        else:

            selected_disease = st.selectbox(
                "Select Disease to Display on Map",
                options=disease_values,
                key="phase6_selected_disease",
            )

        map_df = work[
            work[
                disease_column
            ]
            .astype(str)
            .str.strip()
            ==
            str(
                selected_disease
            ).strip()
        ].copy()

    else:

        selected_disease = (
            "All Available Records"
        )

        map_df = work.copy()

        st.info(
            "Disease column was not identified. "
            "All valid geographic records will be displayed."
        )

    if map_df.empty:

        st.info(
            "No geographic records are available "
            "for the selected disease."
        )

        return

    # ========================================================
    # MAP SETTINGS
    # ========================================================

    st.markdown(
        "### ⚙️ Hotspot Map Settings"
    )

    s1, s2 = st.columns(2)

    with s1:

        cluster_size_label = st.selectbox(
            "Geographic Cluster Size",
            options=[
                "Small (~200 m)",
                "Medium (~500 m)",
                "Large (~1 km)",
            ],
            index=1,
            key="phase6_cluster_size",
        )

    with s2:

        map_view = st.selectbox(
            "Map View",
            options=[
                "Hotspot Clusters",
                "Ward Hotspots",
                "Address Points",
            ],
            key="phase6_map_view",
        )

    grid_sizes = {
        "Small (~200 m)": 0.002,
        "Medium (~500 m)": 0.005,
        "Large (~1 km)": 0.01,
    }

    grid_size = grid_sizes[
        cluster_size_label
    ]

    # ========================================================
    # CREATE CLUSTERS
    # ========================================================

    cluster_df = _create_clusters(
        map_df,
        grid_size,
    )

    # --------------------------------------------------------
    # IMPORTANT FIX:
    # CREATE SAME CLUSTER ID IN RECORD DATA
    # --------------------------------------------------------

    map_df[
        "__lat_bin"
    ] = np.floor(
        map_df[
            "__latitude"
        ]
        / grid_size
    ).astype("int64")

    map_df[
        "__lon_bin"
    ] = np.floor(
        map_df[
            "__longitude"
        ]
        / grid_size
    ).astype("int64")

    map_df[
        "Cluster ID"
    ] = (
        "C-"
        + map_df[
            "__lat_bin"
        ].astype(str)
        + "-"
        + map_df[
            "__lon_bin"
        ].astype(str)
    )

    # --------------------------------------------------------
    # ATTACH WARD / FACILITY / DISEASE
    # --------------------------------------------------------

    cluster_df = _attach_cluster_information(
        cluster_df,
        map_df,
        disease_column,
        ward_column,
        facility_column,
    )

    # ========================================================
    # GLOBAL DATA LABEL STATE
    # ========================================================

    show_labels = (
        _global_data_labels_enabled()
    )

    # ========================================================
    # METRICS
    # ========================================================

    hotspot_count = len(
        cluster_df[
            cluster_df[
                "Hotspot Level"
            ].isin(
                [
                    "Very High",
                    "High",
                ]
            )
        ]
    )

    total_cases = len(
        map_df
    )

    if not cluster_df.empty:

        max_cluster_cases = int(
            cluster_df[
                "Cases"
            ].max()
        )

    else:

        max_cluster_cases = 0

    m1, m2, m3, m4 = st.columns(4)

    with m1:

        st.metric(
            "Disease Cases",
            f"{total_cases:,}",
        )

    with m2:

        st.metric(
            "Geographic Clusters",
            f"{len(cluster_df):,}",
        )

    with m3:

        st.metric(
            "High / Very High",
            f"{hotspot_count:,}",
        )

    with m4:

        st.metric(
            "Largest Cluster",
            f"{max_cluster_cases:,}",
        )

    # ========================================================
    # MAP
    # ========================================================

    st.divider()

    st.markdown(
        "### 📍 Geographic Hotspot Map"
    )

    # ========================================================
    # HOTSPOT CLUSTERS
    # ========================================================

    if map_view == "Hotspot Clusters":

        deck = _build_cluster_map(
            cluster_df,
            show_labels,
        )

        if deck is not None:

            st.pydeck_chart(
                deck,
                use_container_width=True,
            )

        st.caption(
            "Each circle represents a geographic disease "
            "cluster. Larger circles indicate more cases. "
            "Hotspot level is relative to the currently "
            "filtered disease dataset."
        )

    # ========================================================
    # WARD HOTSPOTS
    # ========================================================

    elif map_view == "Ward Hotspots":

        ward_df = _ward_hotspots(
            map_df,
            ward_column,
        )

        if ward_df.empty:

            st.info(
                "Ward information is not available "
                "for the current filtered records."
            )

        else:

            ward_plot = (
                ward_df.copy()
            )

            ward_plot[
                "fill_color"
            ] = (
                ward_plot[
                    "Cases"
                ]
                .rank(
                    pct=True
                )
                .apply(
                    lambda x:
                    [
                        int(
                            255 * x
                        ),
                        int(
                            80
                            + 150
                            * (
                                1 - x
                            )
                        ),
                        60,
                        210,
                    ]
                )
            )

            ward_plot[
                "radius"
            ] = (
                np.sqrt(
                    ward_plot[
                        "Cases"
                    ].clip(
                        lower=1
                    )
                )
                * 80
            )

            ward_plot[
                "radius"
            ] = (
                ward_plot[
                    "radius"
                ].clip(
                    100,
                    1000,
                )
            )

            layers = [
                pdk.Layer(
                    "ScatterplotLayer",
                    data=ward_plot,
                    get_position=[
                        "Longitude",
                        "Latitude",
                    ],
                    get_radius="radius",
                    get_fill_color="fill_color",
                    pickable=True,
                    auto_highlight=True,
                )
            ]

            if show_labels:

                ward_plot[
                    "label"
                ] = (
                    ward_plot[
                        "Ward"
                    ].astype(str)
                    + " | "
                    + ward_plot[
                        "Cases"
                    ].astype(str)
                )

                layers.append(
                    pdk.Layer(
                        "TextLayer",
                        data=ward_plot,
                        get_position=[
                            "Longitude",
                            "Latitude",
                        ],
                        get_text="label",
                        get_size=14,
                        get_color=[
                            20,
                            20,
                            20,
                            255,
                        ],
                        billboard=True,
                    )
                )

            center_lat = float(
                ward_plot[
                    "Latitude"
                ].mean()
            )

            center_lon = float(
                ward_plot[
                    "Longitude"
                ].mean()
            )

            deck = pdk.Deck(
                layers=layers,
                initial_view_state=pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=11,
                    pitch=0,
                ),
                tooltip={
                    "html": """
                    <b>Ward:</b> {Ward}<br/>
                    <b>Cases:</b> {Cases}<br/>
                    <b>Percentage:</b> {Percentage}%
                    """
                },
            )

            st.pydeck_chart(
                deck,
                use_container_width=True,
            )

            st.caption(
                "Ward location is represented using the mean "
                "of available patient/address coordinates "
                "within each ward."
            )

    # ========================================================
    # ADDRESS POINTS
    # ========================================================

    else:

        point_df = (
            map_df[
                [
                    "__latitude",
                    "__longitude",
                ]
            ]
            .rename(
                columns={
                    "__latitude":
                        "latitude",
                    "__longitude":
                        "longitude",
                }
            )
        )

        st.map(
            point_df,
            latitude="latitude",
            longitude="longitude",
            use_container_width=True,
        )

        st.caption(
            f"{len(point_df):,} valid address "
            "coordinates are displayed."
        )

    # ========================================================
    # DOWNLOAD SECTION
    # ========================================================

    st.divider()

    st.markdown(
        "### ⬇️ Download Hotspot Data"
    )

    st.caption(
        "The downloads use the current Global Dashboard "
        "Filters, selected disease and selected cluster size."
    )

    # --------------------------------------------------------
    # SUMMARIES
    # --------------------------------------------------------

    ward_df = _ward_hotspots(
        map_df,
        ward_column,
    )

    area_df = _area_summary(
        map_df,
        area_column,
        address_column,
    )

    facility_df = _facility_summary(
        map_df,
        facility_column,
    )

    # --------------------------------------------------------
    # RECORD EXPORT
    # --------------------------------------------------------

    export_records = (
        map_df.copy()
    )

    export_records = (
        export_records.rename(
            columns={
                "__latitude":
                    "Latitude",
                "__longitude":
                    "Longitude",
            }
        )
    )

    # --------------------------------------------------------
    # ADD CLUSTER CASE COUNT
    # --------------------------------------------------------

    cluster_lookup = (
        cluster_df[
            [
                "Cluster ID",
                "Cases",
                "Hotspot Level",
            ]
        ]
        .rename(
            columns={
                "Cases":
                    "Cluster Cases",
            }
        )
    )

    export_records = (
        export_records.merge(
            cluster_lookup,
            on="Cluster ID",
            how="left",
        )
    )

    # --------------------------------------------------------
    # EXCEL
    # --------------------------------------------------------

    try:

        excel_bytes = _create_excel(
            cluster_df,
            ward_df,
            area_df,
            facility_df,
            export_records,
        )

        st.download_button(
            label=(
                "📊 Download Hotspot Data – Excel"
            ),
            data=excel_bytes,
            file_name=(
                "Disease_Hotspot_Analysis.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
            key=(
                "phase6_excel_download"
            ),
        )

    except Exception as e:

        st.warning(
            "Excel download could not be generated."
        )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    csv_bytes = _create_csv(
        cluster_df
    )

    st.download_button(
        label=(
            "📄 Download Cluster Summary – CSV"
        ),
        data=csv_bytes,
        file_name=(
            "Disease_Hotspot_Clusters.csv"
        ),
        mime="text/csv",
        use_container_width=True,
        key=(
            "phase6_csv_download"
        ),
    )

    # ========================================================
    # PDF REPORT
    # ========================================================

    st.markdown(
        "### 📑 Hotspot Management Report"
    )

    pdf_bytes = _create_pdf_report(
        cluster_df,
        ward_df,
        area_df,
        selected_disease,
    )

    if pdf_bytes is not None:

        st.download_button(
            label=(
                "📑 Download Hotspot Report – PDF"
            ),
            data=pdf_bytes,
            file_name=(
                "Disease_Hotspot_Management_Report.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
            key=(
                "phase6_pdf_download"
            ),
        )

    else:

        st.warning(
            "PDF report requires reportlab and matplotlib."
        )

    # ========================================================
    # TOP HOTSPOTS
    # ========================================================

    st.divider()

    st.markdown(
        "### 🔥 Top Geographic Hotspots"
    )

    if not cluster_df.empty:

        display_clusters = (
            cluster_df[
                [
                    "Rank",
                    "Cluster ID",
                    "Cases",
                    "Hotspot Level",
                    "Ward",
                    "Facility",
                    "Latitude",
                    "Longitude",
                ]
            ]
            .head(25)
        )

        st.dataframe(
            display_clusters,
            use_container_width=True,
            hide_index=True,
        )

    # ========================================================
    # WARD SUMMARY
    # ========================================================

    st.markdown(
        "### 🏘️ Ward-wise Hotspot Summary"
    )

    if not ward_df.empty:

        st.dataframe(
            ward_df.head(25),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Ward-wise geographic information "
            "is not available."
        )

    # ========================================================
    # AREA SUMMARY
    # ========================================================

    st.markdown(
        "### 📍 Area-wise Hotspot Summary"
    )

    if not area_df.empty:

        st.dataframe(
            area_df.head(25),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Area/locality information is not available. "
            "Geographic clusters are being used as the "
            "area-level analysis."
        )

    # ========================================================
    # FACILITY SUMMARY
    # ========================================================

    st.markdown(
        "### 🏥 Facility-wise Disease Hotspot Summary"
    )

    if not facility_df.empty:

        st.dataframe(
            facility_df.head(25),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Facility information is not available."
        )

    # ========================================================
    # METHODOLOGY
    # ========================================================

    st.divider()

    st.markdown(
        "### ℹ️ Geographic Analysis Method"
    )

    st.info(
        "Hotspot clusters are generated by grouping "
        "nearby Address Latitude and Address Longitude "
        "values into geographic grid cells. Cluster case "
        "counts are used to identify relative concentration "
        "levels within the currently filtered data. This "
        "is a programme-management visualization and is "
        "not a formal spatial statistical significance test."
    )
