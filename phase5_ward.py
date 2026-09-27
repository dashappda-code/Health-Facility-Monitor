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

DATA_LABEL_FONT_SIZE = 13
GROUPED_DATA_LABEL_FONT_SIZE = 11


# ============================================================
# COMMON CHART CONFIGURATION
# ============================================================

def _bottom_legend(title=None):

    return alt.Legend(
        title=title,
        orient="bottom",
        direction="horizontal",
        columns=10,
        labelFontSize=9,
        titleFontSize=10,
        symbolSize=70,
        symbolStrokeWidth=2,
        labelLimit=180,
        offset=8,
    )


def _x_axis(title=None):

    return alt.Axis(
        title=title,
        labelAngle=-45,
        labelAlign="right",
        labelBaseline="middle",
        labelFontSize=10,
        titleFontSize=12,
        labelLimit=220,
    )


def _y_axis(title=None):

    return alt.Axis(
        title=title,
        labelFontSize=10,
        titleFontSize=12,
    )


# ============================================================
# TEXT HELPERS
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

    return series[
        series.ne("")
        & series.ne("nan")
        & series.ne("NaT")
        & series.ne("None")
    ]


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
# COLOR HELPERS
# ============================================================

def _build_color_scale(categories):

    categories = list(categories)

    colors = [
        DEFAULT_CATEGORY_COLORS[
            index % len(DEFAULT_CATEGORY_COLORS)
        ]
        for index in range(len(categories))
    ]

    return alt.Scale(
        domain=categories,
        range=colors,
    )


def _build_group_color_scale(groups):

    groups = list(groups)

    colors = []

    for index, group in enumerate(groups):

        if group in GENDER_COLORS:

            colors.append(
                GENDER_COLORS[group]
            )

        else:

            colors.append(
                DEFAULT_CATEGORY_COLORS[
                    index
                    % len(DEFAULT_CATEGORY_COLORS)
                ]
            )

    return alt.Scale(
        domain=groups,
        range=colors,
    )


# ============================================================
# SINGLE CATEGORY BAR CHART
# ============================================================

def _render_category_bar_chart(
    dataframe,
    category_column,
    value_column="Records",
    category_order=None,
    height=430,
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

    else:

        present = (
            chart_df[category_column]
            .drop_duplicates()
            .tolist()
        )

        category_order = [
            value
            for value in category_order
            if value in present
        ] + [
            value
            for value in present
            if value not in category_order
        ]

    color_scale = _build_color_scale(
        category_order
    )

    bars = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{category_column}:N",
                sort=category_order,
                axis=_x_axis(
                    category_column
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
                dy=-9,
                fontWeight="bold",
                fontSize=DATA_LABEL_FONT_SIZE,
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
    height=480,
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

    present_x = (
        chart_df[x_column]
        .drop_duplicates()
        .tolist()
    )

    if x_order is None:

        x_order = present_x

    else:

        x_order = [
            value
            for value in x_order
            if value in present_x
        ] + [
            value
            for value in present_x
            if value not in x_order
        ]

    present_groups = (
        chart_df[group_column]
        .drop_duplicates()
        .tolist()
    )

    if group_order is None:

        groups = present_groups

    else:

        groups = [
            value
            for value in group_order
            if value in present_groups
        ] + [
            value
            for value in present_groups
            if value not in group_order
        ]

    color_scale = _build_group_color_scale(
        groups
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
                sort=groups,
            ),
            y=alt.Y(
                f"{value_column}:Q",
                axis=_y_axis(
                    value_column
                ),
            ),
            color=alt.Color(
                f"{group_column}:N",
                scale=color_scale,
                sort=groups,
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
                dy=-8,
                fontWeight="bold",
                fontSize=GROUPED_DATA_LABEL_FONT_SIZE,
            )
            .encode(
                x=alt.X(
                    f"{x_column}:N",
                    sort=x_order,
                ),
                xOffset=alt.XOffset(
                    f"{group_column}:N",
                    sort=groups,
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
    # 1. WARD SUMMARY
    # ========================================================

    st.markdown(
        "### 1. 📊 Ward Summary"
    )

    if "Ward Name" not in df.columns:

        st.warning(
            "Ward information is not available in the dataset."
        )

        return

    ward = _clean_text(
        df,
        "Ward Name",
    )

    ward = _valid_text(
        ward
    )

    if ward.empty:

        st.warning(
            "No valid ward records are available."
        )

        return

    ward_counts = (
        ward
        .value_counts()
        .rename_axis(
            "Ward"
        )
        .reset_index(
            name="Records"
        )
    )

    total_valid_ward_records = int(
        ward_counts["Records"].sum()
    )

    ward_counts["Percentage"] = (
        ward_counts["Records"]
        / total_valid_ward_records
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

    summary1, summary2, summary3 = (
        st.columns(3)
    )

    with summary1:

        st.metric(
            "Valid Ward Records",
            f"{total_valid_ward_records:,}",
        )

    with summary2:

        st.metric(
            "Unique Wards",
            f"{len(ward_counts):,}",
        )

    with summary3:

        st.metric(
            "Ward Coverage",
            (
                f"{(
                    total_valid_ward_records
                    / max(len(df), 1)
                    * 100
                ):.2f}%"
            ),
        )

    # ========================================================
    # 2. TOP BURDEN WARD
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. 🏆 Top Burden Ward"
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
    # 3. WARD-WISE RANKING
    # ========================================================

    st.divider()

    st.markdown(
        "### 3. 📋 Ward-wise Burden Ranking"
    )

    display_wards = (
        ward_counts.copy()
    )

    display_wards["Percentage"] = (
        display_wards["Percentage"]
        .map(
            lambda x: f"{x:.2f}%"
        )
    )

    st.dataframe(
        display_wards,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # 4. WARD-WISE BAR CHART
    # ========================================================

    st.divider()

    st.markdown(
        "### 4. 📊 Ward-wise Record Distribution"
    )

    chart_wards = (
        ward_counts
        .head(25)
        .copy()
    )

    _render_category_bar_chart(
        dataframe=chart_wards,
        category_column="Ward",
        value_column="Records",
        category_order=(
            chart_wards["Ward"]
            .tolist()
        ),
        height=450,
    )

    if len(ward_counts) > 25:

        st.caption(
            "Chart displays the top 25 wards by record volume. "
            "The Ward-wise Burden Ranking table contains all available wards."
        )

    # ========================================================
    # 5. TOP 10 WARDS
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

    top10_display["Percentage"] = (
        top10_display["Percentage"]
        .map(
            lambda x: f"{x:.2f}%"
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

        disease_ward["Ward Name"] = (
            disease_ward["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_ward["Disease"] = (
            disease_ward["Disease"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_ward = disease_ward[
            disease_ward["Ward Name"].ne("")
            & disease_ward["Disease"].ne("")
            & disease_ward["Ward Name"].ne("nan")
            & disease_ward["Disease"].ne("nan")
            & disease_ward["Ward Name"].ne("NaT")
            & disease_ward["Disease"].ne("NaT")
        ]

        if not disease_ward.empty:

            disease_totals = (
                disease_ward["Disease"]
                .value_counts()
                .head(10)
            )

            top_diseases = (
                disease_totals.index
                .tolist()
            )

            top_ward_order = (
                disease_ward["Ward Name"]
                .value_counts()
                .head(25)
                .index
                .tolist()
            )

            chart_source = (
                disease_ward[
                    disease_ward["Disease"]
                    .isin(top_diseases)
                    & disease_ward["Ward Name"]
                    .isin(top_ward_order)
                ]
            )

            chart_long = (
                chart_source
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

            _render_grouped_bar_chart(
                dataframe=chart_long,
                x_column="Ward Name",
                group_column="Disease",
                value_column="Records",
                x_order=top_ward_order,
                group_order=top_diseases,
                height=500,
            )

            disease_ward_table = (
                pd.crosstab(
                    chart_source["Ward Name"],
                    chart_source["Disease"],
                )
                .reindex(
                    index=top_ward_order,
                    columns=top_diseases,
                    fill_value=0,
                )
            )

            st.caption(
                "Chart displays the top 10 diseases across "
                "the top 25 wards by record volume."
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

        facility_ward["Ward Name"] = (
            facility_ward["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_ward["Facility Name"] = (
            facility_ward["Facility Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        facility_ward = facility_ward[
            facility_ward["Ward Name"].ne("")
            & facility_ward["Facility Name"].ne("")
            & facility_ward["Ward Name"].ne("nan")
            & facility_ward["Facility Name"].ne("nan")
            & facility_ward["Ward Name"].ne("NaT")
            & facility_ward["Facility Name"].ne("NaT")
        ]

        if not facility_ward.empty:

            top_facilities = (
                facility_ward["Facility Name"]
                .value_counts()
                .head(10)
                .index
                .tolist()
            )

            top_ward_order = (
                facility_ward["Ward Name"]
                .value_counts()
                .head(25)
                .index
                .tolist()
            )

            chart_source = (
                facility_ward[
                    facility_ward["Facility Name"]
                    .isin(top_facilities)
                    & facility_ward["Ward Name"]
                    .isin(top_ward_order)
                ]
            )

            chart_long = (
                chart_source
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

            _render_grouped_bar_chart(
                dataframe=chart_long,
                x_column="Ward Name",
                group_column="Facility Name",
                value_column="Records",
                x_order=top_ward_order,
                group_order=top_facilities,
                height=520,
            )

            facility_ward_table = (
                pd.crosstab(
                    chart_source["Ward Name"],
                    chart_source["Facility Name"],
                )
                .reindex(
                    index=top_ward_order,
                    columns=top_facilities,
                    fill_value=0,
                )
            )

            st.caption(
                "Chart displays the top 10 facilities across "
                "the top 25 wards by record volume."
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

        ward_gender["Ward Name"] = (
            ward_gender["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_gender["Gender"] = (
            _standardize_gender(
                ward_gender["Gender"]
            )
        )

        ward_gender = ward_gender[
            ward_gender["Ward Name"].ne("")
            & ward_gender["Gender"].ne("")
            & ward_gender["Ward Name"].ne("nan")
            & ward_gender["Gender"].ne("nan")
            & ward_gender["Ward Name"].ne("NaT")
            & ward_gender["Gender"].ne("NaT")
        ]

        if not ward_gender.empty:

            top_ward_order = (
                ward_gender["Ward Name"]
                .value_counts()
                .head(20)
                .index
                .tolist()
            )

            chart_source = (
                ward_gender[
                    ward_gender["Ward Name"]
                    .isin(top_ward_order)
                ]
            )

            chart_long = (
                chart_source
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

            _render_grouped_bar_chart(
                dataframe=chart_long,
                x_column="Ward Name",
                group_column="Gender",
                value_column="Records",
                x_order=top_ward_order,
                group_order=GENDER_ORDER,
                height=480,
            )

            gender_table = (
                pd.crosstab(
                    chart_source["Ward Name"],
                    chart_source["Gender"],
                )
                .reindex(
                    index=top_ward_order,
                    fill_value=0,
                )
            )

            gender_columns = [
                value
                for value in GENDER_ORDER
                if value in gender_table.columns
            ]

            gender_columns += [
                value
                for value in gender_table.columns
                if value not in GENDER_ORDER
            ]

            gender_table = (
                gender_table[
                    gender_columns
                ]
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

        ward_age["Ward Name"] = (
            ward_age["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_age["Age Group"] = (
            _standardize_age_group(
                ward_age["Age Group"]
            )
        )

        ward_age = ward_age[
            ward_age["Ward Name"].ne("")
            & ward_age["Age Group"].ne("")
            & ward_age["Ward Name"].ne("nan")
            & ward_age["Age Group"].ne("nan")
            & ward_age["Ward Name"].ne("NaT")
            & ward_age["Age Group"].ne("NaT")
        ]

        if not ward_age.empty:

            top_ward_order = (
                ward_age["Ward Name"]
                .value_counts()
                .head(20)
                .index
                .tolist()
            )

            chart_source = (
                ward_age[
                    ward_age["Ward Name"]
                    .isin(top_ward_order)
                ]
            )

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

            present_age_groups = (
                chart_long["Age Group"]
                .drop_duplicates()
                .tolist()
            )

            age_group_order = [
                value
                for value in AGE_GROUP_ORDER
                if value in present_age_groups
            ]

            age_group_order += sorted(
                [
                    value
                    for value in present_age_groups
                    if value not in AGE_GROUP_ORDER
                ]
            )

            _render_grouped_bar_chart(
                dataframe=chart_long,
                x_column="Ward Name",
                group_column="Age Group",
                value_column="Records",
                x_order=top_ward_order,
                group_order=age_group_order,
                height=500,
            )

            age_table = (
                pd.crosstab(
                    chart_source["Ward Name"],
                    chart_source["Age Group"],
                )
                .reindex(
                    index=top_ward_order,
                    fill_value=0,
                )
            )

            available_age_columns = [
                value
                for value in AGE_GROUP_ORDER
                if value in age_table.columns
            ]

            remaining_age_columns = [
                value
                for value in age_table.columns
                if value not in AGE_GROUP_ORDER
            ]

            age_table = (
                age_table[
                    available_age_columns
                    + sorted(
                        remaining_age_columns
                    )
                ]
            )

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
    # 10. TOP WARD × TOP FACILITY DETAIL
    # ========================================================

    st.divider()

    st.markdown(
        "### 10. 🏥 Top Ward – Facility Detail"
    )

    if "Facility Name" in df.columns:

        top_ward_name = str(
            top_ward["Ward"]
        )

        ward_name_series = (
            df["Ward Name"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        ward_facility_df = (
            df[
                ward_name_series
                .eq(top_ward_name)
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
                _valid_text(
                    facility_values
                )
            )

            if not facility_values.empty:

                top_facilities = (
                    facility_values
                    .value_counts()
                    .rename_axis(
                        "Facility"
                    )
                    .reset_index(
                        name="Records"
                    )
                )

                top_facilities.insert(
                    0,
                    "Rank",
                    range(
                        1,
                        len(top_facilities) + 1,
                    ),
                )

                top_facilities[
                    "Percentage"
                ] = (
                    top_facilities[
                        "Records"
                    ]
                    / top_facilities[
                        "Records"
                    ].sum()
                    * 100
                ).round(2)

                chart_facilities = (
                    top_facilities
                    .head(15)
                    .copy()
                )

                _render_category_bar_chart(
                    dataframe=chart_facilities,
                    category_column="Facility",
                    value_column="Records",
                    category_order=(
                        chart_facilities[
                            "Facility"
                        ]
                        .tolist()
                    ),
                    height=450,
                )

                display_top_facilities = (
                    top_facilities.copy()
                )

                display_top_facilities[
                    "Percentage"
                ] = (
                    display_top_facilities[
                        "Percentage"
                    ]
                    .map(
                        lambda x: (
                            f"{x:.2f}%"
                        )
                    )
                )

                st.dataframe(
                    display_top_facilities,
                    use_container_width=True,
                    hide_index=True,
                )

                if len(
                    top_facilities
                ) > 15:

                    st.caption(
                        "Chart displays the top 15 facilities "
                        f"within Ward {top_ward_name}. "
                        "The table contains all facilities."
                    )

            else:

                st.info(
                    "Facility information is not available "
                    "for the top burden ward."
                )

        else:

            st.info(
                "No records found for the top burden ward."
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

    total_records = len(df)

    valid_ward_records = len(
        ward
    )

    missing_ward = (
        total_records
        - valid_ward_records
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
                valid_ward_records,
                missing_ward,
                len(ward_counts),
            ],
        }
    )

    ward_quality["Percentage"] = [
        100.0,
        (
            valid_ward_records
            / max(total_records, 1)
            * 100
        ),
        (
            missing_ward
            / max(total_records, 1)
            * 100
        ),
        None,
    ]

    ward_quality_display = (
        ward_quality.copy()
    )

    ward_quality_display[
        "Percentage"
    ] = (
        ward_quality_display[
            "Percentage"
        ]
        .apply(
            lambda value: (
                f"{value:.2f}%"
                if pd.notna(value)
                else ""
            )
        )
    )

    st.dataframe(
        ward_quality_display,
        use_container_width=True,
        hide_index=True,
    )
