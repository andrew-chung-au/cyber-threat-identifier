from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentence_transformers import CrossEncoder, SentenceTransformer

from src.database.db_connection import get_connection
from src.retrieval.reranked_vector import retrieve_reranked_vector
from src.retrieval.reranker import get_reranker_model
from src.retrieval.vector import embed_query


@dataclass(slots=True)
class RewrittenRerankedRetrievalResult:
    candidates: list
    vector_candidates: list
    candidate_k: int
    top_k: int
    embedding_ms: float
    vector_search_ms: float
    reranking_ms: float
    total_retrieval_ms: float
    reranker_model: str
    fallback_used: bool
    original_query: str
    rewritten_query: str
    query_rewriter_model: str
    query_rewrite_prompt_version: str
    query_rewrite_ms: float
    query_rewrite_error: str | None


def retrieve_rewritten_reranked_vector(
    *,
    query_text: str,
    embedding_model: SentenceTransformer,
    reranker_model: CrossEncoder | None = None,
    candidate_k: int = 20,
    top_k: int = 10,
    query_rewrite_model_id: str | None = None,
    query_rewrite_prompt_version: str = "v1",
    cache_dir: Any | None = None,
    cache_key: str | None = None,
    rate_limiter: Any | None = None,
) -> RewrittenRerankedRetrievalResult:
    import time

    from src.retrieval.query_rewriter import rewrite_query

    total_started = time.perf_counter()

    rewrite_result = rewrite_query(
        query_text=query_text,
        model_id=query_rewrite_model_id,
        prompt_version=query_rewrite_prompt_version,
        cache_dir=cache_dir,
        cache_key=cache_key,
        rate_limiter=rate_limiter,
    )

    if rewrite_result.error is not None:
        raise RuntimeError(
            f"Query rewriting failed: {rewrite_result.error}"
        )

    with get_connection(register_pgvector=True) as connection:
        vector_result = retrieve_reranked_vector(
            connection=connection,
            embedding_model=embedding_model,
            reranker_model=reranker_model or get_reranker_model(),
            query_text=rewrite_result.rewritten_query,
            candidate_k=candidate_k,
            top_k=top_k,
            reranker_model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
        )

    total_retrieval_ms = (time.perf_counter() - total_started) * 1000

    return RewrittenRerankedRetrievalResult(
        candidates=vector_result.candidates,
        vector_candidates=vector_result.vector_candidates,
        candidate_k=vector_result.candidate_k,
        top_k=vector_result.top_k,
        embedding_ms=vector_result.embedding_ms,
        vector_search_ms=vector_result.vector_search_ms,
        reranking_ms=vector_result.reranking_ms,
        total_retrieval_ms=total_retrieval_ms,
        reranker_model=vector_result.reranker_model,
        fallback_used=vector_result.fallback_used,
        original_query=query_text,
        rewritten_query=rewrite_result.rewritten_query,
        query_rewriter_model=rewrite_result.model_id,
        query_rewrite_prompt_version=rewrite_result.prompt_version,
        query_rewrite_ms=rewrite_result.latency_ms,
        query_rewrite_error=rewrite_result.error,
    )