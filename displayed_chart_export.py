import io
import hashlib
import zipfile
import html
import re
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

MIN_CHART_HEIGHT_MM = 55
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
# TEXT CLEANING
# ============================================================

def _clean_heading_text(value):
    """
    Convert Streamlit heading content into a clean plain title.
    """

    if value is None:
        return ""

    try:
        text = str(value).strip()
    except Exception:
        return ""

    if not text:
        return ""

    # Remove common markdown heading markers
    text = re.sub(
        r"^\s*#{1,6}\s*",
        "",
        text,
    )

    # Remove common divider-only content
    if text in (
        "---",
        "***",
        "___",
    ):
        return ""

    return text.strip()


def _looks_like_heading(value):
    """
    Decide whether a captured markdown string looks like
    a section heading rather than ordinary explanatory text.
    """

    text = _clean_heading_text(value)

    if not text:
        return False

    # Ignore very long paragraphs
    if len(text) > 120:
        return False

    # Ignore obvious normal text
    if text.endswith(".") and len(text) > 45:
        return False

    return True


# ============================================================
# EXTRACT DATAFRAME FROM ALTAIR CHART
# ============================================================

def _extract_chart_dataframe(chart):
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
# CAPTURE DISPLAYED CHARTS + SECTION HEADINGS
# ============================================================

@contextmanager
def capture_displayed_charts():
    """
    Capture:
        - Altair charts
        - Streamlit subheaders
        - Markdown headings

    The most recent detected section heading is attached
    to the next displayed chart.
    """

    original_altair_chart = st.altair_chart
    original_subheader = st.subheader
    original_markdown = st.markdown

    _clear_registry()

    # --------------------------------------------------------
    # Local heading state
    # --------------------------------------------------------

    heading_state = {
        "current": "",
        "history": [],
    }

    # --------------------------------------------------------
    # Capture subheader
    # --------------------------------------------------------

    def _captured_subheader(
        body,
        *args,
        **kwargs,
    ):
        text = _clean_heading_text(
            body
        )

        if text:
            heading_state["current"] = text
            heading_state["history"].append(
                text
            )

        return original_subheader(
            body,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Capture markdown headings
    # --------------------------------------------------------

    def _captured_markdown(
        body,
        *args,
        **kwargs,
    ):
        text = ""

        try:
            raw_text = str(body)

            # Capture markdown H1-H6
            match = re.search(
                r"(?m)^\s*#{1,6}\s+(.+?)\s*$",
                raw_text,
            )

            if match:
                candidate = match.group(1)
                candidate = _clean_heading_text(
                    candidate
                )

                if _looks_like_heading(
                    candidate
                ):
                    text = candidate

        except Exception:
            text = ""

        if text:
            heading_state["current"] = text
            heading_state["history"].append(
                text
            )

        return original_markdown(
            body,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Capture Altair
    # --------------------------------------------------------

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

        chart_title = ""

        try:
            chart_dict = chart.to_dict()

            title_data = chart_dict.get(
                "title"
            )

            if isinstance(
                title_data,
                str,
            ):
                chart_title = title_data

            elif isinstance(
                title_data,
                dict,
            ):
                chart_title = str(
                    title_data.get(
                        "text",
                        "",
                    )
                )

        except Exception:
            pass

        # ----------------------------------------------------
        # Actual dashboard section heading
        # ----------------------------------------------------

        section_name = (
            heading_state["current"]
        )

        # ----------------------------------------------------
        # If there is no captured heading,
        # fall back to Altair title.
        # ----------------------------------------------------

        if not section_name:
            section_name = (
                _clean_heading_text(
                    chart_title
                )
            )

        # ----------------------------------------------------
        # Final fallback
        # ----------------------------------------------------

        if not section_name:
            section_name = (
                f"Chart {len(registry) + 1}"
            )

        registry.append(
            {
                "chart": chart,
                "data": chart_data,
                "title": chart_title,
                "section_name": section_name,
            }
        )

        return original_altair_chart(
            chart,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Activate monkey patches
    # --------------------------------------------------------

    st.altair_chart = (
        _captured_altair_chart
    )

    st.subheader = (
        _captured_subheader
    )

    st.markdown = (
        _captured_markdown
    )

    try:
        yield

    finally:
        st.altair_chart = (
            original_altair_chart
        )

        st.subheader = (
            original_subheader
        )

        st.markdown = (
            original_markdown
        )


# ============================================================
# CHART TO PNG
# ============================================================

def _chart_to_png(chart):
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
# IMAGE DIMENSIONS
# ============================================================

def _get_image_dimensions(png_bytes):
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
# CHART IMAGE SIZE
# ============================================================

def _get_chart_image_size(
    png_bytes,
    available_width,
    available_height,
):
    """
    Preserve the actual rendered chart aspect ratio.

    The chart is NOT stretched.

    Width is maximized first.
    Height is calculated automatically.
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
                100,
            ),
        )

    ratio = (
        image_height
        / image_width
    )

    # --------------------------------------------------------
    # Start with full report width.
    # --------------------------------------------------------

    width = available_width

    height = (
        width
        * ratio
    )

    # --------------------------------------------------------
    # Minimum height
    # --------------------------------------------------------

    min_height = (
        MIN_CHART_HEIGHT_MM
        * 2.834645669
    )

    if height < min_height:

        height = min_height

        width = (
            height
            / ratio
        )

        if width > available_width:

            width = available_width

            height = (
                width
                * ratio
            )

    # --------------------------------------------------------
    # Maximum height
    # --------------------------------------------------------

    max_height = min(
        available_height,
        MAX_CHART_HEIGHT_MM
        * 2.834645669,
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


# ============================================================
# REPORT TABLE
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

    table = Table(
        data,
        colWidths=[
            column_width
            for _ in range(
                number_of_columns
            )
        ],
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

    available_width = (
        page_width
        - (
            PDF_MARGIN_MM
            * 2
            * mm
        )
    )

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
        spaceAfter=3,
    )

    section_name_style = ParagraphStyle(
        "SectionName",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor(
            "#111827"
        ),
        spaceAfter=5,
    )

    chart_title_style = ParagraphStyle(
        "ChartTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor(
            "#374151"
        ),
        spaceAfter=7,
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
    # EACH CHART SECTION
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

        section_name = (
            item.get(
                "section_name"
            )
            or ""
        )

        chart_title = (
            item.get(
                "title"
            )
            or ""
        )

        if chart is None:
            continue

        png_bytes = _chart_to_png(
            chart
        )

        if not png_bytes:
            continue

        # ----------------------------------------------------
        # Fallback section name
        # ----------------------------------------------------

        if not section_name:

            section_name = (
                chart_title
                or f"Chart {index}"
            )

        # ----------------------------------------------------
        # New page
        # ----------------------------------------------------

        story.append(
            PageBreak()
        )

        # ----------------------------------------------------
        # SECTION NUMBER
        # ----------------------------------------------------

        story.append(
            Paragraph(
                f"Section {index}",
                section_style,
            )
        )

        # ----------------------------------------------------
        # ACTUAL SECTION NAME
        # ----------------------------------------------------

        story.append(
            Paragraph(
                html.escape(
                    str(
                        section_name
                    )
                ),
                section_name_style,
            )
        )

        # ----------------------------------------------------
        # If chart has a different title, show it separately.
        # ----------------------------------------------------

        if (
            chart_title
            and chart_title.strip()
            and chart_title.strip()
            != str(
                section_name
            ).strip()
        ):

            story.append(
                Paragraph(
                    html.escape(
                        str(
                            chart_title
                        )
                    ),
                    chart_title_style,
                )
            )

        # ----------------------------------------------------
        # Chart available height
        # ----------------------------------------------------

        reserved_height = (
            65 * mm
        )

        max_chart_height = (
            available_page_height
            - reserved_height
        )

        if max_chart_height < (
            MIN_CHART_HEIGHT_MM
            * mm
        ):
            max_chart_height = (
                MIN_CHART_HEIGHT_MM
                * mm
            )

        # ----------------------------------------------------
        # Calculate natural image size
        # ----------------------------------------------------

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

        story.append(
            Image(
                io.BytesIO(
                    png_bytes
                ),
                width=chart_width,
                height=chart_height,
            )
        )

        story.append(
            Spacer(
                1,
                8,
            )
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

            section_name = (
                item.get(
                    "section_name"
                )
                or ""
            )

            title = (
                item.get(
                    "title"
                )
                or ""
            )

            base_title = (
                section_name
                or title
                or f"Chart_{index}"
            )

            base_name = _safe_filename(
                base_title,
                ".png",
            )

            if base_name in used_names:

                base_name = _safe_filename(
                    f"{base_title}_{index}",
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
            section_name = (
                item.get(
                    "section_name"
                )
                or ""
            )

            title = (
                item.get(
                    "title"
                )
                or ""
            )

            if section_name:
                display_name = section_name
            elif title:
                display_name = title
            else:
                display_name = (
                    f"Chart {index}"
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
                f"{index}. {display_name} "
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
