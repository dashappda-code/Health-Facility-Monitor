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

# Increased only to make displayed charts larger in PDF.
# Chart width remains based on available report width,
# while height is adjusted automatically according to aspect ratio.
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
    - DataFrame-backed Altair charts
    - Layered / concatenated charts where possible
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
                    return _safe_dataframe(values)

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
        # HConcat / VConcat
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
# PREPARE REPORT TABLE
# ============================================================

def _prepare_report_table(df):
    if df is None or df.empty:
        return pd.DataFrame()

    table = df.copy()

    # Limit rows
    if len(table) > MAX_TABLE_ROWS:
        table = table.head(MAX_TABLE_ROWS)

    # Limit columns
    if len(table.columns) > MAX_TABLE_COLUMNS:
        table = table.iloc[:, :MAX_TABLE_COLUMNS]

    # Convert problematic values
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
    Captures charts rendered using st.altair_chart()
    while the context manager is active.
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
            chart_data = _extract_chart_dataframe(chart)
        except Exception:
            chart_data = pd.DataFrame()

        title = ""

        try:
            chart_dict = chart.to_dict()

            title_data = chart_dict.get("title")

            if isinstance(title_data, str):
                title = title_data

            elif isinstance(title_data, dict):
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

    if isinstance(
        value,
        float,
    ):
        if value.is_integer():
            return str(int(value))

        return f"{value:.2f}"

    return str(value)


# ============================================================
# BUILD REPORT TABLE
# ============================================================

def _build_report_table(df):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    if df is None or df.empty:
        return None

    table_df = _prepare_report_table(df)

    if table_df.empty:
        return None

    data = [
        [
            str(column)
            for column in table_df.columns
        ]
    ]

    for _, row in table_df.iterrows():
        data.append(
            [
                _format_table_value(value)
                for value in row.tolist()
            ]
        )

    table = Table(
        data,
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#E9EEF5"),
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
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.grey,
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

    Width first fills the available report width.
    Height is then calculated automatically.

    If the calculated height is too large,
    the chart is scaled down proportionally.
    """

    from PIL import Image

    try:
        image = Image.open(
            io.BytesIO(png_bytes)
        )

        pixel_width, pixel_height = image.size

        if not pixel_width or not pixel_height:
            return (
                max_width,
                max_height,
            )

        ratio = (
            pixel_height
            / pixel_width
        )

        # First use full available width.
        width = max_width
        height = width * ratio

        # Only reduce size if height exceeds limit.
        if height > max_height:
            height = max_height
            width = height / ratio

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
# BUILD PDF
# ============================================================

def _build_pdf(
    charts,
    report_title="Displayed Charts Report",
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

    available_height = (
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
        fontSize=15,
        leading=18,
        spaceAfter=8,
    )

    chart_title_style = ParagraphStyle(
        "ChartTitle",
        parent=styles["Heading2"],
        fontSize=10.5,
        leading=13,
        spaceAfter=5,
        textColor=colors.HexColor(
            "#222222"
        ),
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

    story = []

    # --------------------------------------------------------
    # Report title
    # --------------------------------------------------------

    story.append(
        Paragraph(
            html.escape(
                report_title
            ),
            title_style,
        )
    )

    # --------------------------------------------------------
    # Filter summary
    # --------------------------------------------------------

    if filter_summary:
        if isinstance(
            filter_summary,
            dict,
        ):
            summary_parts = []

            for key, value in filter_summary.items():
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
                        str(filter_summary)
                    ),
                    filter_style,
                )
            )

    # --------------------------------------------------------
    # Charts
    # --------------------------------------------------------

    for index, item in enumerate(
        charts,
        start=1,
    ):
        chart = item.get("chart")
        data = item.get("data")
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

        story.append(
            Paragraph(
                html.escape(
                    str(title)
                ),
                chart_title_style,
            )
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # Chart uses full available report width.
        # Height automatically follows chart aspect ratio.
        # Only the maximum height limits extremely tall charts.
        # ----------------------------------------------------

        chart_width, chart_height = (
            _get_chart_image_size(
                png_bytes,
                available_width,
                MAX_CHART_HEIGHT_MM
                * mm,
            )
        )

        image = Image(
            io.BytesIO(
                png_bytes
            ),
            width=chart_width,
            height=chart_height,
        )

        story.append(image)

        # ----------------------------------------------------
        # Table below chart
        # ----------------------------------------------------

        report_table = _build_report_table(
            data
        )

        if report_table is not None:
            story.append(
                Spacer(
                    1,
                    5,
                )
            )

            story.append(
                report_table
            )

        # ----------------------------------------------------
        # Spacing
        # ----------------------------------------------------

        story.append(
            Spacer(
                1,
                10,
            )
        )

        # Keep each chart section readable.
        # Page break occurs naturally if required.
        if index < len(charts):
            story.append(
                Spacer(
                    1,
                    4,
                )
            )

    doc.build(story)

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
        filename or "export"
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
            "." + extension
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
        "Download Displayed Charts"
    )

    st.caption(
        f"{len(charts)} displayed chart(s) captured from this page."
    )

    # --------------------------------------------------------
    # Report contents
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    try:
        pdf_bytes = _build_pdf(
            charts=charts,
            report_title=(
                "MSU Mumbai - "
                "Displayed Charts Report"
            ),
            filter_summary=filter_summary,
        )

        if pdf_bytes:
            st.download_button(
                label=(
                    "📄 Download Displayed Charts PDF"
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
            "Displayed Charts PDF could not be generated."
        )

        with st.expander(
            "Technical details"
        ):
            st.code(
                str(exc)
            )

    # --------------------------------------------------------
    # PNG ZIP
    # --------------------------------------------------------

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
