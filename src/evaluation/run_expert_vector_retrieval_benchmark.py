#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from sentence_transformers import SentenceTransformer

from src.database.db_connection import get_connection


DEFAULT_INPUT_PATH = Path("data/eval/expert_retrieval_cases.csv")
DEFAULT_OUTPUT_PATH = Path("data/evaluation_reports/expert_vector_retrieval_results.csv")
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_TOP_K = 10


def parse_expected_ids(value: str) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    return [item.strip() for item in str(value).split(";") if item.strip()]


def reciprocal_rank(retrieved_ids: list[str], expected_ids: set[str]) -> float:
    for rank, attack_id in enumerate(retrieved_ids, start=1):
        if attack_id in expected_ids:
            return 1.0 / rank
    return 0.0


def recall_at_k(retrieved_ids: list[str], expected_ids: set[str], k: int) -> float:
    if not expected_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    hits = len(top_k.intersection(expected_ids))
    return hits / len(expected_ids)


def hit_at_k(retrieved_ids: list[str], expected_ids: set[str], k: int) -> int:
    top_k = set(retrieved_ids[:k])
    return int(bool(top_k.intersection(expected_ids)))


def retrieve_top_k_vector(
    connection: Any,
    query_embedding: list[float],
    top_k: int,
) -> list[dict[str, Any]]:
    sql = """
        SELECT
            attack_id,
            name,
            1 - (embedding <=> %s::vector) AS retrieval_score
        FROM techniques
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, (query_embedding, query_embedding, top_k))
        rows = cursor.fetchall()

    return [
        {
            "attack_id": attack_id,
            "name": name,
            "retrieval_score": float(score),
        }
        for attack_id, name, score in rows
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run vector retrieval benchmark on expert evaluation cases."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--limit", type=int, default=None)
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
    print(f"[INFO] Loading embedding model: {args.model}")
    model = SentenceTransformer(args.model)
    print("[OK]   Embedding model ready")

    results: list[dict[str, Any]] = []

    with get_connection(register_pgvector=True) as connection:
        for idx, row in enumerate(df.itertuples(index=False), start=1):
            expected_ids = parse_expected_ids(row.expected_attack_ids)
            expected_set = set(expected_ids)

            query_embedding = model.encode(
                row.text1,
                normalize_embeddings=True,
            ).tolist()

            retrieved = retrieve_top_k_vector(
                connection=connection,
                query_embedding=query_embedding,
                top_k=args.top_k,
            )

            retrieved_ids = [item["attack_id"] for item in retrieved]
            retrieved_scores = [item["retrieval_score"] for item in retrieved]

            results.append(
                {
                    "eval_id": row.eval_id,
                    "retrieval_method": "vector",
                    "upstream_split": row.upstream_split,
                    "upstream_row_index": row.upstream_row_index,
                    "query_text": row.text1,
                    "expected_attack_ids": ";".join(expected_ids),
                    "retrieved_attack_ids": ";".join(retrieved_ids),
                    "retrieved_scores": ";".join(f"{score:.6f}" for score in retrieved_scores),
                    "recall_at_1": recall_at_k(retrieved_ids, expected_set, 1),
                    "recall_at_3": recall_at_k(retrieved_ids, expected_set, 3),
                    "recall_at_5": recall_at_k(retrieved_ids, expected_set, 5),
                    "recall_at_10": recall_at_k(retrieved_ids, expected_set, 10),
                    "hit_at_3": hit_at_k(retrieved_ids, expected_set, 3),
                    "hit_at_10": hit_at_k(retrieved_ids, expected_set, 10),
                    "mrr": reciprocal_rank(retrieved_ids, expected_set),
                }
            )

            if idx % 25 == 0 or idx == len(df):
                print(f"[INFO] Processed {idx}/{len(df)} queries")

    results_df = pd.DataFrame(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(args.output, index=False)

    print()
    print("[OK]   Vector retrieval benchmark completed")
    print(f"  Output file: {args.output}")
    print(f"  Queries run: {len(results_df)}")
    print(f"  Recall@1:    {results_df['recall_at_1'].mean():.4f}")
    print(f"  Recall@3:    {results_df['recall_at_3'].mean():.4f}")
    print(f"  Recall@5:    {results_df['recall_at_5'].mean():.4f}")
    print(f"  Recall@10:   {results_df['recall_at_10'].mean():.4f}")
    print(f"  Hit@3:       {results_df['hit_at_3'].mean():.4f}")
    print(f"  Hit@10:      {results_df['hit_at_10'].mean():.4f}")
    print(f"  MRR:         {results_df['mrr'].mean():.4f}")


if __name__ == "__main__":
    main()