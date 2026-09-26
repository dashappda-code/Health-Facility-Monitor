import io
import html

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PDF_MARGIN_MM = 12

MAX_TABLE_ROWS = 300
MAX_TABLE_COLUMNS = 14

MIN_CHART_HEIGHT_MM = 55
MAX_CHART_HEIGHT_MM = 145

MONTHLY_DISEASE_HEIGHT_MM = 88

MAX_IMAGE_HEIGHT_MM = 155


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

    try:

        return html.escape(
            str(value)
        )

    except Exception:

        return ""


# ============================================================
# SAFE FILTER SUMMARY
# ============================================================

def _normalize_filter_summary(
    filter_summary
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

        text_value = (
            filter_summary.strip()
        )

        if not text_value:
            return {}

        return {
            "Filters": text_value
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

            if value is None:
                continue

            text_value = (
                str(value).strip()
            )

            if text_value:

                result[
                    f"Filter {index}"
                ] = text_value

        return result

    try:

        return dict(
            filter_summary
        )

    except Exception:

        return {
            "Filters": str(
                filter_summary
            )
        }


# ============================================================
# GENERIC DATAFRAME CONVERSION
# ============================================================

def _to_dataframe(
    value
):

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


# ============================================================
# IMPORT DISPLAYED CHART HELPERS
# ============================================================

def _chart_to_png(
    item
):

    try:

        from displayed_chart_export import (
            _chart_to_png as helper,
        )

        return helper(
            item
        )

    except Exception:

        return None


def _is_monthly_disease_comparison(
    item
):

    try:

        from displayed_chart_export import (
            _is_monthly_disease_comparison as helper,
        )

        return bool(
            helper(
                item
            )
        )

    except Exception:

        return False


def _format_table_value(
    value
):

    try:

        from displayed_chart_export import (
            _format_table_value as helper,
        )

        return helper(
            value
        )

    except Exception:

        if value is None:
            return ""

        try:

            if pd.isna(
                value
            ):
                return ""

        except Exception:
            pass

        return str(
            value
        )


# ============================================================
# PDF STYLES
# ============================================================

def _get_pdf_styles():

    from reportlab.lib import (
        colors,
    )

    from reportlab.lib.enums import (
        TA_CENTER,
        TA_LEFT,
    )

    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )

    styles = (
        getSampleStyleSheet()
    )

    styles.add(
        ParagraphStyle(
            name="DashboardCoverTitle",
            parent=styles[
                "Title"
            ],
            fontName=(
                "Helvetica-Bold"
            ),
            fontSize=23,
            leading=28,
            alignment=TA_CENTER,
            textColor=(
                colors.HexColor(
                    "#163A5F"
                )
            ),
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name=(
                "DashboardCoverSubtitle"
            ),
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            textColor=(
                colors.HexColor(
                    "#4F5B66"
                )
            ),
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name=(
                "DashboardCoverReportTitle"
            ),
            parent=styles[
                "Normal"
            ],
            fontName=(
                "Helvetica-Bold"
            ),
            fontSize=15,
            leading=19,
            alignment=TA_CENTER,
            textColor=(
                colors.HexColor(
                    "#1F4E78"
                )
            ),
            spaceAfter=15,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardCoverInfo",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            alignment=TA_CENTER,
            textColor=(
                colors.HexColor(
                    "#444444"
                )
            ),
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardIndexTitle",
            parent=styles[
                "Heading1"
            ],
            fontName=(
                "Helvetica-Bold"
            ),
            fontSize=18,
            leading=22,
            alignment=TA_LEFT,
            textColor=(
                colors.HexColor(
                    "#163A5F"
                )
            ),
            spaceAfter=12,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardSectionTitle",
            parent=styles[
                "Heading1"
            ],
            fontName=(
                "Helvetica-Bold"
            ),
            fontSize=16,
            leading=20,
            alignment=TA_LEFT,
            textColor=(
                colors.HexColor(
                    "#163A5F"
                )
            ),
            spaceBefore=0,
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name=(
                "DashboardSubsectionTitle"
            ),
            parent=styles[
                "Heading2"
            ],
            fontName=(
                "Helvetica-Bold"
            ),
            fontSize=14,
            leading=17,
            alignment=TA_LEFT,
            textColor=(
                colors.HexColor(
                    "#163A5F"
                )
            ),
            spaceBefore=0,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardChartTitle",
            parent=styles[
                "Heading2"
            ],
            fontName=(
                "Helvetica-Bold"
            ),
            fontSize=11.5,
            leading=14,
            alignment=TA_LEFT,
            textColor=(
                colors.HexColor(
                    "#1F4E78"
                )
            ),
            spaceBefore=5,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardTableTitle",
            parent=styles[
                "Heading3"
            ],
            fontName=(
                "Helvetica-Bold"
            ),
            fontSize=9.5,
            leading=12,
            alignment=TA_LEFT,
            textColor=(
                colors.HexColor(
                    "#333333"
                )
            ),
            spaceBefore=5,
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardSmallText",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            alignment=TA_LEFT,
            textColor=(
                colors.HexColor(
                    "#555555"
                )
            ),
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardNote",
            parent=styles[
                "Normal"
            ],
            fontName=(
                "Helvetica-Oblique"
            ),
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
            textColor=(
                colors.HexColor(
                    "#666666"
                )
            ),
        )
    )

    styles.add(
        ParagraphStyle(
            name=(
                "DashboardSelectionMessage"
            ),
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            textColor=(
                colors.HexColor(
                    "#5F4B00"
                )
            ),
            backColor=(
                colors.HexColor(
                    "#FFF8D9"
                )
            ),
            borderColor=(
                colors.HexColor(
                    "#E3C95C"
                )
            ),
            borderWidth=0.7,
            borderPadding=8,
            spaceBefore=5,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardTOCEntry",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            leftIndent=12,
            firstLineIndent=-12,
            textColor=(
                colors.HexColor(
                    "#333333"
                )
            ),
            spaceAfter=5,
        )
    )

    return styles


# ============================================================
# REPORT TABLE
# ============================================================

def _build_report_table(
    df,
    table_width,
):

    from reportlab.lib import (
        colors,
    )

    from reportlab.lib.enums import (
        TA_LEFT,
    )

    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )

    from reportlab.platypus import (
        Paragraph,
        LongTable,
        TableStyle,
    )

    work_df = (
        _to_dataframe(
            df
        )
    )

    if work_df.empty:
        return None

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

    work_df.columns = (
        columns
    )

    if not columns:
        return None

    styles = (
        getSampleStyleSheet()
    )

    column_count = len(
        columns
    )

    if column_count <= 5:

        header_font_size = 7.5
        body_font_size = 7.0
        header_leading = 9
        body_leading = 8.5

    elif column_count <= 9:

        header_font_size = 6.8
        body_font_size = 6.3
        header_leading = 8
        body_leading = 7.5

    else:

        header_font_size = 6.0
        body_font_size = 5.5
        header_leading = 7
        body_leading = 6.5

    header_style = (
        ParagraphStyle(
            "ReportTableHeader",
            parent=styles[
                "Normal"
            ],
            fontName=(
                "Helvetica-Bold"
            ),
            fontSize=(
                header_font_size
            ),
            leading=(
                header_leading
            ),
            alignment=TA_LEFT,
            textColor=(
                colors.white
            ),
        )
    )

    body_style = (
        ParagraphStyle(
            "ReportTableBody",
            parent=styles[
                "Normal"
            ],
            fontName="Helvetica",
            fontSize=(
                body_font_size
            ),
            leading=(
                body_leading
            ),
            alignment=TA_LEFT,
            textColor=(
                colors.black
            ),
        )
    )

    table_data = []

    header_row = []

    for column in columns:

        header_row.append(
            Paragraph(
                _safe_text(
                    column
                ),
                header_style,
            )
        )

    table_data.append(
        header_row
    )

    for _, row in (
        work_df.iterrows()
    ):

        body_row = []

        for column in columns:

            value = row[
                column
            ]

            formatted_value = (
                _format_table_value(
                    value
                )
            )

            body_row.append(
                Paragraph(
                    _safe_text(
                        formatted_value
                    ),
                    body_style,
                )
            )

        table_data.append(
            body_row
        )

    equal_width = (
        table_width
        / column_count
    )

    col_widths = [
        equal_width
        for _ in range(
            column_count
        )
    ]

    table = LongTable(
        table_data,
        colWidths=(
            col_widths
        ),
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

    safe_filters = (
        _normalize_filter_summary(
            filter_summary
        )
    )

    if report_period:

        story.append(
            Paragraph(
                (
                    "<b>Reporting Period:</b> "
                    f"{_safe_text(report_period)}"
                ),
                styles[
                    "DashboardSmallText"
                ],
            )
        )

        story.append(
            Spacer(
                1,
                3,
            )
        )

    if not safe_filters:
        return

    story.append(
        Paragraph(
            "<b>Applied Filters</b>",
            styles[
                "DashboardTableTitle"
            ],
        )
    )

    for key, value in (
        safe_filters.items()
    ):

        if value is None:
            continue

        value_text = (
            str(value).strip()
        )

        if not value_text:
            continue

        story.append(
            Paragraph(
                (
                    f"<b>{_safe_text(key)}:"
                    f"</b> "
                    f"{_safe_text(value_text)}"
                ),
                styles[
                    "DashboardSmallText"
                ],
            )
        )

    story.append(
        Spacer(
            1,
            6,
        )
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

    from reportlab.lib.units import (
        mm,
    )

    from reportlab.platypus import (
        Paragraph,
        Spacer,
    )

    safe_filters = (
        _normalize_filter_summary(
            filter_summary
        )
    )

    story.append(
        Spacer(
            1,
            55 * mm,
        )
    )

    story.append(
        Paragraph(
            (
                "MSU Mumbai Public Health "
                "Surveillance Dashboard"
            ),
            styles[
                "DashboardCoverTitle"
            ],
        )
    )

    story.append(
        Paragraph(
            (
                "Surveillance • Monitoring • "
                "Analysis • Management"
            ),
            styles[
                "DashboardCoverSubtitle"
            ],
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
            styles[
                "DashboardCoverReportTitle"
            ],
        )
    )

    if report_period:

        story.append(
            Paragraph(
                (
                    "<b>Reporting Period:</b> "
                    f"{_safe_text(report_period)}"
                ),
                styles[
                    "DashboardCoverInfo"
                ],
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
                styles[
                    "DashboardCoverInfo"
                ],
            )
        )

        for key, value in (
            safe_filters.items()
        ):

            if value is None:
                continue

            value_text = (
                str(value).strip()
            )

            if not value_text:
                continue

            story.append(
                Paragraph(
                    (
                        f"{_safe_text(key)}: "
                        f"{_safe_text(value_text)}"
                    ),
                    styles[
                        "DashboardCoverInfo"
                    ],
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
            (
                "Prepared from the current dashboard "
                "view and selected filters."
            ),
            styles[
                "DashboardCoverInfo"
            ],
        )
    )


# ============================================================
# NEW CONTENT PAGE
# ============================================================

def _add_new_content_page(
    story,
    title,
    styles,
    parent_section=None,
):

    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        Spacer,
    )

    story.append(
        PageBreak()
    )

    if parent_section:

        story.append(
            Paragraph(
                _safe_text(
                    parent_section
                ),
                styles[
                    "DashboardSmallText"
                ],
            )
        )

        story.append(
            Spacer(
                1,
                2,
            )
        )

    story.append(
        Paragraph(
            _safe_text(
                title
            ),
            styles[
                "DashboardSubsectionTitle"
            ],
        )
    )

    story.append(
        Spacer(
            1,
            4,
        )
    )


# ============================================================
# TABLE ITEM PARSER
# ============================================================

def _parse_table_item(
    table_item,
    default_title=(
        "Management Data Table"
    ),
):

    table_title = (
        default_title
    )

    table_df = (
        pd.DataFrame()
    )

    section_name = ""
    note = ""

    if isinstance(
        table_item,
        pd.DataFrame,
    ):

        table_df = (
            table_item.copy()
        )

    elif isinstance(
        table_item,
        dict,
    ):

        table_title = (
            table_item.get(
                "title"
            )
            or table_item.get(
                "name"
            )
            or table_item.get(
                "section_name"
            )
            or default_title
        )

        section_name = (
            table_item.get(
                "section_name"
            )
            or ""
        )

        note = (
            table_item.get(
                "note"
            )
            or table_item.get(
                "message"
            )
            or ""
        )

        # ----------------------------------------------------
        # Support all table key formats.
        # Do NOT use:
        #
        # data or dataframe or df
        #
        # because DataFrames cannot safely be evaluated
        # as boolean values.
        # ----------------------------------------------------

        raw_data = (
            table_item.get(
                "data"
            )
        )

        if raw_data is None:

            raw_data = (
                table_item.get(
                    "dataframe"
                )
            )

        if raw_data is None:

            raw_data = (
                table_item.get(
                    "df"
                )
            )

        if raw_data is None:

            raw_data = (
                table_item.get(
                    "table"
                )
            )

        table_df = (
            _to_dataframe(
                raw_data
            )
        )

    else:

        table_df = (
            _to_dataframe(
                table_item
            )
        )

    return (
        table_title,
        table_df,
        section_name,
        note,
    )


# ============================================================
# ADD TABLE
# ============================================================

def _add_table_to_story(
    story,
    table_item,
    styles,
    table_width,
    parent_section=None,
):

    from reportlab.platypus import (
        Paragraph,
        Spacer,
    )

    (
        table_title,
        table_df,
        section_name,
        note,
    ) = _parse_table_item(
        table_item
    )

    if table_df.empty:
        return False

    subsection_parent = (
        section_name
        or parent_section
    )

    _add_new_content_page(
        story=story,
        title=table_title,
        styles=styles,
        parent_section=(
            subsection_parent
        ),
    )

    if note:

        story.append(
            Paragraph(
                _safe_text(
                    note
                ),
                styles[
                    "DashboardNote"
                ],
            )
        )

        story.append(
            Spacer(
                1,
                5,
            )
        )

    try:

        report_table = (
            _build_report_table(
                table_df,
                table_width,
            )
        )

        if report_table is not None:

            story.append(
                report_table
            )

            return True

    except Exception as exc:

        story.append(
            Paragraph(
                (
                    "Table could not be rendered: "
                    f"{_safe_text(exc)}"
                ),
                styles[
                    "DashboardNote"
                ],
            )
        )

    return False


# ============================================================
# CHART
# ============================================================

def _add_chart_to_story(
    story,
    item,
    styles,
    table_width,
    parent_section=None,
):

    from reportlab.lib.pagesizes import (
        A4,
    )

    from reportlab.lib.units import (
        mm,
    )

    from reportlab.platypus import (
        Image,
        Paragraph,
        Spacer,
    )

    if not isinstance(
        item,
        dict,
    ):
        return False

    chart_title = (
        item.get(
            "title"
        )
        or item.get(
            "section_name"
        )
        or "Dashboard Chart"
    )

    section_name = (
        item.get(
            "section_name"
        )
        or parent_section
        or "Dashboard Section"
    )

    _add_new_content_page(
        story=story,
        title=chart_title,
        styles=styles,
        parent_section=(
            section_name
        ),
    )

    try:

        png_bytes = (
            _chart_to_png(
                item
            )
        )

    except Exception as exc:

        png_bytes = None

        story.append(
            Paragraph(
                (
                    "<b>Chart could not "
                    "be rendered:</b> "
                    f"{_safe_text(exc)}"
                ),
                styles[
                    "DashboardNote"
                ],
            )
        )

    if png_bytes:

        try:

            from PIL import Image as (
                PILImage,
            )

            pil_image = (
                PILImage.open(
                    io.BytesIO(
                        png_bytes
                    )
                )
            )

            image_width = float(
                pil_image.size[0]
            )

            image_height = float(
                pil_image.size[1]
            )

        except Exception:

            image_width = 1000.0
            image_height = 360.0

        if image_width <= 0:

            image_width = 1000.0

        if image_height <= 0:

            image_height = 360.0

        aspect_ratio = (
            image_height
            / image_width
        )

        target_width = (
            table_width
        )

        target_height = (
            target_width
            * aspect_ratio
        )

        if (
            _is_monthly_disease_comparison(
                item
            )
        ):

            max_height = (
                MONTHLY_DISEASE_HEIGHT_MM
                * mm
            )

        else:

            max_height = (
                MAX_CHART_HEIGHT_MM
                * mm
            )

        min_height = (
            MIN_CHART_HEIGHT_MM
            * mm
        )

        page_available_height = (
            A4[1]
            - (
                PDF_MARGIN_MM
                * 2
                * mm
            )
            - (
                35 * mm
            )
        )

        max_height = min(
            max_height,
            page_available_height,
        )

        if target_height > max_height:

            target_height = (
                max_height
            )

            target_width = (
                target_height
                / aspect_ratio
            )

        if (
            target_height < min_height
            and not _is_monthly_disease_comparison(
                item
            )
        ):

            proposed_height = (
                min_height
            )

            proposed_width = (
                proposed_height
                / aspect_ratio
            )

            if (
                proposed_width
                <= table_width
            ):

                target_height = (
                    proposed_height
                )

                target_width = (
                    proposed_width
                )

        if target_width > table_width:

            target_width = (
                table_width
            )

            target_height = (
                target_width
                * aspect_ratio
            )

        try:

            image = Image(
                io.BytesIO(
                    png_bytes
                )
            )

            image.drawWidth = (
                target_width
            )

            image.drawHeight = (
                target_height
            )

            image.hAlign = (
                "CENTER"
            )

            story.append(
                image
            )

        except Exception as exc:

            story.append(
                Paragraph(
                    (
                        "Chart image could not "
                        "be added: "
                        f"{_safe_text(exc)}"
                    ),
                    styles[
                        "DashboardNote"
                    ],
                )
            )

    else:

        story.append(
            Paragraph(
                (
                    "Chart image was not available "
                    "for PDF export."
                ),
                styles[
                    "DashboardNote"
                ],
            )
        )

    # --------------------------------------------------------
    # Chart data
    # --------------------------------------------------------

    raw_chart_data = (
        item.get(
            "data"
        )
    )

    if raw_chart_data is None:

        raw_chart_data = (
            item.get(
                "dataframe"
            )
        )

    if raw_chart_data is None:

        raw_chart_data = (
            item.get(
                "table"
            )
        )

    chart_df = (
        _to_dataframe(
            raw_chart_data
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
                "Data Table",
                styles[
                    "DashboardTableTitle"
                ],
            )
        )

        try:

            table = (
                _build_report_table(
                    chart_df,
                    table_width,
                )
            )

            if table is not None:

                story.append(
                    table
                )

        except Exception as exc:

            story.append(
                Paragraph(
                    (
                        "Data table could not "
                        "be rendered: "
                        f"{_safe_text(exc)}"
                    ),
                    styles[
                        "DashboardNote"
                    ],
                )
            )

    return True


# ============================================================
# IMAGE / MAP ITEM
# ============================================================

def _extract_image_item(
    image_item
):

    title = (
        "Dashboard Image"
    )

    section_name = ""
    caption = ""
    image_bytes = None

    if isinstance(
        image_item,
        bytes,
    ):

        image_bytes = (
            image_item
        )

    elif isinstance(
        image_item,
        bytearray,
    ):

        image_bytes = bytes(
            image_item
        )

    elif isinstance(
        image_item,
        io.BytesIO,
    ):

        try:

            current_position = (
                image_item.tell()
            )

        except Exception:

            current_position = 0

        try:

            image_item.seek(0)

            image_bytes = (
                image_item.read()
            )

            image_item.seek(
                current_position
            )

        except Exception:

            image_bytes = None

    elif isinstance(
        image_item,
        dict,
    ):

        title = (
            image_item.get(
                "title"
            )
            or image_item.get(
                "name"
            )
            or image_item.get(
                "section_name"
            )
            or "Dashboard Image"
        )

        section_name = (
            image_item.get(
                "section_name"
            )
            or ""
        )

        caption = (
            image_item.get(
                "caption"
            )
            or image_item.get(
                "note"
            )
            or ""
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # Do not use:
        #
        # data or bytes or image or png
        #
        # because some image objects / arrays cannot be
        # evaluated as boolean values.
        # ----------------------------------------------------

        raw_image = (
            image_item.get(
                "data"
            )
        )

        if raw_image is None:

            raw_image = (
                image_item.get(
                    "bytes"
                )
            )

        if raw_image is None:

            raw_image = (
                image_item.get(
                    "image"
                )
            )

        if raw_image is None:

            raw_image = (
                image_item.get(
                    "png"
                )
            )

        if isinstance(
            raw_image,
            bytes,
        ):

            image_bytes = (
                raw_image
            )

        elif isinstance(
            raw_image,
            bytearray,
        ):

            image_bytes = bytes(
                raw_image
            )

        elif isinstance(
            raw_image,
            io.BytesIO,
        ):

            try:

                current_position = (
                    raw_image.tell()
                )

            except Exception:

                current_position = 0

            try:

                raw_image.seek(0)

                image_bytes = (
                    raw_image.read()
                )

                raw_image.seek(
                    current_position
                )

            except Exception:

                image_bytes = None

        else:

            # PIL image support
            try:

                from PIL import (
                    Image as PILImage,
                )

                if isinstance(
                    raw_image,
                    PILImage.Image,
                ):

                    buffer = (
                        io.BytesIO()
                    )

                    raw_image.save(
                        buffer,
                        format="PNG",
                    )

                    image_bytes = (
                        buffer.getvalue()
                    )

            except Exception:
                pass

    return (
        title,
        section_name,
        caption,
        image_bytes,
    )


# ============================================================
# ADD IMAGE / MAP
# ============================================================

def _add_image_to_story(
    story,
    image_item,
    styles,
    table_width,
    parent_section=None,
):

    from reportlab.lib.units import (
        mm,
    )

    from reportlab.platypus import (
        Image,
        Paragraph,
        Spacer,
    )

    (
        title,
        section_name,
        caption,
        image_bytes,
    ) = _extract_image_item(
        image_item
    )

    if image_bytes is None:
        return False

    if not isinstance(
        image_bytes,
        (bytes, bytearray),
    ):
        return False

    if len(image_bytes) == 0:
        return False

    _add_new_content_page(
        story=story,
        title=title,
        styles=styles,
        parent_section=(
            section_name
            or parent_section
        ),
    )

    if caption:

        story.append(
            Paragraph(
                _safe_text(
                    caption
                ),
                styles[
                    "DashboardNote"
                ],
            )
        )

        story.append(
            Spacer(
                1,
                5,
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

        image_width = (
            table_width
        )

        if original_width > 0:

            image_height = (
                image_width
                * original_height
                / original_width
            )

        else:

            image_height = (
                80 * mm
            )

        max_height = (
            MAX_IMAGE_HEIGHT_MM
            * mm
        )

        if image_height > max_height:

            scale = (
                max_height
                / image_height
            )

            image_height = (
                max_height
            )

            image_width = (
                image_width
                * scale
            )

        image.drawWidth = (
            image_width
        )

        image.drawHeight = (
            image_height
        )

        image.hAlign = (
            "CENTER"
        )

        story.append(
            image
        )

        return True

    except Exception as exc:

        story.append(
            Paragraph(
                (
                    "Image or map could not "
                    "be rendered: "
                    f"{_safe_text(exc)}"
                ),
                styles[
                    "DashboardNote"
                ],
            )
        )

        return False


# ============================================================
# METRICS
# ============================================================

def _add_metrics_to_story(
    story,
    metrics,
    styles,
    table_width,
    parent_section,
):

    if not metrics:
        return False

    rows = []

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

        value = (
            item.get(
                "value",
                "",
            )
        )

        delta = (
            item.get(
                "delta",
                "",
            )
        )

        rows.append(
            {
                "Indicator": label,
                "Value": value,
                "Change": delta,
            }
        )

    if not rows:
        return False

    metric_df = (
        pd.DataFrame(
            rows
        )
    )

    return _add_table_to_story(
        story=story,
        table_item={
            "title": (
                f"{parent_section} – "
                "Displayed Indicators"
            ),
            "section_name": (
                parent_section
            ),
            "data": metric_df,
            "dataframe": metric_df,
        },
        styles=styles,
        table_width=(
            table_width
        ),
        parent_section=(
            parent_section
        ),
    )


# ============================================================
# FOOTER
# ============================================================

def _add_footer(
    canvas,
    doc,
):

    from reportlab.lib import (
        colors,
    )

    from reportlab.lib.units import (
        mm,
    )

    page_number = (
        canvas.getPageNumber()
    )

    canvas.saveState()

    page_width = (
        doc.pagesize[0]
    )

    canvas.setStrokeColor(
        colors.HexColor(
            "#D0D7DE"
        )
    )

    canvas.setLineWidth(
        0.4
    )

    canvas.line(
        12 * mm,
        8 * mm,
        page_width
        - (12 * mm),
        8 * mm,
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
        12 * mm,
        4.5 * mm,
        (
            "MSU Mumbai Public Health "
            "Surveillance Dashboard"
        ),
    )

    canvas.drawRightString(
        page_width
        - (12 * mm),
        4.5 * mm,
        f"Page {page_number}",
    )

    canvas.restoreState()


# ============================================================
# DOCUMENT CLASS
# ============================================================

def _make_dashboard_document(
    buffer,
    pagesize,
    margin,
):

    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        PageTemplate,
    )

    class DashboardDocTemplate(
        BaseDocTemplate
    ):

        def __init__(
            self,
            filename,
            **kwargs,
        ):

            super().__init__(
                filename,
                **kwargs,
            )

            frame = Frame(
                margin,
                margin,
                pagesize[0]
                - 2 * margin,
                pagesize[1]
                - 2 * margin,
                id="normal",
            )

            self.addPageTemplates(
                [
                    PageTemplate(
                        id="normal",
                        frames=frame,
                        onPage=(
                            _add_footer
                        ),
                    )
                ]
            )

    return DashboardDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=margin,
        leftMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
        title=(
            "MSU Mumbai Public Health "
            "Surveillance Dashboard"
        ),
        author=(
            "MSU Mumbai Public Health "
            "Surveillance Dashboard"
        ),
        subject=(
            "Complete Dashboard Report"
        ),
    )


# ============================================================
# TABLE OF CONTENTS
# ============================================================

def _add_table_of_contents(
    story,
    styles,
    pages,
):

    from reportlab.platypus import (
        Paragraph,
        Spacer,
    )

    story.append(
        Paragraph(
            "Table of Contents",
            styles[
                "DashboardIndexTitle"
            ],
        )
    )

    story.append(
        Paragraph(
            "Dashboard Sections",
            styles[
                "DashboardTableTitle"
            ],
        )
    )

    story.append(
        Spacer(
            1,
            4,
        )
    )

    if not pages:

        story.append(
            Paragraph(
                (
                    "No dashboard sections "
                    "were captured."
                ),
                styles[
                    "DashboardSmallText"
                ],
            )
        )

        return

    for index, page in enumerate(
        pages,
        start=1,
    ):

        if isinstance(
            page,
            dict,
        ):

            page_title = (
                page.get(
                    "title"
                )
                or page.get(
                    "page_name"
                )
                or page.get(
                    "name"
                )
                or (
                    "Dashboard Section "
                    f"{index}"
                )
            )

        else:

            page_title = (
                str(page)
            )

        story.append(
            Paragraph(
                (
                    f"<b>{index}.</b> "
                    f"{_safe_text(page_title)}"
                ),
                styles[
                    "DashboardTOCEntry"
                ],
            )
        )


# ============================================================
# NORMALISE PAGE COLLECTION
# ============================================================

def _get_page_collection(
    page,
    primary_key,
    alternate_key=None,
):

    if not isinstance(
        page,
        dict,
    ):

        return []

    value = page.get(
        primary_key
    )

    if (
        value is None
        and alternate_key
    ):

        value = page.get(
            alternate_key
        )

    if value is None:
        return []

    if isinstance(
        value,
        (list, tuple),
    ):

        return list(
            value
        )

    return [
        value
    ]


# ============================================================
# GENERATE CAPTURED DASHBOARD PDF
# ============================================================

def generate_captured_dashboard_pdf(
    pages,
    report_period=None,
    filter_summary=None,
):

    from reportlab.lib.pagesizes import (
        A4,
    )

    from reportlab.lib.units import (
        mm,
    )

    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        Spacer,
    )

    if pages is None:
        pages = []

    pages = list(
        pages
    )

    buffer = (
        io.BytesIO()
    )

    page_width, _ = (
        A4
    )

    margin = (
        PDF_MARGIN_MM
        * mm
    )

    doc = (
        _make_dashboard_document(
            buffer=buffer,
            pagesize=A4,
            margin=margin,
        )
    )

    styles = (
        _get_pdf_styles()
    )

    story = []

    # ========================================================
    # COVER PAGE
    # ========================================================

    _add_cover_page(
        story=story,
        styles=styles,
        report_period=(
            report_period
        ),
        filter_summary=(
            filter_summary
        ),
    )

    # ========================================================
    # TABLE OF CONTENTS
    # ========================================================

    story.append(
        PageBreak()
    )

    _add_table_of_contents(
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

        if isinstance(
            page,
            dict,
        ):

            page_title = (
                page.get(
                    "title"
                )
                or page.get(
                    "page_name"
                )
                or page.get(
                    "name"
                )
                or (
                    "Dashboard Section "
                    f"{page_index}"
                )
            )

            captured_charts = (
                _get_page_collection(
                    page,
                    "charts",
                    "captured_charts",
                )
            )

            additional_tables = (
                _get_page_collection(
                    page,
                    "tables",
                    "additional_tables",
                )
            )

            metrics = (
                _get_page_collection(
                    page,
                    "metrics",
                )
            )

            notes = (
                _get_page_collection(
                    page,
                    "notes",
                )
            )

            images = (
                _get_page_collection(
                    page,
                    "images",
                    "maps",
                )
            )

            selection_required = (
                bool(
                    page.get(
                        "selection_required",
                        False,
                    )
                )
            )

            selection_message = (
                page.get(
                    "selection_message"
                )
                or page.get(
                    "empty_message"
                )
                or (
                    "Additional selection is required "
                    "in the dashboard before this "
                    "analysis can be displayed."
                )
            )

        else:

            page_title = (
                str(page)
            )

            captured_charts = []
            additional_tables = []
            metrics = []
            notes = []
            images = []

            selection_required = (
                False
            )

            selection_message = ""

        # ====================================================
        # PAGE INTRODUCTION
        # ====================================================

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                _safe_text(
                    page_title
                ),
                styles[
                    "DashboardSectionTitle"
                ],
            )
        )

        story.append(
            Paragraph(
                (
                    f"<b>Section "
                    f"{page_index}</b>"
                ),
                styles[
                    "DashboardSmallText"
                ],
            )
        )

        story.append(
            Spacer(
                1,
                5,
            )
        )

        if page_index == 1:

            _add_filter_summary(
                story=story,
                styles=styles,
                report_period=(
                    report_period
                ),
                filter_summary=(
                    filter_summary
                ),
            )

        # ====================================================
        # NOTES
        # ====================================================

        valid_notes = []

        for note in notes:

            if note is None:
                continue

            if isinstance(
                note,
                dict,
            ):

                note_text = (
                    note.get(
                        "text"
                    )
                    or note.get(
                        "message"
                    )
                    or note.get(
                        "note"
                    )
                    or ""
                )

            else:

                note_text = (
                    str(note)
                )

            note_text = (
                str(
                    note_text
                ).strip()
            )

            if note_text:

                valid_notes.append(
                    note_text
                )

        if valid_notes:

            story.append(
                Paragraph(
                    "Section Notes",
                    styles[
                        "DashboardTableTitle"
                    ],
                )
            )

            for note_text in (
                valid_notes
            ):

                story.append(
                    Paragraph(
                        _safe_text(
                            note_text
                        ),
                        styles[
                            "DashboardNote"
                        ],
                    )
                )

                story.append(
                    Spacer(
                        1,
                        3,
                    )
                )

        # ====================================================
        # CONTENT CHECK
        # ====================================================

        has_tables = bool(
            additional_tables
        )

        has_charts = bool(
            captured_charts
        )

        has_metrics = bool(
            metrics
        )

        has_images = bool(
            images
        )

        has_content = (
            has_tables
            or has_charts
            or has_metrics
            or has_images
        )

        if (
            selection_required
            and not has_content
        ):

            story.append(
                Spacer(
                    1,
                    6,
                )
            )

            story.append(
                Paragraph(
                    "<b>Selection Required</b>",
                    styles[
                        "DashboardTableTitle"
                    ],
                )
            )

            story.append(
                Paragraph(
                    _safe_text(
                        selection_message
                    ),
                    styles[
                        "DashboardSelectionMessage"
                    ],
                )
            )

            continue

        if not has_content:

            story.append(
                Spacer(
                    1,
                    6,
                )
            )

            story.append(
                Paragraph(
                    (
                        "No reportable chart, table, "
                        "metric, or map was captured "
                        "for this section."
                    ),
                    styles[
                        "DashboardNote"
                    ],
                )
            )

            continue

        # ====================================================
        # METRICS
        # ====================================================

        if metrics:

            _add_metrics_to_story(
                story=story,
                metrics=metrics,
                styles=styles,
                table_width=(
                    table_width
                ),
                parent_section=(
                    page_title
                ),
            )

        # ====================================================
        # TABLES
        # ====================================================

        for table_item in (
            additional_tables
        ):

            _add_table_to_story(
                story=story,
                table_item=(
                    table_item
                ),
                styles=styles,
                table_width=(
                    table_width
                ),
                parent_section=(
                    page_title
                ),
            )

        # ====================================================
        # CHARTS
        # ====================================================

        for chart_item in (
            captured_charts
        ):

            if not isinstance(
                chart_item,
                dict,
            ):
                continue

            _add_chart_to_story(
                story=story,
                item=chart_item,
                styles=styles,
                table_width=(
                    table_width
                ),
                parent_section=(
                    page_title
                ),
            )

        # ====================================================
        # IMAGES / MAPS
        # ====================================================

        for image_item in (
            images
        ):

            _add_image_to_story(
                story=story,
                image_item=(
                    image_item
                ),
                styles=styles,
                table_width=(
                    table_width
                ),
                parent_section=(
                    page_title
                ),
            )

    # ========================================================
    # NO PAGES
    # ========================================================

    if not pages:

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                (
                    "No dashboard sections "
                    "were captured."
                ),
                styles[
                    "DashboardSectionTitle"
                ],
            )
        )

        story.append(
            Paragraph(
                (
                    "Please generate the Complete "
                    "Dashboard PDF again after the "
                    "dashboard pages have loaded."
                ),
                styles[
                    "DashboardSmallText"
                ],
            )
        )

    # ========================================================
    # BUILD
    # ========================================================

    doc.build(
        story
    )

    buffer.seek(
        0
    )

    return (
        buffer.getvalue()
    )


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def generate_dashboard_pdf(
    pages,
    report_period=None,
    filter_summary=None,
):

    return (
        generate_captured_dashboard_pdf(
            pages=pages,
            report_period=(
                report_period
            ),
            filter_summary=(
                filter_summary
            ),
        )
    )
