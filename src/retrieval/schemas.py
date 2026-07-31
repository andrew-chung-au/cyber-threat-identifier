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


@dataclass(slots=True)
class HybridCandidate:
    attack_id: str
    name: str
    text_rank: Optional[int]
    vector_rank: Optional[int]
    text_score: Optional[float]
    vector_score: Optional[float]
    rrf_score: float