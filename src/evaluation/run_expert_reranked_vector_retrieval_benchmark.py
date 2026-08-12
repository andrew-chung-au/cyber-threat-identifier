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
from src.retrieval.embedding_model import get_embedding_model
from src.retrieval.reranked_vector import retrieve_reranked_vector
from src.retrieval.reranker import (
    DEFAULT_RERANKER_MODEL_NAME,
    get_reranker_model,
)


DEFAULT_INPUT_PATH = Path("data/eval/expert_retrieval_cases.csv")
DEFAULT_OUTPUT_PATH = Path(
    "data/evaluation_reports/expert_vector_reranked_retrieval_results.csv"
)
DEFAULT_EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CANDIDATE_K = 20
DEFAULT_TOP_K = 10


def format_scores(scores: list[float]) -> str:
    return ";".join(f"{score:.6f}" for score in scores)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run vector retrieval plus local cross-encoder reranking "
            "on expert evaluation cases."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL_NAME,
    )
    parser.add_argument(
        "--reranker-model",
        default=DEFAULT_RERANKER_MODEL_NAME,
    )
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=DEFAULT_CANDIDATE_K,
        help="Number of vector candidates passed to the reranker.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Number of reranked candidates returned for evaluation.",
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if args.candidate_k < 1:
        raise ValueError("--candidate-k must be at least 1.")

    if args.top_k < 10:
        raise ValueError(
            "--top-k must be at least 10 because this benchmark "
            "reports Recall@10 and Hit@10."
        )

    if args.top_k > args.candidate_k:
        raise ValueError("--top-k cannot exceed --candidate-k.")

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
        raise ValueError(
            f"Input CSV is missing required columns: {sorted(missing)}"
        )

    if args.limit is not None:
        df = df.head(args.limit).copy()

    print(f"[INFO] Loaded {len(df)} evaluation cases from {args.input}")

    print(f"[INFO] Loading embedding model: {args.embedding_model}")
    embedding_model = get_embedding_model(args.embedding_model)
    print("[OK]   Embedding model ready")

    print(f"[INFO] Loading local reranker model: {args.reranker_model}")
    reranker_model = get_reranker_model(args.reranker_model)
    print("[OK]   Reranker model ready")

    results: list[dict[str, object]] = []

    with get_connection(register_pgvector=True) as connection:
        for idx, row in enumerate(df.itertuples(index=False), start=1):
            expected_ids = parse_expected_ids(row.expected_attack_ids)
            expected_set = set(expected_ids)

            retrieval_result = retrieve_reranked_vector(
                connection=connection,
                embedding_model=embedding_model,
                reranker_model=reranker_model,
                query_text=row.text1,
                candidate_k=args.candidate_k,
                top_k=args.top_k,
                reranker_model_name=args.reranker_model,
            )

            vector_candidates = retrieval_result.vector_candidates
            reranked_candidates = retrieval_result.candidates

            retrieved_ids = [
                candidate.attack_id
                for candidate in reranked_candidates
            ]

            results.append(
                {
                    "eval_id": row.eval_id,
                    "retrieval_method": "vector_reranked",
                    "upstream_split": row.upstream_split,
                    "upstream_row_index": row.upstream_row_index,
                    "query_text": row.text1,
                    "expected_attack_ids": ";".join(expected_ids),
                    "word_count": row.word_count,
                    "candidate_k": retrieval_result.candidate_k,
                    "top_k": retrieval_result.top_k,
                    "embedding_model": args.embedding_model,
                    "reranker_model": retrieval_result.reranker_model,
                    "vector_candidate_attack_ids": ";".join(
                        candidate.attack_id
                        for candidate in vector_candidates
                    ),
                    "vector_candidate_scores": format_scores(
                        [
                            candidate.vector_score
                            for candidate in vector_candidates
                        ]
                    ),
                    "vector_candidate_ranks": ";".join(
                        str(candidate.vector_rank)
                        for candidate in vector_candidates
                    ),
                    "retrieved_attack_ids": ";".join(retrieved_ids),
                    "retrieved_names": ";".join(
                        candidate.name
                        for candidate in reranked_candidates
                    ),
                    "retrieved_vector_scores": format_scores(
                        [
                            candidate.vector_score
                            for candidate in reranked_candidates
                        ]
                    ),
                    "original_vector_ranks": ";".join(
                        str(candidate.vector_rank)
                        for candidate in reranked_candidates
                    ),
                    "reranker_scores": format_scores(
                        [
                            candidate.reranker_score
                            for candidate in reranked_candidates
                            if candidate.reranker_score is not None
                        ]
                    ),
                    "reranked_ranks": ";".join(
                        str(candidate.reranked_rank)
                        for candidate in reranked_candidates
                    ),
                    "embedding_ms": round(
                        retrieval_result.embedding_ms,
                        3,
                    ),
                    "vector_search_ms": round(
                        retrieval_result.vector_search_ms,
                        3,
                    ),
                    "reranking_ms": round(
                        retrieval_result.reranking_ms,
                        3,
                    ),
                    "total_retrieval_ms": round(
                        retrieval_result.total_retrieval_ms,
                        3,
                    ),
                    "fallback_used": retrieval_result.fallback_used,
                    "recall_at_1": recall_at_k(
                        retrieved_ids,
                        expected_set,
                        1,
                    ),
                    "recall_at_3": recall_at_k(
                        retrieved_ids,
                        expected_set,
                        3,
                    ),
                    "recall_at_5": recall_at_k(
                        retrieved_ids,
                        expected_set,
                        5,
                    ),
                    "recall_at_10": recall_at_k(
                        retrieved_ids,
                        expected_set,
                        10,
                    ),
                    "hit_at_3": hit_at_k(
                        retrieved_ids,
                        expected_set,
                        3,
                    ),
                    "hit_at_10": hit_at_k(
                        retrieved_ids,
                        expected_set,
                        10,
                    ),
                    "mrr": reciprocal_rank(
                        retrieved_ids,
                        expected_set,
                    ),
                }
            )

            if idx % 25 == 0 or idx == len(df):
                print(f"[INFO] Processed {idx}/{len(df)} queries")

    results_df = pd.DataFrame(results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(args.output, index=False)

    print()
    print("[OK]   Vector plus reranking benchmark completed")
    print(f"  Output file:       {args.output}")
    print(f"  Queries run:       {len(results_df)}")
    print(f"  Candidate pool:    {args.candidate_k}")
    print(f"  Returned top-k:    {args.top_k}")
    print(f"  Reranker model:    {args.reranker_model}")
    print(f"  Recall@1:          {results_df['recall_at_1'].mean():.4f}")
    print(f"  Recall@3:          {results_df['recall_at_3'].mean():.4f}")
    print(f"  Recall@5:          {results_df['recall_at_5'].mean():.4f}")
    print(f"  Recall@10:         {results_df['recall_at_10'].mean():.4f}")
    print(f"  Hit@3:             {results_df['hit_at_3'].mean():.4f}")
    print(f"  Hit@10:            {results_df['hit_at_10'].mean():.4f}")
    print(f"  MRR:               {results_df['mrr'].mean():.4f}")
    print(
        f"  Median total ms:   "
        f"{results_df['total_retrieval_ms'].median():.2f}"
    )
    print(
        f"  P95 total ms:      "
        f"{results_df['total_retrieval_ms'].quantile(0.95):.2f}"
    )
    print(
        f"  Median rerank ms:  "
        f"{results_df['reranking_ms'].median():.2f}"
    )
    print(
        f"  P95 rerank ms:     "
        f"{results_df['reranking_ms'].quantile(0.95):.2f}"
    )


if __name__ == "__main__":
    main()