from __future__ import annotations

from typing import Any

from src.retrieval.schemas import RetrievedCandidate, TextCandidate


def retrieve_top_k_text(
    connection: Any,
    query_text: str,
    top_k: int,
) -> list[RetrievedCandidate]:
    sql = """
        WITH ranked_matches AS (
            SELECT
                attack_id,
                name,
                ts_rank_cd(
                    search_vector,
                    websearch_to_tsquery('english', %s),
                    1
                ) AS retrieval_score
            FROM techniques
            WHERE search_vector @@ websearch_to_tsquery('english', %s)
        )
        SELECT
            attack_id,
            name,
            retrieval_score
        FROM ranked_matches
        WHERE retrieval_score > 0
        ORDER BY retrieval_score DESC, attack_id ASC
        LIMIT %s
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, (query_text, query_text, top_k))
        rows = cursor.fetchall()

    return [
        RetrievedCandidate(
            attack_id=attack_id,
            name=name,
            retrieval_score=float(score),
        )
        for attack_id, name, score in rows
    ]


def retrieve_text_candidates(
    connection: Any,
    query_text: str,
    candidate_k: int,
) -> list[TextCandidate]:
    sql = """
        WITH ranked_matches AS (
            SELECT
                attack_id,
                name,
                ts_rank_cd(
                    search_vector,
                    websearch_to_tsquery('english', %s),
                    1
                ) AS retrieval_score
            FROM techniques
            WHERE search_vector @@ websearch_to_tsquery('english', %s)
        )
        SELECT
            attack_id,
            name,
            retrieval_score
        FROM ranked_matches
        WHERE retrieval_score > 0
        ORDER BY retrieval_score DESC, attack_id ASC
        LIMIT %s
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, (query_text, query_text, candidate_k))
        rows = cursor.fetchall()

    return [
        TextCandidate(
            attack_id=attack_id,
            name=name,
            text_score=float(score),
        )
        for attack_id, name, score in rows
    ]