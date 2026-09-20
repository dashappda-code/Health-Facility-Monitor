import streamlit as st
import pandas as pd
import altair as alt


def data_labels_enabled():
    return bool(
        st.session_state.get(
            "show_data_labels",
            False,
        )
    )


def _prepare_chart_data(data):
    """
    Convert Series/DataFrame into a standard dataframe
    without changing the underlying values.
    """

    if isinstance(data, pd.Series):

        result = data.reset_index()

        if len(result.columns) >= 2:
            result.columns = [
                str(result.columns[0]),
                "Records",
            ]

        return result

    if isinstance(data, pd.DataFrame):

        result = data.reset_index()

        if len(result.columns) > 0:
            result = result.rename(
                columns={
                    result.columns[0]: str(
                        result.columns[0]
                    )
                }
            )

        return result

    return pd.DataFrame()


def render_bar_chart(
    data,
    use_container_width=True,
    height=400,
):
    """
    Global bar-chart renderer.

    Existing chart data is not recalculated or changed.
    Data labels are controlled only by the global switch.
    """

    chart_df = _prepare_chart_data(data)

    if chart_df.empty:
        return

    x_column = chart_df.columns[0]
    value_columns = list(chart_df.columns[1:])

    if not value_columns:
        return

    if len(value_columns) == 1:

        value_column = value_columns[0]

        chart = (
            alt.Chart(chart_df)
            .mark_bar()
            .encode(
                x=alt.X(
                    f"{x_column}:N",
                    title=x_column,
                ),
                y=alt.Y(
                    f"{value_column}:Q",
                    title=value_column,
                ),
                tooltip=[
                    alt.Tooltip(
                        f"{x_column}:N",
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

        if data_labels_enabled():

            labels = (
                alt.Chart(chart_df)
                .mark_text(
                    dy=-8,
                )
                .encode(
                    x=alt.X(
                        f"{x_column}:N",
                        title=x_column,
                    ),
                    y=alt.Y(
                        f"{value_column}:Q"
                    ),
                    text=alt.Text(
                        f"{value_column}:Q"
                    ),
                )
            )

            chart = chart + labels

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
                    f"{x_column}:N",
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
                        f"{x_column}:N",
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

        if data_labels_enabled():

            labels = (
                alt.Chart(chart_long)
                .mark_text(
                    dy=-8,
                )
                .encode(
                    x=alt.X(
                        f"{x_column}:N"
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

    st.altair_chart(
        chart,
        use_container_width=use_container_width,
    )


def render_line_chart(
    data,
    use_container_width=True,
    height=400,
):
    """
    Global line-chart renderer.

    Existing chart values and ordering are preserved.
    """

    chart_df = _prepare_chart_data(data)

    if chart_df.empty:
        return

    x_column = chart_df.columns[0]
    value_columns = list(chart_df.columns[1:])

    if not value_columns:
        return

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
                f"{x_column}:N",
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
                    f"{x_column}:N",
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

    if data_labels_enabled():

        labels = (
            alt.Chart(chart_long)
            .mark_text(
                dy=-10,
            )
            .encode(
                x=alt.X(
                    f"{x_column}:N"
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

    st.altair_chart(
        chart,
        use_container_width=use_container_width,
    )
