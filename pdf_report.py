from io import BytesIO
from datetime import datetime
import html

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
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
    LongTable,
    Table,
    TableStyle,
    PageBreak,
    Image,
)

from displayed_chart_export import (
    _chart_to_png,
    _get_chart_image_size,
    _format_table_value,
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
# CONFIGURATION
# ============================================================

PDF_MARGIN_MM = 12

MAX_TABLE_ROWS = 300
MAX_TABLE_COLUMNS = 14

MAX_IMAGE_HEIGHT_MM = 155


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

    return html.escape(
        str(value)
    )


def _format_number(value):

    try:
        return f"{int(value):,}"

    except Exception:
        return str(
            value
            if value is not None
            else ""
        )


def _to_dataframe(value):

    if value is None:
        return pd.DataFrame()

    if isinstance(
        value,
        pd.DataFrame,
    ):
        return value.copy()

    if isinstance(
        value,
        pd.Series,
    ):
        return (
            value
            .to_frame()
            .reset_index(drop=True)
        )

    try:
        return pd.DataFrame(
            value
        )

    except Exception:
        return pd.DataFrame()


def _normalise_items(value):

    if value is None:
        return []

    if isinstance(
        value,
        (list, tuple),
    ):
        return list(value)

    return [value]


def _get_item_dataframe(item):

    if isinstance(
        item,
        pd.DataFrame,
    ):
        return item.copy()

    if not isinstance(
        item,
        dict,
    ):
        return _to_dataframe(
            item
        )

    for key in (
        "data",
        "dataframe",
        "df",
        "table",
    ):

        value = item.get(
            key
        )

        if value is None:
            continue

        dataframe = (
            _to_dataframe(
                value
            )
        )

        if not dataframe.empty:
            return dataframe

    return pd.DataFrame()


def _get_item_title(
    item,
    default_title,
):

    if not isinstance(
        item,
        dict,
    ):
        return default_title

    return (
        item.get("title")
        or item.get("label")
        or item.get("section_name")
        or item.get("name")
        or default_title
    )


# ============================================================
# STYLES
# ============================================================

def _styles():

    styles = (
        getSampleStyleSheet()
    )

    styles.add(
        ParagraphStyle(
            name="PageReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#163A5F"
            ),
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#5B6570"
            ),
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportSectionTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_LEFT,
            textColor=colors.HexColor(
                "#163A5F"
            ),
            spaceBefore=4,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportSubTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor(
                "#1F4E78"
            ),
            spaceBefore=5,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.5,
            alignment=TA_LEFT,
            textColor=colors.HexColor(
                "#555555"
            ),
            spaceAfter=3,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportNote",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8.2,
            leading=11,
            alignment=TA_LEFT,
            textColor=colors.HexColor(
                "#555555"
            ),
            spaceAfter=5,
        )
    )

    return styles


# ============================================================
# FOOTER
# ============================================================

def _header_footer(
    canvas,
    doc,
):

    canvas.saveState()

    page_width = A4[0]

    canvas.setStrokeColor(
        colors.HexColor(
            "#D0D7DE"
        )
    )

    canvas.setLineWidth(
        0.4
    )

    canvas.line(
        PDF_MARGIN_MM * mm,
        9 * mm,
        page_width
        - PDF_MARGIN_MM * mm,
        9 * mm,
    )

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.setFillColor(
        colors.HexColor(
            "#666666"
        )
    )

    canvas.drawString(
        PDF_MARGIN_MM * mm,
        5 * mm,
        DASHBOARD_TITLE,
    )

    canvas.drawRightString(
        page_width
        - PDF_MARGIN_MM * mm,
        5 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# TABLE
# ============================================================

def _build_table(
    dataframe,
    table_width,
):

    if (
        dataframe is None
        or dataframe.empty
    ):
        return None

    work_df = (
        dataframe
        .copy()
    )

    if (
        len(work_df)
        > MAX_TABLE_ROWS
    ):
        work_df = (
            work_df
            .head(
                MAX_TABLE_ROWS
            )
            .copy()
        )

    if (
        len(work_df.columns)
        > MAX_TABLE_COLUMNS
    ):
        work_df = (
            work_df
            .iloc[
                :,
                :MAX_TABLE_COLUMNS,
            ]
            .copy()
        )

    columns = [
        str(column)
        for column
        in work_df.columns
    ]

    if not columns:
        return None

    work_df.columns = (
        columns
    )

    sample_styles = (
        getSampleStyleSheet()
    )

    column_count = len(
        columns
    )

    if column_count <= 5:

        header_size = 7.5
        body_size = 7.0

    elif column_count <= 9:

        header_size = 6.8
        body_size = 6.2

    else:

        header_size = 6.0
        body_size = 5.5

    header_style = (
        ParagraphStyle(
            "PageTableHeader",
            parent=sample_styles[
                "Normal"
            ],
            fontName="Helvetica-Bold",
            fontSize=header_size,
            leading=header_size + 1.5,
            textColor=colors.white,
        )
    )

    body_style = (
        ParagraphStyle(
            "PageTableBody",
            parent=sample_styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=body_size,
            leading=body_size + 1.5,
            textColor=colors.black,
        )
    )

    table_data = [
        [
            Paragraph(
                _safe_text(
                    column
                ),
                header_style,
            )
            for column in columns
        ]
    ]

    for _, row in (
        work_df.iterrows()
    ):

        body_row = []

        for column in columns:

            value = row[
                column
            ]

            try:

                value = (
                    _format_table_value(
                        value
                    )
                )

            except Exception:
                pass

            body_row.append(
                Paragraph(
                    _safe_text(
                        value
                    ),
                    body_style,
                )
            )

        table_data.append(
            body_row
        )

    column_width = (
        table_width
        / column_count
    )

    table = LongTable(
        table_data,
        colWidths=[
            column_width
            for _ in range(
                column_count
            )
        ],
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#1F4E78"
                    ),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
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
                    colors.HexColor(
                        "#B7C9D6"
                    ),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor(
                            "#F5F8FA"
                        ),
                    ],
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
            ]
        )
    )

    return table


# ============================================================
# REPORT HEADER
# ============================================================

def _add_report_header(
    story,
    styles,
    page_name,
    report_period=None,
    filter_summary=None,
    record_count=None,
):

    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles[
                "PageReportTitle"
            ],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles[
                "PageReportSubtitle"
            ],
        )
    )

    story.append(
        Paragraph(
            _safe_text(
                page_name
            ),
            styles[
                "PageReportSectionTitle"
            ],
        )
    )

    story.append(
        Paragraph(
            "Report generated on: "
            + datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            ),
            styles[
                "PageReportSmall"
            ],
        )
    )

    if report_period:

        story.append(
            Paragraph(
                "<b>Reporting Period:</b> "
                + _safe_text(
                    report_period
                ),
                styles[
                    "PageReportSmall"
                ],
            )
        )

    if filter_summary:

        story.append(
            Paragraph(
                "<b>Filter Scope:</b> "
                + _safe_text(
                    filter_summary
                ),
                styles[
                    "PageReportSmall"
                ],
            )
        )

    if record_count is not None:

        story.append(
            Paragraph(
                "<b>Records in current scope:</b> "
                + _format_number(
                    record_count
                ),
                styles[
                    "PageReportSmall"
                ],
            )
        )

    story.append(
        Spacer(
            1,
            8,
        )
    )


# ============================================================
# METRIC TABLE
# ============================================================

def _build_metrics_dataframe(
    metrics,
):

    rows = []

    for item in (
        _normalise_items(
            metrics
        )
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        label = (
            item.get("label")
            or item.get("title")
            or "Metric"
        )

        value = item.get(
            "value",
            "",
        )

        delta = item.get(
            "delta",
            "",
        )

        row = {
            "Indicator": label,
            "Value": value,
        }

        if (
            delta is not None
            and str(delta).strip()
        ):
            row["Change"] = (
                delta
            )

        rows.append(
            row
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(
        rows
    )


# ============================================================
# ADD CHART
# ============================================================

def _add_chart(
    story,
    styles,
    item,
    table_width,
):

    if not isinstance(
        item,
        dict,
    ):
        return False

    title = (
        item.get("title")
        or item.get("section_name")
        or "Dashboard Chart"
    )

    try:

        png_bytes = (
            _chart_to_png(
                item
            )
        )

    except Exception:
        png_bytes = None

    if not png_bytes:
        return False

    story.append(
        Paragraph(
            _safe_text(
                title
            ),
            styles[
                "PageReportSubTitle"
            ],
        )
    )

    available_height = (
        125 * mm
    )

    try:

        chart_width, chart_height = (
            _get_chart_image_size(
                item,
                png_bytes,
                table_width,
                available_height,
            )
        )

    except Exception:

        chart_width = (
            table_width
        )

        chart_height = (
            80 * mm
        )

    try:

        image = Image(
            BytesIO(
                png_bytes
            ),
            width=chart_width,
            height=chart_height,
        )

        image.hAlign = (
            "CENTER"
        )

        story.append(
            image
        )

        story.append(
            Spacer(
                1,
                7,
            )
        )

        return True

    except Exception:

        return False


# ============================================================
# EXTRACT IMAGE
# ============================================================

def _extract_image_bytes(
    item,
):

    if isinstance(
        item,
        bytes,
    ):
        return item

    if isinstance(
        item,
        bytearray,
    ):
        return bytes(
            item
        )

    if isinstance(
        item,
        BytesIO,
    ):

        item.seek(0)

        return item.read()

    if not isinstance(
        item,
        dict,
    ):
        return None

    for key in (
        "data",
        "bytes",
        "image",
        "png",
    ):

        raw = item.get(
            key
        )

        if isinstance(
            raw,
            bytes,
        ):
            return raw

        if isinstance(
            raw,
            bytearray,
        ):
            return bytes(
                raw
            )

        if isinstance(
            raw,
            BytesIO,
        ):

            raw.seek(0)

            return raw.read()

    return None


# ============================================================
# ADD IMAGE
# ============================================================

def _add_image(
    story,
    styles,
    item,
    table_width,
):

    image_bytes = (
        _extract_image_bytes(
            item
        )
    )

    if not image_bytes:
        return False

    title = (
        _get_item_title(
            item,
            "Dashboard Image",
        )
    )

    caption = ""

    if isinstance(
        item,
        dict,
    ):

        caption = (
            item.get("caption")
            or item.get("note")
            or ""
        )

    story.append(
        Paragraph(
            _safe_text(
                title
            ),
            styles[
                "PageReportSubTitle"
            ],
        )
    )

    if caption:

        story.append(
            Paragraph(
                _safe_text(
                    caption
                ),
                styles[
                    "PageReportNote"
                ],
            )
        )

    try:

        image = Image(
            BytesIO(
                image_bytes
            )
        )

        original_width = float(
            image.imageWidth
        )

        original_height = float(
            image.imageHeight
        )

        draw_width = (
            table_width
        )

        if original_width > 0:

            draw_height = (
                draw_width
                * original_height
                / original_width
            )

        else:

            draw_height = (
                80 * mm
            )

        maximum_height = (
            MAX_IMAGE_HEIGHT_MM
            * mm
        )

        if draw_height > maximum_height:

            scale = (
                maximum_height
                / draw_height
            )

            draw_height = (
                maximum_height
            )

            draw_width = (
                draw_width
                * scale
            )

        image.drawWidth = (
            draw_width
        )

        image.drawHeight = (
            draw_height
        )

        image.hAlign = (
            "CENTER"
        )

        story.append(
            image
        )

        story.append(
            Spacer(
                1,
                7,
            )
        )

        return True

    except Exception:

        return False


# ============================================================
# ADD TABLE
# ============================================================

def _add_table(
    story,
    styles,
    item,
    table_width,
):

    dataframe = (
        _get_item_dataframe(
            item
        )
    )

    if dataframe.empty:
        return False

    title = (
        _get_item_title(
            item,
            "Displayed Data",
        )
    )

    story.append(
        Paragraph(
            _safe_text(
                title
            ),
            styles[
                "PageReportSubTitle"
            ],
        )
    )

    table = (
        _build_table(
            dataframe,
            table_width,
        )
    )

    if table is None:
        return False

    story.append(
        table
    )

    story.append(
        Spacer(
            1,
            8,
        )
    )

    return True


# ============================================================
# ADD NOTES
# ============================================================

def _add_notes(
    story,
    styles,
    notes,
):

    valid_notes = []

    for item in (
        _normalise_items(
            notes
        )
    ):

        if isinstance(
            item,
            dict,
        ):

            text = (
                item.get("text")
                or item.get("message")
                or item.get("note")
                or ""
            )

        else:

            text = str(
                item
            )

        text = (
            str(text)
            .strip()
        )

        if text:
            valid_notes.append(
                text
            )

    if not valid_notes:
        return

    story.append(
        Paragraph(
            "Notes",
            styles[
                "PageReportSubTitle"
            ],
        )
    )

    for text in valid_notes:

        story.append(
            Paragraph(
                _safe_text(
                    text
                ),
                styles[
                    "PageReportNote"
                ],
            )
        )


# ============================================================
# CORE DISPLAYED PAGE PDF
# ============================================================

def generate_displayed_page_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
    mode="full_report",
):

    """
    mode:
        full_report
        visuals_only
        tables_only
    """

    captured_content = (
        captured_content
        if isinstance(
            captured_content,
            dict,
        )
        else {}
    )

    charts = (
        _normalise_items(
            captured_content.get(
                "charts",
                []
            )
        )
    )

    tables = (
        _normalise_items(
            captured_content.get(
                "tables",
                []
            )
        )
    )

    metrics = (
        _normalise_items(
            captured_content.get(
                "metrics",
                []
            )
        )
    )

    notes = (
        _normalise_items(
            captured_content.get(
                "notes",
                []
            )
        )
    )

    images = (
        _normalise_items(
            captured_content.get(
                "images",
                []
            )
        )
    )

    buffer = BytesIO()

    document = (
        SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=(
                PDF_MARGIN_MM
                * mm
            ),
            leftMargin=(
                PDF_MARGIN_MM
                * mm
            ),
            topMargin=(
                PDF_MARGIN_MM
                * mm
            ),
            bottomMargin=(
                17 * mm
            ),
            title=(
                f"{page_name} - "
                f"{DASHBOARD_TITLE}"
            ),
            author=(
                DASHBOARD_TITLE
            ),
        )
    )

    styles = (
        _styles()
    )

    story = []

    record_count = None

    if df is not None:

        try:
            record_count = len(
                df
            )
        except Exception:
            record_count = None

    _add_report_header(
        story=story,
        styles=styles,
        page_name=page_name,
        report_period=report_period,
        filter_summary=filter_summary,
        record_count=record_count,
    )

    table_width = (
        A4[0]
        - (
            PDF_MARGIN_MM
            * 2
            * mm
        )
    )

    content_added = False

    # ========================================================
    # FULL REPORT
    # ========================================================

    if mode == "full_report":

        metric_df = (
            _build_metrics_dataframe(
                metrics
            )
        )

        if not metric_df.empty:

            story.append(
                Paragraph(
                    "Displayed Key Indicators",
                    styles[
                        "PageReportSubTitle"
                    ],
                )
            )

            metric_table = (
                _build_table(
                    metric_df,
                    table_width,
                )
            )

            if metric_table is not None:

                story.append(
                    metric_table
                )

                story.append(
                    Spacer(
                        1,
                        8,
                    )
                )

                content_added = True

        for index, item in enumerate(
            charts,
            start=1,
        ):

            if content_added:
                story.append(
                    PageBreak()
                )

            if _add_chart(
                story,
                styles,
                item,
                table_width,
            ):
                content_added = True

            chart_df = (
                _get_item_dataframe(
                    item
                )
            )

            if not chart_df.empty:

                story.append(
                    Paragraph(
                        "Displayed Data",
                        styles[
                            "PageReportSubTitle"
                        ],
                    )
                )

                chart_table = (
                    _build_table(
                        chart_df,
                        table_width,
                    )
                )

                if chart_table is not None:

                    story.append(
                        chart_table
                    )

                    story.append(
                        Spacer(
                            1,
                            8,
                        )
                    )

                    content_added = True

        for item in images:

            if content_added:
                story.append(
                    PageBreak()
                )

            if _add_image(
                story,
                styles,
                item,
                table_width,
            ):
                content_added = True

        for item in tables:

            if content_added:
                story.append(
                    PageBreak()
                )

            if _add_table(
                story,
                styles,
                item,
                table_width,
            ):
                content_added = True

        _add_notes(
            story,
            styles,
            notes,
        )

    # ========================================================
    # VISUALS ONLY
    # ========================================================

    elif mode == "visuals_only":

        visual_number = 0

        for item in charts:

            if visual_number > 0:
                story.append(
                    PageBreak()
                )

            if _add_chart(
                story,
                styles,
                item,
                table_width,
            ):
                visual_number += 1
                content_added = True

        for item in images:

            if visual_number > 0:
                story.append(
                    PageBreak()
                )

            if _add_image(
                story,
                styles,
                item,
                table_width,
            ):
                visual_number += 1
                content_added = True

    # ========================================================
    # TABLES / DATA ONLY
    # ========================================================

    elif mode == "tables_only":

        metric_df = (
            _build_metrics_dataframe(
                metrics
            )
        )

        table_number = 0

        if not metric_df.empty:

            story.append(
                Paragraph(
                    "Displayed Key Indicators",
                    styles[
                        "PageReportSubTitle"
                    ],
                )
            )

            metric_table = (
                _build_table(
                    metric_df,
                    table_width,
                )
            )

            if metric_table is not None:

                story.append(
                    metric_table
                )

                table_number += 1
                content_added = True

        # Chart source data is part of
        # displayed page data.
        for item in charts:

            chart_df = (
                _get_item_dataframe(
                    item
                )
            )

            if chart_df.empty:
                continue

            if table_number > 0:

                story.append(
                    PageBreak()
                )

            title = (
                _get_item_title(
                    item,
                    "Chart Data",
                )
            )

            story.append(
                Paragraph(
                    _safe_text(
                        title
                    ),
                    styles[
                        "PageReportSubTitle"
                    ],
                )
            )

            chart_table = (
                _build_table(
                    chart_df,
                    table_width,
                )
            )

            if chart_table is not None:

                story.append(
                    chart_table
                )

                table_number += 1
                content_added = True

        for item in tables:

            if table_number > 0:

                story.append(
                    PageBreak()
                )

            if _add_table(
                story,
                styles,
                item,
                table_width,
            ):

                table_number += 1
                content_added = True

    else:

        raise ValueError(
            "Unsupported page PDF mode."
        )

    # ========================================================
    # EMPTY FALLBACK
    # ========================================================

    if not content_added:

        story.append(
            Spacer(
                1,
                10,
            )
        )

        if mode == "visuals_only":

            message = (
                "No displayed chart, graph, image, "
                "or map was captured for this page."
            )

        elif mode == "tables_only":

            message = (
                "No displayed table, chart data, "
                "or metric data was captured for this page."
            )

        else:

            message = (
                "No reportable displayed content "
                "was captured for this page."
            )

        story.append(
            Paragraph(
                message,
                styles[
                    "PageReportNote"
                ],
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
# PAGE REPORT
# ============================================================

def generate_page_report_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
):

    return generate_displayed_page_pdf(
        page_name=page_name,
        captured_content=captured_content,
        df=df,
        report_period=report_period,
        filter_summary=filter_summary,
        mode="full_report",
    )


# ============================================================
# PAGE VISUALS
# ============================================================

def generate_page_visuals_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
):

    return generate_displayed_page_pdf(
        page_name=page_name,
        captured_content=captured_content,
        df=df,
        report_period=report_period,
        filter_summary=filter_summary,
        mode="visuals_only",
    )


# ============================================================
# PAGE TABLES / DATA
# ============================================================

def generate_page_tables_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
):

    return generate_displayed_page_pdf(
        page_name=page_name,
        captured_content=captured_content,
        df=df,
        report_period=report_period,
        filter_summary=filter_summary,
        mode="tables_only",
    )


# ============================================================
# BACKWARD COMPATIBILITY
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
    Backward-compatible wrapper.

    Old callers can continue importing generate_pdf_report().
    """

    captured_content = {
        "charts": [],
        "tables": [],
        "metrics": [],
        "notes": [],
        "images": [],
    }

    if kpis:

        for key, value in (
            kpis.items()
        ):

            captured_content[
                "metrics"
            ].append(
                {
                    "label": (
                        str(key)
                        .replace(
                            "_",
                            " ",
                        )
                        .title()
                    ),
                    "value": value,
                }
            )

    if tables:

        for item in tables:

            if (
                isinstance(
                    item,
                    tuple,
                )
                and len(item) >= 2
            ):

                captured_content[
                    "tables"
                ].append(
                    {
                        "title": item[0],
                        "data": item[1],
                    }
                )

            elif isinstance(
                item,
                dict,
            ):

                captured_content[
                    "tables"
                ].append(
                    item
                )

    if charts:

        for item in charts:

            if not isinstance(
                item,
                dict,
            ):
                continue

            # Old matplotlib-style chart definitions
            # cannot be passed directly to _chart_to_png().
            # Their underlying dataframe is still retained
            # as report data.
            dataframe = (
                item.get(
                    "dataframe"
                )
            )

            if (
                isinstance(
                    dataframe,
                    pd.DataFrame,
                )
                and not dataframe.empty
            ):

                captured_content[
                    "tables"
                ].append(
                    {
                        "title": (
                            item.get(
                                "title",
                                "Chart Data",
                            )
                        ),
                        "data": dataframe,
                    }
                )

    return generate_page_report_pdf(
        page_name=report_title,
        captured_content=captured_content,
        df=df,
        report_period=report_period,
        filter_summary=filter_summary,
    )


def generate_complete_dashboard_pdf(
    pages,
    report_period=None,
    filter_summary=None,
):

    """
    Retained only for import compatibility.

    Complete Dashboard PDF is now handled by
    dashboard_pdf_export.py.
    """

    pages = pages or []

    combined = {
        "charts": [],
        "tables": [],
        "metrics": [],
        "notes": [],
        "images": [],
    }

    total_records = 0

    for page in pages:

        if not isinstance(
            page,
            dict,
        ):
            continue

        page_name = (
            page.get(
                "title",
                "Dashboard Section",
            )
        )

        page_df = page.get(
            "df"
        )

        if isinstance(
            page_df,
            pd.DataFrame,
        ):

            total_records += len(
                page_df
            )

        for item in (
            page.get(
                "tables",
                []
            )
            or []
        ):

            if (
                isinstance(
                    item,
                    tuple,
                )
                and len(item) >= 2
            ):

                combined[
                    "tables"
                ].append(
                    {
                        "title": (
                            f"{page_name} - "
                            f"{item[0]}"
                        ),
                        "data": item[1],
                    }
                )

            elif isinstance(
                item,
                dict,
            ):

                clean_item = dict(
                    item
                )

                if not clean_item.get(
                    "section_name"
                ):
                    clean_item[
                        "section_name"
                    ] = page_name

                combined[
                    "tables"
                ].append(
                    clean_item
                )

        combined[
            "charts"
        ].extend(
            page.get(
                "charts",
                []
            )
            or []
        )

        combined[
            "metrics"
        ].extend(
            page.get(
                "metrics",
                []
            )
            or []
        )

        combined[
            "notes"
        ].extend(
            page.get(
                "notes",
                []
            )
            or []
        )

        combined[
            "images"
        ].extend(
            page.get(
                "images",
                []
            )
            or []
        )

    return (
        generate_page_report_pdf(
            page_name=(
                "Complete Dashboard Report"
            ),
            captured_content=combined,
            df=pd.DataFrame(
                index=range(
                    total_records
                )
            ),
            report_period=report_period,
            filter_summary=filter_summary,
        )
    )
