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

def _bottom_legend(
    title=None,
    columns=10,
):

    return alt.Legend(
        title=title,
        orient="bottom",
        direction="horizontal",
        columns=columns,
        labelFontSize=9,
        titleFontSize=10,
        symbolSize=65,
        symbolStrokeWidth=2,
        labelLimit=150,
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
            labelLimit=240,
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
    legend_columns=10,
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
                    category_column,
                    columns=legend_columns,
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
# CHECKBOX SELECTOR
# ============================================================

def _checkbox_selector(
    title,
    options,
    key_prefix,
):

    options = list(options)

    if not options:
        return []

    st.markdown(
        f"**{title}**"
    )

    select_all_key = (
        f"{key_prefix}_select_all"
    )

    previous_all_key = (
        f"{key_prefix}_previous_all"
    )

    initialized_key = (
        f"{key_prefix}_initialized"
    )

    option_keys = {
        option: (
            f"{key_prefix}_option_{index}"
        )
        for index, option
        in enumerate(options)
    }

    # --------------------------------------------------------
    # INITIAL STATE
    # Default = Select All ON
    # --------------------------------------------------------

    if initialized_key not in st.session_state:

        st.session_state[
            initialized_key
        ] = True

        st.session_state[
            select_all_key
        ] = True

        st.session_state[
            previous_all_key
        ] = True

        for option in options:

            st.session_state[
                option_keys[option]
            ] = True

    else:

        # Add newly appearing options safely.
        for option in options:

            option_key = (
                option_keys[option]
            )

            if (
                option_key
                not in st.session_state
            ):

                st.session_state[
                    option_key
                ] = bool(
                    st.session_state.get(
                        select_all_key,
                        True,
                    )
                )

    # --------------------------------------------------------
    # SELECT ALL TOGGLE
    # --------------------------------------------------------

    select_all = st.toggle(
        "Select All",
        key=select_all_key,
    )

    previous_all = (
        st.session_state.get(
            previous_all_key,
            True,
        )
    )

    # --------------------------------------------------------
    # If user manually changes Select All:
    #
    # ON  -> all options ON
    # OFF -> all options OFF
    # --------------------------------------------------------

    if select_all != previous_all:

        for option in options:

            st.session_state[
                option_keys[option]
            ] = select_all

        st.session_state[
            previous_all_key
        ] = select_all

    # --------------------------------------------------------
    # INDIVIDUAL CHECKBOXES
    # --------------------------------------------------------

    column_count = min(
        max(
            len(options),
            1,
        ),
        4,
    )

    columns = st.columns(
        column_count
    )

    selected = []

    for index, option in enumerate(
        options
    ):

        option_key = (
            option_keys[option]
        )

        with columns[
            index % column_count
        ]:

            checked = st.checkbox(
                str(option),
                key=option_key,
            )

        if checked:

            selected.append(
                option
            )

    # --------------------------------------------------------
    # Synchronize Select All state.
    #
    # If one individual option is unticked:
    # Select All becomes OFF, but remaining checked options
    # stay selected.
    #
    # If all individual options are checked:
    # Select All becomes ON.
    # --------------------------------------------------------

    all_selected = (
        len(selected)
        == len(options)
    )

    current_select_all = (
        st.session_state.get(
            select_all_key,
            False,
        )
    )

    if (
        all_selected
        != current_select_all
    ):

        st.session_state[
            select_all_key
        ] = all_selected

    st.session_state[
        previous_all_key
    ] = all_selected

    return selected


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

    if "Ward Name" not in df.columns:

        st.warning(
            "Ward information is not available in the dataset."
        )

        return

    raw_ward_values = (
        df["Ward Name"]
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

    ward = raw_ward_values[
        valid_ward_mask
    ]

    if ward.empty:

        st.warning(
            "No valid ward records are available."
        )

        return

    all_wards = (
        _alphabetical_order(
            ward.unique().tolist()
        )
    )

    ward_counts = (
        ward
        .value_counts()
        .rename_axis("Ward")
        .reset_index(
            name="Records"
        )
    )

    total_records = len(df)

    valid_ward_count = int(
        valid_ward_mask.sum()
    )

    missing_ward = (
        total_records
        - valid_ward_count
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

    top_ward = (
        ward_counts.iloc[0]
    )

    lowest_ward = (
        ward_counts.iloc[-1]
    )

    average_records = (
        ward_counts["Records"].mean()
    )

    median_records = (
        ward_counts["Records"].median()
    )

    top5_records = int(
        ward_counts
        .head(5)["Records"]
        .sum()
    )

    top5_share = (
        top5_records
        / max(
            total_valid_ward_records,
            1,
        )
        * 100
    )


    # ========================================================
    # 1. WARD SUMMARY
    # ========================================================

    st.markdown(
        "### 1. 📊 Ward Summary"
    )

    st.markdown(
        """
        <div style="
            background:#F5F9FF;
            border:1px solid #DCE9F8;
            border-radius:10px;
            padding:10px 14px 4px 14px;
            margin-bottom:10px;
        ">
        <b>Overall Ward Snapshot</b><br>
        <span style="font-size:13px;color:#5B6573;">
        Summary based on the currently selected Global Dashboard Filters.
        </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:

        st.metric(
            "Total Records",
            f"{total_records:,}",
        )

    with c2:

        st.metric(
            "Valid Ward Records",
            f"{valid_ward_count:,}",
        )

    with c3:

        st.metric(
            "Total Wards",
            f"{len(all_wards):,}",
        )

    with c4:

        st.metric(
            "Missing Ward Records",
            f"{missing_ward:,}",
        )

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:

        st.metric(
            "Top Burden Ward",
            str(
                top_ward["Ward"]
            ),
        )

    with c2:

        st.metric(
            "Top Ward Records",
            f"{int(top_ward['Records']):,}",
        )

    with c3:

        st.metric(
            "Top Ward Share",
            f"{float(top_ward['Percentage']):.2f}%",
        )

    with c4:

        st.metric(
            "Average / Ward",
            f"{average_records:,.1f}",
        )


    # ========================================================
    # 2. WARD BURDEN HIGHLIGHTS
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. 🏆 Ward Burden Highlights"
    )

    st.markdown(
        """
        <div style="
            background:#FFF9EE;
            border:1px solid #F3E3BD;
            border-radius:10px;
            padding:10px 14px 4px 14px;
            margin-bottom:10px;
        ">
        <b>Burden Highlights</b><br>
        <span style="font-size:13px;color:#665C4D;">
        Key ward-level burden indicators within the current filter selection.
        </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:

        st.metric(
            "Highest Burden Ward",
            str(
                top_ward["Ward"]
            ),
        )

    with c2:

        st.metric(
            "Lowest Burden Ward",
            str(
                lowest_ward["Ward"]
            ),
        )

    with c3:

        st.metric(
            "Top 5 Wards Share",
            f"{top5_share:.2f}%",
        )

    with c4:

        st.metric(
            "Median Records / Ward",
            f"{median_records:,.1f}",
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
    # 4. TOP WARD BURDEN COMPARISON
    # ========================================================

    st.divider()

    st.markdown(
        "### 4. 🔝 Top Ward Burden Comparison"
    )

    st.caption(
        "By default, the top 10 burden wards are selected. "
        "You can change the ward selection below for comparison."
    )

    default_comparison_wards = (
        ward_counts
        .head(10)["Ward"]
        .astype(str)
        .tolist()
    )

    comparison_options = (
        ward_counts["Ward"]
        .astype(str)
        .tolist()
    )

    selected_comparison_wards = (
        st.multiselect(
            "Select Ward(s) for Comparison",
            options=comparison_options,
            default=default_comparison_wards,
            key=(
                "phase5_top_ward_"
                "comparison_selector"
            ),
        )
    )

    if not selected_comparison_wards:

        st.info(
            "Please select at least one ward "
            "for burden comparison."
        )

    else:

        comparison_df = (
            ward_counts[
                ward_counts["Ward"]
                .astype(str)
                .isin(
                    selected_comparison_wards
                )
            ]
            .copy()
        )

        comparison_df[
            "_selection_order"
        ] = (
            comparison_df["Ward"]
            .astype(str)
            .map(
                {
                    value: index
                    for index, value
                    in enumerate(
                        selected_comparison_wards
                    )
                }
            )
        )

        comparison_df = (
            comparison_df
            .sort_values(
                "_selection_order"
            )
            .drop(
                columns=[
                    "_selection_order"
                ]
            )
            .reset_index(
                drop=True
            )
        )

        comparison_order = (
            comparison_df["Ward"]
            .astype(str)
            .tolist()
        )

        _render_category_bar_chart(
            dataframe=(
                comparison_df[
                    [
                        "Ward",
                        "Records",
                    ]
                ]
            ),
            category_column="Ward",
            value_column="Records",
            category_order=comparison_order,
            height=440,
            legend_columns=max(
                len(comparison_order),
                1,
            ),
        )

        comparison_display = (
            comparison_df[
                [
                    "Rank",
                    "Ward",
                    "Records",
                    "Percentage",
                ]
            ]
            .copy()
        )

        comparison_display[
            "Percentage"
        ] = (
            comparison_display[
                "Percentage"
            ]
            .map(
                lambda value: (
                    f"{value:.2f}%"
                )
            )
        )

        st.dataframe(
            comparison_display,
            use_container_width=True,
            hide_index=True,
        )


    # ========================================================
    # 5. WARD-WISE RECORD DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 5. 📊 Ward-wise Record Distribution"
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
        legend_columns=max(
            len(all_wards),
            1,
        ),
    )

    st.caption(
        "All wards available within the selected Global Dashboard "
        "Filters are displayed alphabetically from A to Z."
    )


    # ========================================================
    # 6. DISEASE-WISE WARD BURDEN
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
                & disease_ward[
                    "Ward Name"
                ].ne("NaT")
                & disease_ward[
                    "Disease"
                ].ne("NaT")
            ]
        )

        if not disease_ward.empty:

            disease_order = (
                disease_ward[
                    "Disease"
                ]
                .value_counts()
                .index
                .tolist()
            )

            selected_diseases = (
                _checkbox_selector(
                    title=(
                        "Select Disease(s)"
                    ),
                    options=disease_order,
                    key_prefix=(
                        "phase5_disease"
                    ),
                )
            )

            if not selected_diseases:

                st.info(
                    "Please select at least one disease "
                    "to display the ward-wise burden."
                )

            else:

                chart_source = (
                    disease_ward[
                        disease_ward[
                            "Disease"
                        ].isin(
                            selected_diseases
                        )
                    ]
                    .copy()
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

                complete_index = (
                    pd.MultiIndex
                    .from_product(
                        [
                            all_wards,
                            selected_diseases,
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
                    group_order=selected_diseases,
                    height=500,
                )

                disease_table = (
                    pd.crosstab(
                        chart_source[
                            "Ward Name"
                        ],
                        chart_source[
                            "Disease"
                        ],
                    )
                )

                disease_table = (
                    disease_table
                    .reindex(
                        index=all_wards,
                        columns=selected_diseases,
                        fill_value=0,
                    )
                )

                st.dataframe(
                    disease_table
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
    # 7. FACILITY-WISE WARD DISTRIBUTION
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
                & facility_ward[
                    "Ward Name"
                ].ne("NaT")
                & facility_ward[
                    "Facility Name"
                ].ne("NaT")
            ]
        )

        if not facility_ward.empty:

            facility_order = (
                facility_ward[
                    "Facility Name"
                ]
                .value_counts()
                .index
                .tolist()
            )

            selected_facilities = (
                _checkbox_selector(
                    title=(
                        "Select Facility(s)"
                    ),
                    options=facility_order,
                    key_prefix=(
                        "phase5_facility"
                    ),
                )
            )

            if not selected_facilities:

                st.info(
                    "Please select at least one facility "
                    "to display the ward-wise distribution."
                )

            else:

                chart_source = (
                    facility_ward[
                        facility_ward[
                            "Facility Name"
                        ].isin(
                            selected_facilities
                        )
                    ]
                    .copy()
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

                complete_index = (
                    pd.MultiIndex
                    .from_product(
                        [
                            all_wards,
                            selected_facilities,
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
                    group_order=selected_facilities,
                    height=500,
                )

                facility_table = (
                    pd.crosstab(
                        chart_source[
                            "Ward Name"
                        ],
                        chart_source[
                            "Facility Name"
                        ],
                    )
                )

                facility_table = (
                    facility_table
                    .reindex(
                        index=all_wards,
                        columns=selected_facilities,
                        fill_value=0,
                    )
                )

                st.dataframe(
                    facility_table
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
    # 8. WARD-WISE GENDER DISTRIBUTION
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
                if value in present_genders
            ]

            gender_order += sorted(
                [
                    value
                    for value in present_genders
                    if value not in GENDER_ORDER
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
    # 9. WARD-WISE AGE GROUP DISTRIBUTION
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

            present_age_groups = (
                ward_age[
                    "Age Group"
                ]
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

            selected_age_groups = (
                _checkbox_selector(
                    title=(
                        "Select Age Group(s)"
                    ),
                    options=age_group_order,
                    key_prefix=(
                        "phase5_age_group"
                    ),
                )
            )

            if not selected_age_groups:

                st.info(
                    "Please select at least one Age Group "
                    "to display the ward-wise distribution."
                )

            else:

                selected_age_groups = [
                    value
                    for value in age_group_order
                    if value in selected_age_groups
                ]

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

                _render_grouped_bar_chart(
                    dataframe=chart_long,
                    x_column="Ward Name",
                    group_column="Age Group",
                    value_column="Records",
                    x_order=all_wards,
                    group_order=selected_age_groups,
                    height=520,
                )

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

        available_detail_wards = (
            _alphabetical_order(
                ward.unique().tolist()
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
                        "phase5_detail_"
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
                            "phase5_detail_"
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
