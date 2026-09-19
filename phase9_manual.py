import streamlit as st


def render_manual():

    st.subheader("📘 User Manual")

    st.caption(
        "Health Programme Management Dashboard — "
        "User Guide and Operational Instructions"
    )

    # =========================================================
    # 1. PURPOSE
    # =========================================================

    st.markdown("## 1. Dashboard Purpose")

    st.write(
        "This dashboard is designed for programme monitoring, "
        "data review, trend analysis, facility-wise and ward-wise "
        "assessment, demographic analysis, validation and "
        "management-level decision support."
    )

    st.write(
        "The dashboard uses the configured Google Sheet as the "
        "primary data source. The analysis displayed on the "
        "dashboard changes according to the Global Dashboard Filters."
    )

    # =========================================================
    # 2. DATA SOURCE
    # =========================================================

    st.markdown("## 2. Data Source")

    st.info(
        "The dashboard is connected to the configured Google Sheet. "
        "When new records are added or existing records are updated "
        "in the source sheet, use the Refresh Google Sheet Data "
        "option to load the latest information."
    )

    st.markdown(
        """
        **Important operational points**

        - The Google Sheet should remain accessible to the dashboard.
        - Column names should not be changed without updating the dashboard.
        - New records should follow the existing data-entry structure.
        - Reporting dates should be entered in a valid date format.
        - Facility and Ward names should be entered consistently.
        """
    )

    # =========================================================
    # 3. GLOBAL DASHBOARD CONTROL
    # =========================================================

    st.markdown("## 3. Global Dashboard Control")

    st.write(
        "The Global Dashboard Filters are common to the entire "
        "dashboard. The selected filters are applied before the "
        "data is passed to the individual dashboard sections."
    )

    filter_table = {
        "Filter": [
            "Year",
            "Month",
            "Week",
            "Disease",
            "Facility",
            "Ward",
            "Gender",
            "Age Group",
            "OPD / IPD",
            "From Date",
            "To Date",
        ],
        "Purpose": [
            "Select reporting year.",
            "Select reporting month.",
            "Select reporting week.",
            "Select one or more diseases.",
            "Analyse selected facilities.",
            "Analyse selected wards.",
            "Analyse selected gender categories.",
            "Analyse selected age groups.",
            "Separate OPD and IPD records.",
            "Set the beginning of the reporting period.",
            "Set the end of the reporting period.",
        ],
    }

    st.dataframe(
        filter_table,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(
        """
        **Filter behaviour**

        - Blank filter = **All records**
        - Multiple values can be selected where applicable.
        - Selecting a filter updates the dashboard automatically.
        - Multiple filters can be used together.
        - Date filters can be used with other filters.
        - Use **Reset** to return all filters to their blank/default state.
        """
    )

    # =========================================================
    # 4. HOW TO USE FILTERS
    # =========================================================

    st.markdown("## 4. How to Apply Filters")

    st.markdown(
        """
        **Step 1:** Open the dashboard.

        **Step 2:** Locate the **Global Dashboard Filters** panel.

        **Step 3:** Select the required Year, Month, Disease, Facility,
        Ward, Gender, Age Group or OPD/IPD.

        **Step 4:** If required, select a From Date and To Date.

        **Step 5:** Review the **Filtered Records** count.

        **Step 6:** Move between dashboard tabs. The selected filters
        continue to control the analysis.

        **Step 7:** To remove all selections, click **↩️ Reset**.
        """
    )

    # =========================================================
    # 5. DASHBOARD TABS
    # =========================================================

    st.markdown("## 5. Dashboard Sections")

    tab_table = {
        "Section": [
            "Overview",
            "Charts & Trends",
            "Demographics",
            "Ward Analysis",
            "Map",
            "Data Explorer",
            "Prediction",
            "User Manual",
            "Validation & KPI",
            "Drill-down & Export",
        ],
        "Primary Use": [
            "Overall programme status, KPIs, disease, facility and ward burden.",
            "Month-wise, disease-wise, facility-wise and ward-wise trends.",
            "Age, age group, gender and OPD/IPD analysis.",
            "Ward burden, ward ranking and ward-level cross-analysis.",
            "Geographic and location-related analysis.",
            "Record-level search, review, filtering and data export.",
            "Historical trend and indicative projection.",
            "Dashboard operating instructions.",
            "Data validation, completeness and KPI checks.",
            "Detailed drill-down and management export.",
        ],
    }

    st.dataframe(
        tab_table,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # 6. OVERVIEW
    # =========================================================

    st.markdown("## 6. Overview")

    st.write(
        "The Overview section provides a management-level summary "
        "of the currently filtered records."
    )

    st.markdown(
        """
        Key indicators include:

        - Total Records
        - Number of Diseases
        - Number of Facilities
        - Number of Wards
        - Disease-wise burden
        - Top facilities
        - Top burden wards
        - Reporting period
        """
    )

    # =========================================================
    # 7. CHARTS & TRENDS
    # =========================================================

    st.markdown("## 7. Charts & Trends")

    st.write(
        "This section provides trend-based analysis for monitoring "
        "changes in programme records over time."
    )

    st.markdown(
        """
        Available analysis includes:

        - Month-wise record trend
        - Monthly disease comparison
        - Disease-wise burden
        - Facility-wise burden
        - Ward-wise burden
        - OPD/IPD distribution
        - Reporting-date trend
        """
    )

    # =========================================================
    # 8. DEMOGRAPHICS
    # =========================================================

    st.markdown("## 8. Demographics")

    st.write(
        "The Demographics section provides population-level "
        "characteristics of the selected records."
    )

    st.markdown(
        """
        Available analysis includes:

        - Mean age
        - Median age
        - Minimum and maximum age
        - Age-wise distribution
        - Age Group-wise distribution
        - Gender-wise distribution
        - Gender × Age Group
        - OPD/IPD distribution
        - Age Group × OPD/IPD
        - Disease × Gender
        - Demographic data quality
        """
    )

    # =========================================================
    # 9. WARD ANALYSIS
    # =========================================================

    st.markdown("## 9. Ward Analysis")

    st.write(
        "Ward Analysis is intended for geographic programme "
        "management at ward level."
    )

    st.markdown(
        """
        Available analysis includes:

        - Top burden ward
        - Ward-wise ranking
        - Ward-wise record distribution
        - Top 10 burden wards
        - Disease × Ward
        - Facility × Ward
        - Ward × Gender
        - Ward × Age Group
        - Top Ward × Facility detail
        - Ward data quality
        """
    )

    # =========================================================
    # 10. MAP
    # =========================================================

    st.markdown("## 10. Map")

    st.write(
        "The Map section uses actual geographic coordinates when "
        "Latitude and Longitude fields are available in the dataset."
    )

    st.warning(
        "If Latitude and Longitude are not available in the "
        "Google Sheet, the dashboard does not create artificial "
        "coordinates. In that situation, ward, facility and "
        "patient-location information is presented as tabular/"
        "distribution analysis."
    )

    # =========================================================
    # 11. DATA EXPLORER
    # =========================================================

    st.markdown("## 11. Data Explorer")

    st.markdown(
        """
        Data Explorer can be used for detailed record-level review.

        **Available functions**

        - Search across all columns
        - Select columns for display
        - Sort records
        - Set display row limit
        - Review filtered records
        - Download complete filtered data as CSV
        - Download complete filtered data as Excel
        - Download selected columns as CSV
        - Review column-wise data quality
        """
    )

    # =========================================================
    # 12. PREDICTION
    # =========================================================

    st.markdown("## 12. Prediction")

    st.write(
        "The Prediction section provides historical trend-based "
        "indicative projections for programme planning."
    )

    st.markdown(
        """
        The section includes:

        - Historical monthly trend
        - Three-period moving average
        - Indicative next-period projection
        - Disease-specific historical trend
        - Facility-specific historical trend
        - Projection methodology
        """
    )

    st.warning(
        "Projection outputs are indicative statistical estimates "
        "based on historical record volume. They are not confirmed "
        "clinical, epidemiological or outbreak forecasts."
    )

    # =========================================================
    # 13. VALIDATION & KPI
    # =========================================================

    st.markdown("## 13. Validation & KPI")

    st.write(
        "This section is intended to assess the completeness, "
        "consistency and basic validity of the filtered dataset."
    )

    st.markdown(
        """
        Typical validation checks include:

        - Total records
        - Missing values
        - Date validity
        - Age validity
        - Gender completeness
        - Disease completeness
        - Facility completeness
        - Ward completeness
        - Duplicate records
        - KPI summary
        """
    )

    # =========================================================
    # 14. DRILL-DOWN & EXPORT
    # =========================================================

    st.markdown("## 14. Drill-down & Export")

    st.write(
        "This section supports management-level detailed review "
        "and extraction of filtered programme information."
    )

    st.markdown(
        """
        Use this section when detailed analysis is required after "
        "applying Year, Month, Disease, Facility, Ward, Gender, "
        "Age Group, OPD/IPD or date filters."
        """
    )

    # =========================================================
    # 15. REFRESH GOOGLE SHEET
    # =========================================================

    st.markdown("## 15. Refresh Google Sheet Data")

    st.markdown(
        """
        To load the latest source data:

        **Step 1:** Update the Google Sheet.

        **Step 2:** Save/complete the required data entry.

        **Step 3:** Return to the dashboard.

        **Step 4:** Use **🔄 Refresh Google Sheet Data** from the "
        sidebar.

        **Step 5:** Wait for the refresh to complete.

        **Step 6:** Review the updated record count and reporting period.
        """
    )

    st.info(
        "The dashboard uses cached data for performance. "
        "The Refresh option clears the relevant cache and reloads "
        "the Google Sheet."
    )

    # =========================================================
    # 16. RECOMMENDED MANAGEMENT WORKFLOW
    # =========================================================

    st.markdown("## 16. Recommended Management Workflow")

    workflow = {
        "Step": [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
        ],
        "Activity": [
            "Refresh the Google Sheet data.",
            "Review overall KPIs in Overview.",
            "Check monthly trends in Charts & Trends.",
            "Review age and gender distribution in Demographics.",
            "Identify ward-level burden in Ward Analysis.",
            "Validate data quality in Validation & KPI.",
            "Use Drill-down & Export for detailed follow-up.",
        ],
    }

    st.dataframe(
        workflow,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # 17. DATA ENTRY GUIDANCE
    # =========================================================

    st.markdown("## 17. Data Entry Guidance")

    st.markdown(
        """
        For reliable dashboard outputs:

        - Use consistent facility names.
        - Use consistent ward names.
        - Avoid unnecessary spelling variations.
        - Enter reporting dates correctly.
        - Enter age as a numeric value wherever possible.
        - Use standard gender categories.
        - Use consistent disease/diagnosis terminology.
        - Avoid accidental blank rows.
        - Do not rename required source columns without updating
          the dashboard data-mapping logic.
        """
    )

    # =========================================================
    # 18. IMPORTANT INTERPRETATION NOTES
    # =========================================================

    st.markdown("## 18. Important Interpretation Notes")

    st.markdown(
        """
        **Record count is not automatically equivalent to disease incidence.**

        Programme managers should interpret dashboard findings in the
        context of:

        - Reporting completeness
        - Facility reporting practices
        - Testing availability
        - Case definition
        - Data entry quality
        - Changes in surveillance intensity
        - Missing records
        - Duplicate records
        - Seasonal variation
        """
    )

    # =========================================================
    # 19. TROUBLESHOOTING
    # =========================================================

    st.markdown("## 19. Troubleshooting")

    troubleshooting = {
        "Problem": [
            "No data displayed",
            "Filters show no records",
            "Reporting period looks incorrect",
            "Facility/Ward missing",
            "Map has no points",
            "Export contains fewer records than expected",
        ],
        "Action": [
            "Check Google Sheet access and refresh the dashboard.",
            "Reset filters and review the selected criteria.",
            "Check Reporting Date values in the source data.",
            "Check source column names and blank values.",
            "Latitude/Longitude may not be available or valid.",
            "Check whether a search term or filter is still active.",
        ],
    }

    st.dataframe(
        troubleshooting,
        use_container_width=True,
        hide_index=True,
    )

    # =========================================================
    # 20. FOOTER
    # =========================================================

    st.divider()

    st.success(
        "Dashboard User Manual completed. "
        "Use the Global Dashboard Filters first, then review "
        "the relevant management section."
    )

    st.caption(
        "Health Programme Management Dashboard | "
        "Live Google Sheet Based Monitoring System"
    )
