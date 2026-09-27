import streamlit as st
import pandas as pd
import altair as alt

from chart_helpers import data_labels_enabled


# ============================================================
# CONFIGURATION
# ============================================================

AGE_GROUP_ORDER = [
    "<1",
    "1-4",
    "5-14",
    "15-24",
    "25-44",
    "45-64",
    "65+",
    "Unknown",
]

GENDER_ORDER = [
    "Male",
    "Female",
    "Transgender",
    "Other",
    "Unknown",
]

GENDER_COLORS = {
    "Male": "#1F77B4",
    "Female": "#E377C2",
    "Transgender": "#9467BD",
    "Other": "#FF7F0E",
    "Unknown": "#7F7F7F",
}

DEFAULT_CATEGORY_COLORS = [
    "#1F77B4",
    "#FF7F0E",
    "#2CA02C",
    "#D62728",
    "#9467BD",
    "#8C564B",
    "#E377C2",
    "#7F7F7F",
    "#BCBD22",
    "#17BECF",
]

DATA_LABEL_FONT_SIZE = 12


# ============================================================
# COMMON HELPERS
# ============================================================

def _clean_text(df, column):

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return pd.Series(dtype="object")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _valid_text(series):

    values = (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return values[
        values.ne("")
        & values.ne("nan")
        & values.ne("NaT")
        & values.ne("None")
    ]


def _alphabetical_order(values):

    clean_values = []

    for value in values:

        text = str(value).strip()

        if (
            text
            and text not in {
                "nan",
                "NaT",
                "None",
            }
        ):
            clean_values.append(text)

    return sorted(
        list(dict.fromkeys(clean_values)),
        key=lambda value: value.upper(),
    )


# ============================================================
# STANDARDIZE GENDER
# ============================================================

def _standardize_gender(series):

    values = (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )

    replacement_map = {
        "male": "Male",
        "MALE": "Male",
        "m": "Male",
        "M": "Male",

        "female": "Female",
        "FEMALE": "Female",
        "f": "Female",
        "F": "Female",

        "transgender": "Transgender",
        "TRANSGENDER": "Transgender",
        "Trans Gender": "Transgender",
        "trans gender": "Transgender",
        "TG": "Transgender",
        "tg": "Transgender",

        "others": "Other",
        "Others": "Other",
        "OTHER": "Other",
        "other": "Other",
    }

    return values.replace(
        replacement_map
    )


# ============================================================
# STANDARDIZE AGE GROUP
# ============================================================

def _standardize_age_group(series):

    values = (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )

    replacement_map = {
        "Below 1 year": "<1",
        "Below 1 Year": "<1",
        "below 1 year": "<1",
        "below 1 Year": "<1",
        "0": "<1",
        "0 year": "<1",
        "0 years": "<1",
        "< 1": "<1",
        "<1 year": "<1",
        "< 1 year": "<1",
        "< 1 Year": "<1",
    }

    return values.replace(
        replacement_map
    )


# ============================================================
# LEGEND
# ============================================================

def _bottom_legend(title=None):

    return alt.Legend(
        title=title,
        orient="bottom",
        direction="horizontal",
        columns=10,
        labelFontSize=10,
        titleFontSize=10,
        symbolSize=80,
        symbolStrokeWidth=2,
        labelLimit=160,
        offset=8,
    )


# ============================================================
# AXIS
# ============================================================

def _x_axis(
    title=None,
    vertical=False,
):

    if vertical:

        return alt.Axis(
            title=title,
            labelAngle=-90,
            labelAlign="right",
            labelBaseline="middle",
            labelFontSize=10,
            titleFontSize=12,
            labelLimit=220,
        )

    return alt.Axis(
        title=title,
        labelAngle=-45,
        labelAlign="right",
        labelBaseline="middle",
        labelFontSize=10,
        titleFontSize=12,
        labelLimit=180,
    )


def _y_axis(title=None):

    return alt.Axis(
        title=title,
        labelFontSize=11,
        titleFontSize=12,
    )


# ============================================================
# CATEGORY BAR CHART
# ============================================================

def _render_category_bar_chart(
    dataframe,
    category_column,
    value_column="Records",
    category_order=None,
    height=430,
    vertical_labels=False,
):

    if dataframe is None or dataframe.empty:
        return

    chart_df = dataframe.copy()

    chart_df[category_column] = (
        chart_df[category_column]
        .astype(str)
    )

    if category_order is None:

        category_order = (
            chart_df[category_column]
            .drop_duplicates()
            .tolist()
        )

    colors = [
        DEFAULT_CATEGORY_COLORS[
            index % len(DEFAULT_CATEGORY_COLORS)
        ]
        for index in range(
            len(category_order)
        )
    ]

    color_scale = alt.Scale(
        domain=category_order,
        range=colors,
    )

    bars = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{category_column}:N",
                sort=category_order,
                axis=_x_axis(
                    category_column,
                    vertical=vertical_labels,
                ),
            ),
            y=alt.Y(
                f"{value_column}:Q",
                axis=_y_axis(
                    value_column
                ),
            ),
            color=alt.Color(
                f"{category_column}:N",
                scale=color_scale,
                legend=_bottom_legend(
                    category_column
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{category_column}:N",
                    title=category_column,
                ),
                alt.Tooltip(
                    f"{value_column}:Q",
                    title=value_column,
                    format=",",
                ),
            ],
        )
        .properties(
            height=height
        )
    )

    chart = bars

    if data_labels_enabled():

        labels = (
            alt.Chart(chart_df)
            .mark_text(
                dy=-8,
                fontSize=DATA_LABEL_FONT_SIZE,
                fontWeight="bold",
            )
            .encode(
                x=alt.X(
                    f"{category_column}:N",
                    sort=category_order,
                ),
                y=alt.Y(
                    f"{value_column}:Q"
                ),
                text=alt.Text(
                    f"{value_column}:Q",
                    format=",",
                ),
                color=alt.Color(
                    f"{category_column}:N",
                    scale=color_scale,
                    legend=None,
                ),
            )
        )

        chart = (
            bars
            + labels
        )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# GROUPED BAR CHART
# ============================================================

def _render_grouped_bar_chart(
    dataframe,
    x_column,
    group_column,
    value_column="Records",
    x_order=None,
    group_order=None,
    height=470,
):

    if dataframe is None or dataframe.empty:
        return

    chart_df = dataframe.copy()

    chart_df[x_column] = (
        chart_df[x_column]
        .astype(str)
    )

    chart_df[group_column] = (
        chart_df[group_column]
        .astype(str)
    )

    if x_order is None:

        x_order = (
            chart_df[x_column]
            .drop_duplicates()
            .tolist()
        )

    if group_order is None:

        group_order = (
            chart_df[group_column]
            .drop_duplicates()
            .tolist()
        )

    colors = []

    for index, group in enumerate(
        group_order
    ):

        if group in GENDER_COLORS:

            colors.append(
                GENDER_COLORS[group]
            )

        else:

            colors.append(
                DEFAULT_CATEGORY_COLORS[
                    index
                    % len(
                        DEFAULT_CATEGORY_COLORS
                    )
                ]
            )

    color_scale = alt.Scale(
        domain=group_order,
        range=colors,
    )

    bars = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{x_column}:N",
                sort=x_order,
                axis=_x_axis(
                    x_column
                ),
            ),
            xOffset=alt.XOffset(
                f"{group_column}:N",
                sort=group_order,
            ),
            y=alt.Y(
                f"{value_column}:Q",
                axis=_y_axis(
                    value_column
                ),
            ),
            color=alt.Color(
                f"{group_column}:N",
                sort=group_order,
                scale=color_scale,
                legend=_bottom_legend(
                    group_column
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{x_column}:N",
                    title=x_column,
                ),
                alt.Tooltip(
                    f"{group_column}:N",
                    title=group_column,
                ),
                alt.Tooltip(
                    f"{value_column}:Q",
                    title=value_column,
                    format=",",
                ),
            ],
        )
        .properties(
            height=height
        )
    )

    chart = bars

    if data_labels_enabled():

        labels = (
            alt.Chart(chart_df)
            .mark_text(
                dy=-7,
                fontSize=11,
                fontWeight="bold",
            )
            .encode(
                x=alt.X(
                    f"{x_column}:N",
                    sort=x_order,
                ),
                xOffset=alt.XOffset(
                    f"{group_column}:N",
                    sort=group_order,
                ),
                y=alt.Y(
                    f"{value_column}:Q"
                ),
                text=alt.Text(
                    f"{value_column}:Q",
                    format=",",
                ),
                color=alt.Color(
                    f"{group_column}:N",
                    scale=color_scale,
                    legend=None,
                ),
            )
        )

        chart = (
            bars
            + labels
        )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# MAIN WARD PAGE
# ============================================================

def render_ward(df):

    st.subheader(
        "📍 Ward Analysis"
    )

    if df is None or df.empty:

        st.warning(
            "No records available for the selected filters."
        )

        return

    st.caption(
        "Ward-wise burden, disease distribution, facility distribution "
        "and demographic analysis based on the selected Global Dashboard Filters."
    )

    # ========================================================
    # VALIDATE WARD COLUMN
    # ========================================================

    if "Ward Name" not in df.columns:

        st.warning(
            "Ward information is not available in the dataset."
        )

        return

    ward = _valid_text(
        df["Ward Name"]
    )

    if ward.empty:

        st.warning(
            "No valid ward records are available."
        )

        return

    # ========================================================
    # COMMON WARD ORDER
    # ========================================================

    all_wards = _alphabetical_order(
        ward.unique().tolist()
    )

    ward_counts = (
        ward
        .value_counts()
        .rename_axis("Ward")
        .reset_index(
            name="Records"
        )
    )

    total_valid_ward_records = int(
        ward_counts["Records"].sum()
    )

    ward_counts["Percentage"] = (
        ward_counts["Records"]
        / max(
            total_valid_ward_records,
            1,
        )
        * 100
    ).round(2)

    ward_counts.insert(
        0,
        "Rank",
        range(
            1,
            len(ward_counts) + 1,
        ),
    )

    # ========================================================
    # 1. WARD SUMMARY
    # ========================================================

    st.markdown(
        "### 1. 📊 Ward Summary"
    )

    top_ward = (
        ward_counts.iloc[0]
    )

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:

        st.metric(
            "Top Ward",
            str(
                top_ward["Ward"]
            ),
        )

    with c2:

        st.metric(
            "Records",
            f"{int(top_ward['Records']):,}",
        )

    with c3:

        st.metric(
            "Share",
            f"{float(top_ward['Percentage']):.2f}%",
        )

    with c4:

        st.metric(
            "Total Wards",
            f"{len(ward_counts):,}",
        )

    # ========================================================
    # 2. TOP BURDEN WARD
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. 🏆 Top Burden Ward"
    )

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:

        st.metric(
            "Top Ward",
            str(
                top_ward["Ward"]
            ),
        )

    with c2:

        st.metric(
            "Records",
            f"{int(top_ward['Records']):,}",
        )

    with c3:

        st.metric(
            "Share",
            f"{float(top_ward['Percentage']):.2f}%",
        )

    with c4:

        st.metric(
            "Total Wards",
            f"{len(ward_counts):,}",
        )

    # ========================================================
    # 3. WARD-WISE BURDEN RANKING
    # ========================================================

    st.divider()

    st.markdown(
        "### 3. 📋 Ward-wise Burden Ranking"
    )

    display_wards = (
        ward_counts.copy()
    )

    display_wards[
        "Percentage"
    ] = (
        display_wards[
            "Percentage"
        ]
        .map(
            lambda value: (
                f"{value:.2f}%"
            )
        )
    )

    st.dataframe(
        display_wards,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # 4. WARD-WISE RECORD DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 4. 📊 Ward-wise Record Distribution"
    )

    chart_wards = (
        ward_counts[
            [
                "Ward",
                "Records",
            ]
        ]
        .copy()
    )

    chart_wards = (
        chart_wards
        .set_index("Ward")
        .reindex(
            all_wards
        )
        .fillna(0)
        .reset_index()
    )

    _render_category_bar_chart(
        dataframe=chart_wards,
        category_column="Ward",
        value_column="Records",
        category_order=all_wards,
        height=450,
    )

    st.caption(
        "All wards available within the selected Global Dashboard "
        "Filters are displayed alphabetically from A to Z."
    )

    # ========================================================
    # 5. TOP 10 BURDEN WARDS
    # ========================================================

    st.divider()

    st.markdown(
        "### 5. 🔝 Top 10 Burden Wards"
    )

    top10 = (
        ward_counts
        .head(10)
        .copy()
    )

    top10_display = (
        top10[
            [
                "Rank",
                "Ward",
                "Records",
                "Percentage",
            ]
        ]
        .copy()
    )

    top10_display[
        "Percentage"
    ] = (
        top10_display[
            "Percentage"
        ]
        .map(
            lambda value: (
                f"{value:.2f}%"
            )
        )
    )

    st.dataframe(
        top10_display,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # 6. DISEASE × WARD
    # ========================================================

    st.divider()

    st.markdown(
        "### 6. 🦠 Disease-wise Ward Burden"
    )

    if "Disease" in df.columns:

        disease_ward = df[
            [
                "Ward Name",
                "Disease",
            ]
        ].copy()

        disease_ward[
            "Ward Name"
        ] = (
            disease_ward[
                "Ward Name"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_ward[
            "Disease"
        ] = (
            disease_ward[
                "Disease"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_ward = (
            disease_ward[
                disease_ward[
                    "Ward Name"
                ].ne("")
                & disease_ward[
                    "Disease"
                ].ne("")
                & disease_ward[
                    "Ward Name"
                ].ne("nan")
                & disease_ward[
                    "Disease"
                ].ne("nan")
            ]
        )

        if not disease_ward.empty:

            top_diseases = (
                disease_ward[
                    "Disease"
                ]
                .value_counts()
                .head(10)
                .index
                .tolist()
            )

            disease_chart_source = (
                disease_ward[
                    disease_ward[
                        "Disease"
                    ].isin(
                        top_diseases
                    )
                ]
                .copy()
            )

            chart_long = (
                disease_chart_source
                .groupby(
                    [
                        "Ward Name",
                        "Disease",
                    ],
                    observed=True,
                )
                .size()
                .reset_index(
                    name="Records"
                )
            )

            complete_index = (
                pd.MultiIndex
                .from_product(
                    [
                        all_wards,
                        top_diseases,
                    ],
                    names=[
                        "Ward Name",
                        "Disease",
                    ],
                )
            )

            chart_long = (
                chart_long
                .set_index(
                    [
                        "Ward Name",
                        "Disease",
                    ]
                )
                .reindex(
                    complete_index,
                    fill_value=0,
                )
                .reset_index()
            )

            _render_grouped_bar_chart(
                dataframe=chart_long,
                x_column="Ward Name",
                group_column="Disease",
                value_column="Records",
                x_order=all_wards,
                group_order=top_diseases,
                height=500,
            )

            disease_ward_table = (
                pd.crosstab(
                    disease_ward[
                        "Ward Name"
                    ],
                    disease_ward[
                        "Disease"
                    ],
                )
            )

            disease_ward_table = (
                disease_ward_table
                .reindex(
                    index=all_wards,
                    columns=top_diseases,
                    fill_value=0,
                )
            )

            st.caption(
                "Chart displays the top 10 diseases across all "
                "available wards. Wards are arranged alphabetically "
                "from A to Z."
            )

            st.dataframe(
                disease_ward_table
                .reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Disease and Ward information is not available."
            )

    else:

        st.info(
            "Disease column is not available."
        )

    # ========================================================
    # 7. FACILITY × WARD
    # ========================================================

    st.divider()

    st.markdown(
        "### 7. 🏥 Facility-wise Ward Distribution"
    )

    if "Facility Name" in df.columns:

        facility_ward = df[
            [
                "Ward Name",
                "Facility Name",
            ]
        ].copy()

        facility_ward[
            "Ward Name"
        ] = (
            facility_ward[
                "Ward Name"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_ward[
            "Facility Name"
        ] = (
            facility_ward[
                "Facility Name"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_ward = (
            facility_ward[
                facility_ward[
                    "Ward Name"
                ].ne("")
                & facility_ward[
                    "Facility Name"
                ].ne("")
                & facility_ward[
                    "Ward Name"
                ].ne("nan")
                & facility_ward[
                    "Facility Name"
                ].ne("nan")
            ]
        )

        if not facility_ward.empty:

            top_facilities = (
                facility_ward[
                    "Facility Name"
                ]
                .value_counts()
                .head(10)
                .index
                .tolist()
            )

            facility_chart_source = (
                facility_ward[
                    facility_ward[
                        "Facility Name"
                    ].isin(
                        top_facilities
                    )
                ]
                .copy()
            )

            chart_long = (
                facility_chart_source
                .groupby(
                    [
                        "Ward Name",
                        "Facility Name",
                    ],
                    observed=True,
                )
                .size()
                .reset_index(
                    name="Records"
                )
            )

            complete_index = (
                pd.MultiIndex
                .from_product(
                    [
                        all_wards,
                        top_facilities,
                    ],
                    names=[
                        "Ward Name",
                        "Facility Name",
                    ],
                )
            )

            chart_long = (
                chart_long
                .set_index(
                    [
                        "Ward Name",
                        "Facility Name",
                    ]
                )
                .reindex(
                    complete_index,
                    fill_value=0,
                )
                .reset_index()
            )

            _render_grouped_bar_chart(
                dataframe=chart_long,
                x_column="Ward Name",
                group_column="Facility Name",
                value_column="Records",
                x_order=all_wards,
                group_order=top_facilities,
                height=500,
            )

            facility_ward_table = (
                pd.crosstab(
                    facility_ward[
                        "Ward Name"
                    ],
                    facility_ward[
                        "Facility Name"
                    ],
                )
            )

            facility_ward_table = (
                facility_ward_table
                .reindex(
                    index=all_wards,
                    columns=top_facilities,
                    fill_value=0,
                )
            )

            st.caption(
                "Chart displays the top 10 facilities across all "
                "available wards. Wards are arranged alphabetically "
                "from A to Z."
            )

            st.dataframe(
                facility_ward_table
                .reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Facility and Ward information is not available."
            )

    else:

        st.info(
            "Facility Name column is not available."
        )

    # ========================================================
    # 8. WARD × GENDER
    # ========================================================

    st.divider()

    st.markdown(
        "### 8. 👥 Ward-wise Gender Distribution"
    )

    if "Gender" in df.columns:

        ward_gender = df[
            [
                "Ward Name",
                "Gender",
            ]
        ].copy()

        ward_gender[
            "Ward Name"
        ] = (
            ward_gender[
                "Ward Name"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_gender[
            "Gender"
        ] = (
            _standardize_gender(
                ward_gender[
                    "Gender"
                ]
            )
        )

        ward_gender = (
            ward_gender[
                ward_gender[
                    "Ward Name"
                ].ne("")
                & ward_gender[
                    "Gender"
                ].ne("")
                & ward_gender[
                    "Ward Name"
                ].ne("nan")
                & ward_gender[
                    "Gender"
                ].ne("nan")
                & ward_gender[
                    "Ward Name"
                ].ne("NaT")
                & ward_gender[
                    "Gender"
                ].ne("NaT")
            ]
        )

        if not ward_gender.empty:

            present_genders = (
                ward_gender[
                    "Gender"
                ]
                .drop_duplicates()
                .tolist()
            )

            gender_order = [
                value
                for value in GENDER_ORDER
                if value
                in present_genders
            ]

            gender_order += sorted(
                [
                    value
                    for value
                    in present_genders
                    if value
                    not in GENDER_ORDER
                ]
            )

            chart_long = (
                ward_gender
                .groupby(
                    [
                        "Ward Name",
                        "Gender",
                    ],
                    observed=True,
                )
                .size()
                .reset_index(
                    name="Records"
                )
            )

            complete_index = (
                pd.MultiIndex
                .from_product(
                    [
                        all_wards,
                        gender_order,
                    ],
                    names=[
                        "Ward Name",
                        "Gender",
                    ],
                )
            )

            chart_long = (
                chart_long
                .set_index(
                    [
                        "Ward Name",
                        "Gender",
                    ]
                )
                .reindex(
                    complete_index,
                    fill_value=0,
                )
                .reset_index()
            )

            _render_grouped_bar_chart(
                dataframe=chart_long,
                x_column="Ward Name",
                group_column="Gender",
                value_column="Records",
                x_order=all_wards,
                group_order=gender_order,
                height=500,
            )

            gender_table = (
                pd.crosstab(
                    ward_gender[
                        "Ward Name"
                    ],
                    ward_gender[
                        "Gender"
                    ],
                )
            )

            gender_table = (
                gender_table
                .reindex(
                    index=all_wards,
                    columns=gender_order,
                    fill_value=0,
                )
            )

            st.caption(
                "All wards available within the selected Global "
                "Dashboard Filters are displayed alphabetically "
                "from A to Z."
            )

            st.dataframe(
                gender_table
                .reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Ward and Gender information is not available."
            )

    else:

        st.info(
            "Gender column is not available."
        )


    # ========================================================
    # 9. WARD × AGE GROUP
    # ========================================================

    st.divider()

    st.markdown(
        "### 9. 🎂 Ward-wise Age Group Distribution"
    )

    if "Age Group" in df.columns:

        ward_age = df[
            [
                "Ward Name",
                "Age Group",
            ]
        ].copy()

        ward_age[
            "Ward Name"
        ] = (
            ward_age[
                "Ward Name"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_age[
            "Age Group"
        ] = (
            _standardize_age_group(
                ward_age[
                    "Age Group"
                ]
            )
        )

        ward_age = (
            ward_age[
                ward_age[
                    "Ward Name"
                ].ne("")
                & ward_age[
                    "Age Group"
                ].ne("")
                & ward_age[
                    "Ward Name"
                ].ne("nan")
                & ward_age[
                    "Age Group"
                ].ne("nan")
                & ward_age[
                    "Ward Name"
                ].ne("NaT")
                & ward_age[
                    "Age Group"
                ].ne("NaT")
            ]
        )

        if not ward_age.empty:

            # ------------------------------------------------
            # AGE GROUP ORDER
            # ------------------------------------------------

            present_age_groups = (
                ward_age[
                    "Age Group"
                ]
                .drop_duplicates()
                .tolist()
            )

            age_group_order = [
                value
                for value
                in AGE_GROUP_ORDER
                if value
                in present_age_groups
            ]

            age_group_order += sorted(
                [
                    value
                    for value
                    in present_age_groups
                    if value
                    not in AGE_GROUP_ORDER
                ]
            )

            

            # ------------------------------------------------
            # MULTIPLE AGE GROUP SELECTION
            # Default = all available age groups
            # ------------------------------------------------

            selected_age_groups = st.multiselect(
                "Select Age Group(s)",
                options=age_group_order,
                default=age_group_order,
                key="phase5_ward_age_group_multiselect",
            )

            

            # ------------------------------------------------
            # NO AGE GROUP SELECTED
            # ------------------------------------------------

            if not selected_age_groups:

                st.info(
                    "Please select at least one Age Group "
                    "to display the ward-wise distribution."
                )

            else:

                # --------------------------------------------
                # Preserve standard age-group order even when
                # multiple groups are selected.
                # --------------------------------------------

                selected_age_groups = [
                    value
                    for value
                    in age_group_order
                    if value
                    in selected_age_groups
                ]

                # --------------------------------------------
                # FILTER SELECTED AGE GROUPS
                # --------------------------------------------

                chart_source = (
                    ward_age[
                        ward_age[
                            "Age Group"
                        ].isin(
                            selected_age_groups
                        )
                    ]
                    .copy()
                )

                # --------------------------------------------
                # GROUP DATA
                # --------------------------------------------

                chart_long = (
                    chart_source
                    .groupby(
                        [
                            "Ward Name",
                            "Age Group",
                        ],
                        observed=True,
                    )
                    .size()
                    .reset_index(
                        name="Records"
                    )
                )

                # --------------------------------------------
                # RETAIN ALL WARDS
                #
                # Even if a ward has zero records for one of
                # the selected age groups, that ward remains
                # visible in the chart/table.
                # --------------------------------------------

                complete_index = (
                    pd.MultiIndex
                    .from_product(
                        [
                            all_wards,
                            selected_age_groups,
                        ],
                        names=[
                            "Ward Name",
                            "Age Group",
                        ],
                    )
                )

                chart_long = (
                    chart_long
                    .set_index(
                        [
                            "Ward Name",
                            "Age Group",
                        ]
                    )
                    .reindex(
                        complete_index,
                        fill_value=0,
                    )
                    .reset_index()
                )

                # --------------------------------------------
                # CHART
                # --------------------------------------------

                _render_grouped_bar_chart(
                    dataframe=chart_long,
                    x_column="Ward Name",
                    group_column="Age Group",
                    value_column="Records",
                    x_order=all_wards,
                    group_order=selected_age_groups,
                    height=520,
                )

                # --------------------------------------------
                # TABLE
                # --------------------------------------------

                age_table = (
                    pd.crosstab(
                        chart_source[
                            "Ward Name"
                        ],
                        chart_source[
                            "Age Group"
                        ],
                    )
                )

                age_table = (
                    age_table
                    .reindex(
                        index=all_wards,
                        columns=selected_age_groups,
                        fill_value=0,
                    )
                )

                # --------------------------------------------
                # CAPTION
                # --------------------------------------------

                if (
                    len(selected_age_groups)
                    == len(age_group_order)
                ):

                    st.caption(
                        "All available age groups are selected. "
                        "All wards are displayed alphabetically "
                        "from A to Z."
                    )

                elif len(selected_age_groups) == 1:

                    st.caption(
                        f"Selected Age Group: "
                        f"{selected_age_groups[0]}. "
                        "All wards are displayed alphabetically "
                        "from A to Z, including wards with zero "
                        "records for the selected age group."
                    )

                else:

                    selected_text = ", ".join(
                        selected_age_groups
                    )

                    st.caption(
                        f"Selected Age Groups: {selected_text}. "
                        "All wards are displayed alphabetically "
                        "from A to Z, including wards with zero "
                        "records for the selected age groups."
                    )

                # --------------------------------------------
                # DISPLAY TABLE
                # --------------------------------------------

                st.dataframe(
                    age_table
                    .reset_index(),
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.info(
                "Ward and Age Group information is not available."
            )

    else:

        st.info(
            "Age Group column is not available."
        )



    
    # ========================================================
    # 10. WARD – FACILITY DETAIL
    # ========================================================

    st.divider()

    st.markdown(
        "### 10. 🏥 Ward – Facility Detail"
    )

    if "Facility Name" in df.columns:

        # ----------------------------------------------------
        # Ward selector
        #
        # If the Global Dashboard Ward filter has already
        # reduced the data to one ward, only that ward appears.
        # Otherwise all currently available wards can be chosen.
        # ----------------------------------------------------

        available_detail_wards = (
            _alphabetical_order(
                df[
                    "Ward Name"
                ]
                .fillna("")
                .astype(str)
                .str.strip()
                .loc[
                    lambda values:
                    values.ne("")
                    & values.ne("nan")
                    & values.ne("NaT")
                ]
                .unique()
                .tolist()
            )
        )

        if available_detail_wards:

            if len(
                available_detail_wards
            ) == 1:

                selected_ward = (
                    available_detail_wards[0]
                )

                st.selectbox(
                    "Select Ward",
                    options=[
                        selected_ward
                    ],
                    index=0,
                    key=(
                        "phase5_facility_"
                        "ward_single"
                    ),
                    disabled=True,
                )

            else:

                default_ward = str(
                    top_ward["Ward"]
                )

                try:

                    default_index = (
                        available_detail_wards
                        .index(
                            default_ward
                        )
                    )

                except ValueError:

                    default_index = 0

                selected_ward = (
                    st.selectbox(
                        "Select Ward",
                        options=(
                            available_detail_wards
                        ),
                        index=default_index,
                        key=(
                            "phase5_facility_"
                            "ward_selector"
                        ),
                    )
                )

            ward_facility_df = (
                df[
                    df[
                        "Ward Name"
                    ]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .eq(
                        selected_ward
                    )
                ]
                .copy()
            )

            if not ward_facility_df.empty:

                facility_values = (
                    ward_facility_df[
                        "Facility Name"
                    ]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )

                facility_values = (
                    facility_values[
                        facility_values.ne("")
                        & facility_values.ne(
                            "nan"
                        )
                        & facility_values.ne(
                            "NaT"
                        )
                    ]
                )

                if not facility_values.empty:

                    facility_counts = (
                        facility_values
                        .value_counts()
                        .rename_axis(
                            "Facility"
                        )
                        .reset_index(
                            name="Records"
                        )
                    )

                    facility_counts.insert(
                        0,
                        "Rank",
                        range(
                            1,
                            len(
                                facility_counts
                            ) + 1,
                        ),
                    )

                    st.caption(
                        f"Facility distribution for Ward "
                        f"{selected_ward}."
                    )

                    # ----------------------------------------
                    # Facility chart
                    # X-axis labels intentionally vertical.
                    # ----------------------------------------

                    _render_category_bar_chart(
                        dataframe=(
                            facility_counts[
                                [
                                    "Facility",
                                    "Records",
                                ]
                            ]
                        ),
                        category_column=(
                            "Facility"
                        ),
                        value_column=(
                            "Records"
                        ),
                        category_order=(
                            facility_counts[
                                "Facility"
                            ]
                            .tolist()
                        ),
                        height=500,
                        vertical_labels=True,
                    )

                    st.dataframe(
                        facility_counts,
                        use_container_width=True,
                        hide_index=True,
                    )

                else:

                    st.info(
                        "Facility information is not available "
                        "for the selected ward."
                    )

            else:

                st.info(
                    "No records found for the selected ward."
                )

        else:

            st.info(
                "No valid wards are available for "
                "facility analysis."
            )

    else:

        st.info(
            "Facility Name column is not available."
        )

    # ========================================================
    # 11. WARD DATA QUALITY
    # ========================================================

    st.divider()

    st.markdown(
        "### 11. ℹ️ Ward Data Quality"
    )

    total_records = len(
        df
    )

    raw_ward_values = (
        df[
            "Ward Name"
        ]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    valid_ward_mask = (
        raw_ward_values.ne("")
        & raw_ward_values.ne("nan")
        & raw_ward_values.ne("NaT")
        & raw_ward_values.ne("None")
    )

    valid_ward_count = int(
        valid_ward_mask.sum()
    )

    missing_ward = (
        total_records
        - valid_ward_count
    )

    ward_quality = pd.DataFrame(
        {
            "Indicator": [
                "Total Records",
                "Records with Valid Ward",
                "Records with Missing / Blank Ward",
                "Unique Wards",
            ],
            "Count": [
                total_records,
                valid_ward_count,
                missing_ward,
                len(all_wards),
            ],
        }
    )

    ward_quality[
        "Percentage"
    ] = (
        ward_quality[
            "Count"
        ]
        / max(
            total_records,
            1,
        )
        * 100
    ).round(2)

    quality_display = (
        ward_quality.copy()
    )

    quality_display[
        "Percentage"
    ] = (
        quality_display[
            "Percentage"
        ]
        .map(
            lambda value: (
                f"{value:.2f}%"
            )
        )
    )

    st.dataframe(
        quality_display,
        use_container_width=True,
        hide_index=True,
    )
