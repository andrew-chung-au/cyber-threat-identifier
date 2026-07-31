#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.database.db_connection import get_connection
from src.evaluation.metrics import (
    hit_at_k,
    parse_expected_ids,
    recall_at_k,
    reciprocal_rank,
)
from src.retrieval.text import retrieve_top_k_text


DEFAULT_INPUT_PATH = Path("data/eval/expert_retrieval_cases.csv")
DEFAULT_OUTPUT_PATH = Path("data/evaluation_reports/expert_text_retrieval_results.csv")
DEFAULT_TOP_K = 10


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run full-text retrieval benchmark on expert evaluation cases."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
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

    results: list[dict[str, object]] = []

    with get_connection() as connection:
        for idx, row in enumerate(df.itertuples(index=False), start=1):
            expected_ids = parse_expected_ids(row.expected_attack_ids)
            expected_set = set(expected_ids)

            retrieved = retrieve_top_k_text(
                connection=connection,
                query_text=row.text1,
                top_k=args.top_k,
            )

            retrieved_ids = [item.attack_id for item in retrieved]
            retrieved_scores = [item.retrieval_score for item in retrieved]

            results.append(
                {
                    "eval_id": row.eval_id,
                    "retrieval_method": "text",
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
    print("[OK]   Text retrieval benchmark completed")
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