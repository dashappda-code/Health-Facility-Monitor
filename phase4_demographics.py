import streamlit as st
import pandas as pd
import altair as alt

from chart_helpers import (
    data_labels_enabled,
    render_bar_chart,
    render_line_chart,
)


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

AGE_LINE_COLOR = "#1F77B4"

# Slightly larger and bold data labels across demographic charts.
DATA_LABEL_FONT_SIZE = 13
GROUPED_DATA_LABEL_FONT_SIZE = 12
PYRAMID_DATA_LABEL_FONT_SIZE = 12


# ============================================================
# COMMON CHART CONFIGURATION
# ============================================================

def _bottom_legend(
    title=None,
):

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


def _x_axis(
    title=None,
):

    return alt.Axis(
        title=title,
        labelAngle=-45,
        labelAlign="right",
        labelBaseline="middle",
        labelFontSize=11,
        titleFontSize=12,
        labelLimit=180,
    )


def _y_axis(
    title=None,
):

    return alt.Axis(
        title=title,
        labelFontSize=11,
        titleFontSize=12,
    )


# ============================================================
# TEXT HELPERS
# ============================================================

def _clean_text(
    df,
    column,
):

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return pd.Series(
            dtype="object"
        )

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


# ============================================================
# STANDARDIZE GENDER
# ============================================================

def _standardize_gender(
    series,
):

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

    values = values.replace(
        replacement_map
    )

    return values


# ============================================================
# STANDARDIZE AGE GROUP
# ============================================================

def _standardize_age_group(
    series,
):

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

    values = values.replace(
        replacement_map
    )

    return values


# ============================================================
# AGE GROUP SORT
# ============================================================

def _age_group_sort(
    df,
    column="Age Group",
):

    if (
        df.empty
        or column not in df.columns
    ):
        return df

    result = df.copy()

    result[column] = (
        _standardize_age_group(
            result[column]
        )
    )

    present_values = (
        result[column]
        .dropna()
        .astype(str)
        .tolist()
    )

    known = [
        value
        for value in AGE_GROUP_ORDER
        if value in present_values
    ]

    remaining = sorted(
        [
            value
            for value in (
                result[column]
                .dropna()
                .astype(str)
                .unique()
            )
            if value not in AGE_GROUP_ORDER
        ]
    )

    final_order = (
        known
        + remaining
    )

    result[column] = pd.Categorical(
        result[column],
        categories=final_order,
        ordered=True,
    )

    return (
        result
        .sort_values(column)
        .reset_index(drop=True)
    )


# ============================================================
# CATEGORY BAR CHART
# ============================================================

def _render_category_bar_chart(
    dataframe,
    category_column,
    value_column="Records",
    height=400,
):

    if dataframe is None or dataframe.empty:
        return

    chart_df = dataframe.copy()

    categories = (
        chart_df[category_column]
        .astype(str)
        .tolist()
    )

    colors = [
        DEFAULT_CATEGORY_COLORS[
            index
            % len(DEFAULT_CATEGORY_COLORS)
        ]
        for index in range(
            len(categories)
        )
    ]

    color_scale = alt.Scale(
        domain=categories,
        range=colors,
    )

    bars = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X(
                f"{category_column}:N",
                sort=categories,
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
                    sort=categories,
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
    height=450,
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

    groups = (
        chart_df[group_column]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    group_colors = []

    for index, group in enumerate(
        groups
    ):

        if group in GENDER_COLORS:

            group_colors.append(
                GENDER_COLORS[group]
            )

        else:

            group_colors.append(
                DEFAULT_CATEGORY_COLORS[
                    index
                    % len(
                        DEFAULT_CATEGORY_COLORS
                    )
                ]
            )

    color_scale = alt.Scale(
        domain=groups,
        range=group_colors,
    )

    if x_order is None:

        x_order = (
            chart_df[x_column]
            .drop_duplicates()
            .tolist()
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
                f"{group_column}:N"
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
                fontSize=GROUPED_DATA_LABEL_FONT_SIZE,
                fontWeight="bold",
            )
            .encode(
                x=alt.X(
                    f"{x_column}:N",
                    sort=x_order,
                ),
                xOffset=alt.XOffset(
                    f"{group_column}:N"
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
# AGE-GENDER POPULATION PYRAMID
# ============================================================

def _render_population_pyramid(
    df,
):

    if (
        "Age Group" not in df.columns
        or "Gender" not in df.columns
    ):

        st.info(
            "Age Group and Gender information "
            "is required for the population pyramid."
        )

        return

    pyramid_df = df[
        [
            "Age Group",
            "Gender",
        ]
    ].copy()

    pyramid_df["Age Group"] = (
        _standardize_age_group(
            pyramid_df["Age Group"]
        )
    )

    pyramid_df["Gender"] = (
        _standardize_gender(
            pyramid_df["Gender"]
        )
    )

    pyramid_df = pyramid_df[
        pyramid_df["Age Group"].ne("")
        & pyramid_df["Gender"].ne("")
        & pyramid_df["Age Group"].ne("nan")
        & pyramid_df["Gender"].ne("nan")
        & pyramid_df["Age Group"].ne("NaT")
        & pyramid_df["Gender"].ne("NaT")
    ]

    if pyramid_df.empty:

        st.info(
            "Age Group and Gender data "
            "is not available for the population pyramid."
        )

        return

    counts = (
        pyramid_df
        .groupby(
            [
                "Age Group",
                "Gender",
            ],
            observed=True,
        )
        .size()
        .reset_index(
            name="Records"
        )
    )

    present_age_groups = (
        counts["Age Group"]
        .astype(str)
        .unique()
        .tolist()
    )

    age_order = [
        value
        for value in AGE_GROUP_ORDER
        if value in present_age_groups
    ]

    age_order += sorted(
        [
            value
            for value in present_age_groups
            if value not in AGE_GROUP_ORDER
        ]
    )

    genders = (
        counts["Gender"]
        .astype(str)
        .unique()
        .tolist()
    )

    ordered_genders = [
        value
        for value in GENDER_ORDER
        if value in genders
    ]

    ordered_genders += sorted(
        [
            value
            for value in genders
            if value not in GENDER_ORDER
        ]
    )

    # --------------------------------------------------------
    # Male is displayed on the left side.
    # All other gender categories remain on the right side.
    # Transgender / Other records are retained even when
    # their counts are very small.
    # --------------------------------------------------------

    counts["Plot Records"] = (
        counts["Records"]
        .astype(float)
    )

    counts.loc[
        counts["Gender"].eq("Male"),
        "Plot Records",
    ] *= -1

    color_range = []

    for index, gender in enumerate(
        ordered_genders
    ):

        if gender in GENDER_COLORS:

            color_range.append(
                GENDER_COLORS[
                    gender
                ]
            )

        else:

            color_range.append(
                DEFAULT_CATEGORY_COLORS[
                    index
                    % len(
                        DEFAULT_CATEGORY_COLORS
                    )
                ]
            )

    color_scale = alt.Scale(
        domain=ordered_genders,
        range=color_range,
    )

    max_count = (
        counts["Records"]
        .max()
    )

    if pd.isna(max_count):
        max_count = 1

    max_count = max(
        int(max_count),
        1,
    )

    domain_limit = (
        max_count
        * 1.18
    )

    bars = (
        alt.Chart(counts)
        .mark_bar()
        .encode(
            y=alt.Y(
                "Age Group:N",
                sort=age_order,
                axis=alt.Axis(
                    title="Age Group",
                    labelFontSize=11,
                    titleFontSize=12,
                ),
            ),
            x=alt.X(
                "Plot Records:Q",
                scale=alt.Scale(
                    domain=[
                        -domain_limit,
                        domain_limit,
                    ]
                ),
                axis=alt.Axis(
                    title="Records",
                    labelExpr="abs(datum.value)",
                    labelFontSize=11,
                    titleFontSize=12,
                ),
            ),
            color=alt.Color(
                "Gender:N",
                scale=color_scale,
                legend=_bottom_legend(
                    "Gender"
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "Age Group:N",
                    title="Age Group",
                ),
                alt.Tooltip(
                    "Gender:N",
                    title="Gender",
                ),
                alt.Tooltip(
                    "Records:Q",
                    title="Records",
                    format=",",
                ),
            ],
        )
        .properties(
            height=430
        )
    )

    zero_line = (
        alt.Chart(
            pd.DataFrame(
                {
                    "x": [0]
                }
            )
        )
        .mark_rule(
            color="#777777",
            strokeWidth=1,
        )
        .encode(
            x="x:Q"
        )
    )

    chart = (
        bars
        + zero_line
    )

    if data_labels_enabled():

        labels = (
            alt.Chart(counts)
            .mark_text(
                fontWeight="bold",
                fontSize=PYRAMID_DATA_LABEL_FONT_SIZE,
                dx=0,
            )
            .encode(
                y=alt.Y(
                    "Age Group:N",
                    sort=age_order,
                ),
                x=alt.X(
                    "Plot Records:Q"
                ),
                text=alt.Text(
                    "Records:Q",
                    format=",",
                ),
                color=alt.Color(
                    "Gender:N",
                    scale=color_scale,
                    legend=None,
                ),
            )
        )

        chart = (
            bars
            + zero_line
            + labels
        )

    st.altair_chart(
        chart,
        use_container_width=True,
    )

    display_table = (
        counts[
            [
                "Age Group",
                "Gender",
                "Records",
            ]
        ]
        .pivot_table(
            index="Age Group",
            columns="Gender",
            values="Records",
            aggfunc="sum",
            fill_value=0,
            observed=True,
        )
        .reset_index()
    )

    display_table["Age Group"] = pd.Categorical(
        display_table["Age Group"],
        categories=age_order,
        ordered=True,
    )

    display_table = (
        display_table
        .sort_values("Age Group")
        .reset_index(drop=True)
    )

    st.dataframe(
        display_table,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Male records are displayed on the left side of the "
        "pyramid. Female, Transgender and other recorded gender "
        "categories are displayed on the right side. Small counts "
        "are retained in the chart and table."
    )


# ============================================================
# MAIN DEMOGRAPHICS PAGE
# ============================================================

def render_demographics(
    df,
):

    st.subheader(
        "👥 Demographic Analysis"
    )

    if df is None or df.empty:

        st.warning(
            "No records available for the selected filters."
        )

        return

    st.caption(
        "Age-wise, age-group-wise, gender-wise and OPD/IPD "
        "analysis based on the selected Global Dashboard Filters."
    )

    # ========================================================
    # 1. DEMOGRAPHIC SUMMARY
    # ========================================================

    st.markdown(
        "### 1. 📊 Demographic Summary"
    )

    total_records = len(
        df
    )

    if "Age" in df.columns:

        age_numeric = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

        valid_age = age_numeric[
            age_numeric.between(
                0,
                120,
            )
        ]

    else:

        valid_age = pd.Series(
            dtype="float64"
        )

    if not valid_age.empty:

        mean_age = valid_age.mean()
        median_age = valid_age.median()
        min_age = valid_age.min()
        max_age = valid_age.max()

    else:

        mean_age = None
        median_age = None
        min_age = None
        max_age = None

    c1, c2, c3, c4, c5 = (
        st.columns(5)
    )

    with c1:

        st.metric(
            "Records",
            f"{total_records:,}",
        )

    with c2:

        st.metric(
            "Mean Age",
            (
                f"{mean_age:.1f} years"
                if mean_age is not None
                else "N/A"
            ),
        )

    with c3:

        st.metric(
            "Median Age",
            (
                f"{median_age:.1f} years"
                if median_age is not None
                else "N/A"
            ),
        )

    with c4:

        st.metric(
            "Minimum Age",
            (
                f"{min_age:.0f}"
                if min_age is not None
                else "N/A"
            ),
        )

    with c5:

        st.metric(
            "Maximum Age",
            (
                f"{max_age:.0f}"
                if max_age is not None
                else "N/A"
            ),
        )

    # ========================================================
    # 2. AGE GROUP-WISE DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. 🎂 Age Group-wise Distribution"
    )

    if "Age Group" in df.columns:

        age_group = (
            _standardize_age_group(
                df["Age Group"]
            )
        )

        age_group = age_group[
            age_group.ne("")
            & age_group.ne("nan")
            & age_group.ne("NaT")
        ]

        if not age_group.empty:

            age_group_counts = (
                age_group
                .value_counts()
                .rename_axis(
                    "Age Group"
                )
                .reset_index(
                    name="Records"
                )
            )

            age_group_counts = (
                _age_group_sort(
                    age_group_counts
                )
            )

            age_group_counts[
                "Percentage"
            ] = (
                age_group_counts[
                    "Records"
                ]
                / age_group_counts[
                    "Records"
                ].sum()
                * 100
            ).round(2)

            _render_category_bar_chart(
                dataframe=age_group_counts,
                category_column="Age Group",
                value_column="Records",
                height=400,
            )

            display_age_group = (
                age_group_counts.copy()
            )

            display_age_group[
                "Percentage"
            ] = (
                display_age_group[
                    "Percentage"
                ]
                .map(
                    lambda x: (
                        f"{x:.2f}%"
                    )
                )
            )

            st.dataframe(
                display_age_group,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Age Group information is not available."
            )

    else:

        st.info(
            "Age Group column is not available."
        )

    # ========================================================
    # 3. GENDER-WISE DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 3. ⚧ Gender-wise Distribution"
    )

    if "Gender" in df.columns:

        gender = (
            _standardize_gender(
                df["Gender"]
            )
        )

        gender = gender[
            gender.ne("")
            & gender.ne("nan")
            & gender.ne("NaT")
        ]

        if not gender.empty:

            gender_counts = (
                gender
                .value_counts()
                .rename_axis(
                    "Gender"
                )
                .reset_index(
                    name="Records"
                )
            )

            gender_counts[
                "Percentage"
            ] = (
                gender_counts[
                    "Records"
                ]
                / gender_counts[
                    "Records"
                ].sum()
                * 100
            ).round(2)

            gender_order = [
                value
                for value in GENDER_ORDER
                if value
                in gender_counts[
                    "Gender"
                ].tolist()
            ]

            gender_order += [
                value
                for value in (
                    gender_counts[
                        "Gender"
                    ].tolist()
                )
                if value
                not in GENDER_ORDER
            ]

            gender_counts[
                "_order"
            ] = (
                gender_counts[
                    "Gender"
                ]
                .map(
                    {
                        value: index
                        for index, value
                        in enumerate(
                            gender_order
                        )
                    }
                )
            )

            gender_counts = (
                gender_counts
                .sort_values(
                    "_order"
                )
                .drop(
                    columns=[
                        "_order"
                    ]
                )
            )

            left, right = (
                st.columns(
                    [1.5, 1],
                    gap="large",
                )
            )

            with left:

                chart_df = (
                    gender_counts.copy()
                )

                domains = (
                    chart_df[
                        "Gender"
                    ].tolist()
                )

                ranges = []

                for index, value in enumerate(
                    domains
                ):

                    ranges.append(
                        GENDER_COLORS.get(
                            value,
                            DEFAULT_CATEGORY_COLORS[
                                index
                                % len(
                                    DEFAULT_CATEGORY_COLORS
                                )
                            ],
                        )
                    )

                color_scale = alt.Scale(
                    domain=domains,
                    range=ranges,
                )

                bars = (
                    alt.Chart(
                        chart_df
                    )
                    .mark_bar()
                    .encode(
                        x=alt.X(
                            "Gender:N",
                            sort=domains,
                            axis=_x_axis(
                                "Gender"
                            ),
                        ),
                        y=alt.Y(
                            "Records:Q",
                            axis=_y_axis(
                                "Records"
                            ),
                        ),
                        color=alt.Color(
                            "Gender:N",
                            scale=color_scale,
                            legend=_bottom_legend(
                                "Gender"
                            ),
                        ),
                        tooltip=[
                            alt.Tooltip(
                                "Gender:N",
                                title="Gender",
                            ),
                            alt.Tooltip(
                                "Records:Q",
                                title="Records",
                                format=",",
                            ),
                            alt.Tooltip(
                                "Percentage:Q",
                                title="Percentage",
                                format=".2f",
                            ),
                        ],
                    )
                    .properties(
                        height=400
                    )
                )

                gender_chart = bars

                if data_labels_enabled():

                    labels = (
                        alt.Chart(
                            chart_df
                        )
                        .mark_text(
                            dy=-9,
                            fontWeight="bold",
                            fontSize=DATA_LABEL_FONT_SIZE,
                        )
                        .encode(
                            x=alt.X(
                                "Gender:N",
                                sort=domains,
                            ),
                            y=alt.Y(
                                "Records:Q"
                            ),
                            text=alt.Text(
                                "Records:Q",
                                format=",",
                            ),
                            color=alt.Color(
                                "Gender:N",
                                scale=color_scale,
                                legend=None,
                            ),
                        )
                    )

                    gender_chart = (
                        bars
                        + labels
                    )

                st.altair_chart(
                    gender_chart,
                    use_container_width=True,
                )

            with right:

                display_gender = (
                    gender_counts.copy()
                )

                display_gender[
                    "Percentage"
                ] = (
                    display_gender[
                        "Percentage"
                    ]
                    .map(
                        lambda x: (
                            f"{x:.2f}%"
                        )
                    )
                )

                st.dataframe(
                    display_gender,
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.info(
                "Gender information is not available."
            )

    else:

        st.info(
            "Gender column is not available."
        )

    # ========================================================
    # 4. AGE-WISE DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 4. 📈 Age-wise Distribution"
    )

    if "Age" in df.columns:

        age_data = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

        age_data = age_data[
            age_data.between(
                0,
                120,
            )
        ]

        if not age_data.empty:

            age_counts = (
                age_data
                .round()
                .astype(int)
                .value_counts()
                .sort_index()
                .rename_axis(
                    "Age"
                )
                .reset_index(
                    name="Records"
                )
            )

            # ------------------------------------------------
            # Fixed chart color:
            # line, points and data labels use the same color.
            # ------------------------------------------------

            age_line = (
                alt.Chart(
                    age_counts
                )
                .mark_line(
                    point=alt.OverlayMarkDef(
                        filled=True,
                        size=60,
                    ),
                    strokeWidth=3,
                    color=AGE_LINE_COLOR,
                )
                .encode(
                    x=alt.X(
                        "Age:O",
                        sort="ascending",
                        axis=_x_axis(
                            "Age"
                        ),
                    ),
                    y=alt.Y(
                        "Records:Q",
                        axis=_y_axis(
                            "Records"
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "Age:O",
                            title="Age",
                        ),
                        alt.Tooltip(
                            "Records:Q",
                            title="Records",
                            format=",",
                        ),
                    ],
                )
                .properties(
                    height=420
                )
            )

            age_chart = age_line

            if data_labels_enabled():

                age_labels = (
                    alt.Chart(
                        age_counts
                    )
                    .mark_text(
                        dy=-10,
                        fontSize=DATA_LABEL_FONT_SIZE,
                        fontWeight="bold",
                        color=AGE_LINE_COLOR,
                    )
                    .encode(
                        x=alt.X(
                            "Age:O",
                            sort="ascending",
                        ),
                        y=alt.Y(
                            "Records:Q"
                        ),
                        text=alt.Text(
                            "Records:Q",
                            format=",",
                        ),
                    )
                )

                age_chart = (
                    age_line
                    + age_labels
                )

            st.altair_chart(
                age_chart,
                use_container_width=True,
            )

            st.dataframe(
                age_counts,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Valid age information is not available."
            )

    else:

        st.info(
            "Age column is not available."
        )

    # ========================================================
    # 5. AGE-GENDER POPULATION PYRAMID
    # ========================================================

    st.divider()

    st.markdown(
        "### 5. 👥 Age–Gender Population Pyramid"
    )

    _render_population_pyramid(
        df
    )

    # ========================================================
    # 6. GENDER × AGE GROUP
    # ========================================================

    st.divider()

    st.markdown(
        "### 6. 👥 Gender × Age Group"
    )

    if (
        "Gender" in df.columns
        and "Age Group" in df.columns
    ):

        cross_df = df[
            [
                "Gender",
                "Age Group",
            ]
        ].copy()

        cross_df[
            "Gender"
        ] = (
            _standardize_gender(
                cross_df[
                    "Gender"
                ]
            )
        )

        cross_df[
            "Age Group"
        ] = (
            _standardize_age_group(
                cross_df[
                    "Age Group"
                ]
            )
        )

        cross_df = cross_df[
            cross_df[
                "Gender"
            ].ne("")
            & cross_df[
                "Age Group"
            ].ne("")
            & cross_df[
                "Gender"
            ].ne("nan")
            & cross_df[
                "Age Group"
            ].ne("nan")
        ]

        if not cross_df.empty:

            gender_age = (
                cross_df
                .groupby(
                    [
                        "Age Group",
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
                dataframe=gender_age,
                x_column="Age Group",
                group_column="Gender",
                value_column="Records",
                x_order=AGE_GROUP_ORDER,
                height=450,
            )

            gender_age_table = (
                pd.crosstab(
                    cross_df[
                        "Age Group"
                    ],
                    cross_df[
                        "Gender"
                    ],
                )
            )

            available = [
                value
                for value
                in AGE_GROUP_ORDER
                if value
                in gender_age_table.index
            ]

            remaining = sorted(
                [
                    value
                    for value
                    in gender_age_table.index
                    if value
                    not in AGE_GROUP_ORDER
                ]
            )

            gender_age_table = (
                gender_age_table
                .reindex(
                    available
                    + remaining
                )
            )

            st.dataframe(
                gender_age_table
                .reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Gender and Age Group cross-analysis "
                "is not available."
            )

    else:

        st.info(
            "Gender and Age Group columns are required."
        )

    # ========================================================
    # 7. OPD / IPD DEMOGRAPHIC DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 7. 🏨 OPD / IPD Demographic Distribution"
    )

    if "OPD/IPD" in df.columns:

        opd = _clean_text(
            df,
            "OPD/IPD",
        )

        opd = opd[
            opd.ne("")
            & opd.ne("nan")
            & opd.ne("NaT")
        ]

        if not opd.empty:

            opd_counts = (
                opd
                .value_counts()
                .rename_axis(
                    "OPD/IPD"
                )
                .reset_index(
                    name="Records"
                )
            )

            opd_counts[
                "Percentage"
            ] = (
                opd_counts[
                    "Records"
                ]
                / opd_counts[
                    "Records"
                ].sum()
                * 100
            ).round(2)

            c1, c2 = (
                st.columns(
                    [1.5, 1],
                    gap="large",
                )
            )

            with c1:

                _render_category_bar_chart(
                    dataframe=opd_counts,
                    category_column="OPD/IPD",
                    value_column="Records",
                    height=400,
                )

            with c2:

                display_opd = (
                    opd_counts.copy()
                )

                display_opd[
                    "Percentage"
                ] = (
                    display_opd[
                        "Percentage"
                    ]
                    .map(
                        lambda x: (
                            f"{x:.2f}%"
                        )
                    )
                )

                st.dataframe(
                    display_opd,
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.info(
                "OPD/IPD information is not available."
            )

    else:

        st.info(
            "OPD/IPD column is not available."
        )

    # ========================================================
    # 8. AGE GROUP × OPD/IPD
    # ========================================================

    st.divider()

    st.markdown(
        "### 8. 🎂 Age Group × OPD/IPD"
    )

    if (
        "Age Group" in df.columns
        and "OPD/IPD" in df.columns
    ):

        age_opd = df[
            [
                "Age Group",
                "OPD/IPD",
            ]
        ].copy()

        age_opd[
            "Age Group"
        ] = (
            _standardize_age_group(
                age_opd[
                    "Age Group"
                ]
            )
        )

        age_opd[
            "OPD/IPD"
        ] = (
            age_opd[
                "OPD/IPD"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        age_opd = age_opd[
            age_opd[
                "Age Group"
            ].ne("")
            & age_opd[
                "OPD/IPD"
            ].ne("")
            & age_opd[
                "Age Group"
            ].ne("nan")
            & age_opd[
                "OPD/IPD"
            ].ne("nan")
        ]

        if not age_opd.empty:

            chart_long = (
                age_opd
                .groupby(
                    [
                        "Age Group",
                        "OPD/IPD",
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
                x_column="Age Group",
                group_column="OPD/IPD",
                value_column="Records",
                x_order=AGE_GROUP_ORDER,
                height=450,
            )

            age_opd_table = (
                pd.crosstab(
                    age_opd[
                        "Age Group"
                    ],
                    age_opd[
                        "OPD/IPD"
                    ],
                )
            )

            available = [
                value
                for value
                in AGE_GROUP_ORDER
                if value
                in age_opd_table.index
            ]

            remaining = sorted(
                [
                    value
                    for value
                    in age_opd_table.index
                    if value
                    not in AGE_GROUP_ORDER
                ]
            )

            age_opd_table = (
                age_opd_table
                .reindex(
                    available
                    + remaining
                )
            )

            st.dataframe(
                age_opd_table
                .reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Age Group and OPD/IPD cross-analysis "
                "is not available."
            )

    else:

        st.info(
            "Age Group and OPD/IPD columns are required."
        )

    # ========================================================
    # 9. DISEASE × GENDER
    # ========================================================

    st.divider()

    st.markdown(
        "### 9. 🦠 Disease × Gender"
    )

    if (
        "Disease" in df.columns
        and "Gender" in df.columns
    ):

        disease_gender = df[
            [
                "Disease",
                "Gender",
            ]
        ].copy()

        disease_gender[
            "Disease"
        ] = (
            disease_gender[
                "Disease"
            ]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        disease_gender[
            "Gender"
        ] = (
            _standardize_gender(
                disease_gender[
                    "Gender"
                ]
            )
        )

        disease_gender = (
            disease_gender[
                disease_gender[
                    "Disease"
                ].ne("")
                & disease_gender[
                    "Gender"
                ].ne("")
                & disease_gender[
                    "Disease"
                ].ne("nan")
                & disease_gender[
                    "Gender"
                ].ne("nan")
            ]
        )

        if not disease_gender.empty:

            disease_totals = (
                disease_gender[
                    "Disease"
                ]
                .value_counts()
                .head(10)
            )

            top_diseases = (
                disease_totals.index
                .tolist()
            )

            top_df = (
                disease_gender[
                    disease_gender[
                        "Disease"
                    ].isin(
                        top_diseases
                    )
                ]
            )

            chart_long = (
                top_df
                .groupby(
                    [
                        "Disease",
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
                x_column="Disease",
                group_column="Gender",
                value_column="Records",
                x_order=top_diseases,
                height=480,
            )

            disease_gender_table = (
                pd.crosstab(
                    top_df[
                        "Disease"
                    ],
                    top_df[
                        "Gender"
                    ],
                )
                .reindex(
                    top_diseases
                )
            )

            st.caption(
                "The chart displays the top 10 diseases "
                "by total records within the selected filters."
            )

            st.dataframe(
                disease_gender_table
                .reset_index(),
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Disease and Gender cross-analysis "
                "is not available."
            )

    else:

        st.info(
            "Disease and Gender columns are required."
        )

    # ========================================================
    # 10. DEMOGRAPHIC DATA QUALITY
    # ========================================================

    st.divider()

    st.markdown(
        "### 10. ℹ️ Demographic Data Quality"
    )

    missing_age = 0
    invalid_age = 0
    missing_gender = 0
    missing_age_group = 0

    if "Age" in df.columns:

        raw_age = df[
            "Age"
        ]

        age_numeric = pd.to_numeric(
            raw_age,
            errors="coerce",
        )

        missing_age = int(
            age_numeric
            .isna()
            .sum()
        )

        invalid_age = int(
            (
                age_numeric.notna()
                & ~age_numeric.between(
                    0,
                    120,
                )
            )
            .sum()
        )

    if "Gender" in df.columns:

        gender_values = (
            _standardize_gender(
                df["Gender"]
            )
        )

        missing_gender = int(
            (
                gender_values.eq("")
                | gender_values.eq("nan")
                | gender_values.eq("NaT")
            )
            .sum()
        )

    if "Age Group" in df.columns:

        age_group_values = (
            _standardize_age_group(
                df["Age Group"]
            )
        )

        missing_age_group = int(
            (
                age_group_values.eq("")
                | age_group_values.eq("nan")
                | age_group_values.eq("NaT")
            )
            .sum()
        )

    quality_table = pd.DataFrame(
        {
            "Indicator": [
                "Total Records",
                "Missing Age",
                "Invalid Age",
                "Missing Gender",
                "Missing Age Group",
            ],
            "Count": [
                total_records,
                missing_age,
                invalid_age,
                missing_gender,
                missing_age_group,
            ],
        }
    )

    quality_table[
        "Percentage"
    ] = (
        quality_table[
            "Count"
        ]
        / max(
            total_records,
            1,
        )
        * 100
    ).round(2)

    quality_display = (
        quality_table.copy()
    )

    quality_display[
        "Percentage"
    ] = (
        quality_display[
            "Percentage"
        ]
        .map(
            lambda x: (
                f"{x:.2f}%"
            )
        )
    )

    st.dataframe(
        quality_display,
        use_container_width=True,
        hide_index=True,
    )
