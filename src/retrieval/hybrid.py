from __future__ import annotations

from src.retrieval.schemas import HybridCandidate, TextCandidate, VectorCandidate


def fuse_with_rrf(
    text_results: list[TextCandidate],
    vector_results: list[VectorCandidate],
    top_k: int,
    rrf_k: int,
) -> list[HybridCandidate]:
    fused: dict[str, HybridCandidate] = {}

    for rank, item in enumerate(text_results, start=1):
        entry = fused.setdefault(
            item.attack_id,
            HybridCandidate(
                attack_id=item.attack_id,
                name=item.name,
                text_rank=None,
                vector_rank=None,
                text_score=None,
                vector_score=None,
                rrf_score=0.0,
            ),
        )
        entry.text_rank = rank
        entry.text_score = item.text_score
        entry.rrf_score += 1.0 / (rrf_k + rank)

    for rank, item in enumerate(vector_results, start=1):
        entry = fused.setdefault(
            item.attack_id,
            HybridCandidate(
                attack_id=item.attack_id,
                name=item.name,
                text_rank=None,
                vector_rank=None,
                text_score=None,
                vector_score=None,
                rrf_score=0.0,
            ),
        )
        entry.vector_rank = rank
        entry.vector_score = item.vector_score
        entry.rrf_score += 1.0 / (rrf_k + rank)

    fused_results = sorted(
        fused.values(),
        key=lambda row: (-row.rrf_score, row.attack_id),
    )

    return fused_results[:top_k]