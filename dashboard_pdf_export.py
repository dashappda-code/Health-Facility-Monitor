from io import BytesIO
from datetime import datetime
from contextlib import contextmanager

import pandas as pd

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
# INTERNAL STATE
# ============================================================

_CAPTURE_STATE = {
    "active": False,
    "pages": [],
    "current_page": None,
    "current_section": None,
}


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
            name="DPE_Title",
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
            name="DPE_Subtitle",
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
            name="DPE_PageTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            spaceBefore=3,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DPE_Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=5,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DPE_Small",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DPE_TableTitle",
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

    width, _ = A4

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
# CAPTURE CONTROL
# ============================================================

def reset_capture():
    _CAPTURE_STATE["pages"] = []
    _CAPTURE_STATE["current_page"] = None
    _CAPTURE_STATE["current_section"] = None


def start_capture():
    reset_capture()
    _CAPTURE_STATE["active"] = True


def stop_capture():
    _CAPTURE_STATE["active"] = False


def get_captured_pages():
    return list(
        _CAPTURE_STATE.get("pages", [])
    )


@contextmanager
def capture_dashboard():
    """
    Context manager used while rendering dashboard
    sections for Complete Dashboard PDF capture.

    This does not change the existing Phase 3
    displayed_chart_export.py system.
    """

    start_capture()

    try:
        yield _CAPTURE_STATE

    finally:
        stop_capture()


# ============================================================
# PAGE MANAGEMENT
# ============================================================

def start_page(
    title,
    page_number=None,
    total_pages=None,
):
    """
    Start a dashboard PDF page.

    Example:

        start_page("Overview")
    """

    if not _CAPTURE_STATE["active"]:
        return

    page = {
        "title": _safe_text(title),
        "page_number": page_number,
        "total_pages": total_pages,
        "charts": [],
        "tables": [],
        "kpis": {},
        "images": [],
        "notes": [],
    }

    _CAPTURE_STATE["pages"].append(page)

    _CAPTURE_STATE["current_page"] = page
    _CAPTURE_STATE["current_section"] = None


def end_page():
    if not _CAPTURE_STATE["active"]:
        return

    _CAPTURE_STATE["current_page"] = None
    _CAPTURE_STATE["current_section"] = None


def start_section(title):
    if not _CAPTURE_STATE["active"]:
        return

    _CAPTURE_STATE["current_section"] = _safe_text(
        title
    )


def add_note(text):
    if not _CAPTURE_STATE["active"]:
        return

    page = _CAPTURE_STATE.get(
        "current_page"
    )

    if page is None:
        return

    page["notes"].append(
        _safe_text(text)
    )


# ============================================================
# DATA CAPTURE
# ============================================================

def add_kpis(kpis):
    if not _CAPTURE_STATE["active"]:
        return

    page = _CAPTURE_STATE.get(
        "current_page"
    )

    if page is None:
        return

    if not kpis:
        return

    page["kpis"].update(
        kpis
    )


def add_table(
    dataframe,
    title=None,
):
    if not _CAPTURE_STATE["active"]:
        return

    if (
        dataframe is None
        or not isinstance(
            dataframe,
            pd.DataFrame,
        )
        or dataframe.empty
    ):
        return

    page = _CAPTURE_STATE.get(
        "current_page"
    )

    if page is None:
        return

    page["tables"].append(
        {
            "title": _safe_text(
                title
                or _CAPTURE_STATE.get(
                    "current_section"
                )
                or "Data Table"
            ),
            "dataframe": dataframe.copy(),
        }
    )


def add_chart(
    chart,
    title=None,
    dataframe=None,
):
    """
    Store an already-created chart.

    chart may be an Altair chart object.

    The actual visual conversion can be handled
    later by the export layer.
    """

    if not _CAPTURE_STATE["active"]:
        return

    page = _CAPTURE_STATE.get(
        "current_page"
    )

    if page is None:
        return

    chart_title = (
        title
        or _CAPTURE_STATE.get(
            "current_section"
        )
        or "Chart"
    )

    page["charts"].append(
        {
            "title": _safe_text(
                chart_title
            ),
            "chart": chart,
            "dataframe": (
                dataframe.copy()
                if isinstance(
                    dataframe,
                    pd.DataFrame,
                )
                else None
            ),
        }
    )


def add_image(
    image_bytes,
    title=None,
    width=None,
    height=None,
):
    if not _CAPTURE_STATE["active"]:
        return

    page = _CAPTURE_STATE.get(
        "current_page"
    )

    if page is None:
        return

    if not image_bytes:
        return

    page["images"].append(
        {
            "title": _safe_text(
                title
                or "Dashboard Map"
            ),
            "bytes": image_bytes,
            "width": width,
            "height": height,
        }
    )


# ============================================================
# TABLE CREATION
# ============================================================

def _make_table(
    dataframe,
    max_rows=300,
    max_columns=14,
):
    if (
        dataframe is None
        or dataframe.empty
    ):
        return None

    df = dataframe.copy()

    if len(df) > max_rows:
        df = df.head(max_rows)

    if len(df.columns) > max_columns:
        df = df.iloc[
            :,
            :max_columns,
        ]

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
            styles["DPE_Section"],
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
        Spacer(1, 7)
    )


# ============================================================
# ALTair → PNG
# ============================================================

def _chart_to_png(chart):
    """
    Convert an Altair chart into PNG.

    This keeps the actual chart definition instead
    of recreating it using matplotlib.
    """

    if chart is None:
        return None

    try:
        import vl_convert as vlc

        try:
            chart_to_use = chart.properties(
                width=1000
            )
        except Exception:
            chart_to_use = chart

        png = vlc.vegalite_to_png(
            chart_to_use.to_dict(),
            scale=2,
        )

        return png

    except Exception:
        return None


# ============================================================
# CHART IMAGE
# ============================================================

def _add_chart(
    story,
    styles,
    chart_item,
):
    chart = chart_item.get(
        "chart"
    )

    title = chart_item.get(
        "title",
        "Chart",
    )

    png = _chart_to_png(
        chart
    )

    if not png:
        return

    story.append(
        Paragraph(
            _safe_text(title),
            styles["DPE_Section"],
        )
    )

    buffer = BytesIO(png)

    available_width = (
        A4[0]
        - 30 * mm
    )

    # --------------------------------------------------------
    # Default chart height
    # --------------------------------------------------------

    image_width = available_width
    image_height = 70 * mm

    # Monthly disease chart / wider charts
    if (
        "monthly disease"
        in title.lower()
    ):
        image_height = 78 * mm

    image = Image(
        buffer,
        width=image_width,
        height=image_height,
    )

    story.append(image)

    story.append(
        Spacer(1, 7)
    )


# ============================================================
# IMAGE SECTION
# ============================================================

def _add_image(
    story,
    styles,
    image_item,
):
    image_bytes = image_item.get(
        "bytes"
    )

    if not image_bytes:
        return

    title = image_item.get(
        "title",
        "Dashboard Image",
    )

    story.append(
        Paragraph(
            _safe_text(title),
            styles["DPE_Section"],
        )
    )

    buffer = BytesIO(
        image_bytes
    )

    width = (
        image_item.get(
            "width"
        )
        or (
            A4[0]
            - 30 * mm
        )
    )

    height = (
        image_item.get(
            "height"
        )
        or 100 * mm
    )

    story.append(
        Image(
            buffer,
            width=width,
            height=height,
        )
    )

    story.append(
        Spacer(1, 7)
    )


# ============================================================
# PAGE HEADER
# ============================================================

def _add_page_header(
    story,
    styles,
    title,
    section_number,
    total_sections,
    report_period,
    filter_summary,
    record_count,
):
    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["DPE_Title"],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["DPE_Subtitle"],
        )
    )

    story.append(
        Paragraph(
            _safe_text(title),
            styles["DPE_PageTitle"],
        )
    )

    story.append(
        Paragraph(
            "Section "
            + str(section_number)
            + " of "
            + str(total_sections),
            styles["DPE_Small"],
        )
    )

    if report_period:
        story.append(
            Paragraph(
                "Reporting Period: "
                + _safe_text(
                    report_period
                ),
                styles["DPE_Small"],
            )
        )

    if filter_summary:
        story.append(
            Paragraph(
                "Filter Scope: "
                + _safe_text(
                    filter_summary
                ),
                styles["DPE_Small"],
            )
        )

    if record_count is not None:
        story.append(
            Paragraph(
                "Records in current scope: "
                + _format_number(
                    record_count
                ),
                styles["DPE_Small"],
            )
        )

    story.append(
        Spacer(1, 8)
    )


# ============================================================
# COMPLETE PDF GENERATOR
# ============================================================

def generate_captured_dashboard_pdf(
    pages,
    report_period=None,
    filter_summary=None,
):
    """
    Generate Complete Dashboard PDF from
    captured dashboard content.

    Unlike the old pdf_report.py approach,
    this function does NOT recreate charts
    with matplotlib.
    """

    pages = pages or []

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

    # ========================================================
    # COVER PAGE
    # ========================================================

    story.append(
        Spacer(1, 25 * mm)
    )

    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["DPE_Title"],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["DPE_Subtitle"],
        )
    )

    story.append(
        Spacer(1, 15)
    )

    story.append(
        Paragraph(
            "Complete Dashboard Management Report",
            styles["DPE_PageTitle"],
        )
    )

    story.append(
        Paragraph(
            "Report generated on: "
            + datetime.now().strftime(
                "%d-%m-%Y %H:%M"
            ),
            styles["DPE_Small"],
        )
    )

    if report_period:
        story.append(
            Paragraph(
                "Reporting Period: "
                + _safe_text(
                    report_period
                ),
                styles["DPE_Small"],
            )
        )

    if filter_summary:
        story.append(
            Paragraph(
                "Global Filter Scope: "
                + _safe_text(
                    filter_summary
                ),
                styles["DPE_Small"],
            )
        )

    story.append(
        Spacer(1, 15)
    )

    story.append(
        Paragraph(
            "This report contains the dashboard "
            "outputs captured from the selected "
            "management sections.",
            styles["DPE_Small"],
        )
    )

    # ========================================================
    # CONTENTS
    # ========================================================

    story.append(
        Spacer(1, 12)
    )

    story.append(
        Paragraph(
            "Dashboard Sections Included",
            styles["DPE_Section"],
        )
    )

    contents = [
        [
            "No.",
            "Dashboard Section",
        ]
    ]

    for index, page in enumerate(
        pages,
        start=1,
    ):
        contents.append(
            [
                str(index),
                _safe_text(
                    page.get(
                        "title",
                        f"Section {index}",
                    )
                ),
            ]
        )

    if len(contents) > 1:

        table = Table(
            contents,
            colWidths=[
                20 * mm,
                130 * mm,
            ],
            repeatRows=1,
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

    # ========================================================
    # EACH CAPTURED PAGE
    # ========================================================

    total_sections = len(
        pages
    )

    for page_index, page in enumerate(
        pages,
        start=1,
    ):

        story.append(
            PageBreak()
        )

        title = page.get(
            "title",
            f"Dashboard Section {page_index}",
        )

        tables = page.get(
            "tables",
            [],
        )

        charts = page.get(
            "charts",
            [],
        )

        images = page.get(
            "images",
            [],
        )

        kpis = page.get(
            "kpis",
            {},
        )

        notes = page.get(
            "notes",
            [],
        )

        df = page.get(
            "df"
        )

        record_count = None

        if isinstance(
            df,
            pd.DataFrame,
        ):
            record_count = len(df)

        _add_page_header(
            story=story,
            styles=styles,
            title=title,
            section_number=page_index,
            total_sections=total_sections,
            report_period=report_period,
            filter_summary=filter_summary,
            record_count=record_count,
        )

        # ----------------------------------------------------
        # KPIs
        # ----------------------------------------------------

        _add_kpi_table(
            story,
            styles,
            kpis,
        )

        # ----------------------------------------------------
        # CHARTS
        # ----------------------------------------------------

        for chart_item in charts:

            _add_chart(
                story,
                styles,
                chart_item,
            )

        # ----------------------------------------------------
        # IMAGES / MAPS
        # ----------------------------------------------------

        for image_item in images:

            _add_image(
                story,
                styles,
                image_item,
            )

        # ----------------------------------------------------
        # TABLES
        # ----------------------------------------------------

        for table_item in tables:

            title_text = table_item.get(
                "title",
                "Data Table",
            )

            dataframe = table_item.get(
                "dataframe"
            )

            if (
                dataframe is None
                or dataframe.empty
            ):
                continue

            story.append(
                Paragraph(
                    _safe_text(
                        title_text
                    ),
                    styles["DPE_TableTitle"],
                )
            )

            table = _make_table(
                dataframe
            )

            if table is not None:

                story.append(
                    table
                )

                story.append(
                    Spacer(1, 7)
                )

        # ----------------------------------------------------
        # NOTES
        # ----------------------------------------------------

        for note in notes:

            if not note:
                continue

            story.append(
                Paragraph(
                    _safe_text(note),
                    styles["DPE_Small"],
                )

            )

            story.append(
                Spacer(1, 4)
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
            styles["DPE_Section"],
        )
    )

    story.append(
        Paragraph(
            "This consolidated dashboard report "
            "represents the dashboard outputs captured "
            "under the selected Global Dashboard Control "
            "filters at the time of report generation.",
            styles["DPE_Small"],
        )
    )

    story.append(
        Spacer(1, 10)
    )

    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["DPE_Small"],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["DPE_Small"],
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
# COMPATIBILITY ALIAS
# ============================================================

def generate_dashboard_pdf(
    pages,
    report_period=None,
    filter_summary=None,
):
    """
    Short compatibility wrapper.
    """

    return generate_captured_dashboard_pdf(
        pages=pages,
        report_period=report_period,
        filter_summary=filter_summary,
    )
