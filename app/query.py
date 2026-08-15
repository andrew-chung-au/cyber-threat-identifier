#!/usr/bin/env python3
"""
Cyber Threat Identifier — Query workflow

Uses vector retrieval + local cross-encoder reranking (DEC-018).
"""
from __future__ import annotations

import os
import uuid

import streamlit as st
import pandas as pd

from src.database.db_connection import get_connection
from src.generation.answer_generator import generate_candidate_answer
from src.retrieval.embedding_model import get_embedding_model
from src.retrieval.reranked_vector import retrieve_reranked_vector
from src.retrieval.reranker import get_reranker_model
from src.retrieval.generation_context import fetch_records_for_generation
from src.monitoring.feedback_store import save_feedback


def render_query_interface() -> None:
    st.subheader("Incident narrative")
    query = st.text_area(
        "Describe the incident:",
        placeholder="E.g., 'Attackers used PowerShell scripts to download and execute malware...'",
        height=150,
        label_visibility="collapsed",
    )

    st.markdown("**Or try a sample query:**")

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

    if run_button:
        with st.spinner(
            "Analyzing incident and retrieving candidate techniques..."
        ):
            try:
                embedding_model = get_embedding_model()
                reranker_model = get_reranker_model()

                with get_connection(register_pgvector=True) as connection:
                    reranked_result = retrieve_reranked_vector(
                        connection=connection,
                        embedding_model=embedding_model,
                        reranker_model=reranker_model,
                        query_text=query,
                        candidate_k=20,
                        top_k=5,
                    )

                    retrieved_ids = [
                        candidate.attack_id
                        for candidate in reranked_result.candidates
                    ]

                    retrieved_rows = fetch_records_for_generation(
                        connection=connection,
                        attack_ids=retrieved_ids,
                    )

                generation_result = generate_candidate_answer(
                    incident_narrative=query,
                    retrieved_rows=retrieved_rows,
                )

                st.session_state.analysis_result = {
                    "query_id": str(uuid.uuid4()),
                    "query": query,
                    "answer": generation_result.answer,
                    "model_id": os.getenv("MODEL_ID"),  # no fallback; must be set in .env
                    "retrieved_ids": retrieved_ids,
                    "retrieval_ms": reranked_result.total_retrieval_ms,
                    "feedback_submitted": False,
                }

            except Exception as error:
                st.error(f"❌ Error during analysis: {error}")
                return

    result = st.session_state.get("analysis_result")
    if not result:
        return

    query = result["query"]
    answer = result["answer"]

    st.success("✅ Analysis complete")

    st.markdown("### Generated answer")
    st.markdown(answer.answer_summary)

    with st.expander("Retrieval grounding note"):
        st.write(answer.retrieval_grounding_note)

    with st.expander("Uncertainty note"):
        st.write(answer.uncertainty_note)

    st.markdown("### Retrieved techniques")
    if not result["retrieved_ids"]:
        st.info("No techniques were retrieved for this query.")
    else:
        with get_connection() as connection:
            rows = fetch_records_for_generation(
                connection=connection,
                attack_ids=result["retrieved_ids"],
            )

        for i, row in enumerate(rows, 1):
            with st.expander(
                f"#{i}: {row['attack_id']} — {row['name']} "
                f"(retrieved via reranking)"
            ):
                st.markdown(f"**Technique ID:** `{row['attack_id']}`")
                st.markdown(f"**Name:** {row['name']}")
                st.markdown("**Description**")
                st.write(row["description_clean"])


    st.markdown("### Feedback")
    st.caption(
        "Feedback is saved with the query and generated answer "
        "to support system evaluation."
    )

    if result.get("feedback_submitted", False):
        st.success("Thanks — your feedback has been recorded.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            helpful_clicked = st.button(
                "👍 Helpful",
                key=f"feedback_up_{result['query_id']}",
            )

        with col2:
            not_helpful_clicked = st.button(
                "👎 Not helpful",
                key=f"feedback_down_{result['query_id']}",
            )

        selected_feedback = None
        if helpful_clicked:
            selected_feedback = "thumbs_up"
        elif not_helpful_clicked:
            selected_feedback = "thumbs_down"

        if selected_feedback:
            try:
                saved_path = save_feedback(
                    query_id=result["query_id"],
                    feedback=selected_feedback,
                    model_id=result["model_id"],
                    query_text=result["query"],
                    answer_text=result["answer"].model_dump_json(),
                    retrieved_technique_ids=result["retrieved_ids"],
                )

                st.session_state.analysis_result["feedback_submitted"] = True
                st.success(f"Feedback saved to `{saved_path}`.")
                st.rerun()

            except Exception as error:
                st.error(f"Could not save feedback: {error}")


if __name__ == "__main__":
    st.set_page_config(
        page_title="Cyber Threat Identifier — Query",
        page_icon="🔍",
        layout="wide",
    )
    st.title("🔍 Query Interface")
    render_query_interface()