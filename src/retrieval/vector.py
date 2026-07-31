from __future__ import annotations

from typing import Any

from sentence_transformers import SentenceTransformer

from src.retrieval.schemas import RetrievedCandidate, VectorCandidate


def embed_query(
    model: SentenceTransformer,
    query_text: str,
) -> list[float]:
    return model.encode(
        query_text,
        normalize_embeddings=True,
    ).tolist()


def retrieve_top_k_vector(
    connection: Any,
    query_embedding: list[float],
    top_k: int,
) -> list[RetrievedCandidate]:
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
        RetrievedCandidate(
            attack_id=attack_id,
            name=name,
            retrieval_score=float(score),
        )
        for attack_id, name, score in rows
    ]


def retrieve_vector_candidates(
    connection: Any,
    query_embedding: list[float],
    candidate_k: int,
) -> list[VectorCandidate]:
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
        cursor.execute(sql, (query_embedding, query_embedding, candidate_k))
        rows = cursor.fetchall()

    return [
        VectorCandidate(
            attack_id=attack_id,
            name=name,
            vector_score=float(score),
        )
        for attack_id, name, score in rows
    ]