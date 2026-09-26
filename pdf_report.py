import io
import html
import re
from datetime import datetime

import pandas as pd
import streamlit as st

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

MAX_CHART_HEIGHT_MM = 145
MAX_IMAGE_HEIGHT_MM = 150

DEFAULT_SECTION_NAME = "Dashboard Section"


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


def _clean_text(value):

    text = _safe_text(
        value
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


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
        return _safe_text(
            value
        )


def _safe_filename(value):

    value = _safe_text(
        value
    )

    value = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        value,
    )

    value = value.strip(
        "_"
    )

    if not value:
        value = "Dashboard_Report"

    return value


# ============================================================
# NORMALISE FILTER SUMMARY
# ============================================================

def _normalise_filter_summary(
    filter_summary,
):

    if filter_summary is None:
        return {}

    if isinstance(
        filter_summary,
        dict,
    ):
        return filter_summary

    if isinstance(
        filter_summary,
        str,
    ):

        text = filter_summary.strip()

        if not text:
            return {}

        return {
            "Filters": text
        }

    if isinstance(
        filter_summary,
        (list, tuple),
    ):

        result = {}

        for index, value in enumerate(
            filter_summary,
            start=1,
        ):

            text = _safe_text(
                value
            ).strip()

            if text:

                result[
                    f"Filter {index}"
                ] = text

        return result

    try:
        return dict(
            filter_summary
        )
    except Exception:
        return {
            "Filters": _safe_text(
                filter_summary
            )
        }


# ============================================================
# NORMALISE CAPTURED CONTENT
# ============================================================

def _normalise_captured_content(
    captured_content,
):

    result = {
        "charts": [],
        "tables": [],
        "metrics": [],
        "notes": [],
        "images": [],
    }

    if not isinstance(
        captured_content,
        dict,
    ):
        return result

    for key in result:

        value = captured_content.get(
            key,
            [],
        )

        if isinstance(
            value,
            list,
        ):
            result[key] = value

        elif value is not None:
            result[key] = [
                value
            ]

    return result


# ============================================================
# SECTION NAME
# ============================================================

def _get_item_section(
    item,
    fallback=DEFAULT_SECTION_NAME,
):

    if not isinstance(
        item,
        dict,
    ):
        return fallback

    section = (
        item.get(
            "section_name"
        )
        or item.get(
            "section"
        )
        or item.get(
            "title"
        )
        or fallback
    )

    section = _clean_text(
        section
    )

    return (
        section
        or fallback
    )


# ============================================================
# SECTION KEY
# ============================================================

def _section_key(value):

    text = _clean_text(
        value
    ).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


# ============================================================
# GROUP CONTENT BY SECTION
# ============================================================

def _group_content_by_section(
    captured_content,
):

    content = (
        _normalise_captured_content(
            captured_content
        )
    )

    sections = []
    section_lookup = {}

    def ensure_section(
        section_name
    ):

        clean_name = (
            _clean_text(
                section_name
            )
            or DEFAULT_SECTION_NAME
        )

        key = _section_key(
            clean_name
        )

        if key not in section_lookup:

            section = {
                "name": clean_name,
                "metrics": [],
                "notes": [],
                "charts": [],
                "tables": [],
                "images": [],
            }

            section_lookup[
                key
            ] = section

            sections.append(
                section
            )

        return section_lookup[
            key
        ]

    # --------------------------------------------------------
    # IMPORTANT
    #
    # The existing capture registry stores content by type,
    # not as one mixed ordered list.
    #
    # We therefore preserve the first-seen SECTION order and
    # keep all related content together inside that section.
    # --------------------------------------------------------

    capture_types = (
        "metrics",
        "notes",
        "charts",
        "tables",
        "images",
    )

    for content_type in capture_types:

        for item in content.get(
            content_type,
            [],
        ):

            section_name = (
                _get_item_section(
                    item
                )
            )

            section = ensure_section(
                section_name
            )

            section[
                content_type
            ].append(
                item
            )

    return sections


# ============================================================
# AVAILABLE SECTIONS
# ============================================================

def get_page_report_sections(
    captured_content,
):

    sections = (
        _group_content_by_section(
            captured_content
        )
    )

    return [
        section["name"]
        for section in sections
        if section.get(
            "name"
        )
    ]


# ============================================================
# FILTER SECTIONS
# ============================================================

def _filter_sections(
    sections,
    include_sections=None,
    exclude_sections=None,
):

    include_keys = None

    if include_sections:

        include_keys = {
            _section_key(
                value
            )
            for value in include_sections
            if _clean_text(
                value
            )
        }

    exclude_keys = {
        _section_key(
            value
        )
        for value in (
            exclude_sections
            or []
        )
        if _clean_text(
            value
        )
    }

    result = []

    for section in sections:

        name = section.get(
            "name",
            DEFAULT_SECTION_NAME,
        )

        key = _section_key(
            name
        )

        if (
            include_keys is not None
            and key not in include_keys
        ):
            continue

        if key in exclude_keys:
            continue

        result.append(
            section
        )

    return result


# ============================================================
# PDF STYLES
# ============================================================

def _get_styles():

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
            name="ReportDashboardTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#163A5F"
            ),
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportDashboardSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor(
                "#666666"
            ),
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportPageTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            alignment=TA_LEFT,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSectionNumber",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor(
                "#6B7280"
            ),
            spaceAfter=3,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor(
                "#163A5F"
            ),
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportItemTitle",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor(
                "#1F4E78"
            ),
            spaceBefore=3,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor(
                "#555555"
            ),
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportNormal",
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
            name="ReportNote",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor(
                "#4B5563"
            ),
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportTableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8,
            alignment=TA_LEFT,
            textColor=colors.white,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportTableBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=6,
            leading=7.5,
            alignment=TA_LEFT,
            textColor=colors.black,
        )
    )

    return styles


# ============================================================
# FOOTER
# ============================================================

def _add_footer(
    canvas,
    doc,
):

    from reportlab.lib import colors
    from reportlab.lib.units import mm

    canvas.saveState()

    page_width = doc.pagesize[0]

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
        10 * mm,
        page_width - 12 * mm,
        10 * mm,
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
        6 * mm,
        DASHBOARD_TITLE,
    )

    canvas.drawRightString(
        page_width - 12 * mm,
        6 * mm,
        f"Page {canvas.getPageNumber()}",
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
):

    from reportlab.platypus import (
        Paragraph,
        Spacer,
    )

    story.append(
        Paragraph(
            _safe_html(
                DASHBOARD_TITLE
            ),
            styles[
                "ReportDashboardTitle"
            ],
        )
    )

    story.append(
        Paragraph(
            _safe_html(
                DASHBOARD_SUBTITLE
            ),
            styles[
                "ReportDashboardSubtitle"
            ],
        )
    )

    story.append(
        Paragraph(
            _safe_html(
                page_name
            ),
            styles[
                "ReportPageTitle"
            ],
        )
    )

    story.append(
        Paragraph(
            "<b>Report Type:</b> Dynamic Page Report",
            styles[
                "ReportSmall"
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
                "ReportSmall"
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
                    "ReportSmall"
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
                    "ReportSmall"
                ],
            )
        )

    filters = (
        _normalise_filter_summary(
            filter_summary
        )
    )

    if filters:

        story.append(
            Spacer(
                1,
                4,
            )
        )

        story.append(
            Paragraph(
                "<b>Applied Filters</b>",
                styles[
                    "ReportItemTitle"
                ],
            )
        )

        for key, value in (
            filters.items()
        ):

            if value in (
                None,
                "",
                "All",
                "All records",
            ):
                continue

            story.append(
                Paragraph(
                    (
                        f"<b>{_safe_html(key)}:</b> "
                        f"{_safe_html(value)}"
                    ),
                    styles[
                        "ReportSmall"
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
# PREPARE TABLE
# ============================================================

def _prepare_table_dataframe(
    dataframe,
):

    df = _to_dataframe(
        dataframe
    )

    if df.empty:
        return pd.DataFrame()

    if len(df) > MAX_TABLE_ROWS:

        df = (
            df
            .head(
                MAX_TABLE_ROWS
            )
            .copy()
        )

    if (
        len(df.columns)
        > MAX_TABLE_COLUMNS
    ):

        df = (
            df.iloc[
                :,
                :MAX_TABLE_COLUMNS,
            ]
            .copy()
        )

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
# BUILD TABLE
# ============================================================

def _build_table(
    dataframe,
    available_width,
    styles,
):

    from reportlab.lib import colors
    from reportlab.platypus import (
        Paragraph,
        LongTable,
        TableStyle,
    )

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

    header = []

    for column in df.columns:

        header.append(
            Paragraph(
                _safe_html(
                    column
                ),
                styles[
                    "ReportTableHeader"
                ],
            )
        )

    data.append(
        header
    )

    for _, row in (
        df.iterrows()
    ):

        cells = []

        for value in (
            row.tolist()
        ):

            cells.append(
                Paragraph(
                    _safe_html(
                        _format_table_value(
                            value
                        )
                    ),
                    styles[
                        "ReportTableBody"
                    ],
                )
            )

        data.append(
            cells
        )

    column_width = (
        available_width
        / column_count
    )

    table = LongTable(
        data,
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
# METRICS
# ============================================================

def _add_metrics(
    story,
    metrics,
    styles,
    available_width,
):

    if not metrics:
        return

    rows = []

    for item in metrics:

        if not isinstance(
            item,
            dict,
        ):
            continue

        rows.append(
            {
                "Indicator": (
                    item.get(
                        "label"
                    )
                    or item.get(
                        "title"
                    )
                    or "Metric"
                ),
                "Value": item.get(
                    "value",
                    "",
                ),
                "Change": item.get(
                    "delta",
                    "",
                ),
            }
        )

    if not rows:
        return

    metric_df = pd.DataFrame(
        rows
    )

    story.append(
        Paragraph(
            "Displayed Indicators",
            styles[
                "ReportItemTitle"
            ],
        )
    )

    table = _build_table(
        metric_df,
        available_width,
        styles,
    )

    if table is not None:

        story.append(
            table
        )


# ============================================================
# NOTES
# ============================================================

def _add_notes(
    story,
    notes,
    styles,
):

    from reportlab.platypus import (
        Paragraph,
        Spacer,
    )

    if not notes:
        return

    valid_notes = []

    for item in notes:

        if isinstance(
            item,
            dict,
        ):

            text = (
                item.get(
                    "text"
                )
                or item.get(
                    "message"
                )
                or item.get(
                    "note"
                )
                or ""
            )

        else:

            text = item

        text = _clean_text(
            text
        )

        if not text:
            continue

        if len(text) > MAX_NOTE_LENGTH:

            text = (
                text[
                    :MAX_NOTE_LENGTH
                ]
                + "..."
            )

        valid_notes.append(
            text
        )

    if not valid_notes:
        return

    story.append(
        Paragraph(
            "Displayed Notes / Messages",
            styles[
                "ReportItemTitle"
            ],
        )
    )

    for text in valid_notes:

        story.append(
            Paragraph(
                _safe_html(
                    text
                ),
                styles[
                    "ReportNote"
                ],
            )
        )

        story.append(
            Spacer(
                1,
                3,
            )
        )


# ============================================================
# CHART DATA
# ============================================================

def _get_chart_dataframe(
    item,
):

    if not isinstance(
        item,
        dict,
    ):
        return pd.DataFrame()

    data = item.get(
        "data"
    )

    if data is None:

        data = item.get(
            "dataframe"
        )

    if data is None:

        data = item.get(
            "table"
        )

    return _to_dataframe(
        data
    )


# ============================================================
# ADD CHART
# ============================================================

def _add_chart(
    story,
    item,
    styles,
    available_width,
    available_height,
    include_chart_data=True,
):

    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        Paragraph,
        Spacer,
    )

    if not isinstance(
        item,
        dict,
    ):
        return

    title = (
        item.get(
            "title"
        )
        or item.get(
            "section_name"
        )
        or "Dashboard Chart"
    )

    story.append(
        Paragraph(
            _safe_html(
                title
            ),
            styles[
                "ReportItemTitle"
            ],
        )
    )

    png_bytes = (
        _chart_to_png(
            item
        )
    )

    if png_bytes:

        max_height = min(
            MAX_CHART_HEIGHT_MM * mm,
            available_height * 0.58,
        )

        try:

            width, height = (
                _get_chart_image_size(
                    item,
                    png_bytes,
                    available_width,
                    max_height,
                )
            )

            image = Image(
                io.BytesIO(
                    png_bytes
                )
            )

            image.drawWidth = width
            image.drawHeight = height
            image.hAlign = "CENTER"

            story.append(
                image
            )

        except Exception as exc:

            story.append(
                Paragraph(
                    (
                        "Chart image could not "
                        "be added: "
                        + _safe_html(
                            exc
                        )
                    ),
                    styles[
                        "ReportNote"
                    ],
                )
            )

    else:

        story.append(
            Paragraph(
                "Chart image was not available for PDF export.",
                styles[
                    "ReportNote"
                ],
            )
        )

    if include_chart_data:

        chart_df = (
            _get_chart_dataframe(
                item
            )
        )

        if not chart_df.empty:

            story.append(
                Spacer(
                    1,
                    6,
                )
            )

            story.append(
                Paragraph(
                    "Chart Data",
                    styles[
                        "ReportItemTitle"
                    ],
                )
            )

            table = _build_table(
                chart_df,
                available_width,
                styles,
            )

            if table is not None:

                story.append(
                    table
                )

    story.append(
        Spacer(
            1,
            8,
        )
    )


# ============================================================
# ADD DISPLAYED TABLE
# ============================================================

def _add_displayed_table(
    story,
    item,
    styles,
    available_width,
):

    from reportlab.platypus import (
        Paragraph,
        Spacer,
    )

    if not isinstance(
        item,
        dict,
    ):

        dataframe = _to_dataframe(
            item
        )

        title = "Displayed Data"

    else:

        title = (
            item.get(
                "title"
            )
            or "Displayed Data"
        )

        data = item.get(
            "data"
        )

        if data is None:

            data = item.get(
                "dataframe"
            )

        dataframe = (
            _to_dataframe(
                data
            )
        )

    if dataframe.empty:
        return

    story.append(
        Paragraph(
            _safe_html(
                title
            ),
            styles[
                "ReportItemTitle"
            ],
        )
    )

    table = _build_table(
        dataframe,
        available_width,
        styles,
    )

    if table is not None:

        story.append(
            table
        )

        story.append(
            Spacer(
                1,
                8,
            )
        )


# ============================================================
# IMAGE BYTES
# ============================================================

def _get_image_bytes(
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
        io.BytesIO,
    ):

        try:

            position = item.tell()

        except Exception:

            position = 0

        try:

            item.seek(0)

            value = item.read()

            item.seek(
                position
            )

            return value

        except Exception:

            return None

    if not isinstance(
        item,
        dict,
    ):
        return None

    value = item.get(
        "data"
    )

    if value is None:

        value = item.get(
            "bytes"
        )

    if value is None:

        value = item.get(
            "image"
        )

    if isinstance(
        value,
        bytes,
    ):
        return value

    if isinstance(
        value,
        bytearray,
    ):
        return bytes(
            value
        )

    if isinstance(
        value,
        io.BytesIO,
    ):

        try:

            position = value.tell()

        except Exception:

            position = 0

        try:

            value.seek(0)

            result = value.read()

            value.seek(
                position
            )

            return result

        except Exception:

            return None

    return None


# ============================================================
# ADD IMAGE / MAP
# ============================================================

def _add_image(
    story,
    item,
    styles,
    available_width,
    available_height,
):

    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        Paragraph,
        Spacer,
    )

    image_bytes = (
        _get_image_bytes(
            item
        )
    )

    if not image_bytes:
        return

    if isinstance(
        item,
        dict,
    ):

        title = (
            item.get(
                "title"
            )
            or item.get(
                "section_name"
            )
            or "Dashboard Image / Map"
        )

        caption = (
            item.get(
                "caption"
            )
            or ""
        )

    else:

        title = (
            "Dashboard Image / Map"
        )

        caption = ""

    story.append(
        Paragraph(
            _safe_html(
                title
            ),
            styles[
                "ReportItemTitle"
            ],
        )
    )

    try:

        image = Image(
            io.BytesIO(
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
            available_width
        )

        if original_width > 0:

            draw_height = (
                draw_width
                * original_height
                / original_width
            )

        else:

            draw_height = (
                90 * mm
            )

        max_height = min(
            MAX_IMAGE_HEIGHT_MM * mm,
            available_height * 0.62,
        )

        if draw_height > max_height:

            scale = (
                max_height
                / draw_height
            )

            draw_height = (
                max_height
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

        image.hAlign = "CENTER"

        story.append(
            image
        )

    except Exception as exc:

        story.append(
            Paragraph(
                (
                    "Image / map could not "
                    "be rendered: "
                    + _safe_html(
                        exc
                    )
                ),
                styles[
                    "ReportNote"
                ],
            )
        )

    if caption:

        story.append(
            Paragraph(
                _safe_html(
                    caption
                ),
                styles[
                    "ReportSmall"
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
# SECTION HAS CONTENT
# ============================================================

def _section_has_content(
    section,
    include_metrics=True,
    include_notes=True,
    include_charts=True,
    include_tables=True,
    include_images=True,
):

    checks = []

    if include_metrics:
        checks.append(
            bool(
                section.get(
                    "metrics"
                )
            )
        )

    if include_notes:
        checks.append(
            bool(
                section.get(
                    "notes"
                )
            )
        )

    if include_charts:
        checks.append(
            bool(
                section.get(
                    "charts"
                )
            )
        )

    if include_tables:
        checks.append(
            bool(
                section.get(
                    "tables"
                )
            )
        )

    if include_images:
        checks.append(
            bool(
                section.get(
                    "images"
                )
            )
        )

    return any(
        checks
    )


# ============================================================
# GENERATE STANDARD PAGE REPORT
# ============================================================

def generate_page_report_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
    include_sections=None,
    exclude_sections=None,
    include_metrics=True,
    include_notes=True,
    include_charts=True,
    include_chart_data=True,
    include_tables=True,
    include_images=True,
):

    """
    Standard dynamic PDF generator for any dashboard page.

    Every captured section starts on a new PDF page.

    Content is grouped by section so charts, tables,
    metrics, notes and images/maps belonging to the same
    dashboard section remain together.

    include_sections:
        Optional list of section names to include.

    exclude_sections:
        Optional list of section names to exclude.
    """

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        PageBreak,
        KeepTogether,
    )

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=PDF_MARGIN_MM * mm,
        leftMargin=PDF_MARGIN_MM * mm,
        topMargin=PDF_MARGIN_MM * mm,
        bottomMargin=16 * mm,
        title=(
            f"{page_name} - "
            f"{DASHBOARD_TITLE}"
        ),
        author=DASHBOARD_TITLE,
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
        - 10 * mm
    )

    styles = (
        _get_styles()
    )

    sections = (
        _group_content_by_section(
            captured_content
        )
    )

    sections = (
        _filter_sections(
            sections,
            include_sections=(
                include_sections
            ),
            exclude_sections=(
                exclude_sections
            ),
        )
    )

    filtered_sections = []

    for section in sections:

        if _section_has_content(
            section,
            include_metrics=(
                include_metrics
            ),
            include_notes=(
                include_notes
            ),
            include_charts=(
                include_charts
            ),
            include_tables=(
                include_tables
            ),
            include_images=(
                include_images
            ),
        ):

            filtered_sections.append(
                section
            )

    sections = (
        filtered_sections
    )

    story = []

    record_count = None

    if isinstance(
        df,
        pd.DataFrame,
    ):

        record_count = len(
            df
        )

    # ========================================================
    # PAGE REPORT INTRODUCTION
    # ========================================================

    _add_report_header(
        story=story,
        styles=styles,
        page_name=page_name,
        report_period=report_period,
        filter_summary=filter_summary,
        record_count=record_count,
    )

    story.append(
        Paragraph(
            (
                "<b>Included sections:</b> "
                f"{len(sections)}"
            ),
            styles[
                "ReportSmall"
            ],
        )
    )

    if sections:

        for index, section in enumerate(
            sections,
            start=1,
        ):

            story.append(
                Paragraph(
                    (
                        f"{index}. "
                        + _safe_html(
                            section[
                                "name"
                            ]
                        )
                    ),
                    styles[
                        "ReportSmall"
                    ],
                )
            )

    else:

        story.append(
            Paragraph(
                (
                    "No reportable content was "
                    "captured for the selected "
                    "page and report options."
                ),
                styles[
                    "ReportNormal"
                ],
            )
        )

    # ========================================================
    # SECTIONS
    # ========================================================

    for section_number, section in enumerate(
        sections,
        start=1,
    ):

        # ----------------------------------------------------
        # IMPORTANT:
        # EVERY NEW DASHBOARD SECTION STARTS ON NEW PDF PAGE.
        # ----------------------------------------------------

        story.append(
            PageBreak()
        )

        section_name = (
            section.get(
                "name"
            )
            or DEFAULT_SECTION_NAME
        )

        # ----------------------------------------------------
        # Keep section number + heading + small spacer
        # together.
        #
        # Because section already starts on a new page,
        # the heading can no longer be orphaned at the
        # bottom of the previous page.
        # ----------------------------------------------------

        section_header = [
            Paragraph(
                (
                    f"Section "
                    f"{section_number}"
                ),
                styles[
                    "ReportSectionNumber"
                ],
            ),
            Paragraph(
                _safe_html(
                    section_name
                ),
                styles[
                    "ReportSectionTitle"
                ],
            ),
            Spacer(
                1,
                4,
            ),
        ]

        story.append(
            KeepTogether(
                section_header
            )
        )

        # ====================================================
        # METRICS
        # ====================================================

        if include_metrics:

            _add_metrics(
                story=story,
                metrics=section.get(
                    "metrics",
                    [],
                ),
                styles=styles,
                available_width=(
                    available_width
                ),
            )

            if section.get(
                "metrics"
            ):

                story.append(
                    Spacer(
                        1,
                        8,
                    )
                )

        # ====================================================
        # NOTES
        # ====================================================

        if include_notes:

            _add_notes(
                story=story,
                notes=section.get(
                    "notes",
                    [],
                ),
                styles=styles,
            )

        # ====================================================
        # CHARTS
        # ====================================================

        if include_charts:

            for chart in section.get(
                "charts",
                [],
            ):

                _add_chart(
                    story=story,
                    item=chart,
                    styles=styles,
                    available_width=(
                        available_width
                    ),
                    available_height=(
                        available_height
                    ),
                    include_chart_data=(
                        include_chart_data
                    ),
                )

        # ====================================================
        # DISPLAYED TABLES
        # ====================================================

        if include_tables:

            for table_item in section.get(
                "tables",
                [],
            ):

                _add_displayed_table(
                    story=story,
                    item=table_item,
                    styles=styles,
                    available_width=(
                        available_width
                    ),
                )

        # ====================================================
        # IMAGES / MAPS
        # ====================================================

        if include_images:

            for image_item in section.get(
                "images",
                [],
            ):

                _add_image(
                    story=story,
                    item=image_item,
                    styles=styles,
                    available_width=(
                        available_width
                    ),
                    available_height=(
                        available_height
                    ),
                )

    # ========================================================
    # FALLBACK
    # ========================================================

    if (
        not sections
        and isinstance(
            df,
            pd.DataFrame,
        )
        and not df.empty
        and include_tables
    ):

        story.append(
            PageBreak()
        )

        story.append(
            KeepTogether(
                [
                    Paragraph(
                        "Section 1",
                        styles[
                            "ReportSectionNumber"
                        ],
                    ),
                    Paragraph(
                        "Filtered Dataset",
                        styles[
                            "ReportSectionTitle"
                        ],
                    ),
                    Spacer(
                        1,
                        4,
                    ),
                ]
            )
        )

        story.append(
            Paragraph(
                (
                    "No separate displayed report "
                    "content was captured. The current "
                    "filtered dataset is included below."
                ),
                styles[
                    "ReportSmall"
                ],
            )
        )

        table = _build_table(
            df,
            available_width,
            styles,
        )

        if table is not None:

            story.append(
                table
            )

    document.build(
        story,
        onFirstPage=_add_footer,
        onLaterPages=_add_footer,
    )

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# VISUALS PDF
# ============================================================

def generate_page_visuals_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
    include_sections=None,
    exclude_sections=None,
):

    return generate_page_report_pdf(
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
        include_sections=(
            include_sections
        ),
        exclude_sections=(
            exclude_sections
        ),
        include_metrics=False,
        include_notes=False,
        include_charts=True,
        include_chart_data=False,
        include_tables=False,
        include_images=True,
    )


# ============================================================
# TABLES PDF
# ============================================================

def generate_page_tables_pdf(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
    include_sections=None,
    exclude_sections=None,
):

    return generate_page_report_pdf(
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
        include_sections=(
            include_sections
        ),
        exclude_sections=(
            exclude_sections
        ),
        include_metrics=True,
        include_notes=False,
        include_charts=False,
        include_chart_data=False,
        include_tables=True,
        include_images=False,
    )


# ============================================================
# COMMON DOWNLOAD CONTROL
# ============================================================

def render_page_pdf_download(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
    key_prefix=None,
    show_section_selector=True,
    expanded=False,
):

    """
    ONE STANDARD DOWNLOAD CONTROL FOR ALL DASHBOARD PAGES.

    Use the same function on:
        Overview
        Charts & Trends
        Demographics
        Ward Analysis
        Map
        Data Explorer
        Prediction
        Validation & KPI
        Drill-down & Export
        and future pages.
    """

    if key_prefix is None:

        key_prefix = (
            _safe_filename(
                page_name
            ).lower()
        )

    sections = (
        get_page_report_sections(
            captured_content
        )
    )

    # Remove duplicate section names while preserving order.

    unique_sections = []

    seen = set()

    for section in sections:

        key = _section_key(
            section
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(
            key
        )

        unique_sections.append(
            section
        )

    with st.expander(
        "📄 Download Page PDF Report",
        expanded=expanded,
    ):

        st.caption(
            (
                "Generate a PDF from the content "
                "currently displayed on this dashboard page."
            )
        )

        selected_sections = (
            unique_sections
        )

        # ====================================================
        # SECTION SELECTOR
        # ====================================================

        if (
            show_section_selector
            and unique_sections
        ):

            st.markdown(
                "**Sections to include**"
            )

            selected_sections = (
                st.multiselect(
                    (
                        "Select report sections"
                    ),
                    options=(
                        unique_sections
                    ),
                    default=(
                        unique_sections
                    ),
                    key=(
                        f"{key_prefix}_"
                        "pdf_sections"
                    ),
                    help=(
                        "Unselect large or unnecessary "
                        "sections to reduce PDF size."
                    ),
                )
            )

        elif not unique_sections:

            st.info(
                (
                    "No named report sections were "
                    "captured. If filtered data is "
                    "available, it can still be used "
                    "as a fallback."
                )
            )

        # ====================================================
        # CONTENT OPTIONS
        # ====================================================

        st.markdown(
            "**Content to include**"
        )

        col1, col2, col3 = (
            st.columns(3)
        )

        with col1:

            include_charts = (
                st.checkbox(
                    "Charts / Graphs",
                    value=True,
                    key=(
                        f"{key_prefix}_"
                        "pdf_charts"
                    ),
                )
            )

            include_metrics = (
                st.checkbox(
                    "Metrics / KPIs",
                    value=True,
                    key=(
                        f"{key_prefix}_"
                        "pdf_metrics"
                    ),
                )
            )

        with col2:

            include_tables = (
                st.checkbox(
                    "Displayed Tables",
                    value=True,
                    key=(
                        f"{key_prefix}_"
                        "pdf_tables"
                    ),
                )
            )

            include_chart_data = (
                st.checkbox(
                    "Chart Data Tables",
                    value=True,
                    key=(
                        f"{key_prefix}_"
                        "pdf_chart_data"
                    ),
                    disabled=(
                        not include_charts
                    ),
                )
            )

        with col3:

            include_images = (
                st.checkbox(
                    "Images / Maps",
                    value=True,
                    key=(
                        f"{key_prefix}_"
                        "pdf_images"
                    ),
                )
            )

            include_notes = (
                st.checkbox(
                    "Notes / Messages",
                    value=True,
                    key=(
                        f"{key_prefix}_"
                        "pdf_notes"
                    ),
                )
            )

        # ====================================================
        # SUMMARY
        # ====================================================

        if unique_sections:

            st.caption(
                (
                    f"{len(selected_sections)} of "
                    f"{len(unique_sections)} "
                    "section(s) selected."
                )
            )

        # ====================================================
        # GENERATE PDF
        # ====================================================

        try:

            pdf_bytes = (
                generate_page_report_pdf(
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
                    include_sections=(
                        selected_sections
                        if unique_sections
                        else None
                    ),
                    include_metrics=(
                        include_metrics
                    ),
                    include_notes=(
                        include_notes
                    ),
                    include_charts=(
                        include_charts
                    ),
                    include_chart_data=(
                        include_chart_data
                        and include_charts
                    ),
                    include_tables=(
                        include_tables
                    ),
                    include_images=(
                        include_images
                    ),
                )
            )

            filename = (
                _safe_filename(
                    page_name
                )
                + "_Page_Report.pdf"
            )

            st.download_button(
                label=(
                    "⬇️ Download Page PDF Report"
                ),
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
                key=(
                    f"{key_prefix}_"
                    "download_page_pdf"
                ),
            )

        except Exception as exc:

            st.error(
                (
                    "Page PDF report could not "
                    "be generated."
                )
            )

            with st.expander(
                "Technical details"
            ):

                st.code(
                    str(exc)
                )


# ============================================================
# ALIAS
# ============================================================

def render_page_pdf_download_controls(
    page_name,
    captured_content,
    df=None,
    report_period=None,
    filter_summary=None,
    key_prefix=None,
    show_section_selector=True,
    expanded=False,
):

    return render_page_pdf_download(
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
        key_prefix=(
            key_prefix
        ),
        show_section_selector=(
            show_section_selector
        ),
        expanded=expanded,
    )
