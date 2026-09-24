import io

import streamlit as st
import pandas as pd
import altair as alt


# ============================================================
# GLOBAL CHART EXPORT REGISTRY
# ============================================================

DISPLAYED_CHARTS_KEY = "displayed_chart_exports"


def _ensure_chart_registry():
    """
    Creates the session-state registry used by the displayed
    chart + table export system.
    """

    if DISPLAYED_CHARTS_KEY not in st.session_state:
        st.session_state[DISPLAYED_CHARTS_KEY] = []

    return st.session_state[DISPLAYED_CHARTS_KEY]


def reset_displayed_chart_registry():
    """
    Clears the displayed-chart registry.

    This should be called once before rendering a dashboard
    section whose displayed charts need to be exported.
    """

    st.session_state[DISPLAYED_CHARTS_KEY] = []


def register_displayed_chart(
    chart,
    title="Chart",
    filename=None,
    table_data=None,
):
    """
    Register an Altair chart for displayed-chart export.

    Parameters
    ----------
    chart:
        Exact Altair chart object displayed on dashboard.

    title:
        Chart title used in exported PDF.

    filename:
        Safe filename used for exported image.

    table_data:
        Optional pandas DataFrame containing the exact
        table associated with this chart.

    The table_data is copied into the registry so that
    later dataframe modifications do not affect the
    already registered export data.
    """

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
    # Prepare table safely
    # --------------------------------------------------------

    if isinstance(table_data, pd.DataFrame):

        table_copy = table_data.copy()

        # Remove pandas index from exported table.
        table_copy = table_copy.reset_index(drop=True)

    elif isinstance(table_data, pd.Series):

        table_copy = (
            table_data
            .reset_index()
            .copy()
        )

    else:

        table_copy = None

    registry.append(
        {
            "title": str(title),
            "filename": safe_filename,
            "chart": chart,
            "table": table_copy,
        }
    )


def get_displayed_charts():
    """
    Return currently registered displayed charts.

    Each registry item can contain:

        title
        filename
        chart
        table
    """

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
    """
    Returns the global dashboard data-label setting.
    """

    return bool(
        st.session_state.get(
            "show_data_labels",
            False,
        )
    )


# ============================================================
# DATA PREPARATION
# ============================================================

def _prepare_chart_data(data):
    """
    Convert Series/DataFrame into a standard dataframe
    without changing the underlying values.
    """

    # --------------------------------------------------------
    # Series
    # --------------------------------------------------------

    if isinstance(data, pd.Series):

        result = data.reset_index()

        if len(result.columns) >= 2:

            result.columns = [
                str(result.columns[0]),
                "Records",
            ]

        return result

    # --------------------------------------------------------
    # DataFrame
    # --------------------------------------------------------

    if isinstance(data, pd.DataFrame):

        result = data.copy()

        # Preserve existing columns.
        result.columns = [
            str(column)
            for column in result.columns
        ]

        return result

    return pd.DataFrame()


def _field_type(series):
    """
    Return Altair field type.
    """

    if pd.api.types.is_numeric_dtype(series):
        return "Q"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "T"

    return "N"


# ============================================================
# SAFE CHART EXPORT REGISTRATION
# ============================================================

def _register_and_display(
    chart,
    title,
    filename,
    table_data=None,
    use_container_width=True,
):
    """
    Register the exact chart object and then display it.

    table_data is the exact dataframe associated with
    the chart and is used by the PDF export.
    """

    register_displayed_chart(
        chart=chart,
        title=title,
        filename=filename,
        table_data=table_data,
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
    use_container_width=True,
    height=400,
    export_title=None,
    export_filename=None,
    export_table=None,
):
    """
    Global bar-chart renderer.

    Existing data and calculations are preserved.

    The exact Altair chart displayed on the dashboard is
    registered for PDF/PNG export.

    export_table:
        Optional exact dataframe to be shown below the
        chart in the exported PDF.

        If not supplied, the chart dataframe itself is used.
    """

    chart_df = _prepare_chart_data(data)

    if chart_df.empty:
        return None

    x_column = chart_df.columns[0]

    value_columns = list(
        chart_df.columns[1:]
    )

    if not value_columns:
        return None

    x_type = _field_type(
        chart_df[x_column]
    )

    # ========================================================
    # SINGLE SERIES BAR CHART
    # ========================================================

    if len(value_columns) == 1:

        value_column = value_columns[0]

        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X(
                    f"{x_column}:{x_type}",
                    title=x_column,
                ),
                y=alt.Y(
                    f"{value_column}:Q",
                    title=value_column,
                ),
                color=alt.Color(
                    f"{x_column}:N",
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip(
                        f"{x_column}:{x_type}",
                        title=x_column,
                    ),
                    alt.Tooltip(
                        f"{value_column}:Q",
                        title=value_column,
                    ),
                ],
            )
            .properties(
                height=height,
            )
        )

        # ----------------------------------------------------
        # DATA LABELS
        # ----------------------------------------------------

        if data_labels_enabled():

            labels = (
                alt.Chart(chart_df)
                .mark_text(
                    dy=-8,
                    fontWeight="bold",
                    fontSize=13,
                )
                .encode(
                    x=alt.X(
                        f"{x_column}:{x_type}"
                    ),
                    y=alt.Y(
                        f"{value_column}:Q"
                    ),
                    color=alt.Color(
                        f"{x_column}:N",
                        legend=None,
                    ),
                    text=alt.Text(
                        f"{value_column}:Q"
                    ),
                )
            )

            chart = chart + labels

    # ========================================================
    # MULTI SERIES BAR CHART
    # ========================================================

    else:

        chart_long = chart_df.melt(
            id_vars=[x_column],
            var_name="Series",
            value_name="Value",
        )

        chart = (
            alt.Chart(chart_long)
            .mark_bar()
            .encode(
                x=alt.X(
                    f"{x_column}:{x_type}",
                    title=x_column,
                ),
                y=alt.Y(
                    "Value:Q",
                    title="Records",
                ),
                color=alt.Color(
                    "Series:N",
                    title="Series",
                ),
                tooltip=[
                    alt.Tooltip(
                        f"{x_column}:{x_type}",
                        title=x_column,
                    ),
                    alt.Tooltip(
                        "Series:N",
                        title="Series",
                    ),
                    alt.Tooltip(
                        "Value:Q",
                        title="Records",
                    ),
                ],
            )
            .properties(
                height=height,
            )
        )

        # ----------------------------------------------------
        # DATA LABELS
        # ----------------------------------------------------

        if data_labels_enabled():

            labels = (
                alt.Chart(chart_long)
                .mark_text(
                    dy=-8,
                    fontWeight="bold",
                    fontSize=13,
                )
                .encode(
                    x=alt.X(
                        f"{x_column}:{x_type}"
                    ),
                    y=alt.Y(
                        "Value:Q"
                    ),
                    color=alt.Color(
                        "Series:N",
                        legend=None,
                    ),
                    text=alt.Text(
                        "Value:Q"
                    ),
                )
            )

            chart = chart + labels

    # ========================================================
    # EXPORT TITLE
    # ========================================================

    if export_title is None:
        export_title = "Bar Chart"

    if export_filename is None:
        export_filename = export_title

    # ========================================================
    # EXPORT TABLE
    # ========================================================

    if export_table is None:

        export_table = chart_df.copy()

    # ========================================================
    # REGISTER + DISPLAY
    # ========================================================

    _register_and_display(
        chart=chart,
        title=export_title,
        filename=export_filename,
        table_data=export_table,
        use_container_width=use_container_width,
    )

    return chart


# ============================================================
# LINE CHART
# ============================================================

def render_line_chart(
    data,
    use_container_width=True,
    height=400,
    export_title=None,
    export_filename=None,
    export_table=None,
):
    """
    Global line-chart renderer.

    Existing values and ordering are preserved.

    The exact Altair chart displayed on the dashboard is
    registered for PDF/PNG export.

    export_table:
        Optional exact dataframe to be shown below the
        chart in the exported PDF.

        If not supplied, the chart dataframe itself is used.
    """

    chart_df = _prepare_chart_data(data)

    if chart_df.empty:
        return None

    x_column = chart_df.columns[0]

    value_columns = list(
        chart_df.columns[1:]
    )

    if not value_columns:
        return None

    x_type = _field_type(
        chart_df[x_column]
    )

    chart_long = chart_df.melt(
        id_vars=[x_column],
        var_name="Series",
        value_name="Value",
    )

    chart = (
        alt.Chart(chart_long)
        .mark_line(
            point=True,
        )
        .encode(
            x=alt.X(
                f"{x_column}:{x_type}",
                title=x_column,
            ),
            y=alt.Y(
                "Value:Q",
                title="Records",
            ),
            color=alt.Color(
                "Series:N",
                title="Series",
            ),
            tooltip=[
                alt.Tooltip(
                    f"{x_column}:{x_type}",
                    title=x_column,
                ),
                alt.Tooltip(
                    "Series:N",
                    title="Series",
                ),
                alt.Tooltip(
                    "Value:Q",
                    title="Records",
                ),
            ],
        )
        .properties(
            height=height,
        )
    )

    # ========================================================
    # DATA LABELS
    # ========================================================

    if data_labels_enabled():

        labels = (
            alt.Chart(chart_long)
            .mark_text(
                dy=-10,
                fontWeight="bold",
                fontSize=12,
            )
            .encode(
                x=alt.X(
                    f"{x_column}:{x_type}"
                ),
                y=alt.Y(
                    "Value:Q"
                ),
                color=alt.Color(
                    "Series:N",
                    legend=None,
                ),
                text=alt.Text(
                    "Value:Q"
                ),
            )
        )

        chart = chart + labels

    # ========================================================
    # EXPORT TITLE
    # ========================================================

    if export_title is None:
        export_title = "Line Chart"

    if export_filename is None:
        export_filename = export_title

    # ========================================================
    # EXPORT TABLE
    # ========================================================

    if export_table is None:

        export_table = chart_df.copy()

    # ========================================================
    # REGISTER + DISPLAY
    # ========================================================

    _register_and_display(
        chart=chart,
        title=export_title,
        filename=export_filename,
        table_data=export_table,
        use_container_width=use_container_width,
    )

    return chart
