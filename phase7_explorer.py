import pandas as pd
import streamlit as st

from phase2_overview import apply_filters, create_filters


# ============================================================
# PAGE CONFIGURATION / HELPERS
# ============================================================

def _clean_dataframe(df):
    """
    Creates a safe copy of the dataframe for exploration.
    """

    if df is None:
        return pd.DataFrame()

    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame()

    clean_df = df.copy()

    # Remove completely empty rows
    clean_df = clean_df.dropna(
        how="all"
    ).reset_index(drop=True)

    return clean_df


def _search_dataframe(df, search_text):
    """
    Performs a global text search across all columns.
    """

    if not search_text:
        return df

    search_text = str(search_text).strip()

    if not search_text:
        return df

    mask = pd.Series(
        False,
        index=df.index
    )

    for col in df.columns:

        try:

            mask = (
                mask
                |
                df[col]
                .astype(str)
                .str.contains(
                    search_text,
                    case=False,
                    na=False,
                    regex=False
                )
            )

        except Exception:
            continue

    return df.loc[mask].copy()


def _format_dataframe_for_display(df):
    """
    Makes a display-safe copy without changing
    the original dataset.
    """

    display_df = df.copy()

    for col in display_df.columns:

        # Convert datetime columns to readable strings
        if pd.api.types.is_datetime64_any_dtype(
            display_df[col]
        ):

            display_df[col] = (
                display_df[col]
                .dt.strftime("%d-%m-%Y")
            )

    return display_df


# ============================================================
# SUMMARY METRICS
# ============================================================

def _show_summary(df):

    total_records = len(df)

    total_columns = len(df.columns)

    missing_values = int(
        df.isna().sum().sum()
    )

    duplicate_rows = int(
        df.duplicated().sum()
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Records",
        f"{total_records:,}"
    )

    c2.metric(
        "Columns",
        f"{total_columns:,}"
    )

    c3.metric(
        "Missing Values",
        f"{missing_values:,}"
    )

    c4.metric(
        "Duplicate Rows",
        f"{duplicate_rows:,}"
    )


# ============================================================
# QUICK MANAGEMENT SUMMARY
# ============================================================

def _management_summary(df):

    st.subheader(
        "📊 Explorer Management Summary"
    )

    summary_items = []

    # --------------------------------------------------------
    # Total cases
    # --------------------------------------------------------

    summary_items.append(
        {
            "Indicator": "Total Records / Cases",
            "Value": len(df)
        }
    )

    # --------------------------------------------------------
    # Wards
    # --------------------------------------------------------

    if "Ward" in df.columns:

        summary_items.append(
            {
                "Indicator": "Wards Covered",
                "Value": df["Ward"].nunique(
                    dropna=True
                )
            }
        )

        ward_counts = (
            df["Ward"]
            .dropna()
            .value_counts()
        )

        if not ward_counts.empty:

            summary_items.append(
                {
                    "Indicator": "Top Burden Ward",
                    "Value": ward_counts.index[0]
                }
            )

            summary_items.append(
                {
                    "Indicator": "Top Ward Cases",
                    "Value": int(
                        ward_counts.iloc[0]
                    )
                }
            )

    # --------------------------------------------------------
    # Facilities
    # --------------------------------------------------------

    if "Facility Name Lform" in df.columns:

        summary_items.append(
            {
                "Indicator": "Facilities Covered",
                "Value": df[
                    "Facility Name Lform"
                ].nunique(
                    dropna=True
                )
            }
        )

        facility_counts = (
            df["Facility Name Lform"]
            .dropna()
            .value_counts()
        )

        if not facility_counts.empty:

            summary_items.append(
                {
                    "Indicator": "Top Facility",
                    "Value": facility_counts.index[0]
                }
            )

            summary_items.append(
                {
                    "Indicator": "Top Facility Cases",
                    "Value": int(
                        facility_counts.iloc[0]
                    )
                }
            )

    # --------------------------------------------------------
    # Gender
    # --------------------------------------------------------

    if "Gender" in df.columns:

        summary_items.append(
            {
                "Indicator": "Gender Categories",
                "Value": df["Gender"].nunique(
                    dropna=True
                )
            }
        )

    # --------------------------------------------------------
    # Disease
    # --------------------------------------------------------

    if "Confirmed Diagnosis" in df.columns:

        summary_items.append(
            {
                "Indicator": "Disease Categories",
                "Value": df[
                    "Confirmed Diagnosis"
                ].nunique(
                    dropna=True
                )
            }
        )

    summary_df = pd.DataFrame(
        summary_items
    )

    if not summary_df.empty:

        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True
        )


# ============================================================
# COLUMN-WISE DATA QUALITY
# ============================================================

def _data_quality_table(df):

    quality = pd.DataFrame(
        {
            "Column": df.columns,
            "Data Type": [
                str(dtype)
                for dtype in df.dtypes
            ],
            "Records": [
                len(df)
                for _ in df.columns
            ],
            "Non-Null": [
                int(df[col].notna().sum())
                for col in df.columns
            ],
            "Missing": [
                int(df[col].isna().sum())
                for col in df.columns
            ],
            "Missing (%)": [
                round(
                    df[col].isna().mean() * 100,
                    2
                )
                for col in df.columns
            ],
            "Unique Values": [
                int(df[col].nunique(
                    dropna=True
                ))
                for col in df.columns
            ]
        }
    )

    quality["Completeness (%)"] = (
        100 - quality["Missing (%)"]
    ).round(2)

    quality = quality.sort_values(
        "Missing (%)",
        ascending=False
    ).reset_index(drop=True)

    return quality


# ============================================================
# CATEGORY ANALYSIS
# ============================================================

def _category_analysis(df, column):

    if column not in df.columns:
        return

    analysis_df = df[column].copy()

    analysis_df = (
        analysis_df
        .dropna()
        .astype(str)
        .str.strip()
    )

    if analysis_df.empty:

        st.info(
            f"No usable data available for {column}."
        )

        return

    counts = (
        analysis_df
        .value_counts()
        .rename_axis(column)
        .reset_index(name="Cases")
    )

    counts["Share (%)"] = (
        counts["Cases"]
        / counts["Cases"].sum()
        * 100
    ).round(2)

    counts.insert(
        0,
        "Rank",
        range(
            1,
            len(counts) + 1
        )
    )

    st.dataframe(
        counts,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# MAIN EXPLORER FUNCTION
# ============================================================

def render_explorer(df):

    st.title(
        "🔎 Interactive Data Explorer"
    )

    st.caption(
        "Search, filter, inspect and download "
        "the underlying programme data."
    )

    # --------------------------------------------------------
    # DATA CHECK
    # --------------------------------------------------------

    df = _clean_dataframe(df)

    if df.empty:

        st.warning(
            "No data available for exploration."
        )

        return

    # --------------------------------------------------------
    # APPLY GLOBAL FILTERS
    # --------------------------------------------------------

    try:

        filters = create_filters(df)

        filtered_df = apply_filters(
            df,
            **filters
        )

    except Exception:

        filtered_df = df.copy()

    if filtered_df.empty:

        st.warning(
            "No records match the selected filters."
        )

        return

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    _show_summary(
        filtered_df
    )

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📋 Data Explorer",
            "📊 Quick Analysis",
            "🔍 Data Quality",
            "⬇️ Download"
        ]
    )

    # ========================================================
    # TAB 1 — DATA EXPLORER
    # ========================================================

    with tab1:

        st.subheader(
            "📋 Interactive Record Explorer"
        )

        # ----------------------------------------------------
        # GLOBAL SEARCH
        # ----------------------------------------------------

        search_text = st.text_input(
            "🔎 Search across all columns",
            placeholder=(
                "Search facility, ward, diagnosis, "
                "gender, patient ID, etc."
            )
        )

        explorer_df = _search_dataframe(
            filtered_df,
            search_text
        )

        st.caption(
            f"Showing {len(explorer_df):,} "
            f"of {len(filtered_df):,} records"
        )

        # ----------------------------------------------------
        # COLUMN SELECTION
        # ----------------------------------------------------

        all_columns = list(
            explorer_df.columns
        )

        default_columns = all_columns[:]

        selected_columns = st.multiselect(
            "Select columns to display",
            options=all_columns,
            default=default_columns
        )

        if not selected_columns:

            st.warning(
                "Please select at least one column."
            )

            return

        display_df = explorer_df[
            selected_columns
        ].copy()

        # ----------------------------------------------------
        # SORTING
        # ----------------------------------------------------

        sort_col = st.selectbox(
            "Sort by column",
            options=[
                "No sorting"
            ] + selected_columns
        )

        if sort_col != "No sorting":

            sort_order = st.radio(
                "Sort order",
                [
                    "Descending",
                    "Ascending"
                ],
                horizontal=True
            )

            display_df = display_df.sort_values(
                by=sort_col,
                ascending=(
                    sort_order == "Ascending"
                ),
                na_position="last"
            )

        # ----------------------------------------------------
        # RECORD LIMIT
        # ----------------------------------------------------

        max_rows = len(display_df)

        if max_rows > 5000:

            display_limit = st.number_input(
                "Maximum records to display",
                min_value=100,
                max_value=max_rows,
                value=1000,
                step=100
            )

        else:

            display_limit = max_rows

        display_df = display_df.head(
            int(display_limit)
        )

        display_df = _format_dataframe_for_display(
            display_df
        )

        # ----------------------------------------------------
        # DATA TABLE
        # ----------------------------------------------------

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=600
        )

    # ========================================================
    # TAB 2 — QUICK ANALYSIS
    # ========================================================

    with tab2:

        _management_summary(
            filtered_df
        )

        st.divider()

        st.subheader(
            "📊 Category-wise Analysis"
        )

        categorical_columns = [
            col
            for col in filtered_df.columns
            if (
                filtered_df[col].dtype == "object"
                or
                str(
                    filtered_df[col].dtype
                ).startswith("category")
            )
        ]

        if categorical_columns:

            selected_category = st.selectbox(
                "Select a variable",
                categorical_columns
            )

            _category_analysis(
                filtered_df,
                selected_category
            )

        else:

            st.info(
                "No categorical variables are available."
            )

        # ----------------------------------------------------
        # COMMON PROGRAMME VARIABLES
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            "🎯 Programme Variables"
        )

        programme_columns = [
            col
            for col in [
                "Ward",
                "Facility Name Lform",
                "Gender",
                "Confirmed Diagnosis",
                "Month",
                "Age",
                "Age Group"
            ]
            if col in filtered_df.columns
        ]

        if programme_columns:

            selected_programme_variable = st.selectbox(
                "Select programme variable",
                programme_columns,
                key="programme_variable"
            )

            _category_analysis(
                filtered_df,
                selected_programme_variable
            )

    # ========================================================
    # TAB 3 — DATA QUALITY
    # ========================================================

    with tab3:

        st.subheader(
            "🔍 Data Quality Assessment"
        )

        quality_df = _data_quality_table(
            filtered_df
        )

        st.dataframe(
            quality_df,
            use_container_width=True,
            hide_index=True
        )

        # ----------------------------------------------------
        # MISSING DATA WARNING
        # ----------------------------------------------------

        high_missing = quality_df[
            quality_df["Missing (%)"] >= 20
        ]

        if not high_missing.empty:

            st.warning(
                f"{len(high_missing)} column(s) have "
                "20% or more missing data."
            )

        # ----------------------------------------------------
        # DUPLICATES
        # ----------------------------------------------------

        duplicate_count = int(
            filtered_df.duplicated().sum()
        )

        st.metric(
            "Duplicate Records",
            f"{duplicate_count:,}"
        )

        # ----------------------------------------------------
        # COMPLETELY EMPTY COLUMNS
        # ----------------------------------------------------

        empty_columns = [
            col
            for col in filtered_df.columns
            if filtered_df[col].notna().sum() == 0
        ]

        if empty_columns:

            st.warning(
                "Completely empty columns detected:"
            )

            st.write(
                empty_columns
            )

    # ========================================================
    # TAB 4 — DOWNLOAD
    # ========================================================

    with tab4:

        st.subheader(
            "⬇️ Download Filtered Data"
        )

        download_df = _format_dataframe_for_display(
            filtered_df
        )

        csv_data = download_df.to_csv(
            index=False
        ).encode(
            "utf-8-sig"
        )

        st.download_button(
            label="⬇️ Download Filtered CSV",
            data=csv_data,
            file_name="filtered_management_data.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.caption(
            "The downloaded file contains the records "
            "after applying the selected dashboard filters."
        )


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================
# Supports different names from app.py.

def render_explorer_analysis(df):
    return render_explorer(df)


def render_data_explorer(df):
    return render_explorer(df)
