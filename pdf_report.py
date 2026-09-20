from io import BytesIO
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
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


DASHBOARD_TITLE = (
    "MSU Mumbai Public Health Surveillance Dashboard"
)

DASHBOARD_SUBTITLE = (
    "Surveillance • Monitoring • Analysis • Management"
)


def _safe_text(value):
    if pd.isna(value):
        return ""
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

    return styles


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


def _make_table(dataframe, max_rows=50):
    if dataframe is None or dataframe.empty:
        return None

    df = dataframe.copy().head(max_rows)

    headers = [
        _safe_text(column)
        for column in df.columns
    ]

    rows = [
        headers
    ]

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
    max_rows=50,
):
    if dataframe is None or dataframe.empty:
        return

    story.append(
        Paragraph(
            title,
            styles["SectionCustom"],
        )
    )

    table = _make_table(
        dataframe,
        max_rows=max_rows,
    )

    if table is not None:
        story.append(table)
        story.append(Spacer(1, 6))


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

        if isinstance(value, (int, float)):
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


def _create_chart_image(
    dataframe,
    x_column,
    y_column,
    title,
):
    if dataframe is None or dataframe.empty:
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

    temp = temp.head(20)

    fig, ax = plt.subplots(
        figsize=(8, 4),
    )

    ax.bar(
        temp[x_column].astype(str),
        temp[y_column],
    )

    ax.set_title(
        title,
        fontsize=10,
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

    Parameters
    ----------
    report_title : str
        Name of the dashboard page.

    df : pandas.DataFrame
        Current filtered dataset.

    kpis : dict
        KPI dictionary.

    tables : list of tuples
        Example:
        [
            ("Top Facilities", dataframe),
            ("Top Wards", dataframe),
        ]

    charts : list of dictionaries
        Example:
        [
            {
                "dataframe": dataframe,
                "x_column": "Facility",
                "y_column": "Records",
                "title": "Facility-wise Burden",
            }
        ]

    report_period : str
        Reporting period shown in the report.

    filter_summary : str
        Description of currently applied filters.
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
        author="MSU Mumbai Public Health Surveillance Dashboard",
    )

    styles = _styles()

    story = []

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
            report_title,
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
        for chart in charts:
            chart_image = _create_chart_image(
                chart.get("dataframe"),
                chart.get("x_column"),
                chart.get("y_column"),
                chart.get("title", ""),
            )

            if chart_image:
                story.append(
                    Paragraph(
                        chart.get(
                            "title",
                            "Chart",
                        ),
                        styles["SectionCustom"],
                    )
                )

                story.append(chart_image)
                story.append(
                    Spacer(1, 6)
                )

    if tables:
        for title, dataframe in tables:
            _add_dataframe_section(
                story,
                styles,
                title,
                dataframe,
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
                "dashboard filters.",
                styles["SmallCustom"],
            )
        )

    story.append(
        Spacer(1, 12)
    )

    story.append(
        Paragraph(
            "MSU Mumbai Public Health Surveillance Dashboard",
            styles["SmallCustom"],
        )
    )

    story.append(
        Paragraph(
            "Surveillance • Monitoring • Analysis • Management",
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
