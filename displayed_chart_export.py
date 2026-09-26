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
CAPTURED_DASHBOARD_CONTENT_KEY = "captured_dashboard_content"

MAX_TABLE_ROWS = 300
MAX_TABLE_COLUMNS = 14

PDF_MARGIN_MM = 12

MIN_CHART_HEIGHT_MM = 55
MAX_CHART_HEIGHT_MM = 145

MONTHLY_DISEASE_HEIGHT_MM = 88


# ============================================================
# EMPTY CAPTURE STRUCTURE
# ============================================================

def _empty_capture_content():
    return {
        "charts": [],
        "tables": [],
        "metrics": [],
        "notes": [],
        "images": [],
    }


# ============================================================
# REGISTRY
# ============================================================

def _get_registry():
    if DISPLAYED_CHARTS_KEY not in st.session_state:
        st.session_state[DISPLAYED_CHARTS_KEY] = []

    return st.session_state[DISPLAYED_CHARTS_KEY]


def _get_capture_registry():
    if CAPTURED_DASHBOARD_CONTENT_KEY not in st.session_state:
        st.session_state[CAPTURED_DASHBOARD_CONTENT_KEY] = (
            _empty_capture_content()
        )

    registry = st.session_state[
        CAPTURED_DASHBOARD_CONTENT_KEY
    ]

    if not isinstance(registry, dict):
        registry = _empty_capture_content()

        st.session_state[
            CAPTURED_DASHBOARD_CONTENT_KEY
        ] = registry

    for key in (
        "charts",
        "tables",
        "metrics",
        "notes",
        "images",
    ):
        if key not in registry:
            registry[key] = []

    return registry


def _clear_registry():
    st.session_state[DISPLAYED_CHARTS_KEY] = []

    st.session_state[
        CAPTURED_DASHBOARD_CONTENT_KEY
    ] = _empty_capture_content()


# ============================================================
# SAFE COPY HELPERS
# ============================================================

def _safe_dataframe_copy(value):
    if value is None:
        return pd.DataFrame()

    if isinstance(value, pd.DataFrame):
        try:
            return value.copy()
        except Exception:
            return value

    if isinstance(value, pd.Series):
        try:
            return value.to_frame().reset_index(drop=True)
        except Exception:
            return pd.DataFrame()

    try:
        return pd.DataFrame(value)

    except Exception:
        return pd.DataFrame()


def _safe_text(value):
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    try:
        return str(value).strip()
    except Exception:
        return ""


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

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = html.unescape(text)

    text = re.sub(
        r"\s+",
        " ",
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


def _extract_markdown_heading(body):
    if body is None:
        return ""

    try:
        raw_text = str(body)
    except Exception:
        return ""

    match = re.search(
        r"(?m)^\s*#{1,6}\s+(.+?)\s*$",
        raw_text,
    )

    if match:
        candidate = _clean_heading_text(
            match.group(1)
        )

        if _looks_like_heading(candidate):
            return candidate

    return ""


# ============================================================
# SIGNATURE / FINGERPRINT
# ============================================================

def _signature_value(value):
    if value is None:
        return ""

    if isinstance(value, pd.DataFrame):
        try:
            work = value.copy().fillna("")

            payload = {
                "columns": [
                    str(column)
                    for column in work.columns
                ],
                "data": (
                    work.astype(str)
                    .to_dict(orient="records")
                ),
            }

            return json.dumps(
                payload,
                sort_keys=True,
                default=str,
            )

        except Exception:
            return repr(value)

    if isinstance(value, pd.Series):
        try:
            return _signature_value(
                value.to_frame()
            )
        except Exception:
            return repr(value)

    if isinstance(value, dict):
        try:
            return json.dumps(
                value,
                sort_keys=True,
                default=str,
            )
        except Exception:
            return repr(value)

    if isinstance(value, (list, tuple)):
        try:
            return json.dumps(
                value,
                sort_keys=True,
                default=str,
            )
        except Exception:
            return repr(value)

    if isinstance(value, (bytes, bytearray)):
        try:
            return hashlib.sha256(
                bytes(value)
            ).hexdigest()
        except Exception:
            return repr(value)

    try:
        return str(value)
    except Exception:
        return repr(value)


def _make_fingerprint(
    item_type,
    section_name="",
    title="",
    data=None,
    value=None,
    text=None,
    extra=None,
):
    raw = (
        f"{item_type}|"
        f"{section_name}|"
        f"{title}|"
        f"{_signature_value(data)}|"
        f"{_signature_value(value)}|"
        f"{_signature_value(text)}|"
        f"{_signature_value(extra)}"
    )

    return hashlib.sha256(
        raw.encode(
            "utf-8",
            errors="ignore",
        )
    ).hexdigest()


# ============================================================
# CHART DATA EXTRACTION
# ============================================================

def _extract_chart_dataframe(chart):
    try:
        chart_dict = chart.to_dict()

        # ----------------------------------------------------
        # Direct data.values
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
                    combined = pd.concat(
                        frames,
                        ignore_index=True,
                    )

                    return combined.drop_duplicates(
                        ignore_index=True
                    )

                except Exception:
                    return frames[0]

        # ----------------------------------------------------
        # Layer charts
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
                    combined = pd.concat(
                        frames,
                        ignore_index=True,
                    )

                    return combined.drop_duplicates(
                        ignore_index=True
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

            if not isinstance(charts, list):
                continue

            frames = []

            for child in charts:
                if not isinstance(child, dict):
                    continue

                child_data = child.get("data")

                if isinstance(child_data, dict):
                    values = child_data.get(
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
                    combined = pd.concat(
                        frames,
                        ignore_index=True,
                    )

                    return combined.drop_duplicates(
                        ignore_index=True
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

        if isinstance(title, str):
            return title.strip()

        if isinstance(title, dict):
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
# CAPTURED CONTENT ACCESS
# ============================================================

def get_captured_dashboard_content():
    registry = _get_capture_registry()

    return {
        "charts": list(
            registry.get(
                "charts",
                [],
            )
        ),
        "tables": list(
            registry.get(
                "tables",
                [],
            )
        ),
        "metrics": list(
            registry.get(
                "metrics",
                [],
            )
        ),
        "notes": list(
            registry.get(
                "notes",
                [],
            )
        ),
        "images": list(
            registry.get(
                "images",
                [],
            )
        ),
    }


# ============================================================
# CAPTURE DISPLAYED DASHBOARD CONTENT
# ============================================================

@contextmanager
def capture_displayed_charts():
    """
    Capture dashboard content displayed while a page render
    function runs.

    Captures:
    - Altair charts
    - st.dataframe
    - st.table
    - st.metric
    - st.info
    - st.warning
    - st.success
    - st.error
    - st.caption
    - st.image
    - headings / section names

    Existing dashboard rendering continues normally.
    """

    original_altair_chart = st.altair_chart
    original_dataframe = st.dataframe
    original_table = st.table
    original_metric = st.metric

    original_info = st.info
    original_warning = st.warning
    original_success = st.success
    original_error = st.error
    original_caption = st.caption

    original_image = st.image

    original_subheader = st.subheader
    original_header = st.header
    original_title = st.title
    original_markdown = st.markdown

    _clear_registry()

    heading_state = {
        "current": "",
    }

    # ========================================================
    # HEADING CAPTURE
    # ========================================================

    def _set_heading(value):
        text = _clean_heading_text(
            value
        )

        if text:
            heading_state[
                "current"
            ] = text

    def _current_section(
        fallback="Dashboard Section"
    ):
        return (
            heading_state.get(
                "current",
                ""
            )
            or fallback
        )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    def _captured_title(
        body,
        *args,
        **kwargs,
    ):
        _set_heading(body)

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
        _set_heading(body)

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
        _set_heading(body)

        return original_subheader(
            body,
            *args,
            **kwargs,
        )

    # --------------------------------------------------------
    # Markdown
    # --------------------------------------------------------

    def _captured_markdown(
        body,
        *args,
        **kwargs,
    ):
        detected_heading = (
            _extract_markdown_heading(
                body
            )
        )

        if detected_heading:
            heading_state[
                "current"
            ] = detected_heading

        return original_markdown(
            body,
            *args,
            **kwargs,
        )

    # ========================================================
    # ALTAIR CHART
    # ========================================================

    def _captured_altair_chart(
        chart,
        *args,
        **kwargs,
    ):
        chart_registry = (
            _get_registry()
        )

        capture_registry = (
            _get_capture_registry()
        )

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
            _current_section(
                chart_title
                or (
                    f"Chart "
                    f"{len(chart_registry) + 1}"
                )
            )
        )

        if not chart_title:
            chart_title = (
                section_name
                or (
                    f"Chart "
                    f"{len(chart_registry) + 1}"
                )
            )

        try:
            chart_dict = chart.to_dict()
        except Exception:
            chart_dict = {}

        fingerprint = (
            _make_fingerprint(
                item_type="chart",
                section_name=section_name,
                title=chart_title,
                data=chart_data,
                extra=chart_dict,
            )
        )

        item = {
            "chart": chart,
            "data": chart_data,
            "title": chart_title,
            "section_name": section_name,
            "fingerprint": fingerprint,
        }

        chart_registry.append(
            item
        )

        capture_registry[
            "charts"
        ].append(
            item
        )

        return original_altair_chart(
            chart,
            *args,
            **kwargs,
        )

    # ========================================================
    # DATAFRAME
    # ========================================================

    def _captured_dataframe(
        data=None,
        *args,
        **kwargs,
    ):
        frame = (
            _safe_dataframe_copy(
                data
            )
        )

        if not frame.empty:
            section_name = (
                _current_section(
                    "Displayed Data"
                )
            )

            title = section_name

            fingerprint = (
                _make_fingerprint(
                    item_type="table",
                    section_name=section_name,
                    title=title,
                    data=frame,
                    extra="dataframe",
                )
            )

            _get_capture_registry()[
                "tables"
            ].append(
                {
                    "title": title,
                    "section_name": (
                        section_name
                    ),
                    "data": frame,
                    "dataframe": frame,
                    "table_type": (
                        "dataframe"
                    ),
                    "fingerprint": (
                        fingerprint
                    ),
                }
            )

        return original_dataframe(
            data,
            *args,
            **kwargs,
        )

    # ========================================================
    # TABLE
    # ========================================================

    def _captured_table(
        data=None,
        *args,
        **kwargs,
    ):
        frame = (
            _safe_dataframe_copy(
                data
            )
        )

        if not frame.empty:
            section_name = (
                _current_section(
                    "Displayed Table"
                )
            )

            title = section_name

            fingerprint = (
                _make_fingerprint(
                    item_type="table",
                    section_name=section_name,
                    title=title,
                    data=frame,
                    extra="table",
                )
            )

            _get_capture_registry()[
                "tables"
            ].append(
                {
                    "title": title,
                    "section_name": (
                        section_name
                    ),
                    "data": frame,
                    "dataframe": frame,
                    "table_type": (
                        "table"
                    ),
                    "fingerprint": (
                        fingerprint
                    ),
                }
            )

        return original_table(
            data,
            *args,
            **kwargs,
        )

    # ========================================================
    # METRIC
    # ========================================================

    def _captured_metric(
        label,
        value,
        delta=None,
        *args,
        **kwargs,
    ):
        section_name = (
            _current_section(
                "Dashboard Metrics"
            )
        )

        label_text = (
            _safe_text(label)
            or "Metric"
        )

        fingerprint = (
            _make_fingerprint(
                item_type="metric",
                section_name=section_name,
                title=label_text,
                value={
                    "value": value,
                    "delta": delta,
                },
            )
        )

        _get_capture_registry()[
            "metrics"
        ].append(
            {
                "title": label_text,
                "label": label_text,
                "value": value,
                "delta": delta,
                "section_name": (
                    section_name
                ),
                "fingerprint": (
                    fingerprint
                ),
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
    # NOTES
    # ========================================================

    def _capture_note(
        body,
        note_type,
    ):
        text = _safe_text(
            body
        )

        if not text:
            return

        section_name = (
            _current_section(
                "Dashboard Notes"
            )
        )

        fingerprint = (
            _make_fingerprint(
                item_type="note",
                section_name=section_name,
                title=note_type,
                text=text,
            )
        )

        _get_capture_registry()[
            "notes"
        ].append(
            {
                "text": text,
                "message": text,
                "note": text,
                "note_type": (
                    note_type
                ),
                "section_name": (
                    section_name
                ),
                "fingerprint": (
                    fingerprint
                ),
            }
        )

    def _captured_info(
        body,
        *args,
        **kwargs,
    ):
        _capture_note(
            body,
            "info",
        )

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
        _capture_note(
            body,
            "warning",
        )

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
        _capture_note(
            body,
            "success",
        )

        return original_success(
            body,
            *args,
            **kwargs,
        )

    def _captured_error(
        body,
        *args,
        **kwargs,
    ):
        _capture_note(
            body,
            "error",
        )

        return original_error(
            body,
            *args,
            **kwargs,
        )

    def _captured_caption(
        body,
        *args,
        **kwargs,
    ):
        _capture_note(
            body,
            "caption",
        )

        return original_caption(
            body,
            *args,
            **kwargs,
        )

    # ========================================================
    # IMAGE
    # ========================================================

    def _captured_image(
        image,
        *args,
        **kwargs,
    ):
        section_name = (
            _current_section(
                "Dashboard Image"
            )
        )

        caption = kwargs.get(
            "caption",
            "",
        )

        image_bytes = None

        # ----------------------------------------------------
        # Raw bytes
        # ----------------------------------------------------

        if isinstance(
            image,
            bytes,
        ):
            image_bytes = image

        elif isinstance(
            image,
            bytearray,
        ):
            image_bytes = bytes(
                image
            )

        elif isinstance(
            image,
            io.BytesIO,
        ):
            try:
                current_position = (
                    image.tell()
                )

                image.seek(0)

                image_bytes = (
                    image.read()
                )

                image.seek(
                    current_position
                )

            except Exception:
                image_bytes = None

        # ----------------------------------------------------
        # PIL image
        # ----------------------------------------------------

        else:
            try:
                from PIL import Image as PILImage

                if isinstance(
                    image,
                    PILImage.Image,
                ):
                    temp_buffer = (
                        io.BytesIO()
                    )

                    image.save(
                        temp_buffer,
                        format="PNG",
                    )

                    image_bytes = (
                        temp_buffer.getvalue()
                    )

            except Exception:
                pass

        if image_bytes:
            fingerprint = (
                _make_fingerprint(
                    item_type="image",
                    section_name=section_name,
                    title=section_name,
                    data=image_bytes,
                    text=caption,
                )
            )

            _get_capture_registry()[
                "images"
            ].append(
                {
                    "title": (
                        section_name
                    ),
                    "section_name": (
                        section_name
                    ),
                    "caption": (
                        _safe_text(
                            caption
                        )
                    ),
                    "type": "image",
                    "data": (
                        image_bytes
                    ),
                    "bytes": (
                        image_bytes
                    ),
                    "fingerprint": (
                        fingerprint
                    ),
                }
            )

        return original_image(
            image,
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

    st.error = (
        _captured_error
    )

    st.caption = (
        _captured_caption
    )

    st.image = (
        _captured_image
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

        st.error = (
            original_error
        )

        st.caption = (
            original_caption
        )

        st.image = (
            original_image
        )


# ============================================================
# MONTHLY DISEASE COMPARISON DETECTION
# ============================================================

def _is_monthly_disease_comparison(item):
    if not isinstance(item, dict):
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

def _prepare_chart_for_export(item):
    if not isinstance(item, dict):
        return None

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

        return chart.properties(
            width=1000,
            height=height,
        )

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
    png_bytes,
):
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
    item,
    png_bytes=None,
    available_width=None,
    available_height=None,
):
    """
    Backward-compatible helper.

    Supported calls:

        _get_chart_image_size(item)

    and:

        _get_chart_image_size(
            item,
            png_bytes,
            available_width,
            available_height,
        )

    When only item is supplied, returns approximate pixel
    dimensions suitable for dashboard_pdf_export.py.
    """

    # --------------------------------------------------------
    # OLD / SIMPLE CALL
    # --------------------------------------------------------

    if (
        png_bytes is None
        and available_width is None
        and available_height is None
    ):
        if _is_monthly_disease_comparison(
            item
        ):
            return (
                1000.0,
                320.0,
            )

        chart = None

        if isinstance(item, dict):
            chart = item.get(
                "chart"
            )

        if chart is not None:
            try:
                chart_dict = (
                    chart.to_dict()
                )

                width = chart_dict.get(
                    "width",
                    1000,
                )

                height = chart_dict.get(
                    "height",
                    360,
                )

                if not isinstance(
                    width,
                    (int, float),
                ):
                    width = 1000

                if not isinstance(
                    height,
                    (int, float),
                ):
                    height = 360

                return (
                    float(width),
                    float(height),
                )

            except Exception:
                pass

        return (
            1000.0,
            360.0,
        )

    # --------------------------------------------------------
    # FULL CALL
    # --------------------------------------------------------

    if available_width is None:
        available_width = 500.0

    if available_height is None:
        available_height = 700.0

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
            float(
                available_width
            ),
            min(
                float(
                    available_height
                ),
                100 * 2.834645669,
            ),
        )

    ratio = (
        image_height
        / image_width
    )

    width = float(
        available_width
    )

    height = (
        width
        * ratio
    )

    # --------------------------------------------------------
    # MONTHLY DISEASE
    # --------------------------------------------------------

    if _is_monthly_disease_comparison(
        item
    ):
        preferred_height = (
            MONTHLY_DISEASE_HEIGHT_MM
            * 2.834645669
        )

        preferred_height = min(
            preferred_height,
            float(
                available_height
            ),
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
            width = float(
                available_width
            )

            height = (
                width
                * ratio
            )

    # --------------------------------------------------------
    # NORMAL CHART
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
            float(
                available_height
            ),
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
            width = float(
                available_width
            )

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
    value,
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
    df,
):
    if (
        df is None
        or not isinstance(
            df,
            pd.DataFrame,
        )
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
        or not isinstance(
            df,
            pd.DataFrame,
        )
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

    number_of_columns = len(
        table_df.columns
    )

    if number_of_columns <= 5:
        header_size = 7.5
        body_size = 7.0

    elif number_of_columns <= 9:
        header_size = 6.8
        body_size = 6.3

    else:
        header_size = 6.0
        body_size = 5.5

    header_style = ParagraphStyle(
        "ReportTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=header_size,
        leading=header_size + 1.5,
        alignment=TA_LEFT,
        textColor=colors.white,
    )

    body_style = ParagraphStyle(
        "ReportTableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=body_size,
        leading=body_size + 1.5,
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
                for value
                in row.tolist()
            ]
        )

    if number_of_columns <= 0:
        return None

    column_width = (
        table_width
        / number_of_columns
    )

    table = LongTable(
        data,
        colWidths=[
            column_width
            for _ in range(
                number_of_columns
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
                        "#B7C9D6"
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
        rightMargin=(
            PDF_MARGIN_MM
            * mm
        ),
        leftMargin=(
            PDF_MARGIN_MM
            * mm
        ),
        topMargin=(
            PDF_MARGIN_MM
            * mm
        ),
        bottomMargin=(
            PDF_MARGIN_MM
            * mm
        ),
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
    # CHART SECTIONS
    # ========================================================

    for index, item in enumerate(
        charts,
        start=1,
    ):
        section_name = (
            item.get(
                "section_name"
            )
            or item.get(
                "title"
            )
            or f"Chart {index}"
        )

        data = (
            item.get(
                "data"
            )
        )

        if not isinstance(
            data,
            pd.DataFrame,
        ):
            data = (
                _safe_dataframe_copy(
                    data
                )
            )

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                f"Section {index}",
                styles[
                    "section_number"
                ],
            )
        )

        story.append(
            Paragraph(
                html.escape(
                    str(
                        section_name
                    )
                ),
                styles[
                    "section_name"
                ],
            )
        )

        # ====================================================
        # CHART
        # ====================================================

        if mode in (
            "charts_only",
            "charts_and_data",
        ):
            png_bytes = (
                _chart_to_png(
                    item
                )
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
                ) = (
                    _get_chart_image_size(
                        item,
                        png_bytes,
                        available_width,
                        max_chart_height,
                    )
                )

                image = Image(
                    io.BytesIO(
                        png_bytes
                    ),
                    width=chart_width,
                    height=chart_height,
                )

                image.hAlign = "CENTER"

                story.append(
                    image
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
                styles[
                    "footer"
                ],
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
                or item.get(
                    "title"
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
        "Section name + chart only."
    )

    try:
        pdf_charts_only = (
            _build_pdf(
                charts=charts,
                report_title=(
                    "MSU Mumbai - "
                    "Charts with Section Name"
                ),
                filter_summary=(
                    filter_summary
                ),
                mode="charts_only",
            )
        )

        if pdf_charts_only:
            st.download_button(
                label=(
                    "📊 Download Charts + "
                    "Section Name PDF"
                ),
                data=(
                    pdf_charts_only
                ),
                file_name=(
                    _safe_filename(
                        (
                            f"{base_filename}_"
                            "Charts_Section_Name"
                        ),
                        ".pdf",
                    )
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
        "Section name + chart + corresponding data table."
    )

    try:
        pdf_charts_data = (
            _build_pdf(
                charts=charts,
                report_title=(
                    "MSU Mumbai - "
                    "Charts with Data & "
                    "Section Name"
                ),
                filter_summary=(
                    filter_summary
                ),
                mode="charts_and_data",
            )
        )

        if pdf_charts_data:
            st.download_button(
                label=(
                    "📊 Download Charts + Data PDF"
                ),
                data=(
                    pdf_charts_data
                ),
                file_name=(
                    _safe_filename(
                        (
                            f"{base_filename}_"
                            "Charts_Data_"
                            "Section_Name"
                        ),
                        ".pdf",
                    )
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
        "Section name + corresponding data table only."
    )

    try:
        pdf_table_only = (
            _build_pdf(
                charts=charts,
                report_title=(
                    "MSU Mumbai - "
                    "Tables with Section Name"
                ),
                filter_summary=(
                    filter_summary
                ),
                mode="table_only",
            )
        )

        if pdf_table_only:
            st.download_button(
                label=(
                    "📋 Download Only Tables PDF"
                ),
                data=(
                    pdf_table_only
                ),
                file_name=(
                    _safe_filename(
                        (
                            f"{base_filename}_"
                            "Only_Tables"
                        ),
                        ".pdf",
                    )
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
