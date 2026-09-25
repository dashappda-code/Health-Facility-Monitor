import io
import html
import re
from contextlib import contextmanager

import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

DISPLAYED_CHARTS_KEY = "displayed_chart_exports"

MAX_TABLE_ROWS = 300
MAX_TABLE_COLUMNS = 14

PDF_MARGIN_MM = 12

# Normal export chart height limits
MIN_CHART_HEIGHT_MM = 55
MAX_CHART_HEIGHT_MM = 145

# Special wide-chart export height
MONTHLY_DISEASE_HEIGHT_MM = 88


# ============================================================
# REGISTRY
# ============================================================

def _get_registry():
    if DISPLAYED_CHARTS_KEY not in st.session_state:
        st.session_state[DISPLAYED_CHARTS_KEY] = []

    return st.session_state[DISPLAYED_CHARTS_KEY]


def _clear_registry():
    st.session_state[DISPLAYED_CHARTS_KEY] = []


# ============================================================
# TEXT HELPERS
# ============================================================

def _clean_heading_text(value):
    if value is None:
        return ""

    try:
        text = str(value).strip()
    except Exception:
        return ""

    if not text:
        return ""

    text = re.sub(
        r"^\s*#{1,6}\s*",
        "",
        text,
    )

    return text.strip()


def _looks_like_heading(value):
    text = _clean_heading_text(value)

    if not text:
        return False

    if len(text) > 120:
        return False

    return True


# ============================================================
# CHART DATA EXTRACTION
# ============================================================

def _extract_chart_dataframe(chart):
    try:
        chart_dict = chart.to_dict()

        # ----------------------------------------------------
        # Direct values
        # ----------------------------------------------------

        data = chart_dict.get("data")

        if isinstance(data, dict):

            values = data.get("values")

            if isinstance(values, list):
                return pd.DataFrame(values)

        # ----------------------------------------------------
        # Named datasets
        # ----------------------------------------------------

        datasets = chart_dict.get("datasets")

        if isinstance(datasets, dict):

            for _, values in datasets.items():

                if isinstance(values, list):

                    frame = pd.DataFrame(values)

                    if not frame.empty:
                        return frame

        # ----------------------------------------------------
        # Layers
        # ----------------------------------------------------

        layers = chart_dict.get("layer")

        if isinstance(layers, list):

            frames = []

            for layer in layers:

                if not isinstance(layer, dict):
                    continue

                layer_data = layer.get("data")

                if isinstance(
                    layer_data,
                    dict,
                ):

                    values = layer_data.get(
                        "values"
                    )

                    if isinstance(
                        values,
                        list,
                    ):

                        frame = pd.DataFrame(
                            values
                        )

                        if not frame.empty:
                            frames.append(
                                frame
                            )

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

            charts = chart_dict.get(
                key
            )

            if isinstance(
                charts,
                list,
            ):

                frames = []

                for child in charts:

                    if not isinstance(
                        child,
                        dict,
                    ):
                        continue

                    child_data = child.get(
                        "data"
                    )

                    if isinstance(
                        child_data,
                        dict,
                    ):

                        values = (
                            child_data.get(
                                "values"
                            )
                        )

                        if isinstance(
                            values,
                            list,
                        ):

                            frame = pd.DataFrame(
                                values
                            )

                            if not frame.empty:
                                frames.append(
                                    frame
                                )

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
# CHART TITLE
# ============================================================

def _get_chart_title(chart):
    try:

        chart_dict = chart.to_dict()

        title = chart_dict.get(
            "title"
        )

        if isinstance(
            title,
            str,
        ):
            return title.strip()

        if isinstance(
            title,
            dict,
        ):

            return str(
                title.get(
                    "text",
                    "",
                )
            ).strip()

    except Exception:
        pass

    return ""


# ============================================================
# CAPTURE DISPLAYED CHARTS
# ============================================================

@contextmanager
def capture_displayed_charts():

    original_altair_chart = (
        st.altair_chart
    )

    original_subheader = (
        st.subheader
    )

    original_header = (
        st.header
    )

    original_title = (
        st.title
    )

    original_markdown = (
        st.markdown
    )

    _clear_registry()

    heading_state = {
        "current": "",
    }

    # --------------------------------------------------------
    # Capture title
    # --------------------------------------------------------

    def _captured_title(
        body,
        *args,
        **kwargs,
    ):

        text = _clean_heading_text(
            body
        )

        if text:
            heading_state["current"] = text

        return original_title(
            body,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Capture header
    # --------------------------------------------------------

    def _captured_header(
        body,
        *args,
        **kwargs,
    ):

        text = _clean_heading_text(
            body
        )

        if text:
            heading_state["current"] = text

        return original_header(
            body,
            *args,
            **kwargs,
        )

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

        detected_heading = ""

        try:

            raw_text = str(body)

            match = re.search(
                r"(?m)^\s*#{1,6}\s+(.+?)\s*$",
                raw_text,
            )

            if match:

                candidate = (
                    match.group(1)
                )

                candidate = (
                    _clean_heading_text(
                        candidate
                    )
                )

                if _looks_like_heading(
                    candidate
                ):

                    detected_heading = (
                        candidate
                    )

        except Exception:
            pass

        if detected_heading:
            heading_state["current"] = (
                detected_heading
            )

        return original_markdown(
            body,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Capture Altair chart
    # --------------------------------------------------------

    def _captured_altair_chart(
        chart,
        *args,
        **kwargs,
    ):

        registry = _get_registry()

        chart_title = (
            _get_chart_title(
                chart
            )
        )

        chart_data = (
            _extract_chart_dataframe(
                chart
            )
        )

        section_name = (
            heading_state["current"]
        )

        if not section_name:
            section_name = (
                chart_title
            )

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
    # Activate capture
    # --------------------------------------------------------

    st.title = _captured_title
    st.header = _captured_header
    st.subheader = _captured_subheader
    st.markdown = _captured_markdown
    st.altair_chart = _captured_altair_chart

    try:
        yield

    finally:

        st.title = original_title
        st.header = original_header
        st.subheader = original_subheader
        st.markdown = original_markdown
        st.altair_chart = original_altair_chart


# ============================================================
# MONTHLY DISEASE COMPARISON DETECTION
# ============================================================

def _is_monthly_disease_comparison(item):
    section_name = str(
        item.get(
            "section_name",
            "",
        )
    ).lower()

    chart_title = str(
        item.get(
            "title",
            "",
        )
    ).lower()

    combined = (
        section_name
        + " "
        + chart_title
    )

    return (
        "monthly disease comparison"
        in combined
    )


# ============================================================
# PREPARE EXPORT CHART SPEC
# ============================================================

def _prepare_chart_for_export(item):
    """
    Creates an export-only version of the Altair chart.

    Original dashboard chart is never modified.
    """

    chart = item.get(
        "chart"
    )

    if chart is None:
        return None

    try:

        export_chart = chart

        # ----------------------------------------------------
        # Monthly Disease Comparison
        # ----------------------------------------------------
        # Force a wide presentation-friendly layout.
        # This affects PDF export only.
        # ----------------------------------------------------

        if _is_monthly_disease_comparison(
            item
        ):

            export_chart = chart.properties(
                width=1000,
                height=320,
            )

        else:

            # ------------------------------------------------
            # For other charts, give Altair a wide canvas.
            # Height is kept from the original chart where
            # possible.
            # ------------------------------------------------

            chart_dict = chart.to_dict()

            original_height = (
                chart_dict.get(
                    "height"
                )
            )

            if isinstance(
                original_height,
                (int, float),
            ):

                height = int(
                    original_height
                )

                height = max(
                    260,
                    min(
                        height,
                        520,
                    ),
                )

            else:
                height = 360

            export_chart = chart.properties(
                width=1000,
                height=height,
            )

        return export_chart

    except Exception:
        return chart


# ============================================================
# CHART TO PNG
# ============================================================

def _chart_to_png(item):
    try:

        import vl_convert as vlc

        export_chart = (
            _prepare_chart_for_export(
                item
            )
        )

        if export_chart is None:
            return None

        chart_dict = (
            export_chart.to_dict()
        )

        return vlc.vegalite_to_png(
            chart_dict,
            scale=2,
        )

    except Exception:
        return None


# ============================================================
# IMAGE DIMENSIONS
# ============================================================

def _get_image_dimensions(
    png_bytes
):
    try:

        from PIL import Image

        image = Image.open(
            io.BytesIO(
                png_bytes
            )
        )

        width, height = image.size

        if (
            width > 0
            and height > 0
        ):
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
# IMAGE SIZE FOR PDF
# ============================================================

def _get_chart_image_size(
    item,
    png_bytes,
    available_width,
    available_height,
):
    """
    Full available PDF width.
    Height calculated from actual image aspect ratio.
    """

    image_width, image_height = (
        _get_image_dimensions(
            png_bytes
        )
    )

    if (
        not image_width
        or not image_height
    ):

        return (
            available_width,
            min(
                available_height,
                100 * 2.834645669,
            ),
        )

    ratio = (
        image_height
        / image_width
    )

    width = available_width

    height = (
        width
        * ratio
    )

    # --------------------------------------------------------
    # Monthly Disease Comparison
    # --------------------------------------------------------

    if _is_monthly_disease_comparison(
        item
    ):

        preferred_height = (
            MONTHLY_DISEASE_HEIGHT_MM
            * 2.834645669
        )

        if height > preferred_height:

            height = preferred_height

            width = (
                height
                / ratio
            )

            # If width becomes too small,
            # return to full width.
            if width < (
                available_width
                * 0.75
            ):

                width = available_width

                height = (
                    width
                    * ratio
                )

    # --------------------------------------------------------
    # Normal charts
    # --------------------------------------------------------

    else:

        min_height = (
            MIN_CHART_HEIGHT_MM
            * 2.834645669
        )

        max_height = (
            MAX_CHART_HEIGHT_MM
            * 2.834645669
        )

        max_height = min(
            max_height,
            available_height,
        )

        if height < min_height:

            height = min_height

            width = (
                height
                / ratio
            )

        if height > max_height:

            height = max_height

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

    return (
        width,
        height,
    )


# ============================================================
# FORMAT TABLE VALUE
# ============================================================

def _format_table_value(
    value
):
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
            return str(
                int(value)
            )

        return f"{value:.2f}"

    return str(value)


# ============================================================
# PREPARE TABLE
# ============================================================

def _prepare_report_table(
    df
):
    if (
        df is None
        or df.empty
    ):
        return pd.DataFrame()

    table = df.copy()

    if len(table) > MAX_TABLE_ROWS:

        table = table.head(
            MAX_TABLE_ROWS
        )

    if (
        len(table.columns)
        > MAX_TABLE_COLUMNS
    ):

        table = table.iloc[
            :,
            :MAX_TABLE_COLUMNS,
        ]

    for column in table.columns:

        try:

            if pd.api.types.is_datetime64_any_dtype(
                table[column]
            ):

                table[column] = (
                    table[column]
                    .dt.strftime(
                        "%Y-%m-%d"
                    )
                )

            else:

                table[column] = (
                    table[column]
                    .apply(
                        _format_table_value
                    )
                )

        except Exception:

            table[column] = (
                table[column]
                .astype(str)
            )

    return table


# ============================================================
# BUILD REPORT TABLE
# ============================================================

def _build_report_table(
    df,
    table_width,
):
    from reportlab import colors
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

    if (
        df is None
        or df.empty
    ):
        return None

    table_df = (
        _prepare_report_table(
            df
        )
    )

    if table_df.empty:
        return None

    styles = (
        getSampleStyleSheet()
    )

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

    number_of_columns = (
        len(
            table_df.columns
        )
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
# PDF STYLES
# ============================================================

def _get_pdf_styles():
    from reportlab import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )

    styles = (
        getSampleStyleSheet()
    )

    return {
        "title": ParagraphStyle(
            "PDFTitle",
            parent=styles["Heading1"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            spaceAfter=8,
        ),
        "section_number": ParagraphStyle(
            "SectionNumber",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor(
                "#4B5563"
            ),
            spaceAfter=3,
        ),
        "section_name": ParagraphStyle(
            "SectionName",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor(
                "#111827"
            ),
            spaceAfter=7,
        ),
        "chart_title": ParagraphStyle(
            "ChartTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor(
                "#374151"
            ),
            spaceAfter=6,
        ),
        "table_heading": ParagraphStyle(
            "TableHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor(
                "#374151"
            ),
            spaceAfter=5,
        ),
        "filter": ParagraphStyle(
            "FilterSummary",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor(
                "#555555"
            ),
            spaceAfter=10,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor(
                "#777777"
            ),
        ),
    }


# ============================================================
# FILTER SUMMARY
# ============================================================

def _add_filter_summary(
    story,
    filter_summary,
    style,
):
    if not filter_summary:
        return

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

            from reportlab.platypus import (
                Paragraph,
            )

            story.append(
                Paragraph(
                    "<br/>".join(
                        summary_parts
                    ),
                    style,
                )
            )

    else:

        from reportlab.platypus import (
            Paragraph,
        )

        story.append(
            Paragraph(
                html.escape(
                    str(
                        filter_summary
                    )
                ),
                style,
            )
        )


# ============================================================
# BUILD PDF
# ============================================================

def _build_pdf(
    charts,
    report_title,
    filter_summary,
    mode,
):
    """
    mode:

        "charts_only"
        "charts_and_data"
        "table_only"
    """

    from reportlab.lib.pagesizes import A4
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

    styles = _get_pdf_styles()

    story = []

    # ========================================================
    # REPORT HEADER
    # ========================================================

    story.append(
        Spacer(
            1,
            15,
        )
    )

    story.append(
        Paragraph(
            html.escape(
                report_title
            ),
            styles["title"],
        )
    )

    story.append(
        Spacer(
            1,
            4,
        )
    )

    _add_filter_summary(
        story,
        filter_summary,
        styles["filter"],
    )

    # ========================================================
    # EACH SECTION
    # ========================================================

    for index, item in enumerate(
        charts,
        start=1,
    ):

        section_name = (
            item.get(
                "section_name"
            )
            or f"Chart {index}"
        )

        chart_title = (
            item.get(
                "title"
            )
            or ""
        )

        data = item.get(
            "data"
        )

        # ----------------------------------------------------
        # Every section starts on new page
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
                styles["section_number"],
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
                styles["section_name"],
            )
        )

        # ====================================================
        # OPTION 1 / OPTION 2
        # ====================================================

        if mode in (
            "charts_only",
            "charts_and_data",
        ):

            png_bytes = _chart_to_png(
                item
            )

            if png_bytes:

                reserved_height = (
                    70 * mm
                )

                max_chart_height = (
                    available_height
                    - reserved_height
                )

                if max_chart_height < (
                    50 * mm
                ):
                    max_chart_height = (
                        50 * mm
                    )

                chart_width, chart_height = (
                    _get_chart_image_size(
                        item,
                        png_bytes,
                        available_width,
                        max_chart_height,
                    )
                )

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

        # ====================================================
        # OPTION 2 / OPTION 3
        # ====================================================

        if mode in (
            "charts_and_data",
            "table_only",
        ):

            table = (
                _build_report_table(
                    data,
                    available_width,
                )
            )

            if table is not None:

                story.append(
                    Paragraph(
                        "Displayed Data",
                        styles["table_heading"],
                    )
                )

                story.append(
                    table
                )

        # ====================================================
        # FOOTER
        # ====================================================

        story.append(
            Spacer(
                1,
                8,
            )
        )

        story.append(
            Paragraph(
                "MSU Mumbai Health Programme Management Dashboard",
                styles["footer"],
            )
        )

    doc.build(
        story
    )

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# FILENAME
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
# DOWNLOAD CONTROLS
# ============================================================

def render_displayed_chart_download_controls(
    filter_summary=None,
    base_filename=(
        "MSU_Mumbai_Charts_Trends_Displayed_Charts"
    ),
):
    charts = _get_registry()

    if not charts:

        st.info(
            "No displayed charts were captured on this page."
        )

        return

    st.subheader(
        "Download Charts & Tables"
    )

    st.caption(
        f"{len(charts)} chart section(s) available for export."
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
                or f"Chart {index}"
            )

            st.write(
                f"{index}. {section_name}"
            )

    st.divider()

    # ========================================================
    # OPTION 1
    # ========================================================

    st.markdown(
        "### 1️⃣ Charts with Section Name"
    )

    st.caption(
        "PDF contains the actual section name and chart only."
    )

    try:

        pdf_charts_only = _build_pdf(
            charts=charts,
            report_title=(
                "MSU Mumbai - "
                "Charts with Section Name"
            ),
            filter_summary=filter_summary,
            mode="charts_only",
        )

        if pdf_charts_only:

            st.download_button(
                label=(
                    "📊 Download Charts + Section Name PDF"
                ),
                data=pdf_charts_only,
                file_name=_safe_filename(
                    f"{base_filename}_Charts_Section_Name",
                    ".pdf",
                ),
                mime="application/pdf",
                use_container_width=True,
                key=(
                    "download_charts_section_name_pdf"
                ),
            )

    except Exception as exc:

        st.error(
            "Charts with Section Name PDF could not be generated."
        )

        with st.expander(
            "Technical details"
        ):
            st.code(
                str(exc)
            )

    # ========================================================
    # OPTION 2
    # ========================================================

    st.markdown(
        "### 2️⃣ Charts with Data & Section Name"
    )

    st.caption(
        "PDF contains section name, chart and the corresponding data table."
    )

    try:

        pdf_charts_data = _build_pdf(
            charts=charts,
            report_title=(
                "MSU Mumbai - "
                "Charts with Data & Section Name"
            ),
            filter_summary=filter_summary,
            mode="charts_and_data",
        )

        if pdf_charts_data:

            st.download_button(
                label=(
                    "📊 Download Charts + Data PDF"
                ),
                data=pdf_charts_data,
                file_name=_safe_filename(
                    f"{base_filename}_Charts_Data_Section_Name",
                    ".pdf",
                ),
                mime="application/pdf",
                use_container_width=True,
                key=(
                    "download_charts_data_section_name_pdf"
                ),
            )

    except Exception as exc:

        st.error(
            "Charts with Data & Section Name PDF could not be generated."
        )

        with st.expander(
            "Technical details"
        ):
            st.code(
                str(exc)
            )

    # ========================================================
    # OPTION 3
    # ========================================================

    st.markdown(
        "### 3️⃣ Only Table"
    )

    st.caption(
        "PDF contains the section name and corresponding data table only."
    )

    try:

        pdf_table_only = _build_pdf(
            charts=charts,
            report_title=(
                "MSU Mumbai - "
                "Tables with Section Name"
            ),
            filter_summary=filter_summary,
            mode="table_only",
        )

        if pdf_table_only:

            st.download_button(
                label=(
                    "📋 Download Only Tables PDF"
                ),
                data=pdf_table_only,
                file_name=_safe_filename(
                    f"{base_filename}_Only_Tables",
                    ".pdf",
                ),
                mime="application/pdf",
                use_container_width=True,
                key=(
                    "download_only_tables_pdf"
                ),
            )

    except Exception as exc:

        st.error(
            "Only Table PDF could not be generated."
        )

        with st.expander(
            "Technical details"
        ):
            st.code(
                str(exc)
            )
