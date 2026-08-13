#!/usr/bin/env python3
"""
Run LLM comparison (gemini-3.1-flash-lite vs gemini-3.5-flash-lite)
on expert evaluation cases for DEC-020.

Checkpointing: Saves after each case, skips already-processed cases on resume.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
from src.retrieval.embedding_model import get_embedding_model
from src.database.db_connection import get_connection
from src.evaluation.metrics import parse_expected_ids
from src.generation.answer_generator import generate_candidate_answer
from src.retrieval.vector import embed_query, retrieve_top_k_vector

DEFAULT_INPUT_PATH = Path("data/eval/expert_retrieval_cases.csv")
DEFAULT_OUTPUT_CSV_PATH = Path("data/evaluation_reports/expert_llm_comparison_v1.csv")
DEFAULT_EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
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
    connection: Any,
    top_k: int,
) -> dict[str, Any]:
    """Run answer generation for a single case with a specific model."""
    expected_ids = parse_expected_ids(row.expected_attack_ids)
    
    start_time = time.perf_counter()
    
    query_embedding = embed_query(
        model=embedding_model,
        query_text=row.text1,
    )
    
    retrieved = retrieve_top_k_vector(
        connection=connection,
        query_embedding=query_embedding,
        top_k=top_k,
    )
    retrieved_ids = [item.attack_id for item in retrieved]
    
    retrieved_rows = fetch_records_for_generation(
        connection=connection,
        attack_ids=retrieved_ids,
    )
    
    if not retrieved_rows:
        latency = time.perf_counter() - start_time
        return {
            "eval_id": row.eval_id,
            "model": model_name,
            "query_text": row.text1,
            "expected_attack_ids": ";".join(expected_ids),
            "retrieved_attack_ids": "",
            "primary_attack_id": "",
            "alternative_attack_ids": "",
            "supporting_attack_ids": "",
            "answer_summary": "",
            "retrieval_grounding_note": "",
            "uncertainty_note": "No ATT&CK records retrieved.",
            "review_required": True,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "latency_seconds": latency,
        }
    
    generation_result = generate_candidate_answer(
        incident_narrative=row.text1,
        retrieved_rows=retrieved_rows,
        model_name=model_name,
        prompt_version="v1",
    )
    
    latency = time.perf_counter() - start_time
    answer = generation_result.answer
    
    return {
        "eval_id": row.eval_id,
        "model": model_name,
        "query_text": row.text1,
        "expected_attack_ids": ";".join(expected_ids),
        "retrieved_attack_ids": ";".join(retrieved_ids),
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
        "latency_seconds": latency,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare gemini-3.1-flash-lite vs gemini-3.5-flash-lite on expert cases."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV_PATH)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL_NAME)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    
    if not args.input.exists():
        raise FileNotFoundError(f"Missing input CSV: {args.input}")
    
    df = pd.read_csv(args.input)
    
    if args.limit is not None:
        df = df.head(args.limit).copy()
    
    # Checkpoint: Load existing output and skip processed eval_ids
    if args.output_csv.exists():
        existing_df = pd.read_csv(args.output_csv)
        processed_eval_ids = set(existing_df['eval_id'].unique())
        print(f"[INFO] Found {len(processed_eval_ids)} already-processed cases in {args.output_csv}")
        print(f"[INFO] Resuming from checkpoint, skipping completed cases...")
        
        # Filter to unprocessed cases
        df = df[~df['eval_id'].isin(processed_eval_ids)].copy()
        output_rows = existing_df.to_dict('records')
    else:
        processed_eval_ids = set()
        output_rows = []
    
    if len(df) == 0:
        print("[OK]   All cases already processed, nothing to do")
        print(f"  Output file: {args.output_csv}")
        return
    
    print(f"[INFO] Loaded {len(df)} remaining evaluation cases from {args.input}")
    print(f"[INFO] Loading embedding model: {args.embedding_model}")
    embedding_model = get_embedding_model(args.embedding_model)
    print("[OK]   Embedding model ready")
    
    with get_connection(register_pgvector=True) as connection:
        for idx, row in enumerate(df.itertuples(index=False), start=1):
            print(f"[INFO] Processing case {idx}/{len(df)}: {row.eval_id}")
            
            # Run with 3.1 Flash-Lite
            print(f"  → Running {MODEL_31}...")
            result_31 = run_single_case(
                row=row,
                model_name=MODEL_31,
                embedding_model=embedding_model,
                connection=connection,
                top_k=args.top_k,
            )
            output_rows.append(result_31)
            
            # Run with 3.5 Flash-Lite
            print(f"  → Running {MODEL_35}...")
            result_35 = run_single_case(
                row=row,
                model_name=MODEL_35,
                embedding_model=embedding_model,
                connection=connection,
                top_k=args.top_k,
            )
            output_rows.append(result_35)
            
            # Save checkpoint after each case
            args.output_csv.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(output_rows).to_csv(args.output_csv, index=False)
            
            if idx % 20 == 0 or idx == len(df):
                print(f"[INFO] Completed {idx}/{len(df)} cases (both models), checkpoint saved")
    
    print()
    print("[OK]   LLM comparison run completed")
    print(f"  CSV output: {args.output_csv}")
    print(f"  Total rows: {len(output_rows)} (2 models × {len(df) + len(processed_eval_ids)} cases)")


if __name__ == "__main__":
    main()