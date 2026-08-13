#!/usr/bin/env python3
"""
Cyber Threat Identifier — Query workflow

Main query interface for mapping incident narratives to ATT&CK techniques.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd

from src.retrieval.embedding_model import get_embedding_model
from src.database.db_connection import get_connection
from src.generation.answer_generator import generate_candidate_answer
from src.retrieval.vector import embed_query, retrieve_vector_candidates


def render_query_interface() -> None:
    """Render the incident → ATT&CK mapping interface."""

    st.subheader("Incident narrative")
    query = st.text_area(
        "Describe the incident:",
        placeholder="E.g., 'Attackers used PowerShell scripts to download and execute malware...'",
        height=150,
        label_visibility="collapsed",
    )

    st.markdown("**Or try a sample query:**")

    # Optional sample queries from evaluation file
    try:
        rewrite_df = pd.read_csv(
            "data/evaluation_reports/local/expert_query_rewrite_retrieval_results.csv"
        )
        sample_cases = rewrite_df.drop_duplicates(subset=["eval_id"]).head(10)
        sample_options = [
            f"{row['eval_id']}: {row['query_text'][:80]}..."
            for _, row in sample_cases.iterrows()
        ]

        selected_sample = st.selectbox("Select:", [""] + sample_options)
        if selected_sample:
            eval_id = selected_sample.split(":")[0]
            matching_row = sample_cases[sample_cases["eval_id"] == eval_id].iloc[0]
            query = matching_row["query_text"]
            st.info("Sample query loaded. You can edit it before running analysis.")
    except Exception as e:
        st.caption(f"Sample queries unavailable: {e}")

    run_button = st.button(
        "🔍 Analyze",
        type="primary",
        disabled=not query.strip(),
    )

    if not run_button:
        return

    with st.spinner("Analyzing incident and retrieving candidate techniques..."):
        try:
            embedding_model = get_embedding_model()
            query_embedding = embed_query(query, embedding_model)

            with get_connection() as conn:
                candidates = retrieve_vector_candidates(
                    conn, query_embedding, top_k=5, rerank=True
                )

            answer = generate_candidate_answer(query, candidates)

        except Exception as e:
            st.error(f"❌ Error during analysis: {e}")
            return

    st.success("✅ Analysis complete")

    # Answer
    st.markdown("### Generated answer")
    st.markdown(answer.get("answer_text", "").strip() or "_No answer text returned._")

    # Retrieved techniques
    st.markdown("### Retrieved techniques")
    if not candidates:
        st.info("No techniques were retrieved for this query.")
    else:
        for i, candidate in enumerate(candidates, 1):
            with st.expander(
                f"#{i}: {candidate.get('technique_id', 'N/A')} "
                f"— {candidate.get('technique_name', 'Unknown')} "
                f"(score: {candidate.get('score', 0):.3f})"
            ):
                st.markdown(f"**Technique ID:** `{candidate.get('technique_id', 'N/A')}`")
                st.markdown(f"**Name:** {candidate.get('technique_name', 'Unknown')}")
                st.markdown("**Description**")
                st.write(candidate.get("description", "No description available."))

    # Feedback
    st.markdown("### Feedback")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Helpful", key="feedback_up"):
            st.success("Thanks for the feedback!")
    with col2:
        if st.button("👎 Not helpful", key="feedback_down"):
            st.success("Thanks for the feedback!")


if __name__ == "__main__":
    # Standalone mode (if you ever run `streamlit run app/query.py`)
    st.set_page_config(
        page_title="Cyber Threat Identifier — Query",
        page_icon="🔍",
        layout="wide",
    )
    st.title("🔍 Query Interface")
    render_query_interface()