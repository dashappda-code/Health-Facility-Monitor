# ============================================================
# PHASE 8B
# INCIDENCE ANALYSIS
# ============================================================
#
# Purpose:
#   Population-based incidence analysis using the globally
#   filtered dashboard dataset.
#
# Important:
#   - phase1_data.py is NOT modified.
#   - This module works with the dataframe supplied by app.py.
#   - Population information is searched from the supplied data.
#   - Disease-wise and Ward-wise analysis are controlled through
#     compact toggle-style selectors.
#   - Plotly legends are positioned at the bottom.
#   - Each analytical chart includes observations.
#   - Methodology is shown within the relevant sections.
#
# Exports:
#   render_incidence_analysis(filtered_df)
#   render_incidence(filtered_df)
#
# ============================================================

import re
from typing import Optional, List

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_DENOMINATOR = 100_000

DENOMINATOR_OPTIONS = {
    "1,000": 1_000,
    "10,000": 10_000,
    "100,000": 100_000,
    "1,000,000": 1_000_000,
}

MONTH_ORDER = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

YEAR_COLUMNS = [
    "Year",
    "Reporting Year",
    "Year of Reporting",
]

MONTH_COLUMNS = [
    "Month",
    "Reporting Month",
]

DATE_COLUMNS = [
    "Test Performed Date",
    "Reporting Date",
    "Date of Reporting",
    "Date",
    "Test Date",
]

DISEASE_COLUMNS = [
    "Confirmed Diagnosis",
    "Disease",
    "Disease Name",
    "Diagnosis",
]

WARD_COLUMNS = [
    "Ward",
    "BMC Ward",
    "Programme Ward",
]

FACILITY_COLUMNS = [
    "Facility Name Lform",
    "Facility Name",
    "Reporting Facility",
    "Facility",
]

POPULATION_COLUMNS = [
    "Population",
    "Ward Population",
    "Population 2025",
    "Population 2026",
    "Population 2024",
    "Estimated Population",
    "Target Population",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def _first_existing_column(
    df: pd.DataFrame,
    candidates: List[str],
) -> Optional[str]:

    if df is None or df.empty:
        return None

    for col in candidates:
        if col in df.columns:
            return col

    return None


def _clean_text_series(
    df: pd.DataFrame,
    column: str,
) -> pd.Series:

    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="object")

    return (
        df[column]
        .astype("string")
        .str.strip()
        .replace(
            {
                "": pd.NA,
                "nan": pd.NA,
                "None": pd.NA,
                "NaN": pd.NA,
            }
        )
    )


def _normalise_month(value):

    if pd.isna(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    text_lower = text.lower()

    month_map = {
        "january": "Jan",
        "jan": "Jan",
        "february": "Feb",
        "feb": "Feb",
        "march": "Mar",
        "mar": "Mar",
        "april": "Apr",
        "apr": "Apr",
        "may": "May",
        "june": "Jun",
        "jun": "Jun",
        "july": "Jul",
        "jul": "Jul",
        "august": "Aug",
        "aug": "Aug",
        "september": "Sep",
        "sep": "Sep",
        "sept": "Sep",
        "october": "Oct",
        "oct": "Oct",
        "november": "Nov",
        "nov": "Nov",
        "december": "Dec",
        "dec": "Dec",
    }

    if text_lower in month_map:
        return month_map[text_lower]

    try:
        number = int(float(text))

        if 1 <= number <= 12:
            return MONTH_ORDER[number - 1]

    except Exception:
        pass

    return text.title()[:3]


def _normalise_year(value):

    if pd.isna(value):
        return pd.NA

    try:
        year = int(float(value))

        if 1900 <= year <= 2100:
            return year

    except Exception:
        pass

    match = re.search(r"(19|20)\d{2}", str(value))

    if match:
        return int(match.group())

    return pd.NA


def _prepare_time_columns(
    df: pd.DataFrame,
) -> pd.DataFrame:

    work = df.copy()

    year_col = _first_existing_column(
        work,
        YEAR_COLUMNS,
    )

    month_col = _first_existing_column(
        work,
        MONTH_COLUMNS,
    )

    date_col = _first_existing_column(
        work,
        DATE_COLUMNS,
    )

    if year_col:
        work["_inc_year"] = (
            work[year_col]
            .apply(_normalise_year)
        )

    else:
        work["_inc_year"] = pd.NA

    if month_col:
        work["_inc_month"] = (
            work[month_col]
            .apply(_normalise_month)
        )

    else:
        work["_inc_month"] = pd.NA

    # If Year or Month are missing, derive them from a valid date.
    if date_col:

        parsed_date = pd.to_datetime(
            work[date_col],
            errors="coerce",
            dayfirst=True,
        )

        missing_year = work["_inc_year"].isna()

        work.loc[
            missing_year,
            "_inc_year",
        ] = parsed_date.loc[
            missing_year
        ].dt.year

        missing_month = work["_inc_month"].isna()

        work.loc[
            missing_month,
            "_inc_month",
        ] = parsed_date.loc[
            missing_month
        ].dt.month.apply(
            lambda x: (
                MONTH_ORDER[int(x) - 1]
                if pd.notna(x)
                and 1 <= int(x) <= 12
                else pd.NA
            )
        )

    return work


def _add_standard_dimensions(
    df: pd.DataFrame,
) -> pd.DataFrame:

    work = _prepare_time_columns(df)

    disease_col = _first_existing_column(
        work,
        DISEASE_COLUMNS,
    )

    ward_col = _first_existing_column(
        work,
        WARD_COLUMNS,
    )

    facility_col = _first_existing_column(
        work,
        FACILITY_COLUMNS,
    )

    if disease_col:
        work["_inc_disease"] = _clean_text_series(
            work,
            disease_col,
        )

    else:
        work["_inc_disease"] = pd.NA

    if ward_col:
        work["_inc_ward"] = _clean_text_series(
            work,
            ward_col,
        )

    else:
        work["_inc_ward"] = pd.NA

    if facility_col:
        work["_inc_facility"] = _clean_text_series(
            work,
            facility_col,
        )

    else:
        work["_inc_facility"] = pd.NA

    return work


# ============================================================
# POPULATION HELPERS
# ============================================================

def _find_population_column(
    df: pd.DataFrame,
) -> Optional[str]:

    if df is None or df.empty:
        return None

    # Exact candidates first.
    for col in POPULATION_COLUMNS:

        if col in df.columns:

            numeric = pd.to_numeric(
                df[col],
                errors="coerce",
            )

            if numeric.notna().any():
                return col

    # Flexible fallback.
    for col in df.columns:

        col_text = str(col).lower()

        if "population" not in col_text:
            continue

        numeric = pd.to_numeric(
            df[col],
            errors="coerce",
        )

        if numeric.notna().any():
            return col

    return None


def _population_summary(
    df: pd.DataFrame,
) -> dict:

    population_col = _find_population_column(df)

    result = {
        "available": False,
        "column": population_col,
        "total": None,
        "wards": 0,
    }

    if population_col is None:
        return result

    numeric_population = pd.to_numeric(
        df[population_col],
        errors="coerce",
    )

    valid = numeric_population[
        numeric_population > 0
    ]

    if valid.empty:
        return result

    result["available"] = True
    result["total"] = float(valid.sum())

    ward_col = _first_existing_column(
        df,
        WARD_COLUMNS,
    )

    if ward_col:

        temp = pd.DataFrame(
            {
                "Ward": df[ward_col],
                "Population": numeric_population,
            }
        )

        temp = temp.dropna(
            subset=["Ward", "Population"]
        )

        if not temp.empty:

            ward_population = (
                temp.groupby(
                    "Ward",
                    as_index=False,
                )["Population"]
                .max()
            )

            result["wards"] = len(
                ward_population
            )

    return result


def _build_ward_population(
    df: pd.DataFrame,
) -> pd.DataFrame:

    population_col = _find_population_column(df)

    ward_col = _first_existing_column(
        df,
        WARD_COLUMNS,
    )

    if (
        population_col is None
        or ward_col is None
    ):
        return pd.DataFrame(
            columns=[
                "Ward",
                "Population",
            ]
        )

    work = pd.DataFrame(
        {
            "Ward": _clean_text_series(
                df,
                ward_col,
            ),
            "Population": pd.to_numeric(
                df[population_col],
                errors="coerce",
            ),
        }
    )

    work = work.dropna(
        subset=[
            "Ward",
            "Population",
        ]
    )

    work = work[
        work["Population"] > 0
    ]

    if work.empty:
        return pd.DataFrame(
            columns=[
                "Ward",
                "Population",
            ]
        )

    # Population is generally repeated across case records.
    # Therefore use MAX per ward rather than SUM.
    result = (
        work.groupby(
            "Ward",
            as_index=False,
        )["Population"]
        .max()
    )

    return result


# ============================================================
# INCIDENCE CALCULATION
# ============================================================

def _calculate_incidence(
    cases,
    population,
    denominator,
):

    if (
        population is None
        or pd.isna(population)
        or population <= 0
    ):
        return None

    try:
        return (
            float(cases)
            / float(population)
            * float(denominator)
        )

    except Exception:
        return None


def _overall_incidence(
    df: pd.DataFrame,
    denominator: int,
):

    pop_info = _population_summary(df)

    if not pop_info["available"]:
        return None

    total_cases = len(df)

    return _calculate_incidence(
        total_cases,
        pop_info["total"],
        denominator,
    )


# ============================================================
# PLOTLY STYLE
# ============================================================

def _apply_chart_style(
    fig,
    height=480,
    title=None,
):

    if title:
        fig.update_layout(
            title=dict(
                text=title,
                x=0,
                xanchor="left",
            )
        )

    fig.update_layout(
        height=height,
        margin=dict(
            l=55,
            r=25,
            t=75,
            b=105,
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.20,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0)",
            borderwidth=0,
        ),
        hovermode="closest",
    )

    fig.update_xaxes(
        showgrid=True,
        zeroline=False,
    )

    fig.update_yaxes(
        showgrid=True,
        zeroline=False,
    )

    return fig


def _observation_box(
    observations,
):

    if not observations:
        return

    st.markdown(
        """
        <div style="
            background:#f7f9fc;
            border-left:4px solid #3b82f6;
            border-radius:8px;
            padding:10px 14px;
            margin-top:4px;
            margin-bottom:14px;
        ">
        <div style="
            font-weight:700;
            font-size:13px;
            margin-bottom:5px;
        ">
        🔎 Observations
        </div>
        """,
        unsafe_allow_html=True,
    )

    for observation in observations:
        st.markdown(
            f"- {observation}"
        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


def _methodology(
    text,
):

    with st.expander(
        "📐 Methodology & Interpretation",
        expanded=False,
    ):
        st.markdown(text)


# ============================================================
# SMART TOGGLE
# ============================================================

def _smart_toggle(
    label,
    options,
    key,
    default_index=0,
):

    return st.radio(
        label,
        options,
        index=default_index,
        horizontal=True,
        key=key,
        label_visibility="collapsed",
    )


# ============================================================
# SECTION 1
# OVERALL INCIDENCE SUMMARY
# ============================================================

def _render_summary(
    df: pd.DataFrame,
    denominator: int,
):

    st.subheader(
        "1. 📊 Population & Incidence Summary"
    )

    pop_info = _population_summary(df)

    if not pop_info["available"]:

        st.warning(
            "Population data is not available in the current dataset. "
            "Case counts can be displayed, but population-based incidence "
            "cannot be calculated until a valid population field is available."
        )

        c1, c2 = st.columns(2)

        with c1:
            st.metric(
                "Reported Records",
                f"{len(df):,}",
            )

        with c2:
            st.metric(
                "Incidence",
                "Not available",
            )

        _methodology(
            """
            **Method used**

            - Incidence is defined as reported cases divided by the
              relevant population, multiplied by the selected denominator.
            - Formula:

              **Incidence = Cases / Population × Denominator**

            - The default denominator is **100,000 population**.
            - No artificial population value is generated.
            - If population is unavailable, the dashboard does not
              label case counts as incidence.
            """
        )

        return

    incidence = _overall_incidence(
        df,
        denominator,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Reported Records",
            f"{len(df):,}",
        )

    with c2:
        st.metric(
            "Population",
            f"{pop_info['total']:,.0f}",
        )

    with c3:
        st.metric(
            f"Incidence / {denominator:,}",
            (
                f"{incidence:,.2f}"
                if incidence is not None
                else "NA"
            ),
        )

    with c4:
        st.metric(
            "Population Wards",
            f"{pop_info['wards']:,}",
        )

    _observation_box(
        [
            (
                f"The filtered dataset contains "
                f"**{len(df):,} reported records**."
            ),
            (
                f"The denominator currently selected is "
                f"**{denominator:,} population**."
            ),
            (
                f"The calculated overall incidence is "
                f"**{incidence:,.2f} per {denominator:,} population**."
                if incidence is not None
                else "Overall incidence could not be calculated."
            ),
            (
                "Incidence should be interpreted as reported-record "
                "incidence within the available surveillance data."
            ),
        ]
    )

    _methodology(
        """
        **Method used**

        Incidence is calculated as:

        **Incidence = Number of reported cases ÷ Population × selected denominator**

        Population values are taken from the available population field in
        the supplied dataset. Population is not artificially estimated.

        For ward-level population values, when population is repeated across
        multiple case records, the maximum valid population value for each
        ward is used to avoid multiplying the same population by the number
        of records.

        **Interpretation**

        Incidence represents the burden of reported records relative to the
        population denominator. It should not automatically be interpreted
        as true disease incidence in the community without considering
        surveillance coverage, reporting completeness, diagnostic practice,
        and population-data quality.
        """
    )


# ============================================================
# SECTION 2
# DENOMINATOR CONTROL
# ============================================================

def _render_denominator_control():

    st.markdown(
        "### 🎛️ Incidence Denominator"
    )

    labels = list(
        DENOMINATOR_OPTIONS.keys()
    )

    selected_label = _smart_toggle(
        "Select denominator",
        labels,
        key="incidence_denominator_toggle",
        default_index=2,
    )

    return DENOMINATOR_OPTIONS[
        selected_label
    ]


# ============================================================
# SECTION 3
# DISEASE / WARD SMART ANALYSIS
# ============================================================

def _render_disease_ward_analysis(
    df: pd.DataFrame,
    denominator: int,
):

    st.subheader(
        "2. 🦠 Disease & 🏙️ Ward Incidence Analysis"
    )

    st.caption(
        "Use the compact selector below to switch the analytical dimension."
    )

    analysis_mode = _smart_toggle(
        "Analysis dimension",
        [
            "Disease-wise",
            "Ward-wise",
        ],
        key="incidence_dimension_toggle",
        default_index=0,
    )

    metric_mode = _smart_toggle(
        "Metric",
        [
            "Cases",
            "Incidence Rate",
        ],
        key="incidence_metric_toggle",
        default_index=1,
    )

    ward_population = _build_ward_population(
        df
    )

    # --------------------------------------------------------
    # DISEASE-WISE
    # --------------------------------------------------------

    if analysis_mode == "Disease-wise":

        disease_col = "_inc_disease"

        if disease_col not in df.columns:

            st.info(
                "Disease information is not available."
            )

            return

        disease_df = df[
            df[disease_col].notna()
        ].copy()

        if disease_df.empty:

            st.info(
                "No valid disease records are available."
            )

            return

        summary = (
            disease_df
            .groupby(disease_col)
            .size()
            .reset_index(name="Cases")
            .sort_values(
                "Cases",
                ascending=False,
            )
        )

        # Top 15 for readable display.
        display_df = summary.head(15).copy()

        if metric_mode == "Cases":

            fig = px.bar(
                display_df.sort_values(
                    "Cases"
                ),
                x="Cases",
                y=disease_col,
                orientation="h",
                text="Cases",
                title=(
                    "Top 15 Diseases by Reported Case Count"
                ),
            )

            fig.update_traces(
                textposition="outside",
            )

            fig.update_layout(
                xaxis_title="Reported Cases",
                yaxis_title="Disease",
            )

            fig = _apply_chart_style(
                fig,
                height=560,
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

            top_row = display_df.iloc[0]

            _observation_box(
                [
                    (
                        f"The highest reported disease category is "
                        f"**{top_row[disease_col]}** with "
                        f"**{int(top_row['Cases']):,} records**."
                    ),
                    (
                        f"The chart displays the top "
                        f"**{len(display_df)} disease categories** "
                        "within the current filtered dataset."
                    ),
                    (
                        "Case volume describes reported burden and "
                        "does not by itself account for population differences."
                    ),
                ]
            )

        else:

            # Disease-specific population incidence requires a common
            # denominator. Use overall available population denominator.
            pop_info = _population_summary(
                df
            )

            if not pop_info["available"]:

                st.warning(
                    "Population data is unavailable, so disease-specific "
                    "incidence rates cannot be calculated."
                )

                return

            display_df["Incidence"] = (
                display_df["Cases"]
                .apply(
                    lambda x:
                    _calculate_incidence(
                        x,
                        pop_info["total"],
                        denominator,
                    )
                )
            )

            fig = px.bar(
                display_df.sort_values(
                    "Incidence"
                ),
                x="Incidence",
                y=disease_col,
                orientation="h",
                text=display_df[
                    "Incidence"
                ].round(2),
                title=(
                    f"Top 15 Diseases — "
                    f"Reported Incidence per {denominator:,}"
                ),
            )

            fig.update_traces(
                textposition="outside",
            )

            fig.update_layout(
                xaxis_title=(
                    f"Incidence per {denominator:,} population"
                ),
                yaxis_title="Disease",
            )

            fig = _apply_chart_style(
                fig,
                height=560,
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

            top_row = display_df.iloc[0]

            _observation_box(
                [
                    (
                        f"**{top_row[disease_col]}** has the highest "
                        f"reported incidence among the displayed disease categories."
                    ),
                    (
                        f"The selected denominator is "
                        f"**{denominator:,} population**."
                    ),
                    (
                        "The same overall population denominator is used "
                        "for disease comparison; this is a proportional "
                        "comparison of reported disease burden."
                    ),
                ]
            )

    # --------------------------------------------------------
    # WARD-WISE
    # --------------------------------------------------------

    else:

        ward_col = "_inc_ward"

        if ward_col not in df.columns:

            st.info(
                "Ward information is not available."
            )

            return

        ward_df = df[
            df[ward_col].notna()
        ].copy()

        if ward_df.empty:

            st.info(
                "No valid ward records are available."
            )

            return

        ward_summary = (
            ward_df
            .groupby(ward_col)
            .size()
            .reset_index(name="Cases")
            .sort_values(
                "Cases",
                ascending=False,
            )
        )

        if metric_mode == "Cases":

            display_df = ward_summary.head(
                15
            ).copy()

            fig = px.bar(
                display_df.sort_values(
                    "Cases"
                ),
                x="Cases",
                y=ward_col,
                orientation="h",
                text="Cases",
                title=(
                    "Top 15 Wards by Reported Case Count"
                ),
            )

            fig.update_traces(
                textposition="outside",
            )

            fig.update_layout(
                xaxis_title="Reported Cases",
                yaxis_title="Ward",
            )

            fig = _apply_chart_style(
                fig,
                height=560,
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

            top_row = display_df.iloc[0]

            _observation_box(
                [
                    (
                        f"**Ward {top_row[ward_col]}** has the highest "
                        f"reported case count among the displayed wards "
                        f"with **{int(top_row['Cases']):,} records**."
                    ),
                    (
                        f"The chart displays the top "
                        f"**{len(display_df)} wards**."
                    ),
                    (
                        "Ward case counts describe reported burden and "
                        "should not be interpreted as population-adjusted risk."
                    ),
                ]
            )

        else:

            if ward_population.empty:

                st.warning(
                    "Ward-level population data is not available. "
                    "Ward incidence cannot be calculated."
                )

                return

            incidence_df = ward_summary.merge(
                ward_population,
                left_on=ward_col,
                right_on="Ward",
                how="left",
            )

            incidence_df["Incidence"] = (
                incidence_df.apply(
                    lambda row:
                    _calculate_incidence(
                        row["Cases"],
                        row["Population"],
                        denominator,
                    ),
                    axis=1,
                )
            )

            incidence_df = incidence_df.dropna(
                subset=["Incidence"]
            )

            display_df = (
                incidence_df
                .sort_values(
                    "Incidence",
                    ascending=False,
                )
                .head(15)
                .copy()
            )

            if display_df.empty:

                st.warning(
                    "Valid ward population values are not available "
                    "for incidence calculation."
                )

                return

            fig = px.bar(
                display_df.sort_values(
                    "Incidence"
                ),
                x="Incidence",
                y=ward_col,
                orientation="h",
                text=display_df[
                    "Incidence"
                ].round(2),
                title=(
                    f"Top 15 Wards by Reported Incidence "
                    f"per {denominator:,}"
                ),
            )

            fig.update_traces(
                textposition="outside",
            )

            fig.update_layout(
                xaxis_title=(
                    f"Incidence per {denominator:,} population"
                ),
                yaxis_title="Ward",
            )

            fig = _apply_chart_style(
                fig,
                height=560,
            )

            st.plotly_chart(
                fig,
                use_container_width=True,
            )

            top_row = display_df.iloc[0]

            _observation_box(
                [
                    (
                        f"**Ward {top_row[ward_col]}** has the highest "
                        f"calculated reported incidence among the displayed wards."
                    ),
                    (
                        f"Its calculated incidence is "
                        f"**{top_row['Incidence']:,.2f} per "
                        f"{denominator:,} population**."
                    ),
                    (
                        "Ward incidence uses the ward population denominator "
                        "available in the dataset."
                    ),
                ]
            )

    _methodology(
        """
        **Analytical approach**

        This section uses a single compact toggle to switch between:

        - Disease-wise analysis
        - Ward-wise analysis

        A second toggle switches between:

        - Reported case count
        - Population-based incidence

        **Disease-wise**

        Disease categories are grouped from the available diagnosis field.
        Disease case counts are compared within the current global dashboard
        filter scope.

        **Ward-wise**

        Records are grouped by programme/BMC ward.

        When ward population is available, incidence is calculated as:

        **Ward cases ÷ Ward population × selected denominator**

        Repeated population values are not summed across individual case
        records. The maximum valid population value available for each ward
        is used.

        **Important interpretation**

        Higher reported case volume and higher population-adjusted incidence
        answer different questions. Case volume reflects surveillance burden;
        incidence adjusts the burden using population.
        """
    )


# ============================================================
# SECTION 4
# DISEASE × WARD
# ============================================================

def _render_disease_ward_matrix(
    df: pd.DataFrame,
):

    st.subheader(
        "3. 🔄 Disease × Ward Distribution"
    )

    disease_col = "_inc_disease"
    ward_col = "_inc_ward"

    if (
        disease_col not in df.columns
        or ward_col not in df.columns
    ):

        st.info(
            "Disease and/or ward information is unavailable."
        )

        return

    work = df[
        df[disease_col].notna()
        & df[ward_col].notna()
    ].copy()

    if work.empty:

        st.info(
            "No valid disease-ward records are available."
        )

        return

    disease_totals = (
        work.groupby(disease_col)
        .size()
        .sort_values(
            ascending=False
        )
    )

    top_diseases = (
        disease_totals
        .head(10)
        .index
        .tolist()
    )

    ward_totals = (
        work.groupby(ward_col)
        .size()
        .sort_values(
            ascending=False
        )
    )

    top_wards = (
        ward_totals
        .head(15)
        .index
        .tolist()
    )

    matrix = (
        work[
            work[disease_col].isin(
                top_diseases
            )
            & work[ward_col].isin(
                top_wards
            )
        ]
        .groupby(
            [
                ward_col,
                disease_col,
            ]
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    if matrix.empty:

        st.info(
            "No disease-ward combination is available."
        )

        return

    view_mode = _smart_toggle(
        "Matrix display",
        [
            "Grouped Bars",
            "Heatmap",
        ],
        key="incidence_matrix_toggle",
        default_index=1,
    )

    if view_mode == "Grouped Bars":

        fig = px.bar(
            matrix,
            x=ward_col,
            y="Cases",
            color=disease_col,
            barmode="group",
            title=(
                "Disease Distribution across Top Wards"
            ),
        )

        fig.update_layout(
            xaxis_title="Ward",
            yaxis_title="Reported Cases",
        )

        fig = _apply_chart_style(
            fig,
            height=560,
        )

    else:

        pivot = matrix.pivot(
            index=ward_col,
            columns=disease_col,
            values="Cases",
        ).fillna(0)

        fig = px.imshow(
            pivot,
            text_auto=True,
            aspect="auto",
            title=(
                "Disease × Ward Reported Case Heatmap"
            ),
            labels={
                "x": "Disease",
                "y": "Ward",
                "color": "Cases",
            },
        )

        fig.update_layout(
            margin=dict(
                l=70,
                r=30,
                t=75,
                b=110,
            ),
        )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    max_row = matrix.loc[
        matrix["Cases"].idxmax()
    ]

    _observation_box(
        [
            (
                f"The largest displayed disease-ward combination is "
                f"**{max_row[ward_col]} × {max_row[disease_col]}** "
                f"with **{int(max_row['Cases']):,} reported records**."
            ),
            (
                f"The analysis covers the top "
                f"**{len(top_wards)} wards** and top "
                f"**{len(top_diseases)} disease categories** by reported volume."
            ),
            (
                "The heatmap/grouped view is intended to identify "
                "where specific disease burdens are concentrated."
            ),
        ]
    )

    _methodology(
        """
        **Method**

        Disease and ward are cross-tabulated using reported records within
        the current dashboard filter scope.

        The display is limited to the highest-volume wards and diseases so
        that the chart remains readable. This is a presentation filter only;
        it does not modify the underlying dataset.

        The analysis describes distribution of reported records and should
        not be interpreted as a causal relationship between ward and disease.
        """
    )


# ============================================================
# SECTION 5
# MONTHLY INCIDENCE TREND
# ============================================================

def _render_monthly_trend(
    df: pd.DataFrame,
    denominator: int,
):

    st.subheader(
        "4. 📈 Monthly Incidence Trend"
    )

    work = df.copy()

    if (
        "_inc_year" not in work.columns
        or "_inc_month" not in work.columns
    ):

        st.info(
            "Year/month information is not available."
        )

        return

    work = work[
        work["_inc_year"].notna()
        & work["_inc_month"].notna()
    ].copy()

    if work.empty:

        st.info(
            "No valid year-month records are available."
        )

        return

    work["_inc_year"] = pd.to_numeric(
        work["_inc_year"],
        errors="coerce",
    )

    work["_month_number"] = (
        work["_inc_month"]
        .map(
            {
                month: index + 1
                for index, month
                in enumerate(MONTH_ORDER)
            }
        )
    )

    work = work.dropna(
        subset=[
            "_inc_year",
            "_month_number",
        ]
    )

    monthly = (
        work.groupby(
            [
                "_inc_year",
                "_month_number",
            ]
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    monthly["Month"] = monthly[
        "_month_number"
    ].map(
        lambda x:
        MONTH_ORDER[int(x) - 1]
    )

    monthly["Year"] = monthly[
        "_inc_year"
    ].astype(int)

    monthly["Month-Year"] = (
        monthly["Month"]
        + "-"
        + monthly["Year"].astype(str)
    )

    metric = _smart_toggle(
        "Monthly metric",
        [
            "Cases",
            "Incidence Rate",
        ],
        key="incidence_monthly_metric_toggle",
        default_index=0,
    )

    if metric == "Cases":

        fig = px.line(
            monthly.sort_values(
                [
                    "Year",
                    "_month_number",
                ]
            ),
            x="Month-Year",
            y="Cases",
            markers=True,
            title="Monthly Reported Cases",
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Reported Cases",
        )

        fig = _apply_chart_style(
            fig,
            height=500,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    else:

        pop_info = _population_summary(
            df
        )

        if not pop_info["available"]:

            st.warning(
                "Population data is unavailable. "
                "Monthly incidence cannot be calculated."
            )

            return

        monthly["Incidence"] = (
            monthly["Cases"]
            .apply(
                lambda x:
                _calculate_incidence(
                    x,
                    pop_info["total"],
                    denominator,
                )
            )
        )

        fig = px.line(
            monthly.sort_values(
                [
                    "Year",
                    "_month_number",
                ]
            ),
            x="Month-Year",
            y="Incidence",
            markers=True,
            title=(
                f"Monthly Reported Incidence "
                f"per {denominator:,} Population"
            ),
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title=(
                f"Incidence per {denominator:,}"
            ),
        )

        fig = _apply_chart_style(
            fig,
            height=500,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    peak_row = monthly.loc[
        monthly["Cases"].idxmax()
    ]

    _observation_box(
        [
            (
                f"The highest monthly reported burden occurred in "
                f"**{peak_row['Month-Year']}** with "
                f"**{int(peak_row['Cases']):,} records**."
            ),
            (
                "Months are displayed in calendar order within each year."
            ),
            (
                "Months without records are not interpreted as zero "
                "incidence unless the corresponding surveillance period "
                "is confirmed to have complete reporting."
            ),
        ]
    )

    _methodology(
        """
        **Method**

        Records are grouped by Year and Month after normalising month names
        and, where required, deriving time information from an available
        date field.

        Month order is explicitly set to calendar order:

        **Jan → Feb → Mar → ... → Dec**

        When incidence is selected, monthly case counts are divided by the
        available population denominator and multiplied by the selected
        denominator.

        A missing month is treated cautiously because absence of records may
        represent zero cases or incomplete reporting. The dashboard therefore
        does not automatically claim that an unreported month represents
        zero incidence.
        """
    )


# ============================================================
# SECTION 6
# YEAR-WISE TREND
# ============================================================

def _render_year_trend(
    df: pd.DataFrame,
    denominator: int,
):

    st.subheader(
        "5. 📅 Year-wise Incidence Comparison"
    )

    if "_inc_year" not in df.columns:

        st.info(
            "Year information is not available."
        )

        return

    work = df[
        df["_inc_year"].notna()
    ].copy()

    if work.empty:

        st.info(
            "No valid year information is available."
        )

        return

    work["_inc_year"] = pd.to_numeric(
        work["_inc_year"],
        errors="coerce",
    )

    yearly = (
        work.dropna(
            subset=["_inc_year"]
        )
        .groupby("_inc_year")
        .size()
        .reset_index(
            name="Cases"
        )
        .sort_values(
            "_inc_year"
        )
    )

    yearly["Year"] = (
        yearly["_inc_year"]
        .astype(int)
        .astype(str)
    )

    metric = _smart_toggle(
        "Yearly metric",
        [
            "Cases",
            "Incidence Rate",
        ],
        key="incidence_yearly_metric_toggle",
        default_index=0,
    )

    if metric == "Cases":

        fig = px.bar(
            yearly,
            x="Year",
            y="Cases",
            text="Cases",
            title="Year-wise Reported Cases",
        )

        fig.update_traces(
            textposition="outside",
        )

        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Reported Cases",
        )

    else:

        pop_info = _population_summary(
            df
        )

        if not pop_info["available"]:

            st.warning(
                "Population data is unavailable. "
                "Year-wise incidence cannot be calculated."
            )

            return

        yearly["Incidence"] = (
            yearly["Cases"]
            .apply(
                lambda x:
                _calculate_incidence(
                    x,
                    pop_info["total"],
                    denominator,
                )
            )
        )

        fig = px.bar(
            yearly,
            x="Year",
            y="Incidence",
            text=yearly[
                "Incidence"
            ].round(2),
            title=(
                f"Year-wise Reported Incidence "
                f"per {denominator:,} Population"
            ),
        )

        fig.update_traces(
            textposition="outside",
        )

        fig.update_layout(
            xaxis_title="Year",
            yaxis_title=(
                f"Incidence per {denominator:,}"
            ),
        )

    fig = _apply_chart_style(
        fig,
        height=480,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    highest = yearly.loc[
        yearly["Cases"].idxmax()
    ]

    _observation_box(
        [
            (
                f"The highest annual reported burden in the available data "
                f"occurred in **{highest['Year']}** with "
                f"**{int(highest['Cases']):,} records**."
            ),
            (
                f"The chart contains "
                f"**{len(yearly)} reporting year(s)** available after filtering."
            ),
            (
                "Year-to-year differences should be interpreted alongside "
                "changes in surveillance coverage and reporting completeness."
            ),
        ]
    )

    _methodology(
        """
        **Method**

        Annual totals are calculated from the current filtered dataset after
        normalising the available Year field.

        When incidence is selected:

        **Annual cases ÷ population × denominator**

        The same population denominator is used for year-to-year comparison
        when a time-specific population series is not available.
        """
    )


# ============================================================
# SECTION 7
# FACILITY CONTEXT
# ============================================================

def _render_facility_context(
    df: pd.DataFrame,
):

    st.subheader(
        "6. 🏥 Facility-wise Reported Burden"
    )

    facility_col = "_inc_facility"

    if facility_col not in df.columns:

        st.info(
            "Facility information is not available."
        )

        return

    work = df[
        df[facility_col].notna()
    ].copy()

    if work.empty:

        st.info(
            "No valid facility information is available."
        )

        return

    facility_summary = (
        work.groupby(
            facility_col
        )
        .size()
        .reset_index(
            name="Cases"
        )
        .sort_values(
            "Cases",
            ascending=False,
        )
        .head(15)
    )

    fig = px.bar(
        facility_summary.sort_values(
            "Cases"
        ),
        x="Cases",
        y=facility_col,
        orientation="h",
        text="Cases",
        title=(
            "Top 15 Facilities by Reported Case Volume"
        ),
    )

    fig.update_traces(
        textposition="outside",
    )

    fig.update_layout(
        xaxis_title="Reported Cases",
        yaxis_title="Facility",
    )

    fig = _apply_chart_style(
        fig,
        height=620,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    top_row = facility_summary.iloc[0]

    _observation_box(
        [
            (
                f"The highest reported facility burden is "
                f"**{top_row[facility_col]}** with "
                f"**{int(top_row['Cases']):,} records**."
            ),
            (
                "Facility volume reflects reporting burden and should not "
                "be interpreted as facility-specific population incidence."
            ),
            (
                "High-volume facilities may require closer review of "
                "reporting completeness, referral patterns and service utilisation."
            ),
        ]
    )

    _methodology(
        """
        **Method**

        Facilities are ranked according to the number of reported records
        within the current global filter scope.

        This section intentionally reports case volume rather than incidence
        because facility catchment populations are generally not equivalent
        and may not be available in the surveillance line list.
        """
    )


# ============================================================
# SECTION 8
# DATA QUALITY / INCIDENCE VALIDATION
# ============================================================

def _render_incidence_data_quality(
    df: pd.DataFrame,
):

    st.subheader(
        "7. ✅ Incidence Data Quality Check"
    )

    population_col = _find_population_column(
        df
    )

    ward_col = _first_existing_column(
        df,
        WARD_COLUMNS,
    )

    year_col = _first_existing_column(
        df,
        YEAR_COLUMNS,
    )

    disease_col = _first_existing_column(
        df,
        DISEASE_COLUMNS,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Records",
            f"{len(df):,}",
        )

    with c2:

        st.metric(
            "Population Field",
            (
                "Available"
                if population_col
                else "Missing"
            ),
        )

    with c3:

        st.metric(
            "Ward Field",
            (
                "Available"
                if ward_col
                else "Missing"
            ),
        )

    with c4:

        st.metric(
            "Year Field",
            (
                "Available"
                if year_col
                else "Missing"
            ),
        )

    checks = []

    if population_col:

        population_values = pd.to_numeric(
            df[population_col],
            errors="coerce",
        )

        valid_population = (
            population_values > 0
        )

        checks.append(
            {
                "Check": "Positive population values",
                "Records": int(
                    valid_population.sum()
                ),
                "Status": (
                    "Pass"
                    if valid_population.any()
                    else "Review"
                ),
            }
        )

    else:

        checks.append(
            {
                "Check": "Population field",
                "Records": 0,
                "Status": "Missing",
            }
        )

    if disease_col:

        disease_valid = (
            _clean_text_series(
                df,
                disease_col,
            )
            .notna()
        )

        checks.append(
            {
                "Check": "Disease completeness",
                "Records": int(
                    disease_valid.sum()
                ),
                "Status": (
                    "Pass"
                    if disease_valid.any()
                    else "Review"
                ),
            }
        )

    if ward_col:

        ward_valid = (
            _clean_text_series(
                df,
                ward_col,
            )
            .notna()
        )

        checks.append(
            {
                "Check": "Ward completeness",
                "Records": int(
                    ward_valid.sum()
                ),
                "Status": (
                    "Pass"
                    if ward_valid.any()
                    else "Review"
                ),
            }
        )

    quality_df = pd.DataFrame(
        checks
    )

    st.dataframe(
        quality_df,
        use_container_width=True,
        hide_index=True,
    )

    _observation_box(
        [
            (
                "Incidence calculation depends on the availability and "
                "quality of population denominators."
            ),
            (
                "Missing ward, disease or time fields reduce the scope of "
                "corresponding analytical sections."
            ),
            (
                "The dashboard does not generate artificial population "
                "values to fill missing denominators."
            ),
        ]
    )

    _methodology(
        """
        **Validation approach**

        Before calculating population-based incidence, the dashboard checks:

        1. Whether a usable population field exists.
        2. Whether population values are positive.
        3. Whether ward information is available.
        4. Whether disease information is available.
        5. Whether year/time information is available.

        These checks are descriptive data-quality checks and are not a
        substitute for formal population-data validation.
        """
    )


# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_incidence_analysis(
    filtered_df: pd.DataFrame,
):

    if (
        filtered_df is None
        or filtered_df.empty
    ):

        st.info(
            "No records are available for incidence analysis "
            "under the current dashboard filters."
        )

        return

    # --------------------------------------------------------
    # Prepare once.
    # This avoids repeatedly rebuilding the same dimensions.
    # --------------------------------------------------------

    analysis_df = _add_standard_dimensions(
        filtered_df
    )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.markdown(
        """
        <div style="
            background:linear-gradient(
                90deg,
                #eef7ff,
                #f8fbff
            );
            border-left:5px solid #1769aa;
            border-radius:10px;
            padding:12px 16px;
            margin-bottom:14px;
        ">
            <div style="
                font-size:21px;
                font-weight:750;
                color:#123b5d;
            ">
                📈 Incidence Analysis
            </div>
            <div style="
                font-size:12px;
                color:#607080;
                margin-top:3px;
            ">
                Population-adjusted surveillance burden by disease,
                ward, time and reporting facility
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------
    # GLOBAL DENOMINATOR
    # --------------------------------------------------------

    denominator = _render_denominator_control()

    st.divider()

    # --------------------------------------------------------
    # SECTION 1
    # --------------------------------------------------------

    _render_summary(
        analysis_df,
        denominator,
    )

    st.divider()

    # --------------------------------------------------------
    # SECTION 2
    # --------------------------------------------------------

    _render_disease_ward_analysis(
        analysis_df,
        denominator,
    )

    st.divider()

    # --------------------------------------------------------
    # SECTION 3
    # --------------------------------------------------------

    _render_disease_ward_matrix(
        analysis_df,
    )

    st.divider()

    # --------------------------------------------------------
    # SECTION 4
    # --------------------------------------------------------

    _render_monthly_trend(
        analysis_df,
        denominator,
    )

    st.divider()

    # --------------------------------------------------------
    # SECTION 5
    # --------------------------------------------------------

    _render_year_trend(
        analysis_df,
        denominator,
    )

    st.divider()

    # --------------------------------------------------------
    # SECTION 6
    # --------------------------------------------------------

    _render_facility_context(
        analysis_df,
    )

    st.divider()

    # --------------------------------------------------------
    # SECTION 7
    # --------------------------------------------------------

    _render_incidence_data_quality(
        analysis_df,
    )

    # --------------------------------------------------------
    # FINAL METHODOLOGY
    # --------------------------------------------------------

    st.divider()

    with st.expander(
        "📘 Overall Incidence Methodology",
        expanded=False,
    ):

        st.markdown(
            f"""
            ### Definition

            Incidence is calculated as:

            **Incidence = Reported Cases ÷ Population × {denominator:,}**

            ### Analytical dimensions

            The module analyses reported burden across:

            - Disease
            - Ward
            - Disease × Ward
            - Month
            - Year
            - Facility

            ### Population handling

            Population values are taken from available population fields in
            the dataset. No artificial coordinates or population values are
            generated.

            For ward population, repeated population values across case
            records are not summed. The maximum valid population value per
            ward is used as the denominator.

            ### Interpretation

            The results describe **reported surveillance incidence/burden**.
            They should be interpreted alongside:

            - surveillance coverage,
            - reporting completeness,
            - diagnostic practices,
            - population-data quality,
            - referral patterns,
            - facility utilisation,
            - and changes in case detection.

            ### Denominator

            The dashboard allows the denominator to be changed between:

            **1,000 | 10,000 | 100,000 | 1,000,000**

            The default is **100,000 population**.

            ### Important distinction

            A high case count and a high incidence rate are not equivalent.

            **Case count** describes the number of reported records.

            **Incidence rate** adjusts reported records using population.

            Both measures are therefore retained as separate analytical
            views rather than replacing one with the other.
            """
        )


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def render_incidence(
    filtered_df: pd.DataFrame,
):

    return render_incidence_analysis(
        filtered_df
    )
