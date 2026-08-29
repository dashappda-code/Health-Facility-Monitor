
import streamlit as st
import pandas as pd

# Configure page settings
st.set_page_config(page_title="IHIP Dashboard", layout="wide")

@st.cache_data
def load_data():
    # Replace 'data.xlsx' with your actual file path
    # df = pd.read_excel("data.xlsx")
    
    # Dummy data for demonstration purposes (replace this with actual data loading)
    data = {
        'Zone/Administrative Ward Name': ['A', 'B', 'A', 'C'], 
        'Facility Type': ['Private Hospital', 'Govt Hospital', 'Private Laboratory', 'Primary Health Centre'],
        'Patients': [15, 30, 10, 45]
    }
    df = pd.DataFrame(data)

    # Rename column as required
    df = df.rename(columns={"Zone/Administrative Ward Name": "Ward"})

    # Categorize facilities into 'Private' and 'Public'
    def classify_facility(facility_type):
        if facility_type in ["Private Hospital", "Private Laboratory"]:
            return "Private"
        return "Public"

    df['Facility Category'] = df['Facility Type'].apply(classify_facility)
    return df

# Load the dataframe
df = load_data()

# Dashboard Title
st.title("IHIP Defaulter Tracking Dashboard")

# Sidebar Filters
st.sidebar.header("Dashboard Filters")
selected_ward = st.sidebar.multiselect(
    "Select Ward", 
    options=df['Ward'].unique(), 
    default=df['Ward'].unique()
)

selected_facility = st.sidebar.radio(
    "Facility Category", 
    options=["All", "Public", "Private"]
)

# Apply Filters
filtered_df = df[df['Ward'].isin(selected_ward)]
if selected_facility != "All":
    filtered_df = filtered_df[filtered_df['Facility Category'] == selected_facility]

# Display Data
st.subheader("Patient and Facility Data")
st.dataframe(filtered_df, use_container_width=True)

# Basic Statistics
st.subheader("Summary Statistics")
st.write(f"Total Records: **{len(filtered_df)}**")
