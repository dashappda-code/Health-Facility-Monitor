import re
import math
import io
import tempfile

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from chart_helpers import data_labels_enabled

# ============================================================
# CONFIGURATION
# ============================================================

POPULATION_SHEET_ID = "18qfha01Czh10i4PDRUpuumtRVwbQv7Pn09jFxGSbXHg"
POPULATION_GID = "846450963"

POPULATION_CSV_URL = (
    f"https://docs.google.com/spreadsheets/d/"
    f"{POPULATION_SHEET_ID}/export"
    f"?format=csv&gid={POPULATION_GID}"
)

DEFAULT_DENOMINATOR = 100_000

DENOMINATOR_OPTIONS = [
    1_000,
    10_000,
    100_000,
    1_000_000,
]

MIN_VALID_YEAR = 2000
MAX_VALID_YEAR = 2100

DATA_LABEL_FONT_SIZE = 10

COLORS = [
    "#1F77B4",
    "#FF7F0E",
    "#2CA02C",
    "#D62728",
    "#9467BD",
    "#8C564B",
    "#E377C2",
    "#7F7F7F",
    "#BCBD22",
    "#17BECF",
    "#4C78A4",
    "#F58518",
]

MONTH_NAMES = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


# ============================================================
# LOCAL UI HELPERS
# ============================================================

def _set_widget_state(widget_key, values):
    st.session_state[widget_key] = list(values)

def _reset_selection(widget_key, applied_key, default_values):
    defaults = list(default_values)
    st.session_state[widget_key] = defaults
    st.session_state[applied_key] = defaults

def _apply_deferred_selection(widget_key, applied_key, select_all_key, options):
    if st.session_state.get(select_all_key):
        st.session_state[widget_key] = list(options)
        st.session_state[applied_key] = list(options)
    else:
        st.session_state[applied_key] = list(st.session_state.get(widget_key, []))

def _reset_compact_selection(widget_key, applied_key, select_all_key, default_values):
    defaults = list(default_values)
    st.session_state[widget_key] = defaults
    st.session_state[applied_key] = defaults
    st.session_state[select_all_key] = False

def _smart_year_slider(label, options, default=None, key=None):
    """A smarter UI for years using a slider instead of a dropdown."""
    options = sorted(list(options))
    if not options:
        return None
        
    if len(options) == 1:
        st.info(f"{label}: **{options[0]}** (Only one year available)")
        return options[0]
        
    if default not in options:
        default = options[-1]
        
    if key is None:
        key = f"_smart_slider_{label}"
        
    widget_key = f"{key}__widget"
    
    if widget_key not in st.session_state:
        st.session_state[widget_key] = default
        
    selected = st.select_slider(
        label,
        options=options,
        value=st.session_state[widget_key],
        key=widget_key,
    )
    
    st.caption(f"✅ **Selected Year:** {selected}")
    return selected

def _single_select(label, options, default=None, key=None, reset_button_key=None, reset_label="↺ Reset", show_selected=True):
    options = list(options)
    if not options:
        return None

    if default not in options:
        default = options[0]

    if key is None:
        key = f"_single_select_{label}"

    widget_key = f"{key}__widget"

    applied = st.session_state.get(key)
    if isinstance(applied, (list, tuple)):
        applied = [value for value in applied if value in options][:1]
    elif applied in options:
        applied = [applied]
    else:
        applied = [default]

    if not applied:
        applied = [default]

    if widget_key not in st.session_state:
        st.session_state[widget_key] = list(applied)

    if reset_button_key is not None:
        st.button(
            reset_label,
            key=reset_button_key,
            help=f"Reset {label} to the default selection.",
            on_click=_reset_selection,
            args=(widget_key, key, (default,)),
        )

    selected = st.multiselect(
        label,
        options=options,
        max_selections=1,
        select_all=False,
        placeholder="Select one option",
        key=widget_key,
    )

    applied_value = selected[0] if selected else None
    if applied_value is not None:
        st.session_state[key] = [applied_value]

    if show_selected:
        if applied_value is None:
            st.caption("☐ **Selected:** None")
        else:
            st.caption(f"✅ **Selected:** {applied_value} · Charts below use this selection.")

    return applied_value

def _compact_multiselect(label, options, default=None, key=None, reset_button_key=None, reset_label="↺ Reset", show_selected=True, defer=False, apply_label="Apply Selection"):
    """Smarter multiselect with 'Select All' tick box feature."""
    options = list(options)
    if not options:
        return []

    if default is None:
        default = options[: min(5, len(options))]

    default = [value for value in default if value in options]

    if key is None:
        key = f"_compact_multiselect_{label}"

    widget_key = f"{key}__widget"
    select_all_key = f"{key}__select_all"
    applied_key = key
    
    applied = st.session_state.get(applied_key)
    if isinstance(applied, (list, tuple)):
        applied = [value for value in applied if value in options]
    else:
        applied = list(default)

    if widget_key not in st.session_state:
        st.session_state[widget_key] = list(applied)

    if defer:
        form_key = f"{key}__form"
        with st.form(form_key, clear_on_submit=False):
            st.checkbox("☑ Select All Options", key=select_all_key)
            selected = st.multiselect(label, options=options, key=widget_key)
            apply_col, reset_col = st.columns(2)
            with apply_col:
                st.form_submit_button(f"✓ {apply_label}", use_container_width=True, on_click=_apply_deferred_selection, args=(widget_key, applied_key, select_all_key, options))
            with reset_col:
                st.form_submit_button(reset_label, use_container_width=True, on_click=_reset_compact_selection, args=(widget_key, applied_key, select_all_key, tuple(default)))
        selected = st.session_state.get(applied_key, list(default))
    else:
        def _toggle_all():
            if st.session_state.get(select_all_key):
                st.session_state[widget_key] = list(options)
            else:
                st.session_state[widget_key] = []
                
        col1, col2 = st.columns([1, 1])
        with col1:
            st.checkbox("☑ Select All Options", key=select_all_key, on_change=_toggle_all)
        with col2:
            if reset_button_key is not None:
                st.button(reset_label, key=reset_button_key, use_container_width=True, on_click=_reset_compact_selection, args=(widget_key, applied_key, select_all_key, tuple(default)))
        
        selected = st.multiselect(label, options=options, key=widget_key)
        st.session_state[applied_key] = list(selected)

    selected = [value for value in selected if value in options]

    if show_selected:
        if selected:
            display = ", ".join(str(value) for value in selected)
            if len(selected) > 5:
                display = f"{len(selected)} options selected"
            st.caption(f"✅ **Selected:** {display} · The chart uses all checked selections.")
        else:
            st.caption("☐ **Selected:** None")

    return selected

def _chart_title(title, x_title, y_title, interpretation=None):
    subtitle_parts = [f"X-axis: {x_title}", f"Y-axis: {y_title}"]
    if interpretation:
        subtitle_parts.append(f"Interpretation: {interpretation}")
    return alt.TitleParams(
        text=title,
        subtitle=" | ".join(subtitle_parts),
        anchor="start",
        fontSize=16,
        fontWeight="bold",
        subtitleFontSize=11,
        subtitleFontWeight="normal",
        subtitlePadding=6,
        limit=1000,
    )

# ============================================================
# BASIC HELPERS
# ============================================================

def _clean_series(series):
    if series is None: return pd.Series(dtype="object")
    return series.fillna("").astype(str).str.strip()

def _valid_text(series):
    values = _clean_series(series)
    return values.ne("") & values.ne("nan") & values.ne("NaT") & values.ne("None") & values.ne("-")

def _safe_numeric(series):
    if series is None: return pd.Series(dtype=float)
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.replace(" ", "", regex=False).str.strip().replace({"": np.nan, "-": np.nan, "nan": np.nan, "NaN": np.nan, "None": np.nan, "NA": np.nan, "N/A": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")

def _alphabetical(values):
    cleaned = []
    for value in values:
        text = str(value).strip()
        if text and text not in {"nan", "NaT", "None", "-"}:
            cleaned.append(text)
    return sorted(list(dict.fromkeys(cleaned)), key=lambda x: x.upper())

def _month_number(value):
    if pd.isna(value): return np.nan
    text = str(value).strip().lower()
    month_map = {"january": 1, "jan": 1, "1": 1, "01": 1, "february": 2, "feb": 2, "2": 2, "02": 2, "march": 3, "mar": 3, "3": 3, "03": 3, "april": 4, "apr": 4, "4": 4, "04": 4, "may": 5, "5": 5, "05": 5, "june": 6, "jun": 6, "6": 6, "06": 6, "july": 7, "jul": 7, "7": 7, "07": 7, "august": 8, "aug": 8, "8": 8, "08": 8, "september": 9, "sep": 9, "sept": 9, "9": 9, "09": 9, "october": 10, "oct": 10, "10": 10, "november": 11, "nov": 11, "11": 11, "december": 12, "dec": 12, "12": 12}
    if text in month_map: return month_map[text]
    try:
        number = int(float(text))
        if 1 <= number <= 12: return number
    except Exception:
        pass
    return np.nan

def _format_number(value, decimals=0):
    if pd.isna(value): return "Unavailable"
    try:
        if decimals == 0: return f"{float(value):,.0f}"
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return str(value)

# ============================================================
# CASE DATA PREPARATION
# ============================================================

@st.cache_data(ttl=1800, show_spinner=False)
def _prepare_case_data(df):
    if df is None or df.empty: return pd.DataFrame()
    temp = df.copy()
    if "Year" in temp.columns:
        temp["Analysis_Year"] = pd.to_numeric(temp["Year"], errors="coerce")
    elif "Reporting Date" in temp.columns:
        dates = pd.to_datetime(temp["Reporting Date"], errors="coerce", dayfirst=True)
        temp["Analysis_Year"] = dates.dt.year
    else:
        temp["Analysis_Year"] = np.nan

    if "Month" in temp.columns:
        temp["Analysis_Month"] = temp["Month"].map(_month_number)
    elif "Reporting Date" in temp.columns:
        dates = pd.to_datetime(temp["Reporting Date"], errors="coerce", dayfirst=True)
        temp["Analysis_Month"] = dates.dt.month
    else:
        temp["Analysis_Month"] = np.nan

    temp = temp[temp["Analysis_Year"].between(MIN_VALID_YEAR, MAX_VALID_YEAR)].copy()
    if temp.empty: return pd.DataFrame()

    temp["Analysis_Year"] = temp["Analysis_Year"].astype(int)
    if "Ward Name" in temp.columns: temp["Ward Name"] = _clean_series(temp["Ward Name"])
    if "Disease" in temp.columns: temp["Disease"] = _clean_series(temp["Disease"])
    if "Facility Name" in temp.columns: temp["Facility Name"] = _clean_series(temp["Facility Name"])
    return temp

# ============================================================
# POPULATION DATA
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def _load_population_raw():
    population_df = pd.read_csv(POPULATION_CSV_URL)
    population_df.columns = [str(column).strip() for column in population_df.columns]
    return population_df

def _find_ward_column(df):
    if df is None or df.empty: return None
    candidates = ["WARD", "Ward", "Ward Name", "WARD NAME", "ward"]
    for candidate in candidates:
        if candidate in df.columns: return candidate
    for column in df.columns:
        normalized = str(column).strip().lower().replace("_", " ")
        if normalized in {"ward", "ward name"}: return column
    return None

def _extract_population_year(column_name):
    match = re.search(r"(20\d{2})", str(column_name))
    if not match: return None
    year = int(match.group(1))
    if MIN_VALID_YEAR <= year <= MAX_VALID_YEAR: return year
    return None

def _prepare_population_data(population_df):
    if population_df is None or population_df.empty: return pd.DataFrame(), pd.DataFrame(), []
    source = population_df.copy()
    ward_column = _find_ward_column(source)
    if ward_column is None: return pd.DataFrame(), pd.DataFrame(), []
    
    year_columns = {}
    for column in source.columns:
        if column == ward_column: continue
        year = _extract_population_year(column)
        if year is not None and year not in year_columns:
            year_columns[year] = column
            
    if not year_columns: return pd.DataFrame(), pd.DataFrame(), []
    
    source["WARD"] = _clean_series(source[ward_column])
    source = source[_valid_text(source["WARD"])].copy()
    total_values = {"TOTAL", "GRAND TOTAL", "MUMBAI TOTAL", "ALL"}
    source = source[~source["WARD"].str.upper().isin(total_values)].copy()
    available_years = sorted(year_columns.keys())
    
    wide_data = {"WARD": source["WARD"]}
    for year in available_years:
        wide_data[str(year)] = _safe_numeric(source[year_columns[year]])
        
    population_wide = pd.DataFrame(wide_data)
    numeric_columns = [str(year) for year in available_years]
    population_wide = population_wide.groupby("WARD", as_index=False)[numeric_columns].sum(min_count=1)
    
    population_long = population_wide.melt(id_vars=["WARD"], value_vars=numeric_columns, var_name="Population_Year", value_name="Population")
    population_long["Population_Year"] = pd.to_numeric(population_long["Population_Year"], errors="coerce")
    population_long["Population"] = pd.to_numeric(population_long["Population"], errors="coerce")
    population_long = population_long[population_long["Population_Year"].notna()].copy()
    population_long["Population_Year"] = population_long["Population_Year"].astype(int)
    population_long.loc[population_long["Population"] <= 0, "Population"] = np.nan
    return population_wide, population_long, available_years

# ============================================================
# POPULATION MATCHING
# ============================================================

def _population_for_ward_year(population_long, ward, analysis_year):
    if population_long is None or population_long.empty: return np.nan, None, "Population unavailable"
    ward_text = str(ward).strip()
    try: analysis_year = int(analysis_year)
    except Exception: return np.nan, None, "Invalid analysis year"
    
    data = population_long[_clean_series(population_long["WARD"]) == ward_text].copy()
    data = data[data["Population"].notna() & data["Population"].gt(0)]
    if data.empty: return np.nan, None, "Population unavailable"
    
    exact = data[data["Population_Year"] == analysis_year]
    if not exact.empty:
        row = exact.iloc[0]
        return float(row["Population"]), int(row["Population_Year"]), "Exact year"
        
    previous = data[data["Population_Year"] < analysis_year]
    if not previous.empty:
        selected_year = int(previous["Population_Year"].max())
        row = previous[previous["Population_Year"] == selected_year].iloc[0]
        return float(row["Population"]), selected_year, "Previous-year fallback"
        
    future = data[data["Population_Year"] > analysis_year]
    if not future.empty:
        selected_year = int(future["Population_Year"].min())
        row = future[future["Population_Year"] == selected_year].iloc[0]
        return float(row["Population"]), selected_year, "Future-year fallback"
        
    return np.nan, None, "Population unavailable"

# ============================================================
# INCIDENCE TABLES
# ============================================================

def _build_ward_year_incidence(case_df, population_long, denominator):
    if case_df is None or case_df.empty or "Ward Name" not in case_df.columns: return pd.DataFrame()
    temp = case_df[_valid_text(case_df["Ward Name"])].copy()
    if temp.empty: return pd.DataFrame()
    
    grouped = temp.groupby(["Ward Name", "Analysis_Year"], observed=True).size().reset_index(name="Cases")
    rows = []
    for _, row in grouped.iterrows():
        population, year_used, status = _population_for_ward_year(population_long, row["Ward Name"], row["Analysis_Year"])
        rate = np.nan
        if pd.notna(population) and population > 0: rate = row["Cases"] / population * denominator
        rows.append({
            "Ward": row["Ward Name"], "Year": int(row["Analysis_Year"]), "Cases": int(row["Cases"]),
            "Population": population, "Population Year Used": year_used, "Population Match Status": status,
            "Incidence Rate": (round(rate, 2) if pd.notna(rate) else np.nan),
        })
    return pd.DataFrame(rows)

def _build_disease_ward_year_incidence(case_df, population_long, denominator):
    required = {"Ward Name", "Disease", "Analysis_Year"}
    if case_df is None or case_df.empty or not required.issubset(case_df.columns): return pd.DataFrame()
    temp = case_df[_valid_text(case_df["Ward Name"]) & _valid_text(case_df["Disease"])].copy()
    if temp.empty: return pd.DataFrame()
    
    grouped = temp.groupby(["Ward Name", "Disease", "Analysis_Year"], observed=True).size().reset_index(name="Cases")
    rows = []
    for _, row in grouped.iterrows():
        population, year_used, status = _population_for_ward_year(population_long, row["Ward Name"], row["Analysis_Year"])
        rate = np.nan
        if pd.notna(population) and population > 0: rate = row["Cases"] / population * denominator
        rows.append({
            "Ward": row["Ward Name"], "Disease": row["Disease"], "Year": int(row["Analysis_Year"]), "Cases": int(row["Cases"]),
            "Population": population, "Population Year Used": year_used, "Population Match Status": status,
            "Incidence Rate": (round(rate, 2) if pd.notna(rate) else np.nan),
        })
    return pd.DataFrame(rows)

def _build_monthly_disease_ward_incidence(case_df, population_long, denominator):
    required = {"Ward Name", "Disease", "Analysis_Year", "Analysis_Month"}
    if case_df is None or case_df.empty or not required.issubset(case_df.columns): return pd.DataFrame()
    temp = case_df[case_df["Analysis_Month"].between(1, 12) & _valid_text(case_df["Ward Name"]) & _valid_text(case_df["Disease"])].copy()
    if temp.empty: return pd.DataFrame()
    
    grouped = temp.groupby(["Ward Name", "Disease", "Analysis_Year", "Analysis_Month"], observed=True).size().reset_index(name="Cases")
    rows = []
    for _, row in grouped.iterrows():
        population, year_used, status = _population_for_ward_year(population_long, row["Ward Name"], row["Analysis_Year"])
        rate = np.nan
        if pd.notna(population) and population > 0: rate = row["Cases"] / population * denominator
        year, month = int(row["Analysis_Year"]), int(row["Analysis_Month"])
        date_value = pd.Timestamp(year, month, 1)
        rows.append({
            "Ward": row["Ward Name"], "Disease": row["Disease"], "Year": year, "Month": month,
            "Date": date_value, "Period": date_value.strftime("%b-%Y"), "Cases": int(row["Cases"]),
            "Population": population, "Population Year Used": year_used, "Population Match Status": status,
            "Incidence Rate": (round(rate, 2) if pd.notna(rate) else np.nan),
        })
    return pd.DataFrame(rows)

def _build_monthly_ward_incidence(case_df, population_long, denominator):
    required = {"Ward Name", "Analysis_Year", "Analysis_Month"}
    if case_df is None or case_df.empty or not required.issubset(case_df.columns): return pd.DataFrame()
    temp = case_df[case_df["Analysis_Month"].between(1, 12) & _valid_text(case_df["Ward Name"])].copy()
    if temp.empty: return pd.DataFrame()
    
    grouped = temp.groupby(["Ward Name", "Analysis_Year", "Analysis_Month"], observed=True).size().reset_index(name="Cases")
    rows = []
    for _, row in grouped.iterrows():
        population, year_used, status = _population_for_ward_year(population_long, row["Ward Name"], row["Analysis_Year"])
        rate = np.nan
        if pd.notna(population) and population > 0: rate = row["Cases"] / population * denominator
        year, month = int(row["Analysis_Year"]), int(row["Analysis_Month"])
        date_value = pd.Timestamp(year, month, 1)
        rows.append({
            "Ward": row["Ward Name"], "Year": year, "Month": month, "Date": date_value, "Period": date_value.strftime("%b-%Y"),
            "Cases": int(row["Cases"]), "Population": population, "Population Year Used": year_used,
            "Population Match Status": status, "Incidence Rate": (round(rate, 2) if pd.notna(rate) else np.nan),
        })
    result = pd.DataFrame(rows)
    if result.empty: return result
    return result.sort_values(["Date", "Ward"]).reset_index(drop=True)

def _aggregate_monthly_incidence(monthly_source, denominator):
    required = {"Date", "Period", "Cases", "Population"}
    if monthly_source is None or monthly_source.empty or not required.issubset(monthly_source.columns): return pd.DataFrame()
    valid = monthly_source[monthly_source["Population"].notna() & monthly_source["Population"].gt(0)].copy()
    if valid.empty: return pd.DataFrame()
    result = valid.groupby(["Date", "Period"], as_index=False).agg(Cases=("Cases", "sum"), Population=("Population", "sum")).sort_values("Date").reset_index(drop=True)
    result["Cases"] = result["Cases"].astype(int)
    result["Incidence Rate"] = (result["Cases"] / result["Population"] * denominator).round(2)
    return result

def _aggregate_year_incidence(ward_incidence, denominator):
    if ward_incidence is None or ward_incidence.empty: return pd.DataFrame()
    rows = []
    for year, group in ward_incidence.groupby("Year", observed=True):
        valid = group[group["Population"].notna() & group["Population"].gt(0)]
        if valid.empty: continue
        cases, population = int(valid["Cases"].sum()), float(valid["Population"].sum())
        rate = cases / population * denominator
        rows.append({"Year": int(year), "Cases": cases, "Population": population, "Incidence Rate": round(rate, 2)})
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Year").reset_index(drop=True)

@st.cache_data(ttl=1800, show_spinner=False)
def _build_incidence_bundle(case_df, population_long, denominator):
    ward_incidence = _build_ward_year_incidence(case_df, population_long, denominator)
    disease_ward_incidence = _build_disease_ward_year_incidence(case_df, population_long, denominator)
    monthly_incidence = _build_monthly_ward_incidence(case_df, population_long, denominator)
    monthly_disease_incidence = _build_monthly_disease_ward_incidence(case_df, population_long, denominator)
    yearly_incidence = _aggregate_year_incidence(ward_incidence, denominator)
    audit = _population_audit(case_df, population_long)
    return ward_incidence, disease_ward_incidence, monthly_incidence, monthly_disease_incidence, yearly_incidence, audit

# ============================================================
# LEGEND & CHART CONFIGURATION
# ============================================================

def _legend_columns(series_count):
    series_count = max(1, int(series_count or 1))
    if series_count == 1: return 1
    return max(2, math.ceil(series_count / 2))

def _legend(series_count, title=None):
    return alt.Legend(title=title, orient="bottom", direction="horizontal", columns=_legend_columns(series_count), labelFontSize=9, titleFontSize=10, symbolSize=65, labelLimit=180, columnPadding=12, rowPadding=6, padding=8)

def _finalize_chart(chart, series_count=1):
    return chart.configure_legend(orient="bottom", direction="horizontal", columns=_legend_columns(max(1, series_count)), labelFontSize=9, titleFontSize=10, symbolSize=65, labelLimit=180, columnPadding=12, rowPadding=6, padding=8, offset=8).configure_title(anchor="start", fontSize=16, subtitleFontSize=11, subtitlePadding=6).configure_view(stroke=None)

# ============================================================
# BAR CHART
# ============================================================

def _render_bar_chart(dataframe, x_column, y_column, title, y_title, height=430):
    if dataframe is None or dataframe.empty or x_column not in dataframe.columns or y_column not in dataframe.columns: return
    chart_df = dataframe[dataframe[y_column].notna()].copy()
    if chart_df.empty: return
    chart_df[x_column] = chart_df[x_column].astype(str)
    order = chart_df[x_column].drop_duplicates().tolist()
    color_range = [COLORS[index % len(COLORS)] for index in range(len(order))]
    scale = alt.Scale(domain=order, range=color_range)
    
    bars = (
        alt.Chart(chart_df).mark_bar()
        .encode(
            x=alt.X(f"{x_column}:N", sort=order, axis=alt.Axis(title=x_column, labelAngle=-45, labelLimit=180)),
            y=alt.Y(f"{y_column}:Q", axis=alt.Axis(title=y_title)),
            color=alt.Color(f"{x_column}:N", scale=scale, legend=_legend(len(order), x_column)),
            tooltip=[alt.Tooltip(f"{x_column}:N", title=x_column), alt.Tooltip(f"{y_column}:Q", title=y_title, format=",.2f")],
        )
        .properties(height=height, title=_chart_title(title, x_column, y_title))
    )
    
    chart = bars
    if data_labels_enabled():
        labels = (
            alt.Chart(chart_df).mark_text(dy=-8, fontSize=DATA_LABEL_FONT_SIZE, fontWeight="bold")
            .encode(x=alt.X(f"{x_column}:N", sort=order), y=alt.Y(f"{y_column}:Q"), text=alt.Text(f"{y_column}:Q", format=",.2f"), color=alt.Color(f"{x_column}:N", scale=scale, legend=None))
        )
        chart = bars + labels
        
    chart = _finalize_chart(chart, series_count=len(order))

    # --- Save Chart for Download Export ---
    if "export_charts" not in st.session_state: st.session_state["export_charts"] = {}
    st.session_state["export_charts"][title] = chart
    # --------------------------------------

    st.altair_chart(chart, use_container_width=True)

# ============================================================
# LINE CHART
# ============================================================

def _render_line_chart(dataframe, x_column, series_column, value_column, title, y_title, height=450):
    required = {x_column, series_column, value_column}
    if dataframe is None or dataframe.empty or not required.issubset(dataframe.columns): return
    chart_df = dataframe[dataframe[value_column].notna()].copy()
    if chart_df.empty: return
    
    series_order = chart_df[series_column].astype(str).drop_duplicates().tolist()
    color_range = [COLORS[index % len(COLORS)] for index in range(len(series_order))]
    scale = alt.Scale(domain=series_order, range=color_range)
    
    lines = (
        alt.Chart(chart_df).mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X(f"{x_column}:N", sort=None, axis=alt.Axis(title=x_column, labelAngle=-45, labelLimit=150)),
            y=alt.Y(f"{value_column}:Q", axis=alt.Axis(title=y_title)),
            color=alt.Color(f"{series_column}:N", sort=series_order, scale=scale, legend=_legend(len(series_order), series_column)),
            tooltip=[alt.Tooltip(f"{x_column}:N", title=x_column), alt.Tooltip(f"{series_column}:N", title=series_column), alt.Tooltip(f"{value_column}:Q", title=y_title, format=",.2f")],
        )
        .properties(height=height, title=_chart_title(title, x_column, y_title))
    )
    
    chart = lines
    if data_labels_enabled():
        labels = (
            alt.Chart(chart_df).mark_text(dy=-9, fontSize=DATA_LABEL_FONT_SIZE, fontWeight="bold")
            .encode(x=alt.X(f"{x_column}:N", sort=None), y=alt.Y(f"{value_column}:Q"), text=alt.Text(f"{value_column}:Q", format=",.2f"), color=alt.Color(f"{series_column}:N", scale=scale, legend=None))
        )
        chart = lines + labels
        
    chart = _finalize_chart(chart, series_count=len(series_order))

    # --- Save Chart for Download Export ---
    if "export_charts" not in st.session_state: st.session_state["export_charts"] = {}
    st.session_state["export_charts"][title] = chart
    # --------------------------------------

    st.altair_chart(chart, use_container_width=True)

# ============================================================
# OBSERVATIONS & METHODOLOGY
# ============================================================

def _observation_box(text):
    if text: st.info(f"📌 **Chart Observation:** {text}")

def _bar_observation(dataframe, category, value, unit):
    if dataframe is None or dataframe.empty or category not in dataframe.columns or value not in dataframe.columns: return None
    valid = dataframe[dataframe[value].notna()].copy()
    if valid.empty: return None
    highest = valid.loc[valid[value].idxmax()]
    lowest = valid.loc[valid[value].idxmin()]
    if len(valid) == 1: return f"{highest[category]} recorded {_format_number(highest[value], 2)} {unit}."
    return f"The highest value is observed for {highest[category]} ({_format_number(highest[value], 2)} {unit}), while the lowest among the displayed categories is {lowest[category]} ({_format_number(lowest[value], 2)} {unit})."

def _trend_observation(dataframe, period_column, value_column):
    if dataframe is None or dataframe.empty or value_column not in dataframe.columns: return None
    valid = dataframe[dataframe[value_column].notna()].copy()
    if valid.empty: return None
    peak, first, last = valid.loc[valid[value_column].idxmax()], valid.iloc[0], valid.iloc[-1]
    first_value, last_value = float(first[value_column]), float(last[value_column])
    direction = "higher" if last_value > first_value else "lower" if last_value < first_value else "the same"
    return f"The highest displayed value occurs in {peak[period_column]} ({_format_number(peak[value_column], 2)}). The last displayed value is {direction} than the first displayed value."

def _methodology_expander(title, lines):
    with st.expander(f"ℹ️ Methodology — {title}", expanded=False):
        for line in lines: st.markdown(f"- {line}")

# ============================================================
# STATISTICAL FUNCTIONS
# ============================================================

def _apply_baseline(source, baseline):
    if source is None or source.empty: return source
    years = sorted(source["Analysis_Year"].dropna().astype(int).unique().tolist())
    if not years: return source
    mapping = {"Last 2 Years": 2, "Last 3 Years": 3, "Last 5 Years": 5}
    if baseline == "All Available Years": return source.copy()
    count = mapping.get(baseline)
    if count is None: return source.copy()
    selected_years = years[-count:]
    return source[source["Analysis_Year"].isin(selected_years)].copy()

def _monthly_case_series(source):
    if source is None or source.empty: return pd.DataFrame()
    required = {"Analysis_Year", "Analysis_Month"}
    if not required.issubset(source.columns): return pd.DataFrame()
    temp = source[source["Analysis_Month"].between(1, 12)].copy()
    if temp.empty: return pd.DataFrame()
    monthly = temp.groupby(["Analysis_Year", "Analysis_Month"], observed=True).size().reset_index(name="Cases")
    monthly["Date"] = pd.to_datetime(dict(year=monthly["Analysis_Year"].astype(int), month=monthly["Analysis_Month"].astype(int), day=1))
    complete_dates = pd.date_range(monthly["Date"].min(), monthly["Date"].max(), freq="MS")
    complete = pd.DataFrame({"Date": complete_dates})
    complete["Analysis_Year"] = complete["Date"].dt.year
    complete["Analysis_Month"] = complete["Date"].dt.month
    complete = complete.merge(monthly[["Analysis_Year", "Analysis_Month", "Cases"]], how="left", on=["Analysis_Year", "Analysis_Month"])
    complete["Cases"] = complete["Cases"].fillna(0).astype(int)
    complete["Period"] = complete["Date"].dt.strftime("%b-%Y")
    return complete

def _threshold_statistics(monthly):
    if monthly is None or monthly.empty: return None
    values = pd.to_numeric(monthly["Cases"], errors="coerce").dropna()
    if values.empty: return None
    mean = float(values.mean())
    sd = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    return {"Mean": mean, "SD": sd, "Mean + 1 SD": mean + sd, "Mean + 2 SD": mean + (2 * sd), "Mean + 3 SD": mean + (3 * sd)}

def _render_threshold_chart(monthly, statistics, title):
    if monthly is None or monthly.empty or statistics is None: return
    chart_df = monthly[["Period", "Cases"]].copy()
    for key in ["Mean", "Mean + 1 SD", "Mean + 2 SD", "Mean + 3 SD"]: chart_df[key] = statistics[key]
    long_df = chart_df.melt(id_vars=["Period"], value_vars=["Cases", "Mean", "Mean + 1 SD", "Mean + 2 SD", "Mean + 3 SD"], var_name="Series", value_name="Value")
    series_order = ["Cases", "Mean", "Mean + 1 SD", "Mean + 2 SD", "Mean + 3 SD"]
    scale = alt.Scale(domain=series_order, range=["#1F77B4", "#2CA02C", "#FFBF00", "#FF7F0E", "#D62728"])
    
    chart = (
        alt.Chart(long_df).mark_line(strokeWidth=3)
        .encode(
            x=alt.X("Period:N", sort=None, axis=alt.Axis(title="Period", labelAngle=-45, labelLimit=140)),
            y=alt.Y("Value:Q", title="Monthly Cases"),
            color=alt.Color("Series:N", sort=series_order, scale=scale, legend=_legend(len(series_order), "Statistical Series")),
            tooltip=[alt.Tooltip("Period:N", title="Period"), alt.Tooltip("Series:N", title="Series"), alt.Tooltip("Value:Q", title="Value", format=",.2f")],
        )
        .properties(height=460, title=_chart_title(title, "Period", "Monthly Cases", "Observed monthly cases compared with Mean and SD thresholds."))
    )
    case_points = long_df[long_df["Series"] == "Cases"]
    points = alt.Chart(case_points).mark_point(filled=True, size=70).encode(x=alt.X("Period:N", sort=None), y="Value:Q", color=alt.Color("Series:N", scale=scale, legend=None))
    chart = chart + points
    
    if data_labels_enabled():
        case_labels = alt.Chart(case_points).mark_text(dy=-10, fontSize=DATA_LABEL_FONT_SIZE, fontWeight="bold").encode(x=alt.X("Period:N", sort=None), y=alt.Y("Value:Q"), text=alt.Text("Value:Q", format=",.1f"), color=alt.Color("Series:N", scale=scale, legend=None))
        chart = chart + case_labels
        
    latest_period = chart_df["Period"].iloc[-1]
    latest_labels = pd.DataFrame({
        "Period": [latest_period] * len(series_order),
        "Series": series_order,
        "Value": [statistics.get(series, chart_df.loc[chart_df["Period"] == latest_period, "Cases"].iloc[0]) if series != "Cases" else chart_df.loc[chart_df["Period"] == latest_period, "Cases"].iloc[0] for series in series_order],
    })
    latest_labels["Label"] = latest_labels.apply(lambda row: (f"Observed = {row['Value']:,.1f}" if row["Series"] == "Cases" else f"{row['Series']} = {row['Value']:,.1f}"), axis=1)
    line_labels = alt.Chart(latest_labels).mark_text(align="left", dx=8, fontSize=10, fontWeight="bold").encode(x=alt.X("Period:N", sort=None), y=alt.Y("Value:Q"), text=alt.Text("Label:N"), color=alt.Color("Series:N", scale=scale, legend=None))
    
    chart = chart + line_labels
    chart = _finalize_chart(chart, series_count=len(series_order))

    # --- Save Chart for Download Export ---
    if "export_charts" not in st.session_state: st.session_state["export_charts"] = {}
    st.session_state["export_charts"][title] = chart
    # --------------------------------------

    st.caption("How to read this chart: blue line = observed cases; green = Mean; yellow/orange/red = Mean + 1/2/3 SD. These are statistical signals, not outbreak confirmation.")
    st.altair_chart(chart, use_container_width=True)

def _threshold_observation(monthly, statistics):
    if monthly is None or monthly.empty or statistics is None: return None
    latest = monthly.iloc[-1]
    latest_cases = float(latest["Cases"])
    status = "above the Mean + 3 SD statistical level" if latest_cases > statistics["Mean + 3 SD"] else "above the Mean + 2 SD statistical level" if latest_cases > statistics["Mean + 2 SD"] else "above the Mean + 1 SD statistical level" if latest_cases > statistics["Mean + 1 SD"] else "within or below the Mean + 1 SD statistical level"
    peak = monthly.loc[monthly["Cases"].idxmax()]
    return f"The latest period ({latest['Period']}) recorded {int(latest_cases):,} cases and is {status}. The highest monthly count in the displayed baseline was {int(peak['Cases']):,} cases in {peak['Period']}. These are descriptive statistical signals and do not independently confirm an outbreak."

def _population_audit(case_df, population_long):
    if case_df is None or case_df.empty or "Ward Name" not in case_df.columns: return pd.DataFrame()
    combinations = case_df[["Ward Name", "Analysis_Year"]].copy()
    combinations = combinations[_valid_text(combinations["Ward Name"])].drop_duplicates().sort_values(["Analysis_Year", "Ward Name"])
    rows = []
    for _, row in combinations.iterrows():
        population, year_used, status = _population_for_ward_year(population_long, row["Ward Name"], row["Analysis_Year"])
        rows.append({"Ward": row["Ward Name"], "Analysis Year": int(row["Analysis_Year"]), "Population": population, "Population Year Used": year_used, "Status": status})
    return pd.DataFrame(rows)

# ============================================================
# MAIN INCIDENCE PAGE
# ============================================================

def render_incidence_analysis(df):
    # CLEARS EXPORT CHARTS ON EVERY NEW RENDER TO AVOID OLD CHARTS IN PDF
    st.session_state["export_charts"] = {}
    
    st.subheader("📐 Incidence & Statistical Surveillance")
    st.caption("This section answers three management questions: 1) What is the disease burden relative to population? 2) Where and when is incidence higher? 3) Are recent monthly case counts above the historical descriptive statistical baseline?")

    if df is None or df.empty:
        st.warning("No records are available for the selected filters.")
        return

    case_df = _prepare_case_data(df)
    if case_df.empty:
        st.warning("Valid year information is required for incidence analysis.")
        return

    population_error = None
    try:
        population_raw = _load_population_raw()
        population_wide, population_long, population_years = _prepare_population_data(population_raw)
    except Exception as error:
        population_error = error
        population_wide = pd.DataFrame()
        population_long = pd.DataFrame()
        population_years = []

    # --- 1. OVERVIEW ---
    st.markdown("### 1. 📊 Population & Incidence Overview")
    st.info("Purpose: Incidence does not simply count cases. It relates the number of cases to the population of the corresponding ward. This allows wards of different population sizes to be compared on a common rate scale.")

    denominator_label = _single_select("Incidence Rate Denominator", ["Per 1,000", "Per 10,000", "Per 100,000", "Per 1,000,000"], default="Per 100,000", key="phase8b_denom_state")
    denominator_map = {"Per 1,000": 1_000, "Per 10,000": 10_000, "Per 100,000": 100_000, "Per 1,000,000": 1_000_000}
    denominator = denominator_map.get(denominator_label, DEFAULT_DENOMINATOR)

    st.caption(f"Selected denominator: {denominator_label}. Formula = Cases ÷ Population × {denominator:,}.")

    case_years = sorted(case_df["Analysis_Year"].unique().tolist())
    population_wards = population_long["WARD"].nunique() if not population_long.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Filtered Records", f"{len(case_df):,}")
    with c2: st.metric("Case Years", f"{len(case_years):,}")
    with c3: st.metric("Population Wards", f"{population_wards:,}")
    with c4: st.metric("Latest Population Year", str(max(population_years)) if population_years else "Unavailable")

    if population_error is not None:
        st.error("Population data could not be loaded from the Population worksheet.")
        with st.expander("Technical Details", expanded=False): st.code(str(population_error))
    elif population_long.empty:
        st.warning("No valid population data or population-year columns were detected.")
    else:
        st.success(f"Population dataset loaded successfully. Detected years: {', '.join(str(x) for x in population_years)}")
        with st.expander("📋 View Complete Population Dataset", expanded=False):
            st.dataframe(population_wide, use_container_width=True, hide_index=True)

    _methodology_expander("Population & Incidence Overview", ["Incidence Rate = Cases ÷ Population × selected denominator.", "The default denominator is 100,000 population.", "Population year columns are detected automatically.", "Population data is read from the configured Google Sheet."])

    if population_long.empty: return

    ward_incidence, disease_ward_incidence, monthly_incidence, monthly_disease_incidence, yearly_incidence, audit = _build_incidence_bundle(case_df, population_long, denominator)

    # --- 2. POPULATION TREND ---
    st.divider()
    st.markdown("### 2. 👥 Population Trend & Matching Quality")
    st.caption("This section checks the denominator used in incidence calculation. First view the population trend, then use the audit to confirm whether the case year had an exact population value or required a fallback.")

    population_tab, audit_tab = st.tabs(["📈 Population Trend", "🔍 Population Matching Audit"])
    with population_tab:
        wards = _alphabetical(population_long["WARD"].unique())
        selected_wards = _compact_multiselect("Select Ward(s)", wards, default=wards[:min(5, len(wards))], key="phase8b_pop_wards_state", reset_button_key="phase8b_pop_wards_reset_v2", defer=True)
        st.caption("Tick one or more wards. The chart compares population size over the available population years.")

        if selected_wards:
            chart_df = population_long[population_long["WARD"].isin(selected_wards)].copy()
            chart_df = chart_df.sort_values(["Population_Year", "WARD"])
            chart_df["Year"] = chart_df["Population_Year"].astype(int).astype(str)
            _render_line_chart(chart_df, "Year", "WARD", "Population", "Ward-wise Population Trend", "Population", height=450)

            if not chart_df.empty:
                latest_year = int(chart_df["Population_Year"].max())
                latest_data = chart_df[chart_df["Population_Year"] == latest_year]
                if not latest_data.empty:
                    top = latest_data.loc[latest_data["Population"].idxmax()]
                    _observation_box(f"For {latest_year}, the highest population among selected wards is {top['WARD']} ({_format_number(top['Population'])}).")
            with st.expander("📋 View Population Trend Data", expanded=False): st.dataframe(chart_df[["WARD", "Population_Year", "Population"]], use_container_width=True, hide_index=True)
        else:
            st.info("Select at least one ward.")
        _methodology_expander("Population Trend", ["Population values are read directly from the Population worksheet.", "Detected population years are displayed chronologically.", "Ward selection changes only the displayed trend."])

    with audit_tab:
        if not audit.empty:
            exact_count = int((audit["Status"] == "Exact year").sum())
            previous_count = int((audit["Status"] == "Previous-year fallback").sum())
            future_count = int((audit["Status"] == "Future-year fallback").sum())
            unavailable_count = int((audit["Status"] == "Population unavailable").sum())
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Exact Matches", f"{exact_count:,}")
            with c2: st.metric("Previous-Year Fallback", f"{previous_count:,}")
            with c3: st.metric("Future-Year Fallback", f"{future_count:,}")
            with c4: st.metric("Unavailable", f"{unavailable_count:,}")
            total_matches = len(audit)
            if total_matches:
                exact_percent = exact_count / total_matches * 100
                _observation_box(f"{exact_percent:.1f}% of Ward × Year population matches use the exact population year.")
            st.dataframe(audit, use_container_width=True, hide_index=True)
        _methodology_expander("Population Matching", ["Exact Ward × Year population is used whenever available.", "Previous-year population is used when the exact year is unavailable.", "Future-year population is used only when no previous year exists.", "Fallback status is retained in the audit table."])

    # --- 3. WARD-WISE INCIDENCE ---
    st.divider()
    st.markdown("### 3. 📍 Ward-wise Incidence Analysis")
    st.info("Purpose: Identify which selected wards have higher or lower population-adjusted disease incidence for the selected year. A higher rate means more cases relative to the ward population; it is not simply a higher case count.")

    if not ward_incidence.empty:
        available_years = sorted(ward_incidence["Year"].unique())
        selected_year = _smart_year_slider("Select Analysis Year", available_years, default=available_years[-1], key="phase8b_ward_year_slider_state")

        if selected_year is not None:
            year_df = ward_incidence[ward_incidence["Year"] == selected_year].copy()
            ward_options = _alphabetical(year_df["Ward"].unique())
            selected_ward_analysis = _compact_multiselect("Select Ward(s)", ward_options, default=ward_options, key="phase8b_ward_sel_state", reset_button_key="phase8b_ward_sel_reset_v2", defer=True)
            st.caption("Tick the wards you want to compare. The bars are incidence rates, not raw case counts.")

            if selected_ward_analysis:
                display_df = year_df[year_df["Ward"].isin(selected_ward_analysis)].copy()
                display_df = display_df.sort_values("Incidence Rate", ascending=False, na_position="last")
                _render_bar_chart(display_df, "Ward", "Incidence Rate", f"Ward-wise Incidence Rate — {selected_year}", f"Incidence per {denominator:,}", height=460)
                _observation_box(_bar_observation(display_df, "Ward", "Incidence Rate", f"cases per {denominator:,} population"))
                with st.expander("📋 View Ward-wise Incidence Data", expanded=False): st.dataframe(display_df[["Ward", "Year", "Cases", "Population", "Population Year Used", "Population Match Status", "Incidence Rate"]], use_container_width=True, hide_index=True)

                if not disease_ward_incidence.empty:
                    st.markdown("#### 🦠 Disease Profile within Selected Ward(s)")
                    ward_disease = disease_ward_incidence[(disease_ward_incidence["Year"] == selected_year) & (disease_ward_incidence["Ward"].isin(selected_ward_analysis))].copy()
                    if not ward_disease.empty:
                        ward_disease["Ward | Disease"] = ward_disease["Ward"] + " | " + ward_disease["Disease"]
                        top_ward_disease = ward_disease.sort_values("Incidence Rate", ascending=False).head(20)
                        _render_bar_chart(top_ward_disease, "Ward | Disease", "Incidence Rate", "Disease-specific Incidence within Selected Ward(s)", f"Incidence per {denominator:,}", height=500)
                        _observation_box(_bar_observation(top_ward_disease, "Ward | Disease", "Incidence Rate", f"cases per {denominator:,} population"))

    _methodology_expander("Ward-wise Incidence", ["Cases are grouped by Ward and Analysis Year.", "Each ward uses its matched population denominator.", f"The incidence rate is expressed per {denominator:,} population.", "Population fallback status is retained for transparency."])

    # --- 4. DISEASE-WISE INCIDENCE ---
    st.divider()
    st.markdown("### 4. 🦠 Disease-wise Incidence Analysis")
    st.info("Purpose: Compare diseases using population-adjusted incidence rather than simply comparing the number of reported cases. The second chart shows where the selected disease(s) are distributed across selected wards.")

    if not disease_ward_incidence.empty:
        disease_years = sorted(disease_ward_incidence["Year"].unique())
        disease_year = _smart_year_slider("Disease Analysis Year", disease_years, default=disease_years[-1], key="phase8b_disease_year_slider_state")

        if disease_year is not None:
            disease_source = disease_ward_incidence[disease_ward_incidence["Year"] == disease_year].copy()
            disease_options = disease_source["Disease"].value_counts().index.tolist()
            selected_diseases = _compact_multiselect("Select Disease(s)", disease_options, default=disease_options[:min(8, len(disease_options))], key="phase8b_disease_sel_state", reset_button_key="phase8b_disease_sel_reset_v2", defer=True)
            st.caption("Tick the disease(s) you want to study. The chart ranks their population-adjusted incidence.")

            if selected_diseases:
                selected_source = disease_source[disease_source["Disease"].isin(selected_diseases)].copy()
                summary_rows = []
                for disease, group in selected_source.groupby("Disease", observed=True):
                    valid = group[group["Population"].notna() & group["Population"].gt(0)]
                    if valid.empty: continue
                    cases, population = int(valid["Cases"].sum()), float(valid["Population"].sum())
                    summary_rows.append({"Disease": disease, "Cases": cases, "Population": population, "Incidence Rate": round((cases / population * denominator), 2)})
                disease_summary = pd.DataFrame(summary_rows)
                if not disease_summary.empty:
                    disease_summary = disease_summary.sort_values("Incidence Rate", ascending=False)
                    _render_bar_chart(disease_summary, "Disease", "Incidence Rate", f"Disease-wise Incidence — {disease_year}", f"Incidence per {denominator:,}", height=450)
                    _observation_box(_bar_observation(disease_summary, "Disease", "Incidence Rate", f"cases per {denominator:,} population"))
                    with st.expander("📋 View Disease-wise Incidence Data", expanded=False): st.dataframe(disease_summary, use_container_width=True, hide_index=True)

                st.markdown("#### 📍 Ward-wise Distribution of Selected Disease(s)")
                disease_ward_options = _alphabetical(selected_source["Ward"].unique())
                selected_disease_wards = _compact_multiselect("Select Ward(s) for Disease Comparison", disease_ward_options, default=disease_ward_options[:min(8, len(disease_ward_options))], key="phase8b_dis_ward_sel_state", reset_button_key="phase8b_dis_ward_sel_reset_v2", defer=True)
                if selected_disease_wards:
                    ward_disease_df = selected_source[selected_source["Ward"].isin(selected_disease_wards)].copy()
                    ward_disease_df["Ward | Disease"] = ward_disease_df["Ward"] + " | " + ward_disease_df["Disease"]
                    ward_disease_df = ward_disease_df.sort_values("Incidence Rate", ascending=False)
                    _render_bar_chart(ward_disease_df, "Ward | Disease", "Incidence Rate", "Ward-wise Disease Incidence Comparison", f"Incidence per {denominator:,}", height=500)
                    _observation_box(_bar_observation(ward_disease_df, "Ward | Disease", "Incidence Rate", f"cases per {denominator:,} population"))
                    with st.expander("📋 View Ward × Disease Data", expanded=False): st.dataframe(ward_disease_df[["Ward", "Disease", "Year", "Cases", "Population", "Population Year Used", "Population Match Status", "Incidence Rate"]], use_container_width=True, hide_index=True)

    _methodology_expander("Disease-wise Incidence", ["Disease-specific cases are grouped by Ward × Disease × Year.", "The corresponding ward population is used as denominator.", "The overall disease comparison uses summed valid ward cases and populations.", "The Ward-wise option shows geographic distribution of selected disease(s)."])

    # --- 5. INCIDENCE TRENDS ---
    st.divider()
    st.markdown("### 5. 📈 Incidence Trends")
    st.info("Purpose: Trends answer WHEN incidence is increasing, decreasing or fluctuating. Monthly trends show short-term changes, while the year-wise trend provides the broader long-term pattern.")
    st.info("**Incidence Rate Formula**\n\n**Incidence Rate = (Number of reported cases ÷ Population at risk) × Denominator**\n\n**Example:** 50 cases ÷ 100,000 population × 100,000 = **50 per 100,000 population**\n\n**Population denominator:** Ward-wise population is matched to the reporting year. Where exact-year population is unavailable, the existing previous/future-year fallback logic is used.")

    trend_disease_options = ["All Diseases"]
    if not monthly_disease_incidence.empty and "Disease" in monthly_disease_incidence.columns:
        trend_disease_options += _alphabetical(monthly_disease_incidence["Disease"].unique())

    selected_trend_disease = _single_select("Select Disease", trend_disease_options, default="All Diseases", key="phase8b_inc_trend_dis_state", reset_button_key="phase8b_inc_trend_dis_reset_v2")
    if selected_trend_disease is None: selected_trend_disease = "All Diseases"

    trend_basis = ("All diseases across all available wards; incidence is calculated " f"as valid reported cases ÷ matched population × {denominator:,}." if selected_trend_disease == "All Diseases" else f"Disease = {selected_trend_disease}; all available wards are included; incidence is calculated as valid reported cases ÷ matched population × {denominator:,}.")
    st.caption(f"✅ **Selected:** {selected_trend_disease} · The checked option is active; the chart below uses this selection.")
    st.info(f"**Chart basis:** {trend_basis}")

    monthly_tab, yearly_tab = st.tabs(["📅 Monthly Trend", "🗓️ Year-wise Trend"])
    with monthly_tab:
        if selected_trend_disease == "All Diseases":
            monthly_source, chart_title = monthly_incidence, "Monthly Overall Incidence Trend — All Diseases"
        else:
            monthly_source, chart_title = monthly_disease_incidence[monthly_disease_incidence["Disease"] == selected_trend_disease].copy(), f"Monthly Overall Incidence Trend — {selected_trend_disease}"
        
        monthly_chart = _aggregate_monthly_incidence(monthly_source, denominator)
        if not monthly_chart.empty:
            monthly_chart["Series"] = "All Diseases" if selected_trend_disease == "All Diseases" else selected_trend_disease
            _render_line_chart(monthly_chart, "Period", "Series", "Incidence Rate", chart_title, f"Incidence per {denominator:,}", height=480)
            _observation_box(_trend_observation(monthly_chart, "Period", "Incidence Rate"))
            with st.expander("📋 View Monthly Incidence Data", expanded=False): st.dataframe(monthly_chart[["Period", "Cases", "Population", "Incidence Rate"]], use_container_width=True, hide_index=True)
        else:
            st.info("Monthly incidence data is not available for the selected disease.")
        _methodology_expander("Monthly Incidence Trend", ["Monthly cases are grouped using the existing Ward × Year × Month incidence calculation.", "The matched annual ward population is retained as denominator for each ward-month.", "For the overall disease trend, valid ward cases and populations are summed before calculating the incidence rate.", "Disease selection changes only the displayed trend; the underlying incidence formula and population fallback logic are unchanged."])

    with yearly_tab:
        if selected_trend_disease == "All Diseases":
            chart_df, chart_title = yearly_incidence.copy(), "Year-wise Overall Incidence Trend — All Diseases"
        else:
            selected_disease_year = disease_ward_incidence[disease_ward_incidence["Disease"] == selected_trend_disease].copy()
            chart_df, chart_title = _aggregate_year_incidence(selected_disease_year, denominator), f"Year-wise Overall Incidence Trend — {selected_trend_disease}"
        
        if not chart_df.empty:
            chart_df["Year Label"] = chart_df["Year"].astype(str)
            chart_df["Series"] = "All Diseases" if selected_trend_disease == "All Diseases" else selected_trend_disease
            _render_line_chart(chart_df, "Year Label", "Series", "Incidence Rate", chart_title, f"Incidence per {denominator:,}", height=430)
            _observation_box(_trend_observation(chart_df, "Year Label", "Incidence Rate"))
            with st.expander("📋 View Year-wise Incidence Data", expanded=False): st.dataframe(chart_df[["Year", "Cases", "Population", "Incidence Rate"]], use_container_width=True, hide_index=True)
        else:
            st.info("Year-wise incidence data is not available for the selected disease.")
        _methodology_expander("Year-wise Incidence Trend", ["Ward-level cases and valid ward populations are aggregated by year.", "Overall yearly incidence uses total valid cases divided by total matched population.", "Individual ward incidence rates are not averaged to produce the overall rate.", "The selected disease follows the same aggregation rule as All Diseases."])

    # --- 6. STATISTICAL SURVEILLANCE ---
    st.divider()
    st.markdown("### 6. 📐 Statistical Surveillance Analysis")
    st.info("Purpose: This analysis compares monthly case counts with their historical mean and standard-deviation levels. It is useful for screening unusual increases in reporting volume, but a statistical threshold crossing alone does not establish an outbreak.")
    st.info("**Statistical Threshold Method**\n\n**Mean** = Average monthly cases\n\n**SD** = Standard Deviation of monthly cases\n\n**Mean + 1 SD** = routine variation reference\n\n**Mean + 2 SD** = increased surveillance signal\n\n**Mean + 3 SD** = stronger statistical signal\n\nThese thresholds are surveillance signals only and do not by themselves confirm an outbreak.")
    st.caption("Disease and Ward are independent native checkbox-style dropdowns. Each allows All or exactly one specific value at a time.")

    def _reset_statistical_defaults():
        st.session_state["phase8b_stat_baseline_state"] = ["All Available Years"]
        st.session_state["phase8b_stat_baseline_state__widget"] = ["All Available Years"]
        st.session_state["phase8b_stat_disease_state"] = ["All Diseases"]
        st.session_state["phase8b_stat_disease_state__widget"] = ["All Diseases"]
        st.session_state["phase8b_stat_ward_state"] = ["All Wards"]
        st.session_state["phase8b_stat_ward_state__widget"] = ["All Wards"]

    st.button("↺ Reset Statistical Selection to Default", key="phase8b_stat_all_reset_v5", on_click=_reset_statistical_defaults)

    baseline = _single_select("Statistical Baseline", ["All Available Years", "Last 2 Years", "Last 3 Years", "Last 5 Years"], default="All Available Years", key="phase8b_stat_baseline_state", reset_button_key="phase8b_stat_baseline_reset_v2")
    statistical_source = _apply_baseline(case_df, baseline)

    disease_options = ["All Diseases"]
    if "Disease" in statistical_source.columns: disease_options += _alphabetical(statistical_source[_valid_text(statistical_source["Disease"])]["Disease"].unique())

    ward_options = ["All Wards"]
    if "Ward Name" in statistical_source.columns: ward_options += _alphabetical(statistical_source[_valid_text(statistical_source["Ward Name"])]["Ward Name"].unique())

    stat_disease_col, stat_ward_col = st.columns(2)
    with stat_disease_col: selected_stat_disease = _single_select("Select Disease", disease_options, default="All Diseases", key="phase8b_stat_disease_state", reset_button_key="phase8b_stat_disease_reset_v4")
    with stat_ward_col: selected_stat_ward = _single_select("Select Ward", ward_options, default="All Wards", key="phase8b_stat_ward_state", reset_button_key="phase8b_stat_ward_reset_v4")

    if selected_stat_disease != "All Diseases" and "Disease" in statistical_source.columns: statistical_source = statistical_source[statistical_source["Disease"] == selected_stat_disease]
    if selected_stat_ward != "All Wards" and "Ward Name" in statistical_source.columns: statistical_source = statistical_source[statistical_source["Ward Name"] == selected_stat_ward]

    statistical_title = "Monthly Cases"
    stat_disease_basis = "All Diseases" if selected_stat_disease in (None, "All Diseases") else selected_stat_disease
    stat_ward_basis = "All Wards" if selected_stat_ward in (None, "All Wards") else selected_stat_ward

    st.info(f"**Chart basis:** Disease = {stat_disease_basis} · Ward = {stat_ward_basis} · Baseline = {baseline}. The graph shows monthly case counts for this exact selection; Mean and SD thresholds are calculated from the displayed monthly series.")

    if selected_stat_disease != "All Diseases": statistical_title += f" — {selected_stat_disease}"
    if selected_stat_ward != "All Wards": statistical_title += f" — Ward {selected_stat_ward}"

    monthly_stats = _monthly_case_series(statistical_source)
    statistics = _threshold_statistics(monthly_stats)

    if statistics is not None and not monthly_stats.empty:
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("Mean", f"{statistics['Mean']:,.2f}")
        with c2: st.metric("SD", f"{statistics['SD']:,.2f}")
        with c3: st.metric("Mean + 1 SD", f"{statistics['Mean + 1 SD']:,.2f}")
        with c4: st.metric("Mean + 2 SD", f"{statistics['Mean + 2 SD']:,.2f}")
        with c5: st.metric("Mean + 3 SD", f"{statistics['Mean + 3 SD']:,.2f}")

        _render_threshold_chart(monthly_stats, statistics, f"{statistical_title} — Statistical Surveillance")
        _observation_box(_threshold_observation(monthly_stats, statistics))

        threshold_table = pd.DataFrame({"Indicator": ["Mean", "Standard Deviation", "Mean + 1 SD", "Mean + 2 SD", "Mean + 3 SD"], "Value": [round(statistics["Mean"], 2), round(statistics["SD"], 2), round(statistics["Mean + 1 SD"], 2), round(statistics["Mean + 2 SD"], 2), round(statistics["Mean + 3 SD"], 2)]})
        with st.expander("📋 View Statistical Data", expanded=False):
            st.dataframe(monthly_stats[["Period", "Cases"]], use_container_width=True, hide_index=True)
            st.dataframe(threshold_table, use_container_width=True, hide_index=True)
    else:
        st.info("Sufficient monthly data is not available for this statistical analysis.")

    _methodology_expander("Statistical Surveillance", ["Monthly case counts are calculated for the selected disease and ward combination.", "Missing calendar months between the first and last available periods are included as zero.", "Mean is the arithmetic mean of monthly case counts.", "SD is the sample standard deviation.", "Mean + 1 SD, Mean + 2 SD and Mean + 3 SD are descriptive surveillance thresholds.", "Threshold crossing should be interpreted together with seasonality and reporting quality.", "Facility analysis is case-volume surveillance and is not presented as facility incidence."])

    # --- 7. METHODOLOGY & DATA QUALITY ---
    st.divider()
    st.markdown("### 7. ℹ️ Methodology, Interpretation & Data Quality")
    st.caption("Use this section when the dashboard is being used for formal programme review, reporting or interpretation. It documents how the incidence and statistical indicators were calculated.")

    methodology = pd.DataFrame({
        "Component": ["Incidence Formula", "Default Denominator", "Available Denominators", "Population Source", "Exact Population Match", "Missing Population Year", "Future Population Fallback", "Ward Incidence", "Disease Incidence", "Monthly Incidence", "Yearly Incidence", "Facility Analysis", "Statistical Mean", "Standard Deviation", "Mean + 1 SD", "Mean + 2 SD", "Mean + 3 SD", "Interpretation"],
        "Methodology": ["Cases ÷ Population × selected denominator", "100,000 population", "1,000; 10,000; 100,000; 1,000,000", "Population worksheet in the configured Google Sheet", "Exact Ward × Analysis Year population when available", "Closest previous available population year", "Nearest future population year when no previous year exists", "Ward cases divided by matched ward population", "Disease cases calculated using corresponding ward populations", "Monthly ward cases using matched annual ward population", "Valid ward cases and populations aggregated before calculating yearly rate", "Case-volume statistical surveillance only", "Arithmetic mean of monthly case counts", "Sample standard deviation", "Mean plus one standard deviation", "Mean plus two standard deviations", "Mean plus three standard deviations", "Results should be interpreted with data quality, seasonality and epidemiological context"]
    })
    st.dataframe(methodology, use_container_width=True, hide_index=True)
    st.warning("Incidence rates depend on the completeness and appropriateness of case and population data. Population fallback values should be reviewed before formal reporting. Statistical Mean/SD levels are descriptive surveillance indicators and do not by themselves establish or confirm an outbreak.")

    # ========================================================
    # 8. DOWNLOAD REPORTS (Excel, Word, PDF with CHARTS)
    # ========================================================
    st.divider()
    st.markdown("### 8. 📥 Download Reports & Data")
    st.caption("Generate a formatted report including data tables and all visible charts.")
    
    col1, col2 = st.columns(2)
    with col1:
        report_format = st.radio("Select Report Format:", ["Excel", "Word", "PDF"], horizontal=True)
    with col2:
        include_tables = st.radio("Include Data Tables?:", ["With Tables", "Without Tables (Summary Only)"], horizontal=True)
    
    # --------------------------------------------------------
    # EXCEL EXPORT
    # --------------------------------------------------------
    if report_format == "Excel":
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                pd.DataFrame({
                    "Metric": ["Total Records Analyzed", "Wards Analyzed", "Denominator Used"],
                    "Value": [len(case_df), population_wards, f"Per {denominator:,}"]
                }).to_excel(writer, sheet_name="Summary", index=False)
                
                if include_tables == "With Tables":
                    if not ward_incidence.empty: ward_incidence.to_excel(writer, sheet_name="Ward Incidence", index=False)
                    if not disease_ward_incidence.empty: disease_ward_incidence.to_excel(writer, sheet_name="Disease Incidence", index=False)
                    if not monthly_incidence.empty: monthly_incidence.to_excel(writer, sheet_name="Monthly Trend", index=False)
            
            st.download_button(label="📥 Download Excel Report", data=output.getvalue(), file_name="Incidence_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"Excel error: {e}")
            
    # --------------------------------------------------------
    # WORD (DOCX) EXPORT
    # --------------------------------------------------------
    elif report_format == "Word":
        try:
            from docx import Document
            from docx.shared import Inches
            doc = Document()
            doc.add_heading('Public Health Incidence & Surveillance Report', 0)
            doc.add_heading('Executive Summary', level=1)
            doc.add_paragraph(f"• Total Records Analyzed: {len(case_df):,}")
            doc.add_paragraph(f"• Denominator Used: Per {denominator:,} Population")
            
            if "export_charts" in st.session_state and st.session_state["export_charts"]:
                doc.add_heading('Visualizations', level=1)
                for chart_title, chart_obj in st.session_state["export_charts"].items():
                    doc.add_heading(chart_title, level=2)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        chart_obj.save(tmp.name, format="png", engine="vl-convert")
                        doc.add_picture(tmp.name, width=Inches(6.0))
            
            if include_tables == "With Tables" and not ward_incidence.empty:
                doc.add_heading('Ward Incidence Data (Top Records)', level=1)
                table = doc.add_table(rows=1, cols=3)
                table.style = 'Table Grid'
                hdr_cells = table.rows[0].cells
                hdr_cells[0].text, hdr_cells[1].text, hdr_cells[2].text = 'Ward', 'Cases', 'Incidence Rate'
                for _, row in ward_incidence.head(50).iterrows(): 
                    row_cells = table.add_row().cells
                    row_cells[0].text, row_cells[1].text, row_cells[2].text = str(row['Ward']), str(row['Cases']), str(row['Incidence Rate'])
                
            output = io.BytesIO()
            doc.save(output)
            st.download_button(label="📥 Download Word Report", data=output.getvalue(), file_name="Incidence_Report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        except Exception as e:
            st.error(f"Word generation failed. Ensure python-docx and vl-convert-python are installed. Error: {e}")

    # --------------------------------------------------------
    # PDF EXPORT
    # --------------------------------------------------------

elif report_format == "PDF":
        try:
            from fpdf import FPDF
            
            # Helper function to remove unsupported Unicode characters for FPDF
            def clean_text(text):
                # Replace Em-dash and En-dash with normal hyphen to avoid latin-1 errors
                return str(text).replace("—", "-").replace("–", "-").encode('latin-1', 'replace').decode('latin-1')

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, txt="Public Health Incidence & Surveillance Report", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, txt=f"Total Records Analyzed: {len(case_df):,}", ln=True)
            pdf.cell(0, 10, txt=f"Denominator Used: Per {denominator:,} Population", ln=True)
            
            if "export_charts" in st.session_state and st.session_state["export_charts"]:
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, txt="Visualizations", ln=True)
                for chart_title, chart_obj in st.session_state["export_charts"].items():
                    pdf.set_font("Arial", 'B', 10)
                    
                    # Apply clean_text to chart titles
                    pdf.cell(0, 10, txt=clean_text(chart_title), ln=True)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        chart_obj.save(tmp.name, format="png", engine="vl-convert")
                        pdf.image(tmp.name, w=180) 
                        pdf.ln(5)
            
            if include_tables == "With Tables" and not ward_incidence.empty:
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, txt="Data Table (Top 30 Records)", ln=True)
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(60, 10, "Ward", border=1)
                pdf.cell(40, 10, "Cases", border=1)
                pdf.cell(40, 10, "Incidence Rate", border=1)
                pdf.ln()
                pdf.set_font("Arial", size=10)
                for _, row in ward_incidence.head(30).iterrows(): 
                    # Apply clean_text to Ward names just in case they have unicode chars
                    pdf.cell(60, 10, clean_text(row['Ward']), border=1)
                    pdf.cell(40, 10, str(row['Cases']), border=1)
                    pdf.cell(40, 10, str(row['Incidence Rate']), border=1)
                    pdf.ln()
                    
            pdf_bytes = pdf.output(dest='S').encode('latin1')
            st.download_button(label="📥 Download PDF Report (With Charts)", data=pdf_bytes, file_name="Incidence_Report.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF generation failed. Ensure fpdf and vl-convert-python are installed. Error: {e}")


 # ============================================================
 # BACKWARD-COMPATIBLE ENTRY POINT
 # ============================================================

def render_incidence(df):
    return render_incidence_analysis(df)
