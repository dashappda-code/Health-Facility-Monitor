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

    return values.replace(replacement_map)


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

    return values.replace(replacement_map)


# ============================================================
# LEGENDS
# ============================================================

def _bottom_legend(
    title=None,
    columns=10,
    label_limit=180,
):

    return alt.Legend(
        title=title,
        orient="bottom",
        direction="horizontal",
        columns=columns,
        labelFontSize=9,
        titleFontSize=10,
        symbolSize=70,
        symbolStrokeWidth=2,
        labelLimit=label_limit,
        columnPadding=10,
        rowPadding=4,
        offset=8,
    )


def _ward_single_row_legend(title=None):

    return alt.Legend(
        title=title,
        orient="bottom",
        direction="horizontal",
        columns=50,
        labelFontSize=8,
        titleFontSize=9,
        symbolSize=50,
        symbolStrokeWidth=1,
        labelLimit=55,
        columnPadding=4,
        rowPadding=2,
        offset=6,
    )


# ============================================================
# AXES
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
            labelLimit=260,
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
    single_row_legend=False,
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
        for index in range(len(category_order))
    ]

    color_scale = alt.Scale(
        domain=category_order,
        range=colors,
    )

    if single_row_legend:

        legend = _ward_single_row_legend(
            category_column
        )

    else:

        legend = _bottom_legend(
            category_column,
            columns=4,
            label_limit=300,
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
                axis=_y_axis(value_column),
            ),
            color=alt.Color(
                f"{category_column}:N",
                scale=color_scale,
                legend=legend,
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
        .properties(height=height)
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

        chart = bars + labels

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
    legend_columns=5,
    legend_label_limit=220,
):

    if dataframe is None or dataframe.empty:
        return

    chart_df = dataframe.copy()

    chart_df[x_column] = (
        chart_df[x_column].astype(str)
    )

    chart_df[group_column] = (
        chart_df[group_column].astype(str)
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

    for index, group in enumerate(group_order):

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

    color_scale = alt.Scale(
        domain=group_order,
        range=colors,
    )

    legend = _bottom_legend(
        group_column,
        columns=legend_columns,
        label_limit=legend_label_limit,
    )

    bars = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{x_column}:N",
                sort=x_order,
                axis=_x_axis(x_column),
            ),
            xOffset=alt.XOffset(
                f"{group_column}:N",
                sort=group_order,
            ),
            y=alt.Y(
                f"{value_column}:Q",
                axis=_y_axis(value_column),
            ),
            color=alt.Color(
                f"{group_column}:N",
                sort=group_order,
                scale=color_scale,
                legend=legend,
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
        .properties(height=height)
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

        chart = bars + labels

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# CHECKBOX MULTI-SELECTION
# ============================================================

def _checkbox_multiselect(
    label,
    options,
    key_prefix,
):

    options = list(options)

    if not options:
        return []

    select_all_key = (
        f"{key_prefix}_select_all"
    )

    option_keys = [
        f"{key_prefix}_option_{index}"
        for index in range(len(options))
    ]

    init_key = (
        f"{key_prefix}_initialized"
    )

    # --------------------------------------------------------
    # INITIAL DEFAULT
    # Select All = ON
    # Every individual option = ON
    # --------------------------------------------------------

    if init_key not in st.session_state:

        st.session_state[init_key] = True
        st.session_state[select_all_key] = True

        for option_key in option_keys:
            st.session_state[option_key] = True

    # --------------------------------------------------------
    # CALLBACK: SELECT ALL
    # --------------------------------------------------------

    def select_all_changed():

        new_value = bool(
            st.session_state.get(
                select_all_key,
                False,
            )
        )

        for option_key in option_keys:

            st.session_state[
                option_key
            ] = new_value

    # --------------------------------------------------------
    # CALLBACK: INDIVIDUAL ITEM
    # --------------------------------------------------------

    def individual_changed():

        all_selected = all(
            bool(
                st.session_state.get(
                    option_key,
                    False,
                )
            )
            for option_key in option_keys
        )

        st.session_state[
            select_all_key
        ] = all_selected

    # --------------------------------------------------------
    # POPOVER / DROPDOWN
    # --------------------------------------------------------

    with st.popover(
        label,
        use_container_width=True,
    ):

        st.checkbox(
            "Select All",
            key=select_all_key,
            on_change=select_all_changed,
        )

        st.divider()

        selected = []

        for index, option in enumerate(options):

            option_key = option_keys[index]

            checked = st.checkbox(
                str(option),
                key=option_key,
                on_change=individual_changed,
            )

            if checked:
                selected.append(option)

    return selected


# ============================================================
# COMPLETE GROUPED DATA
# ============================================================

def _complete_grouped_data(
    source,
    x_column,
    group_column,
    x_order,
    group_order,
):

    chart_long = (
        source
        .groupby(
            [
                x_column,
                group_column,
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
                x_order,
                group_order,
            ],
            names=[
                x_column,
                group_column,
            ],
        )
    )

    return (
        chart_long
        .set_index(
            [
                x_column,
                group_column,
            ]
        )
        .reindex(
            complete_index,
            fill_value=0,
        )
        .reset_index()
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
    # VALIDATE WARD
    # ========================================================

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

    top_ward = ward_counts.iloc[0]

    lowest_ward = ward_counts.iloc[-1]

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
        "**Overall Ward Snapshot** — summary based on the "
        "currently selected Global Dashboard Filters."
    )

    c1, c2, c3, c4 = st.columns(4)

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

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Top Burden Ward",
            str(top_ward["Ward"]),
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
        "**Key burden indicators** within the current "
        "Global Dashboard Filter selection."
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Highest Burden Ward",
            str(top_ward["Ward"]),
        )

    with c2:

        st.metric(
            "Lowest Burden Ward",
            str(lowest_ward["Ward"]),
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

    display_wards["Percentage"] = (
        display_wards["Percentage"]
        .map(
            lambda value:
            f"{value:.2f}%"
        )
    )

    st.dataframe(
        display_wards,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # TOP BURDEN WARDS
    # --------------------------------------------------------

    st.markdown(
        "#### 🔝 Top Burden Wards"
    )

    burden_options = [
        option
        for option in [
            5,
            10,
            15,
            20,
        ]
        if option <= len(ward_counts)
    ]

    if len(ward_counts) not in burden_options:

        burden_options.append(
            len(ward_counts)
        )

    burden_options = sorted(
        list(set(burden_options))
    )

    burden_labels = {
        value: (
            "All Wards"
            if value == len(ward_counts)
            else f"Top {value}"
        )
        for value in burden_options
    }

    selected_burden_count = (
        st.selectbox(
            "Select Burden View",
            options=burden_options,
            format_func=lambda value:
            burden_labels[value],
            index=(
                burden_options.index(10)
                if 10 in burden_options
                else 0
            ),
            key="phase5_burden_view",
        )
    )

    burden_df = (
        ward_counts
        .head(selected_burden_count)
        .copy()
    )

    _render_category_bar_chart(
        dataframe=burden_df[
            [
                "Ward",
                "Records",
            ]
        ],
        category_column="Ward",
        value_column="Records",
        category_order=burden_df[
            "Ward"
        ].tolist(),
        height=430,
        single_row_legend=True,
    )

    burden_display = (
        burden_df[
            [
                "Rank",
                "Ward",
                "Records",
                "Percentage",
            ]
        ]
        .copy()
    )

    burden_display["Percentage"] = (
        burden_display["Percentage"]
        .map(
            lambda value:
            f"{value:.2f}%"
        )
    )

    st.dataframe(
        burden_display,
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
        .set_index("Ward")
        .reindex(all_wards)
        .fillna(0)
        .reset_index()
    )

    _render_category_bar_chart(
        dataframe=chart_wards,
        category_column="Ward",
        value_column="Records",
        category_order=all_wards,
        height=450,
        single_row_legend=True,
    )

    st.caption(
        "All available wards are displayed alphabetically "
        "from A to Z."
    )


    # ========================================================
    # 5. DISEASE-WISE WARD BURDEN
    # ========================================================

    st.divider()

    st.markdown(
        "### 5. 🦠 Disease-wise Ward Burden"
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

            # ALL available diseases
            disease_order = (
                disease_ward["Disease"]
                .value_counts()
                .index
                .tolist()
            )

            selected_diseases = (
                _checkbox_multiselect(
                    label="Select Disease(s)",
                    options=disease_order,
                    key_prefix="phase5_disease",
                )
            )

            if not selected_diseases:

                st.info(
                    "Please select at least one disease."
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
                    _complete_grouped_data(
                        source=chart_source,
                        x_column="Ward Name",
                        group_column="Disease",
                        x_order=all_wards,
                        group_order=selected_diseases,
                    )
                )


                # Keep Disease legend compact:
# up to 2 rows depending on the number of selected diseases.
disease_legend_columns = max(
    1,
    (len(selected_diseases) + 1) // 2,
)

_render_grouped_bar_chart(
    dataframe=chart_long,
    x_column="Ward Name",
    group_column="Disease",
    value_column="Records",
    x_order=all_wards,
    group_order=selected_diseases,
    height=500,
    legend_columns=disease_legend_columns,
    legend_label_limit=220,
)

                

                disease_table = (
                    pd.crosstab(
                        chart_source["Ward Name"],
                        chart_source["Disease"],
                    )
                    .reindex(
                        index=all_wards,
                        columns=selected_diseases,
                        fill_value=0,
                    )
                )

                st.caption(
                    f"{len(selected_diseases)} of "
                    f"{len(disease_order)} available diseases "
                    "are currently selected. Wards are displayed "
                    "alphabetically from A to Z."
                )

                st.dataframe(
                    disease_table.reset_index(),
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
    # 6. WARD-WISE FACILITY DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 6. 🏥 Ward-wise Facility Distribution"
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

            facility_order = (
                facility_ward["Facility Name"]
                .value_counts()
                .index
                .tolist()
            )

            top10_facilities = (
                facility_order[:10]
            )

            remaining_facilities = (
                facility_order[10:]
            )

            facility_view_options = [
                "Top 10 Facilities"
            ]

            if remaining_facilities:

                facility_view_options.append(
                    "Remaining Facilities"
                )

            facility_view = (
                st.radio(
                    "Facility Comparison View",
                    options=facility_view_options,
                    horizontal=True,
                    key="phase5_facility_view",
                )
            )

            if (
                facility_view
                == "Top 10 Facilities"
            ):

                available_facilities = (
                    top10_facilities
                )

                st.caption(
                    "Top 10 facilities by record volume are "
                    "displayed by default."
                )

            else:

                available_facilities = (
                    remaining_facilities
                )

                st.caption(
                    f"Displaying the remaining "
                    f"{len(remaining_facilities)} facilities "
                    "after the Top 10 facilities."
                )

            selected_facilities = (
                _checkbox_multiselect(
                    label="Select Facility(s)",
                    options=available_facilities,
                    key_prefix=(
                        "phase5_facility_top10"
                        if facility_view
                        == "Top 10 Facilities"
                        else
                        "phase5_facility_remaining"
                    ),
                )
            )

            if not selected_facilities:

                st.info(
                    "Please select at least one facility."
                )

            else:

                facility_chart_source = (
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
                    _complete_grouped_data(
                        source=facility_chart_source,
                        x_column="Ward Name",
                        group_column="Facility Name",
                        x_order=all_wards,
                        group_order=selected_facilities,
                    )
                )

                # ------------------------------------------------
                # IMPORTANT:
                # Facility names can be long.
                # Legend uses multiple rows and larger label limit.
                # ------------------------------------------------

                _render_grouped_bar_chart(
                    dataframe=chart_long,
                    x_column="Ward Name",
                    group_column="Facility Name",
                    value_column="Records",
                    x_order=all_wards,
                    group_order=selected_facilities,
                    height=520,
                    legend_columns=3,
                    legend_label_limit=500,
                )

                facility_table = (
                    pd.crosstab(
                        facility_chart_source[
                            "Ward Name"
                        ],
                        facility_chart_source[
                            "Facility Name"
                        ],
                    )
                    .reindex(
                        index=all_wards,
                        columns=selected_facilities,
                        fill_value=0,
                    )
                )

                st.caption(
                    f"{len(selected_facilities)} facility/facilities "
                    "are currently selected. All selected facilities "
                    "are included in the chart legend. Wards are "
                    "displayed alphabetically from A to Z."
                )

                st.dataframe(
                    facility_table.reset_index(),
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
    # 7. WARD-WISE GENDER DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 7. 👥 Ward-wise Gender Distribution"
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

            present_genders = (
                ward_gender["Gender"]
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
                _complete_grouped_data(
                    source=ward_gender,
                    x_column="Ward Name",
                    group_column="Gender",
                    x_order=all_wards,
                    group_order=gender_order,
                )
            )

            _render_grouped_bar_chart(
                dataframe=chart_long,
                x_column="Ward Name",
                group_column="Gender",
                value_column="Records",
                x_order=all_wards,
                group_order=gender_order,
                height=500,
                legend_columns=5,
                legend_label_limit=180,
            )

            gender_table = (
                pd.crosstab(
                    ward_gender["Ward Name"],
                    ward_gender["Gender"],
                )
                .reindex(
                    index=all_wards,
                    columns=gender_order,
                    fill_value=0,
                )
            )

            st.caption(
                "All available wards are displayed "
                "alphabetically from A to Z."
            )

            st.dataframe(
                gender_table.reset_index(),
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
    # 8. WARD-WISE AGE GROUP DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 8. 🎂 Ward-wise Age Group Distribution"
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

            present_age_groups = (
                ward_age["Age Group"]
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
                _checkbox_multiselect(
                    label="Select Age Group(s)",
                    options=age_group_order,
                    key_prefix="phase5_age_group",
                )
            )

            if not selected_age_groups:

                st.info(
                    "Please select at least one Age Group."
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
                    _complete_grouped_data(
                        source=chart_source,
                        x_column="Ward Name",
                        group_column="Age Group",
                        x_order=all_wards,
                        group_order=selected_age_groups,
                    )
                )

                _render_grouped_bar_chart(
                    dataframe=chart_long,
                    x_column="Ward Name",
                    group_column="Age Group",
                    value_column="Records",
                    x_order=all_wards,
                    group_order=selected_age_groups,
                    height=520,
                    legend_columns=8,
                    legend_label_limit=160,
                )

                age_table = (
                    pd.crosstab(
                        chart_source["Ward Name"],
                        chart_source["Age Group"],
                    )
                    .reindex(
                        index=all_wards,
                        columns=selected_age_groups,
                        fill_value=0,
                    )
                )

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
                        "from A to Z."
                    )

                else:

                    selected_text = ", ".join(
                        selected_age_groups
                    )

                    st.caption(
                        f"Selected Age Groups: {selected_text}. "
                        "All wards are displayed alphabetically "
                        "from A to Z."
                    )

                st.dataframe(
                    age_table.reset_index(),
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
    # 9. WARD – FACILITY DETAIL
    # ========================================================

    st.divider()

    st.markdown(
        "### 9. 🏥 Ward – Facility Detail"
    )

    if "Facility Name" in df.columns:

        available_detail_wards = (
            _alphabetical_order(
                ward.unique().tolist()
            )
        )

        if available_detail_wards:

            # ------------------------------------------------
            # If Global Ward filter has reduced data to one
            # ward, that ward is automatically locked here.
            # ------------------------------------------------

            if len(available_detail_wards) == 1:

                selected_ward = (
                    available_detail_wards[0]
                )

                st.selectbox(
                    "Select Ward",
                    options=[selected_ward],
                    index=0,
                    key="phase5_detail_ward_single",
                    disabled=True,
                )

            else:

                default_ward = str(
                    top_ward["Ward"]
                )

                try:

                    default_index = (
                        available_detail_wards
                        .index(default_ward)
                    )

                except ValueError:

                    default_index = 0

                selected_ward = (
                    st.selectbox(
                        "Select Ward",
                        options=available_detail_wards,
                        index=default_index,
                        key="phase5_detail_ward_selector",
                    )
                )

            ward_facility_df = (
                df[
                    df["Ward Name"]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .eq(selected_ward)
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

                facility_values = facility_values[
                    facility_values.ne("")
                    & facility_values.ne("nan")
                    & facility_values.ne("NaT")
                    & facility_values.ne("None")
                ]

                if not facility_values.empty:

                    facility_counts = (
                        facility_values
                        .value_counts()
                        .rename_axis("Facility")
                        .reset_index(
                            name="Records"
                        )
                    )

                    facility_counts.insert(
                        0,
                        "Rank",
                        range(
                            1,
                            len(facility_counts) + 1,
                        ),
                    )

                    st.caption(
                        f"Facility distribution for Ward "
                        f"{selected_ward}."
                    )

                    _render_category_bar_chart(
                        dataframe=facility_counts[
                            [
                                "Facility",
                                "Records",
                            ]
                        ],
                        category_column="Facility",
                        value_column="Records",
                        category_order=facility_counts[
                            "Facility"
                        ].tolist(),
                        height=500,
                        vertical_labels=True,
                        single_row_legend=False,
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
    # 10. WARD DATA QUALITY
    # ========================================================

    st.divider()

    st.markdown(
        "### 10. ℹ️ Ward Data Quality"
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

    ward_quality["Percentage"] = (
        ward_quality["Count"]
        / max(total_records, 1)
        * 100
    ).round(2)

    quality_display = (
        ward_quality.copy()
    )

    quality_display["Percentage"] = (
        quality_display["Percentage"]
        .map(
            lambda value:
            f"{value:.2f}%"
        )
    )

    st.dataframe(
        quality_display,
        use_container_width=True,
        hide_index=True,
    )
