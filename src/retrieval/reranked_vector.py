from __future__ import annotations

from time import perf_counter
from typing import Any

from sentence_transformers import CrossEncoder, SentenceTransformer

from src.retrieval.reranker import (
    DEFAULT_RERANKER_MODEL_NAME,
    rerank_candidates,
)
from src.retrieval.schemas import RerankedRetrievalResult
from src.retrieval.vector import embed_query, retrieve_vector_candidates


def retrieve_reranked_vector(
    connection: Any,
    embedding_model: SentenceTransformer,
    reranker_model: CrossEncoder,
    query_text: str,
    candidate_k: int,
    top_k: int,
    reranker_model_name: str = DEFAULT_RERANKER_MODEL_NAME,
) -> RerankedRetrievalResult:
    if candidate_k < 1:
        raise ValueError("candidate_k must be at least 1.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    if top_k > candidate_k:
        raise ValueError("top_k cannot exceed candidate_k.")

    total_started = perf_counter()

    embedding_started = perf_counter()
    query_embedding = embed_query(
        model=embedding_model,
        query_text=query_text,
    )
    embedding_ms = (perf_counter() - embedding_started) * 1000

    vector_search_started = perf_counter()
    vector_candidates = retrieve_vector_candidates(
        connection=connection,
        query_embedding=query_embedding,
        candidate_k=candidate_k,
    )
    vector_search_ms = (perf_counter() - vector_search_started) * 1000

    reranking_started = perf_counter()
    reranked_candidates = rerank_candidates(
        query_text=query_text,
        candidates=vector_candidates,
        model=reranker_model,
        top_k=top_k,
    )
    reranking_ms = (perf_counter() - reranking_started) * 1000

    total_retrieval_ms = (perf_counter() - total_started) * 1000

    return RerankedRetrievalResult(
        candidates=reranked_candidates,
        vector_candidates=vector_candidates,
        candidate_k=candidate_k,
        top_k=top_k,
        embedding_ms=embedding_ms,
        vector_search_ms=vector_search_ms,
        reranking_ms=reranking_ms,
        total_retrieval_ms=total_retrieval_ms,
        reranker_model=reranker_model_name,
        fallback_used=False,
    )