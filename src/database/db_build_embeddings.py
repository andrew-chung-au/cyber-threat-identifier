#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime
from typing import Any

from sentence_transformers import SentenceTransformer

from src.db import get_connection

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_BATCH_SIZE = 64


def info(message: str) -> None:
    print(f"[INFO] {message}")


def ok(message: str) -> None:
    print(f"[OK]   {message}")


def create_embedding_run(
    connection: Any,
    model_name: str,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ingestion_runs (
                stage,
                started_at,
                embedding_model,
                status,
                notes
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                "build_embeddings",
                datetime.now(UTC).replace(microsecond=0),
                model_name,
                "running",
                "Embedding generation started.",
            ),
        )

        run_id = cursor.fetchone()[0]

    connection.commit()
    return run_id


def complete_embedding_run(
    connection: Any,
    run_id: int,
    records_processed: int,
    status: str,
    notes: str,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE ingestion_runs
            SET
                completed_at = %s,
                records_processed = %s,
                status = %s,
                notes = %s
            WHERE id = %s
            """,
            (
                datetime.now(UTC).replace(microsecond=0),
                records_processed,
                status,
                notes,
                run_id,
            ),
        )

    connection.commit()


def get_techniques_to_embed(
    connection: Any,
    model_name: str,
    force: bool,
) -> list[dict[str, str]]:
    if force:
        sql = """
            SELECT attack_id, embedding_text
            FROM techniques
            ORDER BY attack_id
        """
        parameters: tuple[object, ...] = ()
    else:
        sql = """
            SELECT attack_id, embedding_text
            FROM techniques
            WHERE embedding IS NULL
               OR embedding_model IS DISTINCT FROM %s
            ORDER BY attack_id
        """
        parameters = (model_name,)

    with connection.cursor() as cursor:
        cursor.execute(sql, parameters)
        rows = cursor.fetchall()

    return [
        {
            "attack_id": attack_id,
            "embedding_text": embedding_text,
        }
        for attack_id, embedding_text in rows
    ]


def update_embeddings(
    connection: Any,
    records: list[dict[str, str]],
    model: SentenceTransformer,
    model_name: str,
    batch_size: int,
) -> int:
    if not records:
        return 0

    total_batches = (len(records) + batch_size - 1) // batch_size
    processed = 0

    sql = """
        UPDATE techniques
        SET
            embedding = %(embedding)s,
            embedding_model = %(embedding_model)s,
            embedding_updated_at = NOW(),
            updated_at = NOW()
        WHERE attack_id = %(attack_id)s
    """

    for batch_start in range(0, len(records), batch_size):
        batch_number = (batch_start // batch_size) + 1
        batch = records[batch_start : batch_start + batch_size]

        info(
            f"Creating embeddings for batch {batch_number}/{total_batches} "
            f"({len(batch)} techniques)"
        )

        embedding_texts = [record["embedding_text"] for record in batch]

        embeddings = model.encode(
            embedding_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

        update_rows = [
            {
                "attack_id": record["attack_id"],
                "embedding": embedding.tolist(),
                "embedding_model": model_name,
            }
            for record, embedding in zip(batch, embeddings, strict=True)
        ]

        with connection.cursor() as cursor:
            cursor.executemany(sql, update_rows)

        connection.commit()
        processed += len(update_rows)

    return processed


def create_hnsw_index(connection: Any) -> None:
    info("Ensuring HNSW cosine-distance index exists")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS techniques_embedding_hnsw_idx
            ON techniques
            USING hnsw (embedding vector_cosine_ops)
            WHERE embedding IS NOT NULL
            """
        )
        cursor.execute("ANALYZE techniques")

    connection.commit()
    ok("HNSW vector index is ready")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate local embeddings for PostgreSQL ATT&CK technique records."
        )
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL_NAME,
        help="Sentence Transformers embedding model.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of technique records to embed per batch.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild embeddings even when the selected model is already recorded.",
    )
    parser.add_argument(
        "--create-hnsw-index",
        action="store_true",
        help="Create the HNSW cosine-distance index after embedding.",
    )
    args = parser.parse_args()

    if args.batch_size < 1:
        raise ValueError("--batch-size must be at least 1.")

    with get_connection(register_pgvector=True) as connection:
        records = get_techniques_to_embed(
            connection=connection,
            model_name=args.model,
            force=args.force,
        )

        if not records:
            ok(
                "No technique records require embeddings for the selected model. "
                "Use --force to rebuild them."
            )

            if args.create_hnsw_index:
                create_hnsw_index(connection)

            return

        info(f"Loading local embedding model: {args.model}")
        model = SentenceTransformer(args.model)
        ok("Embedding model ready")

        run_id = create_embedding_run(
            connection=connection,
            model_name=args.model,
        )

        try:
            processed = update_embeddings(
                connection=connection,
                records=records,
                model=model,
                model_name=args.model,
                batch_size=args.batch_size,
            )

            if args.create_hnsw_index:
                create_hnsw_index(connection)

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM techniques
                    WHERE embedding IS NOT NULL
                    """
                )
                total_embedded = cursor.fetchone()[0]

            complete_embedding_run(
                connection=connection,
                run_id=run_id,
                records_processed=processed,
                status="completed",
                notes=(
                    f"Generated embeddings for {processed} techniques using "
                    f"{args.model}. Techniques with embeddings: {total_embedded}."
                ),
            )

        except Exception as error:
            connection.rollback()

            complete_embedding_run(
                connection=connection,
                run_id=run_id,
                records_processed=0,
                status="failed",
                notes=str(error),
            )
            raise

    print()
    ok("Embedding generation completed successfully")
    print(f"  Embedding model:    {args.model}")
    print(f"  Records processed:  {processed}")
    print("  Database table:     techniques")


if __name__ == "__main__":
    main()