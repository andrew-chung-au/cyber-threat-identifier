#!/usr/bin/env python3
"""Manual review workflow for reranked and vector-only judge disagreement cases."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVAL_REPORTS = PROJECT_ROOT / "data" / "evaluation_reports"

DATASETS = {
    "reranked": {
        "label": "Reranked v1 — 55 judge disagreements",
        "queue": EVAL_REPORTS / "reranked" / "manual_review_queue.csv",
        "results": EVAL_REPORTS / "reranked" / "manual_review_results.csv",
    },
    "vector": {
        "label": "Vector-only baseline — 57 judge disagreements",
        "queue": EVAL_REPORTS / "vector" / "manual_review_queue.csv",
        "results": EVAL_REPORTS / "vector" / "manual_review_results.csv",
    },
}

MODEL_31 = "gemini-3.1-flash-lite"
MODEL_35 = "gemini-3.5-flash-lite"

RESULT_FIELDS = [
    "reviewed_at_utc",
    "eval_id",
    "winner",
    "failure_modes",
    "review_notes",
    "answer_a_model",
    "answer_b_model",
    "judge_31_winner",
    "judge_35_winner",
    "judge_31_agrees",
    "judge_35_agrees",
]

FAILURE_MODES = [
    "Unsupported or hallucinated technique",
    "Incorrect technique mapping",
    "Missed expected technique",
    "Weak grounding in narrative",
    "Inadequate uncertainty handling",
    "Retrieved-context contamination",
    "Unclear analyst-facing explanation",
    "No material issue",
    "Other",
]


def _load_results(results_path: Path) -> pd.DataFrame:
    if not results_path.exists() or results_path.stat().st_size == 0:
        return pd.DataFrame(columns=RESULT_FIELDS)
    return pd.read_csv(results_path)


def _load_json(value: Any) -> Any:
    if pd.isna(value) or not str(value).strip():
        return []
    return json.loads(value)


def _judge_agreement(judge_winner: str, manual_winner: str) -> str:
    if manual_winner == "tie":
        return "not_applicable"
    return str(judge_winner == manual_winner).lower()


def _save_review(record: dict[str, str], results_path: Path) -> None:
    results_path.parent.mkdir(parents=True, exist_ok=True)
    exists = results_path.exists() and results_path.stat().st_size > 0

    with results_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(record)


def _render_techniques(techniques: list[dict[str, Any]]) -> None:
    if not techniques:
        st.caption("No technique records available.")
        return

    for technique in techniques:
        attack_id = technique.get("attack_id", "Unknown ID")
        name = technique.get("name", "Unknown technique")
        tactics = ", ".join(technique.get("tactics") or []) or "Not specified"
        description = technique.get("description", "")

        st.markdown(f"**{attack_id} — {name}**")
        st.caption(f"Tactics: {tactics}")
        if description:
            st.write(description)


def _render_answer(answer: dict[str, Any]) -> None:
    primary = answer.get("primary_attack_id") or "No primary technique selected"
    alternatives = answer.get("alternative_attack_ids") or "None"
    supporting = answer.get("supporting_attack_ids") or "None"
    review_required = answer.get("review_required")

    st.markdown(f"**Primary technique:** `{primary}`")
    st.markdown(f"**Alternative techniques:** `{alternatives}`")
    st.markdown(f"**Supporting techniques:** `{supporting}`")
    st.markdown(f"**Analyst summary:** {answer.get('answer_summary') or 'No summary returned.'}")
    st.markdown(
        f"**Grounding note:** {answer.get('retrieval_grounding_note') or 'No grounding note returned.'}"
    )
    st.markdown(
        f"**Uncertainty note:** {answer.get('uncertainty_note') or 'No uncertainty note returned.'}"
    )
    st.markdown(f"**Review required:** {'Yes' if review_required else 'No'}")


def _render_last_saved_audit(
    queue: pd.DataFrame,
    eval_id: str,
) -> None:
    rows = queue[queue["eval_id"].astype(str) == str(eval_id)]
    if rows.empty:
        return

    row = rows.iloc[0]
    with st.expander("Last saved review: reveal identities and judge reasoning", expanded=False):
        st.markdown(f"**Case:** `{eval_id}`")
        st.markdown(f"**Answer A model:** `{row['model_a']}`")
        st.markdown(f"**Answer B model:** `{row['model_b']}`")
        st.markdown(
            f"**Gemini 3.1 judge:** `{row['winner_31']}` "
            f"(confidence: {row['confidence_31']})"
        )
        st.write(row["reasoning_31"])
        st.markdown(
            f"**Gemini 3.5 judge:** `{row['winner_35']}` "
            f"(confidence: {row['confidence_35']})"
        )
        st.write(row["reasoning_35"])


def render_evaluation_review() -> None:
    st.subheader("Manual Review: Judge Disagreements")
    st.caption(
        "Choose the better answer before model identities and LLM-judge reasoning are revealed. "
        "Expected ATT&CK labels and retrieved context are visible because this is an expert "
        "correctness review, not an end-user preference test."
    )

    dataset_key = st.radio(
        "Evaluation dataset",
        options=["reranked", "vector"],
        format_func=lambda key: DATASETS[key]["label"],
        horizontal=True,
        index=0,
    )

    dataset = DATASETS[dataset_key]
    queue_path = dataset["queue"]
    results_path = dataset["results"]

    if not queue_path.exists():
        st.warning(
            f"Manual-review queue not found for {dataset['label']}. "
            "Run: `uv run python -m src.evaluation.build_manual_review_queue` "
            f"with the appropriate inputs to create `{queue_path}`."
        )
        return

    queue = pd.read_csv(queue_path).sort_values("eval_id").reset_index(drop=True)
    results = _load_results(results_path)
    reviewed_ids = set(results["eval_id"].astype(str)) if not results.empty else set()
    pending = queue[~queue["eval_id"].astype(str).isin(reviewed_ids)].reset_index(drop=True)

    progress_left, progress_right = st.columns(2)
    progress_left.metric("Reviewed", len(reviewed_ids))
    progress_right.metric("Remaining", len(pending))

    last_saved = st.session_state.get("last_saved_review_eval_id")
    if last_saved:
        _render_last_saved_audit(queue, last_saved)

    if pending.empty:
        st.success(f"All {dataset['label'].split('—')[0].strip()} cases are complete.")
        st.caption(f"Results saved to: `{results_path.relative_to(PROJECT_ROOT)}`")
        return

    case = pending.iloc[0]
    eval_id = str(case["eval_id"])
    answer_a = _load_json(case["answer_a_json"])
    answer_b = _load_json(case["answer_b_json"])
    expected = _load_json(case["expected_techniques_json"])
    retrieved_31 = _load_json(case["retrieved_techniques_31_json"])
    retrieved_35 = _load_json(case["retrieved_techniques_35_json"])

    st.divider()
    st.caption(f"Case `{eval_id}` — next unreviewed disagreement")

    st.markdown("### Incident narrative")
    st.info(case["query_text"])

    with st.expander("Expected ATT&CK labels and definitions", expanded=True):
        _render_techniques(expected)

    same_retrieval = retrieved_31 == retrieved_35
    with st.expander("Retrieved ATT&CK context", expanded=False):
        if same_retrieval:
            _render_techniques(retrieved_31)
        else:
            st.warning(
                "The retrieved record sets differ between model runs. This is shown for auditability."
            )
            left, right = st.columns(2)
            with left:
                st.markdown("**Answer A context**")
                records = retrieved_31 if case["model_a"] == MODEL_31 else retrieved_35
                _render_techniques(records)
            with right:
                st.markdown("**Answer B context**")
                records = retrieved_31 if case["model_b"] == MODEL_31 else retrieved_35
                _render_techniques(records)

    st.markdown("### Blinded model answers")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Answer A")
        _render_answer(answer_a)
    with right:
        st.markdown("#### Answer B")
        _render_answer(answer_b)

    st.markdown("### Review decision")
    st.markdown(
        "Select the answer that is more correct, grounded in the incident narrative, "
        "appropriately uncertain, and useful for an analyst. Select **Tie** only when "
        "there is no meaningful quality difference."
    )

    with st.form(key=f"manual_review_{eval_id}"):
        choice = st.radio(
            "Which answer is better?",
            options=["Answer A", "Answer B", "Tie"],
            index=None,
            horizontal=True,
        )
        failure_modes = st.multiselect(
            "Observed issues (optional)",
            options=FAILURE_MODES,
        )
        notes = st.text_area(
            "Review notes (optional)",
            placeholder="Brief technical explanation of the winner or shared failure mode.",
        )
        submit = st.form_submit_button("Save review and load next case", type="primary")

    if submit:
        if choice is None:
            st.error("Select Answer A, Answer B, or Tie before saving.")
            return

        winner_map = {
            "Answer A": str(case["model_a"]),
            "Answer B": str(case["model_b"]),
            "Tie": "tie",
        }
        winner = winner_map[choice]

        record = {
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
            "eval_id": eval_id,
            "winner": winner,
            "failure_modes": " | ".join(failure_modes),
            "review_notes": notes.strip(),
            "answer_a_model": str(case["model_a"]),
            "answer_b_model": str(case["model_b"]),
            "judge_31_winner": str(case["winner_31"]),
            "judge_35_winner": str(case["winner_35"]),
            "judge_31_agrees": _judge_agreement(str(case["winner_31"]), winner),
            "judge_35_agrees": _judge_agreement(str(case["winner_35"]), winner),
        }
        _save_review(record, results_path)
        st.session_state.last_saved_review_eval_id = eval_id
        st.rerun()


if __name__ == "__main__":
    st.set_page_config(
        page_title="Cyber Threat Identifier — Evaluation Review",
        page_icon="🧪",
        layout="wide",
    )
    st.title("🧪 Manual Evaluation Review")
    render_evaluation_review()