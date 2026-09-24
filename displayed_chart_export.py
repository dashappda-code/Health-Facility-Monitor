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
# CHART DATA EXTRACTION
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


def _extract_chart_dataframe(chart):

    """
    Try to extract the dataframe directly from an Altair chart.

    Handles:
    - normal charts
    - layered charts
    - concatenated charts
    - charts where data is stored in datasets
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
    # Chart dictionary
    # --------------------------------------------------------

    try:

        spec = chart.to_dict()

    except Exception:

        return pd.DataFrame()


    # --------------------------------------------------------
    # Direct data block
    # --------------------------------------------------------

    try:

        if isinstance(spec, dict):

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

        if datasets:

            frames = []

            for dataset_name, values in datasets.items():

                frame = _safe_dataframe(values)

                if not frame.empty:

                    frames.append(frame)

            if frames:

                # Usually there is one main dataset.
                # If multiple datasets exist, combine where possible.
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

        if layers:

            for layer in layers:

                if not isinstance(layer, dict):
                    continue

                layer_data = layer.get("data")

                if isinstance(layer_data, dict):

                    values = layer_data.get("values")

                    if values is not None:

                        result = _safe_dataframe(
                            values
                        )

                        if not result.empty:
                            return result

                layer_name = layer.get("name")

                if layer_name:
                    continue

    except Exception:
        pass


    return pd.DataFrame()


# ============================================================
# CLEAN TABLE FOR REPORT
# ============================================================

def _prepare_report_table(data):

    df = _safe_dataframe(data)

    if df.empty:
        return df

    result = df.copy()

    # Remove unnamed index columns
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

    # Convert datetime columns to readable text
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
            # Try chart title
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
            # Extract chart data
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
                    "title": title
                    or f"Chart {len(captured_charts) + 1}",
                    "table": table_df,
                }
            )

        except Exception:

            captured_charts.append(
                {
                    "chart": chart,
                    "title": f"Chart {len(captured_charts) + 1}",
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
# ALTair -> PNG
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

    return hashlib.md5(
        raw
    ).hexdigest()


# ============================================================
# PDF HELPERS
# ============================================================

def _build_pdf(
    charts,
    filter_summary="",
):

    try:

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Image,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
            PageBreak,
        )

    except ImportError as e:

        raise ImportError(
            "reportlab is required for PDF export."
        ) from e


    buffer = io.BytesIO()


    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )


    styles = getSampleStyleSheet()


    title_style = styles["Title"]
    title_style.alignment = TA_CENTER


    heading_style = styles["Heading2"]

    body_style = styles["BodyText"]


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
        Spacer(
            1,
            5 * mm,
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

        story.append(
            Paragraph(
                f"<b>Filters:</b> "
                f"{filter_summary}",
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
    # CHARTS
    # ========================================================

    for index, item in enumerate(
        charts,
        start=1,
    ):

        chart = item.get(
            "chart"
        )

        title = item.get(
            "title"
        ) or f"Chart {index}"


        # ----------------------------------------------------
        # Chart title
        # ----------------------------------------------------

        story.append(
            Paragraph(
                f"{index}. {title}",
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

            png_bytes = _chart_to_png(
                chart
            )

            image_buffer = io.BytesIO(
                png_bytes
            )

            image = Image(
                image_buffer,
            )

            # Fit landscape-ish chart into A4 width
            image.drawWidth = 180 * mm
            image.drawHeight = 90 * mm

            story.append(
                image
            )

            story.append(
                Spacer(
                    1,
                    4 * mm,
                )
            )

        except Exception as e:

            story.append(
                Paragraph(
                    f"Chart image could not be rendered: {e}",
                    body_style,
                )
            )


        # ----------------------------------------------------
        # TABLE
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


            display_df = table_df.copy()


            # Avoid extremely wide tables
            if len(display_df.columns) > 12:

                display_df = display_df.iloc[
                    :,
                    :12,
                ]


            # Limit very large chart tables
            if len(display_df) > 100:

                display_df = display_df.head(
                    100
                )


            headers = [
                str(column)
                for column in display_df.columns
            ]


            table_data = [
                headers
            ]


            for _, row in display_df.iterrows():

                values = []

                for value in row:

                    if pd.isna(value):

                        values.append("")

                    elif isinstance(
                        value,
                        float,
                    ):

                        if value.is_integer():

                            values.append(
                                f"{int(value):,}"
                            )

                        else:

                            values.append(
                                f"{value:,.2f}"
                            )

                    else:

                        values.append(
                            str(value)
                        )

                table_data.append(
                    values
                )


            report_table = Table(
                table_data,
                repeatRows=1,
            )


            report_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor(
                                "#E8EEF5"
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


            story.append(
                report_table
            )

            story.append(
                Spacer(
                    1,
                    8 * mm,
                )
            )

        else:

            story.append(
                Paragraph(
                    "No underlying table data available for this chart.",
                    body_style,
                )
            )

            story.append(
                Spacer(
                    1,
                    7 * mm,
                )
            )


        # ----------------------------------------------------
        # Page break after each chart section
        # ----------------------------------------------------

        if index < len(charts):

            story.append(
                PageBreak()
            )


    # ========================================================
    # BUILD PDF
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
                    f"{index:02d}_{safe_title}.png",
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


    fingerprint = _make_fingerprint(
        charts,
        filter_summary,
    )


    cache_key = (
        f"displayed_chart_export_cache_{fingerprint}"
    )


    # ========================================================
    # BUILD EXPORTS ONLY WHEN REQUIRED
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
                f"download_displayed_chart_pdf_"
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
                f"download_displayed_chart_png_"
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
