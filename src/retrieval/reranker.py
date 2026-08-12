from __future__ import annotations

from functools import lru_cache
from typing import Sequence

from sentence_transformers import CrossEncoder

from src.retrieval.schemas import RerankedCandidate, VectorCandidate


DEFAULT_RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_RERANKER_BATCH_SIZE = 16


@lru_cache(maxsize=2)
def get_reranker_model(
    model_name: str = DEFAULT_RERANKER_MODEL_NAME,
) -> CrossEncoder:
    return CrossEncoder(
        model_name,
        device="cpu",
    )


def rerank_candidates(
    query_text: str,
    candidates: Sequence[VectorCandidate],
    model: CrossEncoder,
    top_k: int,
    batch_size: int = DEFAULT_RERANKER_BATCH_SIZE,
) -> list[RerankedCandidate]:
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    if not candidates:
        return []

    pairs = [
        (query_text, candidate.rerank_text)
        for candidate in candidates
    ]

    scores = model.predict(
        pairs,
        batch_size=batch_size,
        show_progress_bar=False,
    )

    scored_candidates = sorted(
        zip(candidates, scores, strict=True),
        key=lambda item: float(item[1]),
        reverse=True,
    )

    return [
        RerankedCandidate(
            attack_id=candidate.attack_id,
            name=candidate.name,
            vector_score=candidate.vector_score,
            vector_rank=candidate.vector_rank,
            reranker_score=float(reranker_score),
            reranked_rank=reranked_rank,
        )
        for reranked_rank, (candidate, reranker_score) in enumerate(
            scored_candidates[:top_k],
            start=1,
        )
    ]