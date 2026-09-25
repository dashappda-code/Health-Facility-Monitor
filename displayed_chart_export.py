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

# Minimum useful chart height.
# This is NOT used as a fixed chart height.
MIN_CHART_HEIGHT_MM = 55

# Maximum chart height only acts as a page-safety limit.
# The chart's original aspect ratio is always preserved.
MAX_CHART_HEIGHT_MM = 250


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
    - HConcat / VConcat / Concat
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
    Capture every Altair chart rendered through
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

    The chart is rendered from its actual Vega-Lite
    specification so its natural width/height ratio
    is preserved.
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
# GET ORIGINAL IMAGE DIMENSIONS
# ============================================================

def _get_image_dimensions(png_bytes):
    """
    Return the original rendered PNG dimensions.
    """

    try:
        from PIL import Image

        image = Image.open(
            io.BytesIO(
                png_bytes
            )
        )

        width, height = image.size

        if width > 0 and height > 0:
            return (
                float(width),
                float(height),
            )

    except Exception:
        pass

    return (
        None,
        None,
    )


# ============================================================
# GET NATURAL CHART SIZE
# ============================================================

def _get_chart_image_size(
    png_bytes,
    available_width,
    available_height,
):
    """
    Calculate the PDF chart size from the actual rendered
    image dimensions.

    IMPORTANT:
    - Original aspect ratio is preserved.
    - Width is maximized.
    - Height is NOT arbitrarily forced.
    - The chart is reduced only if it cannot fit.
    """

    image_width, image_height = (
        _get_image_dimensions(
            png_bytes
        )
    )

    if not image_width or not image_height:
        return (
            available_width,
            min(
                available_height,
                90,
            ),
        )

    # --------------------------------------------------------
    # Natural aspect ratio
    # --------------------------------------------------------

    aspect_ratio = (
        image_height
        / image_width
    )

    # --------------------------------------------------------
    # Start with complete report width.
    # --------------------------------------------------------

    width = available_width

    height = (
        width
        * aspect_ratio
    )

    # --------------------------------------------------------
    # Prevent an extremely small chart.
    #
    # This does NOT distort the image.
    # It simply allows the chart to occupy its natural
    # proportional height.
    # --------------------------------------------------------

    minimum_height = (
        MIN_CHART_HEIGHT_MM
        * 2.834645669
    )

    if height < minimum_height:
        height = minimum_height

        width = (
            height
            / aspect_ratio
        )

        if width > available_width:
            width = available_width
            height = (
                width
                * aspect_ratio
            )

    # --------------------------------------------------------
    # Maximum safety limit.
    # --------------------------------------------------------

    if height > available_height:
        height = available_height
        width = (
            height
            / aspect_ratio
        )

    return (
        width,
        height,
    )


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

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Body
    # --------------------------------------------------------

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
# BUILD PDF
# ============================================================

def _build_pdf(
    charts,
    report_title="Displayed Charts & Tables Report",
    filter_summary=None,
):
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

    # ========================================================
    # EXACT REPORT WIDTH
    # ========================================================

    available_width = (
        page_width
        - (
            PDF_MARGIN_MM
            * 2
            * mm
        )
    )

    # ========================================================
    # PAGE CONTENT HEIGHT
    # ========================================================

    available_page_height = (
        page_height
        - (
            PDF_MARGIN_MM
            * 2
            * mm
        )
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DisplayedChartTitle",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        spaceAfter=8,
    )

    section_style = ParagraphStyle(
        "SectionLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor(
            "#4B5563"
        ),
        spaceAfter=4,
    )

    chart_title_style = ParagraphStyle(
        "ChartTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        spaceAfter=8,
        textColor=colors.HexColor(
            "#111827"
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
        "FilterSummary",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor(
            "#555555"
        ),
        spaceAfter=10,
    )

    footer_style = ParagraphStyle(
        "FooterNote",
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

    # ========================================================
    # EACH SECTION
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
        # NEW PAGE FOR EVERY SECTION
        # ----------------------------------------------------

        story.append(
            PageBreak()
        )

        # ----------------------------------------------------
        # SECTION NAME
        # ----------------------------------------------------

        story.append(
            Paragraph(
                f"Section {index}",
                section_style,
            )
        )

        # ----------------------------------------------------
        # CHART TITLE
        # ----------------------------------------------------

        story.append(
            Paragraph(
                html.escape(
                    str(title)
                ),
                chart_title_style,
            )
        )

        # ----------------------------------------------------
        # Calculate chart dimensions
        # ----------------------------------------------------

        reserved_height = (
            70 * mm
        )

        max_chart_height = (
            available_page_height
            - reserved_height
        )

        if max_chart_height < (
            MIN_CHART_HEIGHT_MM * mm
        ):
            max_chart_height = (
                MIN_CHART_HEIGHT_MM
                * mm
            )

        chart_width, chart_height = (
            _get_chart_image_size(
                png_bytes,
                available_width,
                max_chart_height,
            )
        )

        # ----------------------------------------------------
        # CHART
        # ----------------------------------------------------

        chart_image = Image(
            io.BytesIO(
                png_bytes
            ),
            width=chart_width,
            height=chart_height,
        )

        story.append(
            chart_image
        )

        story.append(
            Spacer(
                1,
                8,
            )
        )

        # ----------------------------------------------------
        # TABLE TITLE
        # ----------------------------------------------------

        report_table = (
            _build_report_table(
                data,
                available_width,
            )
        )

        if report_table is not None:

            story.append(
                Paragraph(
                    "Displayed Data",
                    table_heading_style,
                )
            )

            story.append(
                report_table
            )

        # ----------------------------------------------------
        # FOOTER
        # ----------------------------------------------------

        story.append(
            Spacer(
                1,
                8,
            )
        )

        story.append(
            Paragraph(
                "MSU Mumbai Health Programme Management Dashboard",
                footer_style,
            )
        )

    # ========================================================
    # BUILD
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
    # PDF DOWNLOAD
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
    # PNG ZIP DOWNLOAD
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
