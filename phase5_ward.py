import pandas as pd
import plotly.express as px
import streamlit as st
from phase2_overview import apply_filters, create_filters

def _layout(fig, height=450):
    fig.update_layout(height=height, margin=dict(l=20,r=20,t=60,b=20),
                      legend_title_text="", hovermode="x unified")
    return fig

def render_ward(df):
    filters = create_filters(df)
    filtered_df = apply_filters(df, **filters)

    st.title("🏙️ Ward-wise Management Analysis")
    st.caption("Ward burden, disease pattern, facility coverage and monthly trends.")

    if filtered_df.empty:
        st.warning("No records match the selected filters.")
        return

    ward_counts = filtered_df["Ward"].dropna().value_counts() if "Ward" in filtered_df.columns else pd.Series(dtype="int64")
    top_ward = ward_counts.index[0] if not ward_counts.empty else "N/A"
    top_ward_cases = int(ward_counts.iloc[0]) if not ward_counts.empty else 0

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Total Cases", f"{len(filtered_df):,}")
    k2.metric("Wards Covered", f"{filtered_df['Ward'].nunique(dropna=True):,}" if "Ward" in filtered_df.columns else "0")
    k3.metric("Facilities Covered", f"{filtered_df['Facility Name Lform'].nunique(dropna=True):,}" if "Facility Name Lform" in filtered_df.columns else "0")
    k4.metric("Top Burden Ward", f"{top_ward} ({top_ward_cases:,})")

    st.divider()
    st.subheader("🏆 Ward-wise Case Burden Ranking")

    if "Ward" in filtered_df.columns:
        ward_table = filtered_df["Ward"].dropna().value_counts().rename_axis("Ward").reset_index(name="Cases")
        ward_table["Share (%)"] = (ward_table["Cases"] / ward_table["Cases"].sum() * 100).round(2)
        ward_table.insert(0, "Rank", range(1, len(ward_table)+1))
        st.dataframe(ward_table, use_container_width=True, hide_index=True)

        fig = px.bar(ward_table.head(20).sort_values("Cases"), x="Cases", y="Ward",
                     orientation="h", text="Cases", title="Top 20 Wards by Case Burden")
        fig.update_traces(textposition="outside")
        st.plotly_chart(_layout(fig, 650), use_container_width=True)

    st.divider()
    st.subheader("🦠 Ward × Disease Burden")

    if "Ward" in filtered_df.columns and "Confirmed Diagnosis" in filtered_df.columns:
        top_wards = filtered_df["Ward"].dropna().value_counts().head(15).index
        top_diseases = filtered_df["Confirmed Diagnosis"].dropna().value_counts().head(10).index
        matrix_df = filtered_df[filtered_df["Ward"].isin(top_wards) & filtered_df["Confirmed Diagnosis"].isin(top_diseases)]
        if not matrix_df.empty:
            heatmap = pd.crosstab(matrix_df["Ward"], matrix_df["Confirmed Diagnosis"])
            fig = px.imshow(heatmap, text_auto=True, aspect="auto",
                            title="Top 15 Wards × Top 10 Diseases",
                            labels={"x":"Confirmed Diagnosis","y":"Ward","color":"Cases"})
            st.plotly_chart(_layout(fig, 650), use_container_width=True)

    st.divider()
    st.subheader("🏥 Ward-wise Facility Coverage")

    if "Ward" in filtered_df.columns and "Facility Name Lform" in filtered_df.columns:
        agg = {"Cases": ("Ward","size"), "Facilities": ("Facility Name Lform","nunique")}
        if "Confirmed Diagnosis" in filtered_df.columns:
            agg["Diseases"] = ("Confirmed Diagnosis","nunique")
        ward_facility = (filtered_df.dropna(subset=["Ward","Facility Name Lform"])
                         .groupby("Ward").agg(**agg).reset_index()
                         .sort_values(["Cases","Facilities"], ascending=[False,False]))
        st.dataframe(ward_facility.head(100), use_container_width=True, hide_index=True)

    st.subheader("👥 Ward-wise Gender Distribution")

    if "Ward" in filtered_df.columns and "Gender" in filtered_df.columns:
        top_wards = filtered_df["Ward"].dropna().value_counts().head(15).index
        gender_df = (filtered_df[filtered_df["Ward"].isin(top_wards) & filtered_df["Gender"].notna()]
                     .groupby(["Ward","Gender"]).size().reset_index(name="Cases"))
        if not gender_df.empty:
            fig = px.bar(gender_df, x="Ward", y="Cases", color="Gender",
                         barmode="group", title="Gender Distribution in Top 15 Wards")
            st.plotly_chart(_layout(fig, 500), use_container_width=True)

    st.subheader("📅 Ward-wise Monthly Trend")

    if "Ward" in filtered_df.columns and "Month" in filtered_df.columns:
        top10 = filtered_df["Ward"].dropna().value_counts().head(10).index
        monthly = (filtered_df[filtered_df["Ward"].isin(top10)]
                   .dropna(subset=["Ward","Month"])
                   .groupby(["Month","Ward"]).size().reset_index(name="Cases"))
        if not monthly.empty:
            order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            monthly["Month"] = pd.Categorical(monthly["Month"], categories=order, ordered=True)
            monthly = monthly.sort_values(["Month","Ward"])
            fig = px.line(monthly, x="Month", y="Cases", color="Ward", markers=True,
                          title="Monthly Case Trend — Top 10 Wards")
            st.plotly_chart(_layout(fig, 520), use_container_width=True)

    st.divider()
    st.subheader("📋 Ward Management Summary")

    if "Ward" in filtered_df.columns:
        agg = {"Cases": ("Ward","size")}
        if "Facility Name Lform" in filtered_df.columns:
            agg["Facilities"] = ("Facility Name Lform","nunique")
        if "Confirmed Diagnosis" in filtered_df.columns:
            agg["Diseases"] = ("Confirmed Diagnosis","nunique")
        summary = filtered_df.dropna(subset=["Ward"]).groupby("Ward").agg(**agg).reset_index()
        summary["Share (%)"] = (summary["Cases"] / summary["Cases"].sum() * 100).round(2)
        summary = summary.sort_values("Cases", ascending=False).reset_index(drop=True)
        summary.insert(0, "Rank", range(1, len(summary)+1))
        st.dataframe(summary, use_container_width=True, hide_index=True)
