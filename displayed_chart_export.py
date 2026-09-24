import io
import hashlib
import zipfile
from contextlib import contextmanager

import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

DISPLAYED_CHARTS_KEY = "displayed_chart_exports"
CAPTURE_ACTIVE_KEY = "displayed_chart_capture_active"


# ============================================================
# REGISTRY
# ============================================================

def _ensure_registry():

    if DISPLAYED_CHARTS_KEY not in st.session_state:
        st.session_state[DISPLAYED_CHARTS_KEY] = []

    return st.session_state[DISPLAYED_CHARTS_KEY]


def clear_displayed_charts():

    st.session_state[DISPLAYED_CHARTS_KEY] = []


def get_displayed_charts():

    return st.session_state.get(
        DISPLAYED_CHARTS_KEY,
        [],
    )


# ============================================================
# SAFE DATAFRAME
# ============================================================

def _safe_dataframe(data):

    if data is None:
        return pd.DataFrame()

    if isinstance(data, pd.DataFrame):
        return data.copy()

    if isinstance(data, pd.Series):

        result = data.reset_index()

        if len(result.columns) >= 2:

            result.columns = [
                str(result.columns[0]),
                "Records",
            ]

        return result

    if isinstance(data, dict):

        try:
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame()

    if isinstance(data, list):

        try:
            return pd.DataFrame(data)
        except Exception:
            return pd.DataFrame()

    return pd.DataFrame()


# ============================================================
# EXTRACT CHART DATA
# ============================================================

def _extract_chart_dataframe(chart):

    if chart is None:
        return pd.DataFrame()

    # --------------------------------------------------------
    # Direct chart data
    # --------------------------------------------------------

    try:

        data = getattr(
            chart,
            "data",
            None,
        )

        result = _safe_dataframe(data)

        if not result.empty:
            return result

    except Exception:
        pass

    # --------------------------------------------------------
    # Convert chart to Vega-Lite specification
    # --------------------------------------------------------

    try:

        spec = chart.to_dict()

    except Exception:

        return pd.DataFrame()

    # --------------------------------------------------------
    # Direct values
    # --------------------------------------------------------

    try:

        if isinstance(spec, dict):

            data_block = spec.get(
                "data"
            )

            if isinstance(
                data_block,
                dict,
            ):

                values = data_block.get(
                    "values"
                )

                if values is not None:

                    result = _safe_dataframe(
                        values
                    )

                    if not result.empty:
                        return result

    except Exception:
        pass

    # --------------------------------------------------------
    # Dataset references
    # --------------------------------------------------------

    try:

        datasets = spec.get(
            "datasets",
            {},
        )

        if datasets:

            frames = []

            for values in datasets.values():

                frame = _safe_dataframe(
                    values
                )

                if not frame.empty:
                    frames.append(frame)

            if frames:

                if len(frames) == 1:
                    return frames[0]

                try:

                    return pd.concat(
                        frames,
                        ignore_index=True,
                    )

                except Exception:

                    return frames[0]

    except Exception:
        pass

    # --------------------------------------------------------
    # Layered charts
    # --------------------------------------------------------

    try:

        layers = spec.get(
            "layer",
            [],
        )

        for layer in layers:

            if not isinstance(
                layer,
                dict,
            ):
                continue

            layer_data = layer.get(
                "data"
            )

            if isinstance(
                layer_data,
                dict,
            ):

                values = layer_data.get(
                    "values"
                )

                if values is not None:

                    result = _safe_dataframe(
                        values
                    )

                    if not result.empty:
                        return result

    except Exception:
        pass

    return pd.DataFrame()


# ============================================================
# PREPARE REPORT TABLE
# ============================================================

def _prepare_report_table(data):

    df = _safe_dataframe(data)

    if df.empty:
        return df

    result = df.copy()

    # --------------------------------------------------------
    # Remove unwanted index columns
    # --------------------------------------------------------

    remove_columns = []

    for column in result.columns:

        text = str(column).strip().lower()

        if (
            text.startswith("unnamed:")
            or text == "index"
        ):

            remove_columns.append(
                column
            )

    if remove_columns:

        result = result.drop(
            columns=remove_columns,
            errors="ignore",
        )

    # --------------------------------------------------------
    # Datetime formatting
    # --------------------------------------------------------

    for column in result.columns:

        try:

            if pd.api.types.is_datetime64_any_dtype(
                result[column]
            ):

                result[column] = (
                    result[column]
                    .dt.strftime("%d-%m-%Y")
                )

        except Exception:
            pass

    # --------------------------------------------------------
    # Replace NaN
    # --------------------------------------------------------

    result = result.fillna("")

    return result


# ============================================================
# CAPTURE DISPLAYED CHARTS
# ============================================================

@contextmanager
def capture_displayed_charts():

    clear_displayed_charts()

    captured_charts = []

    original_altair_chart = st.altair_chart

    def wrapped_altair_chart(
        chart,
        *args,
        **kwargs,
    ):

        try:

            title = None

            # ------------------------------------------------
            # Extract title
            # ------------------------------------------------

            try:

                chart_dict = chart.to_dict()

                title_block = chart_dict.get(
                    "title"
                )

                if isinstance(
                    title_block,
                    str,
                ):

                    title = title_block

                elif isinstance(
                    title_block,
                    dict,
                ):

                    title = title_block.get(
                        "text"
                    )

            except Exception:
                pass

            # ------------------------------------------------
            # Extract table
            # ------------------------------------------------

            table_df = _extract_chart_dataframe(
                chart
            )

            table_df = _prepare_report_table(
                table_df
            )

            captured_charts.append(
                {
                    "chart": chart,
                    "title": (
                        title
                        or f"Chart {len(captured_charts) + 1}"
                    ),
                    "table": table_df,
                }
            )

        except Exception:

            captured_charts.append(
                {
                    "chart": chart,
                    "title": (
                        f"Chart {len(captured_charts) + 1}"
                    ),
                    "table": pd.DataFrame(),
                }
            )

        return original_altair_chart(
            chart,
            *args,
            **kwargs,
        )

    try:

        st.altair_chart = wrapped_altair_chart

        st.session_state[
            CAPTURE_ACTIVE_KEY
        ] = True

        yield captured_charts

    finally:

        st.altair_chart = original_altair_chart

        st.session_state[
            CAPTURE_ACTIVE_KEY
        ] = False

        st.session_state[
            DISPLAYED_CHARTS_KEY
        ] = captured_charts


# ============================================================
# ALTAIR → PNG
# ============================================================

def _chart_to_png(chart):

    try:

        import vl_convert as vlc

    except ImportError as e:

        raise ImportError(
            "vl-convert-python is required for "
            "displayed chart PNG/PDF export."
        ) from e

    spec = chart.to_dict()

    # --------------------------------------------------------
    # Render using Vega-Lite's native dimensions.
    #
    # DO NOT force a fixed width/height here.
    # --------------------------------------------------------

    png_bytes = vlc.vegalite_to_png(
        spec,
        scale=2,
    )

    return png_bytes


# ============================================================
# FINGERPRINT
# ============================================================

def _make_fingerprint(
    charts,
    filter_summary="",
):

    pieces = [
        str(filter_summary)
    ]

    for item in charts:

        chart = item.get(
            "chart"
        )

        try:

            spec = chart.to_dict()

            pieces.append(
                repr(spec)
            )

        except Exception:

            pieces.append(
                str(chart)
            )

        table = item.get(
            "table"
        )

        if isinstance(
            table,
            pd.DataFrame,
        ):

            try:

                pieces.append(
                    table.to_csv(
                        index=False
                    )
                )

            except Exception:
                pass

    raw = "\n".join(
        pieces
    ).encode(
        "utf-8",
        errors="ignore",
    )

    return hashlib.md5(
        raw
    ).hexdigest()


# ============================================================
# REPORTLAB IMPORTS
# ============================================================

def _get_reportlab():

    try:

        from reportlab.lib import colors
        from reportlab.lib.enums import (
            TA_CENTER,
            TA_LEFT,
        )
        from reportlab.lib.pagesizes import (
            A4,
            landscape,
        )
        from reportlab.lib.styles import (
            ParagraphStyle,
            getSampleStyleSheet,
        )
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Image,
            KeepTogether,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )

        return {
            "colors": colors,
            "TA_CENTER": TA_CENTER,
            "TA_LEFT": TA_LEFT,
            "A4": A4,
            "landscape": landscape,
            "ParagraphStyle": ParagraphStyle,
            "getSampleStyleSheet": getSampleStyleSheet,
            "mm": mm,
            "Image": Image,
            "KeepTogether": KeepTogether,
            "PageBreak": PageBreak,
            "Paragraph": Paragraph,
            "SimpleDocTemplate": SimpleDocTemplate,
            "Spacer": Spacer,
            "Table": Table,
            "TableStyle": TableStyle,
        }

    except ImportError as e:

        raise ImportError(
            "reportlab is required for PDF export."
        ) from e


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
        bool,
    ):

        return "Yes" if value else "No"

    if isinstance(
        value,
        int,
    ):

        return f"{value:,}"

    if isinstance(
        value,
        float,
    ):

        if value.is_integer():

            return f"{int(value):,}"

        return f"{value:,.2f}"

    return str(value)


# ============================================================
# TABLE COLUMN WIDTH CALCULATION
# ============================================================

def _calculate_column_widths(
    display_df,
    available_width,
):

    column_count = len(
        display_df.columns
    )

    if column_count == 0:
        return []

    # --------------------------------------------------------
    # Estimate width from content
    # --------------------------------------------------------

    estimated = []

    for column in display_df.columns:

        header_length = len(
            str(column)
        )

        sample_values = (
            display_df[column]
            .astype(str)
            .head(80)
            .tolist()
        )

        max_value_length = 0

        for value in sample_values:

            max_value_length = max(
                max_value_length,
                len(value),
            )

        estimated_length = max(
            header_length,
            min(
                max_value_length,
                40,
            ),
        )

        estimated.append(
            max(
                estimated_length,
                8,
            )
        )

    total_estimated = sum(
        estimated
    )

    if total_estimated <= 0:
        return [
            available_width / column_count
        ] * column_count

    # --------------------------------------------------------
    # Convert estimated characters
    # into physical width
    # --------------------------------------------------------

    widths = []

    for value in estimated:

        width = (
            available_width
            * value
            / total_estimated
        )

        widths.append(width)

    # --------------------------------------------------------
    # Minimum and maximum widths
    # --------------------------------------------------------

    min_width = 18 * mm
    max_width = 70 * mm

    widths = [
        max(
            min_width,
            min(
                width,
                max_width,
            ),
        )
        for width in widths
    ]

    # --------------------------------------------------------
    # Re-normalize to available width
    # --------------------------------------------------------

    total_width = sum(
        widths
    )

    if total_width > 0:

        factor = (
            available_width
            / total_width
        )

        widths = [
            width * factor
            for width in widths
        ]

    return widths


# ============================================================
# BUILD REPORT TABLE
# ============================================================

def _build_report_table(
    display_df,
    reportlab,
    available_width,
):

    colors = reportlab["colors"]
    Paragraph = reportlab["Paragraph"]
    ParagraphStyle = reportlab[
        "ParagraphStyle"
    ]
    Table = reportlab["Table"]
    TableStyle = reportlab[
        "TableStyle"
    ]

    if display_df.empty:
        return None

    # --------------------------------------------------------
    # Styles
    # --------------------------------------------------------

    header_style = ParagraphStyle(
        "ReportTableHeader",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        alignment=reportlab["TA_CENTER"],
        textColor=colors.white,
        spaceAfter=0,
        spaceBefore=0,
    )

    cell_style = ParagraphStyle(
        "ReportTableCell",
        fontName="Helvetica",
        fontSize=7,
        leading=8.5,
        alignment=reportlab["TA_LEFT"],
        spaceAfter=0,
        spaceBefore=0,
    )

    # --------------------------------------------------------
    # Headers
    # --------------------------------------------------------

    table_data = [
        [
            Paragraph(
                str(column),
                header_style,
            )
            for column in display_df.columns
        ]
    ]

    # --------------------------------------------------------
    # Rows
    # --------------------------------------------------------

    for _, row in display_df.iterrows():

        row_data = []

        for value in row:

            formatted = _format_table_value(
                value
            )

            row_data.append(
                Paragraph(
                    formatted,
                    cell_style,
                )
            )

        table_data.append(
            row_data
        )

    # --------------------------------------------------------
    # Widths
    # --------------------------------------------------------

    column_widths = (
        _calculate_column_widths(
            display_df,
            available_width,
        )
    )

    # --------------------------------------------------------
    # Table
    # --------------------------------------------------------

    report_table = Table(
        table_data,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
    )

    # --------------------------------------------------------
    # Style
    # --------------------------------------------------------

    report_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#355C7D"
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
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor(
                        "#AAB4BE"
                    ),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor(
                            "#F5F7F9"
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

    return report_table


# ============================================================
# BUILD PDF
# ============================================================

def _build_pdf(
    charts,
    filter_summary="",
):

    reportlab = _get_reportlab()

    colors = reportlab["colors"]
    A4 = reportlab["A4"]
    landscape = reportlab["landscape"]
    ParagraphStyle = reportlab[
        "ParagraphStyle"
    ]
    getSampleStyleSheet = reportlab[
        "getSampleStyleSheet"
    ]
    mm = reportlab["mm"]
    Image = reportlab["Image"]
    PageBreak = reportlab["PageBreak"]
    Paragraph = reportlab["Paragraph"]
    SimpleDocTemplate = reportlab[
        "SimpleDocTemplate"
    ]
    Spacer = reportlab["Spacer"]

    buffer = io.BytesIO()

    # ========================================================
    # LANDSCAPE A4
    # ========================================================

    page_width, page_height = landscape(
        A4
    )

    left_margin = 10 * mm
    right_margin = 10 * mm
    top_margin = 10 * mm
    bottom_margin = 10 * mm

    available_width = (
        page_width
        - left_margin
        - right_margin
    )

    available_height = (
        page_height
        - top_margin
        - bottom_margin
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=right_margin,
        leftMargin=left_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
        title=(
            "MSU Mumbai "
            "Displayed Charts Report"
        ),
        author="MSU Mumbai Public Health Surveillance Dashboard",
    )

    # ========================================================
    # STYLES
    # ========================================================

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=reportlab["TA_CENTER"],
        spaceAfter=5 * mm,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        alignment=reportlab["TA_LEFT"],
        textColor=colors.HexColor(
            "#355C7D"
        ),
        spaceAfter=3 * mm,
    )

    chart_heading_style = ParagraphStyle(
        "ChartHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=reportlab["TA_LEFT"],
        textColor=colors.HexColor(
            "#243746"
        ),
        spaceAfter=3 * mm,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=reportlab["TA_LEFT"],
    )

    table_heading_style = ParagraphStyle(
        "TableHeading",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor(
            "#355C7D"
        ),
        spaceBefore=2 * mm,
        spaceAfter=2 * mm,
    )

    # ========================================================
    # STORY
    # ========================================================

    story = []

    # ========================================================
    # REPORT HEADER
    # ========================================================

    story.append(
        Paragraph(
            "MSU Mumbai Public Health Surveillance Dashboard",
            title_style,
        )
    )

    story.append(
        Paragraph(
            "Charts & Trends — Displayed Charts Report",
            subtitle_style,
        )
    )

    if filter_summary:

        story.append(
            Paragraph(
                f"<b>Applied Filters:</b> "
                f"{filter_summary}",
                body_style,
            )
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

    story.append(
        Paragraph(
            f"<b>Total Charts:</b> "
            f"{len(charts)}",
            body_style,
        )
    )

    story.append(
        Spacer(
            1,
            7 * mm,
        )
    )

    # ========================================================
    # CHART SECTIONS
    # ========================================================

    for index, item in enumerate(
        charts,
        start=1,
    ):

        chart = item.get(
            "chart"
        )

        title = (
            item.get("title")
            or f"Chart {index}"
        )

        # ----------------------------------------------------
        # Chart heading
        # ----------------------------------------------------

        story.append(
            Paragraph(
                f"{index}. {title}",
                chart_heading_style,
            )
        )

        # ----------------------------------------------------
        # Render chart
        # ----------------------------------------------------

        try:

            png_bytes = _chart_to_png(
                chart
            )

            image_buffer = io.BytesIO(
                png_bytes
            )

            image = Image(
                image_buffer
            )

            # ------------------------------------------------
            # Preserve original aspect ratio
            # ------------------------------------------------

            from PIL import Image as PILImage

            pil_image = PILImage.open(
                io.BytesIO(
                    png_bytes
                )
            )

            original_width, original_height = (
                pil_image.size
            )

            if original_width <= 0:
                original_width = 1200

            if original_height <= 0:
                original_height = 600

            aspect_ratio = (
                original_height
                / original_width
            )

            # Maximum chart dimensions
            max_width = available_width
            max_height = 88 * mm

            # Calculate width from height
            target_height = (
                max_width
                * aspect_ratio
            )

            target_width = max_width

            if target_height > max_height:

                target_height = max_height

                target_width = (
                    target_height
                    / aspect_ratio
                )

            # Prevent tiny charts
            if target_width < 100 * mm:

                target_width = (
                    100 * mm
                )

                target_height = (
                    target_width
                    * aspect_ratio
                )

            image.drawWidth = target_width
            image.drawHeight = target_height

            story.append(
                image
            )

            story.append(
                Spacer(
                    1,
                    5 * mm,
                )
            )

        except Exception as e:

            story.append(
                Paragraph(
                    (
                        "<b>Chart rendering error:</b> "
                        f"{str(e)}"
                    ),
                    body_style,
                )
            )

            story.append(
                Spacer(
                    1,
                    4 * mm,
                )
            )

        # ----------------------------------------------------
        # Table
        # ----------------------------------------------------

        table_df = item.get(
            "table"
        )

        if (
            isinstance(
                table_df,
                pd.DataFrame,
            )
            and not table_df.empty
        ):

            display_df = table_df.copy()

            # ------------------------------------------------
            # Keep all columns where possible.
            # If extremely wide, use a readable maximum.
            # ------------------------------------------------

            if len(
                display_df.columns
            ) > 14:

                display_df = display_df.iloc[
                    :,
                    :14,
                ]

            # ------------------------------------------------
            # Very large tables
            # ------------------------------------------------

            total_rows = len(
                display_df
            )

            if total_rows > 300:

                display_df = display_df.head(
                    300
                )

                truncated = True

            else:

                truncated = False

            story.append(
                Paragraph(
                    "Data Table",
                    table_heading_style,
                )
            )

            report_table = _build_report_table(
                display_df,
                reportlab,
                available_width,
            )

            if report_table is not None:

                story.append(
                    report_table
                )

                if truncated:

                    story.append(
                        Spacer(
                            1,
                            2 * mm,
                        )
                    )

                    story.append(
                        Paragraph(
                            (
                                f"Showing first "
                                f"{len(display_df):,} "
                                f"of {total_rows:,} rows."
                            ),
                            body_style,
                        )
                    )

            story.append(
                Spacer(
                    1,
                    5 * mm,
                )
            )

        else:

            story.append(
                Paragraph(
                    "No underlying table data available for this chart.",
                    body_style,
                )
            )

        # ----------------------------------------------------
        # New page
        # ----------------------------------------------------

        if index < len(charts):

            story.append(
                PageBreak()
            )

    # ========================================================
    # BUILD
    # ========================================================

    doc.build(
        story
    )

    return buffer.getvalue()


# ============================================================
# PNG ZIP
# ============================================================

def _build_png_zip(charts):

    output = io.BytesIO()

    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        for index, item in enumerate(
            charts,
            start=1,
        ):

            chart = item.get(
                "chart"
            )

            title = (
                item.get("title")
                or f"Chart {index}"
            )

            safe_title = (
                str(title)
                .strip()
                .replace(
                    "/",
                    "_",
                )
                .replace(
                    "\\",
                    "_",
                )
                .replace(
                    ":",
                    "_",
                )
                .replace(
                    " ",
                    "_",
                )
            )

            try:

                png_bytes = _chart_to_png(
                    chart
                )

                archive.writestr(
                    (
                        f"{index:02d}_"
                        f"{safe_title}.png"
                    ),
                    png_bytes,
                )

            except Exception:

                continue

    return output.getvalue()


# ============================================================
# DOWNLOAD CONTROLS
# ============================================================

def render_displayed_chart_download_controls(
    filter_summary="",
    base_filename="MSU_Mumbai_Displayed_Charts",
):

    charts = get_displayed_charts()

    st.subheader(
        "📊 Displayed Charts Report"
    )

    if not charts:

        st.info(
            "No displayed charts were captured on this page."
        )

        return

    st.caption(
        f"{len(charts)} displayed chart(s) captured. "
        "The PDF uses landscape A4 format and preserves "
        "the chart aspect ratio. Each chart is followed "
        "by its data table."
    )

    fingerprint = _make_fingerprint(
        charts,
        filter_summary,
    )

    cache_key = (
        "displayed_chart_export_cache_v2_"
        f"{fingerprint}"
    )

    # ========================================================
    # BUILD ONLY WHEN NEEDED
    # ========================================================

    if cache_key not in st.session_state:

        with st.spinner(
            "Preparing displayed chart report..."
        ):

            pdf_bytes = _build_pdf(
                charts,
                filter_summary,
            )

            zip_bytes = _build_png_zip(
                charts
            )

        st.session_state[
            cache_key
        ] = {
            "pdf": pdf_bytes,
            "zip": zip_bytes,
        }

    cached = st.session_state[
        cache_key
    ]

    # ========================================================
    # DOWNLOAD BUTTONS
    # ========================================================

    col1, col2 = st.columns(
        2
    )

    with col1:

        st.download_button(
            label=(
                "📄 Download Displayed Charts + Tables PDF"
            ),
            data=cached["pdf"],
            file_name=(
                f"{base_filename}_with_Tables.pdf"
            ),
            mime="application/pdf",
            use_container_width=True,
            key=(
                "download_displayed_chart_pdf_"
                f"{fingerprint}"
            ),
        )

    with col2:

        st.download_button(
            label=(
                "🖼️ Download Displayed Chart PNGs"
            ),
            data=cached["zip"],
            file_name=(
                f"{base_filename}_PNG.zip"
            ),
            mime="application/zip",
            use_container_width=True,
            key=(
                "download_displayed_chart_png_"
                f"{fingerprint}"
            ),
        )

    # ========================================================
    # CONTENT SUMMARY
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
                item.get("title")
                or f"Chart {index}"
            )

            table_df = item.get(
                "table"
            )

            if (
                isinstance(
                    table_df,
                    pd.DataFrame,
                )
                and not table_df.empty
            ):

                st.write(
                    f"**{index}. {title}** "
                    f"— Chart + Table "
                    f"({len(table_df):,} rows)"
                )

            else:

                st.write(
                    f"**{index}. {title}** "
                    "— Chart"
                )
