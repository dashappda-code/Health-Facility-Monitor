import io

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

DEFAULT_ROWS_PER_PAGE = 100

ROWS_PER_PAGE_OPTIONS = [
    50,
    100,
    250,
    500,
    1000,
]


# ============================================================
# COMMON HELPERS
# ============================================================

def _clean_text(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


def _is_missing_series(series):
    """
    Treat actual null values and common blank/text-null values
    as missing.
    """

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
    """
    Return valid unique text values from a Series.
    """

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
        ~values.isin(invalid_values)
    ]

    return sorted(
        values.drop_duplicates().tolist(),
        key=lambda value: str(value).upper(),
    )


def _prepare_display_data(df):
    if df is None or df.empty:
        return pd.DataFrame()

    display_df = df.copy()

    for column in display_df.columns:

        if pd.api.types.is_datetime64_any_dtype(
            display_df[column]
        ):

            display_df[column] = (
                display_df[column]
                .dt.strftime("%d-%m-%Y")
            )

    return display_df


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

    values = _valid_values(
        df[column]
    )

    return len(values)


# ============================================================
# COLUMN MULTI-SELECTION
# ============================================================

def _column_selector(
    all_columns,
    default_columns,
):
    """
    Column selector with:
    - Select All
    - individual column selection
    - default important columns
    """

    all_columns = list(all_columns)

    if not all_columns:
        return []

    select_all_key = (
        "explorer_columns_select_all"
    )

    initialized_key = (
        "explorer_columns_initialized"
    )

    option_keys = {
        column: (
            f"explorer_column_{index}"
        )
        for index, column in enumerate(
            all_columns
        )
    }

    if initialized_key not in st.session_state:

        st.session_state[
            initialized_key
        ] = True

        default_set = set(
            default_columns
        )

        all_default = (
            len(default_set)
            == len(all_columns)
        )

        st.session_state[
            select_all_key
        ] = all_default

        for column in all_columns:

            st.session_state[
                option_keys[column]
            ] = (
                column in default_set
            )

    def select_all_changed():

        selected = bool(
            st.session_state.get(
                select_all_key,
                False,
            )
        )

        for column in all_columns:

            st.session_state[
                option_keys[column]
            ] = selected

    def individual_changed():

        all_selected = all(
            bool(
                st.session_state.get(
                    option_keys[column],
                    False,
                )
            )
            for column in all_columns
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
            on_change=select_all_changed,
        )

        st.divider()

        for column in all_columns:

            checked = st.checkbox(
                column,
                key=option_keys[column],
                on_change=individual_changed,
            )

            if checked:
                selected_columns.append(
                    column
                )

    return selected_columns


# ============================================================
# DATA QUALITY
# ============================================================

def _create_quality_dataframe(df):

    quality_rows = []

    if df is None:
        return pd.DataFrame()

    for column in df.columns:

        series = df[column]

        total = len(series)

        missing_mask = (
            _is_missing_series(
                series
            )
        )

        missing = int(
            missing_mask.sum()
        )

        valid = (
            total
            - missing
        )

        if total > 0:

            missing_percent = (
                missing
                / total
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
                "Records": total,
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

        # ----------------------------------------------------
        # SHEET 1 - FILTERED DATA
        # ----------------------------------------------------

        data_df.to_excel(
            writer,
            index=False,
            sheet_name="Filtered Data",
        )

        # ----------------------------------------------------
        # SHEET 2 - DATA QUALITY
        # ----------------------------------------------------

        quality_df.to_excel(
            writer,
            index=False,
            sheet_name="Data Quality",
        )

        # ----------------------------------------------------
        # SHEET 3 - EXPORT SUMMARY
        # ----------------------------------------------------

        summary_df.to_excel(
            writer,
            index=False,
            sheet_name="Export Summary",
        )

        # ----------------------------------------------------
        # BASIC COLUMN WIDTH FORMATTING
        # ----------------------------------------------------

        workbook = writer.book

        for sheet_name in [
            "Filtered Data",
            "Data Quality",
            "Export Summary",
        ]:

            worksheet = workbook[
                sheet_name
            ]

            for column_cells in (
                worksheet.columns
            ):

                max_length = 0

                column_letter = (
                    column_cells[0]
                    .column_letter
                )

                for cell in column_cells:

                    try:

                        cell_length = len(
                            str(
                                cell.value
                                if cell.value
                                is not None
                                else ""
                            )
                        )

                        max_length = max(
                            max_length,
                            cell_length,
                        )

                    except Exception:
                        pass

                adjusted_width = min(
                    max(
                        max_length + 2,
                        10,
                    ),
                    45,
                )

                worksheet.column_dimensions[
                    column_letter
                ].width = (
                    adjusted_width
                )

            worksheet.freeze_panes = (
                "A2"
            )

            worksheet.auto_filter.ref = (
                worksheet.dimensions
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
        or column not in dataframe.columns
        or not selected_values
    ):
        return dataframe

    values = (
        dataframe[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    return dataframe[
        values.isin(
            selected_values
        )
    ].copy()


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

    # Keep original globally filtered dataset.
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

    missing_cells = 0

    for column in base_df.columns:

        missing_cells += int(
            _is_missing_series(
                base_df[column]
            ).sum()
        )

    total_cells = (
        total_records
        * total_columns
    )

    if total_cells > 0:

        missing_percentage = (
            missing_cells
            / total_cells
            * 100
        )

    else:

        missing_percentage = 0

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

    c1, c2, c3 = (
        st.columns(3)
    )

    with c1:

        st.metric(
            "Columns",
            f"{total_columns:,}",
        )

    with c2:

        st.metric(
            "Missing Cells",
            f"{missing_cells:,}",
        )

    with c3:

        st.metric(
            "Missing %",
            f"{missing_percentage:.2f}%",
        )


    # ========================================================
    # 2. EXPLORER FILTERS
    # ========================================================

    st.divider()

    st.markdown(
        "### 2. 🎛️ Explorer Filters"
    )

    st.caption(
        "These filters apply only to the Data Explorer and do "
        "not change the Global Dashboard Filters."
    )

    explorer_df = (
        base_df.copy()
    )

    available_filter_columns = [
        column
        for column in EXPLORER_FILTER_COLUMNS
        if column in base_df.columns
    ]

    explorer_filter_values = {}

    if available_filter_columns:

        filter_columns = (
            st.columns(3)
        )

        for index, column in enumerate(
            available_filter_columns
        ):

            options = _valid_values(
                base_df[column]
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
                    )
                )

            explorer_filter_values[
                column
            ] = selected_values

        for column, selected_values in (
            explorer_filter_values.items()
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
            "No standard Explorer filter columns are available "
            "in the current dataset."
        )

    active_filter_count = sum(
        1
        for values in (
            explorer_filter_values.values()
        )
        if values
    )

    if active_filter_count > 0:

        st.markdown(
            f"**Explorer filters active:** "
            f"{active_filter_count} | "
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
        )
    )

    if search_text.strip():

        search_value = (
            search_text
            .strip()
            .lower()
        )

        text_df = (
            explorer_df
            .fillna("")
            .astype(str)
        )

        row_mask = (
            text_df
            .apply(
                lambda column:
                column
                .str.lower()
                .str.contains(
                    search_value,
                    regex=False,
                    na=False,
                )
            )
            .any(
                axis=1
            )
        )

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
            "Enter text above to search across all available columns."
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
        base_df.columns.tolist()
    )

    default_columns = [
        column
        for column in DEFAULT_DISPLAY_COLUMNS
        if column in all_columns
    ]

    if not default_columns:

        default_columns = (
            all_columns[:15]
        )

    selected_columns = (
        _column_selector(
            all_columns=all_columns,
            default_columns=default_columns,
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
                options=selected_columns,
                key=(
                    "explorer_sort_column"
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
            )
        )

    if (
        sort_column
        in explorer_df.columns
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
    # 7. DISPLAY OPTIONS / PAGINATION
    # ========================================================

    st.divider()

    st.markdown(
        "### 7. 📄 Display Options"
    )

    display_columns = (
        st.columns(
            [2, 2, 2, 2],
            gap="medium",
        )
    )

    with display_columns[0]:

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
                    "explorer_rows_"
                    "per_page"
                ),
            )
        )

    total_result_rows = len(
        explorer_df
    )

    if total_result_rows == 0:

        total_pages = 1

    else:

        total_pages = (
            total_result_rows
            + rows_per_page
            - 1
        ) // rows_per_page

    with display_columns[1]:

        page_number = (
            st.number_input(
                "Page",
                min_value=1,
                max_value=max(
                    total_pages,
                    1,
                ),
                value=1,
                step=1,
                key="explorer_page",
            )
        )

    page_number = int(
        min(
            page_number,
            total_pages,
        )
    )

    start_row = (
        (page_number - 1)
        * rows_per_page
    )

    end_row = min(
        start_row
        + rows_per_page,
        total_result_rows,
    )

    with display_columns[2]:

        st.metric(
            "Search Results",
            f"{total_result_rows:,}",
        )

    with display_columns[3]:

        if total_result_rows > 0:

            displayed_count = (
                end_row
                - start_row
            )

        else:

            displayed_count = 0

        st.metric(
            "Rows Displayed",
            f"{displayed_count:,}",
        )

    st.caption(
        f"Page {page_number:,} of "
        f"{total_pages:,}"
    )


    # ========================================================
    # 8. RECORD-LEVEL DATA
    # ========================================================

    st.divider()

    st.markdown(
        "### 8. 📋 Record-level Data"
    )

    if explorer_df.empty:

        st.info(
            "No records match the current Explorer filters "
            "and search criteria."
        )

    else:

        table_df = (
            explorer_df[
                selected_columns
            ]
            .iloc[
                start_row:end_row
            ]
            .copy()
        )

        table_df = (
            _prepare_display_data(
                table_df
            )
        )

        st.dataframe(
            table_df,
            use_container_width=True,
            hide_index=True,
            height=550,
        )

        st.caption(
            f"Displaying records "
            f"{start_row + 1:,} to "
            f"{end_row:,} of "
            f"{total_result_rows:,}."
        )


    # ========================================================
    # 9. EXPORT DATA
    # ========================================================

    st.divider()

    st.markdown(
        "### 9. 📦 Export Data"
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

    # --------------------------------------------------------
    # EXPORT SUMMARY
    # --------------------------------------------------------

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

    for column, selected_values in (
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

    export_quality_df = (
        _create_quality_dataframe(
            complete_export_df
        )
    )

    # --------------------------------------------------------
    # CSV
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

    # --------------------------------------------------------
    # EXCEL
    # --------------------------------------------------------

    excel_data = (
        _create_excel_bytes(
            data_df=(
                complete_export_df
            ),
            quality_df=(
                export_quality_df
            ),
            summary_df=(
                export_summary_df
            ),
        )
    )

    # --------------------------------------------------------
    # SELECTED COLUMN CSV
    # --------------------------------------------------------

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
    # SELECTED COLUMN EXCEL
    # --------------------------------------------------------

    selected_quality_df = (
        _create_quality_dataframe(
            selected_export_df
        )
    )

    selected_excel = (
        _create_excel_bytes(
            data_df=(
                selected_export_df
            ),
            quality_df=(
                selected_quality_df
            ),
            summary_df=(
                export_summary_df
            ),
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
                "explorer_download_"
                "selected_csv"
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
                "explorer_download_"
                "selected_excel"
            ),
        )

    st.caption(
        "Excel exports contain Filtered Data, Data Quality "
        "and Export Summary worksheets."
    )


    # ========================================================
    # 10. COLUMN-WISE DATA QUALITY
    # ========================================================

    st.divider()

    st.markdown(
        "### 10. 🧪 Column-wise Data Quality"
    )

    st.caption(
        "Missing values include actual null values, blank cells "
        "and common text-null values such as nan, NaT, None and null."
    )

    quality_df = (
        _create_quality_dataframe(
            explorer_df
        )
    )

    if quality_df.empty:

        st.info(
            "No records are available for data quality analysis."
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
    # 11. CURRENT DATA SCOPE
    # ========================================================

    st.divider()

    st.markdown(
        "### 11. ℹ️ Current Data Scope"
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
                    "Current Page"
                ),
                "Value": (
                    f"{page_number:,} of "
                    f"{total_pages:,}"
                ),
            },
        ]
    )

    scope_df = pd.DataFrame(
        scope_items
    )

    st.dataframe(
        scope_df,
        use_container_width=True,
        hide_index=True,
    )
