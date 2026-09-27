import io
import math

import streamlit as st
import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_DISPLAY_COLUMNS = [
    "Reporting Date",
    "Year",
    "Month",
    "Week",
    "Disease",
    "Facility Name",
    "Ward Name",
    "Gender",
    "Age",
    "Age Group",
    "OPD/IPD",
    "Confirmed Diagnosis",
]

EXPLORER_FILTER_COLUMNS = [
    "Disease",
    "Ward Name",
    "Facility Name",
    "Gender",
    "Age Group",
    "OPD/IPD",
]

ROWS_PER_PAGE_OPTIONS = [
    50,
    100,
    250,
    500,
]

DEFAULT_ROWS_PER_PAGE = 100


# ============================================================
# COMMON HELPERS
# ============================================================

def _is_missing_series(series):

    actual_missing = series.isna()

    text_values = (
        series
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    text_missing = text_values.isin(
        [
            "",
            "nan",
            "nat",
            "none",
            "null",
            "<na>",
        ]
    )

    return actual_missing | text_missing


def _valid_values(series):

    if series is None:
        return []

    values = (
        series
        .fillna("")
        .astype(str)
        .str.strip()
    )

    invalid_values = {
        "",
        "nan",
        "NaT",
        "None",
        "null",
        "NULL",
        "<NA>",
    }

    values = values[
        ~values.isin(
            invalid_values
        )
    ]

    return sorted(
        values
        .drop_duplicates()
        .tolist(),
        key=lambda value:
        str(value).upper(),
    )


def _safe_unique_count(
    df,
    column,
):

    if (
        df is None
        or df.empty
        or column not in df.columns
    ):
        return 0

    series = df[column]

    missing_mask = (
        _is_missing_series(
            series
        )
    )

    try:

        return int(
            series[
                ~missing_mask
            ]
            .nunique(
                dropna=True
            )
        )

    except Exception:

        return len(
            set(
                series[
                    ~missing_mask
                ]
                .astype(str)
                .tolist()
            )
        )


def _prepare_display_data(df):

    if df is None or df.empty:
        return pd.DataFrame()

    display_df = (
        df.copy()
    )

    for column in (
        display_df.columns
    ):

        if (
            pd.api.types
            .is_datetime64_any_dtype(
                display_df[column]
            )
        ):

            display_df[column] = (
                display_df[column]
                .dt.strftime(
                    "%d-%m-%Y"
                )
            )

    return display_df


# ============================================================
# COLUMN SELECTOR
# ============================================================

def _column_selector(
    all_columns,
    default_columns,
):

    all_columns = list(
        all_columns
    )

    if not all_columns:
        return []

    select_all_key = (
        "explorer_columns_select_all"
    )

    initialized_key = (
        "explorer_columns_initialized"
    )

    option_keys = {
        column:
        f"explorer_column_{index}"
        for index, column
        in enumerate(
            all_columns
        )
    }

    if (
        initialized_key
        not in st.session_state
    ):

        st.session_state[
            initialized_key
        ] = True

        default_set = set(
            default_columns
        )

        st.session_state[
            select_all_key
        ] = (
            len(default_set)
            == len(all_columns)
        )

        for column in all_columns:

            st.session_state[
                option_keys[column]
            ] = (
                column
                in default_set
            )

    def select_all_changed():

        new_value = bool(
            st.session_state.get(
                select_all_key,
                False,
            )
        )

        for column in all_columns:

            st.session_state[
                option_keys[column]
            ] = new_value

    def individual_changed():

        all_selected = all(
            bool(
                st.session_state.get(
                    option_keys[column],
                    False,
                )
            )
            for column
            in all_columns
        )

        st.session_state[
            select_all_key
        ] = all_selected

    selected_columns = []

    with st.popover(
        "Select Columns",
        use_container_width=True,
    ):

        st.checkbox(
            "Select All",
            key=select_all_key,
            on_change=(
                select_all_changed
            ),
        )

        st.divider()

        for column in all_columns:

            checked = st.checkbox(
                column,
                key=(
                    option_keys[
                        column
                    ]
                ),
                on_change=(
                    individual_changed
                ),
            )

            if checked:

                selected_columns.append(
                    column
                )

    return selected_columns


# ============================================================
# DATA QUALITY
# ============================================================

def _create_quality_dataframe(
    df,
):

    quality_rows = []

    if df is None:

        return pd.DataFrame()

    total_records = len(
        df
    )

    for column in df.columns:

        series = df[column]

        missing_mask = (
            _is_missing_series(
                series
            )
        )

        missing = int(
            missing_mask.sum()
        )

        valid = (
            total_records
            - missing
        )

        if total_records > 0:

            missing_percent = (
                missing
                / total_records
                * 100
            )

        else:

            missing_percent = 0

        valid_series = (
            series[
                ~missing_mask
            ]
        )

        try:

            unique_count = int(
                valid_series.nunique(
                    dropna=True
                )
            )

        except Exception:

            unique_count = len(
                set(
                    valid_series
                    .astype(str)
                    .tolist()
                )
            )

        quality_rows.append(
            {
                "Column": column,
                "Data Type": str(
                    series.dtype
                ),
                "Records": (
                    total_records
                ),
                "Valid": valid,
                "Missing": missing,
                "Missing %": round(
                    missing_percent,
                    2,
                ),
                "Unique Values": (
                    unique_count
                ),
            }
        )

    return pd.DataFrame(
        quality_rows
    )


# ============================================================
# EXCEL EXPORT
# ============================================================

@st.cache_data(
    show_spinner=False,
    max_entries=5,
)
def _create_excel_bytes(
    data_df,
    quality_df,
    summary_df,
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        data_df.to_excel(
            writer,
            index=False,
            sheet_name=(
                "Filtered Data"
            ),
        )

        quality_df.to_excel(
            writer,
            index=False,
            sheet_name=(
                "Data Quality"
            ),
        )

        summary_df.to_excel(
            writer,
            index=False,
            sheet_name=(
                "Export Summary"
            ),
        )

        workbook = (
            writer.book
        )

        for sheet_name in [
            "Filtered Data",
            "Data Quality",
            "Export Summary",
        ]:

            worksheet = (
                workbook[
                    sheet_name
                ]
            )

            worksheet.freeze_panes = (
                "A2"
            )

            if (
                worksheet.max_row > 1
                and
                worksheet.max_column > 0
            ):

                worksheet.auto_filter.ref = (
                    worksheet.dimensions
                )

            # --------------------------------------------
            # Width calculation limited for performance.
            # Only inspect first 250 rows.
            # --------------------------------------------

            max_scan_row = min(
                worksheet.max_row,
                250,
            )

            for column_cells in (
                worksheet.iter_cols(
                    min_row=1,
                    max_row=max_scan_row,
                )
            ):

                max_length = 0

                first_cell = (
                    column_cells[0]
                )

                column_letter = (
                    first_cell.column_letter
                )

                for cell in (
                    column_cells
                ):

                    value = (
                        ""
                        if cell.value
                        is None
                        else str(
                            cell.value
                        )
                    )

                    max_length = max(
                        max_length,
                        len(value),
                    )

                worksheet.column_dimensions[
                    column_letter
                ].width = min(
                    max(
                        max_length + 2,
                        10,
                    ),
                    40,
                )

    output.seek(0)

    return output.getvalue()


# ============================================================
# EXPLORER FILTER
# ============================================================

def _apply_explorer_filter(
    dataframe,
    column,
    selected_values,
):

    if (
        dataframe is None
        or dataframe.empty
        or column
        not in dataframe.columns
        or not selected_values
    ):

        return dataframe

    values = (
        dataframe[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return (
        dataframe[
            values.isin(
                selected_values
            )
        ]
        .copy()
    )


# ============================================================
# PAGINATION HELPERS
# ============================================================

def _reset_explorer_page():

    st.session_state[
        "explorer_current_page"
    ] = 1


def _previous_page():

    current_page = int(
        st.session_state.get(
            "explorer_current_page",
            1,
        )
    )

    st.session_state[
        "explorer_current_page"
    ] = max(
        1,
        current_page - 1,
    )


def _next_page():

    current_page = int(
        st.session_state.get(
            "explorer_current_page",
            1,
        )
    )

    total_pages = int(
        st.session_state.get(
            "explorer_total_pages",
            1,
        )
    )

    st.session_state[
        "explorer_current_page"
    ] = min(
        total_pages,
        current_page + 1,
    )


# ============================================================
# MAIN DATA EXPLORER
# ============================================================

def render_explorer(df):

    st.subheader(
        "🔎 Data Explorer"
    )

    if df is None or df.empty:

        st.warning(
            "No records available for the selected filters."
        )

        return

    st.caption(
        "Explore, filter, search, sort and export record-level "
        "data after applying the Global Dashboard Filters."
    )

    base_df = df.copy()


    # ========================================================
    # 1. EXPLORER SUMMARY
    # ========================================================

    st.markdown(
        "### 1. 📊 Explorer Summary"
    )

    total_records = len(
        base_df
    )

    total_columns = len(
        base_df.columns
    )

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:

        st.metric(
            "Filtered Records",
            f"{total_records:,}",
        )

    with c2:

        st.metric(
            "Diseases",
            f"{_safe_unique_count(base_df, 'Disease'):,}",
        )

    with c3:

        st.metric(
            "Facilities",
            f"{_safe_unique_count(base_df, 'Facility Name'):,}",
        )

    with c4:

        st.metric(
            "Wards",
            f"{_safe_unique_count(base_df, 'Ward Name'):,}",
        )

    st.caption(
        f"{total_columns:,} data columns are available "
        "within the current Global Dashboard Filter selection."
    )


    # ========================================================
    # 2. EXPLORER FILTERS
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. 🎛️ Explorer Filters"
    )

    st.caption(
        "These filters apply only to the Data Explorer. "
        "They do not change the Global Dashboard Filters."
    )

    explorer_df = (
        base_df.copy()
    )

    available_filter_columns = [
        column
        for column
        in EXPLORER_FILTER_COLUMNS
        if column
        in base_df.columns
    ]

    explorer_filter_values = {}

    if available_filter_columns:

        filter_columns = (
            st.columns(3)
        )

        for index, column in enumerate(
            available_filter_columns
        ):

            options = (
                _valid_values(
                    base_df[
                        column
                    ]
                )
            )

            with filter_columns[
                index % 3
            ]:

                selected_values = (
                    st.multiselect(
                        column,
                        options=options,
                        default=[],
                        placeholder=(
                            f"All {column}"
                        ),
                        key=(
                            f"explorer_filter_"
                            f"{column}"
                        ),
                        on_change=(
                            _reset_explorer_page
                        ),
                    )
                )

            explorer_filter_values[
                column
            ] = selected_values

        for (
            column,
            selected_values,
        ) in (
            explorer_filter_values
            .items()
        ):

            if selected_values:

                explorer_df = (
                    _apply_explorer_filter(
                        explorer_df,
                        column,
                        selected_values,
                    )
                )

    else:

        st.info(
            "No standard Explorer filter columns "
            "are available in the current dataset."
        )

    active_filter_count = sum(
        1
        for values
        in explorer_filter_values.values()
        if values
    )

    if active_filter_count > 0:

        st.markdown(
            f"**Explorer filters active:** "
            f"{active_filter_count}  |  "
            f"**Matching records:** "
            f"{len(explorer_df):,}"
        )

    else:

        st.caption(
            "No Explorer-specific filters are currently applied."
        )


    # ========================================================
    # 3. SEARCH RECORDS
    # ========================================================

    st.divider()

    st.markdown(
        "### 3. 🔍 Search Records"
    )

    search_text = (
        st.text_input(
            "Search across all columns",
            placeholder=(
                "Enter disease, facility, ward, gender, "
                "patient address, diagnosis, etc."
            ),
            key="explorer_search",
            on_change=(
                _reset_explorer_page
            ),
        )
    )

    if search_text.strip():

        search_value = (
            search_text
            .strip()
            .lower()
        )

        # ----------------------------------------------------
        # Search one column at a time instead of building
        # another complete string DataFrame.
        # ----------------------------------------------------

        row_mask = pd.Series(
            False,
            index=explorer_df.index,
        )

        for column in (
            explorer_df.columns
        ):

            try:

                column_mask = (
                    explorer_df[
                        column
                    ]
                    .fillna("")
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        search_value,
                        regex=False,
                        na=False,
                    )
                )

                row_mask = (
                    row_mask
                    | column_mask
                )

            except Exception:

                continue

        explorer_df = (
            explorer_df[
                row_mask
            ]
            .copy()
        )

        st.markdown(
            f"**Search results:** "
            f"{len(explorer_df):,} records"
        )

    else:

        st.caption(
            "Enter text above to search across all "
            "available columns."
        )


    # ========================================================
    # 4. CURRENT RESULT SUMMARY
    # ========================================================

    st.divider()

    st.markdown(
        "### 4. 📈 Current Result Summary"
    )

    c1, c2, c3, c4 = (
        st.columns(4)
    )

    with c1:

        st.metric(
            "Records",
            f"{len(explorer_df):,}",
        )

    with c2:

        st.metric(
            "Diseases",
            f"{_safe_unique_count(explorer_df, 'Disease'):,}",
        )

    with c3:

        st.metric(
            "Facilities",
            f"{_safe_unique_count(explorer_df, 'Facility Name'):,}",
        )

    with c4:

        st.metric(
            "Wards",
            f"{_safe_unique_count(explorer_df, 'Ward Name'):,}",
        )


    # ========================================================
    # 5. SELECT COLUMNS
    # ========================================================

    st.divider()

    st.markdown(
        "### 5. 🧩 Select Columns"
    )

    all_columns = (
        base_df.columns
        .tolist()
    )

    default_columns = [
        column
        for column
        in DEFAULT_DISPLAY_COLUMNS
        if column
        in all_columns
    ]

    if not default_columns:

        default_columns = (
            all_columns[:15]
        )

    selected_columns = (
        _column_selector(
            all_columns=all_columns,
            default_columns=(
                default_columns
            ),
        )
    )

    if not selected_columns:

        st.warning(
            "Please select at least one column."
        )

        return

    st.caption(
        f"{len(selected_columns)} of "
        f"{len(all_columns)} columns selected."
    )


    # ========================================================
    # 6. SORT RECORDS
    # ========================================================

    st.divider()

    st.markdown(
        "### 6. ↕️ Sort Records"
    )

    sort_columns = (
        st.columns(
            [3, 1],
            gap="medium",
        )
    )

    with sort_columns[0]:

        sort_column = (
            st.selectbox(
                "Sort by",
                options=(
                    selected_columns
                ),
                key=(
                    "explorer_sort_column"
                ),
                on_change=(
                    _reset_explorer_page
                ),
            )
        )

    with sort_columns[1]:

        sort_descending = (
            st.checkbox(
                "Descending",
                value=True,
                key=(
                    "explorer_sort_"
                    "descending"
                ),
                on_change=(
                    _reset_explorer_page
                ),
            )
        )

    if (
        sort_column
        in explorer_df.columns
        and
        not explorer_df.empty
    ):

        try:

            explorer_df = (
                explorer_df
                .sort_values(
                    by=sort_column,
                    ascending=(
                        not sort_descending
                    ),
                    na_position="last",
                )
            )

        except Exception:

            pass


    # ========================================================
    # 7. RECORD-LEVEL DATA + PAGE NAVIGATION
    # ========================================================

    st.divider()

    st.markdown(
        "### 7. 📋 Record-level Data"
    )

    st.caption(
        "Use the page controls directly below to move through "
        "the record table. Previous and Next change the records "
        "shown in this table only."
    )

    if (
        "explorer_current_page"
        not in st.session_state
    ):

        st.session_state[
            "explorer_current_page"
        ] = 1

    navigation_columns = (
        st.columns(
            [2, 1, 2, 1, 1],
            gap="small",
        )
    )

    with navigation_columns[0]:

        rows_per_page = (
            st.selectbox(
                "Rows per page",
                options=(
                    ROWS_PER_PAGE_OPTIONS
                ),
                index=(
                    ROWS_PER_PAGE_OPTIONS
                    .index(
                        DEFAULT_ROWS_PER_PAGE
                    )
                ),
                key=(
                    "explorer_rows_per_page"
                ),
                on_change=(
                    _reset_explorer_page
                ),
            )
        )

    total_result_rows = len(
        explorer_df
    )

    total_pages = max(
        1,
        math.ceil(
            total_result_rows
            / rows_per_page
        ),
    )

    st.session_state[
        "explorer_total_pages"
    ] = total_pages

    current_page = int(
        st.session_state.get(
            "explorer_current_page",
            1,
        )
    )

    current_page = max(
        1,
        min(
            current_page,
            total_pages,
        ),
    )

    st.session_state[
        "explorer_current_page"
    ] = current_page

    with navigation_columns[1]:

        st.write("")

        st.button(
            "⬅️ Previous",
            use_container_width=True,
            disabled=(
                current_page <= 1
            ),
            on_click=(
                _previous_page
            ),
            key=(
                "explorer_previous_page"
            ),
        )

    with navigation_columns[2]:

        st.metric(
            "Current Page",
            (
                f"{current_page:,} "
                f"of {total_pages:,}"
            ),
        )

    with navigation_columns[3]:

        st.write("")

        st.button(
            "Next ➡️",
            use_container_width=True,
            disabled=(
                current_page
                >= total_pages
            ),
            on_click=(
                _next_page
            ),
            key=(
                "explorer_next_page"
            ),
        )

    with navigation_columns[4]:

        st.metric(
            "Total Records",
            f"{total_result_rows:,}",
        )

    # --------------------------------------------------------
    # CURRENT PAGE RANGE
    # --------------------------------------------------------

    start_row = (
        (current_page - 1)
        * rows_per_page
    )

    end_row = min(
        start_row
        + rows_per_page,
        total_result_rows,
    )

    if total_result_rows == 0:

        st.info(
            "No records match the current Explorer filters "
            "and search criteria."
        )

    else:

        st.markdown(
            f"**Showing records "
            f"{start_row + 1:,}–{end_row:,} "
            f"of {total_result_rows:,}**"
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # Slice first, then prepare display data.
        # Only the current page is converted/formatted.
        # ----------------------------------------------------

        page_df = (
            explorer_df
            .iloc[
                start_row:end_row
            ][
                selected_columns
            ]
            .copy()
        )

        page_df = (
            _prepare_display_data(
                page_df
            )
        )

        st.dataframe(
            page_df,
            use_container_width=True,
            hide_index=True,
            height=550,
        )

        if total_pages > 1:

            st.caption(
                "Use Previous / Next above the table "
                "to view additional records."
            )


    # ========================================================
    # 8. EXPORT DATA
    # ========================================================

    st.divider()

    st.markdown(
        "### 8. 📦 Export Data"
    )

    st.markdown(
        f"**Current Explorer result:** "
        f"{len(explorer_df):,} records"
    )

    complete_export_df = (
        explorer_df.copy()
    )

    selected_export_df = (
        explorer_df[
            selected_columns
        ]
        .copy()
    )

    summary_items = []

    if (
        "Reporting Date"
        in complete_export_df.columns
    ):

        dates = pd.to_datetime(
            complete_export_df[
                "Reporting Date"
            ],
            errors="coerce",
        ).dropna()

        if not dates.empty:

            summary_items.append(
                {
                    "Indicator": (
                        "Reporting Period"
                    ),
                    "Value": (
                        f"{dates.min().strftime('%d-%m-%Y')} "
                        f"to "
                        f"{dates.max().strftime('%d-%m-%Y')}"
                    ),
                }
            )

    summary_items.extend(
        [
            {
                "Indicator": (
                    "Global Filter Records"
                ),
                "Value": (
                    f"{len(base_df):,}"
                ),
            },
            {
                "Indicator": (
                    "Explorer Result Records"
                ),
                "Value": (
                    f"{len(explorer_df):,}"
                ),
            },
            {
                "Indicator": (
                    "Diseases"
                ),
                "Value": (
                    f"{_safe_unique_count(explorer_df, 'Disease'):,}"
                ),
            },
            {
                "Indicator": (
                    "Facilities"
                ),
                "Value": (
                    f"{_safe_unique_count(explorer_df, 'Facility Name'):,}"
                ),
            },
            {
                "Indicator": (
                    "Wards"
                ),
                "Value": (
                    f"{_safe_unique_count(explorer_df, 'Ward Name'):,}"
                ),
            },
            {
                "Indicator": (
                    "Selected Columns"
                ),
                "Value": (
                    f"{len(selected_columns):,}"
                ),
            },
            {
                "Indicator": (
                    "Search Text"
                ),
                "Value": (
                    search_text.strip()
                    if search_text.strip()
                    else "None"
                ),
            },
        ]
    )

    for (
        column,
        selected_values,
    ) in (
        explorer_filter_values.items()
    ):

        if selected_values:

            summary_items.append(
                {
                    "Indicator": (
                        f"Explorer Filter - "
                        f"{column}"
                    ),
                    "Value": ", ".join(
                        map(
                            str,
                            selected_values,
                        )
                    ),
                }
            )

    export_summary_df = (
        pd.DataFrame(
            summary_items
        )
    )

    # --------------------------------------------------------
    # CSV files are relatively inexpensive.
    # --------------------------------------------------------

    csv_data = (
        complete_export_df
        .to_csv(
            index=False
        )
        .encode(
            "utf-8-sig"
        )
    )

    selected_csv = (
        selected_export_df
        .to_csv(
            index=False
        )
        .encode(
            "utf-8-sig"
        )
    )

    # --------------------------------------------------------
    # Data quality calculations.
    # --------------------------------------------------------

    export_quality_df = (
        _create_quality_dataframe(
            complete_export_df
        )
    )

    selected_quality_df = (
        _create_quality_dataframe(
            selected_export_df
        )
    )

    # --------------------------------------------------------
    # Excel generation is cached.
    # Once created for the same data, page navigation does
    # not need to rebuild the workbook.
    # --------------------------------------------------------

    excel_data = (
        _create_excel_bytes(
            complete_export_df,
            export_quality_df,
            export_summary_df,
        )
    )

    selected_excel = (
        _create_excel_bytes(
            selected_export_df,
            selected_quality_df,
            export_summary_df,
        )
    )

    download_columns = (
        st.columns(4)
    )

    with download_columns[0]:

        st.download_button(
            label="⬇️ Complete CSV",
            data=csv_data,
            file_name=(
                "health_programme_"
                "filtered_data.csv"
            ),
            mime="text/csv",
            use_container_width=True,
            key=(
                "explorer_download_csv"
            ),
        )

    with download_columns[1]:

        st.download_button(
            label="📊 Complete Excel",
            data=excel_data,
            file_name=(
                "health_programme_"
                "filtered_data.xlsx"
            ),
            mime=(
                "application/vnd."
                "openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
            key=(
                "explorer_download_excel"
            ),
        )

    with download_columns[2]:

        st.download_button(
            label="📥 Selected CSV",
            data=selected_csv,
            file_name=(
                "health_programme_"
                "selected_columns.csv"
            ),
            mime="text/csv",
            use_container_width=True,
            key=(
                "explorer_download_selected_csv"
            ),
        )

    with download_columns[3]:

        st.download_button(
            label="📗 Selected Excel",
            data=selected_excel,
            file_name=(
                "health_programme_"
                "selected_columns.xlsx"
            ),
            mime=(
                "application/vnd."
                "openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
            key=(
                "explorer_download_selected_excel"
            ),
        )

    st.caption(
        "Excel exports contain Filtered Data, Data Quality "
        "and Export Summary worksheets."
    )


    # ========================================================
    # 9. COLUMN-WISE DATA QUALITY
    # ========================================================

    st.divider()

    st.markdown(
        "### 9. 🧪 Column-wise Data Quality"
    )

    st.caption(
        "Missing values include actual null values, blank cells "
        "and common text-null values such as nan, NaT, None, "
        "null and <NA>."
    )

    quality_df = (
        export_quality_df.copy()
    )

    if quality_df.empty:

        st.info(
            "No records are available for "
            "data quality analysis."
        )

    else:

        quality_display = (
            quality_df.copy()
        )

        quality_display[
            "Missing %"
        ] = (
            quality_display[
                "Missing %"
            ]
            .map(
                lambda value:
                f"{value:.2f}%"
            )
        )

        st.dataframe(
            quality_display,
            use_container_width=True,
            hide_index=True,
        )


    # ========================================================
    # 10. CURRENT DATA SCOPE
    # ========================================================

    st.divider()

    st.markdown(
        "### 10. ℹ️ Current Data Scope"
    )

    scope_items = []

    if (
        "Reporting Date"
        in base_df.columns
    ):

        dates = pd.to_datetime(
            base_df[
                "Reporting Date"
            ],
            errors="coerce",
        ).dropna()

        if not dates.empty:

            scope_items.append(
                {
                    "Indicator": (
                        "Global Filter "
                        "Reporting Period"
                    ),
                    "Value": (
                        f"{dates.min().strftime('%d-%m-%Y')} "
                        f"to "
                        f"{dates.max().strftime('%d-%m-%Y')}"
                    ),
                }
            )

    if (
        "Reporting Date"
        in explorer_df.columns
    ):

        result_dates = pd.to_datetime(
            explorer_df[
                "Reporting Date"
            ],
            errors="coerce",
        ).dropna()

        if not result_dates.empty:

            scope_items.append(
                {
                    "Indicator": (
                        "Explorer Result "
                        "Reporting Period"
                    ),
                    "Value": (
                        f"{result_dates.min().strftime('%d-%m-%Y')} "
                        f"to "
                        f"{result_dates.max().strftime('%d-%m-%Y')}"
                    ),
                }
            )

    scope_items.extend(
        [
            {
                "Indicator": (
                    "Global Filter Records"
                ),
                "Value": (
                    f"{len(base_df):,}"
                ),
            },
            {
                "Indicator": (
                    "Explorer Result Records"
                ),
                "Value": (
                    f"{len(explorer_df):,}"
                ),
            },
            {
                "Indicator": (
                    "Active Explorer Filters"
                ),
                "Value": (
                    f"{active_filter_count:,}"
                ),
            },
            {
                "Indicator": (
                    "Search Applied"
                ),
                "Value": (
                    "Yes"
                    if search_text.strip()
                    else "No"
                ),
            },
            {
                "Indicator": (
                    "Displayed Columns"
                ),
                "Value": (
                    f"{len(selected_columns):,}"
                ),
            },
            {
                "Indicator": (
                    "Rows per Page"
                ),
                "Value": (
                    f"{rows_per_page:,}"
                ),
            },
            {
                "Indicator": (
                    "Current Page"
                ),
                "Value": (
                    f"{current_page:,} "
                    f"of {total_pages:,}"
                ),
            },
        ]
    )

    scope_df = (
        pd.DataFrame(
            scope_items
        )
    )

    st.dataframe(
        scope_df,
        use_container_width=True,
        hide_index=True,
    )
