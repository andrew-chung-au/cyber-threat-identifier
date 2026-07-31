#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from src.retrieval.embedding_model import get_embedding_model

from src.database.db_connection import get_connection
from src.evaluation.metrics import parse_expected_ids
from src.generation.answer_generator import generate_candidate_answer
from src.retrieval.vector import embed_query, retrieve_top_k_vector


DEFAULT_INPUT_PATH = Path("data/eval/expert_retrieval_cases.csv")
DEFAULT_OUTPUT_JSONL_PATH = Path("data/evaluation_reports/expert_answer_generation_v1.jsonl")
DEFAULT_OUTPUT_CSV_PATH = Path("data/evaluation_reports/expert_answer_generation_v1.csv")
DEFAULT_EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_TOP_K = 5


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run grounded answer generation on expert evaluation cases using vector retrieval."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT_JSONL_PATH)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV_PATH)
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL_NAME)
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--prompt-version", default="v1")
    args = parser.parse_args()

    if args.top_k < 1:
        raise ValueError("--top-k must be at least 1.")

    if not args.input.exists():
        raise FileNotFoundError(f"Missing input CSV: {args.input}")

    df = pd.read_csv(args.input)

    required_columns = {
        "eval_id",
        "upstream_split",
        "upstream_row_index",
        "text1",
        "expected_attack_ids",
        "word_count",
    }
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Input CSV is missing required columns: {sorted(missing)}")

    if args.limit is not None:
        df = df.head(args.limit).copy()

    print(f"[INFO] Loaded {len(df)} evaluation cases from {args.input}")
    print(f"[INFO] Loading embedding model: {args.embedding_model}")
    embedding_model = get_embedding_model(args.embedding_model)
    print("[OK]   Embedding model ready")

    output_rows: list[dict[str, Any]] = []

    with get_connection(register_pgvector=True) as connection:
        for idx, row in enumerate(df.itertuples(index=False), start=1):
            expected_ids = parse_expected_ids(row.expected_attack_ids)

            query_embedding = embed_query(
                model=embedding_model,
                query_text=row.text1,
            )

            retrieved = retrieve_top_k_vector(
                connection=connection,
                query_embedding=query_embedding,
                top_k=args.top_k,
            )
            retrieved_ids = [item.attack_id for item in retrieved]

            retrieved_rows = fetch_records_for_generation(
                connection=connection,
                attack_ids=retrieved_ids,
            )

            if not retrieved_rows:
                output_rows.append(
                    {
                        "eval_id": row.eval_id,
                        "upstream_split": row.upstream_split,
                        "upstream_row_index": row.upstream_row_index,
                        "query_text": row.text1,
                        "expected_attack_ids": ";".join(expected_ids),
                        "retrieved_attack_ids": ";".join(retrieved_ids),
                        "primary_attack_id": "",
                        "alternative_attack_ids": "",
                        "supporting_attack_ids": "",
                        "answer_summary": "",
                        "retrieval_grounding_note": "",
                        "uncertainty_note": "No ATT&CK records were retrieved for answer generation.",
                        "review_required": True,
                        "prompt_version": args.prompt_version,
                        "llm_model": args.llm_model or "",
                        "prompt_tokens": None,
                        "completion_tokens": None,
                        "total_tokens": None,
                    }
                )
                continue

            generation_result = generate_candidate_answer(
                incident_narrative=row.text1,
                retrieved_rows=retrieved_rows,
                model_name=args.llm_model,
                prompt_version=args.prompt_version,
            )

            answer = generation_result.answer

            output_rows.append(
                {
                    "eval_id": row.eval_id,
                    "upstream_split": row.upstream_split,
                    "upstream_row_index": row.upstream_row_index,
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
                    "prompt_version": generation_result.prompt_version,
                    "llm_model": args.llm_model or "",
                    "prompt_tokens": getattr(generation_result.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(generation_result.usage, "completion_tokens", None),
                    "total_tokens": getattr(generation_result.usage, "total_tokens", None),
                }
            )

            if idx % 10 == 0 or idx == len(df):
                print(f"[INFO] Processed {idx}/{len(df)} cases")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(output_rows).to_csv(args.output_csv, index=False)
    write_jsonl(args.output_jsonl, output_rows)

    print()
    print("[OK]   Answer generation run completed")
    print(f"  JSONL output: {args.output_jsonl}")
    print(f"  CSV output:   {args.output_csv}")
    print(f"  Cases run:    {len(output_rows)}")


if __name__ == "__main__":
    main()