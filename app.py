import re
import pandas as pd
import streamlit as st
import pydeck as pdk

# 1. Page Configuration
st.set_page_config(page_title="MSU Mumbai Surveillance Dashboard", page_icon="📈", layout="wide")

# 2. Custom CSS
st.markdown("""
<style>
    .kpi-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: left;
        border: 1px solid #f0f0f0;
    }
    .kpi-title {
        color: #6c757d;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .kpi-value {
        color: #212529;
        font-size: 24px;
        font-weight: bold;
    }
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# 3. Data Loading & Preprocessing
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/1FMxAX2fZtzc8mqconPFzF3cznZvsozcYSwX5zlG8dIM/edit?gid=1168281274#gid=1168281274"

def convert_google_sheet_url(url: str) -> str:
    sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    gid_match = re.search(r"[#&?]gid=([0-9]+)", url)
    if sheet_id_match:
        sheet_id = sheet_id_match.group(1)
        gid = gid_match.group(1) if gid_match else "0"
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return url

@st.cache_data(ttl=60) # Refreshes every 60 seconds
def load_and_clean_data(url: str) -> pd.DataFrame:
    csv_url = convert_google_sheet_url(url)
    try:
        df = pd.read_csv(csv_url)
        
        # Standardize Ward Column
        if "Zone/Administrative Ward Name" in df.columns:
            df.rename(columns={"Zone/Administrative Ward Name": "Ward"}, inplace=True)
            
        # Classify Facility Type
        def classify_facility(f_type):
            f_clean = str(f_type).strip().lower()
            if f_clean in ["private hospital", "private laboratory", "private hosp", "private lab"]:
                return "Private"
            return "Public"
            
        if "Facility Type" in df.columns:
            df["Facility Category"] = df["Facility Type"].apply(classify_facility)
            
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

raw_df = load_and_clean_data(DEFAULT_GSHEET_URL)

# 4. Header Section
header_col1, header_col2 = st.columns([2, 1])
with header_col1:
    st.markdown("### 📈 MSU Mumbai Surveillance Dashboard")
    st.markdown("<span style='color:gray'>Municipal Surveillance Unit - Mumbai</span>", unsafe_allow_html=True)
with header_col2:
    st.write("") 
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    btn_col1.button("📥 Data")
    if btn_col2.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()
    btn_col3.button("📄 PDF")
    btn_col4.button("📊 Excel")

st.divider()

# 5. Dynamic Filters
st.markdown("**🔽 Filters**")
filtered_df = raw_df.copy()

filter_row1_col1, filter_row1_col2 = st.columns(2)

with filter_row1_col1:
    if "Ward" in filtered_df.columns:
        ward_list = ["All Wards"] + sorted([str(w) for w in filtered_df["Ward"].dropna().unique()])
        selected_ward = st.selectbox("Ward", ward_list)
        if selected_ward != "All Wards":
            filtered_df = filtered_df[filtered_df["Ward"] == selected_ward]

with filter_row1_col2:
    if "Facility Category" in filtered_df.columns:
        fac_list = ["All Facilities", "Public", "Private"]
        selected_fac = st.selectbox("Facility Category", fac_list)
        if selected_fac != "All Facilities":
            filtered_df = filtered_df[filtered_df["Facility Category"] == selected_fac]

st.markdown(f"<p style='text-align: right; color: gray;'>{len(filtered_df):,} / {len(raw_df):,} records</p>", unsafe_allow_html=True)

# 6. Dynamic KPI Calculations
total_cases = len(filtered_df)

public_cases = (filtered_df["Facility Category"] == "Public").sum() if "Facility Category" in filtered_df.columns else 0
private_cases = (filtered_df["Facility Category"] == "Private").sum() if "Facility Category" in filtered_df.columns else 0

try:
    top_ward = filtered_df["Ward"].value_counts().idxmax() if "Ward" in filtered_df.columns and not filtered_df.empty else "N/A"
except:
    top_ward = "N/A"

# 7. Render KPI Cards
kpi_cols = st.columns(4)
cards_data = [
    {"title": "👥 Total Cases", "value": f"{total_cases:,}"},
    {"title": "🏛️ Public Facility Cases", "value": f"{public_cases:,}"},
    {"title": "🏥 Private Facility Cases", "value": f"{private_cases:,}"},
    {"title": "📍 Top Ward (Max Cases)", "value": str(top_ward)}
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

# 8. Tabs for Detailed Data
tab1, tab2 = st.tabs(["📋 Data Records", "🗺️ Analytics Placeholder"])

with tab1:
    st.markdown("**Filtered Case Records**")
    st.dataframe(filtered_df, use_container_width=True)

with tab2:
    st.info("Charts and Map visualizations will update here based on filtered data.")
