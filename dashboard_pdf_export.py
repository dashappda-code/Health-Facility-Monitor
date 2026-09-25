import io
import html

import pandas as pd
import streamlit as st

from displayed_chart_export import (
    _chart_to_png,
    _get_chart_image_size,
    _is_monthly_disease_comparison,
    _prepare_report_table,
    _format_table_value,
)


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
# SAFE TEXT
# ============================================================

def _safe_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return html.escape(str(value))


# ============================================================
# SAFE FILTER SUMMARY
# ============================================================

def _normalize_filter_summary(filter_summary):
    """
    Convert filter_summary into a safe dictionary.

    The app may provide:
        - dict
        - string
        - list
        - tuple
        - None

    This function prevents PDF generation from failing.
    """

    if filter_summary is None:
        return {}

    if isinstance(filter_summary, dict):
        return filter_summary

    if isinstance(filter_summary, str):
        text_value = filter_summary.strip()

        if not text_value:
            return {}

        return {
            "Filters": text_value
        }

    if isinstance(filter_summary, (list, tuple)):
        result = {}

        for index, value in enumerate(filter_summary, start=1):
            if value is None:
                continue

            text_value = str(value).strip()

            if text_value:
                result[f"Filter {index}"] = text_value

        return result

    try:
        return dict(filter_summary)
    except Exception:
        return {
            "Filters": str(filter_summary)
        }


# ============================================================
# SECTION NAME
# ============================================================

def _get_section_name(item, default="Dashboard Section"):

    if not isinstance(item, dict):
        return default

    section_name = item.get("section_name")

    if section_name is None:
        section_name = item.get("title")

    if section_name is None:
        return default

    section_name = str(section_name).strip()

    if not section_name:
        return default

    return section_name


# ============================================================
# CHART DATA
# ============================================================

def _get_chart_data(item):

    if not isinstance(item, dict):
        return pd.DataFrame()

    data = item.get("data")

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if data is None:
        return pd.DataFrame()

    try:
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


# ============================================================
# REPORT TABLE
# ============================================================

def _build_report_table(df, table_width):

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

    work_df = df.copy()

    if len(work_df) > MAX_TABLE_ROWS:
        work_df = work_df.head(MAX_TABLE_ROWS).copy()

    if len(work_df.columns) > MAX_TABLE_COLUMNS:
        work_df = work_df.iloc[:, :MAX_TABLE_COLUMNS].copy()

    columns = [str(column) for column in work_df.columns]

    work_df.columns = columns

    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        "ReportTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        alignment=TA_LEFT,
        textColor=colors.white,
    )

    body_style = ParagraphStyle(
        "ReportTableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=8.5,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    table_data = []

    header_row = []

    for column in columns:
        header_row.append(
            Paragraph(
                _safe_text(column),
                header_style,
            )
        )

    table_data.append(header_row)

    for _, row in work_df.iterrows():

        body_row = []

        for column in columns:

            value = row[column]

            try:
                formatted_value = _format_table_value(value)
            except Exception:
                formatted_value = value

            body_row.append(
                Paragraph(
                    _safe_text(formatted_value),
                    body_style,
                )
            )

        table_data.append(body_row)

    if not table_data:
        return None

    column_count = len(columns)

    if column_count <= 0:
        return None

    equal_width = table_width / column_count

    col_widths = [
        equal_width
        for _ in range(column_count)
    ]

    table = Table(
        table_data,
        colWidths=col_widths,
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
                    colors.HexColor("#1F4E78"),
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
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#B7C9D6"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F5F8FA"),
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


# ============================================================
# PDF STYLES
# ============================================================

def _get_pdf_styles():

    from reportlab.lib import colors
    from reportlab.lib.enums import (
        TA_CENTER,
        TA_LEFT,
    )
    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="DashboardCoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#163A5F"),
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardCoverSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#4F5B66"),
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardCoverReportTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1F4E78"),
            spaceAfter=15,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardCoverInfo",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#444444"),
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardIndexTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#163A5F"),
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardSectionTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#163A5F"),
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardChartTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1F4E78"),
            spaceBefore=4,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardTableTitle",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#333333"),
            spaceBefore=5,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardSmallText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#555555"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardNote",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#666666"),
        )
    )

    return styles


# ============================================================
# FILTER SUMMARY
# ============================================================

def _add_filter_summary(
    story,
    styles,
    report_period=None,
    filter_summary=None,
):

    from reportlab.platypus import (
        Paragraph,
        Spacer,
    )

    safe_filters = _normalize_filter_summary(
        filter_summary
    )

    if report_period:

        story.append(
            Paragraph(
                f"<b>Reporting Period:</b> "
                f"{_safe_text(report_period)}",
                styles["DashboardSmallText"],
            )
        )

        story.append(
            Spacer(1, 3)
        )

    if not safe_filters:
        return

    story.append(
        Paragraph(
            "<b>Applied Filters</b>",
            styles["DashboardTableTitle"],
        )
    )

    for key, value in safe_filters.items():

        if value is None:
            continue

        value_text = str(value).strip()

        if not value_text:
            continue

        story.append(
            Paragraph(
                f"<b>{_safe_text(key)}:</b> "
                f"{_safe_text(value_text)}",
                styles["DashboardSmallText"],
            )
        )

    story.append(
        Spacer(1, 6)
    )


# ============================================================
# COVER PAGE
# ============================================================

def _add_cover_page(
    story,
    styles,
    report_period=None,
    filter_summary=None,
):

    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        Spacer,
    )

    safe_filters = _normalize_filter_summary(
        filter_summary
    )

    story.append(
        Spacer(
            1,
            55 * mm,
        )
    )

    story.append(
        Paragraph(
            "MSU Mumbai Public Health Surveillance Dashboard",
            styles["DashboardCoverTitle"],
        )
    )

    story.append(
        Paragraph(
            "Surveillance • Monitoring • Analysis • Management",
            styles["DashboardCoverSubtitle"],
        )
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    story.append(
        Paragraph(
            "Complete Dashboard Report",
            styles["DashboardCoverReportTitle"],
        )
    )

    if report_period:

        story.append(
            Paragraph(
                f"<b>Reporting Period:</b> "
                f"{_safe_text(report_period)}",
                styles["DashboardCoverInfo"],
            )
        )

    if safe_filters:

        story.append(
            Spacer(
                1,
                5 * mm,
            )
        )

        story.append(
            Paragraph(
                "<b>Applied Filters</b>",
                styles["DashboardCoverInfo"],
            )
        )

        for key, value in safe_filters.items():

            if value is None:
                continue

            value_text = str(value).strip()

            if not value_text:
                continue

            story.append(
                Paragraph(
                    f"{_safe_text(key)}: "
                    f"{_safe_text(value_text)}",
                    styles["DashboardCoverInfo"],
                )
            )

    story.append(
        Spacer(
            1,
            12 * mm,
        )
    )

    story.append(
        Paragraph(
            "Prepared from the current dashboard view "
            "and selected filters.",
            styles["DashboardCoverInfo"],
        )
    )


# ============================================================
# INDEX
# ============================================================

def _add_index(
    story,
    styles,
    pages,
):

    from reportlab.lib import colors

    from reportlab.platypus import (
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    story.append(
        Paragraph(
            "Table of Contents",
            styles["DashboardIndexTitle"],
        )
    )

    story.append(
        Paragraph(
            "Dashboard Sections",
            styles["DashboardTableTitle"],
        )
    )

    index_data = [
        [
            Paragraph(
                "<b>No.</b>",
                styles["DashboardSmallText"],
            ),
            Paragraph(
                "<b>Section</b>",
                styles["DashboardSmallText"],
            ),
        ]
    ]

    for index, page in enumerate(
        pages,
        start=1,
    ):

        if isinstance(page, dict):

            title = (
                page.get("title")
                or page.get("page_name")
                or page.get("name")
                or f"Dashboard Section {index}"
            )

        else:

            title = str(page)

        index_data.append(
            [
                Paragraph(
                    str(index),
                    styles["DashboardSmallText"],
                ),
                Paragraph(
                    _safe_text(title),
                    styles["DashboardSmallText"],
                ),
            ]
        )

    table = Table(
        index_data,
        colWidths=[
            18,
            150,
        ],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#EAF1F7"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#B7C9D6"),
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
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    story.append(table)

    story.append(
        Spacer(
            1,
            10,
        )
    )


# ============================================================
# ADD CHART
# ============================================================

def _add_chart_to_story(
    story,
    item,
    styles,
    table_width,
):

    from reportlab.lib.units import mm

    from reportlab.platypus import (
        Image,
        KeepTogether,
        Paragraph,
        Spacer,
    )

    chart_title = item.get("title")

    if not chart_title:
        chart_title = "Dashboard Chart"

    try:
        png_bytes = _chart_to_png(item)
    except Exception as exc:

        story.append(
            Paragraph(
                f"<b>Chart could not be rendered:</b> "
                f"{_safe_text(exc)}",
                styles["DashboardNote"],
            )
        )

        return

    if not png_bytes:

        story.append(
            Paragraph(
                "Chart image was not available.",
                styles["DashboardNote"],
            )
        )

        return

    try:

        image_width, image_height = _get_chart_image_size(
            item
        )

        image_width = float(image_width)
        image_height = float(image_height)

    except Exception:

        image_width = 1000
        image_height = 360

    try:

        is_monthly_disease = (
            _is_monthly_disease_comparison(item)
        )

    except Exception:

        is_monthly_disease = False

    if is_monthly_disease:

        target_height_mm = MONTHLY_DISEASE_HEIGHT_MM

    else:

        aspect_ratio = (
            image_height / image_width
            if image_width
            else 0.36
        )

        target_height_mm = (
            table_width / mm
        ) * aspect_ratio

        target_height_mm = max(
            MIN_CHART_HEIGHT_MM,
            min(
                MAX_CHART_HEIGHT_MM,
                target_height_mm,
            ),
        )

    image = Image(
        io.BytesIO(png_bytes)
    )

    image.drawWidth = table_width

    image.drawHeight = (
        target_height_mm * mm
    )

    chart_title_paragraph = Paragraph(
        _safe_text(chart_title),
        styles["DashboardChartTitle"],
    )

    chart_df = _get_chart_data(item)

    table = None

    if chart_df is not None and not chart_df.empty:

        try:

            table = _build_report_table(
                chart_df,
                table_width,
            )

        except Exception:

            table = None

    elements = [
        chart_title_paragraph,
        image,
    ]

    if table is not None:

        elements.extend(
            [
                Spacer(1, 5),
                Paragraph(
                    "Displayed Data",
                    styles["DashboardTableTitle"],
                ),
                table,
            ]
        )

    elements.append(
        Spacer(1, 10)
    )

    try:

        story.append(
            KeepTogether(elements)
        )

    except Exception:

        for element in elements:
            story.append(element)


# ============================================================
# FOOTER
# ============================================================

def _add_footer(
    canvas,
    doc,
):

    from reportlab.lib import colors
    from reportlab.lib.units import mm

    page_number = canvas.getPageNumber()

    canvas.saveState()

    page_width = doc.pagesize[0]

    canvas.setStrokeColor(
        colors.HexColor("#D0D7DE")
    )

    canvas.setLineWidth(0.4)

    canvas.line(
        12 * mm,
        8 * mm,
        page_width - (12 * mm),
        8 * mm,
    )

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.setFillColor(
        colors.HexColor("#666666")
    )

    canvas.drawString(
        12 * mm,
        4.5 * mm,
        "MSU Mumbai Public Health Surveillance Dashboard",
    )

    canvas.drawRightString(
        page_width - (12 * mm),
        4.5 * mm,
        f"Page {page_number}",
    )

    canvas.restoreState()


# ============================================================
# GENERATE CAPTURED DASHBOARD PDF
# ============================================================

def generate_captured_dashboard_pdf(
    pages,
    report_period=None,
    filter_summary=None,
):

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm

    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    if pages is None:
        pages = []

    pages = list(pages)

    buffer = io.BytesIO()

    page_width, page_height = A4

    margin = PDF_MARGIN_MM * mm

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title="MSU Mumbai Public Health Surveillance Dashboard",
        author="MSU Mumbai Public Health Surveillance Dashboard",
        subject="Complete Dashboard Report",
    )

    styles = _get_pdf_styles()

    story = []

    # ========================================================
    # COVER
    # ========================================================

    _add_cover_page(
        story=story,
        styles=styles,
        report_period=report_period,
        filter_summary=filter_summary,
    )

    # ========================================================
    # INDEX
    # ========================================================

    story.append(
        PageBreak()
    )

    _add_index(
        story=story,
        styles=styles,
        pages=pages,
    )

    table_width = (
        page_width
        - (2 * margin)
    )

    # ========================================================
    # DASHBOARD PAGES
    # ========================================================

    for page_index, page in enumerate(
        pages,
        start=1,
    ):

        story.append(
            PageBreak()
        )

        if isinstance(page, dict):

            page_title = (
                page.get("title")
                or page.get("page_name")
                or page.get("name")
                or f"Dashboard Section {page_index}"
            )

            captured_charts = (
                page.get("charts")
                or page.get("captured_charts")
                or []
            )

            additional_tables = (
                page.get("tables")
                or page.get("additional_tables")
                or []
            )

            notes = (
                page.get("notes")
                or []
            )

            images = (
                page.get("images")
                or []
            )

        else:

            page_title = str(page)

            captured_charts = []
            additional_tables = []
            notes = []
            images = []

        # ----------------------------------------------------
        # SECTION TITLE
        # ----------------------------------------------------

        story.append(
            Paragraph(
                _safe_text(page_title),
                styles["DashboardSectionTitle"],
            )
        )

        # ----------------------------------------------------
        # FILTER INFORMATION
        # ----------------------------------------------------

        if page_index == 1:

            _add_filter_summary(
                story=story,
                styles=styles,
                report_period=report_period,
                filter_summary=filter_summary,
            )

        # ----------------------------------------------------
        # CHARTS
        # ----------------------------------------------------

        if captured_charts:

            for item in captured_charts:

                if not isinstance(item, dict):
                    continue

                _add_chart_to_story(
                    story=story,
                    item=item,
                    styles=styles,
                    table_width=table_width,
                )

        # ----------------------------------------------------
        # ADDITIONAL TABLES
        # ----------------------------------------------------

        if additional_tables:

            for table_item in additional_tables:

                if isinstance(
                    table_item,
                    pd.DataFrame,
                ):

                    table_df = table_item
                    table_title = "Displayed Data"

                elif isinstance(
                    table_item,
                    dict,
                ):

                    table_df = table_item.get(
                        "data"
                    )

                    table_title = (
                        table_item.get("title")
                        or "Displayed Data"
                    )

                    if not isinstance(
                        table_df,
                        pd.DataFrame,
                    ):

                        try:
                            table_df = pd.DataFrame(
                                table_df
                            )
                        except Exception:
                            table_df = pd.DataFrame()

                else:

                    try:
                        table_df = pd.DataFrame(
                            table_item
                        )
                    except Exception:
                        table_df = pd.DataFrame()

                    table_title = "Displayed Data"

                if table_df is None or table_df.empty:
                    continue

                story.append(
                    Paragraph(
                        _safe_text(table_title),
                        styles["DashboardTableTitle"],
                    )
                )

                try:

                    report_table = _build_report_table(
                        table_df,
                        table_width,
                    )

                    if report_table is not None:

                        story.append(
                            report_table
                        )

                        story.append(
                            Spacer(1, 8)
                        )

                except Exception as exc:

                    story.append(
                        Paragraph(
                            f"Table could not be rendered: "
                            f"{_safe_text(exc)}",
                            styles["DashboardNote"],
                        )
                    )

        # ----------------------------------------------------
        # NOTES
        # ----------------------------------------------------

        if notes:

            story.append(
                Spacer(1, 4)
            )

            for note in notes:

                if note is None:
                    continue

                note_text = str(note).strip()

                if not note_text:
                    continue

                story.append(
                    Paragraph(
                        _safe_text(note_text),
                        styles["DashboardNote"],
                    )
                )

                story.append(
                    Spacer(1, 3)
                )

        # ----------------------------------------------------
        # IMAGES
        # ----------------------------------------------------

        if images:

            from reportlab.platypus import Image

            for image_item in images:

                try:

                    if isinstance(
                        image_item,
                        bytes,
                    ):

                        image_bytes = image_item

                    elif isinstance(
                        image_item,
                        io.BytesIO,
                    ):

                        image_item.seek(0)

                        image_bytes = (
                            image_item.read()
                        )

                    else:

                        continue

                    if not image_bytes:
                        continue

                    image = Image(
                        io.BytesIO(
                            image_bytes
                        )
                    )

                    image_width = table_width

                    try:

                        original_width = float(
                            image.imageWidth
                        )

                        original_height = float(
                            image.imageHeight
                        )

                        if original_width > 0:

                            image_height = (
                                image_width
                                * original_height
                                / original_width
                            )

                        else:

                            image_height = 80 * mm

                    except Exception:

                        image_height = 80 * mm

                    max_height = 130 * mm

                    if image_height > max_height:
                        image_height = max_height

                    image.drawWidth = image_width
                    image.drawHeight = image_height

                    story.append(
                        Spacer(1, 5)
                    )

                    story.append(
                        image
                    )

                    story.append(
                        Spacer(1, 8)
                    )

                except Exception:
                    continue

    # ========================================================
    # NO CAPTURE FALLBACK
    # ========================================================

    if not pages:

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "No dashboard sections were captured.",
                styles["DashboardSectionTitle"],
            )
        )

        story.append(
            Paragraph(
                "Please generate the Complete Dashboard PDF "
                "again after the dashboard pages have loaded.",
                styles["DashboardSmallText"],
            )
        )

    # ========================================================
    # BUILD PDF
    # ========================================================

    doc.build(
        story,
        onFirstPage=_add_footer,
        onLaterPages=_add_footer,
    )

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# BACKWARD COMPATIBILITY
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
