from io import BytesIO
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt

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
    Table,
    TableStyle,
    PageBreak,
    Image,
    KeepTogether,
)


# ============================================================
# CONFIGURATION
# ============================================================

DASHBOARD_TITLE = (
    "MSU Mumbai Public Health Surveillance Dashboard"
)

DASHBOARD_SUBTITLE = (
    "Surveillance • Monitoring • Analysis • Management"
)

PAGE_WIDTH, PAGE_HEIGHT = A4


# ============================================================
# BASIC HELPERS
# ============================================================

def _safe_text(value):
    """
    Convert any value into safe display text.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    return str(value)


def _format_number(value):
    """
    Format numbers consistently for PDF display.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""

        numeric = float(value)

        if numeric.is_integer():
            return f"{int(numeric):,}"

        return f"{numeric:,.2f}"

    except Exception:
        return _safe_text(value)


def _format_dataframe_for_pdf(dataframe):
    """
    Convert dataframe values into PDF-safe display strings.
    """

    if dataframe is None:
        return pd.DataFrame()

    if not isinstance(dataframe, pd.DataFrame):
        try:
            dataframe = pd.DataFrame(dataframe)
        except Exception:
            return pd.DataFrame()

    if dataframe.empty:
        return dataframe.copy()

    output = dataframe.copy()

    for column in output.columns:

        def _format_value(value):

            if value is None:
                return ""

            try:
                if pd.isna(value):
                    return ""
            except Exception:
                pass

            if isinstance(
                value,
                (int, float),
            ):
                return _format_number(value)

            return _safe_text(value)

        output[column] = output[column].map(
            _format_value
        )

    return output


# ============================================================
# REPORT STYLES
# ============================================================

def _styles():

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="DashboardTitle",
            parent=styles["Title"],
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="DashboardSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.grey,
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Heading1"],
            fontSize=15,
            leading=19,
            spaceBefore=4,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=8,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SubSectionTitle",
            parent=styles["Heading3"],
            fontSize=10,
            leading=13,
            spaceBefore=5,
            spaceAfter=4,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallText",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9.5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportMeta",
            parent=styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#444444"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["Normal"],
            fontSize=7,
            leading=8.5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="KPIValue",
            parent=styles["Normal"],
            fontSize=13,
            leading=15,
            alignment=TA_CENTER,
        )
    )

    styles.add(
        ParagraphStyle(
            name="KPILabel",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
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

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    canvas.setFont(
        "Helvetica-Bold",
        7.5,
    )

    canvas.drawString(
        15 * mm,
        PAGE_HEIGHT - 10 * mm,
        DASHBOARD_TITLE,
    )

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.drawRightString(
        PAGE_WIDTH - 15 * mm,
        PAGE_HEIGHT - 10 * mm,
        "Management Report",
    )

    # --------------------------------------------------------
    # Footer line
    # --------------------------------------------------------

    canvas.setStrokeColor(
        colors.HexColor("#CCCCCC")
    )

    canvas.line(
        15 * mm,
        12 * mm,
        PAGE_WIDTH - 15 * mm,
        12 * mm,
    )

    # --------------------------------------------------------
    # Footer text
    # --------------------------------------------------------

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.setFillColor(
        colors.HexColor("#666666")
    )

    canvas.drawString(
        15 * mm,
        7 * mm,
        "MSU Mumbai Public Health Surveillance Dashboard",
    )

    canvas.drawRightString(
        PAGE_WIDTH - 15 * mm,
        7 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# DATAFRAME TABLE
# ============================================================

def _make_table(
    dataframe,
    max_rows=None,
):

    if dataframe is None:
        return None

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):

        try:
            dataframe = pd.DataFrame(
                dataframe
            )

        except Exception:
            return None

    if dataframe.empty:
        return None

    table_df = dataframe.copy()

    if max_rows is not None:
        table_df = table_df.head(
            int(max_rows)
        )

    table_df = _format_dataframe_for_pdf(
        table_df
    )

    styles = _styles()

    headers = [
        Paragraph(
            _safe_text(column),
            styles["TableHeader"],
        )
        for column in table_df.columns
    ]

    rows = [headers]

    for _, row in table_df.iterrows():

        rows.append(
            [
                Paragraph(
                    _safe_text(value),
                    styles["TableCell"],
                )
                for value in row.tolist()
            ]
        )

    column_count = len(
        table_df.columns
    )

    if column_count == 0:
        return None

    available_width = (
        PAGE_WIDTH
        - 30 * mm
    )

    col_width = (
        available_width
        / column_count
    )

    table = Table(
        rows,
        repeatRows=1,
        colWidths=[
            col_width
            for _ in range(column_count)
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
                    colors.HexColor("#2F5597"),
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
                    "TOP",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#CCCCCC"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F7F9FC"),
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
# DATAFRAME SECTION
# ============================================================

def _add_dataframe_section(
    story,
    title,
    dataframe,
    styles=None,
    max_rows=None,
):

    if dataframe is None:
        return

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):

        try:
            dataframe = pd.DataFrame(
                dataframe
            )

        except Exception:
            return

    if dataframe.empty:
        return

    if styles is None:
        styles = _styles()

    story.append(
        Paragraph(
            _safe_text(title),
            styles["SectionTitle"],
        )
    )

    table = _make_table(
        dataframe,
        max_rows=max_rows,
    )

    if table is not None:

        story.append(
            KeepTogether(
                [
                    table,
                    Spacer(
                        1,
                        5,
                    ),
                ]
            )
        )


# ============================================================
# KPI TABLE
# ============================================================

def _add_kpi_table(
    story,
    kpis,
    styles=None,
):

    if not kpis:
        return

    if styles is None:
        styles = _styles()

    preferred_keys = [
        "total_records",
        "diseases",
        "facilities",
        "wards",
    ]

    labels = {
        "total_records": "Total Records",
        "diseases": "Diseases",
        "facilities": "Facilities",
        "wards": "Wards",
    }

    available = []

    for key in preferred_keys:

        if key in kpis:

            available.append(
                (
                    key,
                    labels.get(
                        key,
                        key,
                    ),
                    kpis[key],
                )
            )

    # Add any additional KPIs
    # supplied by the dashboard.

    for key, value in kpis.items():

        if key in preferred_keys:
            continue

        available.append(
            (
                key,
                str(key).replace(
                    "_",
                    " ",
                ).title(),
                value,
            )
        )

    if not available:
        return

    cells = []

    for _, label, value in available:

        cell = [
            Paragraph(
                _safe_text(label),
                styles["KPILabel"],
            ),
            Spacer(
                1,
                2,
            ),
            Paragraph(
                _format_number(value),
                styles["KPIValue"],
            ),
        ]

        cells.append(cell)

    table = Table(
        [cells],
        colWidths=[
            (
                PAGE_WIDTH
                - 30 * mm
            )
            / len(cells)
            for _ in cells
        ],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#D9D9D9"),
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F5F7FA"),
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
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
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


# ============================================================
# CHART CREATION
# ============================================================

def _create_chart_image(
    dataframe,
    x_column,
    y_column,
    title,
    chart_type="bar",
    width=7.0,
    height=3.8,
    limit=None,
):

    if dataframe is None:
        return None

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):

        try:
            dataframe = pd.DataFrame(
                dataframe
            )

        except Exception:
            return None

    if dataframe.empty:
        return None

    if x_column not in dataframe.columns:
        return None

    if y_column not in dataframe.columns:
        return None

    temp = dataframe[
        [
            x_column,
            y_column,
        ]
    ].copy()

    temp[y_column] = pd.to_numeric(
        temp[y_column],
        errors="coerce",
    )

    temp = temp.dropna(
        subset=[
            y_column,
        ]
    )

    if temp.empty:
        return None

    if limit is not None:

        temp = temp.head(
            int(limit)
        )

    if temp.empty:
        return None

    temp[x_column] = (
        temp[x_column]
        .astype(str)
    )

    # --------------------------------------------------------
    # Matplotlib figure
    # --------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(
            width,
            height,
        )
    )

    if chart_type == "line":

        ax.plot(
            temp[x_column],
            temp[y_column],
            marker="o",
            linewidth=1.8,
        )

    elif chart_type == "horizontal_bar":

        temp = temp.sort_values(
            by=y_column,
            ascending=True,
        )

        ax.barh(
            temp[x_column],
            temp[y_column],
        )

    else:

        ax.bar(
            temp[x_column],
            temp[y_column],
        )

    ax.set_title(
        _safe_text(title),
        fontsize=11,
        pad=10,
    )

    ax.set_xlabel(
        _safe_text(x_column),
        fontsize=8,
    )

    ax.set_ylabel(
        _safe_text(y_column),
        fontsize=8,
    )

    ax.tick_params(
        axis="both",
        labelsize=7,
    )

    if chart_type == "bar":

        plt.xticks(
            rotation=45,
            ha="right",
        )

    ax.grid(
        axis="y",
        linestyle="--",
        alpha=0.25,
    )

    fig.tight_layout()

    buffer = BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    buffer.seek(0)

    return Image(
        buffer,
        width=175 * mm,
        height=92 * mm,
    )


# ============================================================
# CHART SECTION
# ============================================================

def _add_chart_section(
    story,
    chart_definition,
    styles=None,
):

    if not chart_definition:
        return

    if styles is None:
        styles = _styles()

    if isinstance(
        chart_definition,
        dict,
    ):

        dataframe = chart_definition.get(
            "dataframe"
        )

        x_column = chart_definition.get(
            "x_column"
        )

        y_column = chart_definition.get(
            "y_column"
        )

        title = chart_definition.get(
            "title",
            "Chart",
        )

        chart_type = chart_definition.get(
            "chart_type",
            "bar",
        )

        limit = chart_definition.get(
            "limit"
        )

    else:
        return

    image = _create_chart_image(
        dataframe=dataframe,
        x_column=x_column,
        y_column=y_column,
        title=title,
        chart_type=chart_type,
        limit=limit,
    )

    if image is None:
        return

    story.append(
        Paragraph(
            _safe_text(title),
            styles["SectionTitle"],
        )
    )

    story.append(
        image
    )

    story.append(
        Spacer(
            1,
            6,
        )
    )


# ============================================================
# REPORT HEADER
# ============================================================

def _add_report_header(
    story,
    report_title,
    report_period=None,
    filter_summary=None,
    record_count=None,
    styles=None,
):

    if styles is None:
        styles = _styles()

    story.append(
        Spacer(
            1,
            6,
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["DashboardTitle"],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["DashboardSubtitle"],
        )
    )

    story.append(
        Paragraph(
            _safe_text(report_title),
            styles["ReportTitle"],
        )
    )

    metadata = []

    if report_period:
        metadata.append(
            f"<b>Reporting Period:</b> "
            f"{_safe_text(report_period)}"
        )

    if record_count is not None:
        metadata.append(
            f"<b>Records in Current Scope:</b> "
            f"{_format_number(record_count)}"
        )

    if filter_summary:
        metadata.append(
            f"<b>Filter Scope:</b> "
            f"{_safe_text(filter_summary)}"
        )

    metadata.append(
        f"<b>Generated:</b> "
        f"{datetime.now().strftime('%d-%b-%Y %H:%M')}"
    )

    for item in metadata:

        story.append(
            Paragraph(
                item,
                styles["ReportMeta"],
            )
        )

        story.append(
            Spacer(
                1,
                2,
            )
        )

    story.append(
        Spacer(
            1,
            7,
        )
    )


# ============================================================
# REPORT SCOPE
# ============================================================

def _add_scope_section(
    story,
    report_period=None,
    filter_summary=None,
    record_count=None,
    styles=None,
):

    if styles is None:
        styles = _styles()

    story.append(
        Paragraph(
            "Report Scope",
            styles["SectionTitle"],
        )
    )

    rows = []

    if report_period:

        rows.append(
            [
                "Reporting Period",
                _safe_text(report_period),
            ]
        )

    if filter_summary:

        rows.append(
            [
                "Applied Filters",
                _safe_text(filter_summary),
            ]
        )

    if record_count is not None:

        rows.append(
            [
                "Records Included",
                _format_number(
                    record_count
                ),
            ]
        )

    if not rows:
        return

    table_data = [
        [
            Paragraph(
                "Parameter",
                styles["TableHeader"],
            ),
            Paragraph(
                "Value",
                styles["TableHeader"],
            ),
        ]
    ]

    for key, value in rows:

        table_data.append(
            [
                Paragraph(
                    _safe_text(key),
                    styles["TableCell"],
                ),
                Paragraph(
                    _safe_text(value),
                    styles["TableCell"],
                ),
            ]
        )

    table = Table(
        table_data,
        colWidths=[
            48 * mm,
            127 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#2F5597"),
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
                    0.35,
                    colors.HexColor("#CCCCCC"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, -1),
                    colors.HexColor("#F7F9FC"),
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

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title=_safe_text(
            report_title
        ),
        author="MSU Mumbai Public Health Surveillance Dashboard",
    )

    styles = _styles()

    story = []

    record_count = (
        len(df)
        if isinstance(
            df,
            pd.DataFrame,
        )
        else None
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    _add_report_header(
        story=story,
        report_title=report_title,
        report_period=report_period,
        filter_summary=filter_summary,
        record_count=record_count,
        styles=styles,
    )

    # --------------------------------------------------------
    # KPIs
    # --------------------------------------------------------

    _add_kpi_table(
        story=story,
        kpis=kpis,
        styles=styles,
    )

    # --------------------------------------------------------
    # Charts
    # --------------------------------------------------------

    if charts:

        story.append(
            Paragraph(
                "Dashboard Charts",
                styles["ReportTitle"],
            )
        )

        for chart in charts:

            _add_chart_section(
                story=story,
                chart_definition=chart,
                styles=styles,
            )

    # --------------------------------------------------------
    # Tables
    # --------------------------------------------------------

    if tables:

        story.append(
            Paragraph(
                "Dashboard Tables",
                styles["ReportTitle"],
            )
        )

        for table_item in tables:

            if isinstance(
                table_item,
                tuple,
            ) and len(table_item) >= 2:

                title = table_item[0]
                dataframe = table_item[1]

            elif isinstance(
                table_item,
                dict,
            ):

                title = table_item.get(
                    "title",
                    "Table",
                )

                dataframe = table_item.get(
                    "dataframe"
                )

            else:
                continue

            _add_dataframe_section(
                story=story,
                title=title,
                dataframe=dataframe,
                styles=styles,
                max_rows=None,
            )

    # --------------------------------------------------------
    # Scope
    # --------------------------------------------------------

    _add_scope_section(
        story=story,
        report_period=report_period,
        filter_summary=filter_summary,
        record_count=record_count,
        styles=styles,
    )

    # --------------------------------------------------------
    # Completion note
    # --------------------------------------------------------

    story.append(
        Spacer(
            1,
            8,
        )
    )

    story.append(
        Paragraph(
            "This PDF represents the analytical content "
            "supplied by the dashboard for the selected "
            "filter scope at the time of generation. "
            "Interactive controls are represented by their "
            "selected state/data supplied to the report.",
            styles["SmallText"],
        )
    )

    doc.build(
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

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title=(
            "MSU Mumbai Complete Dashboard Report"
        ),
        author=(
            "MSU Mumbai Public Health Surveillance Dashboard"
        ),
    )

    styles = _styles()

    story = []

    # ========================================================
    # COVER PAGE
    # ========================================================

    story.append(
        Spacer(
            1,
            25 * mm,
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["DashboardTitle"],
        )
    )

    story.append(
        Spacer(
            1,
            4,
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["DashboardSubtitle"],
        )
    )

    story.append(
        Spacer(
            1,
            18,
        )
    )

    story.append(
        Paragraph(
            "Complete Dashboard Management Report",
            styles["ReportTitle"],
        )
    )

    story.append(
        Spacer(
            1,
            8,
        )
    )

    if report_period:

        story.append(
            Paragraph(
                f"<b>Reporting Period:</b> "
                f"{_safe_text(report_period)}",
                styles["ReportMeta"],
            )
        )

    if filter_summary:

        story.append(
            Spacer(
                1,
                4,
            )
        )

        story.append(
            Paragraph(
                f"<b>Filter Scope:</b> "
                f"{_safe_text(filter_summary)}",
                styles["ReportMeta"],
            )
        )

    story.append(
        Spacer(
            1,
            10,
        )
    )

    story.append(
        Paragraph(
            f"<b>Generated:</b> "
            f"{datetime.now().strftime('%d-%b-%Y %H:%M')}",
            styles["ReportMeta"],
        )
    )

    story.append(
        Spacer(
            1,
            20,
        )
    )

    story.append(
        Paragraph(
            "This consolidated report contains the "
            "dashboard sections and analytical outputs "
            "supplied at the time of report generation.",
            styles["SmallText"],
        )
    )

    story.append(
        PageBreak()
    )

    # ========================================================
    # CONTENTS
    # ========================================================

    story.append(
        Paragraph(
            "Contents",
            styles["ReportTitle"],
        )
    )

    if pages:

        contents_data = [
            [
                Paragraph(
                    "No.",
                    styles["TableHeader"],
                ),
                Paragraph(
                    "Dashboard Section",
                    styles["TableHeader"],
                ),
            ]
        ]

        for index, page in enumerate(
            pages,
            start=1,
        ):

            if isinstance(
                page,
                dict,
            ):

                title = page.get(
                    "title",
                    f"Section {index}",
                )

            else:

                title = f"Section {index}"

            contents_data.append(
                [
                    Paragraph(
                        str(index),
                        styles["TableCell"],
                    ),
                    Paragraph(
                        _safe_text(title),
                        styles["TableCell"],
                    ),
                ]
            )

        contents_table = Table(
            contents_data,
            colWidths=[
                18 * mm,
                157 * mm,
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
                        colors.HexColor("#2F5597"),
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
                        0.35,
                        colors.HexColor("#CCCCCC"),
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
                            colors.HexColor("#F7F9FC"),
                        ],
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (0, -1),
                        "CENTER",
                    ),
                ]
            )
        )

        story.append(
            contents_table
        )

    story.append(
        PageBreak()
    )

    # ========================================================
    # EACH DASHBOARD PAGE
    # ========================================================

    for page_index, page in enumerate(
        pages,
        start=1,
    ):

        if not isinstance(
            page,
            dict,
        ):
            continue

        page_title = page.get(
            "title",
            f"Dashboard Section {page_index}",
        )

        page_df = page.get(
            "df"
        )

        page_kpis = page.get(
            "kpis"
        )

        page_tables = page.get(
            "tables"
        )

        page_charts = page.get(
            "charts"
        )

        page_report_period = page.get(
            "report_period",
            report_period,
        )

        page_filter_summary = page.get(
            "filter_summary",
            filter_summary,
        )

        # ----------------------------------------------------
        # Section header
        # ----------------------------------------------------

        story.append(
            Paragraph(
                f"{page_index}. "
                f"{_safe_text(page_title)}",
                styles["ReportTitle"],
            )
        )

        if page_report_period:

            story.append(
                Paragraph(
                    f"<b>Reporting Period:</b> "
                    f"{_safe_text(page_report_period)}",
                    styles["ReportMeta"],
                )
            )

        if page_filter_summary:

            story.append(
                Paragraph(
                    f"<b>Filter Scope:</b> "
                    f"{_safe_text(page_filter_summary)}",
                    styles["ReportMeta"],
                )
            )

        if isinstance(
            page_df,
            pd.DataFrame,
        ):

            story.append(
                Paragraph(
                    f"<b>Records Included:</b> "
                    f"{_format_number(len(page_df))}",
                    styles["ReportMeta"],
                )
            )

        story.append(
            Spacer(
                1,
                7,
            )
        )

        # ----------------------------------------------------
        # KPIs
        # ----------------------------------------------------

        _add_kpi_table(
            story=story,
            kpis=page_kpis,
            styles=styles,
        )

        # ----------------------------------------------------
        # Charts
        # ----------------------------------------------------

        if page_charts:

            story.append(
                Paragraph(
                    "Charts",
                    styles["SectionTitle"],
                )
            )

            for chart in page_charts:

                _add_chart_section(
                    story=story,
                    chart_definition=chart,
                    styles=styles,
                )

        # ----------------------------------------------------
        # Tables
        # ----------------------------------------------------

        if page_tables:

            story.append(
                Paragraph(
                    "Tables",
                    styles["SectionTitle"],
                )
            )

            for table_item in page_tables:

                if isinstance(
                    table_item,
                    tuple,
                ) and len(table_item) >= 2:

                    table_title = (
                        table_item[0]
                    )

                    table_df = (
                        table_item[1]
                    )

                elif isinstance(
                    table_item,
                    dict,
                ):

                    table_title = (
                        table_item.get(
                            "title",
                            "Table",
                        )
                    )

                    table_df = (
                        table_item.get(
                            "dataframe"
                        )
                    )

                else:
                    continue

                _add_dataframe_section(
                    story=story,
                    title=table_title,
                    dataframe=table_df,
                    styles=styles,
                    max_rows=None,
                )

        # ----------------------------------------------------
        # No data state
        # ----------------------------------------------------

        has_tables = bool(
            page_tables
        )

        has_charts = bool(
            page_charts
        )

        if (
            not has_tables
            and not has_charts
        ):

            story.append(
                Paragraph(
                    "No analytical output was supplied "
                    "for this dashboard section under "
                    "the current filter scope.",
                    styles["SmallText"],
                )
            )

        # ----------------------------------------------------
        # Section completion note
        # ----------------------------------------------------

        story.append(
            Spacer(
                1,
                8,
            )
        )

        story.append(
            Paragraph(
                "Management Scope: This section reflects "
                "the data, calculations and report objects "
                "provided by the dashboard at generation time.",
                styles["SmallText"],
            )
        )

        # ----------------------------------------------------
        # New page
        # ----------------------------------------------------

        if page_index < len(pages):

            story.append(
                PageBreak()
            )

    # ========================================================
    # FINAL NOTE
    # ========================================================

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "Report Completion Note",
            styles["ReportTitle"],
        )
    )

    story.append(
        Paragraph(
            "This consolidated PDF was generated from "
            "the dashboard state supplied at the time of "
            "generation. Global filters and section-level "
            "selections supplied by the dashboard are "
            "represented in the report scope and analytical "
            "objects.",
            styles["SmallText"],
        )
    )

    story.append(
        Spacer(
            1,
            8,
        )
    )

    story.append(
        Paragraph(
            "Interactive dashboard controls are not "
            "interactive inside a PDF. The PDF represents "
            "the selected state/data that was supplied "
            "when the report was generated.",
            styles["SmallText"],
        )
    )

    doc.build(
        story,
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )

    buffer.seek(0)

    return buffer.getvalue()
