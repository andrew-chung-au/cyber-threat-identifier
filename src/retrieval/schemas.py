from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class RetrievedCandidate:
    attack_id: str
    name: str
    retrieval_score: float


@dataclass(slots=True)
class TextCandidate:
    attack_id: str
    name: str
    text_score: float


@dataclass(slots=True)
class VectorCandidate:
    attack_id: str
    name: str
    vector_score: float
    vector_rank: int
    rerank_text: str


@dataclass(slots=True)
class HybridCandidate:
    attack_id: str
    name: str
    text_rank: Optional[int]
    vector_rank: Optional[int]
    text_score: Optional[float]
    vector_score: Optional[float]
    rrf_score: float


@dataclass(slots=True)
class RerankedCandidate:
    attack_id: str
    name: str
    vector_score: float
    vector_rank: int
    reranker_score: Optional[float]
    reranked_rank: int


@dataclass(slots=True)
class RerankedRetrievalResult:
    candidates: list[RerankedCandidate]
    vector_candidates: list[VectorCandidate]
    candidate_k: int
    top_k: int
    embedding_ms: float
    vector_search_ms: float
    reranking_ms: float
    total_retrieval_ms: float
    reranker_model: str
    fallback_used: bool