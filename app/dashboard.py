#!/usr/bin/env python3
"""
Monitoring Dashboard — 5 charts for project evaluation
"""
from __future__ import annotations


import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime as dt



def render_monitoring_dashboard() -> None:
    """Render the monitoring dashboard inside a tab or standalone."""

    # Chart 1: Latency distribution
    st.subheader("1️⃣ Answer Generation Latency Distribution")

    try:
        df = pd.read_csv("data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv")

        fig = px.histogram(
            df,
            x="latency_seconds",
            nbins=30,
            title="Latency Distribution (All Models)",
            labels={"latency_seconds": "Latency (seconds)"},
            color_discrete_sequence=["#3498db"],
        )
        fig.add_vline(
            x=df["latency_seconds"].median(),
            line_dash="dash",
            line_color="red",
            annotation_text=f"Median: {df['latency_seconds'].median():.2f}s",
        )
        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.error(f"Could not load latency data: {e}")

    # Chart 2: Judge preferences (3.5 as judge)
    st.subheader("2️⃣ Judge Preferences: Gemini 3.5 Flash-Lite as Judge")

    try:
        judge_35 = pd.read_csv("data/evaluation_reports/reranked/expert_llm_judged_reranked_35_as_judge.csv")
        prefs_35 = judge_35["winner"].value_counts()

        fig = px.bar(
            x=prefs_35.index,
            y=prefs_35.values,
            title="Judge Preferences: Gemini 3.5 Flash-Lite",
            labels={"x": "Model", "y": "Count"},
            color=prefs_35.index,
            color_discrete_map={
                "gemini-3.1-flash-lite": "#3498db",
                "gemini-3.5-flash-lite": "#2ecc71",
            },
        )
        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.error(f"Could not load judge data (3.5): {e}")

    # Chart 3: Judge preferences (3.1 as judge)
    st.subheader("3️⃣ Judge Preferences: Gemini 3.1 Flash-Lite as Judge")

    try:
        judge_31 = pd.read_csv("data/evaluation_reports/reranked/expert_llm_judged_reranked_31_as_judge.csv")
        prefs_31 = judge_31["winner"].value_counts()

        fig = px.bar(
            x=prefs_31.index,
            y=prefs_31.values,
            title="Judge Preferences: Gemini 3.1 Flash-Lite",
            labels={"x": "Model", "y": "Count"},
            color=prefs_31.index,
            color_discrete_map={
                "gemini-3.1-flash-lite": "#3498db",
                "gemini-3.5-flash-lite": "#2ecc71",
            },
        )
        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.error(f"Could not load judge data (3.1): {e}")

    # Chart 4: Retrieval method comparison
    st.subheader("4️⃣ Retrieval Method Comparison (MRR & Hit@3)")

    try:
        methods = ["Vector Only", "Vector+Rerank", "Query Rewrite+Rerank"]
        mrr = [0.3134, 0.3578, 0.3940]
        hit3 = [0.3540, 0.4159, 0.4690]

        df = pd.DataFrame({
            "Method": methods * 2,
            "Score": mrr + hit3,
            "Metric": ["MRR"] * 3 + ["Hit@3"] * 3,
        })

        fig = px.bar(
            df,
            x="Method",
            y="Score",
            color="Metric",
            barmode="group",
            title="Retrieval Method Comparison (MRR & Hit@3)",
            color_discrete_sequence=["#3498db", "#2ecc71"],
        )
        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.error(f"Could not load retrieval comparison data: {e}")

    # Chart 5: Judge agreement rate
    st.subheader("5️⃣ Judge Agreement Rate")

    try:
        agreement = pd.read_csv("data/evaluation_reports/reranked/judge_agreement_summary.csv")
        agree_rate = agreement["agreement_rate"].iloc[0]

        fig = px.pie(
            values=[agree_rate, 1 - agree_rate],
            names=["Agreement", "Disagreement"],
            title=f"Judge Agreement Rate: {agree_rate:.2%}",
            color_discrete_sequence=["#2ecc71", "#e74c3c"],
        )
        st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.error(f"Could not load agreement data: {e}")

    # Chart 6: User feedback distribution
    st.subheader("6️⃣ User Feedback Distribution")

    feedback_path = Path("data/feedback/feedback.csv")

    if not feedback_path.exists():
        st.info("No feedback collected yet. Use the main app to submit feedback!")
    else:
        feedback_df = pd.read_csv(feedback_path)

        if feedback_df.empty or "feedback" not in feedback_df.columns:
            st.info("No feedback collected yet. Use the main app to submit feedback!")
        else:
            counts = feedback_df["feedback"].value_counts()

            fig = px.bar(
                x=counts.index,
                y=counts.values,
                title="User Feedback (Thumbs Up/Down)",
                labels={"x": "Feedback Type", "y": "Count"},
                color=counts.index,
                color_discrete_map={
                    "thumbs_up": "#2ecc71",
                    "thumbs_down": "#e74c3c",
                },
            )
            st.plotly_chart(fig, width="stretch")

    # Footer
    st.divider()
    st.markdown(
        f"""
        <div style='text-align: center; color: gray; font-size: 0.9em;'>
            <b>Monitoring Dashboard</b> | Last updated: {dt.now().strftime("%Y-%m-%d %H:%M")}
        </div>
        """,
        unsafe_allow_html=True,
    )



if __name__ == "__main__":
    # Standalone mode if you ever want to run `streamlit run app/dashboard.py`
    st.set_page_config(
        page_title="Dashboard",
        page_icon="📊",
        layout="wide",
    )
    render_monitoring_dashboard()