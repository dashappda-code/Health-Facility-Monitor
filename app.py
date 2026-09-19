import streamlit as st

from phase1_data import load_data
from phase2_overview import create_filters, apply_filters, render_overview
from phase3_charts import render_charts
from phase4_demographics import render_demographics
from phase5_ward import render_ward_analysis
from phase6_map import render_map
from phase7_explorer import render_explorer
from phase8_prediction import render_prediction
from phase9_manual import render_manual
from phase10_validation_kpi import render_validation_kpi
from phase11_drilldown_export import render_drilldown_export


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Health Programme Management Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div style="
        font-size:30px;
        font-weight:700;
        margin-bottom:0px;
    ">
        🏥 Health Programme Management Dashboard
    </div>

    <div style="
        font-size:15px;
        margin-top:7px;
        color:#555;
    ">
        Health Programme Management Dashboard
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# STEP 1 — LOAD DATA
# ============================================================

st.info("🔄 STEP 1: Google Sheet data loading started...")

try:
    df = load_data()

except Exception as e:
    st.error("❌ STEP 1 FAILED: Google Sheet / data loading error")

    st.exception(e)

    st.warning(
        """
        कृपया वर दिसणारा error screenshot पाठवा.
        आत्ता बाकी dashboard modules बदलू नका.
        """
    )

    st.stop()


# ============================================================
# STEP 1 SUCCESS
# ============================================================

st.success(
    f"✅ STEP 1 DONE — {len(df):,} records loaded successfully."
)


# ============================================================
# BASIC DATA CHECK
# ============================================================

if df is None or df.empty:

    st.error(
        "❌ Google Sheet मधून data आला आहे, पण dataset रिकामा आहे."
    )

    st.stop()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🏥 Programme Dashboard")

    st.markdown("---")

    page = st.radio(
        "Select Section",
        [
            "Overview",
            "Charts & Trends",
            "Demographics",
            "Ward Analysis",
            "Map",
            "Data Explorer",
            "Prediction",
            "Validation & KPI",
            "Drill-down & Export",
            "User Manual",
        ],
    )

    st.markdown("---")

    st.caption(
        f"Total records: {len(df):,}"
    )


# ============================================================
# STEP 2 — GLOBAL FILTERS
# ============================================================

st.info("🔄 STEP 2: Applying global dashboard filters...")

try:

    filter_values = create_filters(df)

    filtered_df = apply_filters(
        df,
        filter_values,
    )

except Exception as e:

    st.error("❌ STEP 2 FAILED: Dashboard filter error")

    st.exception(e)

    st.stop()


# ============================================================
# STEP 2 SUCCESS
# ============================================================

st.success(
    f"✅ STEP 2 DONE — {len(filtered_df):,} records after filters."
)


# ============================================================
# GLOBAL DATA STATUS
# ============================================================

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Total Records",
        f"{len(df):,}",
    )

with col2:
    st.metric(
        "Filtered Records",
        f"{len(filtered_df):,}",
    )

with col3:

    if len(df) > 0:

        percentage = (
            len(filtered_df) / len(df)
        ) * 100

        st.metric(
            "Records Selected",
            f"{percentage:.1f}%",
        )

    else:

        st.metric(
            "Records Selected",
            "0%",
        )


# ============================================================
# PAGE RENDERING
# ============================================================

st.markdown("---")

try:

    # --------------------------------------------------------
    # OVERVIEW
    # --------------------------------------------------------

    if page == "Overview":

        st.info("📊 Loading Overview...")

        render_overview(filtered_df)


    # --------------------------------------------------------
    # CHARTS & TRENDS
    # --------------------------------------------------------

    elif page == "Charts & Trends":

        st.info("📈 Loading Charts & Trends...")

        render_charts(filtered_df)


    # --------------------------------------------------------
    # DEMOGRAPHICS
    # --------------------------------------------------------

    elif page == "Demographics":

        st.info("👥 Loading Demographic Analysis...")

        render_demographics(filtered_df)


    # --------------------------------------------------------
    # WARD ANALYSIS
    # --------------------------------------------------------

    elif page == "Ward Analysis":

        st.info("🏘️ Loading Ward Analysis...")

        render_ward_analysis(filtered_df)


    # --------------------------------------------------------
    # MAP
    # --------------------------------------------------------

    elif page == "Map":

        st.info("🗺️ Loading Map...")

        render_map(filtered_df)


    # --------------------------------------------------------
    # DATA EXPLORER
    # --------------------------------------------------------

    elif page == "Data Explorer":

        st.info("🔎 Loading Data Explorer...")

        render_explorer(filtered_df)


    # --------------------------------------------------------
    # PREDICTION
    # --------------------------------------------------------

    elif page == "Prediction":

        st.info("🔮 Loading Prediction Module...")

        render_prediction(filtered_df)


    # --------------------------------------------------------
    # VALIDATION & KPI
    # --------------------------------------------------------

    elif page == "Validation & KPI":

        st.info("✅ Loading Validation & KPI...")

        render_validation_kpi(filtered_df)


    # --------------------------------------------------------
    # DRILL-DOWN & EXPORT
    # --------------------------------------------------------

    elif page == "Drill-down & Export":

        st.info("📥 Loading Drill-down & Export...")

        render_drilldown_export(filtered_df)


    # --------------------------------------------------------
    # USER MANUAL
    # --------------------------------------------------------

    elif page == "User Manual":

        st.info("📘 Loading User Manual...")

        render_manual()


except Exception as e:

    st.error(
        f"❌ Error while loading section: {page}"
    )

    st.exception(e)

    st.warning(
        """
        हा error संबंधित module मध्ये आहे.
        वर दिसणारा पूर्ण error screenshot पाठवा.
        """
    )

    st.stop()


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Health Programme Management Dashboard | "
    "Live Google Sheet Data"
)
