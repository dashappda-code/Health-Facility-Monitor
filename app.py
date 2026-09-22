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
from phase4_demographics import render_demographics
from phase5_ward import render_ward

# Existing patient/location hotspot map
from phase6_map import render_map

# New Mumbai ward geographic map
from geographic_map import render_geographic_map

from phase7_explorer import render_explorer
from phase8_prediction import render_prediction
from phase9_manual import render_manual
from phase10_validation_kpi import render_validation_kpi
from phase11_drilldown_export import render_drilldown_export

from pdf_report import (
    generate_pdf_report,
    generate_complete_dashboard_pdf,
)

from ppt_report import generate_ppt_report


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

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DASHBOARD HEADER
# ============================================================

st.title(
    "🏥 MSU Mumbai Public Health Surveillance Dashboard"
)

st.caption(
    "Surveillance • Monitoring • Analysis • Management"
)


# ============================================================
# DATA LOADING
# ============================================================

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
# SIDEBAR
# ============================================================

st.sidebar.title(
    "📌 Dashboard Menu"
)


page = st.sidebar.radio(
    "Select Section",
    [
        "Overview",
        "Charts & Trends",
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
)


# ============================================================
# SIDEBAR RECORD COUNT
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    f"Records loaded: {len(df):,}"
)


# ============================================================
# GLOBAL CHART CONTROL
# ============================================================

st.sidebar.markdown("---")

st.sidebar.subheader(
    "📊 Chart Display Controls"
)


show_data_labels = st.sidebar.checkbox(
    "🏷️ Show Data Labels",
    value=st.session_state.get(
        "show_data_labels",
        False,
    ),
    key="show_data_labels",
    help=(
        "Turn ON to display values directly "
        "on dashboard charts."
    ),
)


if show_data_labels:

    st.sidebar.success(
        "Data Labels: ON"
    )

else:

    st.sidebar.info(
        "Data Labels: OFF"
    )


# ============================================================
# GLOBAL FILTER PANEL
# ============================================================

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

    filter_values = create_filters(df)


# ============================================================
# APPLY GLOBAL FILTERS
# ============================================================

filtered_df = apply_filters(
    df=df,
    **filter_values,
)


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

c1, c2, c3, c4 = st.columns(4)


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

    for key, label in labels.items():

        values = filter_values.get(
            key,
            [],
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

    reporting_date = filter_values.get(
        "reporting_date"
    )

    if reporting_date:

        try:

            start_date, end_date = reporting_date

            if start_date and end_date:

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

    return " | ".join(selected)


# ============================================================
# REPORTING PERIOD
# ============================================================

def get_reporting_period(data):

    if (
        data is None
        or data.empty
        or "Reporting Date" not in data.columns
    ):

        return None

    dates = data[
        "Reporting Date"
    ].dropna()

    if dates.empty:

        return None

    try:

        start_date = dates.min().strftime(
            "%d-%m-%Y"
        )

        end_date = dates.max().strftime(
            "%d-%m-%Y"
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
        or column not in data.columns
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
        .rename_axis(output_name)
        .reset_index(
            name="Records"
        )
    )


# ============================================================
# BUILD PAGE REPORT DATA
# ============================================================

def build_page_report_data(
    page_name,
    data,
):

    tables = []
    charts = []

    if data is None or data.empty:

        return tables, charts


    # --------------------------------------------------------
    # DISEASE
    # --------------------------------------------------------

    disease_table = make_frequency_table(
        data,
        "Disease",
        "Disease",
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


    # --------------------------------------------------------
    # FACILITY
    # --------------------------------------------------------

    facility_table = make_frequency_table(
        data,
        "Facility Name",
        "Facility",
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


    # --------------------------------------------------------
    # WARD
    # --------------------------------------------------------

    ward_table = make_frequency_table(
        data,
        "Ward Name",
        "Ward",
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


    # --------------------------------------------------------
    # GENDER
    # --------------------------------------------------------

    gender_table = make_frequency_table(
        data,
        "Gender",
        "Gender",
    )

    if gender_table is not None:

        tables.append(
            (
                "Gender-wise Distribution",
                gender_table,
            )
        )


    # --------------------------------------------------------
    # AGE
    # --------------------------------------------------------

    age_table = make_frequency_table(
        data,
        "Age Group",
        "Age Group",
    )

    if age_table is not None:

        tables.append(
            (
                "Age Group-wise Distribution",
                age_table,
            )
        )


    # --------------------------------------------------------
    # OPD / IPD
    # --------------------------------------------------------

    opd_table = make_frequency_table(
        data,
        "OPD/IPD",
        "OPD/IPD",
    )

    if opd_table is not None:

        tables.append(
            (
                "OPD / IPD Distribution",
                opd_table,
            )
        )


    # --------------------------------------------------------
    # MONTH-WISE ANALYSIS
    # --------------------------------------------------------

    if (
        "Month" in data.columns
        and "Year" in data.columns
    ):

        monthly = (
            data
            .groupby(
                ["Year", "Month"],
                dropna=False,
            )
            .size()
            .reset_index(
                name="Records"
            )
        )

        if not monthly.empty:

            monthly["Period"] = (
                monthly["Year"]
                .astype(str)
                + " - "
                + monthly["Month"]
                .astype(str)
            )

            monthly = monthly[
                [
                    "Period",
                    "Records",
                ]
            ]

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
# PAGE PDF
# ============================================================

def create_page_pdf(
    page_name,
    data,
):

    tables, charts = build_page_report_data(
        page_name,
        data,
    )

    report_period = get_reporting_period(
        data
    )

    filter_summary = get_filter_summary()

    pdf_bytes = generate_pdf_report(
        report_title=page_name,
        df=data,
        kpis=kpis,
        tables=tables,
        charts=charts,
        report_period=report_period,
        filter_summary=filter_summary,
    )

    return pdf_bytes


# ============================================================
# PAGE PDF DOWNLOAD BUTTON
# ============================================================

def render_page_pdf_button(
    page_name,
    data,
):

    try:

        pdf_bytes = create_page_pdf(
            page_name,
            data,
        )

        safe_name = (
            page_name
            .replace("&", "and")
            .replace("/", "_")
            .replace("-", "_")
            .replace(" ", "_")
        )

        st.download_button(
            label="📄 Download This Page PDF",
            data=pdf_bytes,
            file_name=(
                f"{safe_name}_Report.pdf"
            ),
            mime="application/pdf",
            key=f"pdf_page_{safe_name}",
        )

    except Exception as e:

        st.error(
            "PDF report could not be generated."
        )

        st.exception(e)


# ============================================================
# COMPLETE DASHBOARD PDF
# ============================================================

def create_complete_dashboard_pdf():

    report_period = get_reporting_period(
        filtered_df
    )

    filter_summary = get_filter_summary()

    dashboard_pages = []

    page_names = [
        "Overview",
        "Charts & Trends",
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


    for page_name in page_names:

        page_tables, page_charts = build_page_report_data(
            page_name,
            filtered_df,
        )

        dashboard_pages.append(
            {
                "title": page_name,
                "df": filtered_df,
                "kpis": kpis,
                "tables": page_tables,
                "charts": page_charts,
            }
        )


    return generate_complete_dashboard_pdf(
        pages=dashboard_pages,
        report_period=report_period,
        filter_summary=filter_summary,
    )


# ============================================================
# COMPLETE DASHBOARD POWERPOINT
# ============================================================

def create_complete_dashboard_ppt():

    report_period = get_reporting_period(
        filtered_df
    )

    filter_summary = get_filter_summary()

    ppt_bytes = generate_ppt_report(
        df=filtered_df,
        report_period=report_period,
        filter_summary=filter_summary,
    )

    return ppt_bytes


# ============================================================
# SIDEBAR PDF SECTION
# ============================================================

st.sidebar.markdown("---")

st.sidebar.subheader(
    "📄 PDF Reports"
)

st.sidebar.caption(
    "Download the current dashboard view as "
    "a complete consolidated PDF."
)


# ============================================================
# GENERATE COMPLETE PDF
# ============================================================

if st.sidebar.button(
    "📚 Generate Complete Dashboard PDF",
    use_container_width=True,
):

    try:

        with st.spinner(
            "Generating complete dashboard PDF..."
        ):

            st.session_state[
                "complete_dashboard_pdf"
            ] = create_complete_dashboard_pdf()

            st.session_state[
                "complete_dashboard_pdf_filter"
            ] = get_filter_summary()


        st.sidebar.success(
            "Complete PDF generated."
        )


    except Exception as e:

        st.sidebar.error(
            "Complete dashboard PDF could not be generated."
        )

        st.sidebar.exception(e)


# ============================================================
# COMPLETE PDF DOWNLOAD
# ============================================================

if (
    "complete_dashboard_pdf"
    in st.session_state
):

    current_filter = get_filter_summary()

    generated_filter = st.session_state.get(
        "complete_dashboard_pdf_filter",
        "",
    )


    if current_filter == generated_filter:

        st.sidebar.download_button(
            label="⬇️ Download Complete Dashboard PDF",
            data=st.session_state[
                "complete_dashboard_pdf"
            ],
            file_name=(
                "MSU_Mumbai_Complete_Dashboard_Report.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
            key="download_complete_dashboard_pdf",
        )

    else:

        st.sidebar.info(
            "Dashboard filters have changed. "
            "Generate the complete PDF again."
        )


# ============================================================
# SIDEBAR POWERPOINT SECTION
# ============================================================

st.sidebar.markdown("---")

st.sidebar.subheader(
    "📊 PowerPoint Report"
)

st.sidebar.caption(
    "Generate a management presentation from "
    "the currently selected dashboard filters."
)


# ============================================================
# GENERATE POWERPOINT
# ============================================================

if st.sidebar.button(
    "📊 Generate PowerPoint",
    use_container_width=True,
):

    try:

        with st.spinner(
            "Generating PowerPoint report..."
        ):

            st.session_state[
                "complete_dashboard_ppt"
            ] = create_complete_dashboard_ppt()

            st.session_state[
                "complete_dashboard_ppt_filter"
            ] = get_filter_summary()


        st.sidebar.success(
            "PowerPoint generated successfully."
        )


    except Exception as e:

        st.sidebar.error(
            "PowerPoint report could not be generated."
        )

        st.sidebar.exception(e)


# ============================================================
# POWERPOINT DOWNLOAD
# ============================================================

if (
    "complete_dashboard_ppt"
    in st.session_state
):

    current_filter = get_filter_summary()

    generated_ppt_filter = st.session_state.get(
        "complete_dashboard_ppt_filter",
        "",
    )


    if current_filter == generated_ppt_filter:

        st.sidebar.download_button(
            label="⬇️ Download PowerPoint",
            data=st.session_state[
                "complete_dashboard_ppt"
            ],
            file_name=(
                "MSU_Mumbai_Dashboard_Management_Report.pptx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            use_container_width=True,
            key="download_complete_dashboard_ppt",
        )

    else:

        st.sidebar.info(
            "Dashboard filters have changed. "
            "Generate the PowerPoint again."
        )


# ============================================================
# PAGE RENDERING
# ============================================================

try:


    # ========================================================
    # OVERVIEW
    # ========================================================

    if page == "Overview":

        render_overview(
            filtered_df
        )

        st.divider()

        render_page_pdf_button(
            "Overview",
            filtered_df,
        )


    # ========================================================
    # CHARTS & TRENDS
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
    # DEMOGRAPHICS
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
    # WARD ANALYSIS
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
    # EXISTING MAP
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
    # NEW GEOGRAPHIC MAP
    # ========================================================

    elif page == "Geographic Map":

        render_geographic_map(
            filtered_df
        )


    # ========================================================
    # DATA EXPLORER
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
    # PREDICTION
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
    # USER MANUAL
    # ========================================================

    elif page == "User Manual":

        render_manual()

        st.divider()

        render_page_pdf_button(
            "User Manual",
            filtered_df,
        )


    # ========================================================
    # VALIDATION & KPI
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
    # DRILL-DOWN & EXPORT
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


except Exception as e:

    st.error(
        "This dashboard section could not be loaded."
    )

    st.exception(e)


# ============================================================
# GOOGLE SHEET REFRESH
# ============================================================

st.sidebar.markdown("---")


if st.sidebar.button(
    "🔄 Refresh Google Sheet Data",
    use_container_width=True,
):

    with st.spinner(
        "Refreshing Google Sheet data..."
    ):

        from phase1_data import refresh_data

        refresh_data()


    st.success(
        "Google Sheet data refreshed successfully."
    )

    st.rerun()


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="dashboard-footer">
        MSU Mumbai Public Health Surveillance Dashboard |
        Surveillance • Monitoring • Analysis • Management
    </div>
    """,
    unsafe_allow_html=True,
)
