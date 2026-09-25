```python
from io import BytesIO
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
    KeepTogether,
)


# ============================================================
# DASHBOARD BRANDING
# ============================================================

DASHBOARD_TITLE = (
    "MSU Mumbai Public Health Surveillance Dashboard"
)

DASHBOARD_SUBTITLE = (
    "Surveillance • Monitoring • Analysis • Management"
)


# ============================================================
# GENERAL HELPERS
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
            spaceBefore=6,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionPageTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            spaceBefore=3,
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

    styles.add(
        ParagraphStyle(
            name="TableTitleCustom",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            spaceBefore=4,
            spaceAfter=4,
        )
    )

    return styles


# ============================================================
# HEADER / FOOTER
# ============================================================

def _header_footer(canvas, doc):
    canvas.saveState()

    width, height = A4

    canvas.setFont(
        "Helvetica-Bold",
        7.5,
    )

    canvas.drawString(
        15 * mm,
        10 * mm,
        DASHBOARD_TITLE,
    )

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.drawRightString(
        width - 15 * mm,
        10 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# TABLE CREATION
# ============================================================

def _make_table(
    dataframe,
    max_rows=50,
):
    if dataframe is None or dataframe.empty:
        return None

    df = dataframe.copy().head(
        max_rows
    )

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

    available_width = (
        A4[0]
        - 30 * mm
    )

    column_count = max(
        len(headers),
        1,
    )

    col_width = (
        available_width
        / column_count
    )

    table = Table(
        rows,
        repeatRows=1,
        hAlign="LEFT",
        colWidths=[
            col_width
            for _ in headers
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#1f4e78"
                    ),
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
                        colors.HexColor(
                            "#f3f6f9"
                        ),
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
    max_rows=50,
):
    if (
        dataframe is None
        or dataframe.empty
    ):
        return

    story.append(
        Paragraph(
            _safe_text(title),
            styles["TableTitleCustom"],
        )
    )

    table = _make_table(
        dataframe,
        max_rows=max_rows,
    )

    if table is not None:
        story.append(table)
        story.append(
            Spacer(1, 7)
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
            value = _format_number(
                value
            )

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
                    colors.HexColor(
                        "#eaf1f7"
                    ),
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

    story.append(
        Spacer(1, 8)
    )


# ============================================================
# CHART IMAGE CREATION
# ============================================================

def _create_chart_image(
    dataframe,
    x_column,
    y_column,
    title,
):
    if (
        dataframe is None
        or dataframe.empty
    ):
        return None

    if (
        x_column not in dataframe.columns
        or y_column not in dataframe.columns
    ):
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

    # Keep report readable.
    temp = temp.head(20)

    x_values = (
        temp[x_column]
        .astype(str)
        .tolist()
    )

    y_values = (
        temp[y_column]
        .tolist()
    )

    # --------------------------------------------------------
    # Adaptive figure size
    # --------------------------------------------------------

    count = len(temp)

    if count <= 6:
        figsize = (9.0, 4.6)

    elif count <= 12:
        figsize = (9.5, 4.8)

    else:
        figsize = (10.0, 5.0)

    fig, ax = plt.subplots(
        figsize=figsize
    )

    ax.bar(
        x_values,
        y_values,
    )

    ax.set_title(
        _safe_text(title),
        fontsize=11,
        fontweight="bold",
        pad=10,
    )

    ax.tick_params(
        axis="x",
        labelrotation=45,
        labelsize=7,
    )

    ax.tick_params(
        axis="y",
        labelsize=7,
    )

    ax.grid(
        axis="y",
        alpha=0.2,
    )

    ax.set_axisbelow(True)

    fig.tight_layout()

    image_buffer = BytesIO()

    fig.savefig(
        image_buffer,
        format="png",
        dpi=170,
        bbox_inches="tight",
    )

    plt.close(fig)

    image_buffer.seek(0)

    # --------------------------------------------------------
    # Use almost full A4 content width
    # while retaining chart aspect ratio.
    # --------------------------------------------------------

    available_width = (
        A4[0]
        - 30 * mm
    )

    original_width = (
        figsize[0]
    )

    original_height = (
        figsize[1]
    )

    image_height = (
        available_width
        * original_height
        / original_width
    )

    # Prevent an excessively tall chart.
    image_height = min(
        image_height,
        92 * mm,
    )

    return Image(
        image_buffer,
        width=available_width,
        height=image_height,
    )


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
            styles["SectionPageTitle"],
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
                + _safe_text(
                    report_period
                ),
                styles["SmallCustom"],
            )
        )

    if filter_summary:

        story.append(
            Paragraph(
                "Filter Scope: "
                + _safe_text(
                    filter_summary
                ),
                styles["SmallCustom"],
            )
        )

    if record_count is not None:

        story.append(
            Paragraph(
                "Records in current scope: "
                + _format_number(
                    record_count
                ),
                styles["SmallCustom"],
            )
        )

    story.append(
        Spacer(1, 8)
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
    """

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=17 * mm,
        title=report_title,
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
    # CHARTS
    # --------------------------------------------------------

    if charts:

        for chart_index, chart in enumerate(
            charts,
            start=1,
        ):

            chart_title = chart.get(
                "title",
                f"Chart {chart_index}",
            )

            chart_image = _create_chart_image(
                chart.get(
                    "dataframe"
                ),
                chart.get(
                    "x_column"
                ),
                chart.get(
                    "y_column"
                ),
                chart_title,
            )

            if chart_image:

                story.append(
                    Paragraph(
                        _safe_text(
                            chart_title
                        ),
                        styles["SectionCustom"],
                    )
                )

                story.append(
                    chart_image
                )

                story.append(
                    Spacer(1, 8)
                )

    # --------------------------------------------------------
    # TABLES
    # --------------------------------------------------------

    if tables:

        for title, dataframe in tables:

            _add_dataframe_section(
                story,
                styles,
                title,
                dataframe,
            )

    # --------------------------------------------------------
    # REPORT SCOPE
    # --------------------------------------------------------

    if (
        df is not None
        and not df.empty
    ):

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
                "dashboard filters.",
                styles["SmallCustom"],
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

    Each dashboard section starts on a new page.

    Expected page structure:

        {
            "title": "Overview",
            "df": dataframe,
            "kpis": {...},
            "tables": [...],
            "charts": [...],
        }
    """

    buffer = BytesIO()

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

    pages = pages or []

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
            styles["SectionPageTitle"],
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
                + _safe_text(
                    report_period
                ),
                styles["SmallCustom"],
            )
        )

    if filter_summary:

        story.append(
            Paragraph(
                "Global Filter Scope: "
                + _safe_text(
                    filter_summary
                ),
                styles["SmallCustom"],
            )
        )

    story.append(
        Spacer(1, 15)
    )

    story.append(
        Paragraph(
            "This consolidated report contains "
            "the available management outputs from "
            "the dashboard sections under the current "
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

    for page_index, page in enumerate(
        pages,
        start=1,
    ):

        title = page.get(
            "title",
            f"Dashboard Section {page_index}",
        )

        page_names.append(
            [
                str(page_index),
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
                        colors.HexColor(
                            "#1f4e78"
                        ),
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
                            colors.HexColor(
                                "#f3f6f9"
                            ),
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
    # EACH DASHBOARD SECTION
    # ========================================================

    for page_index, page in enumerate(
        pages,
        start=1,
    ):

        title = page.get(
            "title",
            f"Dashboard Section {page_index}",
        )

        df = page.get(
            "df"
        )

        kpis = page.get(
            "kpis"
        )

        tables = page.get(
            "tables"
        )

        charts = page.get(
            "charts"
        )

        # ----------------------------------------------------
        # New page for every dashboard section
        # ----------------------------------------------------

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
                styles["SectionPageTitle"],
            )
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
                    + _safe_text(
                        report_period
                    ),
                    styles["SmallCustom"],
                )
            )

        if filter_summary:

            story.append(
                Paragraph(
                    "Filter Scope: "
                    + _safe_text(
                        filter_summary
                    ),
                    styles["SmallCustom"],
                )
            )

        if df is not None:

            story.append(
                Paragraph(
                    "Records in current scope: "
                    + _format_number(
                        len(df)
                    ),
                    styles["SmallCustom"],
                )
            )

        story.append(
            Spacer(1, 8)
        )

        # ----------------------------------------------------
        # KPI
        # ----------------------------------------------------

        _add_kpi_table(
            story,
            styles,
            kpis,
        )

        # ----------------------------------------------------
        # CHARTS
        # ----------------------------------------------------

        if charts:

            for chart_index, chart in enumerate(
                charts,
                start=1,
            ):

                chart_title = chart.get(
                    "title",
                    f"Chart {chart_index}",
                )

                chart_image = _create_chart_image(
                    chart.get(
                        "dataframe"
                    ),
                    chart.get(
                        "x_column"
                    ),
                    chart.get(
                        "y_column"
                    ),
                    chart_title,
                )

                if chart_image:

                    story.append(
                        Paragraph(
                            _safe_text(
                                chart_title
                            ),
                            styles["SectionCustom"],
                        )
                    )

                    story.append(
                        chart_image
                    )

                    story.append(
                        Spacer(1, 7)
                    )

        # ----------------------------------------------------
        # DATA / TABLES
        # ----------------------------------------------------

        if tables:

            for table_title, dataframe in tables:

                _add_dataframe_section(
                    story,
                    styles,
                    table_title,
                    dataframe,
                )

        # ----------------------------------------------------
        # MANAGEMENT SCOPE
        # ----------------------------------------------------

        if (
            df is not None
            and not df.empty
        ):

            story.append(
                Paragraph(
                    "Management Scope",
                    styles["SectionCustom"],
                )
            )

            story.append(
                Paragraph(
                    "The above outputs represent "
                    "the records available under "
                    "the Global Dashboard Control "
                    "filters active at the time of "
                    "report generation.",
                    styles["ManagementCustom"],
                )
            )

    # ========================================================
    # FINAL PAGE
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
```
