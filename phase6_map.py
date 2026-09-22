import streamlit as st
import pandas as pd

from chart_helpers import render_bar_chart


# ============================================================
# HELPER FUNCTIONS
# ============================================================

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


# ============================================================
# MAIN MAP FUNCTION
# ============================================================

def render_map(df):

    st.subheader("🗺️ Map & Geographic Analysis")

    if df is None or df.empty:
        st.warning(
            "No records available for the selected filters."
        )
        return

    st.caption(
        "Geographic view based on facility coordinates "
        "available in the current Google Sheet data."
    )

    # ========================================================
    # BASIC COLUMN DETECTION
    # ========================================================

    facility_column = _find_column(
        df,
        [
            "Facility Name",
            "Facility",
            "facility_name",
            "facility",
        ],
    )

    ward_column = _find_column(
        df,
        [
            "Ward Name",
            "Ward",
            "ward_name",
            "ward",
        ],
    )

    facility_type_column = _find_column(
        df,
        [
            "Facility Type",
            "facility_type",
        ],
    )

    latitude_column = _find_column(
        df,
        [
            "Facility Latitude",
        ],
    )

    longitude_column = _find_column(
        df,
        [
            "Facility Longitude",
        ],
    )

    # ========================================================
    # GEOGRAPHIC DATA AVAILABILITY
    # ========================================================

    st.markdown("### 📍 Geographic Data Availability")

    c1, c2, c3, c4 = st.columns(4)

    # Filtered Records
    with c1:
        st.metric(
            "Filtered Records",
            f"{len(df):,}"
        )

    # Wards
    with c2:

        if ward_column is not None:

            ward_count = _clean_text(
                df,
                ward_column,
            )

            ward_count = ward_count[
                ward_count.ne("")
                & ward_count.ne("nan")
                & ward_count.ne("NaT")
            ]

            st.metric(
                "Wards",
                f"{ward_count.nunique():,}"
            )

        else:

            st.metric(
                "Wards",
                "0"
            )

    # Facilities
    with c3:

        if facility_column is not None:

            facility_count = _clean_text(
                df,
                facility_column,
            )

            facility_count = facility_count[
                facility_count.ne("")
                & facility_count.ne("nan")
                & facility_count.ne("NaT")
            ]

            st.metric(
                "Facilities",
                f"{facility_count.nunique():,}"
            )

        else:

            st.metric(
                "Facilities",
                "0"
            )

    # Coordinates status
    with c4:

        if (
            latitude_column is not None
            and longitude_column is not None
        ):

            st.metric(
                "Coordinates",
                "Available"
            )

        else:

            st.metric(
                "Coordinates",
                "Not available"
            )

    # ========================================================
    # FACILITY MAP
    # ========================================================

    if (
        latitude_column is not None
        and longitude_column is not None
    ):

        st.divider()

        st.markdown(
            "### 🗺️ Facility Geographic Map"
        )

        # ----------------------------------------------------
        # Prepare working dataframe
        # ----------------------------------------------------

        map_source = df.copy()

        map_source["_facility_latitude"] = pd.to_numeric(
            map_source[latitude_column],
            errors="coerce",
        )

        map_source["_facility_longitude"] = pd.to_numeric(
            map_source[longitude_column],
            errors="coerce",
        )

        # ----------------------------------------------------
        # Remove invalid coordinates
        # ----------------------------------------------------

        map_source = map_source[
            map_source["_facility_latitude"].between(
                -90,
                90,
            )
            &
            map_source["_facility_longitude"].between(
                -180,
                180,
            )
        ].copy()

        # ----------------------------------------------------
        # Facility name cleanup
        # ----------------------------------------------------

        if facility_column is not None:

            map_source["_facility_name"] = _clean_text(
                map_source,
                facility_column,
            )

            map_source = map_source[
                map_source["_facility_name"].ne("")
                & map_source["_facility_name"].ne("nan")
                & map_source["_facility_name"].ne("NaT")
            ].copy()

        # ----------------------------------------------------
        # Create facility-level map
        # ----------------------------------------------------

        if map_source.empty:

            st.info(
                "Facility Latitude and Facility Longitude "
                "fields are available, but no valid facility "
                "coordinates are available for the selected records."
            )

        else:

            # ------------------------------------------------
            # Build facility-level aggregation
            # ------------------------------------------------

            if facility_column is not None:

                aggregation = {
                    "_facility_latitude": "first",
                    "_facility_longitude": "first",
                }

                if ward_column is not None:
                    aggregation[ward_column] = "first"

                if facility_type_column is not None:
                    aggregation[facility_type_column] = "first"

                facility_map = (
                    map_source
                    .groupby(
                        "_facility_name",
                        dropna=False,
                    )
                    .agg(aggregation)
                    .reset_index()
                )

                # Count filtered records for each facility
                record_counts = (
                    map_source["_facility_name"]
                    .value_counts()
                    .rename("Filtered Records")
                    .reset_index()
                )

                record_counts = record_counts.rename(
                    columns={
                        "index": "_facility_name"
                    }
                )

                facility_map = facility_map.merge(
                    record_counts,
                    on="_facility_name",
                    how="left",
                )

            else:

                facility_map = map_source[
                    [
                        "_facility_latitude",
                        "_facility_longitude",
                    ]
                ].copy()

                facility_map["Filtered Records"] = 1

            # ------------------------------------------------
            # Final map dataframe
            # ------------------------------------------------

            final_map = pd.DataFrame(
                {
                    "latitude":
                        facility_map[
                            "_facility_latitude"
                        ],
                    "longitude":
                        facility_map[
                            "_facility_longitude"
                        ],
                }
            )

            # ------------------------------------------------
            # Map
            # ------------------------------------------------

            st.map(
                final_map,
                use_container_width=True,
            )

            st.caption(
                f"{len(facility_map):,} facility location(s) "
                "with valid coordinates are displayed."
            )

            # ------------------------------------------------
            # Facilities without coordinates
            # ------------------------------------------------

            if facility_column is not None:

                all_facilities = set(
                    _clean_text(
                        df,
                        facility_column,
                    )
                    .loc[
                        lambda s:
                        s.ne("")
                        & s.ne("nan")
                        & s.ne("NaT")
                    ]
                    .unique()
                )

                mapped_facilities = set(
                    facility_map[
                        "_facility_name"
                    ]
                    .dropna()
                    .astype(str)
                )

                missing_facilities = sorted(
                    all_facilities
                    - mapped_facilities
                )

                if missing_facilities:

                    st.info(
                        f"{len(missing_facilities):,} "
                        "facility/facilities do not have valid "
                        "coordinates and are not shown on the map."
                    )

    else:

        st.info(
            "Facility Latitude and Facility Longitude "
            "fields are not available in the current data."
        )

    # ========================================================
    # LOCATION-WISE PROGRAMME DISTRIBUTION
    # ========================================================

    st.divider()

    st.markdown(
        "### 📌 Location-wise Programme Distribution"
    )

    location_columns = []

    if ward_column is not None:
        location_columns.append(ward_column)

    if facility_column is not None:
        location_columns.append(facility_column)

    if facility_type_column is not None:
        location_columns.append(facility_type_column)

    patient_address_column = _find_column(
        df,
        [
            "Patient Address",
            "Patient_Address",
            "Address",
            "patient_address",
        ],
    )

    if patient_address_column is not None:
        location_columns.append(
            patient_address_column
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
                .rename_axis(selected_location)
                .reset_index(name="Records")
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

            render_bar_chart(
                location_counts
                .head(25)
                .set_index(selected_location)["Records"],
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

    # ========================================================
    # WARD-WISE SUMMARY
    # ========================================================

    st.divider()

    st.markdown(
        "### 📍 Ward-wise Geographic Summary"
    )

    if ward_column is not None:

        ward_values = _clean_text(
            df,
            ward_column,
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
                .reset_index(name="Records")
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

    else:

        st.info(
            "Ward information is not available."
        )

    # ========================================================
    # FACILITY-WISE SUMMARY
    # ========================================================

    st.divider()

    st.markdown(
        "### 🏥 Facility-wise Geographic Summary"
    )

    if facility_column is not None:

        facility_values = _clean_text(
            df,
            facility_column,
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
                .reset_index(name="Records")
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

    else:

        st.info(
            "Facility information is not available."
        )

    # ========================================================
    # PATIENT ADDRESS INFORMATION
    # ========================================================

    st.divider()

    st.markdown(
        "### 🏠 Patient Address Information"
    )

    if patient_address_column is not None:

        address_values = _clean_text(
            df,
            patient_address_column,
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

            address_counts = (
                address_values
                .value_counts()
                .head(100)
            )

            st.dataframe(
                pd.DataFrame(
                    {
                        "Patient Address":
                            address_counts.index,
                        "Records":
                            address_counts.values,
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    else:

        st.info(
            "Patient address information is not available."
        )

    # ========================================================
    # GEOGRAPHIC DATA REQUIREMENT
    # ========================================================

    st.divider()

    st.markdown(
        "### ℹ️ Geographic Data Requirement"
    )

    if (
        latitude_column is None
        or longitude_column is None
    ):

        st.info(
            "The current Google Sheet does not contain "
            "Facility Latitude and Facility Longitude "
            "fields. Therefore, the dashboard does not "
            "generate artificial coordinates. Ward, facility "
            "and patient-location analysis is shown using "
            "the actual available data."
        )

        st.markdown(
            """
**For a true facility geographic map, the Google Sheet should include:**

- Facility Latitude
- Facility Longitude

Once these fields contain valid coordinates, the dashboard
can plot the corresponding facilities without changing the
existing Global Dashboard Filters.
"""
        )

    else:

        # Check whether any valid coordinates actually exist

        coordinate_check = df[
            [
                latitude_column,
                longitude_column,
            ]
        ].copy()

        coordinate_check["latitude"] = pd.to_numeric(
            coordinate_check[latitude_column],
            errors="coerce",
        )

        coordinate_check["longitude"] = pd.to_numeric(
            coordinate_check[longitude_column],
            errors="coerce",
        )

        valid_coordinate_count = len(
            coordinate_check[
                coordinate_check["latitude"].between(
                    -90,
                    90,
                )
                &
                coordinate_check["longitude"].between(
                    -180,
                    180,
                )
            ]
        )

        if valid_coordinate_count > 0:

            st.success(
                "Facility Latitude and Facility Longitude "
                "fields are available and valid coordinates "
                "are being used for mapping."
            )

        else:

            st.info(
                "Facility Latitude and Facility Longitude "
                "fields are available, but no valid coordinates "
                "have been entered for the selected records yet."
            )
