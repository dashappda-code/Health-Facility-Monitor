import streamlit as st
import pandas as pd


def _clean_text(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="object")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


def _find_column(df, candidates):
    if df is None or df.empty:
        return None

    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    for candidate in candidates:
        key = str(candidate).strip().lower()

        if key in normalized:
            return normalized[key]

    return None


def render_map(df):

    st.subheader("🗺️ Map & Geographic Analysis")

    if df is None or df.empty:
        st.warning(
            "No records available for the selected filters."
        )
        return

    st.caption(
        "Geographic view based on the location information "
        "available in the current Google Sheet data."
    )

    # =========================================================
    # 1. CHECK FOR COORDINATE COLUMNS
    # =========================================================

    latitude_column = _find_column(
        df,
        [
            "Latitude",
            "Lat",
            "latitude",
            "lat",
        ],
    )

    longitude_column = _find_column(
        df,
        [
            "Longitude",
            "Long",
            "Lng",
            "longitude",
            "long",
            "lng",
        ],
    )

    # =========================================================
    # 2. GEOGRAPHIC SUMMARY
    # =========================================================

    st.markdown("### 📍 Geographic Data Availability")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Filtered Records",
            f"{len(df):,}",
        )

    with c2:
        if "Ward Name" in df.columns:
            ward_count = (
                _clean_text(
                    df,
                    "Ward Name",
                )
            )
            ward_count = ward_count[
                ward_count.ne("")
                & ward_count.ne("nan")
            ]

            st.metric(
                "Wards",
                f"{ward_count.nunique():,}",
            )
        else:
            st.metric(
                "Wards",
                "0",
            )

    with c3:
        if "Facility Name" in df.columns:
            facility_count = (
                _clean_text(
                    df,
                    "Facility Name",
                )
            )
            facility_count = facility_count[
                facility_count.ne("")
                & facility_count.ne("nan")
            ]

            st.metric(
                "Facilities",
                f"{facility_count.nunique():,}",
            )
        else:
            st.metric(
                "Facilities",
                "0",
            )

    with c4:
        if (
            latitude_column is not None
            and longitude_column is not None
        ):
            st.metric(
                "Coordinates",
                "Available",
            )
        else:
            st.metric(
                "Coordinates",
                "Not available",
            )

    # =========================================================
    # 3. REAL MAP WHEN LAT/LONG ARE AVAILABLE
    # =========================================================

    if (
        latitude_column is not None
        and longitude_column is not None
    ):

        st.divider()

        st.markdown("### 🗺️ Facility / Record Map")

        map_df = df[
            [
                latitude_column,
                longitude_column,
            ]
        ].copy()

        map_df["latitude"] = pd.to_numeric(
            map_df[latitude_column],
            errors="coerce",
        )

        map_df["longitude"] = pd.to_numeric(
            map_df[longitude_column],
            errors="coerce",
        )

        map_df = map_df[
            map_df["latitude"].between(
                -90,
                90,
            )
            & map_df["longitude"].between(
                -180,
                180,
            )
        ]

        if not map_df.empty:

            st.map(
                map_df[
                    [
                        "latitude",
                        "longitude",
                    ]
                ],
                use_container_width=True,
            )

            st.caption(
                f"{len(map_df):,} valid geographic records "
                "are displayed on the map."
            )

        else:
            st.warning(
                "Latitude and Longitude columns exist, "
                "but no valid coordinates are available "
                "for the selected records."
            )

    # =========================================================
    # 4. LOCATION FIELDS AVAILABLE IN CURRENT DATA
    # =========================================================

    st.divider()

    st.markdown("### 📌 Location-wise Programme Distribution")

    location_columns = []

    if "Ward Name" in df.columns:
        location_columns.append(
            "Ward Name"
        )

    if "Facility Name" in df.columns:
        location_columns.append(
            "Facility Name"
        )

    if "Facility Type" in df.columns:
        location_columns.append(
            "Facility Type"
        )

    if "Patient Address" in df.columns:
        location_columns.append(
            "Patient Address"
        )

    if not location_columns:

        st.info(
            "No location-related fields are available "
            "in the current dataset."
        )

    else:

        selected_location = st.selectbox(
            "Select Location Dimension",
            options=location_columns,
            key="map_location_dimension",
        )

        location_values = _clean_text(
            df,
            selected_location,
        )

        location_values = location_values[
            location_values.ne("")
            & location_values.ne("nan")
            & location_values.ne("NaT")
        ]

        if location_values.empty:

            st.info(
                f"No valid {selected_location} information "
                "is available for the selected records."
            )

        else:

            location_counts = (
                location_values
                .value_counts()
                .rename_axis(
                    selected_location
                )
                .reset_index(
                    name="Records"
                )
            )

            location_counts.insert(
                0,
                "Rank",
                range(
                    1,
                    len(location_counts) + 1,
                ),
            )

            location_counts["Percentage"] = (
                location_counts["Records"]
                / location_counts["Records"].sum()
                * 100
            ).round(2)

            st.bar_chart(
                location_counts
                .head(25)
                .set_index(
                    selected_location
                )["Records"],
                use_container_width=True,
            )

            display_location = (
                location_counts
                .head(50)
                .copy()
            )

            display_location["Percentage"] = (
                display_location["Percentage"]
                .map(
                    lambda x:
                    f"{x:.2f}%"
                )
            )

            st.dataframe(
                display_location,
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # 5. WARD-WISE LOCATION SUMMARY
    # =========================================================

    st.divider()

    st.markdown("### 📍 Ward-wise Geographic Summary")

    if "Ward Name" in df.columns:

        ward_values = _clean_text(
            df,
            "Ward Name",
        )

        ward_values = ward_values[
            ward_values.ne("")
            & ward_values.ne("nan")
            & ward_values.ne("NaT")
        ]

        if not ward_values.empty:

            ward_summary = (
                ward_values
                .value_counts()
                .rename_axis("Ward")
                .reset_index(
                    name="Records"
                )
            )

            ward_summary["Percentage"] = (
                ward_summary["Records"]
                / ward_summary["Records"].sum()
                * 100
            ).round(2)

            st.dataframe(
                ward_summary,
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Ward information is not available."
            )

    # =========================================================
    # 6. FACILITY-WISE LOCATION SUMMARY
    # =========================================================

    st.divider()

    st.markdown("### 🏥 Facility-wise Geographic Summary")

    if "Facility Name" in df.columns:

        facility_values = _clean_text(
            df,
            "Facility Name",
        )

        facility_values = facility_values[
            facility_values.ne("")
            & facility_values.ne("nan")
            & facility_values.ne("NaT")
        ]

        if not facility_values.empty:

            facility_summary = (
                facility_values
                .value_counts()
                .rename_axis("Facility")
                .reset_index(
                    name="Records"
                )
            )

            facility_summary.insert(
                0,
                "Rank",
                range(
                    1,
                    len(facility_summary) + 1,
                ),
            )

            st.dataframe(
                facility_summary.head(100),
                use_container_width=True,
                hide_index=True,
            )

        else:

            st.info(
                "Facility information is not available."
            )

    # =========================================================
    # 7. PATIENT ADDRESS SUMMARY
    # =========================================================

    st.divider()

    st.markdown("### 🏠 Patient Address Information")

    if "Patient Address" in df.columns:

        address_values = _clean_text(
            df,
            "Patient Address",
        )

        address_values = address_values[
            address_values.ne("")
            & address_values.ne("nan")
            & address_values.ne("NaT")
        ]

        if address_values.empty:

            st.info(
                "Patient address information is not available."
            )

        else:

            st.metric(
                "Records with Patient Address",
                f"{len(address_values):,}",
            )

            st.dataframe(
                pd.DataFrame(
                    {
                        "Patient Address": address_values
                        .value_counts()
                        .head(100)
                        .index,
                        "Records": address_values
                        .value_counts()
                        .head(100)
                        .values,
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    # =========================================================
    # 8. MAP DATA REQUIREMENT
    # =========================================================

    st.divider()

    st.markdown("### ℹ️ Geographic Data Requirement")

    if (
        latitude_column is None
        or longitude_column is None
    ):

        st.info(
            "The current Google Sheet does not contain "
            "Latitude and Longitude fields. Therefore, "
            "the dashboard does not generate artificial "
            "coordinates. Ward, facility and patient-location "
            "analysis is shown using the actual available data."
        )

        st.markdown(
            """
            **For a true geographic map in a future update, "
            "the Google Sheet can include:**

            - Latitude
            - Longitude
            - Facility Latitude
            - Facility Longitude
            - Ward Latitude
            - Ward Longitude

            Once these fields are available, the dashboard "
            "can plot the corresponding facilities/wards "
            "without changing the existing Global Dashboard Filters.
            """
        )

    else:

        st.success(
            "Latitude and Longitude fields are available. "
            "Valid geographic records are being used for mapping."
        )
