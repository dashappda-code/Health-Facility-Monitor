import streamlit as st

from phase2_overview import (
    apply_filters,
    create_filters,
)


# ============================================================
# DATA EXPLORER
# ============================================================

def render_explorer(df):

    filters = create_filters(df)

    filtered_df = apply_filters(
        df,
        **filters,
    )

    st.title(
        "🔎 Data Explorer"
    )

    st.caption(
        "Search, inspect and export filtered records"
    )

    # ========================================================
    # SEARCH
    # ========================================================

    search_text = st.text_input(
        "Search records",
        placeholder=(
            "Search disease, ward, facility, "
            "patient address, pathogen..."
        ),
    )

    display_df = filtered_df.copy()

    if search_text.strip():

        search_value = (
            search_text
            .strip()
            .lower()
        )

        text_columns = (
            display_df
            .select_dtypes(
                include="object"
            )
            .columns
        )

        if len(text_columns) > 0:

            search_mask = (
                display_df[
                    text_columns
                ]
                .fillna("")
                .astype(str)
                .apply(
                    lambda column:
                    column.str.lower()
                    .str.contains(
                        search_value,
                        regex=False,
                    )
                )
                .any(axis=1)
            )

            display_df = display_df[
                search_mask
            ]

    # ========================================================
    # RECORD COUNT
    # ========================================================

    st.info(
        f"{len(display_df):,} records found"
    )

    # ========================================================
    # DATA TABLE
    # ========================================================

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=600,
    )

    # ========================================================
    # CSV DOWNLOAD
    # ========================================================

    csv_data = display_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="⬇️ Download CSV",
        data=csv_data,
        file_name="health_facility_filtered_data.csv",
        mime="text/csv",
        use_container_width=False,
    )

    # ========================================================
    # DATA QUALITY
    # ========================================================

    with st.expander(
        "Data Quality Summary"
    ):

        quality = (
            display_df
            .isna()
            .sum()
            .reset_index()
        )

        quality.columns = [
            "Column",
            "Missing Values",
        ]

        quality["Missing %"] = (
            quality["Missing Values"]
            / max(len(display_df), 1)
            * 100
        ).round(2)

        st.dataframe(
            quality,
            use_container_width=True,
            hide_index=True,
        )
