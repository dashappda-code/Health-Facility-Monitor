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
MAX_CHART_HEIGHT_MM = 88


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
        try:
            result = data.reset_index()

            if len(result.columns) >= 2:
                result.columns = [
                    str(result.columns[0]),
                    "Records",
                ]

            return result

        except Exception:
            return pd.DataFrame()

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
# CHART DATA EXTRACTION
# ============================================================

def _extract_chart_dataframe(chart):
    """
    Extract underlying data from an Altair chart.

    Handles:
    - normal Altair charts
    - inline values
    - datasets
    - layered charts
    - hconcat
    - vconcat
    - concat
    """

    if chart is None:
        return pd.DataFrame()

    # --------------------------------------------------------
    # Direct chart data
    # --------------------------------------------------------

    try:
        data = getattr(chart, "data", None)

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

    if not isinstance(spec, dict):
        return pd.DataFrame()

    # --------------------------------------------------------
    # Direct data block
    # --------------------------------------------------------

    try:
        data_block = spec.get("data")

        if isinstance(data_block, dict):
            values = data_block.get("values")

            if values is not None:
                result = _safe_dataframe(values)

                if not result.empty:
                    return result

    except Exception:
        pass

    # --------------------------------------------------------
    # Dataset references
    # --------------------------------------------------------

    try:
        datasets = spec.get("datasets", {})

        if isinstance(datasets, dict) and datasets:
            frames = []

            for values in datasets.values():
                frame = _safe_dataframe(values)

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
        layers = spec.get("layer", [])

        if isinstance(layers, list):
            for layer in layers:
                if not isinstance(layer, dict):
                    continue

                layer_data = layer.get("data")

                if isinstance(layer_data, dict):
                    values = layer_data.get("values")

                    if values is not None:
                        result = _safe_dataframe(values)

                        if not result.empty:
                            return result

                # Nested layer specification
                if "layer" in layer:
                    nested_spec = layer

                    try:
                        nested_values = nested_spec.get(
                            "datasets",
                            {},
                        )

                        if isinstance(
                            nested_values,
                            dict,
                        ):
                            for values in nested_values.values():
                                result = _safe_dataframe(values)

                                if not result.empty:
                                    return result

                    except Exception:
                        pass

    except Exception:
        pass

    # --------------------------------------------------------
    # HConcat / VConcat / Concat
    # --------------------------------------------------------

    for key in (
        "hconcat",
        "vconcat",
        "concat",
    ):
        try:
            children = spec.get(key, [])

            if isinstance(children, list):
                for child in children:
                    if not isinstance(child, dict):
                        continue

                    child_data = child.get("data")

                    if isinstance(child_data, dict):
                        values = child_data.get("values")

                        if values is not None:
                            result = _safe_dataframe(values)

                            if not result.empty:
                                return result

                    child_datasets = child.get(
                        "datasets",
                        {},
                    )

                    if isinstance(
                        child_datasets,
                        dict,
                    ):
                        for values in child_datasets.values():
                            result = _safe_dataframe(values)

                            if not result.empty:
                                return result

        except Exception:
            pass

    return pd.DataFrame()


# ============================================================
# REPORT TABLE PREPARATION
# ============================================================

def _prepare_report_table(data):
    df = _safe_dataframe(data)

    if df.empty:
        return df

    result = df.copy()

    # --------------------------------------------------------
    # Remove artificial index columns
    # --------------------------------------------------------

    remove_columns = []

    for column in result.columns:
        text = str(column).strip().lower()

        if (
            text.startswith("unnamed:")
            or text == "index"
        ):
            remove_columns.append(column)

    if remove_columns:
        result = result.drop(
            columns=remove_columns,
            errors="ignore",
        )

    # --------------------------------------------------------
    # Convert datetime values
    # --------------------------------------------------------

    for column in result.columns:
        try:
            if pd.api.types.is_datetime64_any_dtype(
                result[column]
            ):
                result[column] = result[column].dt.strftime(
                    "%d-%m-%Y"
                )

        except Exception:
            pass

    # --------------------------------------------------------
    # Reset index
    # --------------------------------------------------------

    result = result.reset_index(drop=True)

    return result


# ============================================================
# CAPTURE DISPLAYED CHARTS
# ============================================================

@contextmanager
def capture_displayed_charts():
    """
    Capture every Altair chart rendered while the
    context manager is active.

    The original Streamlit altair_chart function is restored
    automatically after rendering.
    """

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
            # Read chart title
            # ------------------------------------------------

            try:
                chart_dict = chart.to_dict()

                title_block = chart_dict.get("title")

                if isinstance(
                    title_block,
                    str,
                ):
                    title = title_block

                elif isinstance(
                    title_block,
                    dict,
                ):
                    title = title_block.get("text")

            except Exception:
                pass

            # ------------------------------------------------
            # Extract table data
            # ------------------------------------------------

            table_df = _extract_chart_dataframe(chart)

            table_df = _prepare_report_table(table_df)

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
# ALTAIR -> PNG
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

    return vlc.vegalite_to_png(
        spec,
        scale=2,
    )


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
        chart = item.get("chart")

        try:
            spec = chart.to_dict()

            pieces.append(
                repr(spec)
            )

        except Exception:
            pieces.append(
                str(chart)
            )

        table = item.get("table")

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

    return hashlib.md5(raw).hexdigest()


# ============================================================
# VALUE FORMATTER
# ============================================================

def _format_table_value(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    # --------------------------------------------------------
    # Integer
    # --------------------------------------------------------

    if isinstance(
        value,
        int,
    ):
        return f"{value:,}"

    # --------------------------------------------------------
    # Float
    # --------------------------------------------------------

    if isinstance(
        value,
        float,
    ):
        if value.is_integer():
            return f"{int(value):,}"

        return f"{value:,.2f}"

    return str(value)


# ============================================================
# REPORTLAB TABLE BUILDER
# ============================================================

def _build_report_table(
    dataframe,
    available_width,
    colors,
    Paragraph,
    Table,
    TableStyle,
    body_style,
    header_style,
):
    if not isinstance(
        dataframe,
        pd.DataFrame,
    ):
        return None

    if dataframe.empty:
        return None

    df = dataframe.copy()

    # --------------------------------------------------------
    # Limit rows
    # --------------------------------------------------------

    if len(df) > MAX_TABLE_ROWS:
        df = df.head(MAX_TABLE_ROWS)

    # --------------------------------------------------------
    # Limit columns
    # --------------------------------------------------------

    if len(df.columns) > MAX_TABLE_COLUMNS:
        df = df.iloc[
            :,
            :MAX_TABLE_COLUMNS,
        ]

    # --------------------------------------------------------
    # Convert values
    # --------------------------------------------------------

    columns = [
        str(column)
        for column in df.columns
    ]

    table_data = []

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    header_row = []

    for column in columns:
        header_row.append(
            Paragraph(
                html.escape(column),
                header_style,
            )
        )

    table_data.append(header_row)

    # --------------------------------------------------------
    # Body
    # --------------------------------------------------------

    for _, row in df.iterrows():
        table_row = []

        for value in row:
            text = _format_table_value(value)

            table_row.append(
                Paragraph(
                    html.escape(text),
                    body_style,
                )
            )

        table_data.append(table_row)

    # --------------------------------------------------------
    # Calculate intelligent column widths
    # --------------------------------------------------------

    column_weights = []

    for column in df.columns:
        column_name = str(column)

        values = df[column].head(50).tolist()

        lengths = []

        for value in values:
            try:
                if pd.isna(value):
                    continue
            except Exception:
                pass

            lengths.append(len(str(value)))

        max_value_length = (
            max(lengths)
            if lengths
            else 5
        )

        estimated_length = max(
            len(column_name),
            min(
                max_value_length,
                30,
            ),
        )

        column_weights.append(
            float(estimated_length)
        )

    if not column_weights:
        return None

    total_weight = sum(column_weights)

    if total_weight <= 0:
        total_weight = len(column_weights)

        column_weights = [
            1.0
            for _ in column_weights
        ]

    calculated_widths = [
        available_width
        * (
            weight
            / total_weight
        )
        for weight in column_weights
    ]

    # --------------------------------------------------------
    # Minimum / maximum widths
    # --------------------------------------------------------

    column_count = max(
        len(calculated_widths),
        1,
    )

    min_width = (
        available_width
        / column_count
    ) * 0.55

    max_width = available_width * 0.35

    calculated_widths = [
        min(
            max(
                width,
                min_width,
            ),
            max_width,
        )
        for width in calculated_widths
    ]

    # --------------------------------------------------------
    # Re-normalize
    # --------------------------------------------------------

    width_total = sum(
        calculated_widths
    )

    if width_total > 0:
        calculated_widths = [
            width
            * available_width
            / width_total
            for width in calculated_widths
        ]

    # --------------------------------------------------------
    # Create table
    # --------------------------------------------------------

    report_table = Table(
        table_data,
        colWidths=calculated_widths,
        repeatRows=1,
        hAlign="LEFT",
    )

    report_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#E8EEF5"),
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
                    (-1, 0),
                    7,
                ),
                (
                    "FONTSIZE",
                    (0, 1),
                    (-1, -1),
                    6.5,
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
                    "TOP",
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
                        colors.HexColor("#F7F9FB"),
                    ],
                ),
            ]
        )
    )

    return report_table


# ============================================================
# CHART IMAGE SIZE
# ============================================================

def _get_chart_image_size(
    png_bytes,
    max_width,
    max_height,
):
    """
    Preserve original chart aspect ratio.
    """

    try:
        from PIL import Image as PILImage

        image = PILImage.open(
            io.BytesIO(png_bytes)
        )

        pixel_width, pixel_height = image.size

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
            width
            * ratio
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
# PDF BUILDER
# ============================================================

def _build_pdf(
    charts,
    filter_summary="",
):
    try:
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
            Table,
            TableStyle,
        )

    except ImportError as e:
        raise ImportError(
            "reportlab is required for PDF export."
        ) from e

    # --------------------------------------------------------
    # PDF setup
    # --------------------------------------------------------

    buffer = io.BytesIO()

    page_width, page_height = A4

    horizontal_margin = (
        PDF_MARGIN_MM
        * mm
    )

    vertical_margin = (
        PDF_MARGIN_MM
        * mm
    )

    available_width = (
        page_width
        - (
            2
            * horizontal_margin
        )
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=horizontal_margin,
        leftMargin=horizontal_margin,
        topMargin=vertical_margin,
        bottomMargin=vertical_margin,
        title=(
            "MSU Mumbai "
            "Displayed Charts Report"
        ),
        author=(
            "MSU Mumbai "
            "Public Health Surveillance Dashboard"
        ),
    )

    styles = getSampleStyleSheet()

    # --------------------------------------------------------
    # Styles
    # --------------------------------------------------------

    title_style = ParagraphStyle(
        "DisplayedChartTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        spaceAfter=5 * mm,
    )

    heading_style = ParagraphStyle(
        "DisplayedChartHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceAfter=2 * mm,
    )

    body_style = ParagraphStyle(
        "DisplayedChartBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
    )

    table_body_style = ParagraphStyle(
        "DisplayedChartTableBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
    )

    table_header_style = ParagraphStyle(
        "DisplayedChartTableHeader",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8.5,
    )

    # --------------------------------------------------------
    # Story
    # --------------------------------------------------------

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
            heading_style,
        )
    )

    if filter_summary:
        story.append(
            Spacer(
                1,
                2 * mm,
            )
        )

        safe_filter_summary = html.escape(
            str(filter_summary)
        )

        story.append(
            Paragraph(
                (
                    f"<b>Filters:</b> "
                    f"{safe_filter_summary}"
                ),
                body_style,
            )
        )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    # ========================================================
    # CHART SECTIONS
    # ========================================================

    for index, item in enumerate(
        charts,
        start=1,
    ):
        chart = item.get("chart")

        title = (
            item.get("title")
            or f"Chart {index}"
        )

        safe_title = html.escape(
            str(title)
        )

        # ----------------------------------------------------
        # Chart heading
        # ----------------------------------------------------

        story.append(
            Paragraph(
                (
                    f"{index}. "
                    f"{safe_title}"
                ),
                heading_style,
            )
        )

        story.append(
            Spacer(
                1,
                2 * mm,
            )
        )

        # ----------------------------------------------------
        # Chart image
        # ----------------------------------------------------

        try:
            png_bytes = _chart_to_png(chart)

            image_buffer = io.BytesIO(
                png_bytes
            )

            image_width, image_height = (
                _get_chart_image_size(
                    png_bytes,
                    available_width,
                    MAX_CHART_HEIGHT_MM * mm,
                )
            )

            image = Image(
                image_buffer,
                width=image_width,
                height=image_height,
            )

            image.hAlign = "CENTER"

            story.append(image)

            story.append(
                Spacer(
                    1,
                    4 * mm,
                )
            )

        except Exception as e:
            error_text = html.escape(
                str(e)
            )

            story.append(
                Paragraph(
                    (
                        "Chart image could not "
                        "be rendered: "
                        f"{error_text}"
                    ),
                    body_style,
                )
            )

            story.append(
                Spacer(
                    1,
                    3 * mm,
                )
            )

        # ----------------------------------------------------
        # Data table
        # ----------------------------------------------------

        table_df = item.get("table")

        if (
            isinstance(
                table_df,
                pd.DataFrame,
            )
            and not table_df.empty
        ):
            story.append(
                Paragraph(
                    "<b>Data Table</b>",
                    body_style,
                )
            )

            story.append(
                Spacer(
                    1,
                    2 * mm,
                )
            )

            report_table = _build_report_table(
                table_df,
                available_width,
                colors,
                Paragraph,
                Table,
                TableStyle,
                table_body_style,
                table_header_style,
            )

            if report_table is not None:
                story.append(report_table)

                if len(table_df) > MAX_TABLE_ROWS:
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
                                f"{MAX_TABLE_ROWS:,} "
                                f"rows of "
                                f"{len(table_df):,} "
                                "available rows."
                            ),
                            body_style,
                        )
                    )

            story.append(
                Spacer(
                    1,
                    6 * mm,
                )
            )

        else:
            story.append(
                Paragraph(
                    (
                        "No underlying table "
                        "data available "
                        "for this chart."
                    ),
                    body_style,
                )
            )

            story.append(
                Spacer(
                    1,
                    6 * mm,
                )
            )

        # ----------------------------------------------------
        # New page for next chart
        # ----------------------------------------------------

        if index < len(charts):
            story.append(PageBreak())

    # ========================================================
    # BUILD
    # ========================================================

    doc.build(story)

    return buffer.getvalue()


# ============================================================
# SAFE FILE NAME
# ============================================================

def _safe_filename(text):
    text = str(text).strip()

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
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new,
        )

    text = text.replace(
        " ",
        "_",
    )

    if not text:
        text = "Chart"

    return text


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
            chart = item.get("chart")

            title = (
                item.get("title")
                or f"Chart {index}"
            )

            safe_title = _safe_filename(title)

            try:
                png_bytes = _chart_to_png(chart)

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
        "The PDF includes each chart followed by its data table."
    )

    # ========================================================
    # FINGERPRINT
    # ========================================================

    fingerprint = _make_fingerprint(
        charts,
        filter_summary,
    )

    cache_key = (
        "displayed_chart_export_cache_v4_"
        f"{fingerprint}"
    )

    # ========================================================
    # BUILD EXPORTS
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

    col1, col2 = st.columns(2)

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
                item.get("title")
                or f"Chart {index}"
            )

            table_df = item.get("table")

            if (
                isinstance(
                    table_df,
                    pd.DataFrame,
                )
                and not table_df.empty
            ):
                rows = len(table_df)
                columns = len(table_df.columns)

                st.write(
                    f"**{index}. {title}** — "
                    f"{rows:,} rows × "
                    f"{columns:,} columns"
                )
            else:
                st.write(
                    f"**{index}. {title}** — "
                    "Chart image only"
                )
