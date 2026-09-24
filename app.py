import inspect
from datetime import datetime

import pandas as pd
import streamlit as st

from phase1_data import (
    load_data,
    refresh_data,
)

from phase2_overview import (
    create_filters,
    apply_filters,
    calculate_kpis,
    render_overview,
)

from phase3_charts import (
    render_charts,
    get_selected_diseases,
)

from phase3_b_lab_pathogen import (
    render_lab_pathogen,
)

from phase4_demographics import (
    render_demographics,
)

from phase5_ward import (
    render_ward,
)

from phase6_map import (
    render_map,
)

from geographic_map import (
    render_geographic_map,
)

from phase7_explorer import (
    render_explorer,
)

from phase8_prediction import (
    render_prediction,
)

from phase9_manual import (
    render_manual,
)

from phase10_validation_kpi import (
    render_validation_kpi,
)

from phase11_drilldown_export import (
    render_drilldown_export,
)

from pdf_report import (
    generate_pdf_report,
    generate_complete_dashboard_pdf,
)

from ppt_report import (
    generate_ppt_report,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Health Facility Management Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# GLOBAL CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 2px;
    }

    .sub-title {
        font-size: 15px;
        color: #555;
        margin-top: 0px;
        margin-bottom: 15px;
    }

    .section-title {
        font-size: 22px;
        font-weight: 650;
        margin-top: 10px;
        margin-bottom: 8px;
    }

    div[data-testid="stMetric"] {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 10px;
        background-color: #ffffff;
    }

    div[data-testid="stDownloadButton"] button {
        width: 100%;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DASHBOARD HEADER
# ============================================================

st.markdown(
    '<div class="main-title">Health Programme Management Dashboard</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="sub-title">
        Facility-wise, ward-wise, demographic, laboratory,
        geographic and programme surveillance analysis
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data(
    show_spinner=False,
)
def get_data():
    return load_data()


try:

    df = get_data()

except Exception as exc:

    st.error(
        "Unable to load the dashboard data."
    )

    st.exception(exc)

    st.stop()


# ============================================================
# BASIC DATA VALIDATION
# ============================================================

if df is None:

    st.error(
        "No data was returned from the data source."
    )

    st.stop()


if not isinstance(df, pd.DataFrame):

    try:
        df = pd.DataFrame(df)

    except Exception:

        st.error(
            "The loaded data could not be converted into a DataFrame."
        )

        st.stop()


if df.empty:

    st.warning(
        "The current data source contains no records."
    )

    st.stop()


# ============================================================
# SESSION STATE INITIALISATION
# ============================================================

if "phase3_selected_diseases" not in st.session_state:

    st.session_state[
        "phase3_selected_diseases"
    ] = []


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## Dashboard Navigation"
    )

    page = st.radio(
        "Select Dashboard Section",
        [
            "Overview",
            "Charts & Trends",
            "Laboratory & Pathogen Analysis",
            "Demographics",
            "Ward Analysis",
            "Map",
            "Geographic Map",
            "Data Explorer",
            "Prediction",
            "User Manual",
            "Validation & KPI",
            "Drill-down & Export",
        ],
        index=0,
    )

    st.divider()

    st.markdown(
        "### Data Controls"
    )

    st.caption(
        f"Available records: {len(df):,}"
    )

    show_data_labels = st.checkbox(
        "Show chart data labels",
        value=False,
        key="global_show_data_labels",
    )

    st.session_state[
        "show_data_labels"
    ] = show_data_labels


# ============================================================
# GLOBAL FILTERS
# ============================================================

st.sidebar.markdown(
    "### Global Filters"
)

try:

    filter_values = create_filters(
        df
    )

except Exception as exc:

    st.sidebar.error(
        "Unable to create dashboard filters."
    )

    st.sidebar.exception(exc)

    filter_values = {}


try:

    filtered_df = apply_filters(
        df=df,
        **filter_values,
    )

except TypeError:

    try:

        filtered_df = apply_filters(
            df,
            **filter_values,
        )

    except Exception as exc:

        st.error(
            "Unable to apply the selected dashboard filters."
        )

        st.exception(exc)

        st.stop()

except Exception as exc:

    st.error(
        "Unable to apply the selected dashboard filters."
    )

    st.exception(exc)

    st.stop()


if filtered_df is None:

    filtered_df = pd.DataFrame(
        columns=df.columns
    )


# ============================================================
# FILTER SUMMARY
# ============================================================

def get_filter_summary():

    summary_parts = []

    def add_summary(
        label,
        value,
    ):

        if value is None:
            return

        if isinstance(
            value,
            (list, tuple, set),
        ):

            values = [
                str(item)
                for item in value
                if str(item).strip()
            ]

            if not values:
                return

            if len(values) > 5:

                display_value = (
                    ", ".join(values[:5])
                    + f" + {len(values) - 5} more"
                )

            else:

                display_value = ", ".join(values)

        else:

            display_value = str(value).strip()

            if not display_value:
                return

        if display_value.lower() in {
            "all",
            "all years",
            "all months",
            "all weeks",
            "all diseases",
            "all facilities",
            "all wards",
            "all genders",
            "all age groups",
            "all records",
            "none",
        }:

            return

        summary_parts.append(
            f"{label}: {display_value}"
        )

    if not isinstance(
        filter_values,
        dict,
    ):

        return "All records"

    possible_labels = {
        "year": "Year",
        "years": "Year",
        "month": "Month",
        "months": "Month",
        "week": "Week",
        "weeks": "Week",
        "disease": "Disease",
        "diseases": "Disease",
        "facility": "Facility",
        "facilities": "Facility",
        "ward": "Ward",
        "wards": "Ward",
        "gender": "Gender",
        "age_group": "Age Group",
        "age": "Age Group",
        "opd_ipd": "OPD/IPD",
        "reporting_date": "Reporting Date",
    }

    for key, value in filter_values.items():

        label = possible_labels.get(
            key,
            str(key).replace(
                "_",
                " ",
            ).title(),
        )

        add_summary(
            label,
            value,
        )

    if not summary_parts:

        return "All records"

    return " | ".join(
        summary_parts
    )


# ============================================================
# REPORTING PERIOD
# ============================================================

def get_reporting_period(data):

    if (
        data is None
        or data.empty
        or "Reporting Date" not in data.columns
    ):

        return "Not available"

    dates = pd.to_datetime(
        data["Reporting Date"],
        errors="coerce",
    ).dropna()

    if dates.empty:

        return "Not available"

    minimum_date = dates.min()
    maximum_date = dates.max()

    if minimum_date.date() == maximum_date.date():

        return minimum_date.strftime(
            "%d %b %Y"
        )

    return (
        minimum_date.strftime("%d %b %Y")
        + " to "
        + maximum_date.strftime("%d %b %Y")
    )


# ============================================================
# CURRENT FILTER INFORMATION
# ============================================================

filter_summary = get_filter_summary()

reporting_period = get_reporting_period(
    filtered_df
)


# ============================================================
# KPI CALCULATION
# ============================================================

try:

    kpis = calculate_kpis(
        filtered_df
    )

except Exception:

    kpis = {}


# ============================================================
# TOP KPI CARDS
# ============================================================

kpi_columns = st.columns(4)


def _get_kpi_value(
    dictionary,
    keys,
    default,
):
    if not isinstance(
        dictionary,
        dict,
    ):
        return default

    for key in keys:

        if key in dictionary:

            value = dictionary[key]

            if value is not None:
                return value

    return default


with kpi_columns[0]:

    total_records = _get_kpi_value(
        kpis,
        [
            "Total Records",
            "total_records",
            "records",
            "Total",
        ],
        len(filtered_df),
    )

    try:
        total_display = f"{int(total_records):,}"
    except Exception:
        total_display = str(total_records)

    st.metric(
        "Total Records",
        total_display,
    )


with kpi_columns[1]:

    disease_count = _get_kpi_value(
        kpis,
        [
            "Diseases",
            "diseases",
            "Disease Count",
            "disease_count",
        ],
        (
            filtered_df["Disease"]
            .dropna()
            .astype(str)
            .str.strip()
            .replace(
                {
                    "": None,
                    "nan": None,
                    "None": None,
                }
            )
            .dropna()
            .nunique()
            if "Disease" in filtered_df.columns
            else 0
        ),
    )

    try:
        disease_display = f"{int(disease_count):,}"
    except Exception:
        disease_display = str(disease_count)

    st.metric(
        "Diseases",
        disease_display,
    )


with kpi_columns[2]:

    facility_count = _get_kpi_value(
        kpis,
        [
            "Facilities",
            "facilities",
            "Facility Count",
            "facility_count",
        ],
        (
            filtered_df["Facility Name"]
            .dropna()
            .astype(str)
            .str.strip()
            .replace(
                {
                    "": None,
                    "nan": None,
                    "None": None,
                }
            )
            .dropna()
            .nunique()
            if "Facility Name" in filtered_df.columns
            else 0
        ),
    )

    try:
        facility_display = f"{int(facility_count):,}"
    except Exception:
        facility_display = str(facility_count)

    st.metric(
        "Facilities",
        facility_display,
    )


with kpi_columns[3]:

    ward_count = _get_kpi_value(
        kpis,
        [
            "Wards",
            "wards",
            "Ward Count",
            "ward_count",
        ],
        (
            filtered_df["Ward Name"]
            .dropna()
            .astype(str)
            .str.strip()
            .replace(
                {
                    "": None,
                    "nan": None,
                    "None": None,
                }
            )
            .dropna()
            .nunique()
            if "Ward Name" in filtered_df.columns
            else 0
        ),
    )

    try:
        ward_display = f"{int(ward_count):,}"
    except Exception:
        ward_display = str(ward_count)

    st.metric(
        "Wards",
        ward_display,
    )


# ============================================================
# REPORT DATA HELPERS
# ============================================================

def _clean_text_series(
    data,
    column,
):

    if (
        data is None
        or data.empty
        or column not in data.columns
    ):

        return pd.Series(
            dtype="object"
        )

    series = (
        data[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return series[
        series.ne("")
        & series.str.lower().ne("nan")
        & series.str.lower().ne("none")
        & series.str.lower().ne("nat")
    ]


def make_frequency_table(
    data,
    column,
    output_column=None,
    limit=None,
    sort_mode="count",
):

    if (
        data is None
        or data.empty
        or column not in data.columns
    ):

        return pd.DataFrame()

    series = _clean_text_series(
        data,
        column,
    )

    if series.empty:

        return pd.DataFrame()

    table = (
        series
        .value_counts()
        .rename_axis(
            output_column or column
        )
        .reset_index(
            name="Records"
        )
    )

    if sort_mode == "alphabetical":

        first_column = (
            output_column or column
        )

        table["_sort"] = (
            table[first_column]
            .astype(str)
            .str.lower()
        )

        table = (
            table
            .sort_values(
                "_sort",
                kind="stable",
            )
            .drop(
                columns="_sort"
            )
        )

    if limit is not None:

        table = table.head(
            int(limit)
        )

    return table.reset_index(
        drop=True
    )


# ============================================================
# PAGE-SPECIFIC REPORT DATA
# ============================================================

def build_page_report_data(
    page_name,
    data,
):

    report_data = []

    if data is None:

        data = pd.DataFrame()

    # --------------------------------------------------------
    # OVERVIEW
    # --------------------------------------------------------

    if page_name == "Overview":

        disease_table = make_frequency_table(
            data,
            "Disease",
            "Disease",
            limit=20,
        )

        facility_table = make_frequency_table(
            data,
            "Facility Name",
            "Facility",
            limit=20,
        )

        ward_table = make_frequency_table(
            data,
            "Ward Name",
            "Ward",
            limit=20,
            sort_mode="alphabetical",
        )

        if not disease_table.empty:

            report_data.append(
                (
                    "Disease-wise Summary",
                    disease_table,
                )
            )

        if not facility_table.empty:

            report_data.append(
                (
                    "Facility-wise Summary",
                    facility_table,
                )
            )

        if not ward_table.empty:

            report_data.append(
                (
                    "Ward-wise Summary",
                    ward_table,
                )
            )

    # --------------------------------------------------------
    # CHARTS & TRENDS
    # --------------------------------------------------------

    elif page_name == "Charts & Trends":

        month_table = pd.DataFrame()

        if "Month" in data.columns:

            month_table = make_frequency_table(
                data,
                "Month",
                "Month",
            )

        if not month_table.empty:

            report_data.append(
                (
                    "Month-wise Programme Trend",
                    month_table,
                )
            )

        # Disease comparison
        if (
            "Month" in data.columns
            and "Disease" in data.columns
        ):

            disease_month_data = data[
                [
                    "Month",
                    "Disease",
                ]
            ].copy()

            disease_month_data["Month"] = (
                disease_month_data["Month"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            disease_month_data["Disease"] = (
                disease_month_data["Disease"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            disease_month_data = (
                disease_month_data[
                    disease_month_data["Month"].ne("")
                    & disease_month_data["Disease"].ne("")
                ]
            )

            if not disease_month_data.empty:

                selected_diseases = (
                    get_selected_diseases()
                )

                if selected_diseases:

                    disease_month_data = (
                        disease_month_data[
                            disease_month_data[
                                "Disease"
                            ].isin(
                                selected_diseases
                            )
                        ]
                    )

                if not disease_month_data.empty:

                    monthly_disease_table = (
                        pd.crosstab(
                            disease_month_data[
                                "Month"
                            ],
                            disease_month_data[
                                "Disease"
                            ],
                        )
                        .reset_index()
                    )

                    report_data.append(
                        (
                            "Monthly Disease Comparison",
                            monthly_disease_table,
                        )
                    )

        disease_table = make_frequency_table(
            data,
            "Disease",
            "Disease",
            limit=20,
        )

        pathogen_column = None

        for column in [
            "Test Performed Pathogen Name",
            "Pathogen Name",
            "Test Performed Pathogen",
            "Pathogen",
        ]:

            if column in data.columns:

                pathogen_column = column
                break

        if not disease_table.empty:

            report_data.append(
                (
                    "Disease-wise Burden",
                    disease_table,
                )
            )

        if pathogen_column is not None:

            pathogen_table = make_frequency_table(
                data,
                pathogen_column,
                "Test Performed Pathogen Name",
                limit=20,
            )

            if not pathogen_table.empty:

                report_data.append(
                    (
                        "Test Performed / Pathogen Name-wise Analysis",
                        pathogen_table,
                    )
                )

        facility_table = make_frequency_table(
            data,
            "Facility Name",
            "Facility",
            limit=20,
        )

        if not facility_table.empty:

            report_data.append(
                (
                    "Facility-wise Burden",
                    facility_table,
                )
            )

        ward_table = make_frequency_table(
            data,
            "Ward Name",
            "Ward",
            limit=100,
            sort_mode="alphabetical",
        )

        if not ward_table.empty:

            report_data.append(
                (
                    "Ward-wise Burden",
                    ward_table,
                )
            )

        opd_table = make_frequency_table(
            data,
            "OPD/IPD",
            "OPD/IPD",
        )

        if not opd_table.empty:

            report_data.append(
                (
                    "OPD / IPD Distribution",
                    opd_table,
                )
            )

        if "Reporting Date" in data.columns:

            date_data = data[
                ["Reporting Date"]
            ].copy()

            date_data["Reporting Date"] = (
                pd.to_datetime(
                    date_data[
                        "Reporting Date"
                    ],
                    errors="coerce",
                )
            )

            date_data = date_data.dropna(
                subset=[
                    "Reporting Date"
                ]
            )

            if not date_data.empty:

                daily_table = (
                    date_data
                    .assign(
                        Date=lambda x:
                        x[
                            "Reporting Date"
                        ].dt.normalize()
                    )
                    .groupby(
                        "Date"
                    )
                    .size()
                    .rename(
                        "Records"
                    )
                    .reset_index()
                )

                report_data.append(
                    (
                        "Reporting Date Trend",
                        daily_table,
                    )
                )

    # --------------------------------------------------------
    # LABORATORY & PATHOGEN
    # --------------------------------------------------------

    elif page_name == "Laboratory & Pathogen Analysis":

        pathogen_column = None

        for column in [
            "Test Performed Pathogen Name",
            "Pathogen Name",
            "Test Performed Pathogen",
            "Pathogen",
        ]:

            if column in data.columns:

                pathogen_column = column
                break

        if pathogen_column is not None:

            pathogen_table = make_frequency_table(
                data,
                pathogen_column,
                "Test Performed Pathogen Name",
                limit=100,
            )

            if not pathogen_table.empty:

                report_data.append(
                    (
                        "Test Performed / Pathogen Name",
                        pathogen_table,
                    )
                )

        if (
            "Test Performed" in data.columns
            and "Pathogen Name" in data.columns
        ):

            test_pathogen = data[
                [
                    "Test Performed",
                    "Pathogen Name",
                ]
            ].copy()

            test_pathogen = (
                test_pathogen
                .fillna("")
                .astype(str)
            )

            test_pathogen[
                "Test Performed / Pathogen"
            ] = (
                test_pathogen[
                    "Test Performed"
                ].str.strip()
                + " - "
                + test_pathogen[
                    "Pathogen Name"
                ].str.strip()
            )

            test_pathogen = test_pathogen[
                test_pathogen[
                    "Test Performed / Pathogen"
                ].str.strip().ne("-")
            ]

            if not test_pathogen.empty:

                table = (
                    test_pathogen[
                        "Test Performed / Pathogen"
                    ]
                    .value_counts()
                    .rename_axis(
                        "Test Performed / Pathogen"
                    )
                    .reset_index(
                        name="Records"
                    )
                    .head(100)
                )

                report_data.append(
                    (
                        "Test + Pathogen Combination",
                        table,
                    )
                )

        if "Disease" in data.columns:

            disease_table = make_frequency_table(
                data,
                "Disease",
                "Disease",
                limit=50,
            )

            if not disease_table.empty:

                report_data.append(
                    (
                        "Disease-wise Laboratory Records",
                        disease_table,
                    )
                )

    # --------------------------------------------------------
    # DEMOGRAPHICS
    # --------------------------------------------------------

    elif page_name == "Demographics":

        for column, label in [
            (
                "Gender",
                "Gender-wise Distribution",
            ),
            (
                "Age Group",
                "Age Group-wise Distribution",
            ),
            (
                "Age",
                "Age-wise Distribution",
            ),
            (
                "OPD/IPD",
                "OPD / IPD Distribution",
            ),
        ]:

            if column in data.columns:

                table = make_frequency_table(
                    data,
                    column,
                    label.replace(
                        "-wise Distribution",
                        "",
                    ),
                    limit=100,
                )

                if not table.empty:

                    report_data.append(
                        (
                            label,
                            table,
                        )
                    )

    # --------------------------------------------------------
    # WARD ANALYSIS
    # --------------------------------------------------------

    elif page_name == "Ward Analysis":

        ward_table = make_frequency_table(
            data,
            "Ward Name",
            "Ward",
            limit=100,
            sort_mode="alphabetical",
        )

        if not ward_table.empty:

            report_data.append(
                (
                    "Ward-wise Burden",
                    ward_table,
                )
            )

        if (
            "Ward Name" in data.columns
            and "Disease" in data.columns
        ):

            ward_disease = (
                pd.crosstab(
                    data["Ward Name"]
                    .fillna("")
                    .astype(str)
                    .str.strip(),
                    data["Disease"]
                    .fillna("")
                    .astype(str)
                    .str.strip(),
                )
                .reset_index()
            )

            if not ward_disease.empty:

                report_data.append(
                    (
                        "Ward-wise Disease Distribution",
                        ward_disease,
                    )
                )

    # --------------------------------------------------------
    # MAP
    # --------------------------------------------------------

    elif page_name == "Map":

        if (
            "Ward Name" in data.columns
            or "Ward" in data.columns
        ):

            ward_column = (
                "Ward Name"
                if "Ward Name" in data.columns
                else "Ward"
            )

            ward_table = make_frequency_table(
                data,
                ward_column,
                "Ward",
                limit=100,
                sort_mode="alphabetical",
            )

            if not ward_table.empty:

                report_data.append(
                    (
                        "Map-linked Ward Distribution",
                        ward_table,
                    )
                )

        if (
            "Facility Name" in data.columns
        ):

            facility_table = make_frequency_table(
                data,
                "Facility Name",
                "Facility",
                limit=100,
            )

            if not facility_table.empty:

                report_data.append(
                    (
                        "Facility Distribution",
                        facility_table,
                    )
                )

    # --------------------------------------------------------
    # GEOGRAPHIC MAP
    # --------------------------------------------------------

    elif page_name == "Geographic Map":

        coordinate_columns = []

        for column in [
            "Address Latitude",
            "Address Longitude",
            "Latitude",
            "Longitude",
        ]:

            if column in data.columns:

                coordinate_columns.append(
                    column
                )

        if coordinate_columns:

            geographic_data = data[
                coordinate_columns
                + (
                    ["Facility Name"]
                    if "Facility Name"
                    in data.columns
                    else []
                )
                + (
                    ["Ward Name"]
                    if "Ward Name"
                    in data.columns
                    else []
                )
            ].copy()

            report_data.append(
                (
                    "Geographic Records",
                    geographic_data.head(500),
                )
            )

        else:

            report_data.append(
                (
                    "Geographic Map Data",
                    pd.DataFrame(
                        {
                            "Status": [
                                "Latitude/Longitude fields are not available."
                            ]
                        }
                    ),
                )
            )

    # --------------------------------------------------------
    # DATA EXPLORER
    # --------------------------------------------------------

    elif page_name == "Data Explorer":

        if data is not None and not data.empty:

            report_data.append(
                (
                    "Filtered Data",
                    data.copy(),
                )
            )

    # --------------------------------------------------------
    # PREDICTION
    # --------------------------------------------------------

    elif page_name == "Prediction":

        if "Disease" in data.columns:

            disease_table = make_frequency_table(
                data,
                "Disease",
                "Disease",
                limit=50,
            )

            if not disease_table.empty:

                report_data.append(
                    (
                        "Current Disease Distribution",
                        disease_table,
                    )
                )

        if "Month" in data.columns:

            month_table = make_frequency_table(
                data,
                "Month",
                "Month",
                limit=12,
            )

            if not month_table.empty:

                report_data.append(
                    (
                        "Current Month Distribution",
                        month_table,
                    )
                )

    # --------------------------------------------------------
    # USER MANUAL
    # --------------------------------------------------------

    elif page_name == "User Manual":

        manual_table = pd.DataFrame(
            {
                "Dashboard Item": [
                    "Global Filters",
                    "Overview",
                    "Charts & Trends",
                    "Laboratory & Pathogen Analysis",
                    "Demographics",
                    "Ward Analysis",
                    "Map",
                    "Geographic Map",
                    "Data Explorer",
                    "Prediction",
                    "Validation & KPI",
                    "Drill-down & Export",
                ],
                "Purpose": [
                    "Filter the dashboard by available programme dimensions.",
                    "View programme-level summary indicators.",
                    "Analyse monthly, disease, facility and ward trends.",
                    "Analyse laboratory and pathogen-related records.",
                    "Analyse age, gender and OPD/IPD distributions.",
                    "Analyse ward-level burden.",
                    "View programme records spatially.",
                    "View facility/record geographic distribution.",
                    "Inspect filtered records.",
                    "Review available programme prediction outputs.",
                    "Review data validation and KPI information.",
                    "Perform detailed drill-down and export operations.",
                ],
            }
        )

        report_data.append(
            (
                "Dashboard User Guide",
                manual_table,
            )
        )

    # --------------------------------------------------------
    # VALIDATION & KPI
    # --------------------------------------------------------

    elif page_name == "Validation & KPI":

        validation_rows = []

        validation_rows.append(
            {
                "Indicator": "Filtered Records",
                "Value": len(data),
            }
        )

        validation_rows.append(
            {
                "Indicator": "Columns Available",
                "Value": len(data.columns),
            }
        )

        if "Disease" in data.columns:

            validation_rows.append(
                {
                    "Indicator": "Unique Diseases",
                    "Value": (
                        _clean_text_series(
                            data,
                            "Disease",
                        ).nunique()
                    ),
                }
            )

        if "Facility Name" in data.columns:

            validation_rows.append(
                {
                    "Indicator": "Unique Facilities",
                    "Value": (
                        _clean_text_series(
                            data,
                            "Facility Name",
                        ).nunique()
                    ),
                }
            )

        if "Ward Name" in data.columns:

            validation_rows.append(
                {
                    "Indicator": "Unique Wards",
                    "Value": (
                        _clean_text_series(
                            data,
                            "Ward Name",
                        ).nunique()
                    ),
                }
            )

        validation_table = pd.DataFrame(
            validation_rows
        )

        report_data.append(
            (
                "Validation & KPI Summary",
                validation_table,
            )
        )

    # --------------------------------------------------------
    # DRILL-DOWN & EXPORT
    # --------------------------------------------------------

    elif page_name == "Drill-down & Export":

        if data is not None and not data.empty:

            report_data.append(
                (
                    "Filtered Drill-down Dataset",
                    data.copy(),
                )
            )

    return report_data


# ============================================================
# PDF GENERATION SAFE WRAPPER
# ============================================================

def _call_pdf_function(
    function,
    page_name,
    data,
    page_report_data=None,
):

    selected_diseases = (
        get_selected_diseases()
    )

    common_values = {
        "page_name": page_name,
        "data": data,
        "df": data,
        "filtered_df": data,
        "kpis": kpis,
        "filter_summary": filter_summary,
        "reporting_period": reporting_period,
        "report_data": page_report_data or [],
        "selected_diseases": selected_diseases,
        "disease_selection": selected_diseases,
        "show_data_labels": st.session_state.get(
            "show_data_labels",
            False,
        ),
    }

    try:

        signature = inspect.signature(
            function
        )

        kwargs = {}

        positional_only = []

        for parameter in signature.parameters.values():

            if parameter.kind == (
                inspect.Parameter.POSITIONAL_ONLY
            ):

                positional_only.append(
                    parameter
                )

                continue

            if parameter.name in common_values:

                kwargs[
                    parameter.name
                ] = common_values[
                    parameter.name
                ]

        if positional_only:

            positional_values = []

            for parameter in positional_only:

                if parameter.name in common_values:

                    positional_values.append(
                        common_values[
                            parameter.name
                        ]
                    )

            return function(
                *positional_values,
                **kwargs,
            )

        return function(
            **kwargs
        )

    except Exception as exc:

        # Fallback attempts for older report functions.
        attempts = [
            lambda: function(
                page_name,
                data,
                kpis,
                filter_summary,
                reporting_period,
                page_report_data or [],
            ),
            lambda: function(
                page_name,
                data,
                kpis,
                filter_summary,
                reporting_period,
            ),
            lambda: function(
                page_name,
                data,
            ),
            lambda: function(
                data,
            ),
        ]

        last_error = exc

        for attempt in attempts:

            try:

                return attempt()

            except Exception as retry_exc:

                last_error = retry_exc

        raise last_error


# ============================================================
# PAGE PDF
# ============================================================

def create_page_pdf(
    page_name,
    data,
):

    page_report_data = (
        build_page_report_data(
            page_name,
            data,
        )
    )

    result = _call_pdf_function(
        generate_pdf_report,
        page_name,
        data,
        page_report_data,
    )

    if result is None:

        raise ValueError(
            "PDF generator returned no data."
        )

    if isinstance(
        result,
        bytes,
    ):

        return result

    if hasattr(
        result,
        "getvalue",
    ):

        return result.getvalue()

    if hasattr(
        result,
        "read",
    ):

        current_position = None

        try:
            current_position = result.tell()
        except Exception:
            pass

        try:

            result.seek(0)

        except Exception:
            pass

        pdf_bytes = result.read()

        if current_position is not None:

            try:
                result.seek(
                    current_position
                )
            except Exception:
                pass

        return pdf_bytes

    return bytes(result)


# ============================================================
# PAGE PDF BUTTON
# ============================================================

def render_page_pdf_button(
    page_name,
    data,
    key_suffix=None,
):

    if key_suffix is None:

        key_suffix = (
            page_name
            .lower()
            .replace(
                " ",
                "_",
            )
            .replace(
                "&",
                "and",
            )
            .replace(
                "/",
                "_",
            )
        )

    button_key = (
        "pdf_page_"
        + key_suffix
    )

    try:

        pdf_bytes = create_page_pdf(
            page_name,
            data,
        )

        filename = (
            "Health_Dashboard_"
            + key_suffix
            + "_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M"
            )
            + ".pdf"
        )

        st.download_button(
            label="📄 Download This Section as PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            key=button_key,
            use_container_width=True,
        )

    except Exception as exc:

        st.error(
            "Unable to generate the PDF for this section."
        )

        st.exception(exc)


# ============================================================
# COMPLETE DASHBOARD PDF
# ============================================================

def create_complete_dashboard_pdf():

    page_names = [
        "Overview",
        "Charts & Trends",
        "Laboratory & Pathogen Analysis",
        "Demographics",
        "Ward Analysis",
        "Map",
        "Geographic Map",
        "Data Explorer",
        "Prediction",
        "User Manual",
        "Validation & KPI",
        "Drill-down & Export",
    ]

    page_data = {}

    for page_name in page_names:

        page_data[
            page_name
        ] = build_page_report_data(
            page_name,
            filtered_df,
        )

    selected_diseases = (
        get_selected_diseases()
    )

    try:

        result = _call_pdf_function(
            generate_complete_dashboard_pdf,
            "Complete Dashboard",
            filtered_df,
            page_data,
        )

    except Exception as exc:

        # Additional compatibility attempt
        try:

            result = generate_complete_dashboard_pdf(
                filtered_df,
                page_data,
                kpis,
                filter_summary,
                reporting_period,
                selected_diseases,
            )

        except Exception:

            raise exc

    if result is None:

        raise ValueError(
            "Complete PDF generator returned no data."
        )

    if isinstance(
        result,
        bytes,
    ):

        return result

    if hasattr(
        result,
        "getvalue",
    ):

        return result.getvalue()

    if hasattr(
        result,
        "read",
    ):

        try:
            result.seek(0)
        except Exception:
            pass

        return result.read()

    return bytes(result)


# ============================================================
# COMPLETE DASHBOARD PPT
# ============================================================

def create_complete_dashboard_ppt():

    selected_diseases = (
        get_selected_diseases()
    )

    common_values = {
        "data": filtered_df,
        "df": filtered_df,
        "filtered_df": filtered_df,
        "kpis": kpis,
        "filter_summary": filter_summary,
        "reporting_period": reporting_period,
        "selected_diseases": selected_diseases,
        "disease_selection": selected_diseases,
    }

    signature = inspect.signature(
        generate_ppt_report
    )

    kwargs = {}

    for parameter in signature.parameters.values():

        if parameter.name in common_values:

            kwargs[
                parameter.name
            ] = common_values[
                parameter.name
            ]

    result = generate_ppt_report(
        **kwargs
    )

    if result is None:

        raise ValueError(
            "PowerPoint generator returned no data."
        )

    if isinstance(
        result,
        bytes,
    ):

        return result

    if hasattr(
        result,
        "getvalue",
    ):

        return result.getvalue()

    if hasattr(
        result,
        "read",
    ):

        try:
            result.seek(0)
        except Exception:
            pass

        return result.read()

    return bytes(result)


# ============================================================
# SIDEBAR DOWNLOADS
# ============================================================

with st.sidebar:

    st.divider()

    st.markdown(
        "### Reports"
    )

    st.caption(
        "Reports use the currently selected Global Dashboard Filters."
    )

    if page == "Charts & Trends":

        selected_diseases = (
            get_selected_diseases()
        )

        if selected_diseases:

            st.caption(
                "Selected diseases: "
                + ", ".join(
                    selected_diseases
                )
            )

    complete_pdf_button = st.button(
        "📄 Prepare Complete Dashboard PDF",
        key="prepare_complete_pdf",
        use_container_width=True,
    )

    if complete_pdf_button:

        with st.spinner(
            "Generating complete dashboard PDF..."
        ):

            try:

                complete_pdf = (
                    create_complete_dashboard_pdf()
                )

                st.session_state[
                    "complete_dashboard_pdf"
                ] = complete_pdf

            except Exception as exc:

                st.session_state[
                    "complete_dashboard_pdf"
                ] = None

                st.error(
                    "Unable to generate complete dashboard PDF."
                )

                st.exception(exc)

    if st.session_state.get(
        "complete_dashboard_pdf"
    ) is not None:

        st.download_button(
            label="⬇️ Download Complete Dashboard PDF",
            data=st.session_state[
                "complete_dashboard_pdf"
            ],
            file_name=(
                "Health_Programme_Management_Dashboard_"
                + datetime.now().strftime(
                    "%Y%m%d_%H%M"
                )
                + ".pdf"
            ),
            mime="application/pdf",
            key="download_complete_pdf",
            use_container_width=True,
        )

    st.divider()

    ppt_button = st.button(
        "📊 Prepare Complete Dashboard PPT",
        key="prepare_complete_ppt",
        use_container_width=True,
    )

    if ppt_button:

        with st.spinner(
            "Generating PowerPoint..."
        ):

            try:

                complete_ppt = (
                    create_complete_dashboard_ppt()
                )

                st.session_state[
                    "complete_dashboard_ppt"
                ] = complete_ppt

            except Exception as exc:

                st.session_state[
                    "complete_dashboard_ppt"
                ] = None

                st.error(
                    "Unable to generate PowerPoint."
                )

                st.exception(exc)

    if st.session_state.get(
        "complete_dashboard_ppt"
    ) is not None:

        st.download_button(
            label="⬇️ Download Complete Dashboard PPT",
            data=st.session_state[
                "complete_dashboard_ppt"
            ],
            file_name=(
                "Health_Programme_Management_Dashboard_"
                + datetime.now().strftime(
                    "%Y%m%d_%H%M"
                )
                + ".pptx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            key="download_complete_ppt",
            use_container_width=True,
        )


# ============================================================
# ACTIVE FILTER SUMMARY
# ============================================================

with st.expander(
    "🔎 Current Dashboard Filter Summary",
    expanded=False,
):

    st.write(
        filter_summary
    )

    st.caption(
        f"Reporting period: {reporting_period}"
    )

    st.caption(
        f"Records after filters: {len(filtered_df):,}"
    )


# ============================================================
# PAGE RENDERING
# ============================================================

try:

    # ========================================================
    # 1. OVERVIEW
    # ========================================================

    if page == "Overview":

        render_overview(
            filtered_df,
            kpis,
        )

        st.divider()

        render_page_pdf_button(
            "Overview",
            filtered_df,
        )

    # ========================================================
    # 2. CHARTS & TRENDS
    # ========================================================

    elif page == "Charts & Trends":

        render_charts(
            filtered_df
        )

        st.divider()

        render_page_pdf_button(
            "Charts & Trends",
            filtered_df,
        )

    # ========================================================
    # 3. LABORATORY & PATHOGEN
    # ========================================================

    elif page == "Laboratory & Pathogen Analysis":

        render_lab_pathogen(
            filtered_df
        )

        st.divider()

        render_page_pdf_button(
            "Laboratory & Pathogen Analysis",
            filtered_df,
        )

    # ========================================================
    # 4. DEMOGRAPHICS
    # ========================================================

    elif page == "Demographics":

        render_demographics(
            filtered_df
        )

        st.divider()

        render_page_pdf_button(
            "Demographics",
            filtered_df,
        )

    # ========================================================
    # 5. WARD ANALYSIS
    # ========================================================

    elif page == "Ward Analysis":

        render_ward(
            filtered_df
        )

        st.divider()

        render_page_pdf_button(
            "Ward Analysis",
            filtered_df,
        )

    # ========================================================
    # 6. MAP
    # ========================================================

    elif page == "Map":

        render_map(
            filtered_df
        )

        st.divider()

        render_page_pdf_button(
            "Map",
            filtered_df,
        )

    # ========================================================
    # 7. GEOGRAPHIC MAP
    # ========================================================

    elif page == "Geographic Map":

        render_geographic_map(
            filtered_df,
            df,
        )

        st.divider()

        st.markdown(
            "### Geographic Map Report"
        )

        st.caption(
            "The PDF uses the same currently filtered dataset "
            "shown in the Geographic Map section."
        )

        render_page_pdf_button(
            "Geographic Map",
            filtered_df,
            key_suffix="geographic_map",
        )

    # ========================================================
    # 8. DATA EXPLORER
    # ========================================================

    elif page == "Data Explorer":

        render_explorer(
            filtered_df
        )

        st.divider()

        render_page_pdf_button(
            "Data Explorer",
            filtered_df,
        )

    # ========================================================
    # 9. PREDICTION
    # ========================================================

    elif page == "Prediction":

        render_prediction(
            filtered_df
        )

        st.divider()

        render_page_pdf_button(
            "Prediction",
            filtered_df,
        )

    # ========================================================
    # 10. USER MANUAL
    # ========================================================

    elif page == "User Manual":

        render_manual()

        st.divider()

        render_page_pdf_button(
            "User Manual",
            filtered_df,
        )

    # ========================================================
    # 11. VALIDATION & KPI
    # ========================================================

    elif page == "Validation & KPI":

        render_validation_kpi(
            filtered_df
        )

        st.divider()

        render_page_pdf_button(
            "Validation & KPI",
            filtered_df,
        )

    # ========================================================
    # 12. DRILL-DOWN & EXPORT
    # ========================================================

    elif page == "Drill-down & Export":

        render_drilldown_export(
            filtered_df
        )

        st.divider()

        render_page_pdf_button(
            "Drill-down & Export",
            filtered_df,
        )


except Exception as exc:

    st.error(
        "This dashboard section could not be loaded."
    )

    st.exception(exc)


# ============================================================
# DATA REFRESH
# ============================================================

st.sidebar.divider()

with st.sidebar:

    st.markdown(
        "### Data Refresh"
    )

    st.caption(
        "Refresh the dashboard from the connected data source."
    )

    if st.button(
        "🔄 Refresh Data",
        key="refresh_data",
        use_container_width=True,
    ):

        try:

            refresh_data()

        except Exception:

            pass

        get_data.clear()

        st.session_state[
            "complete_dashboard_pdf"
        ] = None

        st.session_state[
            "complete_dashboard_ppt"
        ] = None

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="
        text-align:center;
        color:#777;
        font-size:12px;
        padding:8px;
    ">
        Health Programme Management Dashboard
    </div>
    """,
    unsafe_allow_html=True,
)
