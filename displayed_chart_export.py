import io
import json
import hashlib
import zipfile
from contextlib import contextmanager
from datetime import datetime

import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

DISPLAYED_CHARTS_KEY = "displayed_chart_exports"
DISPLAYED_CHART_CACHE_KEY = "displayed_chart_export_cache"

DEFAULT_PDF_FILENAME = (
    "MSU_Mumbai_Charts_Trends_Displayed_Charts.pdf"
)

DEFAULT_ZIP_FILENAME = (
    "MSU_Mumbai_Charts_Trends_Displayed_Charts_PNG.zip"
)


# ============================================================
# OPTIONAL DEPENDENCIES
# ============================================================

try:
    import vl_convert as vlc

    VLC_AVAILABLE = True

except Exception:
    vlc = None
    VLC_AVAILABLE = False


try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    REPORTLAB_AVAILABLE = True

except Exception:
    colors = None
    TA_LEFT = None
    A4 = None
    getSampleStyleSheet = None
    inch = None
    ImageReader = None
    Image = None
    PageBreak = None
    Paragraph = None
    SimpleDocTemplate = None
    Spacer = None
    REPORTLAB_AVAILABLE = False


# ============================================================
# DISPLAYED CHART CAPTURE
# ============================================================

@contextmanager
def capture_displayed_charts():
    """
    Capture the exact Altair charts rendered during the
    Charts & Trends page.

    This temporarily wraps Streamlit's:
        - st.altair_chart()
        - st.markdown()

    The original Streamlit functions are restored automatically
    after the render is complete.
    """

    captured_charts = []

    current_title = {
        "value": "Displayed Chart"
    }

    original_altair_chart = st.altair_chart
    original_markdown = st.markdown

    # --------------------------------------------------------
    # Markdown wrapper
    # --------------------------------------------------------

    def captured_markdown(
        body,
        *args,
        **kwargs,
    ):
        try:

            if isinstance(body, str):

                text = body.strip()

                # Detect headings such as:
                # ### 🦠 Monthly Disease Comparison
                # ## Heading
                # #### Heading
                if text.startswith("#"):

                    lines = text.splitlines()

                    if lines:

                        first_line = lines[0].strip()

                        if (
                            first_line.startswith("### ")
                            or first_line.startswith("## ")
                            or first_line.startswith("# ")
                        ):

                            heading = first_line.lstrip("#").strip()

                            if heading:
                                current_title["value"] = heading

        except Exception:
            pass

        return original_markdown(
            body,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Altair wrapper
    # --------------------------------------------------------

    def captured_altair_chart(
        chart,
        *args,
        **kwargs,
    ):
        try:

            title = (
                current_title.get(
                    "value",
                    "Displayed Chart",
                )
                or "Displayed Chart"
            )

            # ------------------------------------------------
            # Generate filename
            # ------------------------------------------------

            filename = _safe_filename(
                title
            )

            captured_charts.append(
                {
                    "chart": chart,
                    "title": title,
                    "filename": filename,
                }
            )

        except Exception:
            pass

        return original_altair_chart(
            chart,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Activate wrappers
    # --------------------------------------------------------

    st.altair_chart = captured_altair_chart
    st.markdown = captured_markdown

    # --------------------------------------------------------
    # Store empty registry before rendering
    # --------------------------------------------------------

    st.session_state[
        DISPLAYED_CHARTS_KEY
    ] = []

    try:

        yield captured_charts

    finally:

        # ----------------------------------------------------
        # Restore original Streamlit functions
        # ----------------------------------------------------

        st.altair_chart = original_altair_chart
        st.markdown = original_markdown

        # ----------------------------------------------------
        # Save captured charts
        # ----------------------------------------------------

        st.session_state[
            DISPLAYED_CHARTS_KEY
        ] = captured_charts


# ============================================================
# SAFE FILENAME
# ============================================================

def _safe_filename(value):
    """
    Convert a chart title into a safe filename.
    """

    if value is None:
        value = "displayed_chart"

    text = str(value).strip()

    if not text:
        text = "displayed_chart"

    replacements = {
        "/": "_",
        "\\": "_",
        ":": "_",
        "*": "_",
        "?": "_",
        '"': "_",
        "<": "_",
        ">": "_",
        "|": "_",
        " ": "_",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new,
        )

    # Remove common emoji / unusual characters
    cleaned = []

    for character in text:

        if (
            character.isalnum()
            or character in {
                "_",
                "-",
                ".",
            }
        ):
            cleaned.append(character)

    text = "".join(cleaned)

    while "__" in text:
        text = text.replace(
            "__",
            "_",
        )

    text = text.strip(
        "_"
    )

    if not text:
        text = "displayed_chart"

    return text.lower()


# ============================================================
# GET DISPLAYED CHARTS
# ============================================================

def get_displayed_charts():
    """
    Return charts captured during the current page render.
    """

    charts = st.session_state.get(
        DISPLAYED_CHARTS_KEY,
        [],
    )

    if not isinstance(
        charts,
        list,
    ):
        return []

    return charts


# ============================================================
# CHART SPECIFICATION
# ============================================================

def _prepare_vegalite_spec(chart):
    """
    Convert an Altair chart object into a Vega-Lite specification
    suitable for PNG export.
    """

    if chart is None:
        return None

    if not hasattr(
        chart,
        "to_dict",
    ):
        return None

    spec = chart.to_dict()

    if not isinstance(
        spec,
        dict,
    ):
        return None

    # --------------------------------------------------------
    # Dashboard charts use container width.
    #
    # For PDF/PNG export we provide a fixed wide canvas.
    # --------------------------------------------------------

    current_width = spec.get(
        "width"
    )

    if (
        current_width is None
        or current_width == "container"
        or current_width == "step"
    ):
        spec["width"] = 1000

    return spec


# ============================================================
# CHART PNG CONVERSION
# ============================================================

def _chart_to_png(chart):
    """
    Convert an Altair chart to a high-resolution PNG.
    """

    if not VLC_AVAILABLE:

        raise RuntimeError(
            "vl-convert-python is not installed. "
            "Please add 'vl-convert-python' to requirements.txt "
            "and redeploy the Streamlit app."
        )

    spec = _prepare_vegalite_spec(
        chart
    )

    if spec is None:

        raise RuntimeError(
            "The displayed chart could not be converted "
            "to a Vega-Lite specification."
        )

    try:

        png_bytes = vlc.vegalite_to_png(
            spec,
            scale=2,
        )

    except Exception as exc:

        raise RuntimeError(
            "Could not convert the displayed Altair chart "
            f"to PNG: {exc}"
        ) from exc

    if not png_bytes:

        raise RuntimeError(
            "The chart conversion returned an empty PNG."
        )

    return png_bytes


# ============================================================
# CHART FINGERPRINT
# ============================================================

def _chart_fingerprint(
    chart,
    title,
):
    """
    Create a stable fingerprint for the displayed chart.

    This allows the export to be reused when the dashboard
    reruns without changing the displayed chart.
    """

    spec = _prepare_vegalite_spec(
        chart
    )

    if spec is None:
        spec = {}

    try:

        serialized = json.dumps(
            spec,
            sort_keys=True,
            default=str,
        )

    except Exception:

        serialized = str(
            spec
        )

    payload = (
        str(title)
        + "|"
        + serialized
    )

    return hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# CREATE PNG FILES
# ============================================================

def _create_chart_png_files(
    charts,
):
    """
    Convert all displayed charts into PNG files.

    Returns:
        list of dictionaries:
        [
            {
                "title": ...,
                "filename": ...,
                "png": bytes,
            }
        ]
    """

    if not charts:
        return []

    results = []

    for index, item in enumerate(
        charts,
        start=1,
    ):

        chart = item.get(
            "chart"
        )

        title = item.get(
            "title",
            f"Displayed Chart {index}",
        )

        filename = item.get(
            "filename"
        )

        if not filename:

            filename = _safe_filename(
                title
            )

        png_bytes = _chart_to_png(
            chart
        )

        results.append(
            {
                "title": title,
                "filename": (
                    f"{index:02d}_{filename}.png"
                ),
                "png": png_bytes,
            }
        )

    return results


# ============================================================
# CREATE ZIP
# ============================================================

def _create_png_zip(
    png_files,
):
    """
    Create ZIP archive containing all displayed chart PNGs.
    """

    output = io.BytesIO()

    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        for item in png_files:

            archive.writestr(
                item["filename"],
                item["png"],
            )

    output.seek(0)

    return output.getvalue()


# ============================================================
# PDF PAGE FOOTER
# ============================================================

def _draw_pdf_footer(
    canvas,
    doc,
):
    """
    Draw footer on every PDF page.
    """

    canvas.saveState()

    page_number = canvas.getPageNumber()

    canvas.setFont(
        "Helvetica",
        8,
    )

    canvas.setFillColor(
        colors.grey
    )

    canvas.drawString(
        0.65 * inch,
        0.4 * inch,
        "MSU Mumbai Public Health Surveillance Dashboard",
    )

    canvas.drawRightString(
        7.85 * inch,
        0.4 * inch,
        f"Page {page_number}",
    )

    canvas.restoreState()


# ============================================================
# CREATE PDF
# ============================================================

def _create_pdf(
    png_files,
    filter_summary="All records",
):
    """
    Create a PDF containing the same displayed chart images
    captured from the dashboard.
    """

    if not REPORTLAB_AVAILABLE:

        raise RuntimeError(
            "ReportLab is not available. "
            "Please ensure the 'reportlab' package is installed."
        )

    if not png_files:

        raise RuntimeError(
            "No displayed charts are available for PDF export."
        )

    output = io.BytesIO()

    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.65 * inch,
        title=(
            "MSU Mumbai Charts & Trends "
            "Displayed Charts Export"
        ),
        author=(
            "MSU Mumbai Public Health "
            "Surveillance Dashboard"
        ),
    )

    styles = getSampleStyleSheet()

    title_style = styles["Title"]
    title_style.fontName = "Helvetica-Bold"
    title_style.fontSize = 18
    title_style.leading = 22
    title_style.alignment = TA_LEFT
    title_style.textColor = colors.HexColor(
        "#1f2937"
    )

    subtitle_style = styles["Normal"]
    subtitle_style.fontName = "Helvetica"
    subtitle_style.fontSize = 9
    subtitle_style.leading = 13
    subtitle_style.textColor = colors.HexColor(
        "#555555"
    )

    chart_title_style = styles["Heading2"]
    chart_title_style.fontName = "Helvetica-Bold"
    chart_title_style.fontSize = 13
    chart_title_style.leading = 17
    chart_title_style.textColor = colors.HexColor(
        "#1f2937"
    )

    story = []

    # --------------------------------------------------------
    # PDF HEADER
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "MSU Mumbai Public Health Surveillance Dashboard",
            title_style,
        )
    )

    story.append(
        Spacer(
            1,
            0.12 * inch,
        )
    )

    story.append(
        Paragraph(
            "Charts & Trends — Displayed Charts Export",
            chart_title_style,
        )
    )

    story.append(
        Spacer(
            1,
            0.08 * inch,
        )
    )

    generated_time = datetime.now().strftime(
        "%d %b %Y, %I:%M %p"
    )

    story.append(
        Paragraph(
            f"<b>Applied Filters:</b> "
            f"{_escape_html(filter_summary)}",
            subtitle_style,
        )
    )

    story.append(
        Paragraph(
            f"<b>Generated:</b> "
            f"{generated_time}",
            subtitle_style,
        )
    )

    story.append(
        Spacer(
            1,
            0.22 * inch,
        )
    )

    # --------------------------------------------------------
    # CHARTS
    # --------------------------------------------------------

    for index, item in enumerate(
        png_files,
        start=1,
    ):

        title = item.get(
            "title",
            f"Displayed Chart {index}",
        )

        png_bytes = item.get(
            "png"
        )

        story.append(
            Paragraph(
                f"{index}. {_escape_html(title)}",
                chart_title_style,
            )
        )

        story.append(
            Spacer(
                1,
                0.10 * inch,
            )
        )

        image_stream = io.BytesIO(
            png_bytes
        )

        image_reader = ImageReader(
            image_stream
        )

        image_width, image_height = (
            image_reader.getSize()
        )

        available_width = document.width

        available_height = (
            document.height
            - 0.65 * inch
        )

        width_scale = (
            available_width
            / float(image_width)
        )

        height_scale = (
            available_height
            / float(image_height)
        )

        scale = min(
            width_scale,
            height_scale,
            1.0,
        )

        final_width = (
            image_width * scale
        )

        final_height = (
            image_height * scale
        )

        chart_image = Image(
            image_stream,
            width=final_width,
            height=final_height,
        )

        chart_image.hAlign = "LEFT"

        story.append(
            chart_image
        )

        if index < len(
            png_files
        ):

            story.append(
                PageBreak()
            )

    # --------------------------------------------------------
    # BUILD PDF
    # --------------------------------------------------------

    document.build(
        story,
        onFirstPage=_draw_pdf_footer,
        onLaterPages=_draw_pdf_footer,
    )

    output.seek(0)

    return output.getvalue()


# ============================================================
# HTML ESCAPE
# ============================================================

def _escape_html(value):
    """
    Minimal HTML escaping for ReportLab Paragraph.
    """

    if value is None:
        return ""

    text = str(value)

    text = text.replace(
        "&",
        "&amp;",
    )

    text = text.replace(
        "<",
        "&lt;",
    )

    text = text.replace(
        ">",
        "&gt;",
    )

    return text


# ============================================================
# CREATE EXPORTS
# ============================================================

def create_displayed_chart_exports(
    charts,
    filter_summary="All records",
):
    """
    Create PDF and PNG ZIP exports for displayed charts.

    Returns:
        {
            "pdf": bytes,
            "zip": bytes,
            "png_files": list,
        }
    """

    if not charts:

        raise RuntimeError(
            "No displayed charts are available."
        )

    png_files = _create_chart_png_files(
        charts
    )

    pdf_bytes = _create_pdf(
        png_files,
        filter_summary=filter_summary,
    )

    zip_bytes = _create_png_zip(
        png_files
    )

    return {
        "pdf": pdf_bytes,
        "zip": zip_bytes,
        "png_files": png_files,
    }


# ============================================================
# EXPORT CACHE
# ============================================================

def _build_export_fingerprint(
    charts,
    filter_summary,
):
    """
    Build fingerprint for the complete displayed chart set.
    """

    parts = [
        str(
            filter_summary
        )
    ]

    for item in charts:

        chart = item.get(
            "chart"
        )

        title = item.get(
            "title",
            "Displayed Chart",
        )

        parts.append(
            _chart_fingerprint(
                chart,
                title,
            )
        )

    payload = "|".join(
        parts
    )

    return hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# RENDER DOWNLOAD CONTROLS
# ============================================================

def render_displayed_chart_download_controls(
    filter_summary="All records",
    base_filename="MSU_Mumbai_Charts_Trends_Displayed_Charts",
):
    """
    Render PDF and PNG download controls for the charts that
    were actually displayed on the Charts & Trends page.
    """

    charts = get_displayed_charts()

    st.markdown(
        "### 📥 Download Displayed Charts"
    )

    if not charts:

        st.info(
            "No charts are currently available "
            "for displayed-chart export."
        )

        return

    st.caption(
        f"{len(charts)} displayed chart(s) are available "
        "for export. The export uses the same Altair chart "
        "objects rendered on the dashboard."
    )

    # --------------------------------------------------------
    # Dependency check
    # --------------------------------------------------------

    if not VLC_AVAILABLE:

        st.error(
            "Displayed chart export requires "
            "'vl-convert-python'. "
            "Please add it to requirements.txt and redeploy "
            "the application."
        )

        return

    if not REPORTLAB_AVAILABLE:

        st.error(
            "PDF export requires the 'reportlab' package. "
            "Please ensure reportlab is installed."
        )

        return

    # --------------------------------------------------------
    # Build fingerprint
    # --------------------------------------------------------

    fingerprint = _build_export_fingerprint(
        charts,
        filter_summary,
    )

    cached = st.session_state.get(
        DISPLAYED_CHART_CACHE_KEY
    )

    # --------------------------------------------------------
    # Reuse cached export when possible
    # --------------------------------------------------------

    if (
        isinstance(cached, dict)
        and cached.get(
            "fingerprint"
        ) == fingerprint
        and cached.get(
            "pdf"
        )
        and cached.get(
            "zip"
        )
    ):

        export_data = cached

    else:

        try:

            with st.spinner(
                "Preparing displayed charts for download..."
            ):

                created = (
                    create_displayed_chart_exports(
                        charts,
                        filter_summary=filter_summary,
                    )
                )

            export_data = {
                "fingerprint": fingerprint,
                "pdf": created["pdf"],
                "zip": created["zip"],
                "png_files": created[
                    "png_files"
                ],
            }

            st.session_state[
                DISPLAYED_CHART_CACHE_KEY
            ] = export_data

        except Exception as exc:

            st.error(
                "Displayed chart export could not be created."
            )

            st.exception(
                exc
            )

            return

    # --------------------------------------------------------
    # Download buttons
    # --------------------------------------------------------

    pdf_filename = (
        f"{base_filename}.pdf"
    )

    zip_filename = (
        f"{base_filename}_PNG.zip"
    )

    download_columns = st.columns(
        2
    )

    with download_columns[0]:

        st.download_button(
            label="📄 Download Displayed Charts PDF",
            data=export_data["pdf"],
            file_name=pdf_filename,
            mime="application/pdf",
            use_container_width=True,
            key="download_displayed_charts_pdf",
        )

    with download_columns[1]:

        st.download_button(
            label="🖼️ Download Displayed Charts PNG Images",
            data=export_data["zip"],
            file_name=zip_filename,
            mime="application/zip",
            use_container_width=True,
            key="download_displayed_charts_png",
        )

    # --------------------------------------------------------
    # Export contents
    # --------------------------------------------------------

    with st.expander(
        "View charts included in this export",
        expanded=False,
    ):

        for index, item in enumerate(
            export_data.get(
                "png_files",
                [],
            ),
            start=1,
        ):

            st.write(
                f"{index}. {item.get('title', 'Displayed Chart')}"
            )
