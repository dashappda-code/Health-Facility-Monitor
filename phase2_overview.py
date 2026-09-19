import pandas as pd
import streamlit as st

from phase1_data import refresh_data


MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def find_column(df, keywords):
    if df is None or df.empty:
        return None
    columns = list(df.columns)
    for keyword in keywords:
        k = str(keyword).lower().strip()
        for col in columns:
            if str(col).lower().strip() == k:
                return col
    for keyword in keywords:
        k = str(keyword).lower().strip()
        for col in columns:
            if k in str(col).lower():
                return col
    return None


def get_values(df, column):
    if column is None or column not in df.columns:
        return []
    values = df[column].dropna().astype(str).str.strip()
    values = values[values != ""]
    return sorted(values.unique().tolist(), key=str)


def _all_selected(values, key):
    """Return every available value on first load; preserve user changes afterwards."""
    if key not in st.session_state:
        return list(values)
    current = st.session_state.get(key, [])
    valid = set(values)
    return [v for v in current if v in valid]


def _reset_filters():
    keys = [
        "global_year_filter", "global_month_filter", "global_week_filter",
        "global_disease_filter", "global_facility_filter", "global_ward_filter",
        "global_gender_filter", "global_age_filter", "global_opdipd_filter",
        "global_area_filter", "global_status_filter", "global_date_range",
    ]
    for key in keys:
        st.session_state.pop(key, None)


def create_filters(df):
    year_col = find_column(df, ["year", "वर्ष"])
    month_col = find_column(df, ["month", "महिना"])
    week_col = find_column(df, ["week", "week no", "week number", "आठवडा"])
    disease_col = find_column(df, ["disease", "confirmed diagnosis", "diagnosis", "disease name", "रोग"])
    facility_col = find_column(df, ["facility", "facility name", "facility name lform", "health facility", "institution", "आरोग्य केंद्र"])
    ward_col = find_column(df, ["ward", "ward name", "ward no", "ward number", "प्रभाग"])
    gender_col = find_column(df, ["gender", "sex", "लिंग"])
    age_group_col = find_column(df, ["age group", "age_group", "agegroup", "age category", "वयोगट"])
    opd_ipd_col = find_column(df, ["opd/ipd", "opd ipd", "opd_ipd", "opd ipd", "patient type", "service type"])
    area_col = find_column(df, ["area", "area name", "locality", "location", "patient address", "परिसर"])
    status_col = find_column(df, ["status", "case status", "case_status", "diagnosis status"])
    date_col = find_column(df, ["reporting date", "date of reporting", "date", "event date", "दिनांक"])

    years = get_values(df, year_col)
    months = [m for m in MONTH_ORDER if m in get_values(df, month_col)] or get_values(df, month_col)
    weeks = get_values(df, week_col)
    diseases = get_values(df, disease_col)
    facilities = get_values(df, facility_col)
    wards = get_values(df, ward_col)
    genders = get_values(df, gender_col)
    age_groups = get_values(df, age_group_col)
    opd_ipd = get_values(df, opd_ipd_col)
    areas = get_values(df, area_col)
    statuses = get_values(df, status_col)

    # ------------------------------------------------------------
    # Attractive global control panel
    # ------------------------------------------------------------
    st.markdown("""
    <div class="global-filter-heading">
        <div class="global-filter-title">🎛️ Global Dashboard Control</div>
        <div class="global-filter-subtitle">Filters apply to all dashboard sections. Default view shows the complete available dataset.</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("global_dashboard_filter_form", clear_on_submit=False):
        st.markdown('<div class="filter-row-label">PRIMARY FILTERS</div>', unsafe_allow_html=True)
        r1 = st.columns(6)
        with r1[0]:
            selected_years = st.multiselect("📅 Year", years, default=_all_selected(years, "global_year_filter"), key="global_year_filter")
        with r1[1]:
            selected_months = st.multiselect("🗓️ Month", months, default=_all_selected(months, "global_month_filter"), key="global_month_filter")
        with r1[2]:
            selected_weeks = st.multiselect("📌 Week", weeks, default=_all_selected(weeks, "global_week_filter"), key="global_week_filter")
        with r1[3]:
            selected_diseases = st.multiselect("🦠 Disease", diseases, default=_all_selected(diseases, "global_disease_filter"), key="global_disease_filter")
        with r1[4]:
            selected_facilities = st.multiselect("🏥 Facility", facilities, default=_all_selected(facilities, "global_facility_filter"), key="global_facility_filter")
        with r1[5]:
            selected_wards = st.multiselect("🏘️ Ward", wards, default=_all_selected(wards, "global_ward_filter"), key="global_ward_filter")

        st.markdown('<div class="filter-row-label second">DEMOGRAPHIC / SERVICE FILTERS</div>', unsafe_allow_html=True)
        r2 = st.columns(6)
        with r2[0]:
            selected_genders = st.multiselect("⚥ Gender", genders, default=_all_selected(genders, "global_gender_filter"), key="global_gender_filter")
        with r2[1]:
            selected_age_groups = st.multiselect("👤 Age Group", age_groups, default=_all_selected(age_groups, "global_age_filter"), key="global_age_filter")
        with r2[2]:
            selected_opd_ipd = st.multiselect("🏨 OPD / IPD", opd_ipd, default=_all_selected(opd_ipd, "global_opdipd_filter"), key="global_opdipd_filter")
        with r2[3]:
            selected_areas = st.multiselect("📍 Area", areas, default=_all_selected(areas, "global_area_filter"), key="global_area_filter")
        with r2[4]:
            selected_status = st.multiselect("🔎 Status", statuses, default=_all_selected(statuses, "global_status_filter"), key="global_status_filter")
        with r2[5]:
            date_from = date_to = None
            if date_col and date_col in df.columns:
                dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
                if not dates.empty:
                    min_date, max_date = dates.min().date(), dates.max().date()
                    selected_range = st.date_input(
                        "📆 Reporting Date",
                        value=st.session_state.get("global_date_range", (min_date, max_date)),
                        min_value=min_date,
                        max_value=max_date,
                        key="global_date_range",
                    )
                    if isinstance(selected_range, tuple) and len(selected_range) == 2:
                        date_from, date_to = selected_range
                    elif isinstance(selected_range, tuple) and len(selected_range) == 1:
                        date_from = date_to = selected_range[0]
                    elif hasattr(selected_range, "year"):
                        date_from = date_to = selected_range

        st.markdown('<div class="filter-actions">', unsafe_allow_html=True)
        b1, b2, b3 = st.columns([1.1, 1.1, 5])
        with b1:
            apply_clicked = st.form_submit_button("✅ Apply Filters", type="primary", use_container_width=True)
        with b2:
            reset_clicked = st.form_submit_button("↩️ Reset to All", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if reset_clicked:
        _reset_filters()
        st.rerun()

    return {
        "selected_years": selected_years,
        "selected_months": selected_months,
        "selected_weeks": selected_weeks,
        "selected_diseases": selected_diseases,
        "selected_facilities": selected_facilities,
        "selected_wards": selected_wards,
        "selected_genders": selected_genders,
        "selected_age_groups": selected_age_groups,
        "selected_opd_ipd": selected_opd_ipd,
        "selected_areas": selected_areas,
        "selected_status": selected_status,
        "area_column": area_col,
        "status_column": status_col,
        "date_column": date_col,
        "date_from": date_from,
        "date_to": date_to,
    }


def apply_filters(df, selected_years, selected_months, selected_weeks,
                  selected_diseases, selected_facilities, selected_wards,
                  selected_genders, selected_age_groups, selected_opd_ipd,
                  selected_areas, selected_status, area_column, status_column,
                  date_from, date_to):
    if df is None or df.empty:
        return df
    mask = pd.Series(True, index=df.index)

    def apply_text_filter(column, selected):
        nonlocal mask
        if not column or column not in df.columns or selected is None:
            return
        # Empty selection is treated as ALL, not as zero records.
        if len(selected) == 0:
            return
        mask &= df[column].astype(str).str.strip().isin([str(x).strip() for x in selected])

    mappings = [
        (find_column(df, ["year", "वर्ष"]), selected_years),
        (find_column(df, ["month", "महिना"]), selected_months),
        (find_column(df, ["week", "week no", "week number", "आठवडा"]), selected_weeks),
        (find_column(df, ["disease", "confirmed diagnosis", "diagnosis", "रोग"]), selected_diseases),
        (find_column(df, ["facility", "facility name", "facility name lform", "health facility", "institution"]), selected_facilities),
        (find_column(df, ["ward", "ward name", "ward no", "ward number"]), selected_wards),
        (find_column(df, ["gender", "sex", "लिंग"]), selected_genders),
        (find_column(df, ["age group", "age_group", "agegroup", "age category"]), selected_age_groups),
        (find_column(df, ["opd/ipd", "opd ipd", "opd_ipd", "patient type", "service type"]), selected_opd_ipd),
        (area_column, selected_areas),
        (status_column, selected_status),
    ]
    for col, values in mappings:
        apply_text_filter(col, values)

    date_col = find_column(df, ["reporting date", "date of reporting", "date", "event date", "दिनांक"])
    if date_col and date_col in df.columns and (date_from is not None or date_to is not None):
        dates = df[date_col] if pd.api.types.is_datetime64_any_dtype(df[date_col]) else pd.to_datetime(df[date_col], errors="coerce")
        if date_from is not None:
            mask &= dates.dt.date >= date_from
        if date_to is not None:
            mask &= dates.dt.date <= date_to
    return df.loc[mask].copy()


def calculate_kpis(df):
    if df is None or df.empty:
        return {"total_records": 0, "diseases": 0, "facilities": 0, "wards": 0}
    disease_col = find_column(df, ["disease", "confirmed diagnosis", "diagnosis", "रोग"])
    facility_col = find_column(df, ["facility", "facility name", "facility name lform", "health facility", "institution"])
    ward_col = find_column(df, ["ward", "ward name", "ward no", "ward number"])
    return {
        "total_records": len(df),
        "diseases": df[disease_col].nunique() if disease_col else 0,
        "facilities": df[facility_col].nunique() if facility_col else 0,
        "wards": df[ward_col].nunique() if ward_col else 0,
    }


def render_overview(df):
    st.subheader("📊 Programme Overview")
    if df is None or df.empty:
        st.warning("No records available for the selected filters.")
        return
    facility_col = find_column(df, ["facility", "facility name", "facility name lform", "health facility", "institution"])
    ward_col = find_column(df, ["ward", "ward name", "ward no", "ward number"])
    disease_col = find_column(df, ["disease", "confirmed diagnosis", "diagnosis", "रोग"])
    date_col = find_column(df, ["reporting date", "date of reporting", "date", "event date", "दिनांक"])

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🏥 Top Facilities")
        if facility_col:
            counts = df[facility_col].astype(str).value_counts().head(10)
            st.dataframe(counts.rename("Records"), use_container_width=True)
    with c2:
        st.markdown("#### 🏘️ Top Burden Wards")
        if ward_col:
            counts = df[ward_col].astype(str).value_counts().head(10)
            st.dataframe(counts.rename("Records"), use_container_width=True)

    st.markdown("#### 📈 Monthly Trend")
    if date_col:
        dates = df[date_col] if pd.api.types.is_datetime64_any_dtype(df[date_col]) else pd.to_datetime(df[date_col], errors="coerce")
        monthly = dates.dropna().dt.to_period("M").value_counts().sort_index()
        if not monthly.empty:
            st.line_chart(monthly)

    st.markdown("#### 🦠 Disease Distribution")
    if disease_col:
        counts = df[disease_col].astype(str).value_counts().head(15)
        st.dataframe(counts.rename("Records"), use_container_width=True)
