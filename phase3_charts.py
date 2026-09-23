import streamlit as st
import pandas as pd

from chart_helpers import (
    render_bar_chart,
    render_line_chart,
)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _clean_series(df, column):
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="object")

    return (
        df[column]
        .fillna("")
        .astype(str)
        .str.strip()
    )


# ============================================================
# MONTH ORDER
# ============================================================

CALENDAR_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]

def _normalize_month(value):
    """
    सगळ्या प्रकारच्या महिन्यांच्या नावांना स्टँडर्ड 'Jan', 'Feb' मध्ये बदलते.
    """
    if pd.isna(value):
        return ""
        
    text = str(value).strip().lower()
    
    if text in {"january", "jan", "1", "01"}: return "Jan"
    if text in {"february", "feb", "2", "02"}: return "Feb"
    if text in {"march", "mar", "3", "03"}: return "Mar"
    if text in {"april", "apr", "4", "04"}: return "Apr"
    if text in {"may", "5", "05"}: return "May"
    if text in {"june", "jun", "6", "06"}: return "Jun"
    if text in {"july", "jul", "7", "07"}: return "Jul"
    if text in {"august", "aug", "8", "08"}: return "Aug"
    if text in {"september", "sep", "sept", "9", "09"}: return "Sep"
    if text in {"october", "oct", "10"}: return "Oct"
    if text in {"november", "nov", "11"}: return "Nov"
    if text in {"december", "dec", "12"}: return "Dec"
    
    return text


# ============================================================
# WARD ORDER
# ============================================================

def _sort_ward_dataframe(df, column="Ward"):
    if df is None or df.empty or column not in df.columns:
        return df

    result = df.copy()
    result["_ward_order"] = result[column].astype(str).str.strip().str.lower()
    result = result.sort_values("_ward_order", kind="stable").drop(columns="_ward_order").reset_index(drop=True)
    return result


# ============================================================
# MAIN CHART RENDERER
# ============================================================

def render_charts(df):

    st.subheader("📈 Charts & Trends")

    if df is None or df.empty:
        st.warning("No records available for the selected filters.")
        return

    st.caption(
        "Month-wise, disease-wise, facility-wise and ward-wise "
        "analysis based on the currently selected Global Dashboard Filters."
    )

    # ========================================================
    # 1. MONTH-WISE PROGRAMME TREND
    # ========================================================

    st.markdown("### 🗓️ Month-wise Programme Trend")

    if "Month" in df.columns:
        month_series = _clean_series(df, "Month")
        month_series = month_series[
            month_series.ne("")
            & month_series.str.lower().ne("nan")
            & month_series.str.lower().ne("nat")
            & month_series.str.lower().ne("none")
        ]

        if not month_series.empty:
            
            normalized_months = month_series.apply(_normalize_month)
            month_counts = normalized_months.value_counts().rename_axis("Month").reset_index(name="Records")

            # ------------------------------------------------
            # FORCE CATEGORICAL INDEX FOR CHART (JAN -> DEC)
            # ------------------------------------------------
            month_counts["Month"] = pd.Categorical(
                month_counts["Month"], 
                categories=CALENDAR_MONTHS, 
                ordered=True
            )
            
            # क्रमवारी लावून रिकामे महिने वगळणे
            month_counts = month_counts.dropna(subset=["Month"]).sort_values("Month").reset_index(drop=True)

            # इथे set_index केल्यावर CategoricalIndex तयार होतो ज्यामुळे चार्ट बरोबर दिसतो
            chart_series = month_counts.set_index("Month")["Records"]

            render_bar_chart(
                chart_series,
                use_container_width=True,
            )

            # टेबलमध्ये दाखवण्यासाठी परत string मध्ये बदलणे
            display_month_counts = month_counts.copy()
            display_month_counts["Month"] = display_month_counts["Month"].astype(str)
            st.dataframe(display_month_counts, use_container_width=True, hide_index=True)

        else:
            st.info("Month information is not available for the selected records.")

    # ========================================================
    # 2. MONTHLY DISEASE COMPARISON
    # ========================================================

    st.divider()
    st.markdown("### 🦠 Monthly Disease Comparison")

    if "Month" in df.columns and "Disease" in df.columns:
        temp = df[["Month", "Disease"]].copy()
        temp["Month"] = _clean_series(temp, "Month")
        temp["Disease"] = _clean_series(temp, "Disease")

        temp = temp[
            temp["Month"].ne("") & temp["Disease"].ne("")
            & temp["Month"].str.lower().ne("nan") & temp["Disease"].str.lower().ne("nan")
        ]

        if not temp.empty:
            temp["Month"] = temp["Month"].apply(_normalize_month)
            cross_tab = pd.crosstab(temp["Month"], temp["Disease"])

            # ------------------------------------------------
            # FORCE CATEGORICAL INDEX FOR CROSS_TAB (JAN -> DEC)
            # ------------------------------------------------
            cross_tab.index = pd.CategoricalIndex(
                cross_tab.index,
                categories=CALENDAR_MONTHS,
                ordered=True
            )
            
            # Sort the index based on calendar order
            cross_tab = cross_tab.sort_index().dropna(how='all')

            # TOP 10 DISEASES
            disease_totals = cross_tab.sum().sort_values(ascending=False)
            selected_diseases = disease_totals.head(10).index.tolist()
            chart_data = cross_tab[selected_diseases]

            render_line_chart(
                chart_data,
                use_container_width=True,
            )

            st.caption(
                "Chart displays the top 10 diseases by total "
                "records within the selected filters. "
                "Months are shown in calendar order."
            )

        else:
            st.info("Disease/month information is not available for the selected records.")

    # ========================================================
    # 3. DISEASE-WISE BURDEN
    # ========================================================

    st.divider()
    st.markdown("### 🦠 Disease-wise Burden")

    if "Disease" in df.columns:
        disease_series = _clean_series(df, "Disease")
        disease_series = disease_series[
            disease_series.ne("") & disease_series.str.lower().ne("nan") & disease_series.str.lower().ne("none")
        ]

        if not disease_series.empty:
            disease_counts = disease_series.value_counts().head(15).rename_axis("Disease").reset_index(name="Records")
            render_bar_chart(disease_counts.set_index("Disease")["Records"], use_container_width=True)
            st.dataframe(disease_counts, use_container_width=True, hide_index=True)
        else:
            st.info("Disease information is not available.")

    # ========================================================
    # 4. FACILITY-WISE BURDEN
    # ========================================================

    st.divider()
    st.markdown("### 🏥 Facility-wise Burden")

    if "Facility Name" in df.columns:
        facility_series = _clean_series(df, "Facility Name")
        facility_series = facility_series[
            facility_series.ne("") & facility_series.str.lower().ne("nan") & facility_series.str.lower().ne("none")
        ]

        if not facility_series.empty:
            facility_counts = facility_series.value_counts().head(20).rename_axis("Facility").reset_index(name="Records")
            render_bar_chart(facility_counts.set_index("Facility")["Records"], use_container_width=True)
            st.dataframe(facility_counts, use_container_width=True, hide_index=True)
        else:
            st.info("Facility information is not available.")

    # ========================================================
    # 5. WARD-WISE BURDEN
    # ========================================================

    st.divider()
    st.markdown("### 📍 Ward-wise Burden")

    if "Ward Name" in df.columns:
        ward_series = _clean_series(df, "Ward Name")
        ward_series = ward_series[
            ward_series.ne("") & ward_series.str.lower().ne("nan") & ward_series.str.lower().ne("none")
        ]

        if not ward_series.empty:
            ward_counts = ward_series.value_counts().rename_axis("Ward").reset_index(name="Records")
            ward_counts = _sort_ward_dataframe(ward_counts, "Ward")
            render_bar_chart(ward_counts.set_index("Ward")["Records"], use_container_width=True)
            st.dataframe(ward_counts, use_container_width=True, hide_index=True)
        else:
            st.info("Ward information is not available.")

    # ========================================================
    # 6. OPD / IPD COMPARISON
    # ========================================================

    st.divider()
    st.markdown("### 🏨 OPD / IPD Distribution")

    if "OPD/IPD" in df.columns:
        opd_series = _clean_series(df, "OPD/IPD")
        opd_series = opd_series[
            opd_series.ne("") & opd_series.str.lower().ne("nan") & opd_series.str.lower().ne("none")
        ]

        if not opd_series.empty:
            opd_counts = opd_series.value_counts().rename_axis("OPD/IPD").reset_index(name="Records")
            render_bar_chart(opd_counts.set_index("OPD/IPD")["Records"], use_container_width=True)
            st.dataframe(opd_counts, use_container_width=True, hide_index=True)
        else:
            st.info("OPD/IPD information is not available.")

    # ========================================================
    # 7. REPORTING DATE TREND
    # ========================================================

    st.divider()
    st.markdown("### 📅 Reporting Date Trend")

    if "Reporting Date" in df.columns:
        date_df = df[["Reporting Date"]].copy()
        date_df["Reporting Date"] = pd.to_datetime(date_df["Reporting Date"], errors="coerce")
        date_df = date_df.dropna(subset=["Reporting Date"])

        if not date_df.empty:
            daily_counts = (
                date_df
                .assign(Date=lambda x: x["Reporting Date"].dt.normalize())
                .groupby("Date")
                .size()
                .rename("Records")
            )
            render_line_chart(daily_counts, use_container_width=True)
        else:
            st.info("Valid reporting dates are not available.")

    # ========================================================
    # 8. SUMMARY
    # ========================================================

    st.divider()
    st.markdown("### 📌 Trend Summary")

    summary_columns = st.columns(4)

    with summary_columns[0]:
        st.metric("Records Analysed", f"{len(df):,}")

    with summary_columns[1]:
        if "Disease" in df.columns:
            disease_count = _clean_series(df, "Disease")
            disease_count = disease_count[disease_count.ne("") & disease_count.str.lower().ne("nan") & disease_count.str.lower().ne("none")]
            st.metric("Diseases", f"{disease_count.nunique():,}")
        else:
            st.metric("Diseases", "0")

    with summary_columns[2]:
        if "Facility Name" in df.columns:
            facility_count = _clean_series(df, "Facility Name")
            facility_count = facility_count[facility_count.ne("") & facility_count.str.lower().ne("nan") & facility_count.str.lower().ne("none")]
            st.metric("Facilities", f"{facility_count.nunique():,}")
        else:
            st.metric("Facilities", "0")

    with summary_columns[3]:
        if "Ward Name" in df.columns:
            ward_count = _clean_series(df, "Ward Name")
            ward_count = ward_count[ward_count.ne("") & ward_count.str.lower().ne("nan") & ward_count.str.lower().ne("none")]
            st.metric("Wards", f"{ward_count.nunique():,}")
        else:
            st.metric("Wards", "0")
