import io
import html

import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

PDF_MARGIN_MM = 12

MAX_TABLE_ROWS = 300
MAX_TABLE_COLUMNS = 14

MIN_CHART_HEIGHT_MM = 55
MAX_CHART_HEIGHT_MM = 145

MONTHLY_DISEASE_HEIGHT_MM = 88


# ============================================================
# IMPORT EXISTING WORKING DISPLAYED-CHART ENGINE
# ============================================================

from displayed_chart_export import (
    _chart_to_png,
    _get_chart_image_size,
    _is_monthly_disease_comparison,
    _prepare_report_table,
    _format_table_value,
)


# ============================================================
# HELPERS
# ============================================================

def _safe_text(value):
    if value is None:
        return ""

    try:
        return html.escape(str(value))
    except Exception:
        return ""


def _get_section_name(item, index):
    section_name = item.get("section_name")

    if section_name:
        return str(section_name).strip()

    title = item.get("title")

    if title:
        return str(title).strip()

    return f"Section {index}"


def _get_chart_data(item):
    data = item.get("data")

    if isinstance(data, pd.DataFrame):
        return data

    if data is None:
        return pd.DataFrame()

    try:
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


# ============================================================
# TABLE BUILDER
# ============================================================

def _build_report_table(
    df,
    table_width,
):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )
    from reportlab.platypus import (
        Paragraph,
        Table,
        TableStyle,
    )

    if df is None or df.empty:
        return None

    table_df = _prepare_report_table(df)

    if table_df.empty:
        return None

    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        "DashboardPDFTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.8,
        leading=8,
        alignment=TA_LEFT,
    )

    body_style = ParagraphStyle(
        "DashboardPDFTableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
        alignment=TA_LEFT,
    )

    data = [
        [
            Paragraph(
                _safe_text(column),
                header_style,
            )
            for column in table_df.columns
        ]
    ]

    for _, row in table_df.iterrows():
        data.append(
            [
                Paragraph(
                    _safe_text(
                        _format_table_value(value)
                    ),
                    body_style,
                )
                for value in row.tolist()
            ]
        )

    number_of_columns = len(table_df.columns)

    if number_of_columns <= 0:
        return None

    column_width = table_width / number_of_columns

    table = Table(
        data,
        colWidths=[
            column_width
            for _ in range(number_of_columns)
        ],
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
                    colors.HexColor("#E9EEF5"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.black,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#B7B7B7"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
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
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAFC"),
                    ],
                ),
            ]
        )
    )

    return table


# ============================================================
# PDF STYLES
# ============================================================

def _get_pdf_styles():

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )

    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "DashboardPDFTitle",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "DashboardPDFSubtitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#666666"),
            spaceAfter=10,
        ),
        "section_number": ParagraphStyle(
            "DashboardPDFSectionNumber",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=3,
        ),
        "section_name": ParagraphStyle(
            "DashboardPDFSectionName",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#111827"),
            spaceAfter=7,
        ),
        "table_heading": ParagraphStyle(
            "DashboardPDFTableHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#374151"),
            spaceAfter=5,
        ),
        "filter": ParagraphStyle(
            "DashboardPDFFilter",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#555555"),
            spaceAfter=10,
        ),
        "footer": ParagraphStyle(
            "DashboardPDFFooter",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#777777"),
        ),
    }


# ============================================================
# FILTER SUMMARY
# ============================================================

def _add_filter_summary(
    story,
    filter_summary,
    style,
):

    from reportlab.platypus import Paragraph

    if not filter_summary:
        return

    if isinstance(filter_summary, dict):

        summary_parts = []

        for key, value in filter_summary.items():

            if value in (
                None,
                "",
                "All",
                "All records",
            ):
                continue

            summary_parts.append(
                f"<b>{_safe_text(key)}</b>: "
                f"{_safe_text(value)}"
            )

        if summary_parts:

            story.append(
                Paragraph(
                    "<br/>".join(summary_parts),
                    style,
                )
            )

    else:

        story.append(
            Paragraph(
                _safe_text(filter_summary),
                style,
            )
        )


# ============================================================
# PAGE HEADER
# ============================================================

def _add_report_header(
    story,
    report_title,
    report_period,
    filter_summary,
    styles,
):
    from reportlab.platypus import Spacer, Paragraph

    story.append(
        Spacer(
            1,
            8,
        )
    )

    story.append(
        Paragraph(
            _safe_text(report_title),
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "MSU Mumbai Public Health Surveillance Dashboard",
            styles["subtitle"],
        )
    )

    if report_period:

        story.append(
            Paragraph(
                f"<b>Reporting Period:</b> "
                f"{_safe_text(report_period)}",
                styles["filter"],
            )
        )

    _add_filter_summary(
        story,
        filter_summary,
        styles["filter"],
    )


# ============================================================
# CHART STORY ELEMENT
# ============================================================

def _add_chart_to_story(
    story,
    item,
    available_width,
    available_height,
):
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        Spacer,
    )

    png_bytes = _chart_to_png(item)

    if not png_bytes:
        return False

    chart_width, chart_height = (
        _get_chart_image_size(
            item,
            png_bytes,
            available_width,
            available_height,
        )
    )

    story.append(
        Image(
            io.BytesIO(png_bytes),
            width=chart_width,
            height=chart_height,
        )
    )

    story.append(
        Spacer(
            1,
            7,
        )
    )

    return True


# ============================================================
# COMPLETE DASHBOARD PDF
# ============================================================

def generate_captured_dashboard_pdf(
    pages,
    report_period=None,
    filter_summary=None,
):
    """
    Generate Complete Dashboard PDF using the SAME captured
    Altair chart objects and SAME chart-to-PNG engine used by
    displayed_chart_export.py.

    pages format:

    [
        {
            "title": "Charts & Trends",
            "charts": [
                {
                    "chart": altair_chart,
                    "data": dataframe,
                    "title": "...",
                    "section_name": "..."
                }
            ],
            "tables": [...]
        }
    ]
    """

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        PageBreak,
    )

    if pages is None:
        pages = []

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=PDF_MARGIN_MM * mm,
        leftMargin=PDF_MARGIN_MM * mm,
        topMargin=PDF_MARGIN_MM * mm,
        bottomMargin=PDF_MARGIN_MM * mm,
    )

    page_width, page_height = A4

    available_width = (
        page_width
        - (
            PDF_MARGIN_MM
            * 2
            * mm
        )
    )

    available_height = (
        page_height
        - (
            PDF_MARGIN_MM
            * 2
            * mm
        )
    )

    styles = _get_pdf_styles()

    story = []

    # ========================================================
    # COVER / REPORT HEADER
    # ========================================================

    _add_report_header(
        story=story,
        report_title=(
            "MSU Mumbai Public Health "
            "Surveillance Dashboard"
        ),
        report_period=report_period,
        filter_summary=filter_summary,
        styles=styles,
    )

    story.append(
        Spacer(
            1,
            8,
        )
    )

    story.append(
        Paragraph(
            "Complete Dashboard Report",
            styles["section_name"],
        )
    )

    story.append(
        Paragraph(
            "This report contains the captured dashboard "
            "charts and corresponding displayed data "
            "sections.",
            styles["filter"],
        )
    )

    # ========================================================
    # PAGE / SECTION COUNTER
    # ========================================================

    global_section_number = 0

    # ========================================================
    # PROCESS DASHBOARD PAGES
    # ========================================================

    for page_index, page in enumerate(
        pages,
        start=1,
    ):

        page_title = (
            page.get("title")
            or f"Dashboard Page {page_index}"
        )

        charts = page.get(
            "charts",
            [],
        )

        tables = page.get(
            "tables",
            [],
        )

        notes = page.get(
            "notes",
            [],
        )

        images = page.get(
            "images",
            [],
        )

        # ----------------------------------------------------
        # If page has content
        # ----------------------------------------------------

        if (
            charts
            or tables
            or notes
            or images
        ):

            story.append(
                PageBreak()
            )

            story.append(
                Paragraph(
                    f"Dashboard Page {page_index}",
                    styles["section_number"],
                )
            )

            story.append(
                Paragraph(
                    _safe_text(page_title),
                    styles["section_name"],
                )
            )

        # ====================================================
        # CAPTURED CHARTS
        # ====================================================

        for item in charts:

            global_section_number += 1

            section_name = _get_section_name(
                item,
                global_section_number,
            )

            story.append(
                Paragraph(
                    f"Section {global_section_number}",
                    styles["section_number"],
                )
            )

            story.append(
                Paragraph(
                    _safe_text(section_name),
                    styles["section_name"],
                )
            )

            # ------------------------------------------------
            # Actual captured chart
            # ------------------------------------------------

            chart_available_height = (
                available_height
                - (
                    72 * mm
                )
            )

            if chart_available_height < (
                50 * mm
            ):
                chart_available_height = (
                    50 * mm
                )

            _add_chart_to_story(
                story=story,
                item=item,
                available_width=available_width,
                available_height=chart_available_height,
            )

            # ------------------------------------------------
            # Corresponding displayed data
            # ------------------------------------------------

            data = _get_chart_data(item)

            table = _build_report_table(
                data,
                available_width,
            )

            if table is not None:

                story.append(
                    Paragraph(
                        "Displayed Data",
                        styles["table_heading"],
                    )
                )

                story.append(
                    table
                )

            story.append(
                Spacer(
                    1,
                    8,
                )
            )

            story.append(
                Paragraph(
                    "MSU Mumbai Health Programme "
                    "Management Dashboard",
                    styles["footer"],
                )
            )

        # ====================================================
        # ADDITIONAL TABLES
        # ====================================================

        for table_item in tables:

            if isinstance(
                table_item,
                pd.DataFrame,
            ):
                table_df = table_item

            elif isinstance(
                table_item,
                dict,
            ):
                table_df = table_item.get(
                    "data"
                )

            else:
                table_df = None

            if (
                table_df is None
                or not isinstance(
                    table_df,
                    pd.DataFrame,
                )
                or table_df.empty
            ):
                continue

            global_section_number += 1

            table_title = (
                table_item.get(
                    "title",
                    "Displayed Data",
                )
                if isinstance(
                    table_item,
                    dict,
                )
                else "Displayed Data"
            )

            story.append(
                PageBreak()
            )

            story.append(
                Paragraph(
                    f"Section {global_section_number}",
                    styles["section_number"],
                )
            )

            story.append(
                Paragraph(
                    _safe_text(table_title),
                    styles["section_name"],
                )
            )

            table = _build_report_table(
                table_df,
                available_width,
            )

            if table is not None:
                story.append(table)

        # ====================================================
        # NOTES
        # ====================================================

        for note in notes:

            if not note:
                continue

            story.append(
                Paragraph(
                    _safe_text(note),
                    styles["filter"],
                )
            )

        # ====================================================
        # IMAGES
        # ====================================================

        for image_item in images:

            try:

                from reportlab.platypus import Image

                image_data = None
                image_width = None
                image_height = None

                if isinstance(
                    image_item,
                    dict,
                ):

                    image_data = image_item.get(
                        "data"
                    )

                    image_width = image_item.get(
                        "width"
                    )

                    image_height = image_item.get(
                        "height"
                    )

                else:

                    image_data = image_item

                if not image_data:
                    continue

                if (
                    image_width is None
                    or image_height is None
                ):

                    image_width = available_width
                    image_height = (
                        110 * mm
                    )

                story.append(
                    PageBreak()
                )

                story.append(
                    Image(
                        io.BytesIO(
                            image_data
                        ),
                        width=image_width,
                        height=image_height,
                    )
                )

            except Exception:
                continue

    # ========================================================
    # BUILD
    # ========================================================

    doc.build(
        story
    )

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# BACKWARD-COMPATIBLE ALIAS
# ============================================================

def generate_dashboard_pdf(
    pages,
    report_period=None,
    filter_summary=None,
):
    return generate_captured_dashboard_pdf(
        pages=pages,
        report_period=report_period,
        filter_summary=filter_summary,
    )
