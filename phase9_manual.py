# phase9_manual.py
# ============================================================
# PHASE 9 - USER MANUAL & OPERATING INSTRUCTIONS
# Health Programme Management Dashboard
# ============================================================

import streamlit as st
from io import BytesIO

# ============================================================
# REPORTLAB
# ============================================================

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True

except ImportError:
    REPORTLAB_AVAILABLE = False


# ============================================================
# MANUAL CONTENT
# ============================================================

MANUAL_SECTIONS = [

    {
        "title": "1. Introduction",
        "content": """
The Health Programme Management Dashboard is an interactive web-based
application designed to support programme monitoring, facility-level review,
ward-level analysis, monthly trend monitoring, data quality assessment and
management decision-making.
"""
    },

    {
        "title": "2. Purpose of the Application",
        "content": """
The main objectives of the application are:

• To monitor the overall programme burden.
• To identify high-burden wards.
• To identify high-burden health facilities.
• To analyse monthly trends.
• To understand age-wise and gender-wise distribution.
• To compare wards and facilities.
• To identify increasing or decreasing trends.
• To assess data quality and completeness.
• To support programme review and planning.
"""
    },

    {
        "title": "3. Recommended Users",
        "content": """
The dashboard may be used by:

• Programme Officers
• District / Municipal Health Officials
• Medical Officers
• Surveillance Officers
• Epidemiologists
• Health Supervisors
• Data Managers
• Facility In-charges
• Other authorised programme staff
"""
    },

    {
        "title": "4. Recommended Order of Dashboard Use",
        "content": """
For routine programme review, users are advised to follow this sequence:

1. Overall Situation
2. Monthly Trend
3. Ward Analysis
4. Facility Analysis
5. Map / Geographic View
6. Data Explorer
7. Prediction / Trend Indicators
8. Management Action

This sequence helps the user move from the overall situation to specific
priority areas.
"""
    },

    {
        "title": "5. Global Filters",
        "content": """
Filters allow users to analyse a specific subset of the data.

Depending on the available data, filters may include:

• Year / Date
• Month
• Ward
• Facility
• Diagnosis / Disease
• Gender
• Age Group

Important:

Always check the selected filters before interpreting any number.

If a filter is applied, all charts and indicators may represent only the
selected subset of data.
"""
    },

    {
        "title": "6. Overview / Summary",
        "content": """
The Overview section provides the high-level programme situation.

Users should review:

• Total cases / records
• Number of wards
• Number of facilities
• Major diagnosis categories
• Overall burden
• Available programme indicators

The Overview page should answer:

“What is the overall situation?”
"""
    },

    {
        "title": "7. Monthly / Time-wise Analysis",
        "content": """
Monthly analysis shows how the reported programme burden changes over time.

Users should review:

• Highest-burden month
• Lowest-burden month
• Month-to-month changes
• Overall trend
• Year-wise comparison where available
• Diagnosis-wise monthly trend

An increase in reported cases should be interpreted along with testing,
reporting completeness, surveillance activity and other programme factors.
"""
    },

    {
        "title": "8. Ward-wise Analysis",
        "content": """
Ward Analysis helps identify the geographic concentration of reported burden.

Users should review:

• Total cases by ward
• Top burden wards
• Ward ranking
• Ward-wise diagnosis
• Ward-wise gender distribution
• Ward-wise monthly trend
• Facility distribution within wards

Important:

A high reported burden should be verified with field information and data
quality before drawing programme conclusions.
"""
    },

    {
        "title": "9. Facility-wise Analysis",
        "content": """
Facility Analysis helps compare health facilities.

Users should review:

• Total cases by facility
• High-burden facilities
• Facility trend
• Diagnosis distribution
• Ward-wise facility distribution

When a facility shows an unusual increase, review the underlying records,
reporting completeness and relevant programme activities.
"""
    },

    {
        "title": "10. Age-wise Analysis",
        "content": """
Age-wise analysis identifies the age groups contributing to the reported
burden.

Users should review:

• Age-group distribution
• Number of cases by age group
• Percentage distribution where available
• Changes in age distribution over time

Age findings should be interpreted according to the programme context.
"""
    },

    {
        "title": "11. Gender-wise Analysis",
        "content": """
Gender-wise analysis shows the distribution of reported cases by gender.

Users should review:

• Male
• Female
• Other
• Not Reported / Unknown

Both absolute numbers and percentages should be considered where appropriate.

Missing gender information should also be reviewed during data-quality
assessment.
"""
    },

    {
        "title": "12. Map / Geographic View",
        "content": """
The Map section provides a geographic representation of facilities and/or
wards where location information is available.

It can help users visually understand:

• Facility locations
• Ward distribution
• Geographic concentration
• High-burden areas

The map is a management visualization tool. Incorrect or missing coordinates
may affect geographic interpretation.
"""
    },

    {
        "title": "13. Data Explorer",
        "content": """
Data Explorer provides access to filtered records.

Users can generally:

• Search records
• Select columns
• Sort information
• Review individual records
• Download filtered data where enabled

Recommended approach:

If a chart shows an unusual value, use Data Explorer to verify the
underlying records.
"""
    },

    {
        "title": "14. Data Quality",
        "content": """
Data quality should be checked before final programme interpretation.

Review:

• Missing values
• Duplicate records
• Missing ward
• Missing facility
• Missing date/month
• Missing age
• Missing gender
• Missing diagnosis
• Invalid or inconsistent entries

Poor-quality data can result in misleading management indicators.
"""
    },

    {
        "title": "15. Prediction / Trend Analysis",
        "content": """
The Prediction section provides a trend-based estimate using historical
monthly data.

The current approach is intended for management planning and trend
interpretation.

It should NOT be interpreted as a confirmed future case count.

Increasing Trend:

Historical data show an overall upward movement.

Decreasing Trend:

Historical data show an overall downward movement.

Stable:

Historical data show no strong overall upward or downward movement.
"""
    },

    {
        "title": "16. How to Interpret Prediction Results",
        "content": """
Prediction results should be understood as:

“If the historical pattern continues, the estimated future burden may follow
a similar direction.”

The estimate may be affected by:

• Data completeness
• Seasonal variation
• Sudden outbreaks
• Changes in surveillance
• Changes in testing
• Changes in reporting
• Programme interventions
• Population movement

Therefore, prediction should support planning and discussion rather than
replace programme judgement.
"""
    },

    {
        "title": "17. Management Review Framework",
        "content": """
For every important finding, ask:

WHAT?
What is happening?

WHERE?
Which ward or facility is affected?

WHEN?
During which month or period?

WHO?
Which age or gender group is contributing?

WHY?
What programme or reporting factors may explain the finding?

WHAT NEXT?
What verification or management action is required?
"""
    },

    {
        "title": "18. Suggested Monthly Review Process",
        "content": """
1. Open Overview.
2. Check total burden.
3. Review monthly trend.
4. Identify high-burden wards.
5. Identify high-burden facilities.
6. Review age-wise distribution.
7. Review gender-wise distribution.
8. Review diagnosis-wise distribution.
9. Check geographic map.
10. Review data quality.
11. Verify unusual findings in Data Explorer.
12. Review trend / prediction indicators.
13. Document programme actions required.
"""
    },

    {
        "title": "19. Important Do's",
        "content": """
• Always check filters before interpreting data.
• Review monthly trends, not only totals.
• Verify unusually high values.
• Check data quality before final reporting.
• Compare ward and facility information.
• Review underlying records when required.
• Consider reporting completeness.
• Maintain confidentiality of beneficiary information.
• Use the latest available data version.
"""
    },

    {
        "title": "20. Important Don'ts",
        "content": """
• Do not assume every dashboard value is correct without checking data quality.
• Do not classify an area as an outbreak based only on a dashboard number.
• Do not compare facilities without considering reporting and population context.
• Do not treat prediction as a confirmed future case count.
• Do not ignore missing or duplicate records.
• Do not share confidential individual-level information unnecessarily.
• Do not make programme conclusions based on a single chart.
"""
    },

    {
        "title": "21. Troubleshooting",
        "content": """
Dashboard not updating:

Check internet connectivity, selected filters and data availability.

No data displayed:

Clear restrictive filters and check whether the selected period, ward or
facility contains data.

Unexpectedly high number:

Check date, facility, ward, diagnosis, duplicate records and reporting
completeness.

Map is empty:

Check whether valid geographic coordinates are available.

Prediction appears unreliable:

Check the number of historical months, missing months and data completeness.
"""
    },

    {
        "title": "22. Data Confidentiality",
        "content": """
The application may contain programme and beneficiary-related information.

Users should:

• Use the application only for authorised programme purposes.
• Avoid unnecessary sharing of individual-level information.
• Follow applicable departmental data-security policies.
• Download and circulate data only when authorised.
• Protect exported files appropriately.
"""
    },

    {
        "title": "23. Quick Reference",
        "content": """
Overall situation → Overview

Monthly comparison → Charts & Trends

Highest burden ward → Ward Analysis

Highest burden facility → Facility Analysis

Age distribution → Demographics & Disease

Gender distribution → Demographics & Disease

Geographic distribution → Map View

Individual record verification → Data Explorer

Missing / duplicate data → Data Explorer / Data Quality

Historical trend → Charts & Trends

Future planning indicator → Prediction
"""
    },

    {
        "title": "24. Final Note",
        "content": """
The dashboard is designed to support programme managers in moving from:

DATA → INFORMATION → INTERPRETATION → VERIFICATION → ACTION

Dashboard findings should be considered together with field verification,
programme knowledge and data-quality assessment.
"""
    },
]


# ============================================================
# PDF GENERATOR
# ============================================================

def create_manual_pdf():

    if not REPORTLAB_AVAILABLE:
        return None

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Health Programme Management Dashboard - User Manual",
        author="Health Facility Monitor",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ManualTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=23,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ManualSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=11,
        leading=15,
        spaceAfter=20,
    )

    heading_style = ParagraphStyle(
        "ManualHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        spaceBefore=10,
        spaceAfter=7,
    )

    body_style = ParagraphStyle(
        "ManualBody",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        spaceAfter=7,
    )

    story = []

    story.append(
        Paragraph(
            "HEALTH PROGRAMME MANAGEMENT DASHBOARD",
            title_style,
        )
    )

    story.append(
        Paragraph(
            "User Manual & Operating Instructions",
            subtitle_style,
        )
    )

    intro_data = [
        ["Document", "User Manual"],
        ["Version", "1.0"],
        ["Purpose", "Programme Monitoring & Management Support"],
    ]

    intro_table = Table(
        intro_data,
        colWidths=[40 * mm, 115 * mm],
    )

    intro_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    story.append(intro_table)
    story.append(Spacer(1, 12))

    for section in MANUAL_SECTIONS:

        story.append(
            Paragraph(
                section["title"],
                heading_style,
            )
        )

        paragraphs = section["content"].strip().split("\n\n")

        for para in paragraphs:

            cleaned = para.strip()

            if not cleaned:
                continue

            # Escape special HTML characters
            cleaned = (
                cleaned
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            lines = cleaned.split("\n")

            for line in lines:

                line = line.strip()

                if not line:
                    story.append(Spacer(1, 4))
                    continue

                story.append(
                    Paragraph(
                        line,
                        body_style,
                    )
                )

    story.append(Spacer(1, 15))

    story.append(
        Paragraph(
            "End of User Manual",
            ParagraphStyle(
                "EndStyle",
                parent=body_style,
                alignment=TA_CENTER,
                fontSize=9,
            ),
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer


# ============================================================
# INFORMATION CARD
# ============================================================

def show_info_card(title, text):

    st.info(
        f"**{title}**\n\n{text}"
    )


# ============================================================
# MAIN USER MANUAL PAGE
# ============================================================

def render_manual(df=None):

    # --------------------------------------------------------
    # PAGE TITLE
    # --------------------------------------------------------

    st.title("📘 User Manual & Instructions")

    st.caption(
        "Health Programme Management Dashboard"
    )

    st.divider()

    # --------------------------------------------------------
    # DOWNLOAD PDF
    # --------------------------------------------------------

    col1, col2 = st.columns([1.4, 3])

    with col1:

        pdf_file = create_manual_pdf()

        if pdf_file is not None:

            st.download_button(
                label="📥 Download User Manual (PDF)",
                data=pdf_file,
                file_name="Health_Programme_Dashboard_User_Manual.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        else:

            st.warning(
                "PDF download is unavailable because the "
                "reportlab package is not installed."
            )

    with col2:

        st.success(
            "Use this page as the operating guide for the dashboard."
        )

    st.divider()

    # --------------------------------------------------------
    # QUICK START
    # --------------------------------------------------------

    st.header("🚀 Quick Start")

    show_info_card(
        "Step 1 — Select Filters",
        "Select the required Year, Month, Ward, Facility, Disease or "
        "other available filters. Always check the selected filters "
        "before interpreting the results.",
    )

    show_info_card(
        "Step 2 — Check Overall Situation",
        "Start with Overview to understand the overall programme burden "
        "and coverage.",
    )

    show_info_card(
        "Step 3 — Identify Priority Areas",
        "Use Ward Analysis and Facility Analysis to identify areas with "
        "higher reported burden or changing trends.",
    )

    show_info_card(
        "Step 4 — Verify Findings",
        "Use Data Explorer and data-quality checks to verify unusual "
        "or unexpected findings.",
    )

    show_info_card(
        "Step 5 — Plan Action",
        "Use historical trends and prediction indicators as management "
        "support for programme review and planning.",
    )

    st.divider()

    # --------------------------------------------------------
    # SECTION SELECTOR
    # --------------------------------------------------------

    st.header("📚 Manual Sections")

    section_names = [
        section["title"]
        for section in MANUAL_SECTIONS
    ]

    selected_section = st.selectbox(
        "Select a section",
        ["All Sections"] + section_names,
    )

    st.divider()

    # --------------------------------------------------------
    # CONTENT DISPLAY
    # --------------------------------------------------------

    if selected_section == "All Sections":

        for section in MANUAL_SECTIONS:

            st.subheader(section["title"])

            content = section["content"].strip()

            lines = content.split("\n")

            for line in lines:

                line = line.strip()

                if not line:
                    continue

                if line.startswith("•"):

                    st.markdown(
                        f"- {line[1:].strip()}"
                    )

                elif line.endswith(":") and len(line) < 80:

                    st.markdown(
                        f"**{line}**"
                    )

                else:

                    st.write(line)

            st.divider()

    else:

        selected_data = None

        for section in MANUAL_SECTIONS:

            if section["title"] == selected_section:

                selected_data = section
                break

        if selected_data:

            st.subheader(
                selected_data["title"]
            )

            content = selected_data["content"].strip()

            lines = content.split("\n")

            for line in lines:

                line = line.strip()

                if not line:
                    continue

                if line.startswith("•"):

                    st.markdown(
                        f"- {line[1:].strip()}"
                    )

                elif line.endswith(":") and len(line) < 80:

                    st.markdown(
                        f"**{line}**"
                    )

                else:

                    st.write(line)

    # --------------------------------------------------------
    # IMPORTANT NOTE
    # --------------------------------------------------------

    st.divider()

    st.warning(
        "Important: Dashboard outputs are intended for programme "
        "monitoring and management support. Reported burden, trends "
        "and prediction indicators should be interpreted together "
        "with data quality, reporting completeness, field information "
        "and programme context."
    )


# ============================================================
# COMPATIBILITY ALIASES
# ============================================================

def render_user_manual(df=None):
    return render_manual(df)


def render_help(df=None):
    return render_manual(df)


def render_instructions(df=None):
    return render_manual(df)
