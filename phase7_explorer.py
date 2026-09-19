import io

import streamlit as st
import pandas as pd


def _clean_text(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


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


def _create_excel_bytes(df):
    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="Filtered Data",
        )

    output.seek(0)

    return output.getvalue()


def render_explorer(df):

    st.subheader("🔎 Data Explorer")

    if df is None or df.empty:
        st.warning(
            "No records available for the selected filters."
        )
        return

    st.caption(
        "Explore, search, sort and export records "
        "after applying the Global Dashboard Filters."
    )

    # =========================================================
    # 1. DATA SUMMARY
    # =========================================================

    st.markdown("### 📊 Explorer Summary")

    total_records = len(df)
    total_columns = len(df.columns)

    missing_cells = int(
        df.isna().sum().sum()
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

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Filtered Records",
            f"{total_records:,}",
        )

    with c2:
        st.metric(
            "Columns",
            f"{total_columns:,}",
        )

    with c3:
        st.metric(
            "Missing Cells",
            f"{missing_cells:,}",
        )

    with c4:
        st.metric(
            "Missing %",
            f"{missing_percentage:.2f}%",
        )

    # =========================================================
    # 2. SEARCH
    # =========================================================

    st.divider()

    st.markdown("### 🔍 Search Records")

    search_text = st.text_input(
        "Search across all columns",
        placeholder=(
            "Enter disease, facility, ward, gender, "
            "patient address, diagnosis, etc."
        ),
        key="explorer_search",
    )

    explorer_df = df.copy()

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
                column.str.lower()
                .str.contains(
                    search_value,
                    regex=False,
                    na=False,
                )
            )
            .any(axis=1)
        )

        explorer_df = explorer_df[
            row_mask
        ].copy()

    # =========================================================
    # 3. SEARCH RESULT
    # =========================================================

    if search_text.strip():

        st.info(
            f"Search results: "
            f"**{len(explorer_df):,}** records."
        )

    # =========================================================
    # 4. COLUMN SELECTION
    # =========================================================

    st.divider()

    st.markdown("### 🧩 Select Columns")

    all_columns = df.columns.tolist()

    default_columns = [
        column
        for column in [
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
        if column in all_columns
    ]

    if not default_columns:
        default_columns = all_columns[:15]

    selected_columns = st.multiselect(
        "Columns to display",
        options=all_columns,
        default=default_columns,
        key="explorer_columns",
    )

    if not selected_columns:
        st.warning(
            "Please select at least one column."
        )
        return

    # =========================================================
    # 5. SORT
    # =========================================================

    st.divider()

    st.markdown("### ↕️ Sort Records")

    sort_columns = st.columns(
        [3, 1],
        gap="medium",
    )

    with sort_columns[0]:

        sort_column = st.selectbox(
            "Sort by",
            options=selected_columns,
            key="explorer_sort_column",
        )

    with sort_columns[1]:

        sort_descending = st.checkbox(
            "Descending",
            value=True,
            key="explorer_sort_descending",
        )

    if sort_column in explorer_df.columns:

        try:

            explorer_df = explorer_df.sort_values(
                by=sort_column,
                ascending=not sort_descending,
                na_position="last",
            )

        except Exception:
            pass

    # =========================================================
    # 6. ROW DISPLAY LIMIT
    # =========================================================

    st.markdown("### 📄 Display Options")

    display_columns = st.columns(
        [2, 2, 2],
        gap="medium",
    )

    with display_columns[0]:

        max_rows = st.number_input(
            "Maximum rows to display",
            min_value=50,
            max_value=10000,
            value=1000,
            step=50,
            key="explorer_max_rows",
        )

    with display_columns[1]:

        st.metric(
            "Available Search Results",
            f"{len(explorer_df):,}",
        )

    with display_columns[2]:

        displayed_count = min(
            len(explorer_df),
            int(max_rows),
        )

        st.metric(
            "Rows Displayed",
            f"{displayed_count:,}",
        )

    # =========================================================
    # 7. DATA TABLE
    # =========================================================

    st.divider()

    st.markdown("### 📋 Record-level Data")

    table_df = explorer_df[
        selected_columns
    ].head(
        int(max_rows)
    ).copy()

    table_df = _prepare_display_data(
        table_df
    )

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        height=550,
    )

    if len(explorer_df) > int(max_rows):

        st.caption(
            f"Only the first {int(max_rows):,} rows are "
            f"displayed. The export section below contains "
            f"the complete filtered dataset."
        )

    # =========================================================
    # 8. COMPLETE FILTERED DATA
    # =========================================================

    st.divider()

    st.markdown("### 📦 Complete Filtered Dataset")

    st.write(
        f"Current Global Filter + Search result contains "
        f"**{len(explorer_df):,} records**."
    )

    complete_export_df = explorer_df.copy()

    # =========================================================
    # 9. CSV EXPORT
    # =========================================================

    csv_data = complete_export_df.to_csv(
        index=False
    ).encode(
        "utf-8-sig"
    )

    csv_columns = st.columns(
        [1, 1, 1],
        gap="medium",
    )

    with csv_columns[0]:

        st.download_button(
            label="⬇️ Download CSV",
            data=csv_data,
            file_name=(
                "health_programme_filtered_data.csv"
            ),
            mime="text/csv",
            use_container_width=True,
            key="explorer_download_csv",
        )

    # =========================================================
    # 10. EXCEL EXPORT
    # =========================================================

    excel_data = _create_excel_bytes(
        complete_export_df
    )

    with csv_columns[1]:

        st.download_button(
            label="📊 Download Excel",
            data=excel_data,
            file_name=(
                "health_programme_filtered_data.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
            key="explorer_download_excel",
        )

    # =========================================================
    # 11. SELECTED COLUMNS EXPORT
    # =========================================================

    selected_export_df = explorer_df[
        selected_columns
    ].copy()

    selected_csv = (
        selected_export_df
        .to_csv(index=False)
        .encode("utf-8-sig")
    )

    with csv_columns[2]:

        st.download_button(
            label="📥 Selected Columns CSV",
            data=selected_csv,
            file_name=(
                "health_programme_selected_columns.csv"
            ),
            mime="text/csv",
            use_container_width=True,
            key="explorer_download_selected_csv",
        )

    # =========================================================
    # 12. COLUMN DATA QUALITY
    # =========================================================

    st.divider()

    st.markdown("### 🧪 Column-wise Data Quality")

    quality_rows = []

    for column in df.columns:

        series = df[column]

        total = len(series)
        missing = int(
            series.isna().sum()
        )

        if total > 0:
            missing_percent = (
                missing
                / total
                * 100
            )
        else:
            missing_percent = 0

        unique_count = int(
            series.nunique(
                dropna=True
            )
        )

        quality_rows.append(
            {
                "Column": column,
                "Data Type": str(
                    series.dtype
                ),
                "Records": total,
                "Missing": missing,
                "Missing %": round(
                    missing_percent,
                    2,
                ),
                "Unique Values": unique_count,
            }
        )

    quality_df = pd.DataFrame(
        quality_rows
    )

    st.dataframe(
        quality_df,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # 13. FILTERED DATA INFORMATION
    # =========================================================

    st.divider()

    st.markdown("### ℹ️ Current Data Scope")

    scope_items = []

    if "Reporting Date" in df.columns:

        dates = pd.to_datetime(
            df["Reporting Date"],
            errors="coerce",
        ).dropna()

        if not dates.empty:

            scope_items.append(
                {
                    "Indicator": "Reporting Period",
                    "Value": (
                        f"{dates.min().strftime('%d-%m-%Y')} "
                        f"to "
                        f"{dates.max().strftime('%d-%m-%Y')}"
                    ),
                }
            )

    scope_items.extend(
        [
            {
                "Indicator": "Filtered Records",
                "Value": f"{len(df):,}",
            },
            {
                "Indicator": "Explorer Search Results",
                "Value": f"{len(explorer_df):,}",
            },
            {
                "Indicator": "Displayed Columns",
                "Value": f"{len(selected_columns):,}",
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
