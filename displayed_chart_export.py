import io
import hashlib
import zipfile
import html
from contextlib import contextmanager

import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

DISPLAYED_CHARTS_KEY = "displayed_chart_exports"
CAPTURE_ACTIVE_KEY = "displayed_chart_capture_active"

MAX_TABLE_ROWS = 300
MAX_TABLE_COLUMNS = 14

PDF_MARGIN_MM = 12
MAX_CHART_HEIGHT_MM = 140


# ============================================================
# REGISTRY HELPERS
# ============================================================

def _get_registry():
    if DISPLAYED_CHARTS_KEY not in st.session_state:
        st.session_state[DISPLAYED_CHARTS_KEY] = []

    return st.session_state[DISPLAYED_CHARTS_KEY]


def _clear_registry():
    st.session_state[DISPLAYED_CHARTS_KEY] = []


def _is_capture_active():
    return bool(
        st.session_state.get(
            CAPTURE_ACTIVE_KEY,
            False,
        )
    )


# ============================================================
# SAFE DATAFRAME
# ============================================================

def _safe_dataframe(value):
    if isinstance(value, pd.DataFrame):
        return value.copy()

    if isinstance(value, pd.Series):
        return value.to_frame()

    if value is None:
        return pd.DataFrame()

    try:
        return pd.DataFrame(value)
    except Exception:
        return pd.DataFrame()


# ============================================================
# EXTRACT DATAFRAME FROM ALTAIR CHART
# ============================================================

def _extract_chart_dataframe(chart):
    """
    Extract chart data from an Altair/Vega-Lite chart.

    Supports:
    - Inline data
    - Named datasets
    - Layered charts
    - Concatenated charts
    """

    try:
        chart_dict = chart.to_dict()

        # ----------------------------------------------------
        # Direct data
        # ----------------------------------------------------

        data = chart_dict.get("data")

        if isinstance(data, dict):
            values = data.get("values")

            if isinstance(values, list):
                return _safe_dataframe(values)

        # ----------------------------------------------------
        # Named datasets
        # ----------------------------------------------------

        datasets = chart_dict.get("datasets")

        if isinstance(datasets, dict):
            for _, values in datasets.items():
                if isinstance(values, list):
                    frame = _safe_dataframe(values)

                    if not frame.empty:
                        return frame

        # ----------------------------------------------------
        # Layer
        # ----------------------------------------------------

        layers = chart_dict.get("layer")

        if isinstance(layers, list):
            frames = []

            for layer in layers:
                if not isinstance(layer, dict):
                    continue

                layer_data = layer.get("data")

                if isinstance(layer_data, dict):
                    values = layer_data.get("values")

                    if isinstance(values, list):
                        frame = _safe_dataframe(values)

                        if not frame.empty:
                            frames.append(frame)

            if frames:
                try:
                    return pd.concat(
                        frames,
                        ignore_index=True,
                    )
                except Exception:
                    return frames[0]

        # ----------------------------------------------------
        # HConcat / VConcat / Concat
        # ----------------------------------------------------

        for key in (
            "hconcat",
            "vconcat",
            "concat",
        ):
            charts = chart_dict.get(key)

            if isinstance(charts, list):
                frames = []

                for child in charts:
                    if not isinstance(child, dict):
                        continue

                    child_data = child.get("data")

                    if isinstance(child_data, dict):
                        values = child_data.get("values")

                        if isinstance(values, list):
                            frame = _safe_dataframe(values)

                            if not frame.empty:
                                frames.append(frame)

                if frames:
                    try:
                        return pd.concat(
                            frames,
                            ignore_index=True,
                        )
                    except Exception:
                        return frames[0]

    except Exception:
        pass

    return pd.DataFrame()


# ============================================================
# FORMAT TABLE VALUE
# ============================================================

def _format_table_value(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))

        return f"{value:.2f}"

    return str(value)


# ============================================================
# PREPARE REPORT TABLE
# ============================================================

def _prepare_report_table(df):
    if df is None or df.empty:
        return pd.DataFrame()

    table = df.copy()

    if len(table) > MAX_TABLE_ROWS:
        table = table.head(MAX_TABLE_ROWS)

    if len(table.columns) > MAX_TABLE_COLUMNS:
        table = table.iloc[:, :MAX_TABLE_COLUMNS]

    for column in table.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(
                table[column]
            ):
                table[column] = table[column].dt.strftime(
                    "%Y-%m-%d"
                )
            else:
                table[column] = table[column].apply(
                    _format_table_value
                )
        except Exception:
            table[column] = table[column].astype(str)

    return table


# ============================================================
# CAPTURE DISPLAYED CHARTS
# ============================================================

@contextmanager
def capture_displayed_charts():
    """
    Captures every Altair chart rendered through
    st.altair_chart() while this context is active.
    """

    original_altair_chart = st.altair_chart

    _clear_registry()

    st.session_state[CAPTURE_ACTIVE_KEY] = True

    def _captured_altair_chart(
        chart,
        *args,
        **kwargs,
    ):
        registry = _get_registry()

        try:
            chart_data = _extract_chart_dataframe(
                chart
            )
        except Exception:
            chart_data = pd.DataFrame()

        title = ""

        try:
            chart_dict = chart.to_dict()

            title_data = chart_dict.get(
                "title"
            )

            if isinstance(
                title_data,
                str,
            ):
                title = title_data

            elif isinstance(
                title_data,
                dict,
            ):
                title = str(
                    title_data.get(
                        "text",
                        "",
                    )
                )
        except Exception:
            pass

        registry.append(
            {
                "chart": chart,
                "data": chart_data,
                "title": title,
            }
        )

        return original_altair_chart(
            chart,
            *args,
            **kwargs,
        )

    st.altair_chart = _captured_altair_chart

    try:
        yield
    finally:
        st.altair_chart = original_altair_chart
        st.session_state[CAPTURE_ACTIVE_KEY] = False


# ============================================================
# CHART TO PNG
# ============================================================

def _chart_to_png(chart):
    """
    Convert Altair chart to PNG using vl-convert.
    """

    try:
        import vl_convert as vlc

        chart_dict = chart.to_dict()

        png_bytes = vlc.vegalite_to_png(
            chart_dict,
            scale=2,
        )

        if png_bytes:
            return png_bytes

    except Exception:
        pass

    return None


# ============================================================
# FINGERPRINT
# ============================================================

def _make_fingerprint(chart):
    try:
        payload = chart.to_json()

        return hashlib.md5(
            payload.encode("utf-8")
        ).hexdigest()

    except Exception:
        return str(id(chart))


# ============================================================
# BUILD REPORT TABLE
# ============================================================

def _build_report_table(
    df,
    table_width,
):
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

    table_df = _prepare_report_table(
        df
    )

    if table_df.empty:
        return None

    styles = getSampleStyleSheet()

    header_style = ParagraphStyle(
        "ReportTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.8,
        leading=8,
        alignment=TA_LEFT,
    )

    body_style = ParagraphStyle(
        "ReportTableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
        alignment=TA_LEFT,
    )

    data = [
        [
            Paragraph(
                html.escape(
                    str(column)
                ),
                header_style,
            )
            for column in table_df.columns
        ]
    ]

    for _, row in table_df.iterrows():
        data.append(
            [
                Paragraph(
                    html.escape(
                        _format_table_value(
                            value
                        )
                    ),
                    body_style,
                )
                for value in row.tolist()
            ]
        )

    number_of_columns = len(
        table_df.columns
    )

    if number_of_columns <= 0:
        return None

    column_width = (
        table_width
        / number_of_columns
    )

    col_widths = [
        column_width
        for _ in range(
            number_of_columns
        )
    ]

    table = Table(
        data,
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
# GET CHART IMAGE SIZE
# ============================================================

def _get_chart_image_size(
    png_bytes,
    max_width,
    max_height,
):
    """
    Preserve original chart aspect ratio.

    Chart uses the available width first.
    Height is automatically calculated.

    If required height is too large,
    chart is proportionally reduced.
    """

    try:
        from PIL import Image

        image = Image.open(
            io.BytesIO(
                png_bytes
            )
        )

        pixel_width, pixel_height = (
            image.size
        )

        if (
            not pixel_width
            or not pixel_height
        ):
            return (
                max_width,
                max_height,
            )

        ratio = (
            pixel_height
            / pixel_width
        )

        width = max_width
        height = (
            width * ratio
        )

        if height > max_height:
            height = max_height
            width = (
                height
                / ratio
            )

        return (
            width,
            height,
        )

    except Exception:
        return (
            max_width,
            max_height,
        )


# ============================================================
# BUILD COMBINED CHART + TABLE PDF
# ============================================================

def _build_pdf(
    charts,
    report_title="Displayed Charts & Tables Report",
    filter_summary=None,
):
    """
    Builds a presentation-ready PDF where every section
    contains:

        1. Chart
        2. The chart's displayed data table

    Chart and table share the same report width.
    """

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        PageBreak,
        KeepTogether,
    )

    if not charts:
        return None

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=PDF_MARGIN_MM * mm,
        leftMargin=PDF_MARGIN_MM * mm,
        topMargin=PDF_MARGIN_MM * mm,
        bottomMargin=PDF_MARGIN_MM * mm,
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

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CombinedReportTitle",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        spaceAfter=8,
    )

    section_style = ParagraphStyle(
        "CombinedSection",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=colors.HexColor(
            "#6B7280"
        ),
        spaceAfter=3,
    )

    chart_title_style = ParagraphStyle(
        "CombinedChartTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14,
        spaceAfter=7,
        textColor=colors.HexColor(
            "#1F2937"
        ),
    )

    table_heading_style = ParagraphStyle(
        "TableHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor(
            "#374151"
        ),
        spaceAfter=5,
    )

    filter_style = ParagraphStyle(
        "CombinedFilterSummary",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor(
            "#555555"
        ),
        spaceAfter=10,
    )

    footer_style = ParagraphStyle(
        "CombinedFooter",
        parent=styles["Normal"],
        fontSize=7,
        leading=9,
        textColor=colors.HexColor(
            "#777777"
        ),
    )

    story = []

    # ========================================================
    # REPORT HEADER
    # ========================================================

    story.append(
        Spacer(
            1,
            18,
        )
    )

    story.append(
        Paragraph(
            html.escape(
                report_title
            ),
            title_style,
        )
    )

    story.append(
        Spacer(
            1,
            6,
        )
    )

    if filter_summary:

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
                    f"<b>{html.escape(str(key))}</b>: "
                    f"{html.escape(str(value))}"
                )

            if summary_parts:
                story.append(
                    Paragraph(
                        "<br/>".join(
                            summary_parts
                        ),
                        filter_style,
                    )
                )

        else:
            story.append(
                Paragraph(
                    html.escape(
                        str(
                            filter_summary
                        )
                    ),
                    filter_style,
                )
            )

    story.append(
        Spacer(
            1,
            10,
        )
    )

    # ========================================================
    # EACH CHART + TABLE SECTION
    # ========================================================

    for index, item in enumerate(
        charts,
        start=1,
    ):
        chart = item.get(
            "chart"
        )

        data = item.get(
            "data"
        )

        title = item.get(
            "title",
            "",
        )

        if chart is None:
            continue

        png_bytes = _chart_to_png(
            chart
        )

        if not png_bytes:
            continue

        if not title:
            title = (
                f"Chart {index}"
            )

        # ----------------------------------------------------
        # Every chart-table section starts on new page.
        # ----------------------------------------------------

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                f"Section {index}",
                section_style,
            )
        )

        story.append(
            Paragraph(
                html.escape(
                    str(title)
                ),
                chart_title_style,
            )
        )

        # ----------------------------------------------------
        # CHART
        # ----------------------------------------------------

        chart_width, chart_height = (
            _get_chart_image_size(
                png_bytes,
                available_width,
                MAX_CHART_HEIGHT_MM * mm,
            )
        )

        chart_image = Image(
            io.BytesIO(
                png_bytes
            ),
            width=chart_width,
            height=chart_height,
        )

        # ----------------------------------------------------
        # TABLE
        # ----------------------------------------------------

        report_table = (
            _build_report_table(
                data,
                available_width,
            )
        )

        section_items = [
            chart_image,
            Spacer(
                1,
                8,
            ),
        ]

        if report_table is not None:

            section_items.extend(
                [
                    Paragraph(
                        "Displayed Data",
                        table_heading_style,
                    ),
                    report_table,
                ]
            )

        section_items.extend(
            [
                Spacer(
                    1,
                    8,
                ),
                Paragraph(
                    "MSU Mumbai Health Programme Management Dashboard",
                    footer_style,
                ),
            ]
        )

        # Keep chart + table together when possible.
        story.append(
            KeepTogether(
                section_items
            )
        )

    # ========================================================
    # BUILD PDF
    # ========================================================

    doc.build(
        story
    )

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# SAFE FILENAME
# ============================================================

def _safe_filename(
    filename,
    extension,
):
    filename = str(
        filename
        or "export"
    )

    allowed = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "_-"
    )

    filename = "".join(
        character
        if character in allowed
        else "_"
        for character in filename
    )

    filename = filename.strip(
        "_"
    )

    if not filename:
        filename = "export"

    if not extension.startswith(
        "."
    ):
        extension = (
            "."
            + extension
        )

    return (
        filename
        + extension
    )


# ============================================================
# BUILD PNG ZIP
# ============================================================

def _build_png_zip(charts):
    if not charts:
        return None

    zip_buffer = io.BytesIO()

    used_names = set()

    with zipfile.ZipFile(
        zip_buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        for index, item in enumerate(
            charts,
            start=1,
        ):
            chart = item.get(
                "chart"
            )

            if chart is None:
                continue

            png_bytes = _chart_to_png(
                chart
            )

            if not png_bytes:
                continue

            title = item.get(
                "title",
                "",
            )

            if not title:
                title = (
                    f"Chart_{index}"
                )

            base_name = _safe_filename(
                title,
                ".png",
            )

            if base_name in used_names:
                base_name = _safe_filename(
                    f"{title}_{index}",
                    ".png",
                )

            used_names.add(
                base_name
            )

            archive.writestr(
                base_name,
                png_bytes,
            )

    zip_buffer.seek(0)

    return zip_buffer.getvalue()


# ============================================================
# DOWNLOAD CONTROLS
# ============================================================

def render_displayed_chart_download_controls(
    filter_summary=None,
    base_filename="Displayed_Charts",
):
    charts = _get_registry()

    if not charts:
        st.info(
            "No displayed charts were captured on this page."
        )
        return

    st.subheader(
        "Download Displayed Charts & Tables"
    )

    st.caption(
        f"{len(charts)} displayed chart(s) captured from this page."
    )

    # ========================================================
    # REPORT CONTENTS
    # ========================================================

    with st.expander(
        "📋 Report Contents",
        expanded=False,
    ):
        for index, item in enumerate(
            charts,
            start=1,
        ):
            title = (
                item.get(
                    "title"
                )
                or f"Chart {index}"
            )

            data = item.get(
                "data"
            )

            rows = (
                len(data)
                if isinstance(
                    data,
                    pd.DataFrame,
                )
                else 0
            )

            columns = (
                len(data.columns)
                if isinstance(
                    data,
                    pd.DataFrame,
                )
                else 0
            )

            st.write(
                f"{index}. {title} "
                f"({rows} rows × {columns} columns)"
            )

    # ========================================================
    # COMBINED PDF
    # ========================================================

    try:

        pdf_bytes = _build_pdf(
            charts=charts,
            report_title=(
                "MSU Mumbai - "
                "Displayed Charts & Tables Report"
            ),
            filter_summary=filter_summary,
        )

        if pdf_bytes:

            st.download_button(
                label=(
                    "📊 Download Chart + Displayed Table PDF"
                ),
                data=pdf_bytes,
                file_name=_safe_filename(
                    base_filename,
                    ".pdf",
                ),
                mime="application/pdf",
                use_container_width=True,
            )

    except Exception as exc:

        st.error(
            "Combined Chart + Table PDF could not be generated."
        )

        with st.expander(
            "Technical details"
        ):
            st.code(
                str(exc)
            )

    # ========================================================
    # PNG ZIP
    # ========================================================

    try:

        zip_bytes = _build_png_zip(
            charts
        )

        if zip_bytes:

            st.download_button(
                label=(
                    "🖼️ Download Displayed Charts PNGs"
                ),
                data=zip_bytes,
                file_name=_safe_filename(
                    f"{base_filename}_PNGs",
                    ".zip",
                ),
                mime="application/zip",
                use_container_width=True,
            )

    except Exception as exc:

        st.error(
            "Displayed chart PNG export could not be generated."
        )

        with st.expander(
            "Technical details"
        ):
            st.code(
                str(exc)
            )
