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
from src.llm_client import RateLimiter
from src.retrieval.embedding_model import get_embedding_model
from src.retrieval.query_rewriter import rewrite_query
from src.retrieval.reranker import get_reranker_model
from src.retrieval.rewritten_reranked_vector import retrieve_rewritten_reranked_vector


DEFAULT_INPUT_PATH = Path("data/eval/expert_retrieval_cases.csv")
DEFAULT_OUTPUT_PATH = Path(
    "data/evaluation_reports/local/expert_query_rewrite_retrieval_results.csv"
)
DEFAULT_EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_QUERY_REWRITE_MODEL_ID = "gemini-3.1-flash-lite"
DEFAULT_CANDIDATE_K = 20
DEFAULT_TOP_K = 10


def format_scores(scores: list[float]) -> str:
    return ";".join(f"{score:.6f}" for score in scores)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run query-rewriting plus vector retrieval plus reranking "
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
        "--query-rewrite-model",
        default=DEFAULT_QUERY_REWRITE_MODEL_ID,
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
    parser.add_argument(
        "--no-rate-limit",
        action="store_true",
        help="Disable client-side rate limiting for batch queries.",
    )
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

    print(f"[INFO] Loading local reranker model: cross-encoder/ms-marco-MiniLM-L-6-v2")
    reranker_model = get_reranker_model()
    print("[OK]   Reranker model ready")

    print(f"[INFO] Using query-rewrite model: {args.query_rewrite_model}")

    # Optional rate limiter for batch queries
    rate_limiter: RateLimiter | None = None
    if not args.no_rate_limit:
        rate_limiter = RateLimiter(max_calls=15, window_seconds=60.0)
        print(f"[INFO] Rate limiting enabled: 15 calls/minute")
    else:
        print(f"[INFO] Rate limiting disabled (--no-rate-limit)")

    results: list[dict[str, object]] = []

    with get_connection(register_pgvector=True) as connection:
        for idx, row in enumerate(df.itertuples(index=False), start=1):
            expected_ids = parse_expected_ids(row.expected_attack_ids)
            expected_set = set(expected_ids)

            result = retrieve_rewritten_reranked_vector(
                query_text=row.text1,
                embedding_model=embedding_model,
                reranker_model=reranker_model,
                candidate_k=args.candidate_k,
                top_k=args.top_k,
                query_rewrite_model_id=args.query_rewrite_model,
                query_rewrite_prompt_version="v1",
                rate_limiter=rate_limiter,
            )

            retrieved_ids = [
                candidate.attack_id
                for candidate in result.candidates
            ]

            results.append(
                {
                    "eval_id": row.eval_id,
                    "retrieval_method": "rewritten_vector_reranked",
                    "upstream_split": row.upstream_split,
                    "upstream_row_index": row.upstream_row_index,
                    "query_text": row.text1,
                    "rewritten_query": result.rewritten_query,
                    "expected_attack_ids": ";".join(expected_ids),
                    "word_count": row.word_count,
                    "candidate_k": result.candidate_k,
                    "top_k": result.top_k,
                    "embedding_model": args.embedding_model,
                    "reranker_model": result.reranker_model,
                    "query_rewriter_model": result.query_rewriter_model,
                    "query_rewrite_prompt_version": result.query_rewrite_prompt_version,
                    "vector_candidate_attack_ids": ";".join(
                        candidate.attack_id
                        for candidate in result.vector_candidates
                    ),
                    "vector_candidate_scores": format_scores(
                        [
                            candidate.vector_score
                            for candidate in result.vector_candidates
                        ]
                    ),
                    "vector_candidate_ranks": ";".join(
                        str(candidate.vector_rank)
                        for candidate in result.vector_candidates
                    ),
                    "retrieved_attack_ids": ";".join(retrieved_ids),
                    "retrieved_names": ";".join(
                        candidate.name
                        for candidate in result.candidates
                    ),
                    "retrieved_vector_scores": format_scores(
                        [
                            candidate.vector_score
                            for candidate in result.candidates
                        ]
                    ),
                    "original_vector_ranks": ";".join(
                        str(candidate.vector_rank)
                        for candidate in result.candidates
                    ),
                    "reranker_scores": format_scores(
                        [
                            candidate.reranker_score
                            for candidate in result.candidates
                            if candidate.reranker_score is not None
                        ]
                    ),
                    "reranked_ranks": ";".join(
                        str(candidate.reranked_rank)
                        for candidate in result.candidates
                    ),
                    "query_rewrite_ms": round(result.query_rewrite_ms, 3),
                    "embedding_ms": round(result.embedding_ms, 3),
                    "vector_search_ms": round(result.vector_search_ms, 3),
                    "reranking_ms": round(result.reranking_ms, 3),
                    "total_retrieval_ms": round(result.total_retrieval_ms, 3),
                    "fallback_used": result.fallback_used,
                    "query_rewrite_error": result.query_rewrite_error,
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
    print("[OK]   Query-rewrite plus reranked retrieval benchmark completed")
    print(f"  Output file:       {args.output}")
    print(f"  Queries run:       {len(results_df)}")
    print(f"  Candidate pool:    {args.candidate_k}")
    print(f"  Returned top-k:    {args.top_k}")
    print(f"  Query rewriter:    {args.query_rewrite_model}")
    print(f"  Rate limiting:     {'disabled' if args.no_rate_limit else 'enabled (15/min)'}")
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
        f"  Median rewrite ms: "
        f"{results_df['query_rewrite_ms'].median():.2f}"
    )
    print(
        f"  P95 rewrite ms:    "
        f"{results_df['query_rewrite_ms'].quantile(0.95):.2f}"
    )


if __name__ == "__main__":
    main()