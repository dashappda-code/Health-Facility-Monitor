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

PATHOGEN_COLUMN = "Test Performed Pathogen Name"

INVALID_TEXT_VALUES = {
    "",
    "nan",
    "nat",
    "none",
    "null",
}


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


def _valid_text_mask(series):
    if series is None:
        return pd.Series(dtype="bool")

    cleaned = (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return ~cleaned.str.lower().isin(
        INVALID_TEXT_VALUES
    )


def _clean_valid_series(df, column):
    series = _clean_text(
        df,
        column,
    )

    if series.empty:
        return series

    return series[
        _valid_text_mask(series)
    ]


# ============================================================
# AGE GROUP STANDARDISATION
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
        "Below 1 Years": "<1",
        "below 1 years": "<1",
        "0": "<1",
        "0 year": "<1",
        "0 years": "<1",
        "< 1": "<1",
        "<1 year": "<1",
        "< 1 year": "<1",
        "< 1 Year": "<1",
        "<1 Year": "<1",
    }

    values = values.replace(
        replacement_map
    )

    return values


def _get_age_group_order(values):

    values = (
        pd.Series(values)
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[
        ~values.str.lower().isin(
            INVALID_TEXT_VALUES
        )
    ]

    available = [
        value
        for value in AGE_GROUP_ORDER
        if value in values.tolist()
    ]

    remaining = sorted(
        [
            value
            for value in values.unique()
            if value not in AGE_GROUP_ORDER
        ]
    )

    return available + remaining


def _age_group_sort(
    df,
    column="Age Group",
):

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return df

    result = df.copy()

    result[column] = (
        _standardize_age_group(
            result[column]
        )
    )

    final_order = (
        _get_age_group_order(
            result[column]
        )
    )

    if not final_order:
        return result

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
# GENDER STANDARDISATION
# ============================================================

def _standardize_gender_value(value):

    if pd.isna(value):
        return ""

    text = str(value).strip()

    if not text:
        return ""

    lower = text.lower()

    if lower in INVALID_TEXT_VALUES:
        return ""

    male_values = {
        "male",
        "m",
        "man",
        "boy",
    }

    female_values = {
        "female",
        "f",
        "woman",
        "girl",
    }

    transgender_values = {
        "transgender",
        "trans gender",
        "trans",
        "tg",
        "third gender",
        "thirdgender",
    }

    if lower in male_values:
        return "Male"

    if lower in female_values:
        return "Female"

    if lower in transgender_values:
        return "Transgender"

    return text


def _standardize_gender_series(series):

    return (
        series
        .fillna("")
        .apply(
            _standardize_gender_value
        )
    )


# ============================================================
# CROSS-TABLE HELPERS
# ============================================================

def _prepare_cross_data(
    df,
    column1,
    column2,
):

    if (
        df is None
        or df.empty
        or column1 not in df.columns
        or column2 not in df.columns
    ):
        return pd.DataFrame()

    result = df[
        [
            column1,
            column2,
        ]
    ].copy()

    result[column1] = (
        result[column1]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    result[column2] = (
        result[column2]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    result = result[
        _valid_text_mask(
            result[column1]
        )
        & _valid_text_mask(
            result[column2]
        )
    ]

    return result


def _top_categories(
    dataframe,
    category_column,
    top_n=10,
):

    if (
        dataframe is None
        or dataframe.empty
        or category_column not in dataframe.columns
    ):
        return []

    return (
        dataframe[
            category_column
        ]
        .value_counts()
        .head(top_n)
        .index
        .tolist()
    )


# ============================================================
# POPULATION PYRAMID HELPERS
# ============================================================

def _prepare_pyramid_data(df):

    if (
        df is None
        or df.empty
        or "Age Group" not in df.columns
        or "Gender" not in df.columns
    ):
        return (
            pd.DataFrame(),
            pd.DataFrame(),
        )

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
        _standardize_gender_series(
            pyramid_df["Gender"]
        )
    )

    pyramid_df = pyramid_df[
        _valid_text_mask(
            pyramid_df["Age Group"]
        )
        & _valid_text_mask(
            pyramid_df["Gender"]
        )
    ].copy()

    if pyramid_df.empty:
        return (
            pd.DataFrame(),
            pd.DataFrame(),
        )

    age_order = (
        _get_age_group_order(
            pyramid_df["Age Group"]
        )
    )

    classic_df = pyramid_df[
        pyramid_df["Gender"].isin(
            [
                "Male",
                "Female",
            ]
        )
    ].copy()

    other_df = pyramid_df[
        ~pyramid_df["Gender"].isin(
            [
                "Male",
                "Female",
            ]
        )
    ].copy()

    if classic_df.empty:
        pyramid_table = pd.DataFrame()

    else:

        pyramid_table = (
            pd.crosstab(
                classic_df["Age Group"],
                classic_df["Gender"],
            )
            .reindex(
                age_order,
                fill_value=0,
            )
        )

        for column in [
            "Male",
            "Female",
        ]:
            if column not in pyramid_table.columns:
                pyramid_table[column] = 0

        pyramid_table = (
            pyramid_table[
                [
                    "Male",
                    "Female",
                ]
            ]
            .reset_index()
        )

    if other_df.empty:

        other_table = pd.DataFrame()

    else:

        other_table = (
            other_df
            .groupby(
                [
                    "Age Group",
                    "Gender",
                ],
                observed=False,
            )
            .size()
            .reset_index(
                name="Records"
            )
        )

        other_table["Age Group"] = (
            pd.Categorical(
                other_table["Age Group"],
                categories=age_order,
                ordered=True,
            )
        )

        other_table = (
            other_table
            .sort_values(
                [
                    "Age Group",
                    "Gender",
                ]
            )
            .reset_index(drop=True)
        )

    return (
        pyramid_table,
        other_table,
    )


def _render_population_pyramid(
    pyramid_df,
):

    if (
        pyramid_df is None
        or pyramid_df.empty
    ):
        st.info(
            "Male and Female age-group data are not "
            "available for the population pyramid."
        )
        return

    chart_df = pyramid_df.copy()

    age_order = (
        _get_age_group_order(
            chart_df["Age Group"]
        )
    )

    chart_df["Male Plot"] = (
        -chart_df["Male"]
    )

    chart_df["Female Plot"] = (
        chart_df["Female"]
    )

    max_value = max(
        int(
            chart_df["Male"].max()
        ),
        int(
            chart_df["Female"].max()
        ),
        1,
    )

    # Add some space for labels.
    scale_limit = max_value * 1.20

    male_chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            y=alt.Y(
                "Age Group:N",
                sort=age_order,
                title="Age Group",
            ),
            x=alt.X(
                "Male Plot:Q",
                title="Records",
                scale=alt.Scale(
                    domain=[
                        -scale_limit,
                        scale_limit,
                    ]
                ),
                axis=alt.Axis(
                    labelExpr="abs(datum.value)"
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "Age Group:N",
                    title="Age Group",
                ),
                alt.Tooltip(
                    "Male:Q",
                    title="Male",
                    format=",",
                ),
            ],
        )
    )

    female_chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            y=alt.Y(
                "Age Group:N",
                sort=age_order,
            ),
            x=alt.X(
                "Female Plot:Q",
                scale=alt.Scale(
                    domain=[
                        -scale_limit,
                        scale_limit,
                    ]
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "Age Group:N",
                    title="Age Group",
                ),
                alt.Tooltip(
                    "Female:Q",
                    title="Female",
                    format=",",
                ),
            ],
        )
    )

    pyramid_chart = (
        male_chart
        + female_chart
    ).properties(
        height=430,
    )

    if data_labels_enabled():

        male_labels = (
            alt.Chart(chart_df)
            .mark_text(
                align="right",
                dx=-5,
                fontWeight="bold",
                fontSize=11,
            )
            .encode(
                y=alt.Y(
                    "Age Group:N",
                    sort=age_order,
                ),
                x=alt.X(
                    "Male Plot:Q",
                    scale=alt.Scale(
                        domain=[
                            -scale_limit,
                            scale_limit,
                        ]
                    ),
                ),
                text=alt.Text(
                    "Male:Q",
                    format=",",
                ),
            )
        )

        female_labels = (
            alt.Chart(chart_df)
            .mark_text(
                align="left",
                dx=5,
                fontWeight="bold",
                fontSize=11,
            )
            .encode(
                y=alt.Y(
                    "Age Group:N",
                    sort=age_order,
                ),
                x=alt.X(
                    "Female Plot:Q",
                    scale=alt.Scale(
                        domain=[
                            -scale_limit,
                            scale_limit,
                        ]
                    ),
                ),
                text=alt.Text(
                    "Female:Q",
                    format=",",
                ),
            )
        )

        pyramid_chart = (
            pyramid_chart
            + male_labels
            + female_labels
        )

    st.altair_chart(
        pyramid_chart,
        use_container_width=True,
    )

    st.caption(
        "Male records are displayed on the left and "
        "Female records on the right. Axis labels show "
        "absolute record counts."
    )


# ============================================================
# PYRAMID FILTER
# ============================================================

def _render_interactive_pyramid(df):

    available_types = [
        "Overall",
    ]

    filter_map = {}

    if (
        "Disease" in df.columns
        and not _clean_valid_series(
            df,
            "Disease",
        ).empty
    ):
        available_types.append(
            "Disease"
        )
        filter_map[
            "Disease"
        ] = "Disease"

    if (
        "Facility Name" in df.columns
        and not _clean_valid_series(
            df,
            "Facility Name",
        ).empty
    ):
        available_types.append(
            "Facility"
        )
        filter_map[
            "Facility"
        ] = "Facility Name"

    elif (
        "Facility" in df.columns
        and not _clean_valid_series(
            df,
            "Facility",
        ).empty
    ):
        available_types.append(
            "Facility"
        )
        filter_map[
            "Facility"
        ] = "Facility"

    if (
        "Ward" in df.columns
        and not _clean_valid_series(
            df,
            "Ward",
        ).empty
    ):
        available_types.append(
            "Ward"
        )
        filter_map[
            "Ward"
        ] = "Ward"

    if (
        "OPD/IPD" in df.columns
        and not _clean_valid_series(
            df,
            "OPD/IPD",
        ).empty
    ):
        available_types.append(
            "OPD/IPD"
        )
        filter_map[
            "OPD/IPD"
        ] = "OPD/IPD"

    if (
        PATHOGEN_COLUMN in df.columns
        and not _clean_valid_series(
            df,
            PATHOGEN_COLUMN,
        ).empty
    ):
        available_types.append(
            "Pathogen"
        )
        filter_map[
            "Pathogen"
        ] = PATHOGEN_COLUMN

    col1, col2 = st.columns(
        [1, 2],
        gap="large",
    )

    with col1:

        analysis_type = (
            st.selectbox(
                "Pyramid Analysis By",
                options=available_types,
                key=(
                    "demographic_pyramid_"
                    "analysis_type"
                ),
            )
        )

    pyramid_source = df.copy()

    selected_value = None

    if analysis_type != "Overall":

        filter_column = (
            filter_map.get(
                analysis_type
            )
        )

        if (
            filter_column
            and filter_column in df.columns
        ):

            options = (
                _clean_valid_series(
                    df,
                    filter_column,
                )
                .value_counts()
                .index
                .tolist()
            )

            if options:

                with col2:

                    selected_value = (
                        st.selectbox(
                            (
                                f"Select "
                                f"{analysis_type}"
                            ),
                            options=options,
                            key=(
                                "demographic_pyramid_"
                                f"{analysis_type.lower()}_"
                                "value"
                            ),
                        )
                    )

                source_values = (
                    df[
                        filter_column
                    ]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                )

                pyramid_source = df[
                    source_values.eq(
                        str(
                            selected_value
                        ).strip()
                    )
                ].copy()

    pyramid_table, other_table = (
        _prepare_pyramid_data(
            pyramid_source
        )
    )

    pyramid_records = len(
        pyramid_source
    )

    male_count = 0
    female_count = 0

    if not pyramid_table.empty:

        male_count = int(
            pyramid_table[
                "Male"
            ].sum()
        )

        female_count = int(
            pyramid_table[
                "Female"
            ].sum()
        )

    other_count = 0

    if not other_table.empty:

        other_count = int(
            other_table[
                "Records"
            ].sum()
        )

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:
        st.metric(
            "Selected Records",
            f"{pyramid_records:,}",
        )

    with c2:
        st.metric(
            "Male",
            f"{male_count:,}",
        )

    with c3:
        st.metric(
            "Female",
            f"{female_count:,}",
        )

    with c4:
        st.metric(
            "Other Gender Categories",
            f"{other_count:,}",
        )

    if selected_value is not None:

        st.caption(
            (
                f"Population pyramid for "
                f"{analysis_type}: "
                f"{selected_value}"
            )
        )

    _render_population_pyramid(
        pyramid_table
    )

    if not pyramid_table.empty:

        display_pyramid = (
            pyramid_table.copy()
        )

        display_pyramid[
            "Total"
        ] = (
            display_pyramid[
                "Male"
            ]
            + display_pyramid[
                "Female"
            ]
        )

        st.markdown(
            "**Age Group-wise Male / Female Records**"
        )

        st.dataframe(
            display_pyramid,
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # TRANSGENDER / OTHER GENDER CATEGORIES
    # --------------------------------------------------------

    if not other_table.empty:

        st.markdown(
            "**Additional Gender Categories**"
        )

        st.caption(
            "Gender categories other than Male and Female "
            "are reported separately so that small counts "
            "are not hidden by the population-pyramid scale."
        )

        other_summary = (
            other_table
            .groupby(
                "Gender",
                observed=False,
            )["Records"]
            .sum()
            .reset_index()
            .sort_values(
                "Records",
                ascending=False,
            )
        )

        other_summary[
            "Percentage of Selected Records"
        ] = (
            other_summary[
                "Records"
            ]
            / max(
                pyramid_records,
                1,
            )
            * 100
        ).round(3)

        display_other_summary = (
            other_summary.copy()
        )

        display_other_summary[
            "Percentage of Selected Records"
        ] = (
            display_other_summary[
                "Percentage of Selected Records"
            ]
            .map(
                lambda x: f"{x:.3f}%"
            )
        )

        st.dataframe(
            display_other_summary,
            use_container_width=True,
            hide_index=True,
        )

        with st.expander(
            "View Age Group-wise Additional Gender Details"
        ):

            st.dataframe(
                other_table,
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# GENERIC TOP CATEGORY CROSS ANALYSIS
# ============================================================

def _render_top_category_cross_analysis(
    df,
    primary_column,
    secondary_column,
    top_n=10,
    caption=None,
):

    cross_df = (
        _prepare_cross_data(
            df,
            primary_column,
            secondary_column,
        )
    )

    if cross_df.empty:
        st.info(
            (
                f"{primary_column} and "
                f"{secondary_column} cross-analysis "
                "is not available."
            )
        )
        return

    if primary_column == "Age Group":

        cross_df[
            primary_column
        ] = _standardize_age_group(
            cross_df[
                primary_column
            ]
        )

    if secondary_column == "Age Group":

        cross_df[
            secondary_column
        ] = _standardize_age_group(
            cross_df[
                secondary_column
            ]
        )

    if primary_column == "Gender":

        cross_df[
            primary_column
        ] = _standardize_gender_series(
            cross_df[
                primary_column
            ]
        )

    if secondary_column == "Gender":

        cross_df[
            secondary_column
        ] = _standardize_gender_series(
            cross_df[
                secondary_column
            ]
        )

    top_values = (
        _top_categories(
            cross_df,
            primary_column,
            top_n=top_n,
        )
    )

    if top_values:

        cross_df = cross_df[
            cross_df[
                primary_column
            ].isin(
                top_values
            )
        ]

    cross_table = pd.crosstab(
        cross_df[
            primary_column
        ],
        cross_df[
            secondary_column
        ],
    )

    if primary_column == "Age Group":

        order = (
            _get_age_group_order(
                cross_table.index
            )
        )

        cross_table = (
            cross_table.reindex(
                order
            )
        )

    else:

        total_order = (
            cross_table
            .sum(axis=1)
            .sort_values(
                ascending=False
            )
            .index
        )

        cross_table = (
            cross_table.loc[
                total_order
            ]
        )

    render_bar_chart(
        cross_table,
        use_container_width=True,
    )

    if caption:
        st.caption(
            caption
        )

    st.dataframe(
        cross_table.reset_index(),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# MAIN PAGE
# ============================================================

def render_demographics(df):

    st.subheader(
        "👥 Demographic Analysis"
    )

    if df is None or df.empty:

        st.warning(
            "No records available for the selected filters."
        )
        return

    st.caption(
        "Age, age-group, gender, disease and OPD/IPD "
        "demographic analysis based on the selected "
        "Global Dashboard Filters."
    )

    total_records = len(df)

    # ========================================================
    # 1. DEMOGRAPHIC SUMMARY
    # ========================================================

    st.markdown(
        "### 1. 📊 Demographic Summary"
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

        mean_age = (
            valid_age.mean()
        )

        median_age = (
            valid_age.median()
        )

        min_age = (
            valid_age.min()
        )

        max_age = (
            valid_age.max()
        )

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

    if "Age Group" in df.columns:

        age_group = (
            _standardize_age_group(
                df["Age Group"]
            )
        )

        age_group = age_group[
            _valid_text_mask(
                age_group
            )
        ]

        if not age_group.empty:

            st.divider()

            st.markdown(
                "### 2. 🎂 Age Group-wise Distribution"
            )

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

            chart_df = (
                age_group_counts.copy()
            )

            age_order = (
                _get_age_group_order(
                    chart_df[
                        "Age Group"
                    ]
                )
            )

            chart_df[
                "Age Group"
            ] = pd.Categorical(
                chart_df[
                    "Age Group"
                ],
                categories=age_order,
                ordered=True,
            )

            chart_df = (
                chart_df.sort_values(
                    "Age Group"
                )
            )

            age_chart = (
                alt.Chart(
                    chart_df
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Age Group:N",
                        sort=age_order,
                        title="Age Group",
                    ),
                    y=alt.Y(
                        "Records:Q",
                        title="Records",
                    ),
                    color=alt.Color(
                        "Age Group:N",
                        scale=alt.Scale(
                            domain=age_order
                        ),
                        legend=None,
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "Age Group:N",
                            title="Age Group",
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

            if data_labels_enabled():

                age_labels = (
                    alt.Chart(
                        chart_df
                    )
                    .mark_text(
                        dy=-8,
                        fontWeight="bold",
                        fontSize=13,
                    )
                    .encode(
                        x=alt.X(
                            "Age Group:N",
                            sort=age_order,
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
                    age_chart
                    + age_labels
                )

            st.altair_chart(
                age_chart,
                use_container_width=True,
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
                    lambda x: f"{x:.2f}%"
                )
            )

            st.dataframe(
                display_age_group,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 3. GENDER-WISE DISTRIBUTION
    # ========================================================

    if "Gender" in df.columns:

        gender = (
            _standardize_gender_series(
                df["Gender"]
            )
        )

        gender = gender[
            _valid_text_mask(
                gender
            )
        ]

        if not gender.empty:

            st.divider()

            st.markdown(
                "### 3. ⚧ Gender-wise Distribution"
            )

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
            ).round(3)

            left, right = st.columns(
                [1.5, 1],
                gap="large",
            )

            with left:

                render_bar_chart(
                    gender_counts.set_index(
                        "Gender"
                    )["Records"],
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
                        lambda x: f"{x:.3f}%"
                    )
                )

                st.dataframe(
                    display_gender,
                    use_container_width=True,
                    hide_index=True,
                )

    # ========================================================
    # 4. AGE-WISE DISTRIBUTION
    # ========================================================

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

            st.divider()

            st.markdown(
                "### 4. 📈 Age-wise Distribution"
            )

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

            render_line_chart(
                age_counts.set_index(
                    "Age"
                )["Records"],
                use_container_width=True,
            )

            st.dataframe(
                age_counts,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 5. AGE-GENDER POPULATION PYRAMID
    # ========================================================

    if (
        "Age Group" in df.columns
        and "Gender" in df.columns
    ):

        pyramid_test = df[
            [
                "Age Group",
                "Gender",
            ]
        ].copy()

        if not pyramid_test.empty:

            st.divider()

            st.markdown(
                "### 5. 👥 Age–Gender Population Pyramid"
            )

            st.caption(
                "Interactive Male–Female age-group pyramid. "
                "Use the controls below to analyse the overall "
                "population or selected Disease, Facility, Ward, "
                "OPD/IPD or Pathogen."
            )

            _render_interactive_pyramid(
                df
            )

    # ========================================================
    # 6. GENDER × AGE GROUP
    # ========================================================

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
            _standardize_gender_series(
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
            _valid_text_mask(
                cross_df[
                    "Gender"
                ]
            )
            & _valid_text_mask(
                cross_df[
                    "Age Group"
                ]
            )
        ]

        if not cross_df.empty:

            st.divider()

            st.markdown(
                "### 6. 👥 Gender × Age Group"
            )

            gender_age = (
                pd.crosstab(
                    cross_df[
                        "Age Group"
                    ],
                    cross_df[
                        "Gender"
                    ],
                )
            )

            age_order = (
                _get_age_group_order(
                    gender_age.index
                )
            )

            gender_age = (
                gender_age.reindex(
                    age_order
                )
            )

            render_bar_chart(
                gender_age,
                use_container_width=True,
            )

            st.dataframe(
                gender_age.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 7. DISEASE × AGE GROUP
    # ========================================================

    if (
        "Disease" in df.columns
        and "Age Group" in df.columns
    ):

        disease_age = (
            _prepare_cross_data(
                df,
                "Disease",
                "Age Group",
            )
        )

        if not disease_age.empty:

            st.divider()

            st.markdown(
                "### 7. 🦠 Disease × Age Group"
            )

            disease_age[
                "Age Group"
            ] = (
                _standardize_age_group(
                    disease_age[
                        "Age Group"
                    ]
                )
            )

            top_diseases = (
                disease_age[
                    "Disease"
                ]
                .value_counts()
                .head(10)
                .index
            )

            disease_age = (
                disease_age[
                    disease_age[
                        "Disease"
                    ].isin(
                        top_diseases
                    )
                ]
            )

            disease_age_table = (
                pd.crosstab(
                    disease_age[
                        "Disease"
                    ],
                    disease_age[
                        "Age Group"
                    ],
                )
            )

            age_columns = (
                _get_age_group_order(
                    disease_age_table.columns
                )
            )

            disease_age_table = (
                disease_age_table.reindex(
                    columns=age_columns,
                    fill_value=0,
                )
            )

            disease_order = (
                disease_age_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .index
            )

            disease_age_table = (
                disease_age_table.loc[
                    disease_order
                ]
            )

            render_bar_chart(
                disease_age_table,
                use_container_width=True,
            )

            st.caption(
                "The chart displays the top 10 diseases "
                "by total records within the selected filters."
            )

            st.dataframe(
                disease_age_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 8. DISEASE × GENDER
    # ========================================================

    if (
        "Disease" in df.columns
        and "Gender" in df.columns
    ):

        disease_gender = (
            _prepare_cross_data(
                df,
                "Disease",
                "Gender",
            )
        )

        if not disease_gender.empty:

            st.divider()

            st.markdown(
                "### 8. 🦠 Disease × Gender"
            )

            disease_gender[
                "Gender"
            ] = (
                _standardize_gender_series(
                    disease_gender[
                        "Gender"
                    ]
                )
            )

            top_diseases = (
                disease_gender[
                    "Disease"
                ]
                .value_counts()
                .head(10)
                .index
            )

            disease_gender = (
                disease_gender[
                    disease_gender[
                        "Disease"
                    ].isin(
                        top_diseases
                    )
                ]
            )

            disease_gender_table = (
                pd.crosstab(
                    disease_gender[
                        "Disease"
                    ],
                    disease_gender[
                        "Gender"
                    ],
                )
            )

            disease_order = (
                disease_gender_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .index
            )

            disease_gender_table = (
                disease_gender_table.loc[
                    disease_order
                ]
            )

            render_bar_chart(
                disease_gender_table,
                use_container_width=True,
            )

            st.caption(
                "The chart displays the top 10 diseases "
                "by total records within the selected filters."
            )

            st.dataframe(
                disease_gender_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 9. OPD / IPD DEMOGRAPHIC DISTRIBUTION
    # ========================================================

    if "OPD/IPD" in df.columns:

        opd = (
            _clean_valid_series(
                df,
                "OPD/IPD",
            )
        )

        if not opd.empty:

            st.divider()

            st.markdown(
                "### 9. 🏨 OPD / IPD Demographic Distribution"
            )

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

            c1, c2 = st.columns(
                [1.5, 1],
                gap="large",
            )

            with c1:

                render_bar_chart(
                    opd_counts.set_index(
                        "OPD/IPD"
                    )["Records"],
                    use_container_width=True,
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
                        lambda x: f"{x:.2f}%"
                    )
                )

                st.dataframe(
                    display_opd,
                    use_container_width=True,
                    hide_index=True,
                )

    # ========================================================
    # 10. AGE GROUP × OPD/IPD
    # ========================================================

    if (
        "Age Group" in df.columns
        and "OPD/IPD" in df.columns
    ):

        age_opd = (
            _prepare_cross_data(
                df,
                "Age Group",
                "OPD/IPD",
            )
        )

        if not age_opd.empty:

            st.divider()

            st.markdown(
                "### 10. 🎂 Age Group × OPD/IPD"
            )

            age_opd[
                "Age Group"
            ] = (
                _standardize_age_group(
                    age_opd[
                        "Age Group"
                    ]
                )
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

            age_order = (
                _get_age_group_order(
                    age_opd_table.index
                )
            )

            age_opd_table = (
                age_opd_table.reindex(
                    age_order
                )
            )

            chart_df = (
                age_opd_table
                .reset_index()
            )

            chart_long = (
                chart_df.melt(
                    id_vars=[
                        "Age Group"
                    ],
                    var_name="OPD/IPD",
                    value_name="Records",
                )
            )

            age_opd_chart = (
                alt.Chart(
                    chart_long
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Age Group:N",
                        sort=age_order,
                        title="Age Group",
                    ),
                    y=alt.Y(
                        "Records:Q",
                        title="Records",
                    ),
                    color=alt.Color(
                        "OPD/IPD:N",
                        title="OPD/IPD",
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "Age Group:N",
                            title="Age Group",
                        ),
                        alt.Tooltip(
                            "OPD/IPD:N",
                            title="OPD/IPD",
                        ),
                        alt.Tooltip(
                            "Records:Q",
                            title="Records",
                            format=",",
                        ),
                    ],
                )
                .properties(
                    height=450
                )
            )

            if data_labels_enabled():

                age_opd_labels = (
                    alt.Chart(
                        chart_long
                    )
                    .mark_text(
                        dy=-8,
                        fontWeight="bold",
                    )
                    .encode(
                        x=alt.X(
                            "Age Group:N",
                            sort=age_order,
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

                age_opd_chart = (
                    age_opd_chart
                    + age_opd_labels
                )

            st.altair_chart(
                age_opd_chart,
                use_container_width=True,
            )

            st.dataframe(
                chart_df,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 11. GENDER × OPD/IPD
    # ========================================================

    if (
        "Gender" in df.columns
        and "OPD/IPD" in df.columns
    ):

        gender_opd = (
            _prepare_cross_data(
                df,
                "Gender",
                "OPD/IPD",
            )
        )

        if not gender_opd.empty:

            st.divider()

            st.markdown(
                "### 11. ⚧ Gender × OPD/IPD"
            )

            gender_opd[
                "Gender"
            ] = (
                _standardize_gender_series(
                    gender_opd[
                        "Gender"
                    ]
                )
            )

            gender_opd_table = (
                pd.crosstab(
                    gender_opd[
                        "Gender"
                    ],
                    gender_opd[
                        "OPD/IPD"
                    ],
                )
            )

            gender_order = (
                gender_opd_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .index
            )

            gender_opd_table = (
                gender_opd_table.loc[
                    gender_order
                ]
            )

            render_bar_chart(
                gender_opd_table,
                use_container_width=True,
            )

            st.dataframe(
                gender_opd_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 12. DISEASE × OPD/IPD
    # ========================================================

    if (
        "Disease" in df.columns
        and "OPD/IPD" in df.columns
    ):

        disease_opd = (
            _prepare_cross_data(
                df,
                "Disease",
                "OPD/IPD",
            )
        )

        if not disease_opd.empty:

            st.divider()

            st.markdown(
                "### 12. 🦠 Disease × OPD/IPD"
            )

            top_diseases = (
                disease_opd[
                    "Disease"
                ]
                .value_counts()
                .head(10)
                .index
            )

            disease_opd = (
                disease_opd[
                    disease_opd[
                        "Disease"
                    ].isin(
                        top_diseases
                    )
                ]
            )

            disease_opd_table = (
                pd.crosstab(
                    disease_opd[
                        "Disease"
                    ],
                    disease_opd[
                        "OPD/IPD"
                    ],
                )
            )

            disease_order = (
                disease_opd_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .index
            )

            disease_opd_table = (
                disease_opd_table.loc[
                    disease_order
                ]
            )

            render_bar_chart(
                disease_opd_table,
                use_container_width=True,
            )

            st.caption(
                "The chart displays the top 10 diseases "
                "by total records within the selected filters."
            )

            st.dataframe(
                disease_opd_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 13. PATHOGEN × AGE GROUP
    # ========================================================

    if (
        PATHOGEN_COLUMN in df.columns
        and "Age Group" in df.columns
    ):

        pathogen_age = (
            _prepare_cross_data(
                df,
                PATHOGEN_COLUMN,
                "Age Group",
            )
        )

        if not pathogen_age.empty:

            st.divider()

            st.markdown(
                "### 13. 🧪 Pathogen × Age Group"
            )

            pathogen_age[
                "Age Group"
            ] = (
                _standardize_age_group(
                    pathogen_age[
                        "Age Group"
                    ]
                )
            )

            top_pathogens = (
                pathogen_age[
                    PATHOGEN_COLUMN
                ]
                .value_counts()
                .head(10)
                .index
            )

            pathogen_age = (
                pathogen_age[
                    pathogen_age[
                        PATHOGEN_COLUMN
                    ].isin(
                        top_pathogens
                    )
                ]
            )

            pathogen_age_table = (
                pd.crosstab(
                    pathogen_age[
                        PATHOGEN_COLUMN
                    ],
                    pathogen_age[
                        "Age Group"
                    ],
                )
            )

            age_columns = (
                _get_age_group_order(
                    pathogen_age_table.columns
                )
            )

            pathogen_age_table = (
                pathogen_age_table.reindex(
                    columns=age_columns,
                    fill_value=0,
                )
            )

            pathogen_order = (
                pathogen_age_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .index
            )

            pathogen_age_table = (
                pathogen_age_table.loc[
                    pathogen_order
                ]
            )

            render_bar_chart(
                pathogen_age_table,
                use_container_width=True,
            )

            st.caption(
                "The chart displays the top 10 reported "
                "pathogens by total records within the "
                "selected filters."
            )

            st.dataframe(
                pathogen_age_table.reset_index(),
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 14. DEMOGRAPHIC DATA QUALITY
    # ========================================================

    st.divider()

    st.markdown(
        "### 14. ℹ️ Demographic Data Quality"
    )

    missing_age = total_records
    invalid_age = 0
    missing_gender = total_records
    missing_age_group = total_records

    if "Age" in df.columns:

        raw_age = (
            df["Age"]
        )

        age_numeric = pd.to_numeric(
            raw_age,
            errors="coerce",
        )

        missing_age = int(
            raw_age.isna().sum()
            + (
                raw_age
                .fillna("")
                .astype(str)
                .str.strip()
                .eq("")
                & raw_age.notna()
            ).sum()
        )

        invalid_age = int(
            (
                age_numeric.notna()
                & ~age_numeric.between(
                    0,
                    120,
                )
            ).sum()
        )

        non_numeric_age = int(
            (
                age_numeric.isna()
                & _valid_text_mask(
                    raw_age
                )
            ).sum()
        )

        invalid_age += (
            non_numeric_age
        )

    if "Gender" in df.columns:

        gender_values = (
            _standardize_gender_series(
                df["Gender"]
            )
        )

        missing_gender = int(
            (
                ~_valid_text_mask(
                    gender_values
                )
            ).sum()
        )

    if "Age Group" in df.columns:

        age_group_values = (
            _standardize_age_group(
                df["Age Group"]
            )
        )

        missing_age_group = int(
            (
                ~_valid_text_mask(
                    age_group_values
                )
            ).sum()
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

    # Total Records is not a missing-data percentage.
    quality_table.loc[
        quality_table[
            "Indicator"
        ].eq(
            "Total Records"
        ),
        "Percentage",
    ] = 100.00

    display_quality = (
        quality_table.copy()
    )

    display_quality[
        "Percentage"
    ] = (
        display_quality[
            "Percentage"
        ]
        .map(
            lambda x: f"{x:.2f}%"
        )
    )

    st.dataframe(
        display_quality,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # COMPLETENESS METRICS
    # --------------------------------------------------------

    c1, c2, c3 = (
        st.columns(3)
    )

    age_complete = max(
        total_records
        - missing_age
        - invalid_age,
        0,
    )

    gender_complete = max(
        total_records
        - missing_gender,
        0,
    )

    age_group_complete = max(
        total_records
        - missing_age_group,
        0,
    )

    with c1:

        st.metric(
            "Valid Age",
            (
                f"{age_complete:,} "
                f"({age_complete / max(total_records, 1) * 100:.1f}%)"
            ),
        )

    with c2:

        st.metric(
            "Gender Available",
            (
                f"{gender_complete:,} "
                f"({gender_complete / max(total_records, 1) * 100:.1f}%)"
            ),
        )

    with c3:

        st.metric(
            "Age Group Available",
            (
                f"{age_group_complete:,} "
                f"({age_group_complete / max(total_records, 1) * 100:.1f}%)"
            ),
        )
