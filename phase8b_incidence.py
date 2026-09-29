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

DATA_LABEL_FONT_SIZE = 10

COLORS = [
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
    "#4C78A8",
    "#F58518",
]

MONTH_NAMES = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


# ============================================================
# UI HELPERS
# ============================================================

def _inject_toggle_css():
    """
    Compact segmented-control styling for horizontal radio buttons.
    """

    st.markdown(
        """
        <style>
        div[data-testid="stRadio"] > div {
            gap: 0.35rem;
        }

        div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }

        div[data-testid="stRadio"] label {
            border: 1px solid #D9DEE7;
            border-radius: 8px;
            padding: 5px 13px;
            background: #F7F8FA;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        div[data-testid="stRadio"] label:hover {
            border-color: #1F77B4;
            background: #EEF5FB;
        }

        div[data-testid="stRadio"] label:has(input:checked) {
            border-color: #1F77B4;
            background: #1F77B4;
            color: white;
            font-weight: 600;
        }

        div[data-testid="stRadio"] label p {
            margin: 0;
            font-size: 0.88rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _smart_toggle(
    label,
    options,
    default=None,
    key=None,
):

    options = list(options)

    if not options:
        return None

    if default is None:
        default = options[0]

    if default not in options:
        default = options[0]

    index = options.index(default)

    return st.radio(
        label,
        options=options,
        index=index,
        horizontal=True,
        key=key,
        label_visibility="visible",
    )


def _compact_multiselect(
    label,
    options,
    default=None,
    key=None,
):

    options = list(options)

    if not options:
        return []

    if default is None:
        default = options[:min(5, len(options))]

    default = [
        value
        for value in default
        if value in options
    ]

    return st.multiselect(
        label,
        options=options,
        default=default,
        key=key,
    )


# ============================================================
# BASIC HELPERS
# ============================================================

def _clean_series(series):

    if series is None:
        return pd.Series(dtype="object")

    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _valid_text(series):

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

    cleaned = []

    for value in values:

        text = str(value).strip()

        if text and text not in {
            "nan",
            "NaT",
            "None",
            "-",
        }:
            cleaned.append(text)

    return sorted(
        list(dict.fromkeys(cleaned)),
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


def _format_number(value, decimals=0):

    if pd.isna(value):
        return "Unavailable"

    try:

        if decimals == 0:
            return f"{float(value):,.0f}"

        return f"{float(value):,.{decimals}f}"

    except Exception:
        return str(value)


# ============================================================
# CASE DATA PREPARATION
# ============================================================

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

        dates = pd.to_datetime(
            temp["Reporting Date"],
            errors="coerce",
            dayfirst=True,
        )

        temp["Analysis_Year"] = dates.dt.year

    else:

        temp["Analysis_Year"] = np.nan

    # --------------------------------------------------------
    # MONTH
    # --------------------------------------------------------

    if "Month" in temp.columns:

        temp["Analysis_Month"] = (
            temp["Month"].map(_month_number)
        )

    elif "Reporting Date" in temp.columns:

        dates = pd.to_datetime(
            temp["Reporting Date"],
            errors="coerce",
            dayfirst=True,
        )

        temp["Analysis_Month"] = dates.dt.month

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
        temp["Analysis_Year"].astype(int)
    )

    if "Ward Name" in temp.columns:

        temp["Ward Name"] = _clean_series(
            temp["Ward Name"]
        )

    if "Disease" in temp.columns:

        temp["Disease"] = _clean_series(
            temp["Disease"]
        )

    if "Facility Name" in temp.columns:

        temp["Facility Name"] = _clean_series(
            temp["Facility Name"]
        )

    return temp


# ============================================================
# POPULATION DATA LOADER
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def _load_population_raw():

    population_df = pd.read_csv(
        POPULATION_CSV_URL
    )

    population_df.columns = [
        str(column).strip()
        for column in population_df.columns
    ]

    return population_df


def _find_ward_column(df):

    if df is None or df.empty:
        return None

    candidates = [
        "WARD",
        "Ward",
        "Ward Name",
        "WARD NAME",
        "ward",
    ]

    for candidate in candidates:

        if candidate in df.columns:
            return candidate

    for column in df.columns:

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

    match = re.search(
        r"(20\d{2})",
        str(column_name),
    )

    if not match:
        return None

    year = int(match.group(1))

    if MIN_VALID_YEAR <= year <= MAX_VALID_YEAR:
        return year

    return None


def _prepare_population_data(population_df):

    if population_df is None or population_df.empty:

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

        if (
            year is not None
            and year not in year_columns
        ):
            year_columns[year] = column

    if not year_columns:

        return (
            pd.DataFrame(),
            pd.DataFrame(),
            [],
        )

    source["WARD"] = _clean_series(
        source[ward_column]
    )

    source = source[
        _valid_text(
            source["WARD"]
        )
    ].copy()

    total_values = {
        "TOTAL",
        "GRAND TOTAL",
        "MUMBAI TOTAL",
        "ALL",
    }

    source = source[
        ~source["WARD"]
        .str.upper()
        .isin(total_values)
    ].copy()

    available_years = sorted(
        year_columns.keys()
    )

    wide_data = {
        "WARD": source["WARD"]
    }

    for year in available_years:

        wide_data[str(year)] = (
            _safe_numeric(
                source[
                    year_columns[year]
                ]
            )
        )

    population_wide = pd.DataFrame(
        wide_data
    )

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
        .sum(min_count=1)
    )

    population_long = (
        population_wide
        .melt(
            id_vars=["WARD"],
            value_vars=numeric_columns,
            var_name="Population_Year",
            value_name="Population",
        )
    )

    population_long["Population_Year"] = (
        pd.to_numeric(
            population_long[
                "Population_Year"
            ],
            errors="coerce",
        )
    )

    population_long["Population"] = (
        pd.to_numeric(
            population_long[
                "Population"
            ],
            errors="coerce",
        )
    )

    population_long = population_long[
        population_long[
            "Population_Year"
        ].notna()
    ].copy()

    population_long["Population_Year"] = (
        population_long[
            "Population_Year"
        ].astype(int)
    )

    population_long.loc[
        population_long["Population"] <= 0,
        "Population",
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

    if population_long is None or population_long.empty:

        return (
            np.nan,
            None,
            "Population unavailable",
        )

    ward_text = str(
        ward
    ).strip()

    try:
        analysis_year = int(
            analysis_year
        )

    except Exception:

        return (
            np.nan,
            None,
            "Invalid analysis year",
        )

    data = population_long[
        _clean_series(
            population_long["WARD"]
        ) == ward_text
    ].copy()

    data = data[
        data["Population"].notna()
        & data["Population"].gt(0)
    ]

    if data.empty:

        return (
            np.nan,
            None,
            "Population unavailable",
        )

    exact = data[
        data["Population_Year"]
        == analysis_year
    ]

    if not exact.empty:

        row = exact.iloc[0]

        return (
            float(row["Population"]),
            int(row["Population_Year"]),
            "Exact year",
        )

    previous = data[
        data["Population_Year"]
        < analysis_year
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
            ] == selected_year
        ].iloc[0]

        return (
            float(row["Population"]),
            selected_year,
            "Previous-year fallback",
        )

    future = data[
        data["Population_Year"]
        > analysis_year
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
            ] == selected_year
        ].iloc[0]

        return (
            float(row["Population"]),
            selected_year,
            "Future-year fallback",
        )

    return (
        np.nan,
        None,
        "Population unavailable",
    )


# ============================================================
# PREPARED INCIDENCE TABLES
# ============================================================

def _build_ward_year_incidence(
    case_df,
    population_long,
    denominator,
):

    if (
        case_df is None
        or case_df.empty
        or "Ward Name" not in case_df.columns
    ):
        return pd.DataFrame()

    temp = case_df[
        _valid_text(
            case_df["Ward Name"]
        )
    ].copy()

    if temp.empty:
        return pd.DataFrame()

    grouped = (
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

    rows = []

    for _, row in grouped.iterrows():

        population, year_used, status = (
            _population_for_ward_year(
                population_long,
                row["Ward Name"],
                row["Analysis_Year"],
            )
        )

        rate = np.nan

        if pd.notna(population) and population > 0:

            rate = (
                row["Cases"]
                / population
                * denominator
            )

        rows.append(
            {
                "Ward": row["Ward Name"],
                "Year": int(row["Analysis_Year"]),
                "Cases": int(row["Cases"]),
                "Population": population,
                "Population Year Used": year_used,
                "Population Match Status": status,
                "Incidence Rate": (
                    round(rate, 2)
                    if pd.notna(rate)
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows)


def _build_disease_ward_year_incidence(
    case_df,
    population_long,
    denominator,
):

    required = {
        "Ward Name",
        "Disease",
        "Analysis_Year",
    }

    if (
        case_df is None
        or case_df.empty
        or not required.issubset(
            case_df.columns
        )
    ):
        return pd.DataFrame()

    temp = case_df[
        _valid_text(
            case_df["Ward Name"]
        )
        & _valid_text(
            case_df["Disease"]
        )
    ].copy()

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

        rate = np.nan

        if pd.notna(population) and population > 0:

            rate = (
                row["Cases"]
                / population
                * denominator
            )

        rows.append(
            {
                "Ward": row["Ward Name"],
                "Disease": row["Disease"],
                "Year": int(row["Analysis_Year"]),
                "Cases": int(row["Cases"]),
                "Population": population,
                "Population Year Used": year_used,
                "Population Match Status": status,
                "Incidence Rate": (
                    round(rate, 2)
                    if pd.notna(rate)
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows)


def _build_monthly_ward_incidence(
    case_df,
    population_long,
    denominator,
):

    required = {
        "Ward Name",
        "Analysis_Year",
        "Analysis_Month",
    }

    if (
        case_df is None
        or case_df.empty
        or not required.issubset(
            case_df.columns
        )
    ):
        return pd.DataFrame()

    temp = case_df[
        case_df[
            "Analysis_Month"
        ].between(1, 12)
        & _valid_text(
            case_df["Ward Name"]
        )
    ].copy()

    if temp.empty:
        return pd.DataFrame()

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

        rate = np.nan

        if pd.notna(population) and population > 0:

            rate = (
                row["Cases"]
                / population
                * denominator
            )

        year = int(row["Analysis_Year"])
        month = int(row["Analysis_Month"])

        date_value = pd.Timestamp(
            year,
            month,
            1,
        )

        rows.append(
            {
                "Ward": row["Ward Name"],
                "Year": year,
                "Month": month,
                "Date": date_value,
                "Period": date_value.strftime(
                    "%b-%Y"
                ),
                "Cases": int(row["Cases"]),
                "Population": population,
                "Population Year Used": year_used,
                "Population Match Status": status,
                "Incidence Rate": (
                    round(rate, 2)
                    if pd.notna(rate)
                    else np.nan
                ),
            }
        )

    result = pd.DataFrame(rows)

    if result.empty:
        return result

    return (
        result
        .sort_values(
            [
                "Date",
                "Ward",
            ]
        )
        .reset_index(drop=True)
    )


# ============================================================
# AGGREGATION HELPERS
# ============================================================

def _aggregate_year_incidence(
    ward_incidence,
    denominator,
):

    if ward_incidence is None or ward_incidence.empty:
        return pd.DataFrame()

    rows = []

    for year, group in ward_incidence.groupby(
        "Year",
        observed=True,
    ):

        valid = group[
            group["Population"].notna()
            & group["Population"].gt(0)
        ]

        if valid.empty:
            continue

        cases = int(
            valid["Cases"].sum()
        )

        population = float(
            valid["Population"].sum()
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
                "Incidence Rate": round(
                    rate,
                    2,
                ),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("Year")
        .reset_index(drop=True)
    )


# ============================================================
# CHART HELPERS
# ============================================================

def _legend_columns(series_count):

    if series_count <= 4:
        return 4

    if series_count <= 8:
        return 4

    if series_count <= 12:
        return 6

    return 6


def _legend(series_count, title=None):

    return alt.Legend(
        title=title,
        orient="bottom",
        direction="horizontal",
        columns=_legend_columns(
            series_count
        ),
        labelFontSize=9,
        titleFontSize=10,
        symbolSize=65,
        labelLimit=180,
        columnPadding=8,
        rowPadding=5,
    )


def _render_bar_chart(
    dataframe,
    x_column,
    y_column,
    title,
    y_title,
    height=430,
):

    if (
        dataframe is None
        or dataframe.empty
        or x_column not in dataframe.columns
        or y_column not in dataframe.columns
    ):
        return

    chart_df = dataframe[
        dataframe[y_column].notna()
    ].copy()

    if chart_df.empty:
        return

    chart_df[x_column] = (
        chart_df[x_column].astype(str)
    )

    order = chart_df[x_column].tolist()

    color_range = [
        COLORS[index % len(COLORS)]
        for index in range(len(order))
    ]

    scale = alt.Scale(
        domain=order,
        range=color_range,
    )

    bars = (
        alt.Chart(chart_df)
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
                    title=y_title
                ),
            ),
            color=alt.Color(
                f"{x_column}:N",
                scale=scale,
                legend=_legend(
                    len(order),
                    x_column,
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    f"{x_column}:N",
                    title=x_column,
                ),
                alt.Tooltip(
                    f"{y_column}:Q",
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


def _render_line_chart(
    dataframe,
    x_column,
    series_column,
    value_column,
    title,
    y_title,
    height=450,
):

    required = {
        x_column,
        series_column,
        value_column,
    }

    if (
        dataframe is None
        or dataframe.empty
        or not required.issubset(
            dataframe.columns
        )
    ):
        return

    chart_df = dataframe[
        dataframe[value_column].notna()
    ].copy()

    if chart_df.empty:
        return

    series_order = (
        chart_df[series_column]
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    color_range = [
        COLORS[index % len(COLORS)]
        for index in range(
            len(series_order)
        )
    ]

    scale = alt.Scale(
        domain=series_order,
        range=color_range,
    )

    lines = (
        alt.Chart(chart_df)
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
                legend=_legend(
                    len(series_order),
                    series_column,
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
            alt.Chart(chart_df)
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
# OBSERVATION HELPERS
# ============================================================

def _observation_box(text):

    if not text:
        return

    st.info(
        f"📌 **Chart Observation:** {text}"
    )


def _bar_observation(
    dataframe,
    category,
    value,
    unit,
):

    if (
        dataframe is None
        or dataframe.empty
        or category not in dataframe.columns
        or value not in dataframe.columns
    ):
        return None

    valid = dataframe[
        dataframe[value].notna()
    ].copy()

    if valid.empty:
        return None

    highest = valid.loc[
        valid[value].idxmax()
    ]

    lowest = valid.loc[
        valid[value].idxmin()
    ]

    if len(valid) == 1:

        return (
            f"{highest[category]} recorded "
            f"{_format_number(highest[value], 2)} "
            f"{unit}."
        )

    return (
        f"The highest value is observed for "
        f"{highest[category]} "
        f"({_format_number(highest[value], 2)} {unit}), "
        f"while the lowest among the displayed categories is "
        f"{lowest[category]} "
        f"({_format_number(lowest[value], 2)} {unit})."
    )


def _trend_observation(
    dataframe,
    period_column,
    value_column,
):

    if (
        dataframe is None
        or dataframe.empty
        or value_column not in dataframe.columns
    ):
        return None

    valid = dataframe[
        dataframe[value_column].notna()
    ].copy()

    if valid.empty:
        return None

    peak = valid.loc[
        valid[value_column].idxmax()
    ]

    first = valid.iloc[0]
    last = valid.iloc[-1]

    first_value = float(
        first[value_column]
    )

    last_value = float(
        last[value_column]
    )

    if last_value > first_value:
        direction = "higher"
    elif last_value < first_value:
        direction = "lower"
    else:
        direction = "the same"

    return (
        f"The highest displayed value occurs in "
        f"{peak[period_column]} "
        f"({_format_number(peak[value_column], 2)}). "
        f"The last displayed value is {direction} than "
        f"the first displayed value."
    )


# ============================================================
# METHODOLOGY HELPERS
# ============================================================

def _methodology_expander(
    title,
    lines,
):

    with st.expander(
        f"ℹ️ Methodology — {title}",
        expanded=False,
    ):

        for line in lines:
            st.markdown(
                f"- {line}"
            )


# ============================================================
# STATISTICAL ANALYSIS
# ============================================================

def _apply_baseline(
    source,
    baseline,
):

    if source is None or source.empty:
        return source

    years = sorted(
        source["Analysis_Year"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if not years:
        return source

    mapping = {
        "Last 2 Years": 2,
        "Last 3 Years": 3,
        "Last 5 Years": 5,
    }

    if baseline == "All Available Years":
        return source.copy()

    count = mapping.get(
        baseline
    )

    if count is None:
        return source.copy()

    selected_years = years[-count:]

    return source[
        source["Analysis_Year"].isin(
            selected_years
        )
    ].copy()


def _monthly_case_series(source):

    if source is None or source.empty:
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
        ].between(1, 12)
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

    complete_dates = pd.date_range(
        monthly["Date"].min(),
        monthly["Date"].max(),
        freq="MS",
    )

    complete = pd.DataFrame(
        {
            "Date": complete_dates
        }
    )

    complete["Analysis_Year"] = (
        complete["Date"].dt.year
    )

    complete["Analysis_Month"] = (
        complete["Date"].dt.month
    )

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

    complete["Cases"] = (
        complete["Cases"]
        .fillna(0)
        .astype(int)
    )

    complete["Period"] = (
        complete["Date"]
        .dt.strftime("%b-%Y")
    )

    return complete


def _threshold_statistics(monthly):

    if monthly is None or monthly.empty:
        return None

    values = pd.to_numeric(
        monthly["Cases"],
        errors="coerce",
    ).dropna()

    if values.empty:
        return None

    mean = float(values.mean())

    sd = (
        float(values.std(ddof=1))
        if len(values) > 1
        else 0.0
    )

    return {
        "Mean": mean,
        "SD": sd,
        "Mean + 1 SD": mean + sd,
        "Mean + 2 SD": mean + (2 * sd),
        "Mean + 3 SD": mean + (3 * sd),
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

    for key in [
        "Mean",
        "Mean + 1 SD",
        "Mean + 2 SD",
        "Mean + 3 SD",
    ]:

        chart_df[key] = statistics[key]

    long_df = chart_df.melt(
        id_vars=["Period"],
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

    scale = alt.Scale(
        domain=series_order,
        range=[
            "#1F77B4",
            "#2CA02C",
            "#FFBF00",
            "#FF7F0E",
            "#D62728",
        ],
    )

    chart = (
        alt.Chart(long_df)
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
                title="Cases",
            ),
            color=alt.Color(
                "Series:N",
                sort=series_order,
                scale=scale,
                legend=_legend(
                    len(series_order),
                    "Series",
                ),
            ),
            strokeDash=alt.StrokeDash(
                "Series:N",
                scale=alt.Scale(
                    domain=series_order,
                    range=[
                        [1, 0],
                        [7, 4],
                        [7, 4],
                        [7, 4],
                        [7, 4],
                    ],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("Period:N"),
                alt.Tooltip("Series:N"),
                alt.Tooltip(
                    "Value:Q",
                    format=",.2f",
                ),
            ],
        )
        .properties(
            height=460,
            title=title,
        )
    )

    case_points = long_df[
        long_df["Series"] == "Cases"
    ]

    points = (
        alt.Chart(case_points)
        .mark_point(
            filled=True,
            size=70,
        )
        .encode(
            x=alt.X(
                "Period:N",
                sort=None,
            ),
            y="Value:Q",
            color=alt.Color(
                "Series:N",
                scale=scale,
                legend=None,
            ),
        )
    )

    chart = chart + points

    if data_labels_enabled():

        labels = (
            alt.Chart(case_points)
            .mark_text(
                dy=-10,
                fontSize=10,
                fontWeight="bold",
            )
            .encode(
                x=alt.X(
                    "Period:N",
                    sort=None,
                ),
                y="Value:Q",
                text=alt.Text(
                    "Value:Q",
                    format=",.0f",
                ),
            )
        )

        chart = chart + labels

    st.altair_chart(
        chart,
        use_container_width=True,
    )


def _threshold_observation(
    monthly,
    statistics,
):

    if (
        monthly is None
        or monthly.empty
        or statistics is None
    ):
        return None

    latest = monthly.iloc[-1]

    latest_cases = float(
        latest["Cases"]
    )

    level_2 = statistics[
        "Mean + 2 SD"
    ]

    level_3 = statistics[
        "Mean + 3 SD"
    ]

    if latest_cases > level_3:

        status = (
            "above the Mean + 3 SD statistical level"
        )

    elif latest_cases > level_2:

        status = (
            "above the Mean + 2 SD statistical level"
        )

    elif latest_cases > statistics[
        "Mean + 1 SD"
    ]:

        status = (
            "above the Mean + 1 SD statistical level"
        )

    else:

        status = (
            "within or below the Mean + 1 SD statistical level"
        )

    peak = monthly.loc[
        monthly["Cases"].idxmax()
    ]

    return (
        f"The latest period ({latest['Period']}) recorded "
        f"{int(latest_cases):,} cases and is {status}. "
        f"The highest monthly count in the displayed baseline "
        f"was {int(peak['Cases']):,} cases in "
        f"{peak['Period']}. These are descriptive statistical "
        f"signals and do not independently confirm an outbreak."
    )


# ============================================================
# POPULATION AUDIT
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

    combinations = combinations[
        _valid_text(
            combinations["Ward Name"]
        )
    ]

    combinations = (
        combinations
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
                "Ward": row["Ward Name"],
                "Analysis Year": int(
                    row["Analysis_Year"]
                ),
                "Population": population,
                "Population Year Used": year_used,
                "Status": status,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# MAIN PAGE
# ============================================================

def render_incidence_analysis(df):

    _inject_toggle_css()

    st.subheader(
        "📐 Incidence & Statistical Surveillance"
    )

    st.caption(
        "Population-based incidence analysis, trend monitoring "
        "and descriptive statistical surveillance using the "
        "currently selected Global Dashboard Filters."
    )

    if df is None or df.empty:

        st.warning(
            "No records are available for the selected filters."
        )

        return

    # ========================================================
    # PREPARE CASE DATA ONCE
    # ========================================================

    case_df = _prepare_case_data(df)

    if case_df.empty:

        st.warning(
            "Valid year information is required for "
            "incidence analysis."
        )

        return

    # ========================================================
    # LOAD POPULATION ONCE
    # ========================================================

    population_error = None

    try:

        population_raw = _load_population_raw()

        (
            population_wide,
            population_long,
            population_years,
        ) = _prepare_population_data(
            population_raw
        )

    except Exception as error:

        population_error = error

        population_wide = pd.DataFrame()
        population_long = pd.DataFrame()
        population_years = []

    # ========================================================
    # SECTION 1
    # POPULATION & INCIDENCE OVERVIEW
    # ========================================================

    st.markdown(
        "### 1. 📊 Population & Incidence Overview"
    )

    denominator = _smart_toggle(
        "Incidence Rate Denominator",
        [
            "Per 1,000",
            "Per 10,000",
            "Per 100,000",
            "Per 1,000,000",
        ],
        default="Per 100,000",
        key="phase8b_incidence_denominator_toggle",
    )

    denominator_map = {
        "Per 1,000": 1_000,
        "Per 10,000": 10_000,
        "Per 100,000": 100_000,
        "Per 1,000,000": 1_000_000,
    }

    denominator = denominator_map.get(
        denominator,
        DEFAULT_DENOMINATOR,
    )

    st.caption(
        f"All incidence rates displayed on this page are "
        f"currently expressed per {denominator:,} population."
    )

    case_years = sorted(
        case_df["Analysis_Year"]
        .unique()
        .tolist()
    )

    population_wards = (
        population_long["WARD"].nunique()
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
            f"{population_wards:,}",
        )

    with c4:

        st.metric(
            "Latest Population Year",
            (
                str(max(population_years))
                if population_years
                else "Unavailable"
            ),
        )

    if population_error is not None:

        st.error(
            "Population data could not be loaded from "
            "the Population worksheet."
        )

        with st.expander(
            "Technical Details",
            expanded=False,
        ):

            st.code(
                str(population_error)
            )

    elif population_long.empty:

        st.warning(
            "No valid population data or population-year "
            "columns were detected."
        )

    else:

        st.success(
            "Population dataset loaded successfully. "
            f"Detected years: "
            f"{', '.join(str(x) for x in population_years)}"
        )

        with st.expander(
            "📋 View Complete Population Dataset",
            expanded=False,
        ):

            st.dataframe(
                population_wide,
                use_container_width=True,
                hide_index=True,
            )

    _methodology_expander(
        "Population & Incidence Overview",
        [
            (
                "Incidence Rate = Cases ÷ Population × "
                "selected denominator."
            ),
            (
                "The default denominator is 100,000 population."
            ),
            (
                "Population year columns are detected "
                "automatically from the Population worksheet."
            ),
            (
                "New population year columns can therefore "
                "be added without changing this module."
            ),
        ],
    )

    if population_long.empty:
        return

    # ========================================================
    # PREPARE COMMON INCIDENCE TABLES ONCE
    # ========================================================

    ward_incidence = (
        _build_ward_year_incidence(
            case_df,
            population_long,
            denominator,
        )
    )

    disease_ward_incidence = (
        _build_disease_ward_year_incidence(
            case_df,
            population_long,
            denominator,
        )
    )

    monthly_incidence = (
        _build_monthly_ward_incidence(
            case_df,
            population_long,
            denominator,
        )
    )

    yearly_incidence = (
        _aggregate_year_incidence(
            ward_incidence,
            denominator,
        )
    )

    audit = (
        _population_audit(
            case_df,
            population_long,
        )
    )

    # ========================================================
    # SECTION 2
    # POPULATION TREND & MATCHING QUALITY
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. 👥 Population Trend & Matching Quality"
    )

    population_tab, audit_tab = st.tabs(
        [
            "📈 Population Trend",
            "🔍 Population Matching Audit",
        ]
    )

    with population_tab:

        wards = _alphabetical(
            population_long["WARD"].unique()
        )

        selected_wards = _compact_multiselect(
            "Select Ward(s)",
            wards,
            default=wards[
                :min(5, len(wards))
            ],
            key="phase8b_population_wards",
        )

        if selected_wards:

            chart_df = population_long[
                population_long["WARD"].isin(
                    selected_wards
                )
            ].copy()

            chart_df = chart_df.sort_values(
                [
                    "Population_Year",
                    "WARD",
                ]
            )

            chart_df["Year"] = (
                chart_df[
                    "Population_Year"
                ]
                .astype(int)
                .astype(str)
            )

            _render_line_chart(
                chart_df,
                "Year",
                "WARD",
                "Population",
                "Ward-wise Population Trend",
                "Population",
                height=450,
            )

            if not chart_df.empty:

                latest_year = int(
                    chart_df[
                        "Population_Year"
                    ].max()
                )

                latest_data = chart_df[
                    chart_df[
                        "Population_Year"
                    ] == latest_year
                ]

                if not latest_data.empty:

                    top = latest_data.loc[
                        latest_data[
                            "Population"
                        ].idxmax()
                    ]

                    _observation_box(
                        f"For {latest_year}, the highest "
                        f"population among the selected wards "
                        f"is recorded for {top['WARD']} "
                        f"({_format_number(top['Population'])})."
                    )

            with st.expander(
                "📋 View Population Trend Data",
                expanded=False,
            ):

                st.dataframe(
                    chart_df[
                        [
                            "WARD",
                            "Population_Year",
                            "Population",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

        else:

            st.info(
                "Select at least one ward."
            )

        _methodology_expander(
            "Population Trend",
            [
                (
                    "Population values are read directly "
                    "from the Population worksheet."
                ),
                (
                    "Each detected population year is "
                    "displayed chronologically."
                ),
                (
                    "Ward selection changes only the "
                    "displayed trend and does not modify "
                    "the source population dataset."
                ),
            ],
        )

    with audit_tab:

        if not audit.empty:

            exact_count = int(
                (
                    audit["Status"]
                    == "Exact year"
                ).sum()
            )

            previous_count = int(
                (
                    audit["Status"]
                    == "Previous-year fallback"
                ).sum()
            )

            future_count = int(
                (
                    audit["Status"]
                    == "Future-year fallback"
                ).sum()
            )

            unavailable_count = int(
                (
                    audit["Status"]
                    == "Population unavailable"
                ).sum()
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "Exact Matches",
                    f"{exact_count:,}",
                )

            with c2:
                st.metric(
                    "Previous-Year Fallback",
                    f"{previous_count:,}",
                )

            with c3:
                st.metric(
                    "Future-Year Fallback",
                    f"{future_count:,}",
                )

            with c4:
                st.metric(
                    "Unavailable",
                    f"{unavailable_count:,}",
                )

            total_matches = len(audit)

            if total_matches > 0:

                exact_percent = (
                    exact_count
                    / total_matches
                    * 100
                )

                _observation_box(
                    f"{exact_percent:.1f}% of Ward × Year "
                    f"population matches use the exact "
                    f"population year. "
                    f"{previous_count:,} combinations use a "
                    f"previous-year fallback and "
                    f"{future_count:,} use a future-year fallback."
                )

            st.dataframe(
                audit,
                use_container_width=True,
                hide_index=True,
            )

        _methodology_expander(
            "Population Matching",
            [
                (
                    "The exact Ward × Year population is "
                    "used whenever available."
                ),
                (
                    "If the exact year is unavailable, the "
                    "closest previous available population "
                    "year for that ward is used."
                ),
                (
                    "If no previous population year exists, "
                    "the nearest future available year is used."
                ),
                (
                    "Every fallback is explicitly identified "
                    "in the audit table."
                ),
            ],
        )

    # ========================================================
    # SECTION 3
    # WARD-WISE INCIDENCE
    # ========================================================

    st.divider()

    st.markdown(
        "### 3. 📍 Ward-wise Incidence Analysis"
    )

    if not ward_incidence.empty:

        available_years = sorted(
            ward_incidence[
                "Year"
            ].unique()
        )

        selected_year = _smart_toggle(
            "Select Analysis Year",
            available_years,
            default=available_years[-1],
            key="phase8b_ward_year_toggle",
        )

        year_df = ward_incidence[
            ward_incidence["Year"]
            == selected_year
        ].copy()

        ward_options = _alphabetical(
            year_df["Ward"].unique()
        )

        selected_ward_analysis = _compact_multiselect(
            "Select Ward(s)",
            ward_options,
            default=ward_options,
            key="phase8b_ward_analysis_selection",
        )

        if selected_ward_analysis:

            display_df = year_df[
                year_df["Ward"].isin(
                    selected_ward_analysis
                )
            ].copy()

            display_df = display_df.sort_values(
                "Incidence Rate",
                ascending=False,
                na_position="last",
            )

            _render_bar_chart(
                display_df,
                "Ward",
                "Incidence Rate",
                (
                    f"Ward-wise Incidence Rate — "
                    f"{selected_year}"
                ),
                (
                    f"Incidence per "
                    f"{denominator:,}"
                ),
                height=460,
            )

            _observation_box(
                _bar_observation(
                    display_df,
                    "Ward",
                    "Incidence Rate",
                    (
                        f"cases per "
                        f"{denominator:,} population"
                    ),
                )
            )

            with st.expander(
                "📋 View Ward-wise Incidence Data",
                expanded=False,
            ):

                st.dataframe(
                    display_df[
                        [
                            "Ward",
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

            if not disease_ward_incidence.empty:

                st.markdown(
                    "#### 🦠 Disease Profile within Selected Ward(s)"
                )

                ward_disease = (
                    disease_ward_incidence[
                        (
                            disease_ward_incidence[
                                "Year"
                            ] == selected_year
                        )
                        & (
                            disease_ward_incidence[
                                "Ward"
                            ].isin(
                                selected_ward_analysis
                            )
                        )
                    ].copy()
                )

                if not ward_disease.empty:

                    ward_disease[
                        "Ward | Disease"
                    ] = (
                        ward_disease["Ward"]
                        + " | "
                        + ward_disease["Disease"]
                    )

                    top_ward_disease = (
                        ward_disease
                        .sort_values(
                            "Incidence Rate",
                            ascending=False,
                        )
                        .head(20)
                    )

                    _render_bar_chart(
                        top_ward_disease,
                        "Ward | Disease",
                        "Incidence Rate",
                        (
                            "Disease-specific Incidence "
                            "within Selected Ward(s)"
                        ),
                        (
                            f"Incidence per "
                            f"{denominator:,}"
                        ),
                        height=500,
                    )

                    _observation_box(
                        _bar_observation(
                            top_ward_disease,
                            "Ward | Disease",
                            "Incidence Rate",
                            (
                                f"cases per "
                                f"{denominator:,} population"
                            ),
                        )
                    )

    _methodology_expander(
        "Ward-wise Incidence",
        [
            (
                "Cases are grouped by Ward and Analysis Year."
            ),
            (
                "Each ward's case count is divided by the "
                "matched population for that ward and year."
            ),
            (
                f"The result is multiplied by {denominator:,}."
            ),
            (
                "A higher incidence rate indicates more "
                "reported cases relative to the population "
                "denominator; it is not simply a count ranking."
            ),
        ],
    )

    # ========================================================
    # SECTION 4
    # DISEASE-WISE INCIDENCE
    # ========================================================

    st.divider()

    st.markdown(
        "### 4. 🦠 Disease-wise Incidence Analysis"
    )

    if not disease_ward_incidence.empty:

        disease_years = sorted(
            disease_ward_incidence[
                "Year"
            ].unique()
        )

        disease_year = _smart_toggle(
            "Disease Analysis Year",
            disease_years,
            default=disease_years[-1],
            key="phase8b_disease_year_toggle",
        )

        disease_source = (
            disease_ward_incidence[
                disease_ward_incidence[
                    "Year"
                ] == disease_year
            ].copy()
        )

        disease_options = (
            disease_source[
                "Disease"
            ]
            .value_counts()
            .index
            .tolist()
        )

        selected_diseases = _compact_multiselect(
            "Select Disease(s)",
            disease_options,
            default=disease_options[
                :min(8, len(disease_options))
            ],
            key="phase8b_disease_selection",
        )

        if selected_diseases:

            selected_source = disease_source[
                disease_source[
                    "Disease"
                ].isin(
                    selected_diseases
                )
            ].copy()

            summary_rows = []

            for disease, group in (
                selected_source.groupby(
                    "Disease",
                    observed=True,
                )
            ):

                valid = group[
                    group["Population"].notna()
                    & group["Population"].gt(0)
                ]

                if valid.empty:
                    continue

                cases = int(
                    valid["Cases"].sum()
                )

                population = float(
                    valid["Population"].sum()
                )

                rate = (
                    cases
                    / population
                    * denominator
                )

                summary_rows.append(
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

            disease_summary = pd.DataFrame(
                summary_rows
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
                    disease_summary,
                    "Disease",
                    "Incidence Rate",
                    (
                        f"Disease-wise Incidence — "
                        f"{disease_year}"
                    ),
                    (
                        f"Incidence per "
                        f"{denominator:,}"
                    ),
                    height=450,
                )

                _observation_box(
                    _bar_observation(
                        disease_summary,
                        "Disease",
                        "Incidence Rate",
                        (
                            f"cases per "
                            f"{denominator:,} population"
                        ),
                    )
                )

                with st.expander(
                    "📋 View Disease-wise Incidence Data",
                    expanded=False,
                ):

                    st.dataframe(
                        disease_summary,
                        use_container_width=True,
                        hide_index=True,
                    )

            # ------------------------------------------------
            # WARD-WISE OPTION
            # ------------------------------------------------

            st.markdown(
                "#### 📍 Ward-wise Distribution of Selected Disease(s)"
            )

            disease_ward_options = _alphabetical(
                selected_source[
                    "Ward"
                ].unique()
            )

            selected_disease_wards = _compact_multiselect(
                "Select Ward(s) for Disease Comparison",
                disease_ward_options,
                default=disease_ward_options[
                    :min(
                        8,
                        len(disease_ward_options),
                    )
                ],
                key="phase8b_disease_ward_selection",
            )

            if selected_disease_wards:

                ward_disease_df = (
                    selected_source[
                        selected_source[
                            "Ward"
                        ].isin(
                            selected_disease_wards
                        )
                    ].copy()
                )

                ward_disease_df[
                    "Ward | Disease"
                ] = (
                    ward_disease_df["Ward"]
                    + " | "
                    + ward_disease_df["Disease"]
                )

                ward_disease_df = (
                    ward_disease_df
                    .sort_values(
                        "Incidence Rate",
                        ascending=False,
                    )
                )

                _render_bar_chart(
                    ward_disease_df,
                    "Ward | Disease",
                    "Incidence Rate",
                    (
                        "Ward-wise Disease Incidence Comparison"
                    ),
                    (
                        f"Incidence per "
                        f"{denominator:,}"
                    ),
                    height=500,
                )

                _observation_box(
                    _bar_observation(
                        ward_disease_df,
                        "Ward | Disease",
                        "Incidence Rate",
                        (
                            f"cases per "
                            f"{denominator:,} population"
                        ),
                    )
                )

                with st.expander(
                    "📋 View Ward × Disease Data",
                    expanded=False,
                ):

                    st.dataframe(
                        ward_disease_df[
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

    _methodology_expander(
        "Disease-wise Incidence",
        [
            (
                "Disease-specific cases are first grouped "
                "by Ward × Disease × Year."
            ),
            (
                "Each ward uses its corresponding population "
                "denominator."
            ),
            (
                "For the overall disease comparison, valid "
                "ward populations are summed and compared "
                "with the corresponding summed disease cases."
            ),
            (
                "The Ward-wise option shows how the selected "
                "disease burden varies geographically."
            ),
        ],
    )

    # ========================================================
    # SECTION 5
    # INCIDENCE TRENDS
    # ========================================================

    st.divider()

    st.markdown(
        "### 5. 📈 Incidence Trends"
    )

    monthly_tab, yearly_tab = st.tabs(
        [
            "📅 Monthly Trend",
            "🗓️ Year-wise Trend",
        ]
    )

    with monthly_tab:

        if not monthly_incidence.empty:

            monthly_wards = _alphabetical(
                monthly_incidence[
                    "Ward"
                ].unique()
            )

            selected_monthly_wards = _compact_multiselect(
                "Select Ward(s)",
                monthly_wards,
                default=monthly_wards[
                    :min(
                        5,
                        len(monthly_wards),
                    )
                ],
                key="phase8b_monthly_wards",
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
                    .sort_values(
                        [
                            "Date",
                            "Ward",
                        ]
                    )
                )

                _render_line_chart(
                    monthly_chart,
                    "Period",
                    "Ward",
                    "Incidence Rate",
                    (
                        "Monthly Ward-wise Incidence Trend"
                    ),
                    (
                        f"Incidence per "
                        f"{denominator:,}"
                    ),
                    height=480,
                )

                overall_monthly = (
                    monthly_chart
                    .groupby(
                        [
                            "Date",
                            "Period",
                        ],
                        as_index=False,
                    )[
                        "Incidence Rate"
                    ]
                    .mean()
                    .sort_values("Date")
                )

                _observation_box(
                    _trend_observation(
                        overall_monthly,
                        "Period",
                        "Incidence Rate",
                    )
                )

                with st.expander(
                    "📋 View Monthly Incidence Data",
                    expanded=False,
                ):

                    st.dataframe(
                        monthly_chart[
                            [
                                "Ward",
                                "Year",
                                "Month",
                                "Period",
                                "Cases",
                                "Population",
                                "Population Year Used",
                                "Incidence Rate",
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

        _methodology_expander(
            "Monthly Incidence Trend",
            [
                (
                    "Monthly cases are grouped by "
                    "Ward × Year × Month."
                ),
                (
                    "The annual ward population matched to "
                    "that year is used as the denominator."
                ),
                (
                    "The chart displays chronological "
                    "Month-Year periods."
                ),
            ],
        )

    with yearly_tab:

        if not yearly_incidence.empty:

            chart_df = yearly_incidence.copy()

            chart_df["Year Label"] = (
                chart_df["Year"]
                .astype(str)
            )

            chart_df["Series"] = (
                "Overall Incidence"
            )

            _render_line_chart(
                chart_df,
                "Year Label",
                "Series",
                "Incidence Rate",
                "Year-wise Overall Incidence Trend",
                (
                    f"Incidence per "
                    f"{denominator:,}"
                ),
                height=430,
            )

            _observation_box(
                _trend_observation(
                    chart_df,
                    "Year Label",
                    "Incidence Rate",
                )
            )

            with st.expander(
                "📋 View Year-wise Incidence Data",
                expanded=False,
            ):

                st.dataframe(
                    yearly_incidence,
                    use_container_width=True,
                    hide_index=True,
                )

        _methodology_expander(
            "Year-wise Incidence Trend",
            [
                (
                    "Ward-level cases and valid ward "
                    "populations are aggregated by year."
                ),
                (
                    "Overall yearly incidence is calculated "
                    "from total valid cases divided by total "
                    "matched population."
                ),
                (
                    "The calculation does not average "
                    "individual ward incidence rates."
                ),
            ],
        )

    # ========================================================
    # SECTION 6
    # STATISTICAL SURVEILLANCE
    # ========================================================

    st.divider()

    st.markdown(
        "### 6. 📐 Statistical Surveillance Analysis"
    )

    st.caption(
        "Mean and standard-deviation levels are descriptive "
        "surveillance indicators. They do not independently "
        "confirm an outbreak."
    )

    baseline = _smart_toggle(
        "Statistical Baseline",
        [
            "All Available Years",
            "Last 2 Years",
            "Last 3 Years",
            "Last 5 Years",
        ],
        default="All Available Years",
        key="phase8b_stat_baseline_toggle",
    )

    analysis_type = _smart_toggle(
        "Analysis Type",
        [
            "Overall",
            "Disease",
            "Ward",
            "Facility",
        ],
        default="Overall",
        key="phase8b_stat_type_toggle",
    )

    statistical_source = _apply_baseline(
        case_df,
        baseline,
    )

    statistical_title = (
        "Overall Monthly Cases"
    )

    # --------------------------------------------------------
    # DISEASE
    # --------------------------------------------------------

    if analysis_type == "Disease":

        if "Disease" in statistical_source.columns:

            options = (
                statistical_source[
                    _valid_text(
                        statistical_source[
                            "Disease"
                        ]
                    )
                ]["Disease"]
                .value_counts()
                .index
                .tolist()
            )

            if options:

                selected = _smart_toggle(
                    "Select Disease",
                    options[:min(10, len(options))],
                    default=options[0],
                    key="phase8b_stat_disease_toggle",
                )

                statistical_source = (
                    statistical_source[
                        statistical_source[
                            "Disease"
                        ] == selected
                    ]
                )

                statistical_title = (
                    f"{selected} Monthly Cases"
                )

    # --------------------------------------------------------
    # WARD
    # --------------------------------------------------------

    elif analysis_type == "Ward":

        if "Ward Name" in statistical_source.columns:

            options = _alphabetical(
                statistical_source[
                    _valid_text(
                        statistical_source[
                            "Ward Name"
                        ]
                    )
                ]["Ward Name"].unique()
            )

            if options:

                selected = _smart_toggle(
                    "Select Ward",
                    options,
                    default=options[0],
                    key="phase8b_stat_ward_toggle",
                )

                statistical_source = (
                    statistical_source[
                        statistical_source[
                            "Ward Name"
                        ] == selected
                    ]
                )

                statistical_title = (
                    f"Ward {selected} Monthly Cases"
                )

    # --------------------------------------------------------
    # FACILITY
    # --------------------------------------------------------

    elif analysis_type == "Facility":

        if "Facility Name" in statistical_source.columns:

            options = (
                statistical_source[
                    _valid_text(
                        statistical_source[
                            "Facility Name"
                        ]
                    )
                ]["Facility Name"]
                .value_counts()
                .index
                .tolist()
            )

            if options:

                selected = _smart_toggle(
                    "Select Facility",
                    options[:min(10, len(options))],
                    default=options[0],
                    key="phase8b_stat_facility_toggle",
                )

                statistical_source = (
                    statistical_source[
                        statistical_source[
                            "Facility Name"
                        ] == selected
                    ]
                )

                statistical_title = (
                    f"{selected} Monthly Cases"
                )

    monthly_stats = _monthly_case_series(
        statistical_source
    )

    statistics = _threshold_statistics(
        monthly_stats
    )

    if (
        statistics is not None
        and not monthly_stats.empty
    ):

        c1, c2, c3, c4 = st.columns(4)

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
            monthly_stats,
            statistics,
            (
                f"{statistical_title} — "
                f"Statistical Surveillance"
            ),
        )

        _observation_box(
            _threshold_observation(
                monthly_stats,
                statistics,
            )
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
                        statistics["Mean"],
                        2,
                    ),
                    round(
                        statistics["SD"],
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

        with st.expander(
            "📋 View Statistical Data",
            expanded=False,
        ):

            st.dataframe(
                monthly_stats[
                    [
                        "Period",
                        "Cases",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.dataframe(
                threshold_table,
                use_container_width=True,
                hide_index=True,
            )

    else:

        st.info(
            "Sufficient monthly data is not available "
            "for this statistical analysis."
        )

    _methodology_expander(
        "Statistical Surveillance",
        [
            (
                "Monthly case counts are calculated for "
                "the selected Overall, Disease, Ward or "
                "Facility view."
            ),
            (
                "Missing calendar months between the first "
                "and last available periods are included "
                "with zero cases."
            ),
            (
                "Mean is the arithmetic mean of monthly "
                "case counts in the selected baseline."
            ),
            (
                "SD is the sample standard deviation of "
                "monthly case counts."
            ),
            (
                "Mean + 1 SD, Mean + 2 SD and Mean + 3 SD "
                "are descriptive statistical surveillance levels."
            ),
            (
                "Crossing these levels should prompt review "
                "alongside seasonality, reporting completeness, "
                "testing practices and epidemiological context."
            ),
            (
                "Facility analysis represents case-volume "
                "statistical surveillance, not facility incidence, "
                "because a facility-specific population denominator "
                "is not available."
            ),
        ],
    )

    # ========================================================
    # SECTION 7
    # METHODOLOGY & INTERPRETATION
    # ========================================================

    st.divider()

    st.markdown(
        "### 7. ℹ️ Methodology, Interpretation & Data Quality"
    )

    methodology = pd.DataFrame(
        {
            "Component": [
                "Incidence Formula",
                "Default Denominator",
                "Available Denominators",
                "Population Source",
                "Exact Population Match",
                "Missing Population Year",
                "Future Population Fallback",
                "Ward Incidence",
                "Disease Incidence",
                "Monthly Incidence",
                "Yearly Incidence",
                "Facility Analysis",
                "Statistical Mean",
                "Standard Deviation",
                "Mean + 1 SD",
                "Mean + 2 SD",
                "Mean + 3 SD",
                "Interpretation",
            ],
            "Methodology": [
                (
                    "Cases ÷ Population × selected denominator"
                ),
                (
                    "100,000 population"
                ),
                (
                    "1,000; 10,000; 100,000; 1,000,000"
                ),
                (
                    "Population worksheet in the configured "
                    "Google Sheet"
                ),
                (
                    "Exact Ward × Analysis Year population "
                    "is used when available"
                ),
                (
                    "Closest previous available population "
                    "year for the ward is used"
                ),
                (
                    "If no previous year exists, the nearest "
                    "future available population year is used"
                ),
                (
                    "Ward cases divided by the matched "
                    "ward population"
                ),
                (
                    "Disease cases are calculated using "
                    "corresponding ward populations"
                ),
                (
                    "Monthly ward cases use the matched "
                    "annual ward population denominator"
                ),
                (
                    "Valid ward cases and populations are "
                    "aggregated before calculating yearly rate"
                ),
                (
                    "Case-volume statistical surveillance only; "
                    "not labelled as facility incidence"
                ),
                (
                    "Arithmetic mean of monthly case counts"
                ),
                (
                    "Sample standard deviation of monthly "
                    "case counts"
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
                    "Results support surveillance and programme "
                    "review and should be interpreted with data "
                    "quality, seasonality and epidemiological context"
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
        "Population fallback values should be reviewed before "
        "formal reporting. Statistical Mean/SD levels are "
        "descriptive surveillance indicators and do not, by "
        "themselves, establish or confirm an outbreak."
    )


# ============================================================
# BACKWARD-COMPATIBLE ENTRY POINT
# ============================================================

def render_incidence(df):

    return render_incidence_analysis(df)
