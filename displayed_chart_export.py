import copy
import hashlib
import json

import streamlit as st
import pandas as pd

from phase1_data import load_data

from phase2_overview import (
    create_filters,
    apply_filters,
    calculate_kpis,
    render_overview,
)

from phase3_charts import render_charts
from phase3_b_lab_pathogen import render_lab_pathogen
from phase4_demographics import render_demographics
from phase5_ward import render_ward

from phase6_map import render_map
from geographic_map import render_geographic_map

from phase7_explorer import render_explorer
from phase8_prediction import render_prediction
from phase9_manual import render_manual
from phase10_validation_kpi import render_validation_kpi
from phase11_drilldown_export import render_drilldown_export

from pdf_report import generate_pdf_report

from dashboard_pdf_export import (
    generate_captured_dashboard_pdf,
)

from ppt_report import generate_ppt_report

from displayed_chart_export import (
    capture_displayed_charts,
    get_captured_dashboard_content,
    render_displayed_chart_download_controls,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="MSU Mumbai Public Health Surveillance Dashboard",
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

    .block-container {
        padding-top: 0.65rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }

    section[data-testid="stSidebar"] {
        width: 250px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 12px !important;
        border: 1px solid rgba(120, 140, 160, 0.35) !important;
        padding: 10px 12px 8px 12px !important;
        margin-top: 4px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    }

    div[data-testid="stMultiSelect"] label,
    div[data-testid="stDateInput"] label {
        font-size: 11px !important;
        font-weight: 650 !important;
        margin-bottom: 2px !important;
    }

    div[data-testid="stMultiSelect"] > div,
    div[data-testid="stDateInput"] > div {
        min-height: 36px !important;
    }

    div[data-testid="stMultiSelect"] [data-baseweb="select"] {
        min-height: 36px !important;
        border-radius: 7px !important;
    }

    div[data-testid="stDateInput"] input {
        min-height: 34px !important;
        border-radius: 7px !important;
    }

    .st-key-global_reset_filters button {
        min-height: 36px !important;
        border-radius: 7px !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 0.55rem !important;
    }

    [data-testid="stMetric"] {
        padding: 7px 10px !important;
    }

    .dashboard-footer {
        text-align: center;
        color: #777;
        font-size: 12px;
        padding-top: 18px;
    }

    .capture-banner {
        padding: 9px 12px;
        border-radius: 8px;
        background: #eef5fb;
        border: 1px solid #c9d9e8;
        color: #24445f;
        font-size: 13px;
        margin-bottom: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PAGE LIST
# ============================================================

PAGE_OPTIONS = [
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


# ============================================================
# COMPLETE PDF CAPTURE STATE
# ============================================================

CAPTURED_PAGE_REGISTRY_KEY = (
    "complete_dashboard_captured_pages"
)

CAPTURE_QUEUE_KEY = (
    "complete_dashboard_capture_queue"
)

CAPTURE_ACTIVE_KEY = (
    "complete_dashboard_capture_active"
)

CAPTURE_CURRENT_PAGE_KEY = (
    "complete_dashboard_capture_current_page"
)

CAPTURE_FILTER_VALUES_KEY = (
    "complete_dashboard_capture_filter_values"
)

CAPTURE_FILTER_SUMMARY_KEY = (
    "complete_dashboard_capture_filter_summary"
)

CAPTURE_REPORT_PERIOD_KEY = (
    "complete_dashboard_capture_report_period"
)


# ============================================================
# CAPTURE REGISTRY
# ============================================================

def get_captured_page_registry():

    if (
        CAPTURED_PAGE_REGISTRY_KEY
        not in st.session_state
    ):

        st.session_state[
            CAPTURED_PAGE_REGISTRY_KEY
        ] = {}

    return st.session_state[
        CAPTURED_PAGE_REGISTRY_KEY
    ]


# ============================================================
# GENERIC SIGNATURE HELPERS
# ============================================================

def _capture_value_signature(value):

    if value is None:
        return ""

    if isinstance(
        value,
        pd.DataFrame,
    ):

        try:

            work = value.copy()

            work = work.fillna("")

            payload = {
                "columns": [
                    str(column)
                    for column in work.columns
                ],
                "data": (
                    work.astype(str)
                    .to_dict(
                        orient="records"
                    )
                ),
            }

            return json.dumps(
                payload,
                sort_keys=True,
                default=str,
            )

        except Exception:

            return repr(
                value
            )

    if isinstance(
        value,
        dict,
    ):

        try:

            return json.dumps(
                value,
                sort_keys=True,
                default=str,
            )

        except Exception:

            return repr(
                value
            )

    if isinstance(
        value,
        (list, tuple),
    ):

        try:

            return json.dumps(
                value,
                sort_keys=True,
                default=str,
            )

        except Exception:

            return repr(
                value
            )

    if isinstance(
        value,
        (bytes, bytearray),
    ):

        try:

            return hashlib.sha256(
                bytes(value)
            ).hexdigest()

        except Exception:

            return repr(
                value
            )

    return str(
        value
    )


def _get_item_signature(
    page_name,
    item,
    item_type,
):

    if not isinstance(
        item,
        dict,
    ):
        return None

    # Prefer fingerprint already created by
    # displayed_chart_export.py.
    existing_fingerprint = (
        item.get(
            "fingerprint"
        )
    )

    if existing_fingerprint:

        raw_signature = (
            f"{page_name}|"
            f"{item_type}|"
            f"{existing_fingerprint}"
        )

        return hashlib.sha256(
            raw_signature.encode(
                "utf-8",
                errors="ignore",
            )
        ).hexdigest()

    title = str(
        item.get(
            "title",
            "",
        )
    ).strip()

    section = str(
        item.get(
            "section_name",
            "",
        )
    ).strip()

    chart_signature = ""

    chart = item.get(
        "chart"
    )

    if chart is not None:

        try:

            if hasattr(
                chart,
                "to_dict",
            ):

                chart_signature = (
                    json.dumps(
                        chart.to_dict(),
                        sort_keys=True,
                        default=str,
                    )
                )

        except Exception:

            chart_signature = ""

    data_signature = (
        _capture_value_signature(
            item.get(
                "data"
            )
        )
    )

    value_signature = (
        _capture_value_signature(
            item.get(
                "value"
            )
        )
    )

    delta_signature = (
        _capture_value_signature(
            item.get(
                "delta"
            )
        )
    )

    text_signature = (
        _capture_value_signature(
            item.get(
                "text"
            )
        )
    )

    caption_signature = (
        _capture_value_signature(
            item.get(
                "caption"
            )
        )
    )

    raw_signature = (
        f"{page_name}|"
        f"{item_type}|"
        f"{section}|"
        f"{title}|"
        f"{chart_signature}|"
        f"{data_signature}|"
        f"{value_signature}|"
        f"{delta_signature}|"
        f"{text_signature}|"
        f"{caption_signature}"
    )

    return hashlib.sha256(
        raw_signature.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()


# ============================================================
# DEDUPLICATE CAPTURED ITEMS
# ============================================================

def _deduplicate_captured_items(
    page_name,
    items,
    item_type,
):

    if not items:
        return []

    unique = []
    seen = set()

    for item in items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        signature = (
            _get_item_signature(
                page_name,
                item,
                item_type,
            )
        )

        if signature is None:
            continue

        if signature in seen:
            continue

        seen.add(
            signature
        )

        clean_item = dict(
            item
        )

        if not clean_item.get(
            "section_name"
        ):

            clean_item[
                "section_name"
            ] = page_name

        if (
            item_type == "charts"
            and not clean_item.get(
                "title"
            )
        ):

            clean_item[
                "title"
            ] = "Dashboard Chart"

        elif (
            item_type == "tables"
            and not clean_item.get(
                "title"
            )
        ):

            clean_item[
                "title"
            ] = "Displayed Data"

        elif (
            item_type == "images"
            and not clean_item.get(
                "title"
            )
        ):

            clean_item[
                "title"
            ] = "Dashboard Image"

        unique.append(
            clean_item
        )

    return unique


# ============================================================
# NORMALISE CAPTURED CONTENT
# ============================================================

def _normalise_captured_content(
    page_name,
    captured_content,
):

    if not isinstance(
        captured_content,
        dict,
    ):

        captured_content = {}

    charts = (
        _deduplicate_captured_items(
            page_name,
            captured_content.get(
                "charts",
                [],
            ),
            "charts",
        )
    )

    tables = (
        _deduplicate_captured_items(
            page_name,
            captured_content.get(
                "tables",
                [],
            ),
            "tables",
        )
    )

    metrics = (
        _deduplicate_captured_items(
            page_name,
            captured_content.get(
                "metrics",
                [],
            ),
            "metrics",
        )
    )

    notes = (
        _deduplicate_captured_items(
            page_name,
            captured_content.get(
                "notes",
                [],
            ),
            "notes",
        )
    )

    images = (
        _deduplicate_captured_items(
            page_name,
            captured_content.get(
                "images",
                [],
            ),
            "images",
        )
    )

    return {
        "charts": charts,
        "tables": tables,
        "metrics": metrics,
        "notes": notes,
        "images": images,
    }


# ============================================================
# STORE PAGE CAPTURE
# ============================================================

def store_current_page_capture(
    page_name,
    captured_content,
):

    registry = (
        get_captured_page_registry()
    )

    content = (
        _normalise_captured_content(
            page_name,
            captured_content,
        )
    )

    # Replace rather than append.
    # This prevents Streamlit rerun duplication.
    registry[page_name] = {
        "charts": content[
            "charts"
        ],
        "tables": content[
            "tables"
        ],
        "metrics": content[
            "metrics"
        ],
        "notes": content[
            "notes"
        ],
        "images": content[
            "images"
        ],
        "chart_count": len(
            content["charts"]
        ),
        "table_count": len(
            content["tables"]
        ),
        "metric_count": len(
            content["metrics"]
        ),
        "note_count": len(
            content["notes"]
        ),
        "image_count": len(
            content["images"]
        ),
    }


# ============================================================
# GET PAGE CAPTURE
# ============================================================

def get_page_capture(
    page_name,
):

    registry = (
        get_captured_page_registry()
    )

    record = registry.get(
        page_name,
        {},
    )

    return {
        "charts": list(
            record.get(
                "charts",
                [],
            )
        ),
        "tables": list(
            record.get(
                "tables",
                [],
            )
        ),
        "metrics": list(
            record.get(
                "metrics",
                [],
            )
        ),
        "notes": list(
            record.get(
                "notes",
                [],
            )
        ),
        "images": list(
            record.get(
                "images",
                [],
            )
        ),
    }


# ============================================================
# CAPTURE STATUS
# ============================================================

def is_complete_pdf_capture_active():

    return bool(
        st.session_state.get(
            CAPTURE_ACTIVE_KEY,
            False,
        )
    )


# ============================================================
# START CAPTURE
# ============================================================

def start_complete_pdf_capture(
    current_filter_values,
    current_filter_summary,
    current_report_period,
):

    st.session_state[
        CAPTURED_PAGE_REGISTRY_KEY
    ] = {}

    st.session_state[
        CAPTURE_QUEUE_KEY
    ] = list(
        PAGE_OPTIONS
    )

    st.session_state[
        CAPTURE_ACTIVE_KEY
    ] = True

    st.session_state[
        CAPTURE_CURRENT_PAGE_KEY
    ] = PAGE_OPTIONS[0]

    st.session_state[
        CAPTURE_FILTER_VALUES_KEY
    ] = copy.deepcopy(
        current_filter_values
    )

    st.session_state[
        CAPTURE_FILTER_SUMMARY_KEY
    ] = str(
        current_filter_summary
    )

    st.session_state[
        CAPTURE_REPORT_PERIOD_KEY
    ] = current_report_period

    st.session_state.pop(
        "complete_dashboard_pdf",
        None,
    )

    st.session_state.pop(
        "complete_dashboard_pdf_filter",
        None,
    )


# ============================================================
# FINISH CAPTURE
# ============================================================

def finish_complete_pdf_capture():

    st.session_state[
        CAPTURE_ACTIVE_KEY
    ] = False

    st.session_state[
        CAPTURE_QUEUE_KEY
    ] = []

    st.session_state.pop(
        CAPTURE_CURRENT_PAGE_KEY,
        None,
    )

    st.session_state.pop(
        CAPTURE_FILTER_VALUES_KEY,
        None,
    )

    st.session_state.pop(
        CAPTURE_FILTER_SUMMARY_KEY,
        None,
    )

    st.session_state.pop(
        CAPTURE_REPORT_PERIOD_KEY,
        None,
    )


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def get_data():

    return load_data()


df = get_data()


# ============================================================
# DATA VALIDATION
# ============================================================

if df is None or df.empty:

    st.error(
        "No data available from the Google Sheet."
    )

    st.info(
        "Please verify that the Google Sheet is shared as "
        "'Anyone with the link - Viewer' and that the configured "
        "worksheet GID is correct."
    )

    st.stop()


# ============================================================
# CAPTURE PAGE CONTROL
# ============================================================

capture_active = (
    is_complete_pdf_capture_active()
)

if capture_active:

    capture_queue = (
        st.session_state.get(
            CAPTURE_QUEUE_KEY,
            [],
        )
    )

    if capture_queue:

        capture_page = (
            capture_queue[0]
        )

        st.session_state[
            "dashboard_page"
        ] = capture_page

        st.session_state[
            CAPTURE_CURRENT_PAGE_KEY
        ] = capture_page

    else:

        st.session_state[
            CAPTURE_ACTIVE_KEY
        ] = False

        capture_active = False


# ============================================================
# DASHBOARD HEADER
# ============================================================

if not capture_active:

    st.title(
        "🏥 MSU Mumbai Public Health Surveillance Dashboard"
    )

    st.caption(
        "Surveillance • Monitoring • Analysis • Management"
    )

else:

    st.markdown(
        """
        <div class="capture-banner">
            📄 Preparing Complete Dashboard Report —
            capturing dashboard sections, charts, tables,
            metrics, notes and map images.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "📌 Dashboard Menu"
)

page = st.sidebar.radio(
    "Select Section",
    PAGE_OPTIONS,
    key="dashboard_page",
)


# ============================================================
# SIDEBAR RECORD COUNT
# ============================================================

if not capture_active:

    st.sidebar.divider()

    st.sidebar.caption(
        f"Records loaded: {len(df):,}"
    )


# ============================================================
# GLOBAL CHART CONTROL
# ============================================================

if not capture_active:

    st.sidebar.markdown(
        "---"
    )

    st.sidebar.subheader(
        "📊 Chart Display Controls"
    )

    show_data_labels = (
        st.sidebar.checkbox(
            "🏷️ Show Data Labels",
            value=(
                st.session_state.get(
                    "show_data_labels",
                    False,
                )
            ),
            key="show_data_labels",
            help=(
                "Turn ON to display values directly "
                "on dashboard charts."
            ),
        )
    )

    if show_data_labels:

        st.sidebar.success(
            "Data Labels: ON"
        )

    else:

        st.sidebar.info(
            "Data Labels: OFF"
        )

else:

    show_data_labels = (
        st.session_state.get(
            "show_data_labels",
            False,
        )
    )


# ============================================================
# GLOBAL FILTER PANEL
# ============================================================

if not capture_active:

    st.subheader(
        "🎛️ Global Dashboard Control"
    )

    st.caption(
        "Select any filter to update the entire dashboard immediately. "
        "Leave filters blank to include all records."
    )

    with st.container(
        border=True,
        key="global_filter_panel",
    ):

        filter_values = (
            create_filters(
                df
            )
        )

else:

    filter_values = (
        copy.deepcopy(
            st.session_state.get(
                CAPTURE_FILTER_VALUES_KEY,
                {},
            )
        )
    )


# ============================================================
# APPLY GLOBAL FILTERS
# ============================================================

filtered_df = apply_filters(
    df=df,
    **filter_values,
)


if not capture_active:

    st.caption(
        f"📊 Filtered Records: "
        f"**{len(filtered_df):,}** / "
        f"**{len(df):,}**"
    )


# ============================================================
# KPI CALCULATION
# ============================================================

kpis = calculate_kpis(
    filtered_df
)


# ============================================================
# TOP KPI CARDS
# ============================================================

if not capture_active:

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:

        st.metric(
            "Total Records",
            f"{kpis.get('total_records', len(filtered_df)):,}",
        )

    with c2:

        st.metric(
            "Diseases",
            f"{kpis.get('diseases', 0):,}",
        )

    with c3:

        st.metric(
            "Facilities",
            f"{kpis.get('facilities', 0):,}",
        )

    with c4:

        st.metric(
            "Wards",
            f"{kpis.get('wards', 0):,}",
        )

    st.divider()


# ============================================================
# FILTER SUMMARY
# ============================================================

def get_filter_summary():

    if is_complete_pdf_capture_active():

        return (
            st.session_state.get(
                CAPTURE_FILTER_SUMMARY_KEY,
                "All records",
            )
        )

    labels = {
        "year": "Year",
        "month": "Month",
        "week": "Week",
        "disease": "Disease",
        "facility": "Facility",
        "ward": "Ward",
        "gender": "Gender",
        "age_group": "Age Group",
        "opd_ipd": "OPD/IPD",
    }

    selected = []

    for key, label in (
        labels.items()
    ):

        values = (
            filter_values.get(
                key,
                [],
            )
        )

        if values:

            if len(values) <= 5:

                value_text = ", ".join(
                    str(value)
                    for value in values
                )

            else:

                value_text = (
                    f"{len(values)} selected"
                )

            selected.append(
                f"{label}: {value_text}"
            )

    reporting_date = (
        filter_values.get(
            "reporting_date"
        )
    )

    if reporting_date:

        try:

            start_date, end_date = (
                reporting_date
            )

            if (
                start_date
                and end_date
            ):

                selected.append(
                    "Date: "
                    f"{start_date.strftime('%d-%m-%Y')}"
                    " to "
                    f"{end_date.strftime('%d-%m-%Y')}"
                )

            elif start_date:

                selected.append(
                    "From Date: "
                    f"{start_date.strftime('%d-%m-%Y')}"
                )

            elif end_date:

                selected.append(
                    "To Date: "
                    f"{end_date.strftime('%d-%m-%Y')}"
                )

        except Exception:
            pass

    if not selected:
        return "All records"

    return " | ".join(
        selected
    )


# ============================================================
# REPORTING PERIOD
# ============================================================

def get_reporting_period(
    data
):

    if (
        data is None
        or data.empty
        or "Reporting Date"
        not in data.columns
    ):

        return None

    dates = (
        data[
            "Reporting Date"
        ]
        .dropna()
    )

    if dates.empty:
        return None

    try:

        start_date = (
            dates.min()
            .strftime(
                "%d-%m-%Y"
            )
        )

        end_date = (
            dates.max()
            .strftime(
                "%d-%m-%Y"
            )
        )

        return (
            f"{start_date} to {end_date}"
        )

    except Exception:

        return None


# ============================================================
# FREQUENCY TABLE
# ============================================================

def make_frequency_table(
    data,
    column,
    output_name,
    limit=20,
):

    if (
        data is None
        or data.empty
        or column
        not in data.columns
    ):

        return None

    values = (
        data[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    values = values[
        values.ne("")
        & values.ne("nan")
    ]

    if values.empty:
        return None

    return (
        values
        .value_counts()
        .head(limit)
        .rename_axis(
            output_name
        )
        .reset_index(
            name="Records"
        )
    )


# ============================================================
# LAB / PATHOGEN TABLE
# ============================================================

def make_pathogen_table(
    data,
    limit=30,
):

    column = (
        "Test Performed Pathogen Name"
    )

    if (
        data is None
        or data.empty
        or column
        not in data.columns
    ):

        return None

    values = (
        data[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    values = values[
        values.ne("")
        & values.ne("nan")
    ]

    if values.empty:
        return None

    return (
        values
        .value_counts()
        .head(limit)
        .rename_axis(
            "Test Performed Pathogen Name"
        )
        .reset_index(
            name="Records"
        )
    )


# ============================================================
# MONTHLY TABLE
# ============================================================

def make_monthly_table(
    data
):

    if (
        data is None
        or data.empty
    ):

        return None

    if (
        "Year" not in data.columns
        or "Month"
        not in data.columns
    ):

        return None

    monthly = (
        data
        .groupby(
            [
                "Year",
                "Month",
            ],
            dropna=False,
        )
        .size()
        .reset_index(
            name="Records"
        )
    )

    if monthly.empty:
        return None

    monthly["Period"] = (
        monthly["Year"]
        .astype(str)
        + " - "
        + monthly["Month"]
        .astype(str)
    )

    return monthly[
        [
            "Period",
            "Records",
        ]
    ]


# ============================================================
# MAP SUMMARY TABLES
# ============================================================

def make_map_summary_tables(
    data
):

    tables = []

    if (
        data is None
        or data.empty
    ):

        return tables

    ward_column = None

    if "Ward Name" in data.columns:

        ward_column = (
            "Ward Name"
        )

    elif "Ward" in data.columns:

        ward_column = "Ward"

    if ward_column:

        ward_table = (
            make_frequency_table(
                data,
                ward_column,
                "Ward",
                limit=50,
            )
        )

        if ward_table is not None:

            tables.append(
                (
                    "Map – Ward-wise Case Distribution",
                    ward_table,
                )
            )

    if (
        "Address Latitude"
        in data.columns
        and "Address Longitude"
        in data.columns
    ):

        coordinate_data = (
            data[
                [
                    "Address Latitude",
                    "Address Longitude",
                ]
            ]
            .copy()
        )

        coordinate_data = (
            coordinate_data
            .dropna()
            .drop_duplicates()
        )

        if not coordinate_data.empty:

            tables.append(
                (
                    "Geographic Map – Available Coordinates",
                    coordinate_data.head(
                        100
                    ),
                )
            )

    return tables


# ============================================================
# PAGE-SPECIFIC MANAGEMENT TABLES
# ============================================================

def build_management_tables(
    page_name,
    data,
):

    tables = []

    if (
        data is None
        or data.empty
    ):

        return tables

    # --------------------------------------------------------
    # OVERVIEW
    # --------------------------------------------------------

    if page_name == "Overview":

        if "Ward Name" in data.columns:

            ward_series = (
                data["Ward Name"]
            )

        elif "Ward" in data.columns:

            ward_series = (
                data["Ward"]
            )

        else:

            ward_series = (
                pd.Series(
                    dtype="object"
                )
            )

        kpi_table = (
            pd.DataFrame(
                [
                    {
                        "Indicator": "Total Records",
                        "Value": int(
                            len(data)
                        ),
                    },
                    {
                        "Indicator": "Diseases",
                        "Value": int(
                            data["Disease"]
                            .dropna()
                            .astype(str)
                            .str.strip()
                            .replace(
                                "",
                                pd.NA,
                            )
                            .dropna()
                            .nunique()
                        )
                        if "Disease"
                        in data.columns
                        else 0,
                    },
                    {
                        "Indicator": "Facilities",
                        "Value": int(
                            data[
                                "Facility Name"
                            ]
                            .dropna()
                            .astype(str)
                            .str.strip()
                            .replace(
                                "",
                                pd.NA,
                            )
                            .dropna()
                            .nunique()
                        )
                        if "Facility Name"
                        in data.columns
                        else 0,
                    },
                    {
                        "Indicator": "Wards",
                        "Value": int(
                            ward_series
                            .dropna()
                            .astype(str)
                            .str.strip()
                            .replace(
                                "",
                                pd.NA,
                            )
                            .dropna()
                            .nunique()
                        ),
                    },
                ]
            )
        )

        tables.append(
            (
                "Overview – Key Programme Indicators",
                kpi_table,
            )
        )

        disease_table = (
            make_frequency_table(
                data,
                "Disease",
                "Disease",
                limit=20,
            )
        )

        if disease_table is not None:

            tables.append(
                (
                    "Overview – Disease-wise Burden",
                    disease_table,
                )
            )

        facility_table = (
            make_frequency_table(
                data,
                "Facility Name",
                "Facility",
                limit=20,
            )
        )

        if facility_table is not None:

            tables.append(
                (
                    "Overview – Facility-wise Burden",
                    facility_table,
                )
            )

        ward_column = (
            "Ward Name"
            if "Ward Name"
            in data.columns
            else "Ward"
            if "Ward"
            in data.columns
            else None
        )

        if ward_column:

            ward_table = (
                make_frequency_table(
                    data,
                    ward_column,
                    "Ward",
                    limit=30,
                )
            )

            if ward_table is not None:

                tables.append(
                    (
                        "Overview – Ward-wise Burden",
                        ward_table,
                    )
                )

        gender_table = (
            make_frequency_table(
                data,
                "Gender",
                "Gender",
                limit=10,
            )
        )

        if gender_table is not None:

            tables.append(
                (
                    "Overview – Gender-wise Distribution",
                    gender_table,
                )
            )

        age_table = (
            make_frequency_table(
                data,
                "Age Group",
                "Age Group",
                limit=20,
            )
        )

        if age_table is not None:

            tables.append(
                (
                    "Overview – Age Group-wise Distribution",
                    age_table,
                )
            )

        opd_table = (
            make_frequency_table(
                data,
                "OPD/IPD",
                "OPD/IPD",
                limit=10,
            )
        )

        if opd_table is not None:

            tables.append(
                (
                    "Overview – OPD / IPD Distribution",
                    opd_table,
                )
            )

        monthly_table = (
            make_monthly_table(
                data
            )
        )

        if monthly_table is not None:

            tables.append(
                (
                    "Overview – Month-wise Programme Analysis",
                    monthly_table,
                )
            )

    # --------------------------------------------------------
    # LABORATORY
    # --------------------------------------------------------

    elif (
        page_name
        == "Laboratory & Pathogen Analysis"
    ):

        pathogen_table = (
            make_pathogen_table(
                data
            )
        )

        if pathogen_table is not None:

            tables.append(
                (
                    "Laboratory – Test Performed Pathogen Name-wise Analysis",
                    pathogen_table,
                )
            )

    # --------------------------------------------------------
    # DEMOGRAPHICS
    # --------------------------------------------------------

    elif page_name == "Demographics":

        gender_table = (
            make_frequency_table(
                data,
                "Gender",
                "Gender",
                limit=10,
            )
        )

        if gender_table is not None:

            tables.append(
                (
                    "Demographics – Gender-wise Distribution",
                    gender_table,
                )
            )

        age_table = (
            make_frequency_table(
                data,
                "Age Group",
                "Age Group",
                limit=20,
            )
        )

        if age_table is not None:

            tables.append(
                (
                    "Demographics – Age Group-wise Distribution",
                    age_table,
                )
            )

    # --------------------------------------------------------
    # WARD
    # --------------------------------------------------------

    elif page_name == "Ward Analysis":

        ward_column = (
            "Ward Name"
            if "Ward Name"
            in data.columns
            else "Ward"
            if "Ward"
            in data.columns
            else None
        )

        if ward_column:

            ward_table = (
                make_frequency_table(
                    data,
                    ward_column,
                    "Ward",
                    limit=50,
                )
            )

            if ward_table is not None:

                tables.append(
                    (
                        "Ward Analysis – Ward-wise Burden",
                        ward_table,
                    )
                )

    # --------------------------------------------------------
    # MAP
    # --------------------------------------------------------

    elif page_name == "Map":

        tables.extend(
            make_map_summary_tables(
                data
            )
        )

    # --------------------------------------------------------
    # GEOGRAPHIC MAP
    # --------------------------------------------------------

    elif page_name == "Geographic Map":

        tables.extend(
            make_map_summary_tables(
                data
            )
        )

        if (
            "Address Latitude"
            not in data.columns
            or "Address Longitude"
            not in data.columns
        ):

            tables.append(
                (
                    "Geographic Map – Coordinate Availability",
                    pd.DataFrame(
                        [
                            {
                                "Status": (
                                    "Address Latitude / "
                                    "Address Longitude "
                                    "columns are not available"
                                )
                            }
                        ]
                    ),
                )
            )

    # --------------------------------------------------------
    # DATA EXPLORER
    # --------------------------------------------------------

    elif page_name == "Data Explorer":

        tables.append(
            (
                "Data Explorer – Filtered Data Summary",
                pd.DataFrame(
                    [
                        {
                            "Indicator": "Filtered Records",
                            "Value": len(data),
                        },
                        {
                            "Indicator": "Columns Available",
                            "Value": len(
                                data.columns
                            ),
                        },
                    ]
                ),
            )
        )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    elif page_name == "Validation & KPI":

        tables.append(
            (
                "Validation & KPI – Dataset Summary",
                pd.DataFrame(
                    [
                        {
                            "Indicator": "Records",
                            "Value": len(data),
                        },
                        {
                            "Indicator": "Missing Values",
                            "Value": int(
                                data.isna()
                                .sum()
                                .sum()
                            ),
                        },
                        {
                            "Indicator": "Duplicate Rows",
                            "Value": int(
                                data.duplicated()
                                .sum()
                            ),
                        },
                    ]
                ),
            )
        )

    return tables


# ============================================================
# INDIVIDUAL PAGE REPORT DATA
# ============================================================

def build_individual_page_report_data(
    page_name,
    data,
):

    tables = []
    charts = []

    if (
        data is None
        or data.empty
    ):

        return tables, charts

    disease_table = (
        make_frequency_table(
            data,
            "Disease",
            "Disease",
        )
    )

    if disease_table is not None:

        tables.append(
            (
                "Disease-wise Burden",
                disease_table,
            )
        )

        charts.append(
            {
                "dataframe": disease_table,
                "x_column": "Disease",
                "y_column": "Records",
                "title": "Disease-wise Burden",
            }
        )

    facility_table = (
        make_frequency_table(
            data,
            "Facility Name",
            "Facility",
        )
    )

    if facility_table is not None:

        tables.append(
            (
                "Facility-wise Burden",
                facility_table,
            )
        )

        charts.append(
            {
                "dataframe": facility_table,
                "x_column": "Facility",
                "y_column": "Records",
                "title": "Facility-wise Burden",
            }
        )

    ward_column = None

    if "Ward Name" in data.columns:

        ward_column = (
            "Ward Name"
        )

    elif "Ward" in data.columns:

        ward_column = "Ward"

    if ward_column:

        ward_table = (
            make_frequency_table(
                data,
                ward_column,
                "Ward",
            )
        )

        if ward_table is not None:

            tables.append(
                (
                    "Ward-wise Burden",
                    ward_table,
                )
            )

            charts.append(
                {
                    "dataframe": ward_table,
                    "x_column": "Ward",
                    "y_column": "Records",
                    "title": "Ward-wise Burden",
                }
            )

    gender_table = (
        make_frequency_table(
            data,
            "Gender",
            "Gender",
        )
    )

    if gender_table is not None:

        tables.append(
            (
                "Gender-wise Distribution",
                gender_table,
            )
        )

    age_table = (
        make_frequency_table(
            data,
            "Age Group",
            "Age Group",
        )
    )

    if age_table is not None:

        tables.append(
            (
                "Age Group-wise Distribution",
                age_table,
            )
        )

    opd_table = (
        make_frequency_table(
            data,
            "OPD/IPD",
            "OPD/IPD",
        )
    )

    if opd_table is not None:

        tables.append(
            (
                "OPD / IPD Distribution",
                opd_table,
            )
        )

    monthly = (
        make_monthly_table(
            data
        )
    )

    if monthly is not None:

        tables.append(
            (
                "Month-wise Analysis",
                monthly,
            )
        )

        charts.append(
            {
                "dataframe": monthly,
                "x_column": "Period",
                "y_column": "Records",
                "title": "Month-wise Analysis",
            }
        )

    return tables, charts


# ============================================================
# INDIVIDUAL PAGE PDF
# ============================================================

def create_page_pdf(
    page_name,
    data,
):

    tables, charts = (
        build_individual_page_report_data(
            page_name,
            data,
        )
    )

    report_period = (
        get_reporting_period(
            data
        )
    )

    filter_summary = (
        get_filter_summary()
    )

    return generate_pdf_report(
        report_title=page_name,
        df=data,
        kpis=kpis,
        tables=tables,
        charts=charts,
        report_period=report_period,
        filter_summary=filter_summary,
    )


def render_page_pdf_button(
    page_name,
    data,
):

    try:

        pdf_bytes = (
            create_page_pdf(
                page_name,
                data,
            )
        )

        safe_name = (
            page_name
            .replace(
                "&",
                "and",
            )
            .replace(
                "/",
                "_",
            )
            .replace(
                "-",
                "_",
            )
            .replace(
                " ",
                "_",
            )
        )

        st.download_button(
            label="📄 Download This Page PDF",
            data=pdf_bytes,
            file_name=(
                f"{safe_name}_Report.pdf"
            ),
            mime="application/pdf",
            key=(
                f"pdf_page_{safe_name}"
            ),
        )

    except Exception as e:

        st.error(
            "PDF report could not be generated."
        )

        st.exception(
            e
        )


# ============================================================
# COMPLETE DASHBOARD PDF DATA
# ============================================================

def build_complete_dashboard_pages():

    captured_registry = (
        get_captured_page_registry()
    )

    dashboard_pages = []

    for page_name in PAGE_OPTIONS:

        page_capture = (
            captured_registry.get(
                page_name,
                {},
            )
        )

        captured_charts = (
            _deduplicate_captured_items(
                page_name,
                page_capture.get(
                    "charts",
                    [],
                ),
                "charts",
            )
        )

        captured_tables = (
            _deduplicate_captured_items(
                page_name,
                page_capture.get(
                    "tables",
                    [],
                ),
                "tables",
            )
        )

        captured_metrics = (
            _deduplicate_captured_items(
                page_name,
                page_capture.get(
                    "metrics",
                    [],
                ),
                "metrics",
            )
        )

        captured_notes = (
            _deduplicate_captured_items(
                page_name,
                page_capture.get(
                    "notes",
                    [],
                ),
                "notes",
            )
        )

        captured_images = (
            _deduplicate_captured_items(
                page_name,
                page_capture.get(
                    "images",
                    [],
                ),
                "images",
            )
        )

        # ----------------------------------------------------
        # MANAGEMENT TABLES
        # ----------------------------------------------------

        management_tables = (
            build_management_tables(
                page_name,
                filtered_df,
            )
        )

        page_tables = []

        # First include actual tables displayed
        # on the dashboard.
        for item in captured_tables:

            dataframe = (
                item.get(
                    "data"
                )
            )

            if (
                isinstance(
                    dataframe,
                    pd.DataFrame,
                )
                and not dataframe.empty
            ):

                page_tables.append(
                    {
                        "title": (
                            item.get(
                                "title"
                            )
                            or item.get(
                                "section_name"
                            )
                            or "Displayed Data"
                        ),
                        "section_name": (
                            item.get(
                                "section_name"
                            )
                            or page_name
                        ),
                        "dataframe": dataframe,
                        "source": "captured",
                    }
                )

        # Then add management/support tables.
        for title, dataframe in (
            management_tables
        ):

            if (
                dataframe is None
                or dataframe.empty
            ):
                continue

            page_tables.append(
                {
                    "title": title,
                    "section_name": page_name,
                    "dataframe": dataframe,
                    "source": "management",
                }
            )

        # ----------------------------------------------------
        # METRICS
        # ----------------------------------------------------

        page_metrics = []

        for item in captured_metrics:

            page_metrics.append(
                {
                    "title": (
                        item.get(
                            "title"
                        )
                        or item.get(
                            "label"
                        )
                        or "Metric"
                    ),
                    "label": (
                        item.get(
                            "label"
                        )
                        or item.get(
                            "title"
                        )
                        or "Metric"
                    ),
                    "value": (
                        item.get(
                            "value",
                            "",
                        )
                    ),
                    "delta": (
                        item.get(
                            "delta",
                            "",
                        )
                    ),
                    "section_name": (
                        item.get(
                            "section_name"
                        )
                        or page_name
                    ),
                }
            )

        # ----------------------------------------------------
        # NOTES
        # ----------------------------------------------------

        notes = []

        for item in captured_notes:

            text = str(
                item.get(
                    "text",
                    "",
                )
            ).strip()

            if not text:
                continue

            notes.append(
                {
                    "text": text,
                    "note_type": (
                        item.get(
                            "note_type",
                            "info",
                        )
                    ),
                    "section_name": (
                        item.get(
                            "section_name"
                        )
                        or page_name
                    ),
                    "source": "captured",
                }
            )

        # ----------------------------------------------------
        # PAGE-SPECIFIC NOTES
        # ----------------------------------------------------

        if page_name == "Map":

            if not captured_images:

                notes.append(
                    {
                        "text": (
                            "Map visualisation is represented "
                            "through the available dashboard "
                            "summary data where a static map "
                            "image was not captured."
                        ),
                        "note_type": "info",
                        "section_name": "Map",
                        "source": "system",
                    }
                )

        if page_name == "Geographic Map":

            if (
                "Address Latitude"
                not in filtered_df.columns
                or "Address Longitude"
                not in filtered_df.columns
            ):

                notes.append(
                    {
                        "text": (
                            "Geographic map coordinates are "
                            "not available because Address "
                            "Latitude and Address Longitude "
                            "columns are unavailable in the "
                            "filtered dataset."
                        ),
                        "note_type": "warning",
                        "section_name": (
                            "Geographic Map"
                        ),
                        "source": "system",
                    }
                )

            elif not captured_images:

                notes.append(
                    {
                        "text": (
                            "Address Latitude and Address "
                            "Longitude data are available. "
                            "The geographic map is represented "
                            "through supporting geographic "
                            "summary tables where a static map "
                            "image was not captured."
                        ),
                        "note_type": "info",
                        "section_name": (
                            "Geographic Map"
                        ),
                        "source": "system",
                    }
                )

        if page_name == "User Manual":

            notes.append(
                {
                    "text": (
                        "This section contains dashboard "
                        "user guidance and operational "
                        "instructions."
                    ),
                    "note_type": "info",
                    "section_name": (
                        "User Manual"
                    ),
                    "source": "system",
                }
            )

        if page_name == "Prediction":

            if not captured_charts:

                notes.append(
                    {
                        "text": (
                            "Prediction results are included "
                            "only where prediction outputs "
                            "were available and captured "
                            "during dashboard rendering."
                        ),
                        "note_type": "info",
                        "section_name": (
                            "Prediction"
                        ),
                        "source": "system",
                    }
                )

        # ----------------------------------------------------
        # IMAGES / MAPS
        # ----------------------------------------------------

        page_images = []

        for item in captured_images:

            image_data = (
                item.get(
                    "data"
                )
            )

            if not image_data:
                continue

            page_images.append(
                {
                    "title": (
                        item.get(
                            "title"
                        )
                        or "Dashboard Image"
                    ),
                    "section_name": (
                        item.get(
                            "section_name"
                        )
                        or page_name
                    ),
                    "caption": (
                        item.get(
                            "caption",
                            "",
                        )
                    ),
                    "type": (
                        item.get(
                            "type",
                            "image",
                        )
                    ),
                    "data": image_data,
                }
            )

        dashboard_pages.append(
            {
                "title": page_name,
                "section_name": page_name,
                "df": filtered_df,
                "kpis": kpis,
                "tables": page_tables,
                "charts": captured_charts,
                "metrics": page_metrics,
                "images": page_images,
                "notes": notes,
            }
        )

    return dashboard_pages


# ============================================================
# COMPLETE DASHBOARD PDF
# ============================================================

def create_complete_dashboard_pdf():

    report_period = (
        st.session_state.get(
            CAPTURE_REPORT_PERIOD_KEY
        )
    )

    if not report_period:

        report_period = (
            get_reporting_period(
                filtered_df
            )
        )

    filter_summary = (
        st.session_state.get(
            CAPTURE_FILTER_SUMMARY_KEY
        )
    )

    if not filter_summary:

        filter_summary = (
            get_filter_summary()
        )

    dashboard_pages = (
        build_complete_dashboard_pages()
    )

    return generate_captured_dashboard_pdf(
        pages=dashboard_pages,
        report_period=report_period,
        filter_summary=filter_summary,
    )


# ============================================================
# COMPLETE POWERPOINT
# ============================================================

def create_complete_dashboard_ppt():

    report_period = (
        get_reporting_period(
            filtered_df
        )
    )

    filter_summary = (
        get_filter_summary()
    )

    return generate_ppt_report(
        df=filtered_df,
        report_period=report_period,
        filter_summary=filter_summary,
    )


# ============================================================
# SIDEBAR PDF SECTION
# ============================================================

if not capture_active:

    st.sidebar.markdown(
        "---"
    )

    st.sidebar.subheader(
        "📄 PDF Reports"
    )

    st.sidebar.caption(
        "Generate a complete consolidated dashboard report."
    )


# ============================================================
# CAPTURE STATUS
# ============================================================

captured_pages = (
    get_captured_page_registry()
)

captured_chart_count = sum(
    len(
        record.get(
            "charts",
            [],
        )
    )
    for record
    in captured_pages.values()
)

captured_table_count = sum(
    len(
        record.get(
            "tables",
            [],
        )
    )
    for record
    in captured_pages.values()
)

captured_metric_count = sum(
    len(
        record.get(
            "metrics",
            [],
        )
    )
    for record
    in captured_pages.values()
)

captured_note_count = sum(
    len(
        record.get(
            "notes",
            [],
        )
    )
    for record
    in captured_pages.values()
)

captured_image_count = sum(
    len(
        record.get(
            "images",
            [],
        )
    )
    for record
    in captured_pages.values()
)


if is_complete_pdf_capture_active():

    capture_queue = (
        st.session_state.get(
            CAPTURE_QUEUE_KEY,
            [],
        )
    )

    total_pages = len(
        PAGE_OPTIONS
    )

    completed_pages = (
        total_pages
        - len(capture_queue)
    )

    st.sidebar.info(
        "Automatic PDF capture running..."
    )

    st.sidebar.caption(
        f"Captured pages: "
        f"{completed_pages} / "
        f"{total_pages}"
    )

    st.sidebar.caption(
        f"Charts: {captured_chart_count} | "
        f"Tables: {captured_table_count}"
    )

    st.sidebar.caption(
        f"Metrics: {captured_metric_count} | "
        f"Notes: {captured_note_count} | "
        f"Images/Maps: {captured_image_count}"
    )

elif captured_pages:

    st.sidebar.caption(
        f"Captured dashboard pages: "
        f"{len(captured_pages)}"
    )

    st.sidebar.caption(
        f"Charts: {captured_chart_count} | "
        f"Tables: {captured_table_count}"
    )

    st.sidebar.caption(
        f"Metrics: {captured_metric_count} | "
        f"Notes: {captured_note_count} | "
        f"Images/Maps: {captured_image_count}"
    )


# ============================================================
# GENERATE COMPLETE PDF
# ============================================================

if not is_complete_pdf_capture_active():

    if st.sidebar.button(
        "📚 Generate Complete Dashboard PDF",
        use_container_width=True,
    ):

        current_summary = (
            get_filter_summary()
        )

        current_period = (
            get_reporting_period(
                filtered_df
            )
        )

        start_complete_pdf_capture(
            current_filter_values=filter_values,
            current_filter_summary=current_summary,
            current_report_period=current_period,
        )

        st.rerun()


# ============================================================
# COMPLETE PDF DOWNLOAD
# ============================================================

if (
    "complete_dashboard_pdf"
    in st.session_state
):

    current_filter = (
        get_filter_summary()
    )

    generated_filter = (
        st.session_state.get(
            "complete_dashboard_pdf_filter",
            "",
        )
    )

    if (
        current_filter
        == generated_filter
    ):

        st.sidebar.download_button(
            label=(
                "⬇️ Download Complete Dashboard PDF"
            ),
            data=(
                st.session_state[
                    "complete_dashboard_pdf"
                ]
            ),
            file_name=(
                "MSU_Mumbai_Complete_Dashboard_Report.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
            key=(
                "download_complete_dashboard_pdf"
            ),
        )

    else:

        st.sidebar.info(
            "Dashboard filters have changed. "
            "Generate the complete PDF again."
        )


# ============================================================
# POWERPOINT
# ============================================================

if not capture_active:

    st.sidebar.markdown(
        "---"
    )

    st.sidebar.subheader(
        "📊 PowerPoint Report"
    )

    st.sidebar.caption(
        "Generate a management presentation from "
        "the currently selected dashboard filters."
    )


if (
    not is_complete_pdf_capture_active()
    and st.sidebar.button(
        "📊 Generate PowerPoint",
        use_container_width=True,
    )
):

    try:

        with st.spinner(
            "Generating PowerPoint report..."
        ):

            st.session_state[
                "complete_dashboard_ppt"
            ] = (
                create_complete_dashboard_ppt()
            )

            st.session_state[
                "complete_dashboard_ppt_filter"
            ] = (
                get_filter_summary()
            )

        st.sidebar.success(
            "PowerPoint generated successfully."
        )

    except Exception as e:

        st.sidebar.error(
            "PowerPoint report could not be generated."
        )

        st.sidebar.exception(
            e
        )


# ============================================================
# POWERPOINT DOWNLOAD
# ============================================================

if (
    "complete_dashboard_ppt"
    in st.session_state
):

    current_filter = (
        get_filter_summary()
    )

    generated_ppt_filter = (
        st.session_state.get(
            "complete_dashboard_ppt_filter",
            "",
        )
    )

    if (
        current_filter
        == generated_ppt_filter
    ):

        st.sidebar.download_button(
            label="⬇️ Download PowerPoint",
            data=(
                st.session_state[
                    "complete_dashboard_ppt"
                ]
            ),
            file_name=(
                "MSU_Mumbai_Dashboard_Management_Report.pptx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            use_container_width=True,
            key=(
                "download_complete_dashboard_ppt"
            ),
        )

    else:

        st.sidebar.info(
            "Dashboard filters have changed. "
            "Generate the PowerPoint again."
        )


# ============================================================
# HELPER: CAPTURE CURRENT PAGE
# ============================================================

def capture_and_store_page(
    page_name,
    render_function,
    *args,
    **kwargs,
):
    """
    Render one dashboard page inside the capture context,
    collect all displayed content, and replace that page's
    previous capture in the complete-dashboard registry.
    """

    with capture_displayed_charts():

        render_function(
            *args,
            **kwargs,
        )

    captured_content = (
        get_captured_dashboard_content()
    )

    store_current_page_capture(
        page_name,
        captured_content,
    )

    return captured_content


# ============================================================
# PAGE RENDERING
# ============================================================

try:

    # ========================================================
    # OVERVIEW
    # ========================================================

    if page == "Overview":

        capture_and_store_page(
            "Overview",
            render_overview,
            filtered_df,
        )

        if not capture_active:

            st.divider()

            render_page_pdf_button(
                "Overview",
                filtered_df,
            )


    # ========================================================
    # CHARTS & TRENDS
    # ========================================================

    elif page == "Charts & Trends":

        capture_and_store_page(
            "Charts & Trends",
            render_charts,
            filtered_df,
        )

        if not capture_active:

            st.divider()

            render_displayed_chart_download_controls(
                filter_summary=(
                    get_filter_summary()
                ),
                base_filename=(
                    "MSU_Mumbai_Charts_Trends_"
                    "Displayed_Charts"
                ),
            )

            st.divider()

            render_page_pdf_button(
                "Charts & Trends",
                filtered_df,
            )


    # ========================================================
    # LABORATORY & PATHOGEN
    # ========================================================

    elif (
        page
        == "Laboratory & Pathogen Analysis"
    ):

        capture_and_store_page(
            "Laboratory & Pathogen Analysis",
            render_lab_pathogen,
            filtered_df,
        )

        if not capture_active:

            st.divider()

            render_page_pdf_button(
                "Laboratory & Pathogen Analysis",
                filtered_df,
            )


    # ========================================================
    # DEMOGRAPHICS
    # ========================================================

    elif page == "Demographics":

        capture_and_store_page(
            "Demographics",
            render_demographics,
            filtered_df,
        )

        if not capture_active:

            st.divider()

            render_page_pdf_button(
                "Demographics",
                filtered_df,
            )


    # ========================================================
    # WARD ANALYSIS
    # ========================================================

    elif page == "Ward Analysis":

        capture_and_store_page(
            "Ward Analysis",
            render_ward,
            filtered_df,
        )

        if not capture_active:

            st.divider()

            render_page_pdf_button(
                "Ward Analysis",
                filtered_df,
            )


    # ========================================================
    # MAP
    # ========================================================

    elif page == "Map":

        capture_and_store_page(
            "Map",
            render_map,
            filtered_df,
        )

        if not capture_active:

            st.divider()

            render_page_pdf_button(
                "Map",
                filtered_df,
            )


    # ========================================================
    # GEOGRAPHIC MAP
    # ========================================================

    elif page == "Geographic Map":

        capture_and_store_page(
            "Geographic Map",
            render_geographic_map,
            filtered_df,
            df,
        )


    # ========================================================
    # DATA EXPLORER
    # ========================================================

    elif page == "Data Explorer":

        capture_and_store_page(
            "Data Explorer",
            render_explorer,
            filtered_df,
        )

        if not capture_active:

            st.divider()

            render_page_pdf_button(
                "Data Explorer",
                filtered_df,
            )


    # ========================================================
    # PREDICTION
    # ========================================================

    elif page == "Prediction":

        capture_and_store_page(
            "Prediction",
            render_prediction,
            filtered_df,
        )

        if not capture_active:

            st.divider()

            render_page_pdf_button(
                "Prediction",
                filtered_df,
            )


    # ========================================================
    # USER MANUAL
    # ========================================================

    elif page == "User Manual":

        capture_and_store_page(
            "User Manual",
            render_manual,
        )

        if not capture_active:

            st.divider()

            render_page_pdf_button(
                "User Manual",
                filtered_df,
            )


    # ========================================================
    # VALIDATION & KPI
    # ========================================================

    elif page == "Validation & KPI":

        capture_and_store_page(
            "Validation & KPI",
            render_validation_kpi,
            filtered_df,
        )

        if not capture_active:

            st.divider()

            render_page_pdf_button(
                "Validation & KPI",
                filtered_df,
            )


    # ========================================================
    # DRILL-DOWN & EXPORT
    # ========================================================

    elif page == "Drill-down & Export":

        capture_and_store_page(
            "Drill-down & Export",
            render_drilldown_export,
            filtered_df,
        )

        if not capture_active:

            st.divider()

            render_page_pdf_button(
                "Drill-down & Export",
                filtered_df,
            )


except Exception as e:

    st.error(
        "This dashboard section could not be loaded."
    )

    st.exception(
        e
    )


# ============================================================
# AUTOMATIC CAPTURE SEQUENCE CONTROLLER
# ============================================================

if is_complete_pdf_capture_active():

    capture_queue = (
        st.session_state.get(
            CAPTURE_QUEUE_KEY,
            [],
        )
    )

    current_capture_page = (
        st.session_state.get(
            CAPTURE_CURRENT_PAGE_KEY
        )
    )

    if (
        capture_queue
        and current_capture_page
        == capture_queue[0]
    ):

        remaining_queue = (
            capture_queue[1:]
        )

        st.session_state[
            CAPTURE_QUEUE_KEY
        ] = remaining_queue

        if remaining_queue:

            next_page = (
                remaining_queue[0]
            )

            st.session_state[
                CAPTURE_CURRENT_PAGE_KEY
            ] = next_page

            st.rerun()

        else:

            try:

                with st.spinner(
                    "Building Complete Dashboard PDF..."
                ):

                    pdf_bytes = (
                        create_complete_dashboard_pdf()
                    )

                    st.session_state[
                        "complete_dashboard_pdf"
                    ] = pdf_bytes

                    st.session_state[
                        "complete_dashboard_pdf_filter"
                    ] = (
                        st.session_state.get(
                            CAPTURE_FILTER_SUMMARY_KEY,
                            get_filter_summary(),
                        )
                    )

                finish_complete_pdf_capture()

                st.rerun()

            except Exception as e:

                finish_complete_pdf_capture()

                st.error(
                    "Complete dashboard PDF "
                    "could not be generated."
                )

                st.exception(
                    e
                )


# ============================================================
# GOOGLE SHEET REFRESH
# ============================================================

if not is_complete_pdf_capture_active():

    st.sidebar.markdown(
        "---"
    )

    if st.sidebar.button(
        "🔄 Refresh Google Sheet Data",
        use_container_width=True,
    ):

        with st.spinner(
            "Refreshing Google Sheet data..."
        ):

            from phase1_data import (
                refresh_data,
            )

            refresh_data()

        try:

            get_data.clear()

        except Exception:

            pass

        st.success(
            "Google Sheet data refreshed successfully."
        )

        st.rerun()


# ============================================================
# FOOTER
# ============================================================

if not capture_active:

    st.markdown(
        """
        <div class="dashboard-footer">
            MSU Mumbai Public Health Surveillance Dashboard |
            Surveillance • Monitoring • Analysis • Management
        </div>
        """,
        unsafe_allow_html=True,
    )
