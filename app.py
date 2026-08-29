import re
import pandas as pd
import streamlit as st
import pydeck as pdk

# 1. Page Configuration
st.set_page_config(page_title="MSU Mumbai Surveillance Dashboard", page_icon="📈", layout="wide")

# 2. Custom CSS for Image-Matching UI
st.markdown("""
<style>
    .kpi-card {
        background-color: white;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: left;
        border: 1px solid #e2e8f0;
    }
    .kpi-title {
        color: #64748b;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .kpi-value {
        color: #0f172a;
        font-size: 22px;
        font-weight: bold;
    }
    .block-container {
        padding-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# 3. Data Loading & Flow Mapping
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/1FMxAX2fZtzc8mqconPFzF3cznZvsozcYSwX5zlG8dIM/edit?gid=1168281274#gid=1168281274"

def convert_google_sheet_url(url: str) -> str:
    sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    gid_match = re.search(r"[#&?]gid=([0-9]+)", url)
    if sheet_id_match:
        sheet_id = sheet_id_match.group(1)
        gid = gid_match.group(1) if gid_match else "0"
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return url

@st.cache_data(ttl=60)
def load_and_map_data(url: str) -> pd.DataFrame:
    csv_url = convert_google_sheet_url(url)
    try:
        df = pd.read_csv(csv_url)
        
        # Standardize Columns to Match Image Flow
        if "Zone/Administrative Ward Name" in df.columns:
            df.rename(columns={"Zone/Administrative Ward Name": "Ward"}, inplace=True)
            
        # Ensure fallback columns exist if your sheet has slightly different names
        expected_cols = ['Year', 'Month', 'Week', 'Disease', 'Gender', 'Type']
        for col in expected_cols:
            if col not in df.columns:
                # Create dummy mappings based on available data or defaults for visual flow
                if col == 'Year' and 'Date' in df.columns:
                    df['Year'] = pd.to_datetime(df['Date'], errors='coerce').dt.year.fillna(2026).astype(str)
                else:
                    df[col] = 'Not Specified'

        return df
    except Exception as e:
        st.error(f"Data Load Error: {e}")
        return pd.DataFrame()

raw_df = load_and_map_data(DEFAULT_GSHEET_URL)

# 4. Top Header & Action Buttons (Matching image_301b8c.png)
header_col1, header_col2 = st.columns([2, 1])
with header_col1:
    st.markdown("### MSU Mumbai Surveillance Dashboard")
    st.markdown("<span style='color:gray; font-size:14px;'>Municipal Surveillance Unit - Mumbai</span>", unsafe_allow_html=True)
with header_col2:
    st.write("") 
    b1, b2, b3, b4, b5 = st.columns(5)
    b1.button("Download")
    if b2.button("Refresh"):
        st.cache_data.clear()
        st.rerun()
    b3.button("PDF")
    b4.button("Excel")
    b5.button("CSV")

st.divider()

# 5. Image-Style Filter Panel (8 Filters Layout across 2 rows)
st.markdown("**Filters**")
filtered_df = raw_df.copy()

f_row1_1, f_row1_2, f_row1_3, f_row1_4 = st.columns(4)
f_row2_1, f_row2_2, f_row2_3, f_row2_4 = st.columns(4)

with f_row1_1:
    years = ["All Years"] + sorted(list(filtered_df['Year'].dropna().astype(str).unique())) if 'Year' in filtered_df.columns else ["All Years"]
    sel_year = st.selectbox("Year", years)
    if sel_year != "All Years" and 'Year' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Year'].astype(str) == sel_year]

with f_row1_2:
    months = ["All Months"] + sorted(list(filtered_df['Month'].dropna().astype(str).unique())) if 'Month' in filtered_df.columns else ["All Months"]
    sel_month = st.selectbox("Month", months)
    if sel_month != "All Months":
        filtered_df = filtered_df[filtered_df['Month'].astype(str) == sel_month]

with f_row1_3:
    weeks = ["All Weeks"] + sorted(list(filtered_df['Week'].dropna().astype(str).unique())) if 'Week' in filtered_df.columns else ["All Weeks"]
    sel_week = st.selectbox("Week", weeks)
    if sel_week != "All Weeks":
        filtered_df = filtered_df[filtered_df['Week'].astype(str) == sel_week]

with f_row1_4:
    diseases = ["All Diseases"] + sorted(list(filtered_df['Disease'].dropna().astype(str).unique())) if 'Disease' in filtered_df.columns else ["All Diseases"]
    sel_disease = st.selectbox("Disease", diseases)
    if sel_disease != "All Diseases":
        filtered_df = filtered_df[filtered_df['Disease'].astype(str) == sel_disease]

with f_row2_1:
    wards = ["All Wards"] + sorted(list(filtered_df['Ward'].dropna().astype(str).unique())) if 'Ward' in filtered_df.columns else ["All Wards"]
    sel_ward = st.selectbox("Ward", wards)
    if sel_ward != "All Wards":
        filtered_df = filtered_df[filtered_df['Ward'] == sel_ward]

with f_row2_2:
    genders = ["All Genders"] + sorted(list(filtered_df['Gender'].dropna().astype(str).unique())) if 'Gender' in filtered_df.columns else ["All Genders"]
    sel_gender = st.selectbox("Gender", genders)
    if sel_gender != "All Genders":
        filtered_df = filtered_df[filtered_df['Gender'].astype(str) == sel_gender]

with f_row2_3:
    types = ["All Types"] + sorted(list(filtered_df['Type'].dropna().astype(str).unique())) if 'Type' in filtered_df.columns else ["All Types"]
    sel_type = st.selectbox("OPD / IPD", types)
    if sel_type != "All Types":
        filtered_df = filtered_df[filtered_df['Type'].astype(str) == sel_type]

with f_row2_4:
    d_col1, d_col2 = st.columns(2)
    d_col1.date_input("Date From", key="df_from")
    d_col2.date_input("Date To", key="df_to")

st.markdown(f"<p style='text-align: right; color: gray; font-size: 13px;'>{len(filtered_df):,} / {len(raw_df):,} records</p>", unsafe_allow_html=True)

# 6. Dynamic Flow Calculations for the 6 KPI Cards
total_cases = len(filtered_df)
opd_cases = len(filtered_df[filtered_df['Type'].str.lower() == 'opd']) if 'Type' in filtered_df.columns else 0
ipd_cases = len(filtered_df[filtered_df['Type'].str.lower() == 'ipd']) if 'Type' in filtered_df.columns else 0

male_count = len(filtered_df[filtered_df['Gender'].str.lower().str.contains('m', na=False)]) if 'Gender' in filtered_df.columns else 0
female_count = len(filtered_df[filtered_df['Gender'].str.lower().str.contains('f', na=False)]) if 'Gender' in filtered_df.columns else 0

try:
    top_disease = filtered_df['Disease'].mode()[0] if 'Disease' in filtered_df.columns and not filtered_df.empty else "N/A"
except:
    top_disease = "N/A"

try:
    top_ward = filtered_df['Ward'].mode()[0] if 'Ward' in filtered_df.columns and not filtered_df.empty else "N/A"
except:
    top_ward = "N/A"

# 7. Render 6 KPI Summary Cards in Image Layout
kpi_cols = st.columns(6)
cards_data = [
    {"title": "Total Cases", "value": f"{total_cases:,}"},
    {"title": "OPD Cases", "value": f"{opd_cases:,}"},
    {"title": "IPD Cases", "value": f"{ipd_cases:,}"},
    {"title": "Male / Female", "value": f"{male_count:,} / {female_count:,}"},
    {"title": "Top Disease", "value": str(top_disease)},
    {"title": "Top Ward", "value": str(top_ward)}
]

for col, data in zip(kpi_cols, cards_data):
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">{data['title']}</div>
            <div class="kpi-value">{data['value']}</div>
        </div>
        """, unsafe_allow_html=True)

st.write("")

# 8. Nested Analytics Tabs & Map Flow (Matching image_301bca.png & image_301c0d.png)
main_tab1, main_tab2 = st.tabs(["Charts & Analytics", "Map View"])

with main_tab1:
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["Year Comparison", "Trends", "Prediction", "Distribution"])
    
    with sub_tab1:
        st.info("Interactive Year Comparison analytics flowing from active filters.")
    with sub_tab2:
        st.info("Trend lines based on selected time and disease parameters.")
    with sub_tab3:
        st.info("Surveillance predictive metrics.")
    with sub_tab4:
        st.info("Demographic distribution charts.")

with main_tab2:
    st.markdown("**Geospatial Distribution - Ward-wise Clustering**")
    
    # Map coordinates handler based on filtered data
    map_sample = pd.DataFrame({
        "lat": [19.0760, 19.0144, 19.1136, 18.9220],
        "lon": [72.8777, 72.8479, 72.8697, 72.8347],
        "cases": [total_cases * 0.4, total_cases * 0.3, total_cases * 0.2, total_cases * 0.1]
    })
    
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=pdk.ViewState(latitude=19.0760, longitude=72.8777, zoom=10, pitch=0),
        layers=[
            pdk.Layer(
                'ScatterplotLayer',
                data=map_sample,
                get_position='[lon, lat]',
                get_color='[220, 38, 38, 160]',
                get_radius='cases + 50',
                pickable=True
            ),
        ],
    ))
