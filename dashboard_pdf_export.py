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
# EXISTING WORKING CHART ENGINE
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
        return html.escape(
            str(value)
        )
    except Exception:
        return ""


def _get_section_name(
    item,
    index,
):

    section_name = item.get(
        "section_name"
    )

    if section_name:
        return str(
            section_name
        ).strip()

    title = item.get(
        "title"
    )

    if title:
        return str(
            title
        ).strip()

    return f"Section {index}"


def _get_chart_data(item):

    data = item.get(
        "data"
    )

    if isinstance(
        data,
        pd.DataFrame,
    ):
        return data

    if data is None:
        return pd.DataFrame()

    try:
        return pd.DataFrame(
            data
        )
    except Exception:
        return pd.DataFrame()


# ============================================================
# TABLE BUILDER
# ============================================================

def _build_report_table(
    df,
    table_width,
):

    from reportlab import colors

    from reportlab.lib.enums import (
        TA_LEFT,
    )

    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )

    from reportlab.platypus import (
        Paragraph,
        Table,
        TableStyle,
    )

    if (
        df is None
        or df.empty
    ):
        return None

    table_df = _prepare_report_table(
        df
    )

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
                _safe_text(
                    column
                ),
                header_style,
            )
            for column
            in table_df.columns
        ]
    ]

    for _, row in table_df.iterrows():

        data.append(
            [
                Paragraph(
                    _safe_text(
                        _format_table_value(
                            value
                        )
                    ),
                    body_style,
                )
                for value
                in row.tolist()
            ]
        )

    number_of_columns = (
        len(
            table_df.columns
        )
    )

    if number_of_columns <= 0:
        return None

    column_width = (
        table_width
        / number_of_columns
    )

    table = Table(
        data,
        colWidths=[
            column_width
            for _ in range(
                number_of_columns
            )
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
                    colors.HexColor(
                        "#E9EEF5"
                    ),
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
                    colors.HexColor(
                        "#B7B7B7"
                    ),
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
                        colors.HexColor(
                            "#F8FAFC"
                        ),
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

    from reportlab import colors

    from reportlab.lib.enums import (
        TA_CENTER,
        TA_LEFT,
    )

    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )

    styles = getSampleStyleSheet()

    return {

        "cover_title": ParagraphStyle(
            "DashboardPDFCoverTitle",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceAfter=10,
        ),

        "cover_subtitle": ParagraphStyle(
            "DashboardPDFCoverSubtitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(
                "#4B5563"
            ),
            spaceAfter=8,
        ),

        "cover_period": ParagraphStyle(
            "DashboardPDFCoverPeriod",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor(
                "#374151"
            ),
            spaceAfter=8,
        ),

        "cover_filter": ParagraphStyle(
            "DashboardPDFCoverFilter",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor(
                "#6B7280"
            ),
            spaceAfter=12,
        ),

        "index_title": ParagraphStyle(
            "DashboardPDFIndexTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceAfter=14,
        ),

        "index_item": ParagraphStyle(
            "DashboardPDFIndexItem",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            leftIndent=5,
            textColor=colors.HexColor(
                "#374151"
            ),
        ),

        "page_number": ParagraphStyle(
            "DashboardPDFPageNumber",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor(
                "#4B5563"
            ),
            spaceAfter=3,
        ),

        "section_number": ParagraphStyle(
            "DashboardPDFSectionNumber",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor(
                "#4B5563"
            ),
            spaceAfter=3,
        ),

        "section_name": ParagraphStyle(
            "DashboardPDFSectionName",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceAfter=7,
            keepWithNext=True,
        ),

        "table_heading": ParagraphStyle(
            "DashboardPDFTableHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor(
                "#374151"
            ),
            spaceAfter=5,
            keepWithNext=True,
        ),

        "filter": ParagraphStyle(
            "DashboardPDFFilter",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor(
                "#555555"
            ),
            spaceAfter=10,
        ),

        "footer": ParagraphStyle(
            "DashboardPDFFooter",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor(
                "#777777"
            ),
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

    from reportlab.platypus import (
        Paragraph,
    )

    if not filter_summary:
        return

    if isinstance(
        filter_summary,
        dict,
    ):

        summary_parts = []

        for key, value in (
            filter_summary.items()
        ):

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
                    "<br/>".join(
                        summary_parts
                    ),
                    style,
                )
            )

    else:

        story.append(
            Paragraph(
                _safe_text(
                    filter_summary
                ),
                style,
            )
        )


# ============================================================
# COVER PAGE
# ============================================================

def _add_cover_page(
    story,
    report_period,
    filter_summary,
    styles,
):

    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        Spacer,
    )

    story.append(
        Spacer(
            1,
            55 * mm,
        )
    )

    story.append(
        Paragraph(
            "MSU Mumbai Public Health "
            "Surveillance Dashboard",
            styles["cover_title"],
        )
    )

    story.append(
        Paragraph(
            "Surveillance • Monitoring • "
            "Analysis • Management",
            styles["cover_subtitle"],
        )
    )

    story.append(
        Spacer(
            1,
            8 * mm,
        )
    )

    story.append(
        Paragraph(
            "Complete Dashboard Report",
            styles["cover_subtitle"],
        )
    )

    if report_period:

        story.append(
            Spacer(
                1,
                8 * mm,
            )
        )

        story.append(
            Paragraph(
                "<b>Reporting Period</b><br/>"
                f"{_safe_text(report_period)}",
                styles["cover_period"],
            )
        )

    if filter_summary:

        story.append(
            Spacer(
                1,
                5 * mm,
            )
        )

        story.append(
            Paragraph(
                "<b>Applied Filters</b><br/>"
                f"{_safe_text(filter_summary)}",
                styles["cover_filter"],
            )
        )

    story.append(
        Spacer(
            1,
            20 * mm,
        )
    )

    story.append(
        Paragraph(
            "Prepared from the current dashboard "
            "view and selected filters.",
            styles["cover_filter"],
        )
    )


# ============================================================
# INDEX
# ============================================================

def _add_index(
    story,
    pages,
    styles,
):

    from reportlab.platypus import (
        Paragraph,
        PageBreak,
        Spacer,
    )

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "Table of Contents",
            styles["index_title"],
        )
    )

    story.append(
        Paragraph(
            "Dashboard Sections",
            styles["section_name"],
        )
    )

    for index, page in enumerate(
        pages,
        start=1,
    ):

        title = (
            page.get(
                "title"
            )
            or f"Dashboard Page {index}"
        )

        story.append(
            Paragraph(
                f"{index}. "
                f"{_safe_text(title)}",
                styles["index_item"],
            )
        )

        story.append(
            Spacer(
                1,
                3,
            )
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

    from reportlab.platypus import (
        Image,
        Spacer,
    )

    try:

        png_bytes = _chart_to_png(
            item
        )

    except Exception:
        return False

    if not png_bytes:
        return False

    try:

        chart_width, chart_height = (
            _get_chart_image_size(
                item,
                png_bytes,
                available_width,
                available_height,
            )
        )

    except Exception:

        chart_width = available_width
        chart_height = (
            available_height
        )

    story.append(
        Image(
            io.BytesIO(
                png_bytes
            ),
            width=chart_width,
            height=chart_height,
        )
    )

    story.append(
        Spacer(
            1,
            6,
        )
    )

    return True


# ============================================================
# ADD FOOTER
# ============================================================

def _add_footer(
    story,
    styles,
):

    from reportlab.platypus import (
        Paragraph,
    )

    story.append(
        Paragraph(
            "MSU Mumbai Health Programme "
            "Management Dashboard",
            styles["footer"],
        )
    )


# ============================================================
# COMPLETE DASHBOARD PDF
# ============================================================

def generate_captured_dashboard_pdf(
    pages,
    report_period=None,
    filter_summary=None,
):

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    from reportlab.platypus import (
        KeepTogether,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    if pages is None:
        pages = []

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=(
            PDF_MARGIN_MM * mm
        ),
        leftMargin=(
            PDF_MARGIN_MM * mm
        ),
        topMargin=(
            PDF_MARGIN_MM * mm
        ),
        bottomMargin=(
            PDF_MARGIN_MM * mm
        ),
        title=(
            "MSU Mumbai Public Health "
            "Surveillance Dashboard"
        ),
        author="MSU Mumbai",
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
    # 1. COVER
    # ========================================================

    _add_cover_page(
        story=story,
        report_period=report_period,
        filter_summary=filter_summary,
        styles=styles,
    )

    # ========================================================
    # 2. INDEX
    # ========================================================

    _add_index(
        story=story,
        pages=pages,
        styles=styles,
    )

    # ========================================================
    # 3. DASHBOARD SECTIONS
    # ========================================================

    global_section_number = 0

    for page_index, page in enumerate(
        pages,
        start=1,
    ):

        page_title = (
            page.get(
                "title"
            )
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

        has_content = bool(
            charts
            or tables
            or notes
            or images
        )

        # ----------------------------------------------------
        # Every major dashboard page starts on new PDF page
        # ----------------------------------------------------

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                f"{page_index}. "
                f"{_safe_text(page_title)}",
                styles["page_number"],
            )
        )

        # ----------------------------------------------------
        # If nothing captured
        # ----------------------------------------------------

        if not has_content:

            story.append(
                Paragraph(
                    "No reportable chart or data object "
                    "was captured for this dashboard section.",
                    styles["filter"],
                )
            )

            continue

        # ====================================================
        # CAPTURED CHARTS
        # ====================================================

        for chart_index, item in enumerate(
            charts,
            start=1,
        ):

            global_section_number += 1

            section_name = (
                _get_section_name(
                    item,
                    global_section_number,
                )
            )

            # ------------------------------------------------
            # Every chart/report section starts on new page
            # ------------------------------------------------

            if chart_index > 1:

                story.append(
                    PageBreak()
                )

            section_header = [
                Paragraph(
                    f"Section "
                    f"{global_section_number}",
                    styles["section_number"],
                ),

                Paragraph(
                    _safe_text(
                        section_name
                    ),
                    styles["section_name"],
                ),
            ]

            # ------------------------------------------------
            # Actual captured chart
            # ------------------------------------------------

            chart_available_height = (
                available_height
                - (
                    70 * mm
                )
            )

            if chart_available_height < (
                MIN_CHART_HEIGHT_MM * mm
            ):

                chart_available_height = (
                    MIN_CHART_HEIGHT_MM
                    * mm
                )

            chart_available_height = min(
                chart_available_height,
                MAX_CHART_HEIGHT_MM * mm,
            )

            chart_story = []

            chart_story.extend(
                section_header
            )

            chart_added = (
                _add_chart_to_story(
                    story=chart_story,
                    item=item,
                    available_width=available_width,
                    available_height=(
                        chart_available_height
                    ),
                )
            )

            # ------------------------------------------------
            # Corresponding displayed data
            # ------------------------------------------------

            data = _get_chart_data(
                item
            )

            table = _build_report_table(
                data,
                available_width,
            )

            if table is not None:

                chart_story.append(
                    Paragraph(
                        "Displayed Data",
                        styles["table_heading"],
                    )
                )

                chart_story.append(
                    table
                )

            # ------------------------------------------------
            # Keep heading + chart together.
            # Table may flow if it is very large.
            # ------------------------------------------------

            if chart_added or table is not None:

                try:

                    story.append(
                        KeepTogether(
                            chart_story
                        )
                    )

                except Exception:

                    story.extend(
                        chart_story
                    )

            else:

                story.extend(
                    section_header
                )

                story.append(
                    Paragraph(
                        "Chart image could not be "
                        "generated from the captured "
                        "dashboard object.",
                        styles["filter"],
                    )
                )

            story.append(
                Spacer(
                    1,
                    5,
                )
            )

            _add_footer(
                story,
                styles,
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
                table_title = (
                    "Displayed Data"
                )

            elif isinstance(
                table_item,
                dict,
            ):

                table_df = (
                    table_item.get(
                        "dataframe"
                    )
                )

                if table_df is None:

                    table_df = (
                        table_item.get(
                            "data"
                        )
                    )

                table_title = (
                    table_item.get(
                        "title",
                        "Displayed Data",
                    )
                )

            else:

                table_df = None
                table_title = (
                    "Displayed Data"
                )

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

            story.append(
                PageBreak()
            )

            story.append(
                Paragraph(
                    f"Section "
                    f"{global_section_number}",
                    styles["section_number"],
                )
            )

            story.append(
                Paragraph(
                    _safe_text(
                        table_title
                    ),
                    styles["section_name"],
                )
            )

            table = _build_report_table(
                table_df,
                available_width,
            )

            if table is not None:
                story.append(
                    table
                )

            story.append(
                Spacer(
                    1,
                    6,
                )
            )

            _add_footer(
                story,
                styles,
            )

        # ====================================================
        # NOTES
        # ====================================================

        for note in notes:

            if not note:
                continue

            story.append(
                Spacer(
                    1,
                    5,
                )
            )

            story.append(
                Paragraph(
                    _safe_text(
                        note
                    ),
                    styles["filter"],
                )
            )

        # ====================================================
        # IMAGE ELEMENTS
        # ====================================================

        for image_item in images:

            try:

                from reportlab.platypus import (
                    Image,
                )

                image_data = None
                image_width = None
                image_height = None

                if isinstance(
                    image_item,
                    dict,
                ):

                    image_data = (
                        image_item.get(
                            "data"
                        )
                    )

                    image_width = (
                        image_item.get(
                            "width"
                        )
                    )

                    image_height = (
                        image_item.get(
                            "height"
                        )
                    )

                else:

                    image_data = (
                        image_item
                    )

                if not image_data:
                    continue

                if (
                    image_width is None
                    or image_height is None
                ):

                    image_width = (
                        available_width
                    )

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

                story.append(
                    Spacer(
                        1,
                        6,
                    )
                )

                _add_footer(
                    story,
                    styles,
                )

            except Exception:
                continue

    # ========================================================
    # BUILD PDF
    # ========================================================

    doc.build(
        story
    )

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# BACKWARD COMPATIBLE ALIAS
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
