import pandas as pd
import streamlit as st
import pydeck as pdk

# 1. Page Configuration (Must be the first command)
st.set_page_config(page_title="MSU Mumbai Surveillance Dashboard", page_icon="📈", layout="wide")

# 2. Custom CSS for KPI Cards and UI tweaks
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
    /* Hide default Streamlit top margin */
    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# 3. Header Section (Matching image_301b8c.png)
header_col1, header_col2 = st.columns([2, 1])
with header_col1:
    st.markdown("### 📈 MSU Mumbai Surveillance Dashboard")
    st.markdown("<span style='color:gray'>Municipal Surveillance Unit - Mumbai</span>", unsafe_allow_html=True)
with header_col2:
    st.write("") # Spacer
    # Using columns for horizontal buttons
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    btn_col1.button("📥 Data")
    btn_col2.button("🔄 Refresh")
    btn_col3.button("📄 PDF")
    btn_col4.button("📊 Excel")

st.divider()

# 4. Filter Section
st.markdown("**🔽 Filters**")
filter_row1_col1, filter_row1_col2, filter_row1_col3, filter_row1_col4 = st.columns(4)
with filter_row1_col1:
    st.selectbox("Year", ["2026", "2025", "2024"])
with filter_row1_col2:
    st.selectbox("Month", ["All Months", "Jan", "Feb", "Mar", "Apr", "May"])
with filter_row1_col3:
    st.selectbox("Week", ["All Weeks", "Week 1", "Week 2"])
with filter_row1_col4:
    st.selectbox("Disease", ["Dengue", "Malaria", "Chikungunya"])

filter_row2_col1, filter_row2_col2, filter_row2_col3, filter_row2_col4 = st.columns(4)
with filter_row2_col1:
    st.selectbox("Ward", ["All Wards", "GS", "A", "B", "C"])
with filter_row2_col2:
    st.selectbox("Gender", ["All Genders", "Male", "Female"])
with filter_row2_col3:
    st.selectbox("OPD / IPD", ["All Types", "OPD", "IPD"])
with filter_row2_col4:
    date_col1, date_col2 = st.columns(2)
    date_col1.date_input("Date From")
    date_col2.date_input("Date To")

st.markdown("<p style='text-align: right; color: gray;'>1,810 / 38,988 records</p>", unsafe_allow_html=True)

# 5. KPI Summary Cards
kpi_cols = st.columns(6)

cards_data = [
    {"title": "👥 Total Cases", "value": "1,810"},
    {"title": "🩺 OPD Cases", "value": "950"},
    {"title": "🏥 IPD Cases", "value": "860"},
    {"title": "👫 Male / Female", "value": "1,147 / 663"},
    {"title": "🦠 Top Disease", "value": "Dengue"},
    {"title": "📍 Top Ward", "value": "GS"}
]

for col, data in zip(kpi_cols, cards_data):
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">{data['title']}</div>
            <div class="kpi-value">{data['value']}</div>
        </div>
        """, unsafe_allow_html=True)

st.write("") # Spacer

# 6. Tabs Integration (Matching image_301bca.png & image_301c0d.png)
tab1, tab2 = st.tabs(["📊 Charts & Analytics", "🗺️ Map View"])

with tab1:
    # Nested tabs for analytics
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["🔄 Year Comparison", "📈 Trends", "🧠 Prediction", "🥧 Distribution"])
    
    with sub_tab1:
        st.info("Year Comparison Charts will render here. (Integration with your Ward/Public-Private data)")
    with sub_tab2:
        st.info("Trend Line Charts will render here.")
    with sub_tab3:
        st.info("Machine Learning Predictions will render here.")
    with sub_tab4:
        st.info("Pie charts for demographic distribution will render here.")

with tab2:
    st.markdown("**📍 Geospatial Distribution - Ward-wise Clustering**")
    
    # Mock data for Mumbai Wards Map (Placeholder for actual lat/lon data)
    map_data = pd.DataFrame({
        "lat": [19.0760, 19.0144, 19.1136, 18.9220],
        "lon": [72.8777, 72.8479, 72.8697, 72.8347],
        "cases": [500, 300, 800, 210]
    })
    
    # Using PyDeck for bubble clustering map
    st.pydeck_chart(pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=pdk.ViewState(
            latitude=19.0760,
            longitude=72.8777,
            zoom=10,
            pitch=0,
        ),
        layers=[
            pdk.Layer(
                'ScatterplotLayer',
                data=map_data,
                get_position='[lon, lat]',
                get_color='[200, 30, 0, 160]',
                get_radius='cases * 5',
                pickable=True
            ),
        ],
    ))
