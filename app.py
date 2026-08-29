import re
import pandas as pd
import streamlit as st

# 1. Page Configuration
st.set_page_config(
    page_title="Daily IHIP Defaulter Dashboard", 
    page_icon="🏥",
    layout="wide"
)

# Default Google Sheets Link
DEFAULT_GSHEET_URL = "https://docs.google.com/spreadsheets/d/1FMxAX2fZtzc8mqconPFzF3cznZvsozcYSwX5zlG8dIM/edit?gid=1168281274#gid=1168281274"

def convert_google_sheet_url(url: str) -> str:
    """Converts a standard Google Sheets URL into a direct CSV export URL."""
    sheet_id_match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    gid_match = re.search(r"[#&?]gid=([0-9]+)", url)

    if sheet_id_match:
        sheet_id = sheet_id_match.group(1)
        gid = gid_match.group(1) if gid_match else "0"
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return url

@st.cache_data(ttl=60)
def load_data(url: str) -> pd.DataFrame:
    """Loads data from the Google Sheet. Refreshes automatically every 60 seconds."""
    csv_url = convert_google_sheet_url(url)
    df = pd.read_csv(csv_url)
    return df

def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans data and applies Public/Private classification rules."""
    # Standardize Ward column name
    if "Zone/Administrative Ward Name" in df.columns:
        df.rename(columns={"Zone/Administrative Ward Name": "Ward"}, inplace=True)

    # Classify Private vs Public facilities
    def classify_facility(f_type):
        f_type_clean = str(f_type).strip().lower()
        if f_type_clean in ["private hospital", "private laboratory", "private hosp", "private lab"]:
            return "Private"
        return "Public"

    if "Facility Type" in df.columns:
        df["Facility Category"] = df["Facility Type"].apply(classify_facility)

    return df

# 2. Dashboard UI
st.title("📊 IHIP Defaulter & Health Surveillance Dashboard")

# Sidebar Configuration
st.sidebar.header("⚙️ Data Source Settings")
sheet_url = st.sidebar.text_input("Google Sheets Link:", value=DEFAULT_GSHEET_URL)

if st.sidebar.button("🔄 Force Data Refresh"):
    st.cache_data.clear()
    st.rerun()

# 3. Main Application Logic
try:
    with st.spinner("Fetching live data from Google Sheets..."):
        raw_df = load_data(sheet_url)
        df = preprocess_data(raw_df)

    st.success(f"✅ Data loaded successfully! Total records: {len(df)}")

    # Top KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Reported Cases", len(df))
    with col2:
        total_public = (df["Facility Category"] == "Public").sum() if "Facility Category" in df.columns else 0
        st.metric("Public Facility Cases", total_public)
    with col3:
        total_private = (df["Facility Category"] == "Private").sum() if "Facility Category" in df.columns else 0
        st.metric("Private Facility Cases", total_private)
    with col4:
        total_wards = df["Ward"].nunique() if "Ward" in df.columns else 0
        st.metric("Active Wards Tracked", total_wards)

    st.divider()

    # Data Filters
    st.subheader("🔍 Filter Records")
    filter_col1, filter_col2 = st.columns(2)
    filtered_df = df.copy()

    with filter_col1:
        if "Ward" in df.columns:
            wards_list = ["All"] + sorted(list(df["Ward"].dropna().unique()))
            selected_ward = st.selectbox("Filter by Ward:", wards_list)
            if selected_ward != "All":
                filtered_df = filtered_df[filtered_df["Ward"] == selected_ward]

    with filter_col2:
        if "Facility Category" in df.columns:
            facility_list = ["All", "Public", "Private"]
            selected_facility = st.selectbox("Filter by Facility Type:", facility_list)
            if selected_facility != "All":
                filtered_df = filtered_df[filtered_df["Facility Category"] == selected_facility]

    # Display Filtered Data
    st.subheader("📋 Detailed Case Records")
    st.dataframe(filtered_df, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ Error loading data: {e}\n\nPlease ensure your Google Sheet is set to 'Anyone with the link can view'.")
