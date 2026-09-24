from io import BytesIO
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt

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

TABLE_FONT_SIZE = 6.5
TABLE_HEADER_FONT_SIZE = 6.8

MAX_CHART_CATEGORIES = 40
TABLE_ROWS_PER_BLOCK = 45


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
        if pd.isna(value):
            return "0"
    except Exception:
        pass

    try:
        return f"{int(float(value)):,}"
    except Exception:
        return _safe_text(value)


def _clean_text_series(df, column):
    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return pd.Series(dtype="object")

    result = (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    result = result[
        result.ne("")
        & result.str.lower().ne("nan")
        & result.str.lower().ne("none")
        & result.str.lower().ne("nat")
    ]

    return result


def _find_column(df, candidates):
    if df is None or df.empty:
        return None

    for column in candidates:
        if column in df.columns:
            return column

    return None


# ============================================================
# MONTH HELPERS
# ============================================================

CALENDAR_MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

MONTH_NUMBER_MAP = {
    month: index
    for index, month in enumerate(
        CALENDAR_MONTHS,
        start=1,
    )
}


def _normalize_month(value):
    if pd.isna(value):
        return ""

    text = str(value).strip().lower()

    mapping = {
        "january": "Jan",
        "jan": "Jan",
        "1": "Jan",
        "01": "Jan",

        "february": "Feb",
        "feb": "Feb",
        "2": "Feb",
        "02": "Feb",

        "march": "Mar",
        "mar": "Mar",
        "3": "Mar",
        "03": "Mar",

        "april": "Apr",
        "apr": "Apr",
        "4": "Apr",
        "04": "Apr",

        "may": "May",
        "5": "May",
        "05": "May",

        "june": "Jun",
        "jun": "Jun",
        "6": "Jun",
        "06": "Jun",

        "july": "Jul",
        "jul": "Jul",
        "7": "Jul",
        "07": "Jul",

        "august": "Aug",
        "aug": "Aug",
        "8": "Aug",
        "08": "Aug",

        "september": "Sep",
        "sep": "Sep",
        "sept": "Sep",
        "9": "Sep",
        "09": "Sep",

        "october": "Oct",
        "oct": "Oct",
        "10": "Oct",

        "november": "Nov",
        "nov": "Nov",
        "11": "Nov",

        "december": "Dec",
        "dec": "Dec",
        "12": "Dec",
    }

    return mapping.get(text, text)


# ============================================================
# YEAR HELPERS
# ============================================================

def _normalize_year(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    try:
        numeric = float(text)

        if numeric.is_integer():
            year = int(numeric)

            if 1900 <= year <= 2100:
                return year

    except Exception:
        pass

    try:
        parsed = pd.to_datetime(
            value,
            errors="coerce",
        )

        if not pd.isna(parsed):
            year = int(parsed.year)

            if 1900 <= year <= 2100:
                return year

    except Exception:
        pass

    return ""


# ============================================================
# STYLES
# ============================================================

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
            name="SubSectionCustom",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            spaceBefore=6,
            spaceAfter=4,
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

    styles.add(
        ParagraphStyle(
            name="ManagementCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            spaceAfter=6,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableCellCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=6.2,
            leading=7.5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableHeaderCustom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=7.5,
            textColor=colors.white,
        )
    )

    return styles


# ============================================================
# HEADER / FOOTER
# ============================================================

def _header_footer(canvas, doc):
    canvas.saveState()

    width, height = A4

    # Header line
    canvas.setStrokeColor(
        colors.HexColor("#1f4e78")
    )

    canvas.setLineWidth(0.5)

    canvas.line(
        15 * mm,
        height - 10 * mm,
        width - 15 * mm,
        height - 10 * mm,
    )

    # Footer line
    canvas.line(
        15 * mm,
        14 * mm,
        width - 15 * mm,
        14 * mm,
    )

    canvas.setFont(
        "Helvetica-Bold",
        7.2,
    )

    canvas.drawString(
        15 * mm,
        9 * mm,
        DASHBOARD_TITLE,
    )

    canvas.setFont(
        "Helvetica",
        7,
    )

    canvas.drawRightString(
        width - 15 * mm,
        9 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# TABLE CONVERSION
# ============================================================

def _prepare_dataframe_for_pdf(dataframe):
    if dataframe is None:
        return pd.DataFrame()

    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):
        try:
            dataframe = pd.DataFrame(dataframe)
        except Exception:
            return pd.DataFrame()

    if dataframe.empty:
        return pd.DataFrame()

    df = dataframe.copy()

    # Replace NaN / NaT
    df = df.replace(
        {
            pd.NaT: "",
        }
    )

    for column in df.columns:

        if pd.api.types.is_datetime64_any_dtype(
            df[column]
        ):
            df[column] = df[column].dt.strftime(
                "%d-%m-%Y"
            )

        df[column] = df[column].map(
            _safe_text
        )

    return df


# ============================================================
# TABLE CREATION
# ============================================================

def _make_table(
    dataframe,
    max_rows=None,
    styles=None,
):
    if dataframe is None or dataframe.empty:
        return None

    df = _prepare_dataframe_for_pdf(
        dataframe
    )

    if df.empty:
        return None

    if max_rows is not None:
        df = df.head(max_rows)

    headers = [
        Paragraph(
            _safe_text(column),
            styles["TableHeaderCustom"]
            if styles
            else getSampleStyleSheet()["Normal"],
        )
        for column in df.columns
    ]

    rows = [headers]

    for _, row in df.iterrows():

        row_values = []

        for value in row.tolist():

            text = _safe_text(value)

            # Keep very long cell values readable.
            if len(text) > 180:
                text = text[:177] + "..."

            if styles:
                row_values.append(
                    Paragraph(
                        text,
                        styles["TableCellCustom"],
                    )
                )
            else:
                row_values.append(text)

        rows.append(row_values)

    column_count = len(df.columns)

    if column_count <= 3:
        available_width = 180 * mm

        col_widths = [
            available_width / column_count
            for _ in range(column_count)
        ]

    elif column_count <= 6:

        col_widths = [
            180 * mm / column_count
            for _ in range(column_count)
        ]

    else:

        col_widths = [
            180 * mm / column_count
            for _ in range(column_count)
        ]

    table = Table(
        rows,
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
                    TABLE_FONT_SIZE,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#9e9e9e"),
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
# PAGINATED TABLE SECTION
# ============================================================

def _add_dataframe_section(
    story,
    styles,
    title,
    dataframe,
    max_rows=None,
):
    if dataframe is None or dataframe.empty:
        return

    df = _prepare_dataframe_for_pdf(
        dataframe
    )

    if df.empty:
        return

    story.append(
        Paragraph(
            title,
            styles["SectionCustom"],
        )
    )

    # Do NOT arbitrarily cut the table.
    # Split large datasets into multiple PDF blocks.
    if max_rows is not None:
        df = df.head(max_rows)

    total_rows = len(df)

    if total_rows <= TABLE_ROWS_PER_BLOCK:

        table = _make_table(
            df,
            styles=styles,
        )

        if table is not None:
            story.append(table)
            story.append(
                Spacer(1, 7)
            )

        return

    # Large table
    for start in range(
        0,
        total_rows,
        TABLE_ROWS_PER_BLOCK,
    ):

        end = min(
            start + TABLE_ROWS_PER_BLOCK,
            total_rows,
        )

        block = df.iloc[
            start:end
        ].copy()

        table = _make_table(
            block,
            styles=styles,
        )

        if table is None:
            continue

        story.append(table)

        if end < total_rows:

            story.append(
                Paragraph(
                    f"Continued: rows {end + 1:,} "
                    f"to {total_rows:,}",
                    styles["SmallCustom"],
                )
            )

            story.append(
                PageBreak()
            )

        else:

            story.append(
                Spacer(1, 7)
            )


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
                    colors.HexColor("#9e9e9e"),
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
        Spacer(1, 8)
    )


# ============================================================
# CHART IMAGE
# ============================================================

def _create_chart_image(
    dataframe,
    x_column,
    y_column,
    title,
    chart_type="bar",
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

    # No arbitrary head(20).
    # For extremely large categorical charts,
    # preserve the highest-burden categories so
    # the PDF remains readable.
    if len(temp) > MAX_CHART_CATEGORIES:

        temp = (
            temp.sort_values(
                y_column,
                ascending=False,
                kind="stable",
            )
            .head(MAX_CHART_CATEGORIES)
        )

    fig, ax = plt.subplots(
        figsize=(8.6, 4.6)
    )

    x_values = (
        temp[x_column]
        .astype(str)
        .tolist()
    )

    y_values = (
        temp[y_column]
        .tolist()
    )

    if chart_type == "line":

        ax.plot(
            range(len(x_values)),
            y_values,
            marker="o",
            linewidth=1.5,
        )

        ax.set_xticks(
            range(len(x_values))
        )

        ax.set_xticklabels(
            x_values,
            rotation=45,
            ha="right",
            fontsize=7,
        )

    else:

        ax.bar(
            range(len(x_values)),
            y_values,
        )

        ax.set_xticks(
            range(len(x_values))
        )

        ax.set_xticklabels(
            x_values,
            rotation=45,
            ha="right",
            fontsize=7,
        )

    ax.set_title(
        title,
        fontsize=10,
        fontweight="bold",
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
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    image_buffer.seek(0)

    return Image(
        image_buffer,
        width=175 * mm,
        height=88 * mm,
    )


# ============================================================
# REPORT HEADER
# ============================================================

def _add_report_header(
    story,
    styles,
    report_title,
    report_period=None,
    filter_summary=None,
    record_count=None,
):
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
            _safe_text(report_title),
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

    if record_count is not None:

        story.append(
            Paragraph(
                "Records in current scope: "
                + _format_number(record_count),
                styles["SmallCustom"],
            )
        )

    story.append(
        Spacer(1, 8)
    )


# ============================================================
# AUTOMATIC MANAGEMENT ANALYSIS
# ============================================================

def _build_auto_analysis_tables(df):
    """
    Build useful management tables directly from the
    currently filtered dataframe.

    This acts as a safety layer so the PDF still contains
    meaningful analysis even when app.py does not explicitly
    pass page-specific tables.
    """

    tables = []

    if df is None or df.empty:
        return tables

    # --------------------------------------------------------
    # Disease
    # --------------------------------------------------------

    disease_column = _find_column(
        df,
        [
            "Disease",
        ],
    )

    if disease_column:

        series = _clean_text_series(
            df,
            disease_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis("Disease")
                .reset_index(
                    name="Records"
                )
            )

            tables.append(
                (
                    "Disease-wise Burden",
                    table,
                )
            )

    # --------------------------------------------------------
    # Pathogen
    # --------------------------------------------------------

    pathogen_column = _find_column(
        df,
        [
            "Test Performed Pathogen Name",
            "Pathogen Name",
            "Test Performed Pathogen",
            "Pathogen",
        ],
    )

    if pathogen_column:

        series = _clean_text_series(
            df,
            pathogen_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis(
                    "Test Performed Pathogen Name"
                )
                .reset_index(
                    name="Records"
                )
            )

            tables.append(
                (
                    "Test Performed / Pathogen Name-wise Analysis",
                    table,
                )
            )

    # --------------------------------------------------------
    # Facility
    # --------------------------------------------------------

    facility_column = _find_column(
        df,
        [
            "Facility Name",
            "Facility",
        ],
    )

    if facility_column:

        series = _clean_text_series(
            df,
            facility_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis("Facility")
                .reset_index(
                    name="Records"
                )
            )

            tables.append(
                (
                    "Facility-wise Burden",
                    table,
                )
            )

    # --------------------------------------------------------
    # Ward
    # --------------------------------------------------------

    ward_column = _find_column(
        df,
        [
            "Ward Name",
            "Ward",
        ],
    )

    if ward_column:

        series = _clean_text_series(
            df,
            ward_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis("Ward")
                .reset_index(
                    name="Records"
                )
            )

            tables.append(
                (
                    "Ward-wise Burden",
                    table,
                )
            )

    # --------------------------------------------------------
    # Gender
    # --------------------------------------------------------

    gender_column = _find_column(
        df,
        [
            "Gender",
            "Sex",
        ],
    )

    if gender_column:

        series = _clean_text_series(
            df,
            gender_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis("Gender")
                .reset_index(
                    name="Records"
                )
            )

            tables.append(
                (
                    "Gender-wise Distribution",
                    table,
                )
            )

    # --------------------------------------------------------
    # Age Group
    # --------------------------------------------------------

    age_column = _find_column(
        df,
        [
            "Age Group",
            "Age_Group",
            "Age group",
            "Age",
        ],
    )

    if age_column:

        series = _clean_text_series(
            df,
            age_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis("Age Group")
                .reset_index(
                    name="Records"
                )
            )

            tables.append(
                (
                    "Age-wise Distribution",
                    table,
                )
            )

    # --------------------------------------------------------
    # OPD / IPD
    # --------------------------------------------------------

    opd_column = _find_column(
        df,
        [
            "OPD/IPD",
            "OPD IPD",
            "OPD_IPD",
        ],
    )

    if opd_column:

        series = _clean_text_series(
            df,
            opd_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis("OPD/IPD")
                .reset_index(
                    name="Records"
                )
            )

            tables.append(
                (
                    "OPD / IPD Distribution",
                    table,
                )
            )

    # --------------------------------------------------------
    # Month-wise
    # --------------------------------------------------------

    month_column = _find_column(
        df,
        [
            "Month",
        ],
    )

    if month_column:

        series = _clean_text_series(
            df,
            month_column,
        )

        if not series.empty:

            normalized = series.apply(
                _normalize_month
            )

            month_table = (
                normalized
                .value_counts()
                .rename_axis("Month")
                .reset_index(
                    name="Records"
                )
            )

            month_table = month_table[
                month_table["Month"].isin(
                    CALENDAR_MONTHS
                )
            ].copy()

            month_table["_order"] = (
                month_table["Month"]
                .map(MONTH_NUMBER_MAP)
            )

            month_table = (
                month_table
                .sort_values(
                    "_order"
                )
                .drop(
                    columns="_order"
                )
                .reset_index(
                    drop=True
                )
            )

            if not month_table.empty:

                tables.append(
                    (
                        "Month-wise Programme Trend",
                        month_table,
                    )
                )

    # --------------------------------------------------------
    # Year + Month
    # --------------------------------------------------------

    year_column = _find_column(
        df,
        [
            "Year",
            "Reporting Year",
            "Year of Reporting",
        ],
    )

    if (
        year_column
        and month_column
    ):

        temp = df[
            [
                year_column,
                month_column,
            ]
        ].copy()

        temp["Year"] = temp[
            year_column
        ].apply(
            _normalize_year
        )

        temp["Month"] = temp[
            month_column
        ].apply(
            _normalize_month
        )

        temp = temp[
            temp["Year"].astype(str).ne("")
            & temp["Month"].isin(
                CALENDAR_MONTHS
            )
        ].copy()

        if not temp.empty:

            temp["Year"] = pd.to_numeric(
                temp["Year"],
                errors="coerce",
            )

            temp = temp.dropna(
                subset=["Year"]
            )

            if not temp.empty:

                temp["Year"] = (
                    temp["Year"]
                    .astype(int)
                )

                temp["Month Number"] = (
                    temp["Month"]
                    .map(MONTH_NUMBER_MAP)
                )

                temp["Month-Year"] = (
                    temp["Month"]
                    + "-"
                    + temp["Year"]
                    .astype(str)
                )

                table = (
                    temp
                    .groupby(
                        [
                            "Year",
                            "Month Number",
                            "Month",
                            "Month-Year",
                        ],
                        as_index=False,
                    )
                    .size()
                    .rename(
                        columns={
                            "size": "Records"
                        }
                    )
                    .sort_values(
                        [
                            "Year",
                            "Month Number",
                        ]
                    )
                    .reset_index(
                        drop=True
                    )
                )

                tables.append(
                    (
                        "Year-wise / Month-wise Programme Trend",
                        table[
                            [
                                "Year",
                                "Month",
                                "Month-Year",
                                "Records",
                            ]
                        ],
                    )
                )

    # --------------------------------------------------------
    # Reporting Date
    # --------------------------------------------------------

    reporting_date_column = _find_column(
        df,
        [
            "Reporting Date",
        ],
    )

    if reporting_date_column:

        dates = pd.to_datetime(
            df[reporting_date_column],
            errors="coerce",
        )

        dates = dates.dropna()

        if not dates.empty:

            table = (
                dates
                .dt.normalize()
                .value_counts()
                .rename_axis(
                    "Reporting Date"
                )
                .reset_index(
                    name="Records"
                )
                .sort_values(
                    "Reporting Date"
                )
                .reset_index(
                    drop=True
                )
            )

            table["Reporting Date"] = (
                table["Reporting Date"]
                .dt.strftime(
                    "%d-%m-%Y"
                )
            )

            tables.append(
                (
                    "Reporting Date-wise Trend",
                    table,
                )
            )

    return tables


# ============================================================
# AUTOMATIC MANAGEMENT CHARTS
# ============================================================

def _build_auto_analysis_charts(df):
    charts = []

    if df is None or df.empty:
        return charts

    # --------------------------------------------------------
    # Disease
    # --------------------------------------------------------

    disease_column = _find_column(
        df,
        [
            "Disease",
        ],
    )

    if disease_column:

        series = _clean_text_series(
            df,
            disease_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis("Disease")
                .reset_index(
                    name="Records"
                )
            )

            charts.append(
                {
                    "title": "Disease-wise Burden",
                    "dataframe": table,
                    "x_column": "Disease",
                    "y_column": "Records",
                    "chart_type": "bar",
                }
            )

    # --------------------------------------------------------
    # Pathogen
    # --------------------------------------------------------

    pathogen_column = _find_column(
        df,
        [
            "Test Performed Pathogen Name",
            "Pathogen Name",
            "Test Performed Pathogen",
            "Pathogen",
        ],
    )

    if pathogen_column:

        series = _clean_text_series(
            df,
            pathogen_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis(
                    "Test Performed Pathogen Name"
                )
                .reset_index(
                    name="Records"
                )
            )

            charts.append(
                {
                    "title": (
                        "Test Performed / "
                        "Pathogen Name-wise Analysis"
                    ),
                    "dataframe": table,
                    "x_column": (
                        "Test Performed "
                        "Pathogen Name"
                    ),
                    "y_column": "Records",
                    "chart_type": "bar",
                }
            )

    # --------------------------------------------------------
    # Facility
    # --------------------------------------------------------

    facility_column = _find_column(
        df,
        [
            "Facility Name",
            "Facility",
        ],
    )

    if facility_column:

        series = _clean_text_series(
            df,
            facility_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis("Facility")
                .reset_index(
                    name="Records"
                )
            )

            charts.append(
                {
                    "title": "Facility-wise Burden",
                    "dataframe": table,
                    "x_column": "Facility",
                    "y_column": "Records",
                    "chart_type": "bar",
                }
            )

    # --------------------------------------------------------
    # Ward
    # --------------------------------------------------------

    ward_column = _find_column(
        df,
        [
            "Ward Name",
            "Ward",
        ],
    )

    if ward_column:

        series = _clean_text_series(
            df,
            ward_column,
        )

        if not series.empty:

            table = (
                series
                .value_counts()
                .rename_axis("Ward")
                .reset_index(
                    name="Records"
                )

            charts.append(
                {
                    "title": "Ward-wise Burden",
                    "dataframe": table,
                    "x_column": "Ward",
                    "y_column": "Records",
                    "chart_type": "bar",
                }
            )

    # --------------------------------------------------------
    # Month-wise
    # --------------------------------------------------------

    month_column = _find_column(
        df,
        [
            "Month",
        ],
    )

    if month_column:

        series = _clean_text_series(
            df,
            month_column,
        )

        if not series.empty:

            normalized = series.apply(
                _normalize_month
            )

            table = (
                normalized
                .value_counts()
                .rename_axis("Month")
                .reset_index(
                    name="Records"
                )
            )

            table = table[
                table["Month"].isin(
                    CALENDAR_MONTHS
                )
            ].copy()

            table["_order"] = (
                table["Month"]
                .map(MONTH_NUMBER_MAP)
            )

            table = (
                table
                .sort_values(
                    "_order"
                )
                .drop(
                    columns="_order"
                )
                .reset_index(
                    drop=True
                )
            )

            if not table.empty:

                charts.append(
                    {
                        "title": (
                            "Month-wise "
                            "Programme Trend"
                        ),
                        "dataframe": table,
                        "x_column": "Month",
                        "y_column": "Records",
                        "chart_type": "bar",
                    }
                )

    # --------------------------------------------------------
    # Reporting Date
    # --------------------------------------------------------

    reporting_date_column = _find_column(
        df,
        [
            "Reporting Date",
        ],
    )

    if reporting_date_column:

        dates = pd.to_datetime(
            df[reporting_date_column],
            errors="coerce",
        )

        dates = dates.dropna()

        if not dates.empty:

            table = (
                dates
                .dt.normalize()
                .value_counts()
                .rename_axis("Date")
                .reset_index(
                    name="Records"
                )
                .sort_values(
                    "Date"
                )
                .reset_index(
                    drop=True
                )
            )

            table["Date"] = (
                table["Date"]
                .dt.strftime(
                    "%d-%m-%Y"
                )
            )

            charts.append(
                {
                    "title": "Reporting Date Trend",
                    "dataframe": table,
                    "x_column": "Date",
                    "y_column": "Records",
                    "chart_type": "line",
                }
            )

    return charts


# ============================================================
# REPORT TABLE / CHART NORMALISATION
# ============================================================

def _normalise_tables(
    tables,
    df,
):
    result = []

    if tables:

        for item in tables:

            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
            ):

                title = item[0]
                dataframe = item[1]

                if (
                    dataframe is not None
                    and isinstance(
                        dataframe,
                        pd.DataFrame,
                    )
                    and not dataframe.empty
                ):

                    result.append(
                        (
                            str(title),
                            dataframe,
                        )
                    )

    # If caller supplied no tables,
    # build useful management analysis.
    if not result:

        result = _build_auto_analysis_tables(
            df
        )

    return result


def _normalise_charts(
    charts,
    df,
):
    result = []

    if charts:

        for chart in charts:

            if not isinstance(
                chart,
                dict,
            ):
                continue

            dataframe = chart.get(
                "dataframe"
            )

            if (
                dataframe is None
                or not isinstance(
                    dataframe,
                    pd.DataFrame,
                )
                or dataframe.empty
            ):
                continue

            result.append(
                {
                    "dataframe": dataframe,
                    "x_column": chart.get(
                        "x_column"
                    ),
                    "y_column": chart.get(
                        "y_column"
                    ),
                    "title": chart.get(
                        "title",
                        "Chart",
                    ),
                    "chart_type": chart.get(
                        "chart_type",
                        "bar",
                    ),
                }
            )

    if not result:

        result = _build_auto_analysis_charts(
            df
        )

    return result


# ============================================================
# PAGE REPORT
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
    Generate a management PDF for one dashboard section.

    Existing app.py can continue calling this function
    without modification.
    """

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=17 * mm,
        title=_safe_text(
            report_title
        ),
        author=DASHBOARD_TITLE,
    )

    styles = _styles()

    story = []

    record_count = (
        len(df)
        if df is not None
        else None
    )

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    _add_report_header(
        story,
        styles,
        report_title,
        report_period,
        filter_summary,
        record_count,
    )

    # --------------------------------------------------------
    # KPI
    # --------------------------------------------------------

    _add_kpi_table(
        story,
        styles,
        kpis,
    )

    # --------------------------------------------------------
    # NORMALISE OUTPUTS
    # --------------------------------------------------------

    report_charts = _normalise_charts(
        charts,
        df,
    )

    report_tables = _normalise_tables(
        tables,
        df,
    )

    # --------------------------------------------------------
    # CHARTS
    # --------------------------------------------------------

    if report_charts:

        story.append(
            Paragraph(
                "Visual Analysis",
                styles["SectionCustom"],
            )
        )

        for index, chart in enumerate(
            report_charts
        ):

            chart_image = _create_chart_image(
                chart.get("dataframe"),
                chart.get("x_column"),
                chart.get("y_column"),
                chart.get(
                    "title",
                    "Chart",
                ),
                chart.get(
                    "chart_type",
                    "bar",
                ),
            )

            if chart_image:

                block = [
                    Paragraph(
                        chart.get(
                            "title",
                            "Chart",
                        ),
                        styles[
                            "SubSectionCustom"
                        ],
                    ),
                    chart_image,
                    Spacer(1, 5),
                ]

                story.append(
                    KeepTogether(block)
                )

    # --------------------------------------------------------
    # TABLES
    # --------------------------------------------------------

    if report_tables:

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "Detailed Management Analysis",
                styles["SectionCustom"],
            )
        )

        for title, dataframe in report_tables:

            _add_dataframe_section(
                story,
                styles,
                title,
                dataframe,
            )

    # --------------------------------------------------------
    # REPORT SCOPE
    # --------------------------------------------------------

    if df is not None and not df.empty:

        story.append(
            Spacer(1, 8)
        )

        story.append(
            Paragraph(
                "Report Scope",
                styles["SectionCustom"],
            )
        )

        story.append(
            Paragraph(
                "This report represents the records "
                "available under the dashboard filters "
                "active at the time of report generation. "
                "The PDF is a static management report and "
                "does not retain dashboard interactivity.",
                styles["ManagementCustom"],
            )
        )

        story.append(
            Paragraph(
                "Total records represented in the current "
                "scope: "
                + _format_number(
                    len(df)
                ),
                styles["ManagementCustom"],
            )
        )

    # --------------------------------------------------------
    # FOOT NOTE
    # --------------------------------------------------------

    story.append(
        Spacer(1, 10)
    )

    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["SmallCustom"],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["SmallCustom"],
        )
    )

    # --------------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------------

    document.build(
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
    """
    Generate one consolidated PDF containing all supplied
    dashboard sections.

    Compatible with the existing app.py.
    """

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

    pages = pages or []

    # ========================================================
    # COVER PAGE
    # ========================================================

    story.append(
        Spacer(1, 25 * mm)
    )

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
        Spacer(1, 12)
    )

    story.append(
        Paragraph(
            "Complete Dashboard Management Report",
            styles["Heading1"],
        )
    )

    story.append(
        Spacer(1, 8)
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
                "Global Filter Scope: "
                + _safe_text(filter_summary),
                styles["SmallCustom"],
            )
        )

    story.append(
        Spacer(1, 15)
    )

    story.append(
        Paragraph(
            "This consolidated report contains the "
            "management outputs supplied by the dashboard "
            "sections using the current Global Dashboard "
            "Filter scope.",
            styles["ManagementCustom"],
        )
    )

    # ========================================================
    # CONTENTS
    # ========================================================

    story.append(
        Spacer(1, 8)
    )

    story.append(
        Paragraph(
            "Dashboard Sections Included",
            styles["SectionCustom"],
        )
    )

    page_names = []

    for page_index, page in enumerate(
        pages,
        start=1,
    ):

        title = page.get(
            "title",
            f"Dashboard Section {page_index}",
        )

        page_names.append(
            [
                str(page_index),
                _safe_text(title),
            ]
        )

    if page_names:

        contents_table = Table(
            [
                [
                    "No.",
                    "Dashboard Section",
                ]
            ]
            + page_names,
            colWidths=[
                20 * mm,
                130 * mm,
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
                        colors.HexColor(
                            "#9e9e9e"
                        ),
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

        story.append(
            contents_table
        )

    # ========================================================
    # EACH DASHBOARD SECTION
    # ========================================================

    for page_index, page in enumerate(
        pages,
        start=1,
    ):

        title = page.get(
            "title",
            f"Dashboard Section {page_index}",
        )

        df = page.get("df")

        kpis = page.get("kpis")

        tables = page.get("tables")

        charts = page.get("charts")

        # ----------------------------------------------------
        # New section
        # ----------------------------------------------------

        story.append(
            PageBreak()
        )

        _add_report_header(
            story,
            styles,
            title,
            report_period,
            filter_summary,
            len(df)
            if df is not None
            else None,
        )

        story.append(
            Paragraph(
                "Section "
                + str(page_index)
                + " of "
                + str(len(pages)),
                styles["SmallCustom"],
            )
        )

        story.append(
            Spacer(1, 5)
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
        # Charts
        # ----------------------------------------------------

        report_charts = _normalise_charts(
            charts,
            df,
        )

        if report_charts:

            story.append(
                Paragraph(
                    "Visual Analysis",
                    styles["SectionCustom"],
                )
            )

            for chart in report_charts:

                chart_image = _create_chart_image(
                    chart.get(
                        "dataframe"
                    ),
                    chart.get(
                        "x_column"
                    ),
                    chart.get(
                        "y_column"
                    ),
                    chart.get(
                        "title",
                        "Chart",
                    ),
                    chart.get(
                        "chart_type",
                        "bar",
                    ),
                )

                if chart_image:

                    story.append(
                        Paragraph(
                            chart.get(
                                "title",
                                "Chart",
                            ),
                            styles[
                                "SubSectionCustom"
                            ],
                        )
                    )

                    story.append(
                        chart_image
                    )

                    story.append(
                        Spacer(1, 5)
                    )

        # ----------------------------------------------------
        # Tables
        # ----------------------------------------------------

        report_tables = _normalise_tables(
            tables,
            df,
        )

        if report_tables:

            story.append(
                Paragraph(
                    "Detailed Management Analysis",
                    styles["SectionCustom"],
                )
            )

            for (
                table_title,
                dataframe,
            ) in report_tables:

                _add_dataframe_section(
                    story,
                    styles,
                    table_title,
                    dataframe,
                )

        # ----------------------------------------------------
        # Section Scope
        # ----------------------------------------------------

        if df is not None and not df.empty:

            story.append(
                Spacer(1, 6)
            )

            story.append(
                Paragraph(
                    "Management Scope",
                    styles["SectionCustom"],
                )
            )

            story.append(
                Paragraph(
                    "This section represents the records "
                    "available under the Global Dashboard "
                    "filters active at the time of report "
                    "generation.",
                    styles["ManagementCustom"],
                )
            )

    # ========================================================
    # FINAL NOTE
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
            styles["SectionCustom"],
        )
    )

    story.append(
        Paragraph(
            "This consolidated PDF is intended for "
            "programme monitoring, management review, "
            "data interpretation and official reporting. "
            "It represents the dashboard data and report "
            "outputs available at the time of generation.",
            styles["ManagementCustom"],
        )
    )

    story.append(
        Spacer(1, 10)
    )

    story.append(
        Paragraph(
            "Important: The PDF is a static representation "
            "of the selected dashboard scope. Interactive "
            "controls such as checkboxes, filters and "
            "dashboard navigation are not interactive "
            "inside the PDF.",
            styles["ManagementCustom"],
        )
    )

    story.append(
        Spacer(1, 10)
    )

    story.append(
        Paragraph(
            DASHBOARD_TITLE,
            styles["SmallCustom"],
        )
    )

    story.append(
        Paragraph(
            DASHBOARD_SUBTITLE,
            styles["SmallCustom"],
        )
    )

    # ========================================================
    # BUILD
    # ========================================================

    document.build(
        story,
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )

    buffer.seek(0)

    return buffer.getvalue()
