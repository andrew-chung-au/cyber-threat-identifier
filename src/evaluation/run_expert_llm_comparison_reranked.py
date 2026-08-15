#!/usr/bin/env python3
"""
Run a reranked LLM comparison (gemini-3.1-flash-lite vs gemini-3.5-flash-lite)
on expert evaluation cases.

This script preserves vector-only comparison artifacts by writing reranked results
to a separate output directory by default. It checkpoints after each case and
skips completed eval_ids on resume.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import pandas as pd

from src.database.db_connection import get_connection
from src.evaluation.metrics import parse_expected_ids
from src.generation.answer_generator import generate_candidate_answer
from src.retrieval.embedding_model import get_embedding_model
from src.retrieval.reranked_vector import retrieve_reranked_vector
from src.retrieval.reranker import (
    DEFAULT_RERANKER_MODEL_NAME,
    get_reranker_model,
)


DEFAULT_INPUT_PATH = Path("data/eval/expert_retrieval_cases.csv")
DEFAULT_OUTPUT_CSV_PATH = Path(
    "data/evaluation_reports/reranked/expert_llm_comparison_reranked_v1.csv"
)
DEFAULT_EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CANDIDATE_K = 20
DEFAULT_TOP_K = 5

MODEL_31 = "gemini-3.1-flash-lite"
MODEL_35 = "gemini-3.5-flash-lite"


def fetch_records_for_generation(
    connection: Any,
    attack_ids: list[str],
) -> list[dict[str, Any]]:
    if not attack_ids:
        return []

    sql = """
        SELECT
            attack_id,
            name,
            is_subtechnique,
            parent_attack_id,
            tactics,
            platforms,
            description_clean,
            source_url
        FROM techniques
        WHERE attack_id = ANY(%s)
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, (attack_ids,))
        rows = cursor.fetchall()

    rows_by_attack_id = {
        row[0]: {
            "attack_id": row[0],
            "name": row[1],
            "is_subtechnique": row[2],
            "parent_attack_id": row[3],
            "tactics": row[4],
            "platforms": row[5],
            "description_clean": row[6],
            "source_url": row[7],
        }
        for row in rows
    }

    return [
        rows_by_attack_id[attack_id]
        for attack_id in attack_ids
        if attack_id in rows_by_attack_id
    ]


def run_single_case(
    row: Any,
    model_name: str,
    embedding_model: Any,
    reranker_model: Any,
    connection: Any,
    candidate_k: int,
    top_k: int,
    reranker_model_name: str,
) -> dict[str, Any]:
    expected_ids = parse_expected_ids(row.expected_attack_ids)
    start_time = time.perf_counter()

    retrieval_result = retrieve_reranked_vector(
        connection=connection,
        embedding_model=embedding_model,
        reranker_model=reranker_model,
        query_text=row.text1,
        candidate_k=candidate_k,
        top_k=top_k,
        reranker_model_name=reranker_model_name,
    )

    retrieved_ids = [
        candidate.attack_id
        for candidate in retrieval_result.candidates
    ]
    retrieved_rows = fetch_records_for_generation(
        connection=connection,
        attack_ids=retrieved_ids,
    )

    base_result = {
        "eval_id": row.eval_id,
        "model": model_name,
        "query_text": row.text1,
        "expected_attack_ids": ";".join(expected_ids),
        "retrieved_attack_ids": ";".join(retrieved_ids),
        "retrieval_method": "vector_plus_cross_encoder_rerank",
        "candidate_k": candidate_k,
        "top_k": top_k,
        "reranker_model": reranker_model_name,
        "embedding_ms": retrieval_result.embedding_ms,
        "vector_search_ms": retrieval_result.vector_search_ms,
        "reranking_ms": retrieval_result.reranking_ms,
        "total_retrieval_ms": retrieval_result.total_retrieval_ms,
    }

    if not retrieved_rows:
        return {
            **base_result,
            "primary_attack_id": "",
            "alternative_attack_ids": "",
            "supporting_attack_ids": "",
            "answer_summary": "",
            "retrieval_grounding_note": "",
            "uncertainty_note": "No ATT&CK records retrieved after reranking.",
            "review_required": True,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "latency_seconds": time.perf_counter() - start_time,
        }

    generation_result = generate_candidate_answer(
        incident_narrative=row.text1,
        retrieved_rows=retrieved_rows,
        model_name=model_name,
        prompt_version="v1",
    )
    answer = generation_result.answer

    return {
        **base_result,
        "primary_attack_id": answer.primary_attack_id or "",
        "alternative_attack_ids": ";".join(answer.alternative_attack_ids),
        "supporting_attack_ids": ";".join(answer.supporting_attack_ids),
        "answer_summary": answer.answer_summary,
        "retrieval_grounding_note": answer.retrieval_grounding_note,
        "uncertainty_note": answer.uncertainty_note,
        "review_required": answer.review_required,
        "prompt_tokens": getattr(generation_result.usage, "prompt_tokens", None),
        "completion_tokens": getattr(generation_result.usage, "completion_tokens", None),
        "total_tokens": getattr(generation_result.usage, "total_tokens", None),
        "latency_seconds": time.perf_counter() - start_time,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare Gemini 3.1 and 3.5 Flash-Lite using vector retrieval "
            "plus local cross-encoder reranking."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV_PATH)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL_NAME)
    parser.add_argument("--reranker-model", default=DEFAULT_RERANKER_MODEL_NAME)
    parser.add_argument("--candidate-k", type=int, default=DEFAULT_CANDIDATE_K)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Missing input CSV: {args.input}")
    if args.candidate_k < 1:
        raise ValueError("--candidate-k must be at least 1.")
    if args.top_k < 1:
        raise ValueError("--top-k must be at least 1.")
    if args.top_k > args.candidate_k:
        raise ValueError("--top-k cannot exceed --candidate-k.")

    df = pd.read_csv(args.input)
    if args.limit is not None:
        df = df.head(args.limit).copy()

    if args.output_csv.exists():
        existing_df = pd.read_csv(args.output_csv)
        processed_eval_ids = set(existing_df["eval_id"].unique())
        output_rows = existing_df.to_dict("records")
        df = df[~df["eval_id"].isin(processed_eval_ids)].copy()
        print(
            f"[INFO] Found {len(processed_eval_ids)} completed cases in "
            f"{args.output_csv}; resuming."
        )
    else:
        processed_eval_ids: set[str] = set()
        output_rows: list[dict[str, Any]] = []

    if df.empty:
        print("[OK]   All requested cases have already been processed.")
        return

    print(f"[INFO] Processing {len(df)} remaining expert cases.")
    print(f"[INFO] Embedding model: {args.embedding_model}")
    embedding_model = get_embedding_model(args.embedding_model)
    print(f"[INFO] Local reranker: {args.reranker_model}")
    reranker_model = get_reranker_model(args.reranker_model)

    with get_connection(register_pgvector=True) as connection:
        for index, row in enumerate(df.itertuples(index=False), start=1):
            print(f"[INFO] Case {index}/{len(df)}: {row.eval_id}")

            result_31 = run_single_case(
                row=row,
                model_name=MODEL_31,
                embedding_model=embedding_model,
                reranker_model=reranker_model,
                connection=connection,
                candidate_k=args.candidate_k,
                top_k=args.top_k,
                reranker_model_name=args.reranker_model,
            )
            output_rows.append(result_31)

            result_35 = run_single_case(
                row=row,
                model_name=MODEL_35,
                embedding_model=embedding_model,
                reranker_model=reranker_model,
                connection=connection,
                candidate_k=args.candidate_k,
                top_k=args.top_k,
                reranker_model_name=args.reranker_model,
            )
            output_rows.append(result_35)

            args.output_csv.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(output_rows).to_csv(args.output_csv, index=False)

            if index % 20 == 0 or index == len(df):
                print(f"[INFO] Checkpoint saved: {index}/{len(df)} cases.")

    print()
    print("[OK]   Reranked LLM comparison completed.")
    print(f"  Output CSV: {args.output_csv}")
    print(f"  Cases:      {len(output_rows) // 2}")
    print(f"  Retrieval:  vector candidates={args.candidate_k}, reranked top_k={args.top_k}")


if __name__ == "__main__":
    main()
