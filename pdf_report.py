import io
import html
from datetime import datetime

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
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
    LongTable,
    PageBreak,
    Image,
    KeepTogether,
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

MAX_NOTE_LENGTH = 3000


# ============================================================
# SAFE HELPERS
# ============================================================

def _safe_text(value):

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    try:
        return str(value)
    except Exception:
        return ""


def _safe_html(value):

    return html.escape(
        _safe_text(value)
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
            .reset_index(
                drop=True
            )
        )

    try:
        return pd.DataFrame(
            value
        )
    except Exception:
        return pd.DataFrame()


def _format_number(value):

    try:
        return f"{int(value):,}"
    except Exception:
        return _safe_text(value)


# ============================================================
# NORMALISE CAPTURED CONTENT
# ============================================================

def _normalise_captured_content(
    captured_content,
):

    if not isinstance(
        captured_content,
        dict,
    ):
        captured_content = {}

    result = {}

    for key in (
        "charts",
        "tables",
        "metrics",
        "notes",
        "images",
    ):

        value = captured_content.get(
            key,
            [],
        )

        if isinstance(
            value,
            list,
        ):
            result[key] = value
        else:
            result[key] = []

    return result


# ============================================================
# STYLES
# ============================================================

def _styles():

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="PageReportDashboardTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#17365D"
            ),
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#666666"
            ),
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=17,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceBefore=3,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor(
                "#1F4E78"
            ),
            spaceBefore=7,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportItemTitle",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor(
                "#374151"
            ),
            spaceBefore=4,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor(
                "#4B5563"
            ),
            spaceAfter=3,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor(
                "#222222"
            ),
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportNote",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor(
                "#374151"
            ),
            leftIndent=4,
            rightIndent=4,
            spaceBefore=3,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportTableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8,
            textColor=colors.white,
            alignment=TA_LEFT,
        )
    )

    styles.add(
        ParagraphStyle(
            name="PageReportTableBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=6,
            leading=7.5,
            textColor=colors.black,
            alignment=TA_LEFT,
        )
    )

    return styles


# ============================================================
# HEADER / FOOTER
# ============================================================

def _header_footer(
    canvas,
    doc,
):

    canvas.saveState()

    page_width, _ = (
        doc.pagesize
    )

    canvas.setStrokeColor(
        colors.HexColor(
            "#D1D5DB"
        )
    )

    canvas.setLineWidth(
        0.4
    )

    canvas.line(
        12 * mm,
        11 * mm,
        page_width - 12 * mm,
        11 * mm,
    )

    canvas.setFont(
        "Helvetica",
        6.8,
    )

    canvas.setFillColor(
        colors.HexColor(
            "#666666"
        )
    )

    canvas.drawString(
        12 * mm,
        7 * mm,
        DASHBOARD_TITLE,
    )

    canvas.drawRightString(
        page_width - 12 * mm,
        7 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


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
    report_type="Page Report",
):

    story.append(
        Paragraph(
            _safe_html(
                DASHBOARD_TITLE
            ),
            styles[
                "PageReportDashboardTitle"
            ],
        )
    )

    story.append(
        Paragraph(
            _safe_html(
                DASHBOARD_SUBTITLE
            ),
            styles[
                "PageReportSubtitle"
            ],
        )
    )

    story.append(
        Paragraph(
            _safe_html(
                page_name
            ),
            styles[
                "PageReportTitle"
            ],
        )
    )

    story.append(
        Paragraph(
            _safe_html(
                report_type
            ),
            styles[
                "PageReportSmall"
            ],
        )
    )

    story.append(
        Paragraph(
            (
                "<b>Generated:</b> "
                + _safe_html(
                    datetime.now().strftime(
                        "%d-%m-%Y %H:%M"
                    )
                )
            ),
            styles[
                "PageReportSmall"
            ],
        )
    )

    if report_period:

        story.append(
            Paragraph(
                (
                    "<b>Reporting Period:</b> "
                    + _safe_html(
                        report_period
                    )
                ),
                styles[
                    "PageReportSmall"
                ],
            )
        )

    if filter_summary:

        story.append(
            Paragraph(
                (
                    "<b>Filter Scope:</b> "
                    + _safe_html(
                        filter_summary
                    )
                ),
                styles[
                    "PageReportSmall"
                ],
            )
        )

    if record_count is not None:

        story.append(
            Paragraph(
                (
                    "<b>Records in current scope:</b> "
                    + _safe_html(
                        _format_number(
                            record_count
                        )
                    )
                ),
                styles[
                    "PageReportSmall"
                ],
            )
        )

    story.append(
        Spacer(
            1,
            7,
        )
    )


# ============================================================
# METRICS
# ============================================================

def _build_metrics_table(
    metrics,
    available_width,
    styles,
):

    if not metrics:
        return None

    cells = []

    for item in metrics:

        if not isinstance(
            item,
            dict,
        ):
            continue

        label = (
            item.get(
                "label"
            )
            or item.get(
                "title"
            )
            or "Metric"
        )

        value = item.get(
            "value",
            "",
        )

        delta = item.get(
            "delta"
        )

        text = (
            "<b>"
            + _safe_html(
                label
            )
            + "</b><br/>"
            + "<font size='11'>"
            + _safe_html(
                value
            )
            + "</font>"
        )

        if delta not in (
            None,
            "",
        ):

            text += (
                "<br/><font size='7'>"
                + _safe_html(
                    delta
                )
                + "</font>"
            )

        cells.append(
            Paragraph(
                text,
                styles[
                    "PageReportNormal"
                ],
            )
        )

    if not cells:
        return None

    columns = min(
        4,
        len(cells),
    )

    rows = []

    for start in range(
        0,
        len(cells),
        columns,
    ):

        row = cells[
            start:
            start + columns
        ]

        while len(row) < columns:
            row.append("")

        rows.append(
            row
        )

    col_width = (
        available_width
        / columns
    )

    table = Table(
        rows,
        colWidths=[
            col_width
            for _ in range(
                columns
            )
        ],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(
                        "#F3F6F9"
                    ),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor(
                        "#C7D5E0"
                    ),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor(
                        "#D8E1E8"
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
                    6,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    return table


# ============================================================
# TABLE PREPARATION
# ============================================================

def _prepare_table_dataframe(
    value,
):

    df = _to_dataframe(
        value
    )

    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    if len(df) > MAX_TABLE_ROWS:

        df = df.head(
            MAX_TABLE_ROWS
        )

    if (
        len(df.columns)
        > MAX_TABLE_COLUMNS
    ):

        df = df.iloc[
            :,
            :MAX_TABLE_COLUMNS,
        ]

    for column in df.columns:

        try:

            if (
                pd.api.types
                .is_datetime64_any_dtype(
                    df[column]
                )
            ):

                df[column] = (
                    df[column]
                    .dt.strftime(
                        "%d-%m-%Y"
                    )
                )

            else:

                df[column] = (
                    df[column]
                    .apply(
                        _format_table_value
                    )
                )

        except Exception:

            df[column] = (
                df[column]
                .astype(str)
            )

    return df


# ============================================================
# TABLE CREATION
# ============================================================

def _build_table(
    dataframe,
    available_width,
    styles,
):

    df = (
        _prepare_table_dataframe(
            dataframe
        )
    )

    if df.empty:
        return None

    column_count = len(
        df.columns
    )

    if column_count <= 0:
        return None

    data = []

    header_row = []

    for column in df.columns:

        header_row.append(
            Paragraph(
                _safe_html(
                    column
                ),
                styles[
                    "PageReportTableHeader"
                ],
            )
        )

    data.append(
        header_row
    )

    for _, row in (
        df.iterrows()
    ):

        row_items = []

        for value in (
            row.tolist()
        ):

            row_items.append(
                Paragraph(
                    _safe_html(
                        _format_table_value(
                            value
                        )
                    ),
                    styles[
                        "PageReportTableBody"
                    ],
                )
            )

        data.append(
            row_items
        )

    col_width = (
        available_width
        / column_count
    )

    table = LongTable(
        data,
        colWidths=[
            col_width
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
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor(
                        "#B7C9D6"
                    ),
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
                            "#F8FAFC"
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
# ADD NOTES
# ============================================================

def _add_notes(
    story,
    notes,
    styles,
):

    if not notes:
        return

    story.append(
        Paragraph(
            "Displayed Notes / Messages",
            styles[
                "PageReportSection"
            ],
        )
    )

    for item in notes:

        if not isinstance(
            item,
            dict,
        ):
            continue

        text = _safe_text(
            item.get(
                "text",
                "",
            )
        ).strip()

        if not text:
            continue

        if len(text) > MAX_NOTE_LENGTH:

            text = (
                text[
                    :MAX_NOTE_LENGTH
                ]
                + "..."
            )

        note_type = (
            _safe_text(
                item.get(
                    "note_type",
                    "info",
                )
            )
            .strip()
            .title()
        )

        section_name = (
            _safe_text(
                item.get(
                    "section_name",
                    "",
                )
            )
            .strip()
        )

        heading = note_type

        if section_name:

            heading = (
                f"{note_type} – "
                f"{section_name}"
            )

        story.append(
            Paragraph(
                (
                    "<b>"
                    + _safe_html(
                        heading
                    )
                    + "</b><br/>"
                    + _safe_html(
                        text
                    )
                ),
                styles[
                    "PageReportNote"
                ],
            )
        )


# ============================================================
# ADD CHARTS
# ============================================================

def _add_charts(
    story,
    charts,
    styles,
    available_width,
    available_height,
):

    if not charts:
        return

    story.append(
        Paragraph(
            "Displayed Charts / Graphs",
            styles[
                "PageReportSection"
            ],
        )
    )

    chart_number = 0

    for item in charts:

        if not isinstance(
            item,
            dict,
        ):
            continue

        png_bytes = (
            _chart_to_png(
                item
            )
        )

        if not png_bytes:
            continue

        chart_number += 1

        title = (
            item.get(
                "title"
            )
            or item.get(
                "section_name"
            )
            or f"Chart {chart_number}"
        )

        section_name = (
            item.get(
                "section_name"
            )
            or ""
        )

        story.append(
            Paragraph(
                (
                    f"{chart_number}. "
                    + _safe_html(
                        title
                    )
                ),
                styles[
                    "PageReportItemTitle"
                ],
            )
        )

        if (
            section_name
            and section_name
            != title
        ):

            story.append(
                Paragraph(
                    (
                        "<b>Section:</b> "
                        + _safe_html(
                            section_name
                        )
                    ),
                    styles[
                        "PageReportSmall"
                    ],
                )
            )

        max_chart_height = (
            min(
                available_height
                * 0.58,
                135 * mm,
            )
        )

        chart_width, chart_height = (
            _get_chart_image_size(
                item,
                png_bytes,
                available_width,
                max_chart_height,
            )
        )

        image = Image(
            io.BytesIO(
                png_bytes
            )
        )

        image.drawWidth = (
            chart_width
        )

        image.drawHeight = (
            chart_height
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
                9,
            )
        )


# ============================================================
# ADD IMAGES
# ============================================================

def _get_image_dimensions(
    image_bytes,
):

    try:

        from PIL import Image as PILImage

        image = PILImage.open(
            io.BytesIO(
                image_bytes
            )
        )

        width, height = (
            image.size
        )

        return (
            float(width),
            float(height),
        )

    except Exception:

        return (
            None,
            None,
        )


def _add_images(
    story,
    images,
    styles,
    available_width,
    available_height,
):

    if not images:
        return

    valid_images = []

    for item in images:

        if not isinstance(
            item,
            dict,
        ):
            continue

        image_bytes = (
            item.get(
                "data"
            )
            or item.get(
                "bytes"
            )
        )

        if image_bytes:

            valid_images.append(
                item
            )

    if not valid_images:
        return

    story.append(
        Paragraph(
            "Displayed Images / Maps",
            styles[
                "PageReportSection"
            ],
        )
    )

    for index, item in enumerate(
        valid_images,
        start=1,
    ):

        image_bytes = (
            item.get(
                "data"
            )
            or item.get(
                "bytes"
            )
        )

        title = (
            item.get(
                "title"
            )
            or item.get(
                "section_name"
            )
            or f"Image {index}"
        )

        caption = (
            item.get(
                "caption",
                "",
            )
        )

        story.append(
            Paragraph(
                (
                    f"{index}. "
                    + _safe_html(
                        title
                    )
                ),
                styles[
                    "PageReportItemTitle"
                ],
            )
        )

        width, height = (
            _get_image_dimensions(
                image_bytes
            )
        )

        max_width = (
            available_width
        )

        max_height = min(
            available_height
            * 0.60,
            145 * mm,
        )

        if (
            width
            and height
            and width > 0
            and height > 0
        ):

            ratio = (
                height
                / width
            )

            draw_width = (
                max_width
            )

            draw_height = (
                draw_width
                * ratio
            )

            if (
                draw_height
                > max_height
            ):

                draw_height = (
                    max_height
                )

                draw_width = (
                    draw_height
                    / ratio
                )

        else:

            draw_width = (
                max_width
            )

            draw_height = (
                90 * mm
            )

        image = Image(
            io.BytesIO(
                image_bytes
            )
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

        if caption:

            story.append(
                Paragraph(
                    _safe_html(
                        caption
                    ),
                    styles[
                        "PageReportSmall"
                    ],
                )
            )

        story.append(
            Spacer(
                1,
                9,
            )
        )


# ============================================================
# ADD CAPTURED TABLES
# ============================================================

def _add_tables(
    story,
    tables,
    styles,
    available_width,
):

    if not tables:
        return

    valid_tables = []

    for item in tables:

        if not isinstance(
            item,
            dict,
        ):
            continue

        data = (
            item.get(
                "data"
            )
        )

        if data is None:

            data = (
                item.get(
                    "dataframe"
                )
            )

        dataframe = (
            _to_dataframe(
                data
            )
        )

        if dataframe.empty:
            continue

        valid_tables.append(
            (
                item,
                dataframe,
            )
        )

    if not valid_tables:
        return

    story.append(
        Paragraph(
            "Displayed Tables / Data",
            styles[
                "PageReportSection"
            ],
        )
    )

    for index, (
        item,
        dataframe,
    ) in enumerate(
        valid_tables,
        start=1,
    ):

        title = (
            item.get(
                "title"
            )
            or item.get(
                "section_name"
            )
            or f"Displayed Data {index}"
        )

        story.append(
            Paragraph(
                (
                    f"{index}. "
                    + _safe_html(
                        title
                    )
                ),
                styles[
                    "PageReportItemTitle"
                ],
            )
        )

        table = (
            _build_table(
                dataframe,
                available_width,
                styles,
            )
        )

        if table is not None:

            story.append(
                table
            )

            story.append(
                Spacer(
                    1,
                    9,
                )
            )


# ============================================================
# FALLBACK DATA
# ============================================================

def _add_fallback_dataframe(
    story,
    df,
    styles,
    available_width,
):

    if (
        df is None
        or df.empty
    ):
        return

    story.append(
        Paragraph(
            "Filtered Dataset",
            styles[
                "PageReportSection"
            ],
        )
    )

    story.append(
        Paragraph(
            (
                "No separate displayed table was captured "
                "for this page. The current filtered dataset "
                "is included below."
            ),
            styles[
                "PageReportSmall"
            ],
        )
    )

    table = (
        _build_table(
            df,
            available_width,
            styles,
        )
    )

    if table is not None:

        story.append(
            table
        )


# ============================================================
# GENERIC PAGE PDF BUILDER
# ============================================================

def _generate_page_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
    mode="full",
):

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
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
            16 * mm
        ),
        title=(
            f"{page_name} - "
            f"{DASHBOARD_TITLE}"
        ),
        author=DASHBOARD_TITLE,
    )

    page_width, page_height = (
        A4
    )

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

    styles = (
        _styles()
    )

    content = (
        _normalise_captured_content(
            captured_content
        )
    )

    charts = content[
        "charts"
    ]

    tables = content[
        "tables"
    ]

    metrics = content[
        "metrics"
    ]

    notes = content[
        "notes"
    ]

    images = content[
        "images"
    ]

    story = []

    if mode == "full":

        report_type = (
            "Complete Page Report"
        )

    elif mode == "visuals":

        report_type = (
            "Page Visuals Report"
        )

    else:

        report_type = (
            "Page Tables / Data Report"
        )

    record_count = None

    if isinstance(
        df,
        pd.DataFrame,
    ):

        record_count = len(
            df
        )

    _add_report_header(
        story=story,
        styles=styles,
        page_name=page_name,
        report_period=report_period,
        filter_summary=filter_summary,
        record_count=record_count,
        report_type=report_type,
    )

    # ========================================================
    # FULL PAGE REPORT
    # ========================================================

    if mode == "full":

        if metrics:

            story.append(
                Paragraph(
                    "Displayed Metrics",
                    styles[
                        "PageReportSection"
                    ],
                )
            )

            metric_table = (
                _build_metrics_table(
                    metrics,
                    available_width,
                    styles,
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

        _add_notes(
            story,
            notes,
            styles,
        )

        _add_charts(
            story,
            charts,
            styles,
            available_width,
            available_height,
        )

        _add_images(
            story,
            images,
            styles,
            available_width,
            available_height,
        )

        _add_tables(
            story,
            tables,
            styles,
            available_width,
        )

        if (
            not tables
            and isinstance(
                df,
                pd.DataFrame,
            )
            and not df.empty
        ):

            _add_fallback_dataframe(
                story,
                df,
                styles,
                available_width,
            )

    # ========================================================
    # VISUALS ONLY
    # ========================================================

    elif mode == "visuals":

        _add_charts(
            story,
            charts,
            styles,
            available_width,
            available_height,
        )

        _add_images(
            story,
            images,
            styles,
            available_width,
            available_height,
        )

        if (
            not charts
            and not images
        ):

            story.append(
                Paragraph(
                    (
                        "No chart, graph, image or static map "
                        "was captured from this dashboard page."
                    ),
                    styles[
                        "PageReportNormal"
                    ],
                )
            )

    # ========================================================
    # TABLES / DATA ONLY
    # ========================================================

    elif mode == "tables":

        _add_tables(
            story,
            tables,
            styles,
            available_width,
        )

        if (
            not tables
            and isinstance(
                df,
                pd.DataFrame,
            )
            and not df.empty
        ):

            _add_fallback_dataframe(
                story,
                df,
                styles,
                available_width,
            )

        elif (
            not tables
            and (
                df is None
                or not isinstance(
                    df,
                    pd.DataFrame,
                )
                or df.empty
            )
        ):

            story.append(
                Paragraph(
                    (
                        "No displayed table or data was "
                        "captured from this dashboard page."
                    ),
                    styles[
                        "PageReportNormal"
                    ],
                )
            )

    # ========================================================
    # COMPLETION NOTE
    # ========================================================

    story.append(
        Spacer(
            1,
            12,
        )
    )

    story.append(
        Paragraph(
            (
                "Report generated from the dashboard "
                "content available under the selected "
                "filter scope."
            ),
            styles[
                "PageReportSmall"
            ],
        )
    )

    document.build(
        story,
        onFirstPage=(
            _header_footer
        ),
        onLaterPages=(
            _header_footer
        ),
    )

    buffer.seek(
        0
    )

    return buffer.getvalue()


# ============================================================
# PUBLIC FUNCTION
# FULL PAGE REPORT
# ============================================================

def generate_page_report_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
):

    """
    Generate the complete report for the currently
    displayed dashboard page.

    Includes:
        - captured metrics
        - captured notes/messages
        - captured Altair charts
        - captured st.image images
        - captured displayed tables/dataframes
        - fallback filtered data when no displayed
          table was captured
    """

    return _generate_page_pdf(
        page_name=page_name,
        captured_content=(
            captured_content
        ),
        df=df,
        report_period=(
            report_period
        ),
        filter_summary=(
            filter_summary
        ),
        mode="full",
    )


# ============================================================
# PUBLIC FUNCTION
# VISUALS ONLY
# ============================================================

def generate_page_visuals_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
):

    """
    Generate a PDF containing only the captured
    visual content from the current dashboard page.

    Includes:
        - Altair charts / graphs
        - st.image images
        - static map images when captured through st.image
    """

    return _generate_page_pdf(
        page_name=page_name,
        captured_content=(
            captured_content
        ),
        df=df,
        report_period=(
            report_period
        ),
        filter_summary=(
            filter_summary
        ),
        mode="visuals",
    )


# ============================================================
# PUBLIC FUNCTION
# TABLES / DATA ONLY
# ============================================================

def generate_page_tables_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
):

    """
    Generate a PDF containing only displayed
    tables/data from the current dashboard page.

    If no displayed table was captured, the current
    filtered dataset is used as a fallback.
    """

    return _generate_page_pdf(
        page_name=page_name,
        captured_content=(
            captured_content
        ),
        df=df,
        report_period=(
            report_period
        ),
        filter_summary=(
            filter_summary
        ),
        mode="tables",
    )
