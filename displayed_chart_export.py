import io
import html
import re
import hashlib
import json
from contextlib import contextmanager

import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

DISPLAYED_CHARTS_KEY = "displayed_chart_exports"
DISPLAYED_TABLES_KEY = "displayed_table_exports"
DISPLAYED_METRICS_KEY = "displayed_metric_exports"
DISPLAYED_NOTES_KEY = "displayed_note_exports"

MAX_TABLE_ROWS = 300
MAX_TABLE_COLUMNS = 14

PDF_MARGIN_MM = 12

MIN_CHART_HEIGHT_MM = 55
MAX_CHART_HEIGHT_MM = 145

MONTHLY_DISEASE_HEIGHT_MM = 88


# ============================================================
# REGISTRY HELPERS
# ============================================================

def _get_registry():
    if DISPLAYED_CHARTS_KEY not in st.session_state:
        st.session_state[DISPLAYED_CHARTS_KEY] = []

    return st.session_state[DISPLAYED_CHARTS_KEY]


def _get_table_registry():
    if DISPLAYED_TABLES_KEY not in st.session_state:
        st.session_state[DISPLAYED_TABLES_KEY] = []

    return st.session_state[DISPLAYED_TABLES_KEY]


def _get_metric_registry():
    if DISPLAYED_METRICS_KEY not in st.session_state:
        st.session_state[DISPLAYED_METRICS_KEY] = []

    return st.session_state[DISPLAYED_METRICS_KEY]


def _get_note_registry():
    if DISPLAYED_NOTES_KEY not in st.session_state:
        st.session_state[DISPLAYED_NOTES_KEY] = []

    return st.session_state[DISPLAYED_NOTES_KEY]


def _clear_registry():
    st.session_state[DISPLAYED_CHARTS_KEY] = []
    st.session_state[DISPLAYED_TABLES_KEY] = []
    st.session_state[DISPLAYED_METRICS_KEY] = []
    st.session_state[DISPLAYED_NOTES_KEY] = []


def get_captured_dashboard_content():
    """
    Return all captured content for the currently rendered dashboard page.

    This is used by app.py when building the Complete Dashboard PDF.
    """

    return {
        "charts": list(
            st.session_state.get(
                DISPLAYED_CHARTS_KEY,
                [],
            )
        ),
        "tables": list(
            st.session_state.get(
                DISPLAYED_TABLES_KEY,
                [],
            )
        ),
        "metrics": list(
            st.session_state.get(
                DISPLAYED_METRICS_KEY,
                [],
            )
        ),
        "notes": list(
            st.session_state.get(
                DISPLAYED_NOTES_KEY,
                [],
            )
        ),
    }


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

    # Remove simple markdown emphasis around headings.
    text = re.sub(
        r"^\s*\*{1,2}(.*?)\*{1,2}\s*$",
        r"\1",
        text,
    )

    return text.strip()


def _looks_like_heading(value):
    text = _clean_heading_text(value)

    if not text:
        return False

    if len(text) > 160:
        return False

    return True


def _clean_display_text(value):
    if value is None:
        return ""

    try:
        text = str(value).strip()
    except Exception:
        return ""

    if not text:
        return ""

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# GENERIC DATAFRAME CONVERSION
# ============================================================

def _to_dataframe(value):
    if value is None:
        return pd.DataFrame()

    if isinstance(value, pd.DataFrame):
        return value.copy()

    if isinstance(value, pd.Series):
        return (
            value
            .to_frame()
            .reset_index()
        )

    try:
        return pd.DataFrame(value)

    except Exception:
        return pd.DataFrame()


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
                frame = pd.DataFrame(values)

                if not frame.empty:
                    return frame

        # ----------------------------------------------------
        # Named datasets
        # ----------------------------------------------------

        datasets = chart_dict.get("datasets")

        if isinstance(datasets, dict):
            frames = []

            for _, values in datasets.items():

                if isinstance(values, list):
                    frame = pd.DataFrame(values)

                    if not frame.empty:
                        frames.append(frame)

            if frames:
                try:
                    return pd.concat(
                        frames,
                        ignore_index=True,
                    ).drop_duplicates(
                        ignore_index=True,
                    )

                except Exception:
                    return frames[0]

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

                if isinstance(layer_data, dict):

                    values = layer_data.get(
                        "values"
                    )

                    if isinstance(values, list):

                        frame = pd.DataFrame(
                            values
                        )

                        if not frame.empty:
                            frames.append(frame)

            if frames:

                try:
                    return pd.concat(
                        frames,
                        ignore_index=True,
                    ).drop_duplicates(
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

                        values = child_data.get(
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
                        ).drop_duplicates(
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
# FINGERPRINT HELPERS
# ============================================================

def _stable_json(value):
    try:
        return json.dumps(
            value,
            sort_keys=True,
            default=str,
            ensure_ascii=False,
        )

    except Exception:
        return str(value)


def _hash_text(value):
    return hashlib.sha256(
        str(value).encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()


def _chart_fingerprint(
    chart,
    chart_title,
    section_name,
):
    """
    Duplicate-safe chart fingerprint.

    The chart specification itself is included so that two genuinely
    different charts are not removed merely because they use similar data.
    """

    try:
        chart_dict = chart.to_dict()

        payload = {
            "section_name": section_name,
            "title": chart_title,
            "chart": chart_dict,
        }

        return _hash_text(
            _stable_json(payload)
        )

    except Exception:

        payload = (
            f"{section_name}|"
            f"{chart_title}|"
            f"{repr(chart)}"
        )

        return _hash_text(payload)


def _dataframe_fingerprint(
    dataframe,
    title,
    section_name,
):
    try:
        work_df = dataframe.copy()

        payload = {
            "title": title,
            "section_name": section_name,
            "columns": [
                str(column)
                for column in work_df.columns
            ],
            "data": work_df.astype(
                str
            ).to_dict(
                orient="records"
            ),
        }

        return _hash_text(
            _stable_json(payload)
        )

    except Exception:
        return _hash_text(
            f"{section_name}|"
            f"{title}|"
            f"{repr(dataframe)}"
        )


# ============================================================
# CAPTURE DISPLAYED DASHBOARD CONTENT
# ============================================================

@contextmanager
def capture_displayed_charts():
    """
    Backward-compatible dashboard capture context.

    Historically this function captured only Altair charts.

    It now captures:
        - Altair charts
        - st.dataframe
        - st.table
        - st.metric
        - selected informational messages

    Existing code can continue using:

        with capture_displayed_charts():
            render_page(...)

    without modification.
    """

    original_altair_chart = st.altair_chart

    original_dataframe = st.dataframe
    original_table = st.table
    original_metric = st.metric

    original_subheader = st.subheader
    original_header = st.header
    original_title = st.title
    original_markdown = st.markdown

    original_info = st.info
    original_warning = st.warning
    original_success = st.success

    _clear_registry()

    heading_state = {
        "page": "",
        "current": "",
    }

    seen_chart_fingerprints = set()
    seen_table_fingerprints = set()
    seen_metric_fingerprints = set()
    seen_note_fingerprints = set()

    # ========================================================
    # HEADING STATE
    # ========================================================

    def _set_heading(
        text,
        heading_type,
    ):
        cleaned = _clean_heading_text(
            text
        )

        if not cleaned:
            return

        if heading_type == "title":
            heading_state["page"] = cleaned
            heading_state["current"] = cleaned

        else:
            heading_state["current"] = cleaned

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    def _captured_title(
        body,
        *args,
        **kwargs,
    ):
        _set_heading(
            body,
            "title",
        )

        return original_title(
            body,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    def _captured_header(
        body,
        *args,
        **kwargs,
    ):
        _set_heading(
            body,
            "header",
        )

        return original_header(
            body,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Subheader
    # --------------------------------------------------------

    def _captured_subheader(
        body,
        *args,
        **kwargs,
    ):
        _set_heading(
            body,
            "subheader",
        )

        return original_subheader(
            body,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Markdown heading
    # --------------------------------------------------------

    def _captured_markdown(
        body,
        *args,
        **kwargs,
    ):
        detected_heading = ""

        try:
            raw_text = str(body)

            # Only treat actual Markdown # headings as section headings.
            match = re.search(
                r"(?m)^\s*#{1,6}\s+(.+?)\s*$",
                raw_text,
            )

            if match:
                candidate = _clean_heading_text(
                    match.group(1)
                )

                if _looks_like_heading(
                    candidate
                ):
                    detected_heading = candidate

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

    # ========================================================
    # CHART CAPTURE
    # ========================================================

    def _captured_altair_chart(
        chart,
        *args,
        **kwargs,
    ):
        registry = _get_registry()

        chart_title = _get_chart_title(
            chart
        )

        section_name = (
            heading_state["current"]
            or chart_title
            or heading_state["page"]
            or f"Chart {len(registry) + 1}"
        )

        if not chart_title:
            chart_title = section_name

        fingerprint = (
            _chart_fingerprint(
                chart=chart,
                chart_title=chart_title,
                section_name=section_name,
            )
        )

        if (
            fingerprint
            not in seen_chart_fingerprints
        ):
            seen_chart_fingerprints.add(
                fingerprint
            )

            chart_data = (
                _extract_chart_dataframe(
                    chart
                )
            )

            registry.append(
                {
                    "type": "chart",
                    "chart": chart,
                    "data": chart_data,
                    "title": chart_title,
                    "section_name": section_name,
                    "fingerprint": fingerprint,
                }
            )

        return original_altair_chart(
            chart,
            *args,
            **kwargs,
        )

    # ========================================================
    # TABLE CAPTURE
    # ========================================================

    def _capture_table_object(
        data,
        table_type,
    ):
        dataframe = _to_dataframe(
            data
        )

        if dataframe.empty:
            return

        registry = (
            _get_table_registry()
        )

        section_name = (
            heading_state["current"]
            or heading_state["page"]
            or "Displayed Data"
        )

        table_title = section_name

        fingerprint = (
            _dataframe_fingerprint(
                dataframe=dataframe,
                title=table_title,
                section_name=section_name,
            )
        )

        if (
            fingerprint
            in seen_table_fingerprints
        ):
            return

        seen_table_fingerprints.add(
            fingerprint
        )

        registry.append(
            {
                "type": "table",
                "table_type": table_type,
                "title": table_title,
                "section_name": section_name,
                "data": dataframe,
                "fingerprint": fingerprint,
            }
        )

    def _captured_dataframe(
        data=None,
        *args,
        **kwargs,
    ):
        try:
            _capture_table_object(
                data=data,
                table_type="dataframe",
            )

        except Exception:
            pass

        return original_dataframe(
            data,
            *args,
            **kwargs,
        )

    def _captured_table(
        data=None,
        *args,
        **kwargs,
    ):
        try:
            _capture_table_object(
                data=data,
                table_type="table",
            )

        except Exception:
            pass

        return original_table(
            data,
            *args,
            **kwargs,
        )

    # ========================================================
    # METRIC CAPTURE
    # ========================================================

    def _captured_metric(
        label,
        value,
        delta=None,
        *args,
        **kwargs,
    ):
        registry = (
            _get_metric_registry()
        )

        section_name = (
            heading_state["current"]
            or heading_state["page"]
            or "Key Performance Indicators"
        )

        payload = {
            "label": str(label),
            "value": str(value),
            "delta": (
                ""
                if delta is None
                else str(delta)
            ),
            "section_name": section_name,
        }

        fingerprint = _hash_text(
            _stable_json(payload)
        )

        if (
            fingerprint
            not in seen_metric_fingerprints
        ):
            seen_metric_fingerprints.add(
                fingerprint
            )

            registry.append(
                {
                    "type": "metric",
                    "title": str(label),
                    "label": str(label),
                    "value": str(value),
                    "delta": (
                        ""
                        if delta is None
                        else str(delta)
                    ),
                    "section_name": section_name,
                    "fingerprint": fingerprint,
                }
            )

        return original_metric(
            label,
            value,
            delta,
            *args,
            **kwargs,
        )

    # ========================================================
    # NOTE CAPTURE
    # ========================================================

    def _capture_note(
        body,
        note_type,
    ):
        text = _clean_display_text(
            body
        )

        if not text:
            return

        # Avoid capturing very large HTML / technical blocks.
        if len(text) > 1200:
            return

        section_name = (
            heading_state["current"]
            or heading_state["page"]
            or "Dashboard Information"
        )

        payload = {
            "text": text,
            "note_type": note_type,
            "section_name": section_name,
        }

        fingerprint = _hash_text(
            _stable_json(payload)
        )

        if (
            fingerprint
            in seen_note_fingerprints
        ):
            return

        seen_note_fingerprints.add(
            fingerprint
        )

        _get_note_registry().append(
            {
                "type": "note",
                "note_type": note_type,
                "text": text,
                "section_name": section_name,
                "fingerprint": fingerprint,
            }
        )

    def _captured_info(
        body,
        *args,
        **kwargs,
    ):
        try:
            _capture_note(
                body,
                "info",
            )
        except Exception:
            pass

        return original_info(
            body,
            *args,
            **kwargs,
        )

    def _captured_warning(
        body,
        *args,
        **kwargs,
    ):
        try:
            _capture_note(
                body,
                "warning",
            )
        except Exception:
            pass

        return original_warning(
            body,
            *args,
            **kwargs,
        )

    def _captured_success(
        body,
        *args,
        **kwargs,
    ):
        try:
            _capture_note(
                body,
                "success",
            )
        except Exception:
            pass

        return original_success(
            body,
            *args,
            **kwargs,
        )

    # ========================================================
    # ACTIVATE CAPTURE
    # ========================================================

    st.title = _captured_title
    st.header = _captured_header
    st.subheader = _captured_subheader
    st.markdown = _captured_markdown

    st.altair_chart = (
        _captured_altair_chart
    )

    st.dataframe = (
        _captured_dataframe
    )

    st.table = (
        _captured_table
    )

    st.metric = (
        _captured_metric
    )

    st.info = (
        _captured_info
    )

    st.warning = (
        _captured_warning
    )

    st.success = (
        _captured_success
    )

    try:
        yield

    finally:
        st.title = original_title
        st.header = original_header
        st.subheader = original_subheader
        st.markdown = original_markdown

        st.altair_chart = (
            original_altair_chart
        )

        st.dataframe = (
            original_dataframe
        )

        st.table = (
            original_table
        )

        st.metric = (
            original_metric
        )

        st.info = (
            original_info
        )

        st.warning = (
            original_warning
        )

        st.success = (
            original_success
        )


# ============================================================
# MONTHLY DISEASE COMPARISON DETECTION
# ============================================================

def _is_monthly_disease_comparison(
    item
):
    if not isinstance(
        item,
        dict,
    ):
        return False

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
# PREPARE EXPORT CHART
# ============================================================

def _prepare_chart_for_export(
    item
):
    chart = item.get(
        "chart"
    )

    if chart is None:
        return None

    try:
        if _is_monthly_disease_comparison(
            item
        ):
            return chart.properties(
                width=1000,
                height=320,
            )

        chart_dict = (
            chart.to_dict()
        )

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

        return chart.properties(
            width=1000,
            height=height,
        )

    except Exception:
        return chart


# ============================================================
# CHART TO PNG
# ============================================================

def _chart_to_png(
    item
):
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

        width, height = (
            image.size
        )

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
# IMAGE SIZE
# ============================================================

def _get_chart_image_size(
    item,
    png_bytes=None,
    available_width=None,
    available_height=None,
):
    """
    Backward-compatible sizing helper.

    Supported calls:

        _get_chart_image_size(item)

    and:

        _get_chart_image_size(
            item,
            png_bytes,
            available_width,
            available_height,
        )
    """

    from reportlab.lib.units import mm

    # --------------------------------------------------------
    # Compatibility defaults
    # --------------------------------------------------------

    if png_bytes is None:
        png_bytes = _chart_to_png(
            item
        )

    if available_width is None:
        available_width = (
            186 * mm
        )

    if available_height is None:
        available_height = (
            250 * mm
        )

    image_width, image_height = (
        _get_image_dimensions(
            png_bytes
        )
        if png_bytes
        else (
            None,
            None,
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
                100 * mm,
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
            * mm
        )

        if height > preferred_height:
            height = (
                preferred_height
            )

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
    # Normal charts
    # --------------------------------------------------------

    else:
        min_height = (
            MIN_CHART_HEIGHT_MM
            * mm
        )

        max_height = (
            MAX_CHART_HEIGHT_MM
            * mm
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
# BUILD TABLE
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
        LongTable,
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

    column_count = len(
        table_df.columns
    )

    if column_count <= 5:
        header_font_size = 7.2
        body_font_size = 6.8

    elif column_count <= 9:
        header_font_size = 6.5
        body_font_size = 6.0

    else:
        header_font_size = 5.8
        body_font_size = 5.3

    header_style = ParagraphStyle(
        "ReportTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=header_font_size,
        leading=header_font_size + 1.5,
        alignment=TA_LEFT,
        textColor=colors.white,
    )

    body_style = ParagraphStyle(
        "ReportTableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=body_font_size,
        leading=body_font_size + 1.5,
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
            for column
            in table_df.columns
        ]
    ]

    for _, row in (
        table_df.iterrows()
    ):
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
                for value
                in row.tolist()
            ]
        )

    if column_count <= 0:
        return None

    column_width = (
        table_width
        / column_count
    )

    table = LongTable(
        data,
        colWidths=[
            column_width
            for _ in range(
                column_count
            )
        ],
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#1F4E78"
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
    from reportlab.lib import colors
    from reportlab.lib.enums import (
        TA_CENTER,
    )

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
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor(
                "#1F4E78"
            ),
            spaceAfter=5,
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
    from reportlab.platypus import (
        Paragraph,
    )

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
            story.append(
                Paragraph(
                    "<br/>".join(
                        summary_parts
                    ),
                    style,
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
                style,
            )
        )


# ============================================================
# BUILD DISPLAYED CHART PDF
# ============================================================

def _build_pdf(
    charts,
    report_title,
    filter_summary,
    mode,
):
    from reportlab.lib.pagesizes import (
        A4,
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
    # SECTIONS
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
            or section_name
        )

        data = item.get(
            "data"
        )

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                f"Section {index}",
                styles["section_number"],
            )
        )

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

        if (
            chart_title
            and chart_title
            != section_name
        ):
            story.append(
                Paragraph(
                    html.escape(
                        str(
                            chart_title
                        )
                    ),
                    styles["chart_title"],
                )
            )

        # ====================================================
        # CHART
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

                (
                    chart_width,
                    chart_height,
                ) = _get_chart_image_size(
                    item,
                    png_bytes,
                    available_width,
                    max_chart_height,
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
        # TABLE
        # ====================================================

        if mode in (
            "charts_and_data",
            "table_only",
        ):
            table_df = _to_dataframe(
                data
            )

            table = (
                _build_report_table(
                    table_df,
                    available_width,
                )
            )

            if table is not None:
                story.append(
                    Paragraph(
                        "Displayed Data",
                        styles[
                            "table_heading"
                        ],
                    )
                )

                story.append(
                    table
                )

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
        f"{len(charts)} unique chart section(s) "
        "available for export."
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

            chart_title = (
                item.get(
                    "title"
                )
                or ""
            )

            if (
                chart_title
                and chart_title
                != section_name
            ):
                st.write(
                    f"{index}. "
                    f"{section_name} — "
                    f"{chart_title}"
                )

            else:
                st.write(
                    f"{index}. "
                    f"{section_name}"
                )

    st.divider()

    # ========================================================
    # OPTION 1
    # ========================================================

    st.markdown(
        "### 1️⃣ Charts with Section Name"
    )

    st.caption(
        "Section name + chart only."
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
                    "📊 Download Charts + "
                    "Section Name PDF"
                ),
                data=pdf_charts_only,
                file_name=_safe_filename(
                    f"{base_filename}"
                    "_Charts_Section_Name",
                    ".pdf",
                ),
                mime="application/pdf",
                use_container_width=True,
                key=(
                    "download_charts_"
                    "section_name_pdf"
                ),
            )

    except Exception as exc:
        st.error(
            "Charts with Section Name PDF "
            "could not be generated."
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
        "Section name + chart + "
        "corresponding data table."
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
                    f"{base_filename}"
                    "_Charts_Data_Section_Name",
                    ".pdf",
                ),
                mime="application/pdf",
                use_container_width=True,
                key=(
                    "download_charts_data_"
                    "section_name_pdf"
                ),
            )

    except Exception as exc:
        st.error(
            "Charts with Data & Section Name "
            "PDF could not be generated."
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
        "Section name + corresponding "
        "chart data table only."
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
                    f"{base_filename}"
                    "_Only_Tables",
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
            "Only Table PDF could not "
            "be generated."
        )

        with st.expander(
            "Technical details"
        ):
            st.code(
                str(exc)
            )
