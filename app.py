import streamlit as st
import pandas as pd
import plotly.express as px

# Page Setup
st.set_page_config(
    page_title="IHIP Defaulter & Health Facility Dashboard",
    page_icon="🏥",
    layout="wide"
)

# Custom CSS for Professional Styling
st.markdown("""
    <style>
    .main-title {
        font-size: 30px;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 5px;
    }
    .sub-title {
        font-size: 16px;
        color: #64748B;
        margin-bottom: 25px;
    }
    .stMetric {
        background-color: #F8FAFC;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2563EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# Dashboard Header
st.markdown('<div class="main-title">🏥 IHIP Defaulter & Health Facility Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Epidemiological Data Analysis and Ward-wise Defaulter Tracking System</div>', unsafe_allow_html=True)

# Data Processing Function
def process_data(df):
    # Rename Ward Column if exists
    if 'Zone/Administrative Ward Name' in df.columns:
        df = df.rename(columns={'Zone/Administrative Ward Name': 'Ward'})
    
    # Facility Categorization Logic
    if 'Facility Type' in df.columns:
        def categorize(facility):
            if str(facility).strip() in ["Private Hospital", "Private Laboratory"]:
                return "Private"
            return "Public"
        
        df['Facility Category'] = df['Facility Type'].apply(categorize)
    else:
        df['Facility Category'] = "Unknown"
        
    return df

# Sidebar Controls
st.sidebar.header("📂 Data Import & Filters")
uploaded_file = st.sidebar.file_uploader("Upload IHIP Excel / CSV File", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)
        df = process_data(raw_df)
    except Exception as e:
        st.error(f"Error loading file: {e}")
        st.stop()
else:
    # Demo Mock Data if no file uploaded
    demo_data = {
        'Zone/Administrative Ward Name': ['Ward A', 'Ward B', 'Ward A', 'Ward C', 'Ward B', 'Ward D', 'Ward A', 'Ward C'],
        'Facility Type': ['Private Hospital', 'Govt Hospital', 'Private Laboratory', 'Primary Health Centre', 'Private Hospital', 'Govt Hospital', 'Urban Health Post', 'Private Laboratory'],
        'Defaulter Count': [24, 45, 12, 38, 19, 50, 15, 8]
    }
    df = pd.DataFrame(demo_data)
    df = process_data(df)
    st.sidebar.info("💡 Showing Demo Data. Upload your actual IHIP file to analyze real records.")

# Sidebar Filters
wards_list = df['Ward'].dropna().unique().tolist()
selected_wards = st.sidebar.multiselect("Filter by Ward", options=wards_list, default=wards_list)

category_list = ["All", "Public", "Private"]
selected_category = st.sidebar.radio("Facility Category", options=category_list)

# Filter Dataframe
filtered_df = df[df['Ward'].isin(selected_wards)]
if selected_category != "All":
    filtered_df = filtered_df[filtered_df['Facility Category'] == selected_category]

# Metric Cards (KPI Summary)
val_column = 'Defaulter Count' if 'Defaulter Count' in filtered_df.columns else filtered_df.columns[-1]

total_cases = filtered_df[val_column].sum() if pd.api.types.is_numeric_dtype(filtered_df[val_column]) else len(filtered_df)
public_cases = filtered_df[filtered_df['Facility Category'] == 'Public'][val_column].sum() if pd.api.types.is_numeric_dtype(filtered_df[val_column]) else len(filtered_df[filtered_df['Facility Category'] == 'Public'])
private_cases = filtered_df[filtered_df['Facility Category'] == 'Private'][val_column].sum() if pd.api.types.is_numeric_dtype(filtered_df[val_column]) else len(filtered_df[filtered_df['Facility Category'] == 'Private'])

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Defaulter Cases", f"{total_cases:,}")
with col2:
    st.metric("Public Facility Cases", f"{public_cases:,}")
with col3:
    st.metric("Private Facility Cases", f"{private_cases:,}")
with col4:
    st.metric("Active Wards Tracked", len(filtered_df['Ward'].unique()))

st.divider()

# Dashboard Tabs Layout
tab1, tab2, tab3 = st.tabs(["📊 Visual Analytics", "📋 Detailed Data View", "📈 Ward Summary"])

with tab1:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("Defaulters by Ward")
        if pd.api.types.is_numeric_dtype(filtered_df[val_column]):
            ward_chart_data = filtered_df.groupby('Ward')[val_column].sum().reset_index()
            fig_ward = px.bar(
                ward_chart_data, 
                x='Ward', 
                y=val_column, 
                color='Ward', 
                text_auto=True,
                title="Total Defaulter Count per Ward"
            )
            st.plotly_chart(fig_ward, use_container_width=True)
        else:
            st.info("No numeric column available for bar aggregation.")

    with col_right:
        st.subheader("Public vs Private Distribution")
        cat_chart_data = filtered_df.groupby('Facility Category')[val_column].sum().reset_index() if pd.api.types.is_numeric_dtype(filtered_df[val_column]) else filtered_df['Facility Category'].value_counts().reset_index()
        fig_pie = px.pie(
            cat_chart_data, 
            names='Facility Category', 
            values=val_column if pd.api.types.is_numeric_dtype(filtered_df[val_column]) else 'count',
            color='Facility Category',
            color_discrete_map={'Public': '#2563EB', 'Private': '#F59E0B'},
            hole=0.4,
            title="Facility Share"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    st.subheader("Raw Data Records")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    
    # Download Button
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data CSV",
        data=csv,
        file_name="ihip_filtered_data.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("Ward-wise Cross Tabulation")
    if 'Facility Type' in filtered_df.columns:
        pivot_table = pd.pivot_table(
            filtered_df, 
            index='Ward', 
            columns='Facility Category', 
            values=val_column, 
            aggfunc='sum' if pd.api.types.is_numeric_dtype(filtered_df[val_column]) else 'count',
            fill_value=0
        )
        st.dataframe(pivot_table, use_container_width=True)
