from __future__ import annotations

import logging
from src.database.db_connection import get_connection

logger = logging.getLogger(__name__)

def save_incident_query(
    *,
    query_id: str,
    query_text: str,
    answer_text: str,
    model_id: str,
    retrieved_technique_ids: list[str],
    retrieval_ms: float,
) -> None:
    """Logs the generated query and answer immediately upon completion."""
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO incident_queries (
                        query_id,
                        query_text,
                        answer_text,
                        model_id,
                        retrieved_technique_ids,
                        retrieval_ms
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        query_id,
                        query_text,
                        answer_text,
                        model_id,
                        "|".join(retrieved_technique_ids),
                        retrieval_ms,
                    ),
                )
            connection.commit()
    except Exception as e:
        logger.error(f"Failed to log incident query {query_id}: {e}")
        # We don't raise the error here because telemetry failure 
        # shouldn't break the user experience in the UI.


def save_feedback(
    *,
    query_id: str,
    feedback: str,
) -> None:
    """Appends user feedback to a previously logged query."""
    if feedback not in {"thumbs_up", "thumbs_down"}:
        raise ValueError(f"Unsupported feedback value: {feedback}")

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO feedback (query_id, feedback)
                    VALUES (%s, %s)
                    """,
                    (query_id, feedback),
                )
            connection.commit()
    except Exception as e:
        logger.error(f"Failed to save feedback for {query_id}: {e}")
        raise