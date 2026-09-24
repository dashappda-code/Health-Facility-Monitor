from io import BytesIO
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)


# ============================================================
# CONFIGURATION
# ============================================================

DASHBOARD_TITLE = "MSU Mumbai Public Health Surveillance Dashboard"
DASHBOARD_SUBTITLE = "Surveillance - Monitoring - Analysis - Management"

TABLE_ROWS_PER_BLOCK = 35
MAX_CHART_CATEGORIES = 20


# ============================================================
# BASIC HELPERS
# ============================================================

def _safe_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value)


def _format_number(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return _safe_text(value)


def _clean_series(df, column):
    if df is None or df.empty:
        return pd.Series(dtype="object")

    if column not in df.columns:
        return pd.Series(dtype="object")

    series = df[column].copy()

    series = series.dropna()

    series = series.astype(str).str.strip()

    series = series[
        (series != "")
        & (series.str.lower() != "nan")
        & (series.str.lower() != "none")
    ]

    return series


def _find_column(df, candidates):
    if df is None or df.empty:
        return None

    lookup = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower()

        if key in lookup:
            return lookup[key]

    return None


# ============================================================
# STYLES
# ============================================================

def _styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitleCustom",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSubtitleCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.grey,
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionCustom",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ManagementCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            spaceAfter=6,
        )
    )

    return styles


# ============================================================
# HEADER / FOOTER
# ============================================================

def _header_footer(canvas, doc):
    canvas.saveState()

    width, height = A4

    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(
        15 * mm,
        10 * mm,
        DASHBOARD_TITLE,
    )

    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(
        width - 15 * mm,
        10 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# TABLE CREATION
# ============================================================

def _make_table(dataframe):
    if dataframe is None or dataframe.empty:
        return None

    df = dataframe.copy()

    headers = [
        _safe_text(column)
        for column in df.columns
    ]

    rows = [headers]

    for _, row in df.iterrows():
        rows.append(
            [
                _safe_text(value)
                for value in row.tolist()
            ]
        )

    table = Table(
        rows,
        repeatRows=1,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1f4e78"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    6.5,
                ),
                (
                    "LEADING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#f3f6f9"),
                    ],
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    return table


def _add_dataframe_section(
    story,
    styles,
    title,
    dataframe,
):
    if dataframe is None or dataframe.empty:
        return

    story.append(
        Paragraph(
            _safe_text(title),
            styles["SectionCustom"],
        )
    )

    df = dataframe.copy()

    total_rows = len(df)

    for start in range(
        0,
        total_rows,
        TABLE_ROWS_PER_BLOCK,
    ):
        block = df.iloc[
            start:start + TABLE_ROWS_PER_BLOCK
        ]

        table = _make_table(block)

        if table is not None:
            story.append(table)
            story.append(Spacer(1, 6))

        if (
            start + TABLE_ROWS_PER_BLOCK
            < total_rows
        ):
            story.append(PageBreak())

            story.append(
                Paragraph(
                    _safe_text(title)
                    + " - Continued",
                    styles["SectionCustom"],
                )
            )


# ============================================================
# KPI TABLE
# ============================================================

def _add_kpi_table(
    story,
    styles,
    kpis,
):
    if not kpis:
        return

    rows = []

    for key, value in kpis.items():

        label = (
            str(key)
            .replace("_", " ")
            .title()
        )

        if isinstance(
            value,
            (int, float),
        ):
            value = _format_number(value)

        rows.append(
            [
                label,
                _safe_text(value),
            ]
        )

    if not rows:
        return

    story.append(
        Paragraph(
            "Key Performance Indicators",
            styles["SectionCustom"],
        )
    )

    table = Table(
        rows,
        colWidths=[
            70 * mm,
            80 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#eaf1f7"),
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold",
                ),
                (
                    "FONTNAME",
                    (1, 0),
                    (1, -1),
                    "Helvetica",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 8))


# ============================================================
# CHART
# ============================================================

def _create_chart_image(
    dataframe,
    x_column,
    y_column,
    title,
):
    if dataframe is None or dataframe.empty:
        return None

    if x_column not in dataframe.columns:
        return None

    if y_column not in dataframe.columns:
        return None

    temp = dataframe[
        [x_column, y_column]
    ].copy()

    temp[y_column] = pd.to_numeric(
        temp[y_column],
        errors="coerce",
    )

    temp = temp.dropna(
        subset=[y_column]
    )

    if temp.empty:
        return None

    temp = temp.sort_values(
        y_column,
        ascending=False,
    )

    temp = temp.head(
        MAX_CHART_CATEGORIES
    )

    temp = temp.iloc[::-1]

    fig, ax = plt.subplots(
        figsize=(8, 4.2),
    )

    ax.barh(
        temp[x_column].astype(str),
        temp[y_column],
    )

    ax.set_title(
        _safe_text(title),
        fontsize=10,
    )

    ax.tick_params(
        axis="x",
        labelsize=7,
    )

    ax.tick_params(
        axis="y",
        labelsize=7,
    )

    ax.grid(
        axis="x",
        alpha=0.2,
    )

    fig.tight_layout()

    image_buffer = BytesIO()

    fig.savefig(
        image_buffer,
        format="png",
        dpi=150,
        bbox_inches="tight",
    )

    plt.close(fig)

    image_buffer.seek(0)

    return Image(
        image_buffer,
        width=175 * mm,
        height=85 * mm,
    )


# ============================================================
# AUTOMATIC ANALYSIS
# ============================================================

def _frequency_table(
    df,
    column,
    label,
    sort_desc=True,
):
    if column is None:
        return None

    series = _clean_series(
        df,
        column,
    )

    if series.empty:
        return None

    result = (
        series.value_counts()
        .reset_index()
    )

    result.columns = [
        label,
        "Records",
    ]

    if sort_desc:
        result = result.sort_values(
            "Records",
            ascending=False,
        )

    result.insert(
        0,
        "Rank",
        range(1, len(result) + 1),
    )

    return result


def _detect_pathogen_column(df):
    return _find_column(
        df,
        [
            "Test Performed Pathogen Name",
            "Pathogen Name",
            "Test Performed Pathogen",
            "Pathogen",
        ],
    )


def _build_monthly_table(df):
    date_column = _find_column(
        df,
        [
            "Reporting Date",
            "Report Date",
            "Date",
        ],
    )

    if date_column is not None:

        dates = pd.to_datetime(
            df[date_column],
            errors="coerce",
        )

        temp = pd.DataFrame(
            {
                "Date": dates,
            }
        ).dropna()

        if not temp.empty:

            result = (
                temp.assign(
                    Year=temp["Date"].dt.year,
                    Month_Number=temp["Date"].dt.month,
                    Month=temp["Date"].dt.strftime("%B"),
                )
                .groupby(
                    [
                        "Year",
                        "Month_Number",
                        "Month",
                    ],
                    as_index=False,
                )
                .size()
                .rename(
                    columns={
                        "size": "Records"
                    }
                )
            )

            result = result.sort_values(
                [
                    "Year",
                    "Month_Number",
                ]
            )

            result.insert(
                0,
                "Rank",
                range(1, len(result) + 1),
            )

            return result[
                [
                    "Rank",
                    "Year",
                    "Month",
                    "Records",
                ]
            ]

    month_column = _find_column(
        df,
        [
            "Month",
            "Reporting Month",
        ],
    )

    if month_column is None:
        return None

    result = _frequency_table(
        df,
        month_column,
        "Month",
    )

    return result


def _build_management_tables(df):
    tables = []

    if df is None or df.empty:
        return tables

    disease_column = _find_column(
        df,
        [
            "Disease",
            "Disease Name",
            "Diagnosis",
            "Disease_Name",
        ],
    )

    facility_column = _find_column(
        df,
        [
            "Facility",
            "Facility Name",
            "Health Facility",
            "Institution",
        ],
    )

    ward_column = _find_column(
        df,
        [
            "Ward",
            "Ward Name",
            "BMC Ward",
        ],
    )

    gender_column = _find_column(
        df,
        [
            "Gender",
            "Sex",
        ],
    )

    age_column = _find_column(
        df,
        [
            "Age Group",
            "Age group",
            "Age_Group",
            "Age",
        ],
    )

    opd_ipd_column = _find_column(
        df,
        [
            "OPD/IPD",
            "OPD IPD",
            "OPD_IPD",
            "Patient Type",
        ],
    )

    pathogen_column = _detect_pathogen_column(df)

    disease_table = _frequency_table(
        df,
        disease_column,
        "Disease",
    )

    if disease_table is not None:
        tables.append(
            (
                "Disease-wise Burden",
                disease_table,
            )
        )

    pathogen_table = _frequency_table(
        df,
        pathogen_column,
        "Test Performed Pathogen Name",
    )

    if pathogen_table is not None:
        tables.append(
            (
                "Test Performed / Pathogen Name-wise Analysis",
                pathogen_table,
            )
        )

    facility_table = _frequency_table(
        df,
        facility_column,
        "Facility",
    )

    if facility_table is not None:
        tables.append(
            (
                "Facility-wise Burden",
                facility_table,
            )
        )

    ward_table = _frequency_table(
        df,
        ward_column,
        "Ward",
    )

    if ward_table is not None:
        tables.append(
            (
                "Ward-wise Burden",
                ward_table,
            )
        )

    gender_table = _frequency_table(
        df,
        gender_column,
        "Gender",
    )

    if gender_table is not None:
        tables.append(
            (
                "Gender-wise Distribution",
                gender_table,
            )
        )

    age_table = _frequency_table(
        df,
        age_column,
        "Age Group",
    )

    if age_table is not None:
        tables.append(
            (
                "Age-wise Distribution",
                age_table,
            )
        )

    opd_ipd_table = _frequency_table(
        df,
        opd_ipd_column,
        "OPD/IPD",
    )

    if opd_ipd_table is not None:
        tables.append(
            (
                "OPD/IPD Distribution",
                opd_ipd_table,
            )
        )

    monthly_table = _build_monthly_table(df)

    if monthly_table is not None:
        tables.append(
            (
                "Month-wise Programme Trend",
                monthly_table,
            )
        )

    date_column = _find_column(
        df,
        [
            "Reporting Date",
            "Report Date",
            "Date",
        ],
    )

    if date_column is not None:

        dates = pd.to_datetime(
            df[date_column],
            errors="coerce",
        )

        daily = (
            dates.dropna()
            .dt.date
            .value_counts()
            .sort_index()
            .reset_index()
        )

        if not daily.empty:
            daily.columns = [
                "Reporting Date",
                "Records",
            ]

            tables.append(
                (
                    "Reporting Date-wise Trend",
                    daily,
                )
            )

    return tables


def _build_management_charts(df):
    charts = []

    if df is None or df.empty:
        return charts

    candidates = [
        (
            [
                "Disease",
                "Disease Name",
                "Diagnosis",
                "Disease_Name",
            ],
            "Disease",
            "Disease-wise Burden",
        ),
        (
            [
                "Facility",
                "Facility Name",
                "Health Facility",
                "Institution",
            ],
            "Facility",
            "Facility-wise Burden",
        ),
        (
            [
                "Ward",
                "Ward Name",
                "BMC Ward",
            ],
            "Ward",
            "Ward-wise Burden",
        ),
        (
            [
                "Gender",
                "Sex",
            ],
            "Gender",
            "Gender-wise Distribution",
        ),
        (
            [
                "Age Group",
                "Age group",
                "Age_Group",
                "Age",
            ],
            "Age Group",
            "Age-wise Distribution",
        ),
        (
            [
                "OPD/IPD",
                "OPD IPD",
                "OPD_IPD",
                "Patient Type",
            ],
            "OPD/IPD",
            "OPD/IPD Distribution",
        ),
    ]

    for candidates_list, label, title in candidates:

        column = _find_column(
            df,
            candidates_list,
        )

        if column is None:
            continue

        table = _frequency_table(
            df,
            column,
            label,
        )

        if table is None:
            continue

        charts.append(
            {
                "dataframe": table,
                "x_column": label,
                "y_column": "Records",
                "title": title,
            }
        )

    pathogen_column = _detect_pathogen_column(df)

    if pathogen_column is not None:

        table = _frequency_table(
            df,
            pathogen_column,
            "Test Performed Pathogen Name",
        )

        if table is not None:
            charts.append(
                {
                    "dataframe": table,
                    "x_column": "Test Performed Pathogen Name",
                    "y_column": "Records",
                    "title": (
                        "Test Performed / "
                        "Pathogen Name-wise Analysis"
                    ),
                }
            )

    return charts


# ============================================================
# REPORT HEADER
# ============================================================

def _add_report_header(
    story,
    styles,
    report_title,
    report_period=None,
    filter_summary=None,
    record_count=None,
):
    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["ReportTitleCustom"],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["ReportSubtitleCustom"],
        )
    )

    story.append(
        Paragraph(
            _safe_text(report_title),
            styles["Heading1"],
        )
    )

    story.append(
        Spacer(1, 5)
    )

    story.append(
        Paragraph(
            "Report generated on: "
            + datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            ),
            styles["SmallCustom"],
        )
    )

    if report_period:
        story.append(
            Paragraph(
                "Reporting Period: "
                + _safe_text(report_period),
                styles["SmallCustom"],
            )
        )

    if filter_summary:
        story.append(
            Paragraph(
                "Filter Scope: "
                + _safe_text(filter_summary),
                styles["SmallCustom"],
            )
        )

    if record_count is not None:
        story.append(
            Paragraph(
                "Records in current scope: "
                + _format_number(record_count),
                styles["SmallCustom"],
            )
        )

    story.append(
        Spacer(1, 8)
    )


# ============================================================
# SUPPLIED OUTPUTS
# ============================================================

def _render_charts(
    story,
    styles,
    charts,
):
    if not charts:
        return

    for chart in charts:

        if not isinstance(
            chart,
            dict,
        ):
            continue

        chart_image = _create_chart_image(
            chart.get("dataframe"),
            chart.get("x_column"),
            chart.get("y_column"),
            chart.get("title", ""),
        )

        if chart_image is None:
            continue

        story.append(
            Paragraph(
                _safe_text(
                    chart.get(
                        "title",
                        "Chart",
                    )
                ),
                styles["SectionCustom"],
            )
        )

        story.append(chart_image)

        story.append(
            Spacer(1, 6)
        )


def _render_tables(
    story,
    styles,
    tables,
):
    if not tables:
        return

    for item in tables:

        if not isinstance(
            item,
            (list, tuple),
        ):
            continue

        if len(item) < 2:
            continue

        title = item[0]
        dataframe = item[1]

        _add_dataframe_section(
            story,
            styles,
            title,
            dataframe,
        )


# ============================================================
# SINGLE PAGE PDF
# ============================================================

def generate_pdf_report(
    report_title,
    df=None,
    kpis=None,
    tables=None,
    charts=None,
    report_period=None,
    filter_summary=None,
):
    """
    Generate a PDF report for one dashboard page.

    Existing app.py interface is preserved.
    """

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=17 * mm,
        title=_safe_text(report_title),
        author=DASHBOARD_TITLE,
    )

    styles = _styles()
    story = []

    record_count = (
        len(df)
        if df is not None
        else None
    )

    _add_report_header(
        story,
        styles,
        report_title,
        report_period,
        filter_summary,
        record_count,
    )

    _add_kpi_table(
        story,
        styles,
        kpis,
    )

    # --------------------------------------------------------
    # Use supplied dashboard outputs first.
    # If they are not supplied, create management outputs
    # automatically from the current dataframe.
    # --------------------------------------------------------

    if charts:
        final_charts = charts
    else:
        final_charts = _build_management_charts(df)

    if tables:
        final_tables = tables
    else:
        final_tables = _build_management_tables(df)

    _render_charts(
        story,
        styles,
        final_charts,
    )

    _render_tables(
        story,
        styles,
        final_tables,
    )

    if df is not None and not df.empty:

        story.append(
            Paragraph(
                "Report Scope",
                styles["SectionCustom"],
            )
        )

        story.append(
            Paragraph(
                "This report represents the records "
                "available under the currently selected "
                "dashboard filters at the time of report "
                "generation.",
                styles["ManagementCustom"],
            )
        )

    story.append(
        Spacer(1, 12)
    )

    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["SmallCustom"],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["SmallCustom"],
        )
    )

    document.build(
        story,
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# COMPLETE DASHBOARD PDF
# ============================================================

def generate_complete_dashboard_pdf(
    pages,
    report_period=None,
    filter_summary=None,
):
    """
    Generate one consolidated PDF containing
    all dashboard page reports.

    Existing app.py interface is preserved.
    """

    buffer = BytesIO()

    pages = pages or []

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=17 * mm,
        title=(
            "Complete Dashboard Report - "
            + DASHBOARD_TITLE
        ),
        author=DASHBOARD_TITLE,
    )

    styles = _styles()
    story = []

    # ========================================================
    # COVER PAGE
    # ========================================================

    story.append(
        Spacer(1, 25 * mm)
    )

    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["ReportTitleCustom"],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["ReportSubtitleCustom"],
        )
    )

    story.append(
        Spacer(1, 12)
    )

    story.append(
        Paragraph(
            "Complete Dashboard Management Report",
            styles["Heading1"],
        )
    )

    story.append(
        Spacer(1, 8)
    )

    story.append(
        Paragraph(
            "Report generated on: "
            + datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            ),
            styles["SmallCustom"],
        )
    )

    if report_period:
        story.append(
            Paragraph(
                "Reporting Period: "
                + _safe_text(report_period),
                styles["SmallCustom"],
            )
        )

    if filter_summary:
        story.append(
            Paragraph(
                "Global Filter Scope: "
                + _safe_text(filter_summary),
                styles["SmallCustom"],
            )
        )

    story.append(
        Spacer(1, 15)
    )

    story.append(
        Paragraph(
            "This consolidated report contains the "
            "available management outputs from all "
            "dashboard sections under the current "
            "Global Dashboard Control.",
            styles["ManagementCustom"],
        )
    )

    story.append(
        Spacer(1, 8)
    )

    # ========================================================
    # CONTENTS
    # ========================================================

    story.append(
        Paragraph(
            "Dashboard Sections Included",
            styles["SectionCustom"],
        )
    )

    page_names = []

    for index, page in enumerate(
        pages,
        start=1,
    ):
        title = page.get(
            "title",
            "Dashboard Section",
        )

        page_names.append(
            [
                str(index),
                _safe_text(title),
            ]
        )

    if page_names:

        contents_table = Table(
            [
                [
                    "No.",
                    "Dashboard Section",
                ]
            ]
            + page_names,
            colWidths=[
                20 * mm,
                130 * mm,
            ],
            repeatRows=1,
        )

        contents_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#1f4e78"),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.white,
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold",
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.3,
                        colors.grey,
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor("#f3f6f9"),
                        ],
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        story.append(
            contents_table
        )

    # ========================================================
    # EACH DASHBOARD PAGE
    # ========================================================

    for page_index, page in enumerate(
        pages,
        start=1,
    ):
        title = page.get(
            "title",
            f"Dashboard Section {page_index}",
        )

        df = page.get("df")
        kpis = page.get("kpis")
        tables = page.get("tables")
        charts = page.get("charts")

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                DASHBOARD_TITLE,
                styles["ReportTitleCustom"],
            )
        )

        story.append(
            Paragraph(
                DASHBOARD_SUBTITLE,
                styles["ReportSubtitleCustom"],
            )
        )

        story.append(
            Paragraph(
                _safe_text(title),
                styles["Heading1"],
            )
        )

        story.append(
            Spacer(1, 5)
        )

        story.append(
            Paragraph(
                "Section "
                + str(page_index)
                + " of "
                + str(len(pages)),
                styles["SmallCustom"],
            )
        )

        if report_period:
            story.append(
                Paragraph(
                    "Reporting Period: "
                    + _safe_text(report_period),
                    styles["SmallCustom"],
                )
            )

        if filter_summary:
            story.append(
                Paragraph(
                    "Filter Scope: "
                    + _safe_text(filter_summary),
                    styles["SmallCustom"],
                )
            )

        if df is not None:
            story.append(
                Paragraph(
                    "Records in current scope: "
                    + _format_number(len(df)),
                    styles["SmallCustom"],
                )
            )

        story.append(
            Spacer(1, 8)
        )

        _add_kpi_table(
            story,
            styles,
            kpis,
        )

        if charts:
            final_charts = charts
        else:
            final_charts = _build_management_charts(
                df
            )

        if tables:
            final_tables = tables
        else:
            final_tables = _build_management_tables(
                df
            )

        _render_charts(
            story,
            styles,
            final_charts,
        )

        _render_tables(
            story,
            styles,
            final_tables,
        )

        if df is not None and not df.empty:

            story.append(
                Paragraph(
                    "Management Scope",
                    styles["SectionCustom"],
                )
            )

            story.append(
                Paragraph(
                    "The above outputs represent the "
                    "records available under the Global "
                    "Dashboard Control filters active at "
                    "the time of report generation.",
                    styles["ManagementCustom"],
                )
            )

    # ========================================================
    # FINAL NOTE
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        Spacer(1, 25 * mm)
    )

    story.append(
        Paragraph(
            "Report Completion Note",
            styles["SectionCustom"],
        )
    )

    story.append(
        Paragraph(
            "This consolidated PDF is intended for "
            "programme monitoring, management review, "
            "data interpretation and official reporting. "
            "The report reflects the dashboard data "
            "available at the time of generation.",
            styles["ManagementCustom"],
        )
    )

    story.append(
        Spacer(1, 10)
    )

    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["SmallCustom"],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["SmallCustom"],
        )
    )

    document.build(
        story,
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )

    buffer.seek(0)

    return buffer.getvalue()
    
