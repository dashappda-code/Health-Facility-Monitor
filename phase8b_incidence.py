import re

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from chart_helpers import data_labels_enabled


# ============================================================
# CONFIGURATION
# ============================================================

POPULATION_SHEET_ID = (
    "18qfha01Czh10i4PDRUpuumtRVwbQv7Pn09jFxGSbXHg"
)

POPULATION_GID = "846450963"

POPULATION_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{POPULATION_SHEET_ID}/export"
    f"?format=csv&gid={POPULATION_GID}"
)

DEFAULT_DENOMINATOR = 100_000

DENOMINATOR_OPTIONS = [
    1_000,
    10_000,
    100_000,
    1_000_000,
]

MIN_VALID_YEAR = 2000
MAX_VALID_YEAR = 2100

DATA_LABEL_FONT_SIZE = 11

DEFAULT_COLORS = [
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


# ============================================================
# BASIC HELPERS
# ============================================================

def _clean_series(series):

    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _valid_text_mask(series):

    values = _clean_series(series)

    return (
        values.ne("")
        & values.ne("nan")
        & values.ne("NaT")
        & values.ne("None")
        & values.ne("-")
    )


def _safe_numeric(series):

    if series is None:
        return pd.Series(dtype=float)

    cleaned = (
        series
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.strip()
        .replace(
            {
                "": np.nan,
                "-": np.nan,
                "nan": np.nan,
                "NaN": np.nan,
                "None": np.nan,
                "NA": np.nan,
                "N/A": np.nan,
            }
        )
    )

    return pd.to_numeric(
        cleaned,
        errors="coerce",
    )


def _alphabetical(values):

    clean = []

    for value in values:

        text = str(value).strip()

        if (
            text
            and text not in {
                "nan",
                "NaT",
                "None",
                "-",
            }
        ):
            clean.append(text)

    return sorted(
        list(dict.fromkeys(clean)),
        key=lambda x: x.upper(),
    )


def _month_number(value):

    if pd.isna(value):
        return np.nan

    text = str(value).strip().lower()

    month_map = {
        "january": 1,
        "jan": 1,
        "1": 1,
        "01": 1,

        "february": 2,
        "feb": 2,
        "2": 2,
        "02": 2,

        "march": 3,
        "mar": 3,
        "3": 3,
        "03": 3,

        "april": 4,
        "apr": 4,
        "4": 4,
        "04": 4,

        "may": 5,
        "5": 5,
        "05": 5,

        "june": 6,
        "jun": 6,
        "6": 6,
        "06": 6,

        "july": 7,
        "jul": 7,
        "7": 7,
        "07": 7,

        "august": 8,
        "aug": 8,
        "8": 8,
        "08": 8,

        "september": 9,
        "sep": 9,
        "sept": 9,
        "9": 9,
        "09": 9,

        "october": 10,
        "oct": 10,
        "10": 10,

        "november": 11,
        "nov": 11,
        "11": 11,

        "december": 12,
        "dec": 12,
        "12": 12,
    }

    if text in month_map:
        return month_map[text]

    try:

        number = int(float(text))

        if 1 <= number <= 12:
            return number

    except Exception:
        pass

    return np.nan


def _prepare_case_data(df):

    if df is None or df.empty:
        return pd.DataFrame()

    temp = df.copy()

    # --------------------------------------------------------
    # YEAR
    # --------------------------------------------------------

    if "Year" in temp.columns:

        temp["Analysis_Year"] = pd.to_numeric(
            temp["Year"],
            errors="coerce",
        )

    elif "Reporting Date" in temp.columns:

        reporting_date = pd.to_datetime(
            temp["Reporting Date"],
            errors="coerce",
            dayfirst=True,
        )

        temp["Analysis_Year"] = (
            reporting_date.dt.year
        )

    else:

        temp["Analysis_Year"] = np.nan

    # --------------------------------------------------------
    # MONTH
    # --------------------------------------------------------

    if "Month" in temp.columns:

        temp["Analysis_Month"] = (
            temp["Month"]
            .map(_month_number)
        )

    elif "Reporting Date" in temp.columns:

        reporting_date = pd.to_datetime(
            temp["Reporting Date"],
            errors="coerce",
            dayfirst=True,
        )

        temp["Analysis_Month"] = (
            reporting_date.dt.month
        )

    else:

        temp["Analysis_Month"] = np.nan

    temp = temp[
        temp["Analysis_Year"].between(
            MIN_VALID_YEAR,
            MAX_VALID_YEAR,
        )
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    temp["Analysis_Year"] = (
        temp["Analysis_Year"]
        .astype(int)
    )

    valid_month = (
        temp["Analysis_Month"]
        .between(1, 12)
    )

    temp.loc[
        valid_month,
        "Analysis_Month"
    ] = (
        temp.loc[
            valid_month,
            "Analysis_Month"
        ]
        .astype(int)
    )

    return temp


# ============================================================
# POPULATION LOADER
# ============================================================

@st.cache_data(ttl=3600)
def _load_population_raw():

    population_df = pd.read_csv(
        POPULATION_CSV_URL
    )

    population_df.columns = [
        str(column).strip()
        for column in population_df.columns
    ]

    return population_df


def _find_ward_column(population_df):

    if (
        population_df is None
        or population_df.empty
    ):
        return None

    candidates = [
        "WARD",
        "Ward",
        "Ward Name",
        "WARD NAME",
        "ward",
    ]

    for candidate in candidates:

        if candidate in population_df.columns:
            return candidate

    for column in population_df.columns:

        normalized = (
            str(column)
            .strip()
            .lower()
            .replace("_", " ")
        )

        if normalized in {
            "ward",
            "ward name",
        }:
            return column

    return None


def _extract_population_year(column_name):

    text = str(column_name).strip()

    match = re.search(
        r"(20\d{2})",
        text,
    )

    if not match:
        return None

    year = int(
        match.group(1)
    )

    if (
        MIN_VALID_YEAR
        <= year
        <= MAX_VALID_YEAR
    ):
        return year

    return None


def _prepare_population_data(
    population_df,
):

    if (
        population_df is None
        or population_df.empty
    ):
        return (
            pd.DataFrame(),
            pd.DataFrame(),
            [],
        )

    source = population_df.copy()

    ward_column = _find_ward_column(
        source
    )

    if ward_column is None:

        return (
            pd.DataFrame(),
            pd.DataFrame(),
            [],
        )

    year_columns = {}

    for column in source.columns:

        if column == ward_column:
            continue

        year = _extract_population_year(
            column
        )

        if year is not None:

            # If duplicate year-like columns exist,
            # use the first detected column.
            if year not in year_columns:
                year_columns[year] = column

    if not year_columns:

        return (
            pd.DataFrame(),
            pd.DataFrame(),
            [],
        )

    source["WARD"] = (
        _clean_series(
            source[ward_column]
        )
    )

    source = source[
        source["WARD"].ne("")
        & source["WARD"].ne("nan")
        & source["WARD"].ne("NaT")
        & source["WARD"].ne("None")
    ].copy()

    # --------------------------------------------------------
    # REMOVE TOTAL / GRAND TOTAL ROWS
    # --------------------------------------------------------

    total_mask = (
        source["WARD"]
        .str.upper()
        .isin(
            {
                "TOTAL",
                "GRAND TOTAL",
                "MUMBAI TOTAL",
                "ALL",
            }
        )
    )

    source = source[
        ~total_mask
    ].copy()

    if source.empty:

        return (
            pd.DataFrame(),
            pd.DataFrame(),
            [],
        )

    available_years = sorted(
        year_columns.keys()
    )

    wide_rows = {
        "WARD": source["WARD"]
    }

    for year in available_years:

        original_column = (
            year_columns[year]
        )

        wide_rows[
            str(year)
        ] = _safe_numeric(
            source[original_column]
        )

    population_wide = pd.DataFrame(
        wide_rows
    )

    # --------------------------------------------------------
    # HANDLE DUPLICATE WARD ROWS
    # --------------------------------------------------------

    numeric_columns = [
        str(year)
        for year in available_years
    ]

    population_wide = (
        population_wide
        .groupby(
            "WARD",
            as_index=False,
        )[numeric_columns]
        .sum(
            min_count=1
        )
    )

    # --------------------------------------------------------
    # LONG FORMAT
    # --------------------------------------------------------

    population_long = (
        population_wide
        .melt(
            id_vars=["WARD"],
            value_vars=numeric_columns,
            var_name="Population_Year",
            value_name="Population",
        )
    )

    population_long[
        "Population_Year"
    ] = pd.to_numeric(
        population_long[
            "Population_Year"
        ],
        errors="coerce",
    )

    population_long[
        "Population"
    ] = pd.to_numeric(
        population_long[
            "Population"
        ],
        errors="coerce",
    )

    population_long = population_long[
        population_long[
            "Population_Year"
        ].notna()
    ].copy()

    population_long[
        "Population_Year"
    ] = (
        population_long[
            "Population_Year"
        ]
        .astype(int)
    )

    # Population must be > 0 for incidence.
    population_long.loc[
        population_long[
            "Population"
        ] <= 0,
        "Population"
    ] = np.nan

    return (
        population_wide,
        population_long,
        available_years,
    )


# ============================================================
# POPULATION MATCHING
# ============================================================

def _population_for_ward_year(
    population_long,
    ward,
    analysis_year,
):

    if (
        population_long is None
        or population_long.empty
    ):
        return (
            np.nan,
            None,
            "Population unavailable",
        )

    ward_text = str(
        ward
    ).strip()

    try:
        year_value = int(
            analysis_year
        )

    except Exception:

        return (
            np.nan,
            None,
            "Invalid analysis year",
        )

    ward_population = (
        population_long[
            population_long[
                "WARD"
            ].astype(str).str.strip()
            == ward_text
        ]
        .copy()
    )

    ward_population = (
        ward_population[
            ward_population[
                "Population"
            ].notna()
            & (
                ward_population[
                    "Population"
                ]
                > 0
            )
        ]
    )

    if ward_population.empty:

        return (
            np.nan,
            None,
            "Population unavailable",
        )

    exact = ward_population[
        ward_population[
            "Population_Year"
        ]
        == year_value
    ]

    if not exact.empty:

        row = exact.iloc[0]

        return (
            float(
                row["Population"]
            ),
            int(
                row["Population_Year"]
            ),
            "Exact year",
        )

    # --------------------------------------------------------
    # FIRST FALLBACK:
    # Closest previous available year
    # --------------------------------------------------------

    previous = ward_population[
        ward_population[
            "Population_Year"
        ]
        < year_value
    ]

    if not previous.empty:

        selected_year = int(
            previous[
                "Population_Year"
            ].max()
        )

        row = previous[
            previous[
                "Population_Year"
            ]
            == selected_year
        ].iloc[0]

        return (
            float(
                row["Population"]
            ),
            selected_year,
            "Previous-year fallback",
        )

    # --------------------------------------------------------
    # SECOND FALLBACK:
    # No earlier population exists.
    # Use nearest future available population.
    # --------------------------------------------------------

    future = ward_population[
        ward_population[
            "Population_Year"
        ]
        > year_value
    ]

    if not future.empty:

        selected_year = int(
            future[
                "Population_Year"
            ].min()
        )

        row = future[
            future[
                "Population_Year"
            ]
            == selected_year
        ].iloc[0]

        return (
            float(
                row["Population"]
            ),
            selected_year,
            "Future-year fallback",
        )

    return (
        np.nan,
        None,
        "Population unavailable",
    )


# ============================================================
# INCIDENCE CALCULATION
# ============================================================

def _ward_year_case_counts(
    source,
):

    if (
        source is None
        or source.empty
        or "Ward Name" not in source.columns
    ):
        return pd.DataFrame()

    temp = source.copy()

    temp["Ward Name"] = (
        _clean_series(
            temp["Ward Name"]
        )
    )

    temp = temp[
        temp["Ward Name"].ne("")
        & temp["Ward Name"].ne("nan")
        & temp["Ward Name"].ne("NaT")
        & temp["Ward Name"].ne("None")
    ]

    if temp.empty:
        return pd.DataFrame()

    return (
        temp
        .groupby(
            [
                "Ward Name",
                "Analysis_Year",
            ],
            observed=True,
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )


def _attach_population(
    case_table,
    population_long,
    denominator,
):

    if (
        case_table is None
        or case_table.empty
    ):
        return pd.DataFrame()

    result = case_table.copy()

    populations = []
    years_used = []
    statuses = []

    for _, row in result.iterrows():

        population, year_used, status = (
            _population_for_ward_year(
                population_long,
                row["Ward Name"],
                row["Analysis_Year"],
            )
        )

        populations.append(
            population
        )

        years_used.append(
            year_used
        )

        statuses.append(
            status
        )

    result[
        "Population"
    ] = populations

    result[
        "Population Year Used"
    ] = years_used

    result[
        "Population Match Status"
    ] = statuses

    result[
        "Incidence Rate"
    ] = np.where(
        result["Population"].notna()
        & result["Population"].gt(0),
        (
            result["Cases"]
            / result["Population"]
            * denominator
        ),
        np.nan,
    )

    result[
        "Incidence Rate"
    ] = (
        result[
            "Incidence Rate"
        ]
        .round(2)
    )

    return result


def _aggregate_incidence_by_year(
    source,
    population_long,
    denominator,
):

    ward_year = (
        _ward_year_case_counts(
            source
        )
    )

    incidence = _attach_population(
        ward_year,
        population_long,
        denominator,
    )

    if incidence.empty:
        return pd.DataFrame()

    rows = []

    for year, group in incidence.groupby(
        "Analysis_Year",
        observed=True,
    ):

        valid = group[
            group["Population"].notna()
            & group["Population"].gt(0)
        ]

        if valid.empty:

            population = np.nan
            cases = int(
                group["Cases"].sum()
            )

            rate = np.nan

        else:

            population = float(
                valid["Population"].sum()
            )

            cases = int(
                valid["Cases"].sum()
            )

            rate = (
                cases
                / population
                * denominator
            )

        rows.append(
            {
                "Year": int(year),
                "Cases": cases,
                "Population": population,
                "Incidence Rate": (
                    round(rate, 2)
                    if pd.notna(rate)
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(
        rows
    ).sort_values(
        "Year"
    ).reset_index(
        drop=True
    )


# ============================================================
# MULTI SELECT
# ============================================================

def _checkbox_multiselect(
    label,
    options,
    key_prefix,
    default_count=None,
):

    options = list(options)

    if not options:
        return []

    if default_count is None:
        default_count = len(
            options
        )

    default_count = min(
        default_count,
        len(options),
    )

    select_all_key = (
        f"{key_prefix}_select_all"
    )

    init_key = (
        f"{key_prefix}_initialized"
    )

    option_keys = [
        f"{key_prefix}_option_{index}"
        for index in range(
            len(options)
        )
    ]

    if init_key not in st.session_state:

        st.session_state[
            init_key
        ] = True

        select_all_default = (
            default_count
            == len(options)
        )

        st.session_state[
            select_all_key
        ] = select_all_default

        for index, key in enumerate(
            option_keys
        ):

            st.session_state[
                key
            ] = (
                index
                < default_count
            )

    def select_all_changed():

        new_value = bool(
            st.session_state.get(
                select_all_key,
                False,
            )
        )

        for key in option_keys:

            st.session_state[
                key
            ] = new_value

    def individual_changed():

        all_selected = all(
            bool(
                st.session_state.get(
                    key,
                    False,
                )
            )
            for key in option_keys
        )

        st.session_state[
            select_all_key
        ] = all_selected

    selected = []

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

        for index, option in enumerate(
            options
        ):

            checked = st.checkbox(
                str(option),
                key=option_keys[
                    index
                ],
                on_change=individual_changed,
            )

            if checked:
                selected.append(
                    option
                )

    return selected


# ============================================================
# CHART HELPERS
# ============================================================

def _chart_legend(
    title=None,
):

    return alt.Legend(
        title=title,
        orient="bottom",
        direction="horizontal",
        columns=6,
        labelFontSize=9,
        titleFontSize=10,
        symbolSize=70,
        labelLimit=220,
        columnPadding=8,
        rowPadding=4,
    )


def _render_bar_chart(
    dataframe,
    x_column,
    y_column,
    title,
    y_title=None,
    height=430,
):

    if (
        dataframe is None
        or dataframe.empty
        or x_column not in dataframe.columns
        or y_column not in dataframe.columns
    ):
        return

    chart_df = dataframe.copy()

    chart_df = chart_df[
        chart_df[y_column].notna()
    ]

    if chart_df.empty:
        return

    chart_df[x_column] = (
        chart_df[x_column]
        .astype(str)
    )

    order = (
        chart_df[x_column]
        .tolist()
    )

    colors = [
        DEFAULT_COLORS[
            index
            % len(DEFAULT_COLORS)
        ]
        for index in range(
            len(order)
        )
    ]

    scale = alt.Scale(
        domain=order,
        range=colors,
    )

    bars = (
        alt.Chart(
            chart_df
        )
        .mark_bar()
        .encode(
            x=alt.X(
                f"{x_column}:N",
                sort=order,
                axis=alt.Axis(
                    title=x_column,
                    labelAngle=-45,
                    labelLimit=180,
                ),
            ),
            y=alt.Y(
                f"{y_column}:Q",
                axis=alt.Axis(
                    title=(
                        y_title
                        or y_column
                    )
                ),
            ),
            color=alt.Color(
                f"{x_column}:N",
                scale=scale,
                legend=_chart_legend(
                    x_column
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{x_column}:N",
                    title=x_column,
                ),
                alt.Tooltip(
                    f"{y_column}:Q",
                    title=(
                        y_title
                        or y_column
                    ),
                    format=",.2f",
                ),
            ],
        )
        .properties(
            height=height,
            title=title,
        )
    )

    chart = bars

    if data_labels_enabled():

        labels = (
            alt.Chart(
                chart_df
            )
            .mark_text(
                dy=-8,
                fontSize=DATA_LABEL_FONT_SIZE,
                fontWeight="bold",
            )
            .encode(
                x=alt.X(
                    f"{x_column}:N",
                    sort=order,
                ),
                y=alt.Y(
                    f"{y_column}:Q"
                ),
                text=alt.Text(
                    f"{y_column}:Q",
                    format=",.2f",
                ),
                color=alt.Color(
                    f"{x_column}:N",
                    scale=scale,
                    legend=None,
                ),
            )
        )

        chart = bars + labels

    st.altair_chart(
        chart,
        use_container_width=True,
    )


def _render_multi_line_chart(
    dataframe,
    x_column,
    series_column,
    value_column,
    title,
    y_title,
    height=460,
):

    if (
        dataframe is None
        or dataframe.empty
    ):
        return

    required = {
        x_column,
        series_column,
        value_column,
    }

    if not required.issubset(
        dataframe.columns
    ):
        return

    chart_df = dataframe.copy()

    chart_df = chart_df[
        chart_df[
            value_column
        ].notna()
    ]

    if chart_df.empty:
        return

    series_order = (
        chart_df[
            series_column
        ]
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    colors = [
        DEFAULT_COLORS[
            index
            % len(DEFAULT_COLORS)
        ]
        for index in range(
            len(series_order)
        )
    ]

    scale = alt.Scale(
        domain=series_order,
        range=colors,
    )

    lines = (
        alt.Chart(
            chart_df
        )
        .mark_line(
            point=True,
            strokeWidth=3,
        )
        .encode(
            x=alt.X(
                f"{x_column}:N",
                sort=None,
                axis=alt.Axis(
                    title=x_column,
                    labelAngle=-45,
                    labelLimit=150,
                ),
            ),
            y=alt.Y(
                f"{value_column}:Q",
                axis=alt.Axis(
                    title=y_title
                ),
            ),
            color=alt.Color(
                f"{series_column}:N",
                sort=series_order,
                scale=scale,
                legend=_chart_legend(
                    series_column
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{x_column}:N",
                    title=x_column,
                ),
                alt.Tooltip(
                    f"{series_column}:N",
                    title=series_column,
                ),
                alt.Tooltip(
                    f"{value_column}:Q",
                    title=y_title,
                    format=",.2f",
                ),
            ],
        )
        .properties(
            height=height,
            title=title,
        )
    )

    chart = lines

    if data_labels_enabled():

        labels = (
            alt.Chart(
                chart_df
            )
            .mark_text(
                dy=-9,
                fontSize=DATA_LABEL_FONT_SIZE,
                fontWeight="bold",
            )
            .encode(
                x=alt.X(
                    f"{x_column}:N",
                    sort=None,
                ),
                y=alt.Y(
                    f"{value_column}:Q"
                ),
                text=alt.Text(
                    f"{value_column}:Q",
                    format=",.2f",
                ),
                color=alt.Color(
                    f"{series_column}:N",
                    scale=scale,
                    legend=None,
                ),
            )
        )

        chart = lines + labels

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# DISEASE / WARD INCIDENCE
# ============================================================

def _disease_ward_incidence(
    source,
    population_long,
    denominator,
    selected_diseases=None,
    selected_wards=None,
):

    required = {
        "Ward Name",
        "Disease",
        "Analysis_Year",
    }

    if (
        source is None
        or source.empty
        or not required.issubset(
            source.columns
        )
    ):
        return pd.DataFrame()

    temp = source.copy()

    temp["Ward Name"] = (
        _clean_series(
            temp["Ward Name"]
        )
    )

    temp["Disease"] = (
        _clean_series(
            temp["Disease"]
        )
    )

    temp = temp[
        temp["Ward Name"].ne("")
        & temp["Disease"].ne("")
        & temp["Ward Name"].ne("nan")
        & temp["Disease"].ne("nan")
    ]

    if selected_diseases:

        temp = temp[
            temp["Disease"].isin(
                selected_diseases
            )
        ]

    if selected_wards:

        temp = temp[
            temp["Ward Name"].isin(
                selected_wards
            )
        ]

    if temp.empty:
        return pd.DataFrame()

    grouped = (
        temp
        .groupby(
            [
                "Ward Name",
                "Disease",
                "Analysis_Year",
            ],
            observed=True,
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    rows = []

    for _, row in grouped.iterrows():

        population, year_used, status = (
            _population_for_ward_year(
                population_long,
                row["Ward Name"],
                row["Analysis_Year"],
            )
        )

        if (
            pd.notna(population)
            and population > 0
        ):

            incidence = (
                row["Cases"]
                / population
                * denominator
            )

        else:

            incidence = np.nan

        rows.append(
            {
                "Ward": row[
                    "Ward Name"
                ],
                "Disease": row[
                    "Disease"
                ],
                "Year": int(
                    row[
                        "Analysis_Year"
                    ]
                ),
                "Cases": int(
                    row["Cases"]
                ),
                "Population": population,
                "Population Year Used": (
                    year_used
                ),
                "Population Match Status": (
                    status
                ),
                "Incidence Rate": (
                    round(
                        incidence,
                        2,
                    )
                    if pd.notna(
                        incidence
                    )
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# MONTHLY INCIDENCE
# ============================================================

def _monthly_incidence(
    source,
    population_long,
    denominator,
):

    required = {
        "Ward Name",
        "Analysis_Year",
        "Analysis_Month",
    }

    if (
        source is None
        or source.empty
        or not required.issubset(
            source.columns
        )
    ):
        return pd.DataFrame()

    temp = source[
        source[
            "Analysis_Month"
        ].between(
            1,
            12,
        )
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    temp["Ward Name"] = (
        _clean_series(
            temp["Ward Name"]
        )
    )

    temp = temp[
        temp["Ward Name"].ne("")
        & temp["Ward Name"].ne("nan")
    ]

    grouped = (
        temp
        .groupby(
            [
                "Ward Name",
                "Analysis_Year",
                "Analysis_Month",
            ],
            observed=True,
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    rows = []

    for _, row in grouped.iterrows():

        population, year_used, status = (
            _population_for_ward_year(
                population_long,
                row["Ward Name"],
                row["Analysis_Year"],
            )
        )

        if (
            pd.notna(population)
            and population > 0
        ):

            rate = (
                row["Cases"]
                / population
                * denominator
            )

        else:
            rate = np.nan

        month = int(
            row["Analysis_Month"]
        )

        year = int(
            row["Analysis_Year"]
        )

        rows.append(
            {
                "Ward": row[
                    "Ward Name"
                ],
                "Year": year,
                "Month": month,
                "Period": (
                    f"{pd.Timestamp(2000, month, 1).strftime('%b')}"
                    f"-{year}"
                ),
                "Cases": int(
                    row["Cases"]
                ),
                "Population": population,
                "Population Year Used": (
                    year_used
                ),
                "Population Match Status": (
                    status
                ),
                "Incidence Rate": (
                    round(
                        rate,
                        2,
                    )
                    if pd.notna(rate)
                    else np.nan
                ),
            }
        )

    result = pd.DataFrame(
        rows
    )

    if result.empty:
        return result

    return result.sort_values(
        [
            "Year",
            "Month",
            "Ward",
        ]
    ).reset_index(
        drop=True
    )


# ============================================================
# STATISTICAL THRESHOLDS
# ============================================================

def _monthly_case_series(
    source,
):

    if (
        source is None
        or source.empty
    ):
        return pd.DataFrame()

    required = {
        "Analysis_Year",
        "Analysis_Month",
    }

    if not required.issubset(
        source.columns
    ):
        return pd.DataFrame()

    temp = source[
        source[
            "Analysis_Month"
        ].between(
            1,
            12,
        )
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    monthly = (
        temp
        .groupby(
            [
                "Analysis_Year",
                "Analysis_Month",
            ],
            observed=True,
        )
        .size()
        .reset_index(
            name="Cases"
        )
    )

    monthly["Date"] = pd.to_datetime(
        dict(
            year=monthly[
                "Analysis_Year"
            ].astype(int),
            month=monthly[
                "Analysis_Month"
            ].astype(int),
            day=1,
        )
    )

    first_date = monthly[
        "Date"
    ].min()

    last_date = monthly[
        "Date"
    ].max()

    complete_dates = pd.date_range(
        start=first_date,
        end=last_date,
        freq="MS",
    )

    complete = pd.DataFrame(
        {
            "Date": complete_dates
        }
    )

    complete[
        "Analysis_Year"
    ] = complete[
        "Date"
    ].dt.year

    complete[
        "Analysis_Month"
    ] = complete[
        "Date"
    ].dt.month

    complete = complete.merge(
        monthly[
            [
                "Analysis_Year",
                "Analysis_Month",
                "Cases",
            ]
        ],
        how="left",
        on=[
            "Analysis_Year",
            "Analysis_Month",
        ],
    )

    complete[
        "Cases"
    ] = (
        complete[
            "Cases"
        ]
        .fillna(0)
        .astype(int)
    )

    complete[
        "Period"
    ] = (
        complete[
            "Date"
        ]
        .dt.strftime(
            "%b-%Y"
        )
    )

    return complete


def _apply_baseline_years(
    source,
    option,
):

    if (
        source is None
        or source.empty
    ):
        return source

    years = sorted(
        source[
            "Analysis_Year"
        ]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if not years:
        return source

    baseline_map = {
        "Last 2 Years": 2,
        "Last 3 Years": 3,
        "Last 5 Years": 5,
    }

    if option == "All Available Years":
        return source.copy()

    count = baseline_map.get(
        option
    )

    if count is None:
        return source.copy()

    selected_years = (
        years[-count:]
    )

    return source[
        source[
            "Analysis_Year"
        ].isin(
            selected_years
        )
    ].copy()


def _threshold_statistics(
    monthly,
):

    if (
        monthly is None
        or monthly.empty
    ):
        return None

    values = pd.to_numeric(
        monthly["Cases"],
        errors="coerce",
    ).dropna()

    if values.empty:
        return None

    mean = float(
        values.mean()
    )

    if len(values) > 1:

        sd = float(
            values.std(
                ddof=1
            )
        )

    else:
        sd = 0.0

    return {
        "Mean": mean,
        "SD": sd,
        "Mean + 1 SD": (
            mean + sd
        ),
        "Mean + 2 SD": (
            mean + 2 * sd
        ),
        "Mean + 3 SD": (
            mean + 3 * sd
        ),
    }


def _render_threshold_chart(
    monthly,
    statistics,
    title,
):

    if (
        monthly is None
        or monthly.empty
        or statistics is None
    ):
        return

    chart_df = monthly[
        [
            "Period",
            "Cases",
        ]
    ].copy()

    chart_df[
        "Mean"
    ] = statistics[
        "Mean"
    ]

    chart_df[
        "Mean + 1 SD"
    ] = statistics[
        "Mean + 1 SD"
    ]

    chart_df[
        "Mean + 2 SD"
    ] = statistics[
        "Mean + 2 SD"
    ]

    chart_df[
        "Mean + 3 SD"
    ] = statistics[
        "Mean + 3 SD"
    ]

    long_df = chart_df.melt(
        id_vars=[
            "Period"
        ],
        value_vars=[
            "Cases",
            "Mean",
            "Mean + 1 SD",
            "Mean + 2 SD",
            "Mean + 3 SD",
        ],
        var_name="Series",
        value_name="Value",
    )

    series_order = [
        "Cases",
        "Mean",
        "Mean + 1 SD",
        "Mean + 2 SD",
        "Mean + 3 SD",
    ]

    colors = [
        "#1F77B4",
        "#2CA02C",
        "#FFBF00",
        "#FF7F0E",
        "#D62728",
    ]

    scale = alt.Scale(
        domain=series_order,
        range=colors,
    )

    lines = (
        alt.Chart(
            long_df
        )
        .mark_line(
            strokeWidth=3,
        )
        .encode(
            x=alt.X(
                "Period:N",
                sort=None,
                axis=alt.Axis(
                    title="Period",
                    labelAngle=-45,
                    labelLimit=140,
                ),
            ),
            y=alt.Y(
                "Value:Q",
                axis=alt.Axis(
                    title="Cases"
                ),
            ),
            color=alt.Color(
                "Series:N",
                sort=series_order,
                scale=scale,
                legend=_chart_legend(
                    "Series"
                ),
            ),
            strokeDash=alt.StrokeDash(
                "Series:N",
                scale=alt.Scale(
                    domain=series_order,
                    range=[
                        [1, 0],
                        [8, 4],
                        [8, 4],
                        [8, 4],
                        [8, 4],
                    ],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip(
                    "Period:N",
                    title="Period",
                ),
                alt.Tooltip(
                    "Series:N",
                    title="Series",
                ),
                alt.Tooltip(
                    "Value:Q",
                    title="Value",
                    format=",.2f",
                ),
            ],
        )
        .properties(
            height=470,
            title=title,
        )
    )

    points_df = long_df[
        long_df[
            "Series"
        ]
        == "Cases"
    ]

    points = (
        alt.Chart(
            points_df
        )
        .mark_point(
            filled=True,
            size=65,
        )
        .encode(
            x=alt.X(
                "Period:N",
                sort=None,
            ),
            y=alt.Y(
                "Value:Q"
            ),
            color=alt.Color(
                "Series:N",
                scale=scale,
                legend=None,
            ),
        )
    )

    chart = (
        lines
        + points
    )

    if data_labels_enabled():

        labels = (
            alt.Chart(
                points_df
            )
            .mark_text(
                dy=-10,
                fontSize=11,
                fontWeight="bold",
            )
            .encode(
                x=alt.X(
                    "Period:N",
                    sort=None,
                ),
                y=alt.Y(
                    "Value:Q"
                ),
                text=alt.Text(
                    "Value:Q",
                    format=",.0f",
                ),
                color=alt.Color(
                    "Series:N",
                    scale=scale,
                    legend=None,
                ),
            )
        )

        chart = (
            chart
            + labels
        )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# POPULATION AUDIT TABLE
# ============================================================

def _population_audit(
    case_df,
    population_long,
):

    if (
        case_df is None
        or case_df.empty
        or "Ward Name" not in case_df.columns
    ):
        return pd.DataFrame()

    combinations = (
        case_df[
            [
                "Ward Name",
                "Analysis_Year",
            ]
        ]
        .copy()
    )

    combinations[
        "Ward Name"
    ] = _clean_series(
        combinations[
            "Ward Name"
        ]
    )

    combinations = (
        combinations[
            combinations[
                "Ward Name"
            ].ne("")
        ]
        .drop_duplicates()
        .sort_values(
            [
                "Analysis_Year",
                "Ward Name",
            ]
        )
    )

    rows = []

    for _, row in combinations.iterrows():

        population, year_used, status = (
            _population_for_ward_year(
                population_long,
                row["Ward Name"],
                row["Analysis_Year"],
            )
        )

        rows.append(
            {
                "Ward": row[
                    "Ward Name"
                ],
                "Analysis Year": int(
                    row[
                        "Analysis_Year"
                    ]
                ),
                "Population": population,
                "Population Year Used": (
                    year_used
                ),
                "Status": status,
            }
        )

    return pd.DataFrame(
        rows
    )


# ============================================================
# MAIN PAGE
# ============================================================

def render_incidence(df):

    st.subheader(
        "📐 Incidence & Statistical Surveillance"
    )

    if df is None or df.empty:

        st.warning(
            "No records available for the selected filters."
        )

        return

    st.caption(
        "Population-based incidence analysis and statistical "
        "surveillance thresholds based on the selected "
        "Global Dashboard Filters."
    )

    # ========================================================
    # LOAD CASE DATA
    # ========================================================

    case_df = _prepare_case_data(
        df
    )

    if case_df.empty:

        st.warning(
            "Valid Year information is required for "
            "incidence analysis."
        )

        return

    # ========================================================
    # LOAD POPULATION DATA
    # ========================================================

    population_error = None

    try:

        population_raw = (
            _load_population_raw()
        )

        (
            population_wide,
            population_long,
            population_years,
        ) = _prepare_population_data(
            population_raw
        )

    except Exception as error:

        population_error = error

        population_raw = (
            pd.DataFrame()
        )

        population_wide = (
            pd.DataFrame()
        )

        population_long = (
            pd.DataFrame()
        )

        population_years = []

    # ========================================================
    # 1. POPULATION & INCIDENCE SUMMARY
    # ========================================================

    st.markdown(
        "### 1. 📊 Population & Incidence Summary"
    )

    denominator = st.selectbox(
        "Incidence Rate Per Population",
        options=DENOMINATOR_OPTIONS,
        index=DENOMINATOR_OPTIONS.index(
            DEFAULT_DENOMINATOR
        ),
        format_func=lambda value:
        f"Per {value:,} Population",
        key=(
            "phase8b_incidence_denominator"
        ),
    )

    st.caption(
        f"All incidence rates on this page are currently "
        f"expressed per {denominator:,} population."
    )

    case_years = sorted(
        case_df[
            "Analysis_Year"
        ]
        .unique()
        .tolist()
    )

    valid_population_wards = (
        population_long[
            "WARD"
        ].nunique()
        if not population_long.empty
        else 0
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Filtered Records",
            f"{len(case_df):,}",
        )

    with c2:

        st.metric(
            "Case Years",
            f"{len(case_years):,}",
        )

    with c3:

        st.metric(
            "Population Wards",
            f"{valid_population_wards:,}",
        )

    with c4:

        if population_years:

            st.metric(
                "Latest Population Year",
                f"{max(population_years)}",
            )

        else:

            st.metric(
                "Latest Population Year",
                "Unavailable",
            )

    # ========================================================
    # 2. POPULATION DATA STATUS
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. 👥 Population Data Status"
    )

    if population_error is not None:

        st.error(
            "Population data could not be loaded from "
            "the Population worksheet."
        )

        st.caption(
            str(
                population_error
            )
        )

    elif population_long.empty:

        st.warning(
            "Population data is unavailable or no valid "
            "population year columns were detected."
        )

    else:

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Population Wards",
                f"{population_wide['WARD'].nunique():,}",
            )

        with c2:

            st.metric(
                "Population Years",
                f"{len(population_years):,}",
            )

        with c3:

            st.metric(
                "First Population Year",
                str(
                    min(
                        population_years
                    )
                ),
            )

        with c4:

            st.metric(
                "Latest Population Year",
                str(
                    max(
                        population_years
                    )
                ),
            )

        st.write(
            "**Detected Population Years:** "
            + ", ".join(
                str(year)
                for year in population_years
            )
        )

        with st.expander(
            "📋 View Complete Population Dataset",
            expanded=False,
        ):

            population_display = (
                population_wide.copy()
            )

            for column in (
                population_display.columns
            ):

                if column == "WARD":
                    continue

                population_display[
                    column
                ] = (
                    population_display[
                        column
                    ]
                    .round(0)
                )

            st.dataframe(
                population_display,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 3. POPULATION TREND BY WARD
    # ========================================================

    st.divider()

    st.markdown(
        "### 3. 📈 Population Trend by Ward"
    )

    if not population_long.empty:

        population_wards = (
            _alphabetical(
                population_long[
                    "WARD"
                ].unique()
            )
        )

        default_count = min(
            5,
            len(
                population_wards
            ),
        )

        selected_population_wards = (
            _checkbox_multiselect(
                "Select Ward(s)",
                population_wards,
                "phase8b_population_wards",
                default_count=default_count,
            )
        )

        if selected_population_wards:

            population_chart = (
                population_long[
                    population_long[
                        "WARD"
                    ].isin(
                        selected_population_wards
                    )
                ]
                .copy()
            )

            population_chart[
                "Year"
            ] = (
                population_chart[
                    "Population_Year"
                ]
                .astype(int)
                .astype(str)
            )

            _render_multi_line_chart(
                dataframe=population_chart,
                x_column="Year",
                series_column="WARD",
                value_column="Population",
                title=(
                    "Ward-wise Population Trend"
                ),
                y_title="Population",
                height=450,
            )

            st.dataframe(
                population_chart[
                    [
                        "WARD",
                        "Population_Year",
                        "Population",
                    ]
                ].sort_values(
                    [
                        "Population_Year",
                        "WARD",
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Please select at least one ward."
            )

    else:

        st.info(
            "Population trend cannot be displayed "
            "because population data is unavailable."
        )

    # ========================================================
    # 4. OVERALL WARD-WISE INCIDENCE
    # ========================================================

    st.divider()

    st.markdown(
        "### 4. 📍 Overall Ward-wise Incidence Rate"
    )

    if (
        "Ward Name" in case_df.columns
        and not population_long.empty
    ):

        ward_year_cases = (
            _ward_year_case_counts(
                case_df
            )
        )

        ward_incidence = (
            _attach_population(
                ward_year_cases,
                population_long,
                denominator,
            )
        )

        if not ward_incidence.empty:

            incidence_years = sorted(
                ward_incidence[
                    "Analysis_Year"
                ]
                .unique()
                .tolist()
            )

            selected_incidence_year = (
                st.selectbox(
                    "Select Analysis Year",
                    options=incidence_years,
                    index=(
                        len(
                            incidence_years
                        )
                        - 1
                    ),
                    key=(
                        "phase8b_ward_incidence_year"
                    ),
                )
            )

            selected_year_incidence = (
                ward_incidence[
                    ward_incidence[
                        "Analysis_Year"
                    ]
                    == selected_incidence_year
                ]
                .copy()
            )

            selected_year_incidence = (
                selected_year_incidence
                .sort_values(
                    "Incidence Rate",
                    ascending=False,
                    na_position="last",
                )
            )

            _render_bar_chart(
                dataframe=selected_year_incidence,
                x_column="Ward Name",
                y_column="Incidence Rate",
                title=(
                    f"Ward-wise Incidence Rate — "
                    f"{selected_incidence_year}"
                ),
                y_title=(
                    f"Incidence per "
                    f"{denominator:,}"
                ),
                height=460,
            )

            display = (
                selected_year_incidence[
                    [
                        "Ward Name",
                        "Cases",
                        "Population",
                        "Population Year Used",
                        "Population Match Status",
                        "Incidence Rate",
                    ]
                ]
                .copy()
            )

            display = display.rename(
                columns={
                    "Ward Name": "Ward",
                    "Incidence Rate": (
                        f"Incidence / "
                        f"{denominator:,}"
                    ),
                }
            )

            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True,
            )

    else:

        st.info(
            "Ward and population information is required "
            "for ward-wise incidence analysis."
        )

    # ========================================================
    # 5. DISEASE-WISE INCIDENCE ANALYSIS
    # ========================================================

    st.divider()

    st.markdown(
        "### 5. 🦠 Disease-wise Incidence Analysis"
    )

    if (
        "Disease" in case_df.columns
        and "Ward Name" in case_df.columns
        and not population_long.empty
    ):

        disease_values = (
            _clean_series(
                case_df[
                    "Disease"
                ]
            )
        )

        disease_values = (
            disease_values[
                disease_values.ne("")
                & disease_values.ne("nan")
                & disease_values.ne("NaT")
                & disease_values.ne("None")
            ]
        )

        disease_options = (
            disease_values
            .value_counts()
            .index
            .tolist()
        )

        selected_diseases = (
            _checkbox_multiselect(
                "Select Disease(s)",
                disease_options,
                "phase8b_diseases",
                default_count=min(
                    5,
                    len(
                        disease_options
                    ),
                ),
            )
        )

        if selected_diseases:

            disease_incidence = (
                _disease_ward_incidence(
                    case_df,
                    population_long,
                    denominator,
                    selected_diseases=(
                        selected_diseases
                    ),
                )
            )

            if not disease_incidence.empty:

                disease_years = sorted(
                    disease_incidence[
                        "Year"
                    ]
                    .unique()
                    .tolist()
                )

                selected_disease_year = (
                    st.selectbox(
                        "Disease Analysis Year",
                        options=disease_years,
                        index=(
                            len(
                                disease_years
                            )
                            - 1
                        ),
                        key=(
                            "phase8b_disease_year"
                        ),
                    )
                )

                disease_year_df = (
                    disease_incidence[
                        disease_incidence[
                            "Year"
                        ]
                        == selected_disease_year
                    ]
                    .copy()
                )

                # Aggregate ward rates by calculating
                # cases / summed valid ward populations.

                disease_summary_rows = []

                for disease in (
                    selected_diseases
                ):

                    group = (
                        disease_year_df[
                            disease_year_df[
                                "Disease"
                            ]
                            == disease
                        ]
                    )

                    valid = group[
                        group[
                            "Population"
                        ].notna()
                        & group[
                            "Population"
                        ].gt(0)
                    ]

                    if valid.empty:
                        continue

                    cases = int(
                        valid[
                            "Cases"
                        ].sum()
                    )

                    population = float(
                        valid[
                            "Population"
                        ].sum()
                    )

                    rate = (
                        cases
                        / population
                        * denominator
                    )

                    disease_summary_rows.append(
                        {
                            "Disease": disease,
                            "Cases": cases,
                            "Population": population,
                            "Incidence Rate": round(
                                rate,
                                2,
                            ),
                        }
                    )

                disease_summary = (
                    pd.DataFrame(
                        disease_summary_rows
                    )
                )

                if not disease_summary.empty:

                    disease_summary = (
                        disease_summary
                        .sort_values(
                            "Incidence Rate",
                            ascending=False,
                        )
                    )

                    _render_bar_chart(
                        dataframe=disease_summary,
                        x_column="Disease",
                        y_column="Incidence Rate",
                        title=(
                            "Selected Disease "
                            "Incidence Comparison"
                        ),
                        y_title=(
                            f"Incidence per "
                            f"{denominator:,}"
                        ),
                        height=450,
                    )

                    st.dataframe(
                        disease_summary,
                        use_container_width=True,
                        hide_index=True,
                    )

        else:

            st.info(
                "Please select at least one disease."
            )

    else:

        st.info(
            "Disease, Ward and Population information "
            "is required for disease-wise incidence analysis."
        )

    # ========================================================
    # 6. WARD × DISEASE INCIDENCE COMPARISON
    # ========================================================

    st.divider()

    st.markdown(
        "### 6. 📊 Ward × Disease Incidence Comparison"
    )

    if (
        "Disease" in case_df.columns
        and "Ward Name" in case_df.columns
        and not population_long.empty
    ):

        ward_options = (
            _alphabetical(
                _clean_series(
                    case_df[
                        "Ward Name"
                    ]
                ).unique()
            )
        )

        disease_options_2 = (
            _clean_series(
                case_df[
                    "Disease"
                ]
            )
        )

        disease_options_2 = (
            disease_options_2[
                disease_options_2.ne("")
                & disease_options_2.ne("nan")
            ]
            .value_counts()
            .index
            .tolist()
        )

        c1, c2 = st.columns(2)

        with c1:

            selected_compare_wards = (
                _checkbox_multiselect(
                    "Select Ward(s) for Comparison",
                    ward_options,
                    "phase8b_compare_wards",
                    default_count=min(
                        5,
                        len(
                            ward_options
                        ),
                    ),
                )
            )

        with c2:

            selected_compare_diseases = (
                _checkbox_multiselect(
                    "Select Disease(s) for Comparison",
                    disease_options_2,
                    "phase8b_compare_diseases",
                    default_count=min(
                        3,
                        len(
                            disease_options_2
                        ),
                    ),
                )
            )

        if (
            selected_compare_wards
            and selected_compare_diseases
        ):

            comparison = (
                _disease_ward_incidence(
                    case_df,
                    population_long,
                    denominator,
                    selected_diseases=(
                        selected_compare_diseases
                    ),
                    selected_wards=(
                        selected_compare_wards
                    ),
                )
            )

            if not comparison.empty:

                comparison_years = (
                    sorted(
                        comparison[
                            "Year"
                        ]
                        .unique()
                        .tolist()
                    )
                )

                selected_compare_year = (
                    st.selectbox(
                        "Comparison Year",
                        options=(
                            comparison_years
                        ),
                        index=(
                            len(
                                comparison_years
                            )
                            - 1
                        ),
                        key=(
                            "phase8b_compare_year"
                        ),
                    )
                )

                comparison_year_df = (
                    comparison[
                        comparison[
                            "Year"
                        ]
                        == selected_compare_year
                    ]
                    .copy()
                )

                comparison_year_df[
                    "Ward × Disease"
                ] = (
                    comparison_year_df[
                        "Ward"
                    ]
                    + " | "
                    + comparison_year_df[
                        "Disease"
                    ]
                )

                _render_bar_chart(
                    dataframe=(
                        comparison_year_df
                    ),
                    x_column=(
                        "Ward × Disease"
                    ),
                    y_column=(
                        "Incidence Rate"
                    ),
                    title=(
                        "Ward × Disease "
                        "Incidence Comparison"
                    ),
                    y_title=(
                        f"Incidence per "
                        f"{denominator:,}"
                    ),
                    height=500,
                )

                st.dataframe(
                    comparison_year_df[
                        [
                            "Ward",
                            "Disease",
                            "Year",
                            "Cases",
                            "Population",
                            "Population Year Used",
                            "Population Match Status",
                            "Incidence Rate",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

    # ========================================================
    # 7. MONTHLY INCIDENCE TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 7. 📅 Monthly Incidence Trend"
    )

    if (
        "Ward Name" in case_df.columns
        and not population_long.empty
    ):

        monthly_incidence = (
            _monthly_incidence(
                case_df,
                population_long,
                denominator,
            )
        )

        if not monthly_incidence.empty:

            monthly_wards = (
                _alphabetical(
                    monthly_incidence[
                        "Ward"
                    ].unique()
                )
            )

            selected_monthly_wards = (
                _checkbox_multiselect(
                    "Select Ward(s) for Monthly Trend",
                    monthly_wards,
                    "phase8b_monthly_wards",
                    default_count=min(
                        5,
                        len(
                            monthly_wards
                        ),
                    ),
                )
            )

            if selected_monthly_wards:

                monthly_chart = (
                    monthly_incidence[
                        monthly_incidence[
                            "Ward"
                        ].isin(
                            selected_monthly_wards
                        )
                    ]
                    .copy()
                )

                _render_multi_line_chart(
                    dataframe=monthly_chart,
                    x_column="Period",
                    series_column="Ward",
                    value_column=(
                        "Incidence Rate"
                    ),
                    title=(
                        "Monthly Ward-wise "
                        "Incidence Trend"
                    ),
                    y_title=(
                        f"Incidence per "
                        f"{denominator:,}"
                    ),
                    height=480,
                )

    # ========================================================
    # 8. YEAR-WISE INCIDENCE TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 8. 🗓️ Year-wise Incidence Trend"
    )

    if (
        "Ward Name" in case_df.columns
        and not population_long.empty
    ):

        yearly_incidence = (
            _aggregate_incidence_by_year(
                case_df,
                population_long,
                denominator,
            )
        )

        if not yearly_incidence.empty:

            yearly_chart = (
                yearly_incidence.copy()
            )

            yearly_chart[
                "Year Label"
            ] = (
                yearly_chart[
                    "Year"
                ]
                .astype(int)
                .astype(str)
            )

            yearly_chart[
                "Series"
            ] = "Overall Incidence"

            _render_multi_line_chart(
                dataframe=yearly_chart,
                x_column="Year Label",
                series_column="Series",
                value_column=(
                    "Incidence Rate"
                ),
                title=(
                    "Year-wise Overall "
                    "Incidence Trend"
                ),
                y_title=(
                    f"Incidence per "
                    f"{denominator:,}"
                ),
                height=430,
            )

            st.dataframe(
                yearly_incidence,
                use_container_width=True,
                hide_index=True,
            )

    # ========================================================
    # 9. STATISTICAL THRESHOLD ANALYSIS
    # ========================================================

    st.divider()

    st.markdown(
        "### 9. 📐 Statistical Threshold Analysis"
    )

    st.caption(
        "Mean and standard-deviation thresholds are "
        "descriptive statistical surveillance indicators. "
        "They are not, by themselves, confirmed outbreak thresholds."
    )

    c1, c2 = st.columns(2)

    with c1:

        baseline_option = (
            st.selectbox(
                "Statistical Baseline",
                options=[
                    "All Available Years",
                    "Last 2 Years",
                    "Last 3 Years",
                    "Last 5 Years",
                ],
                index=0,
                key=(
                    "phase8b_stat_baseline"
                ),
            )
        )

    with c2:

        statistical_view = (
            st.selectbox(
                "Statistical Analysis",
                options=[
                    "Overall",
                    "Disease",
                    "Ward",
                    "Facility",
                ],
                index=0,
                key=(
                    "phase8b_stat_view"
                ),
            )
        )

    statistical_source = (
        _apply_baseline_years(
            case_df,
            baseline_option,
        )
    )

    statistical_title = (
        "Overall Monthly Cases"
    )

    # --------------------------------------------------------
    # DISEASE FILTER
    # --------------------------------------------------------

    if (
        statistical_view
        == "Disease"
    ):

        if "Disease" not in (
            statistical_source.columns
        ):

            st.info(
                "Disease column is not available."
            )

            statistical_source = (
                pd.DataFrame()
            )

        else:

            options = (
                _clean_series(
                    statistical_source[
                        "Disease"
                    ]
                )
            )

            options = (
                options[
                    options.ne("")
                    & options.ne("nan")
                ]
                .value_counts()
                .index
                .tolist()
            )

            if options:

                selected = (
                    st.selectbox(
                        "Select Disease",
                        options=options,
                        key=(
                            "phase8b_stat_disease"
                        ),
                    )
                )

                statistical_source = (
                    statistical_source[
                        _clean_series(
                            statistical_source[
                                "Disease"
                            ]
                        )
                        == selected
                    ]
                    .copy()
                )

                statistical_title = (
                    f"{selected} Monthly Cases"
                )

    # --------------------------------------------------------
    # WARD FILTER
    # --------------------------------------------------------

    elif (
        statistical_view
        == "Ward"
    ):

        if "Ward Name" not in (
            statistical_source.columns
        ):

            st.info(
                "Ward Name column is not available."
            )

            statistical_source = (
                pd.DataFrame()
            )

        else:

            options = (
                _alphabetical(
                    _clean_series(
                        statistical_source[
                            "Ward Name"
                        ]
                    ).unique()
                )
            )

            if options:

                selected = (
                    st.selectbox(
                        "Select Ward",
                        options=options,
                        key=(
                            "phase8b_stat_ward"
                        ),
                    )
                )

                statistical_source = (
                    statistical_source[
                        _clean_series(
                            statistical_source[
                                "Ward Name"
                            ]
                        )
                        == selected
                    ]
                    .copy()
                )

                statistical_title = (
                    f"Ward {selected} Monthly Cases"
                )

    # --------------------------------------------------------
    # FACILITY FILTER
    # --------------------------------------------------------

    elif (
        statistical_view
        == "Facility"
    ):

        if "Facility Name" not in (
            statistical_source.columns
        ):

            st.info(
                "Facility Name column is not available."
            )

            statistical_source = (
                pd.DataFrame()
            )

        else:

            options = (
                _clean_series(
                    statistical_source[
                        "Facility Name"
                    ]
                )
            )

            options = (
                options[
                    options.ne("")
                    & options.ne("nan")
                ]
                .value_counts()
                .index
                .tolist()
            )

            if options:

                selected = (
                    st.selectbox(
                        "Select Facility",
                        options=options,
                        key=(
                            "phase8b_stat_facility"
                        ),
                    )
                )

                statistical_source = (
                    statistical_source[
                        _clean_series(
                            statistical_source[
                                "Facility Name"
                            ]
                        )
                        == selected
                    ]
                    .copy()
                )

                statistical_title = (
                    f"{selected} Monthly Cases"
                )

    statistical_monthly = (
        _monthly_case_series(
            statistical_source
        )
    )

    statistics = (
        _threshold_statistics(
            statistical_monthly
        )
    )

    if (
        statistics is not None
        and not statistical_monthly.empty
    ):

        c1, c2, c3, c4 = (
            st.columns(4)
        )

        with c1:

            st.metric(
                "Mean",
                f"{statistics['Mean']:,.2f}",
            )

        with c2:

            st.metric(
                "Mean + 1 SD",
                (
                    f"{statistics['Mean + 1 SD']:,.2f}"
                ),
            )

        with c3:

            st.metric(
                "Mean + 2 SD",
                (
                    f"{statistics['Mean + 2 SD']:,.2f}"
                ),
            )

        with c4:

            st.metric(
                "Mean + 3 SD",
                (
                    f"{statistics['Mean + 3 SD']:,.2f}"
                ),
            )

        _render_threshold_chart(
            monthly=statistical_monthly,
            statistics=statistics,
            title=(
                f"{statistical_title} — "
                f"Mean / SD Thresholds"
            ),
        )

        threshold_table = pd.DataFrame(
            {
                "Indicator": [
                    "Mean",
                    "Standard Deviation",
                    "Mean + 1 SD",
                    "Mean + 2 SD",
                    "Mean + 3 SD",
                ],
                "Value": [
                    round(
                        statistics[
                            "Mean"
                        ],
                        2,
                    ),
                    round(
                        statistics[
                            "SD"
                        ],
                        2,
                    ),
                    round(
                        statistics[
                            "Mean + 1 SD"
                        ],
                        2,
                    ),
                    round(
                        statistics[
                            "Mean + 2 SD"
                        ],
                        2,
                    ),
                    round(
                        statistics[
                            "Mean + 3 SD"
                        ],
                        2,
                    ),
                ],
            }
        )

        st.dataframe(
            threshold_table,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "Sufficient monthly data is not available "
            "for the selected statistical analysis."
        )

    # ========================================================
    # 10. DISEASE-WISE STATISTICAL TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 10. 🦠 Disease-wise Statistical Trend"
    )

    if "Disease" in case_df.columns:

        disease_stat_options = (
            _clean_series(
                case_df[
                    "Disease"
                ]
            )
        )

        disease_stat_options = (
            disease_stat_options[
                disease_stat_options.ne("")
                & disease_stat_options.ne("nan")
            ]
            .value_counts()
            .index
            .tolist()
        )

        if disease_stat_options:

            selected_stat_disease = (
                st.selectbox(
                    "Select Disease for Statistical Trend",
                    options=(
                        disease_stat_options
                    ),
                    key=(
                        "phase8b_disease_stat_selector"
                    ),
                )
            )

            source = case_df[
                _clean_series(
                    case_df[
                        "Disease"
                    ]
                )
                == selected_stat_disease
            ]

            source = (
                _apply_baseline_years(
                    source,
                    baseline_option,
                )
            )

            monthly = (
                _monthly_case_series(
                    source
                )
            )

            stats = (
                _threshold_statistics(
                    monthly
                )
            )

            _render_threshold_chart(
                monthly,
                stats,
                (
                    f"{selected_stat_disease} "
                    "Statistical Trend"
                ),
            )

    # ========================================================
    # 11. WARD-WISE STATISTICAL TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 11. 📍 Ward-wise Statistical Trend"
    )

    if "Ward Name" in case_df.columns:

        ward_stat_options = (
            _alphabetical(
                _clean_series(
                    case_df[
                        "Ward Name"
                    ]
                ).unique()
            )
        )

        if ward_stat_options:

            selected_stat_ward = (
                st.selectbox(
                    "Select Ward for Statistical Trend",
                    options=(
                        ward_stat_options
                    ),
                    key=(
                        "phase8b_ward_stat_selector"
                    ),
                )
            )

            source = case_df[
                _clean_series(
                    case_df[
                        "Ward Name"
                    ]
                )
                == selected_stat_ward
            ]

            source = (
                _apply_baseline_years(
                    source,
                    baseline_option,
                )
            )

            monthly = (
                _monthly_case_series(
                    source
                )
            )

            stats = (
                _threshold_statistics(
                    monthly
                )
            )

            _render_threshold_chart(
                monthly,
                stats,
                (
                    f"Ward {selected_stat_ward} "
                    "Statistical Trend"
                ),
            )

    # ========================================================
    # 12. FACILITY-WISE STATISTICAL TREND
    # ========================================================

    st.divider()

    st.markdown(
        "### 12. 🏥 Facility-wise Statistical Trend"
    )

    st.caption(
        "Facility analysis displays case-volume statistical "
        "trends. It is not labelled as facility incidence "
        "because a facility-specific population denominator "
        "is not available."
    )

    if "Facility Name" in case_df.columns:

        facility_options = (
            _clean_series(
                case_df[
                    "Facility Name"
                ]
            )
        )

        facility_options = (
            facility_options[
                facility_options.ne("")
                & facility_options.ne("nan")
            ]
            .value_counts()
            .index
            .tolist()
        )

        if facility_options:

            selected_stat_facility = (
                st.selectbox(
                    "Select Facility for Statistical Trend",
                    options=(
                        facility_options
                    ),
                    key=(
                        "phase8b_facility_stat_selector"
                    ),
                )
            )

            source = case_df[
                _clean_series(
                    case_df[
                        "Facility Name"
                    ]
                )
                == selected_stat_facility
            ]

            source = (
                _apply_baseline_years(
                    source,
                    baseline_option,
                )
            )

            monthly = (
                _monthly_case_series(
                    source
                )
            )

            stats = (
                _threshold_statistics(
                    monthly
                )
            )

            _render_threshold_chart(
                monthly,
                stats,
                (
                    f"{selected_stat_facility} "
                    "Statistical Trend"
                ),
            )

    # ========================================================
    # 13. POPULATION MATCHING / FALLBACK AUDIT
    # ========================================================

    st.divider()

    st.markdown(
        "### 13. 🔍 Population Matching & Fallback Audit"
    )

    st.caption(
        "This table shows which population year was used "
        "for each Ward × Analysis Year combination."
    )

    if not population_long.empty:

        audit = (
            _population_audit(
                case_df,
                population_long,
            )
        )

        if not audit.empty:

            exact_count = int(
                (
                    audit[
                        "Status"
                    ]
                    == "Exact year"
                ).sum()
            )

            previous_count = int(
                (
                    audit[
                        "Status"
                    ]
                    == "Previous-year fallback"
                ).sum()
            )

            future_count = int(
                (
                    audit[
                        "Status"
                    ]
                    == "Future-year fallback"
                ).sum()
            )

            unavailable_count = int(
                (
                    audit[
                        "Status"
                    ]
                    == "Population unavailable"
                ).sum()
            )

            c1, c2, c3, c4 = (
                st.columns(4)
            )

            with c1:

                st.metric(
                    "Exact Matches",
                    f"{exact_count:,}",
                )

            with c2:

                st.metric(
                    "Previous-Year Fallbacks",
                    f"{previous_count:,}",
                )

            with c3:

                st.metric(
                    "Future-Year Fallbacks",
                    f"{future_count:,}",
                )

            with c4:

                st.metric(
                    "Population Unavailable",
                    f"{unavailable_count:,}",
                )

            st.dataframe(
                audit,
                use_container_width=True,
                hide_index=True,
            )

    else:

        st.info(
            "Population matching audit is unavailable "
            "because population data could not be loaded."
        )

    # ========================================================
    # 14. METHODOLOGY & INTERPRETATION
    # ========================================================

    st.divider()

    st.markdown(
        "### 14. ℹ️ Methodology & Interpretation"
    )

    methodology = pd.DataFrame(
        {
            "Component": [
                "Incidence Formula",
                "Default Denominator",
                "Available Denominators",
                "Population Matching",
                "Missing Population Year",
                "Future Fallback",
                "Disease Incidence",
                "Ward Incidence",
                "Facility Analysis",
                "Statistical Mean",
                "Standard Deviation",
                "Mean + 1 SD",
                "Mean + 2 SD",
                "Mean + 3 SD",
                "Interpretation",
            ],
            "Description": [
                (
                    "Cases divided by population multiplied "
                    "by the selected denominator"
                ),
                (
                    "100,000 population"
                ),
                (
                    "1,000; 10,000; 100,000; "
                    "1,000,000 population"
                ),
                (
                    "Exact Ward × Year population is used "
                    "when available"
                ),
                (
                    "If exact population year is unavailable, "
                    "the closest previous available population "
                    "year for that ward is used"
                ),
                (
                    "If no previous population year exists, "
                    "the nearest future available year is used "
                    "and explicitly identified as a fallback"
                ),
                (
                    "Disease cases are related to the "
                    "corresponding ward population"
                ),
                (
                    "Ward cases are related to the "
                    "corresponding ward population"
                ),
                (
                    "Facility-specific incidence is not "
                    "calculated without a valid "
                    "facility-specific population denominator"
                ),
                (
                    "Arithmetic mean of monthly case counts "
                    "within the selected statistical baseline"
                ),
                (
                    "Sample standard deviation of monthly "
                    "case counts within the selected baseline"
                ),
                (
                    "Mean plus one standard deviation"
                ),
                (
                    "Mean plus two standard deviations"
                ),
                (
                    "Mean plus three standard deviations"
                ),
                (
                    "Statistical surveillance and programme "
                    "planning support; thresholds do not by "
                    "themselves confirm an outbreak"
                ),
            ],
        }
    )

    st.dataframe(
        methodology,
        use_container_width=True,
        hide_index=True,
    )

    st.warning(
        "Incidence rates depend on the completeness and "
        "appropriateness of both case and population data. "
        "Population fallback values are clearly identified "
        "and should be reviewed before formal reporting. "
        "Mean and standard-deviation thresholds are descriptive "
        "statistical indicators and should be interpreted "
        "alongside seasonality, reporting completeness, testing "
        "practices, epidemiological investigation and programme context."
    )
