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

GENDER_COLORS = {
    "Male": "#2F80ED",
    "Female": "#E85AAD",
    "Transgender": "#8E44AD",
    "Other": "#7F8C8D",
    "Unknown": "#95A5A6",
}


# ============================================================
# HELPER FUNCTIONS
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

    values = values.replace(
        replacement_map
    )

    return values


def _get_age_group_order(series):

    values = (
        pd.Series(series)
        .dropna()
        .astype(str)
        .str.strip()
    )

    available = [
        value
        for value in AGE_GROUP_ORDER
        if value in values.tolist()
    ]

    remaining = sorted(
        [
            value
            for value in values.unique()
            if value
            and value not in AGE_GROUP_ORDER
        ]
    )

    return (
        available
        + remaining
    )


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

    final_order = (
        _get_age_group_order(
            result[column]
        )
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


def _standardize_gender(series):

    values = (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )

    def convert(value):

        text = str(value).strip()
        lower = text.lower()

        if lower in {
            "male",
            "m",
            "man",
        }:
            return "Male"

        if lower in {
            "female",
            "f",
            "woman",
        }:
            return "Female"

        if lower in {
            "transgender",
            "trans",
            "third gender",
            "thirdgender",
            "tg",
        }:
            return "Transgender"

        if lower in {
            "other",
            "others",
        }:
            return "Other"

        if lower in {
            "",
            "nan",
            "nat",
            "none",
            "unknown",
            "not known",
        }:
            return ""

        return text

    return values.apply(
        convert
    )


# ============================================================
# POPULATION PYRAMID
# ============================================================

def _render_population_pyramid(df):

    if (
        df is None
        or df.empty
        or "Age Group" not in df.columns
        or "Gender" not in df.columns
    ):

        st.info(
            "Age Group and Gender information is not "
            "available for the population pyramid."
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
    ].copy()

    if pyramid_df.empty:

        st.info(
            "Valid Age Group and Gender information "
            "is not available for the population pyramid."
        )

        return

    gender_counts = (
        pyramid_df["Gender"]
        .value_counts()
    )

    has_male = (
        gender_counts.get(
            "Male",
            0,
        )
        > 0
    )

    has_female = (
        gender_counts.get(
            "Female",
            0,
        )
        > 0
    )

    if not (
        has_male
        or has_female
    ):

        st.info(
            "Male or Female records are not available "
            "for the population pyramid."
        )

        return

    # --------------------------------------------------------
    # Male / Female pyramid
    # --------------------------------------------------------

    mf_df = pyramid_df[
        pyramid_df["Gender"].isin(
            [
                "Male",
                "Female",
            ]
        )
    ].copy()

    pyramid_table = pd.crosstab(
        mf_df["Age Group"],
        mf_df["Gender"],
    )

    if "Male" not in pyramid_table.columns:
        pyramid_table["Male"] = 0

    if "Female" not in pyramid_table.columns:
        pyramid_table["Female"] = 0

    age_order = (
        _get_age_group_order(
            pyramid_table.index
        )
    )

    pyramid_table = (
        pyramid_table
        .reindex(
            age_order,
            fill_value=0,
        )
        .reset_index()
    )

    male_df = pyramid_table[
        [
            "Age Group",
            "Male",
        ]
    ].copy()

    male_df["Gender"] = "Male"

    male_df["Records"] = (
        pd.to_numeric(
            male_df["Male"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    male_df["Plot Value"] = (
        -male_df["Records"]
    )

    female_df = pyramid_table[
        [
            "Age Group",
            "Female",
        ]
    ].copy()

    female_df["Gender"] = "Female"

    female_df["Records"] = (
        pd.to_numeric(
            female_df["Female"],
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )

    female_df["Plot Value"] = (
        female_df["Records"]
    )

    chart_df = pd.concat(
        [
            male_df[
                [
                    "Age Group",
                    "Gender",
                    "Records",
                    "Plot Value",
                ]
            ],
            female_df[
                [
                    "Age Group",
                    "Gender",
                    "Records",
                    "Plot Value",
                ]
            ],
        ],
        ignore_index=True,
    )

    max_value = max(
        int(
            chart_df["Records"].max()
        ),
        1,
    )

    scale_limit = (
        max_value
        * 1.22
    )

    gender_domain = [
        "Male",
        "Female",
    ]

    gender_range = [
        GENDER_COLORS["Male"],
        GENDER_COLORS["Female"],
    ]

    bars = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            y=alt.Y(
                "Age Group:N",
                sort=age_order,
                title="Age Group",
                axis=alt.Axis(
                    labelFontSize=11,
                    titleFontSize=12,
                ),
            ),
            x=alt.X(
                "Plot Value:Q",
                title="Records",
                scale=alt.Scale(
                    domain=[
                        -scale_limit,
                        scale_limit,
                    ],
                    nice=False,
                ),
                axis=alt.Axis(
                    labelExpr=(
                        "abs(datum.value)"
                    ),
                    labelFontSize=10,
                    titleFontSize=11,
                    grid=True,
                ),
            ),
            color=alt.Color(
                "Gender:N",
                title=None,
                scale=alt.Scale(
                    domain=gender_domain,
                    range=gender_range,
                ),
                legend=alt.Legend(
                    orient="bottom",
                    direction="horizontal",
                    columns=2,
                    labelFontSize=9,
                    symbolSize=70,
                    offset=8,
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
            height=430,
        )
    )

    centre_line = (
        alt.Chart(
            pd.DataFrame(
                {
                    "Zero": [0]
                }
            )
        )
        .mark_rule(
            strokeWidth=1.2
        )
        .encode(
            x="Zero:Q"
        )
    )

    pyramid_chart = (
        bars
        + centre_line
    )

    # --------------------------------------------------------
    # Data labels controlled by global Show Data Labels
    # --------------------------------------------------------

    if data_labels_enabled():

        male_labels = (
            alt.Chart(male_df)
            .mark_text(
                align="right",
                baseline="middle",
                dx=-5,
                fontSize=11,
                fontWeight="bold",
                color=GENDER_COLORS[
                    "Male"
                ],
            )
            .encode(
                y=alt.Y(
                    "Age Group:N",
                    sort=age_order,
                ),
                x=alt.X(
                    "Plot Value:Q",
                    scale=alt.Scale(
                        domain=[
                            -scale_limit,
                            scale_limit,
                        ],
                        nice=False,
                    ),
                ),
                text=alt.Text(
                    "Records:Q",
                    format=",",
                ),
            )
        )

        female_labels = (
            alt.Chart(female_df)
            .mark_text(
                align="left",
                baseline="middle",
                dx=5,
                fontSize=11,
                fontWeight="bold",
                color=GENDER_COLORS[
                    "Female"
                ],
            )
            .encode(
                y=alt.Y(
                    "Age Group:N",
                    sort=age_order,
                ),
                x=alt.X(
                    "Plot Value:Q",
                    scale=alt.Scale(
                        domain=[
                            -scale_limit,
                            scale_limit,
                        ],
                        nice=False,
                    ),
                ),
                text=alt.Text(
                    "Records:Q",
                    format=",",
                ),
            )
        )

        pyramid_chart = (
            pyramid_chart
            + male_labels
            + female_labels
        )

    pyramid_chart = (
        pyramid_chart
        .configure_view(
            strokeWidth=0
        )
        .configure_legend(
            labelFontSize=9,
            titleFontSize=9,
        )
    )

    st.altair_chart(
        pyramid_chart,
        use_container_width=True,
    )

    st.caption(
        "Male records are displayed on the left and "
        "Female records on the right. Axis values represent "
        "absolute record counts."
    )

    # --------------------------------------------------------
    # Display pyramid table
    # --------------------------------------------------------

    display_table = (
        pyramid_table[
            [
                "Age Group",
                "Male",
                "Female",
            ]
        ]
        .copy()
    )

    display_table[
        "Total"
    ] = (
        display_table["Male"]
        + display_table["Female"]
    )

    st.dataframe(
        display_table,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # Transgender / Other genders
    # --------------------------------------------------------

    additional_gender_df = pyramid_df[
        ~pyramid_df["Gender"].isin(
            [
                "Male",
                "Female",
            ]
        )
    ].copy()

    if not additional_gender_df.empty:

        st.caption(
            "Additional gender categories are reported "
            "separately below and are not forced into the "
            "two-sided Male–Female pyramid."
        )

        additional_table = (
            additional_gender_df
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

        additional_table[
            "Age Group"
        ] = pd.Categorical(
            additional_table[
                "Age Group"
            ],
            categories=age_order,
            ordered=True,
        )

        additional_table = (
            additional_table
            .sort_values(
                [
                    "Age Group",
                    "Gender",
                ]
            )
            .reset_index(
                drop=True
            )
        )

        st.dataframe(
            additional_table,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# MAIN DEMOGRAPHICS PAGE
# ============================================================

def render_demographics(df):

    st.subheader(
        "👥 Demographic Analysis"
    )

    if (
        df is None
        or df.empty
    ):

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

    total_records = len(df)

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
                chart_df
                .sort_values(
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
                        title=None,
                        sort=age_order,
                        legend=alt.Legend(
                            orient="bottom",
                            direction="horizontal",
                            labelFontSize=9,
                            symbolSize=60,
                        ),
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
                    ],
                )
                .properties(
                    height=400
                )
            )

            if data_labels_enabled():

                labels = (
                    alt.Chart(
                        chart_df
                    )
                    .mark_text(
                        dy=-8,
                        fontWeight="bold",
                        fontSize=11,
                    )
                    .encode(
                        x=alt.X(
                            "Age Group:N",
                            sort=age_order,
                        ),
                        y="Records:Q",
                        text=alt.Text(
                            "Records:Q",
                            format=",",
                        ),
                    )
                )

                age_chart = (
                    age_chart
                    + labels
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
                    lambda x:
                    f"{x:.2f}%"
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

            gender_order = (
                gender_counts[
                    "Gender"
                ].tolist()
            )

            gender_colors = [
                GENDER_COLORS.get(
                    gender_name,
                    "#7F8C8D",
                )
                for gender_name
                in gender_order
            ]

            left, right = (
                st.columns(
                    [1.5, 1],
                    gap="large",
                )
            )

            with left:

                gender_chart = (
                    alt.Chart(
                        gender_counts
                    )
                    .mark_bar()
                    .encode(
                        x=alt.X(
                            "Gender:N",
                            sort=gender_order,
                            title="Gender",
                        ),
                        y=alt.Y(
                            "Records:Q",
                            title="Records",
                        ),
                        color=alt.Color(
                            "Gender:N",
                            title=None,
                            scale=alt.Scale(
                                domain=gender_order,
                                range=gender_colors,
                            ),
                            legend=alt.Legend(
                                orient="bottom",
                                direction="horizontal",
                                labelFontSize=9,
                                symbolSize=70,
                            ),
                        ),
                        tooltip=[
                            alt.Tooltip(
                                "Gender:N"
                            ),
                            alt.Tooltip(
                                "Records:Q",
                                format=",",
                            ),
                        ],
                    )
                    .properties(
                        height=400
                    )
                )

                if data_labels_enabled():

                    gender_labels = (
                        alt.Chart(
                            gender_counts
                        )
                        .mark_text(
                            dy=-8,
                            fontWeight="bold",
                            fontSize=11,
                        )
                        .encode(
                            x=alt.X(
                                "Gender:N",
                                sort=gender_order,
                            ),
                            y="Records:Q",
                            text=alt.Text(
                                "Records:Q",
                                format=",",
                            ),
                        )
                    )

                    gender_chart = (
                        gender_chart
                        + gender_labels
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
                        lambda x:
                        f"{x:.2f}%"
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

        else:

            st.info(
                "Valid age information is not available."
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
        ] = _standardize_gender(
            cross_df["Gender"]
        )

        cross_df[
            "Age Group"
        ] = _standardize_age_group(
            cross_df["Age Group"]
        )

        cross_df = cross_df[
            cross_df["Gender"].ne("")
            & cross_df[
                "Age Group"
            ].ne("")
        ]

        if not cross_df.empty:

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

        else:

            st.info(
                "Gender and Age Group cross-analysis "
                "is not available."
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
                        lambda x:
                        f"{x:.2f}%"
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
        ] = _standardize_age_group(
            age_opd[
                "Age Group"
            ]
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
                "OPD/IPD"
            ].ne("nan")
        ]

        if not age_opd.empty:

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

            opd_order = (
                chart_long[
                    "OPD/IPD"
                ]
                .drop_duplicates()
                .tolist()
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
                    xOffset=alt.XOffset(
                        "OPD/IPD:N"
                    ),
                    color=alt.Color(
                        "OPD/IPD:N",
                        title=None,
                        legend=alt.Legend(
                            orient="bottom",
                            direction="horizontal",
                            columns=len(
                                opd_order
                            ),
                            labelFontSize=9,
                            symbolSize=70,
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "Age Group:N"
                        ),
                        alt.Tooltip(
                            "OPD/IPD:N"
                        ),
                        alt.Tooltip(
                            "Records:Q",
                            format=",",
                        ),
                    ],
                )
                .properties(
                    height=450
                )
            )

            if data_labels_enabled():

                labels = (
                    alt.Chart(
                        chart_long
                    )
                    .mark_text(
                        dy=-7,
                        fontSize=10,
                        fontWeight="bold",
                    )
                    .encode(
                        x=alt.X(
                            "Age Group:N",
                            sort=age_order,
                        ),
                        xOffset=alt.XOffset(
                            "OPD/IPD:N"
                        ),
                        y="Records:Q",
                        text=alt.Text(
                            "Records:Q",
                            format=",",
                        ),
                    )
                )

                age_opd_chart = (
                    age_opd_chart
                    + labels
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

        else:

            st.info(
                "Age Group and OPD/IPD cross-analysis "
                "is not available."
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
        ] = _standardize_gender(
            disease_gender[
                "Gender"
            ]
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
            ]
        )

        if not disease_gender.empty:

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

            top_diseases = (
                disease_gender_table
                .sum(axis=1)
                .sort_values(
                    ascending=False
                )
                .head(10)
                .index
            )

            disease_gender_table = (
                disease_gender_table
                .loc[
                    top_diseases
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

        else:

            st.info(
                "Disease and Gender cross-analysis "
                "is not available."
            )

    # ========================================================
    # 10. DEMOGRAPHIC DATA QUALITY
    # ========================================================

    st.divider()

    st.markdown(
        "### 10. ℹ️ Demographic Data Quality"
    )

    missing_age = 0
    missing_gender = 0
    missing_age_group = 0

    if "Age" in df.columns:

        age_numeric = pd.to_numeric(
            df["Age"],
            errors="coerce",
        )

        valid_age_mask = (
            age_numeric.between(
                0,
                120,
            )
        )

        missing_age = int(
            (
                age_numeric.isna()
                | ~valid_age_mask.fillna(
                    False
                )
            ).sum()
        )

    if "Gender" in df.columns:

        gender_values = (
            _standardize_gender(
                df["Gender"]
            )
        )

        missing_gender = int(
            gender_values
            .eq("")
            .sum()
        )

    if "Age Group" in df.columns:

        age_group_values = (
            _standardize_age_group(
                df["Age Group"]
            )
        )

        invalid_age_group = (
            age_group_values
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(
                [
                    "",
                    "nan",
                    "nat",
                    "none",
                ]
            )
        )

        missing_age_group = int(
            invalid_age_group.sum()
        )

    quality_table = pd.DataFrame(
        {
            "Indicator": [
                "Total Records",
                "Missing / Invalid Age",
                "Missing Gender",
                "Missing Age Group",
            ],
            "Count": [
                total_records,
                missing_age,
                missing_gender,
                missing_age_group,
            ],
        }
    )

    st.dataframe(
        quality_table,
        use_container_width=True,
        hide_index=True,
    )
