import pandas as pd
import streamlit as st
import altair as alt


# ============================================================
# DISPLAYED CHART REGISTRY
# ============================================================

DISPLAYED_CHARTS_KEY = "displayed_chart_exports"


# ============================================================
# REGISTRY HELPERS
# ============================================================

def _ensure_chart_registry():

    if DISPLAYED_CHARTS_KEY not in st.session_state:
        st.session_state[DISPLAYED_CHARTS_KEY] = []

    return st.session_state[DISPLAYED_CHARTS_KEY]


def reset_displayed_chart_registry():

    st.session_state[
        DISPLAYED_CHARTS_KEY
    ] = []


def register_displayed_chart(
    chart,
    title="Chart",
    filename=None,
    table_data=None,
):

    if chart is None:
        return

    registry = _ensure_chart_registry()

    if filename is None:
        filename = title

    safe_filename = (
        str(filename)
        .strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace("&", "and")
        .replace(":", "_")
    )

    # --------------------------------------------------------
    # Prepare exact table data
    # --------------------------------------------------------

    table = None

    if isinstance(
        table_data,
        pd.DataFrame,
    ):

        table = table_data.copy()

    elif isinstance(
        table_data,
        pd.Series,
    ):

        table = table_data.reset_index()

        if len(table.columns) >= 2:

            table.columns = [
                str(table.columns[0]),
                "Records",
            ]

    elif table_data is not None:

        try:
            table = pd.DataFrame(
                table_data
            )
        except Exception:
            table = None

    registry.append(
        {
            "title": str(title),
            "filename": safe_filename,
            "chart": chart,
            "table": table,
        }
    )


def get_displayed_charts():

    return list(
        st.session_state.get(
            DISPLAYED_CHARTS_KEY,
            [],
        )
    )


# ============================================================
# DATA LABEL CONTROL
# ============================================================

def data_labels_enabled():

    return bool(
        st.session_state.get(
            "show_data_labels",
            False,
        )
    )


# ============================================================
# CHART DATA PREPARATION
# ============================================================

def _prepare_chart_data(data):

    if isinstance(
        data,
        pd.Series,
    ):

        result = data.reset_index()

        if len(result.columns) >= 2:

            result.columns = [
                str(result.columns[0]),
                "Records",
            ]

        return result

    if isinstance(
        data,
        pd.DataFrame,
    ):

        result = data.copy()

        return result

    return pd.DataFrame()


# ============================================================
# FIELD TYPE
# ============================================================

def _field_type(series):

    if pd.api.types.is_numeric_dtype(
        series
    ):

        return "Q"

    if pd.api.types.is_datetime64_any_dtype(
        series
    ):

        return "T"

    return "N"


# ============================================================
# REGISTER + DISPLAY
# ============================================================

def _register_and_display(
    chart,
    title,
    filename,
    export_table=None,
    use_container_width=True,
):

    register_displayed_chart(
        chart=chart,
        title=title,
        filename=filename,
        table_data=export_table,
    )

    st.altair_chart(
        chart,
        use_container_width=use_container_width,
    )


# ============================================================
# BAR CHART
# ============================================================

def render_bar_chart(
    data,
    title=None,
    x_title=None,
    y_title="Records",
    horizontal=False,
    use_container_width=True,
    show_values=None,
    export_title=None,
    export_filename=None,
    export_table=None,
):

    chart_df = _prepare_chart_data(
        data
    )

    if chart_df.empty:
        st.info(
            "No data available for this chart."
        )
        return None

    # --------------------------------------------------------
    # Determine columns
    # --------------------------------------------------------

    columns = list(
        chart_df.columns
    )

    if len(columns) < 2:

        st.info(
            "Insufficient data for chart."
        )
        return None

    x_column = columns[0]
    y_column = columns[1]

    # --------------------------------------------------------
    # If x_title / y_title are not supplied
    # --------------------------------------------------------

    x_axis_title = (
        x_title
        if x_title
        else str(x_column)
    )

    y_axis_title = (
        y_title
        if y_title
        else str(y_column)
    )

    # --------------------------------------------------------
    # Horizontal chart
    # --------------------------------------------------------

    if horizontal:

        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                y=alt.Y(
                    f"{x_column}:N",
                    sort="-x",
                    title=x_axis_title,
                ),
                x=alt.X(
                    f"{y_column}:Q",
                    title=y_axis_title,
                ),
                tooltip=[
                    alt.Tooltip(
                        f"{x_column}:N",
                        title=x_axis_title,
                    ),
                    alt.Tooltip(
                        f"{y_column}:Q",
                        title=y_axis_title,
                        format=",",
                    ),
                ],
            )
        )

        if show_values:

            text = (
                alt.Chart(chart_df)
                .mark_text(
                    align="left",
                    dx=4,
                )
                .encode(
                    y=alt.Y(
                        f"{x_column}:N",
                        sort="-x",
                    ),
                    x=alt.X(
                        f"{y_column}:Q"
                    ),
                    text=alt.Text(
                        f"{y_column}:Q",
                        format=",",
                    ),
                )
            )

            chart = (
                chart
                + text
            )

    # --------------------------------------------------------
    # Vertical chart
    # --------------------------------------------------------

    else:

        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X(
                    f"{x_column}:N",
                    title=x_axis_title,
                    sort=None,
                    axis=alt.Axis(
                        labelAngle=-45,
                    ),
                ),
                y=alt.Y(
                    f"{y_column}:Q",
                    title=y_axis_title,
                ),
                tooltip=[
                    alt.Tooltip(
                        f"{x_column}:N",
                        title=x_axis_title,
                    ),
                    alt.Tooltip(
                        f"{y_column}:Q",
                        title=y_axis_title,
                        format=",",
                    ),
                ],
            )
        )

        if show_values:

            text = (
                alt.Chart(chart_df)
                .mark_text(
                    dy=-6,
                )
                .encode(
                    x=alt.X(
                        f"{x_column}:N",
                        sort=None,
                    ),
                    y=alt.Y(
                        f"{y_column}:Q"
                    ),
                    text=alt.Text(
                        f"{y_column}:Q",
                        format=",",
                    ),
                )
            )

            chart = (
                chart
                + text
            )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if title:

        chart = chart.properties(
            title=alt.TitleParams(
                text=title,
                fontSize=18,
                anchor="start",
            )
        )

    # --------------------------------------------------------
    # Size
    # --------------------------------------------------------

    if horizontal:

        chart = chart.properties(
            height=max(
                300,
                min(
                    700,
                    len(chart_df) * 28,
                ),
            )
        )

    else:

        chart = chart.properties(
            height=430
        )

    chart = chart.configure_axis(
        labelFontSize=11,
        titleFontSize=12,
    )

    chart = chart.configure_title(
        fontSize=18,
    )

    # --------------------------------------------------------
    # Export table
    # --------------------------------------------------------

    if export_table is None:

        export_table = chart_df.copy()

    _register_and_display(
        chart=chart,
        title=(
            export_title
            or title
            or "Bar Chart"
        ),
        filename=(
            export_filename
            or export_title
            or title
            or "Bar_Chart"
        ),
        export_table=export_table,
        use_container_width=use_container_width,
    )

    return chart


# ============================================================
# LINE CHART
# ============================================================

def render_line_chart(
    data,
    title=None,
    x_title=None,
    y_title="Records",
    use_container_width=True,
    show_values=None,
    export_title=None,
    export_filename=None,
    export_table=None,
):

    chart_df = _prepare_chart_data(
        data
    )

    if chart_df.empty:
        st.info(
            "No data available for this chart."
        )
        return None

    columns = list(
        chart_df.columns
    )

    if len(columns) < 2:

        st.info(
            "Insufficient data for chart."
        )
        return None

    x_column = columns[0]
    y_column = columns[1]

    x_type = _field_type(
        chart_df[x_column]
    )

    x_axis_title = (
        x_title
        if x_title
        else str(x_column)
    )

    y_axis_title = (
        y_title
        if y_title
        else str(y_column)
    )

    # --------------------------------------------------------
    # Base chart
    # --------------------------------------------------------

    chart = (
        alt.Chart(chart_df)
        .mark_line(
            point=True,
        )
        .encode(
            x=alt.X(
                f"{x_column}:{x_type}",
                title=x_axis_title,
            ),
            y=alt.Y(
                f"{y_column}:Q",
                title=y_axis_title,
            ),
            tooltip=[
                alt.Tooltip(
                    f"{x_column}:{x_type}",
                    title=x_axis_title,
                ),
                alt.Tooltip(
                    f"{y_column}:Q",
                    title=y_axis_title,
                    format=",",
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # Data labels
    # --------------------------------------------------------

    if show_values:

        text = (
            alt.Chart(chart_df)
            .mark_text(
                dy=-10,
                fontSize=10,
            )
            .encode(
                x=alt.X(
                    f"{x_column}:{x_type}"
                ),
                y=alt.Y(
                    f"{y_column}:Q"
                ),
                text=alt.Text(
                    f"{y_column}:Q",
                    format=",",
                ),
            )
        )

        chart = (
            chart
            + text
        )

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    if title:

        chart = chart.properties(
            title=alt.TitleParams(
                text=title,
                fontSize=18,
                anchor="start",
            )
        )

    chart = chart.properties(
        height=480
    )

    chart = chart.configure_axis(
        labelFontSize=11,
        titleFontSize=12,
    )

    chart = chart.configure_title(
        fontSize=18,
    )

    # --------------------------------------------------------
    # Export table
    # --------------------------------------------------------

    if export_table is None:

        export_table = chart_df.copy()

    _register_and_display(
        chart=chart,
        title=(
            export_title
            or title
            or "Line Chart"
        ),
        filename=(
            export_filename
            or export_title
            or title
            or "Line_Chart"
        ),
        export_table=export_table,
        use_container_width=use_container_width,
    )

    return chart
