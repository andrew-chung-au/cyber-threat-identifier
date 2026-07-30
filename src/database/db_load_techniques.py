#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from src.db import get_connection

DEFAULT_INPUT_PATH = "data/processed/techniques.jsonl"


def info(message: str) -> None:
    print(f"[INFO] {message}")


def ok(message: str) -> None:
    print(f"[OK]   {message}")


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def load_jsonl(input_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    with input_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number} in {input_path}: {error}"
                ) from error

            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected a JSON object on line {line_number} in {input_path}."
                )

            records.append(record)

    return records


def require_string(record: dict[str, Any], field_name: str) -> str:
    value = record.get(field_name)

    if not isinstance(value, str) or not value.strip():
        attack_id = record.get("attack_id", "<unknown>")
        raise ValueError(
            f"Record {attack_id} is missing a non-empty '{field_name}' field."
        )

    return value.strip()


def get_tactic_short_names(record: dict[str, Any]) -> list[str]:
    tactics = record.get("tactics", [])

    if not isinstance(tactics, list):
        return []

    return [
        tactic["short_name"].strip()
        for tactic in tactics
        if isinstance(tactic, dict)
        and isinstance(tactic.get("short_name"), str)
        and tactic["short_name"].strip()
    ]


def get_tactic_display_names(record: dict[str, Any]) -> list[str]:
    tactics = record.get("tactics", [])

    if not isinstance(tactics, list):
        return []

    return [
        tactic["name"].strip()
        for tactic in tactics
        if isinstance(tactic, dict)
        and isinstance(tactic.get("name"), str)
        and tactic["name"].strip()
    ]


def get_platforms(record: dict[str, Any]) -> list[str]:
    platforms = record.get("platforms", [])

    if not isinstance(platforms, list):
        return []

    return [
        platform.strip()
        for platform in platforms
        if isinstance(platform, str) and platform.strip()
    ]


def build_embedding_text(record: dict[str, Any]) -> str:
    attack_id = require_string(record, "attack_id")
    name = require_string(record, "name")
    description_clean = require_string(record, "description_clean")

    tactics = get_tactic_display_names(record)
    platforms = get_platforms(record)

    tactics_text = ", ".join(tactics) if tactics else "Not specified"
    platforms_text = ", ".join(platforms) if platforms else "Not specified"

    return (
        f"ATT&CK ID: {attack_id}\n"
        f"Technique: {name}\n"
        f"Tactics: {tactics_text}\n"
        f"Platforms: {platforms_text}\n\n"
        f"Description:\n{description_clean}"
    )


def build_database_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for record in records:
        parent_attack_id = record.get("parent_attack_id")

        if parent_attack_id is not None and not isinstance(parent_attack_id, str):
            raise ValueError(
                f"Record {record.get('attack_id', '<unknown>')} has an invalid "
                "'parent_attack_id' field."
            )

        rows.append(
            {
                "attack_id": require_string(record, "attack_id"),
                "stix_id": require_string(record, "stix_id"),
                "name": require_string(record, "name"),
                "is_subtechnique": bool(record.get("is_subtechnique", False)),
                "parent_attack_id": parent_attack_id,
                "tactics": Jsonb(get_tactic_short_names(record)),
                "platforms": Jsonb(get_platforms(record)),
                "description_raw": require_string(record, "description_raw"),
                "description_clean": require_string(record, "description_clean"),
                "embedding_text": build_embedding_text(record),
                "source_url": require_string(record, "source_url"),
                "source_created_at": record.get("created"),
                "source_modified_at": record.get("modified"),
            }
        )

    return rows


def create_ingestion_run(
    connection: Any,
    input_path: Path,
    input_sha256: str,
) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ingestion_runs (
                stage,
                started_at,
                input_path,
                input_sha256,
                status,
                notes
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                "load_techniques",
                datetime.now(UTC).replace(microsecond=0),
                str(input_path),
                input_sha256,
                "running",
                "Technique loading started.",
            ),
        )

        run_id = cursor.fetchone()[0]

    connection.commit()
    return run_id


def complete_ingestion_run(
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


def upsert_techniques(connection: Any, rows: list[dict[str, Any]]) -> None:
    info(f"Upserting {len(rows)} technique records into PostgreSQL")

    sql = """
        INSERT INTO techniques (
            attack_id,
            stix_id,
            name,
            is_subtechnique,
            parent_attack_id,
            tactics,
            platforms,
            description_raw,
            description_clean,
            embedding_text,
            source_url,
            source_created_at,
            source_modified_at,
            loaded_at,
            updated_at
        )
        VALUES (
            %(attack_id)s,
            %(stix_id)s,
            %(name)s,
            %(is_subtechnique)s,
            %(parent_attack_id)s,
            %(tactics)s,
            %(platforms)s,
            %(description_raw)s,
            %(description_clean)s,
            %(embedding_text)s,
            %(source_url)s,
            %(source_created_at)s,
            %(source_modified_at)s,
            NOW(),
            NOW()
        )
        ON CONFLICT (attack_id)
        DO UPDATE SET
            stix_id = EXCLUDED.stix_id,
            name = EXCLUDED.name,
            is_subtechnique = EXCLUDED.is_subtechnique,
            parent_attack_id = EXCLUDED.parent_attack_id,
            tactics = EXCLUDED.tactics,
            platforms = EXCLUDED.platforms,
            description_raw = EXCLUDED.description_raw,
            description_clean = EXCLUDED.description_clean,
            embedding_text = EXCLUDED.embedding_text,
            source_url = EXCLUDED.source_url,
            source_created_at = EXCLUDED.source_created_at,
            source_modified_at = EXCLUDED.source_modified_at,
            embedding = NULL,
            embedding_model = NULL,
            embedding_updated_at = NULL,
            updated_at = NOW()
    """

    with connection.cursor() as cursor:
        cursor.executemany(sql, rows)

    connection.commit()
    ok(f"Upserted {len(rows)} technique records")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Load extracted MITRE ATT&CK technique records into PostgreSQL. "
            "This stage does not create embeddings."
        )
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_PATH,
        help="Input JSONL file from extract_attack_techniques.py.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Processed technique dataset not found: {input_path}\n"
            "Run: uv run python -m src.ingestion.extract_attack_techniques"
        )

    info(f"Reading processed technique records: {input_path}")
    records = load_jsonl(input_path)

    if not records:
        raise ValueError(f"No records found in {input_path}.")

    attack_ids = [require_string(record, "attack_id") for record in records]

    if len(attack_ids) != len(set(attack_ids)):
        raise ValueError(
            "Duplicate ATT&CK IDs found in techniques.jsonl. "
            "Resolve them in extract_attack_techniques.py before loading."
        )

    rows = build_database_rows(records)
    input_sha256 = sha256_file(input_path)

    info(f"Validated {len(rows)} technique records")

    with get_connection() as connection:
        run_id = create_ingestion_run(
            connection=connection,
            input_path=input_path,
            input_sha256=input_sha256,
        )

        try:
            upsert_techniques(connection, rows)

            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM techniques")
                total_techniques = cursor.fetchone()[0]

            complete_ingestion_run(
                connection=connection,
                run_id=run_id,
                records_processed=len(rows),
                status="completed",
                notes=(
                    f"Upserted {len(rows)} records. "
                    f"Techniques table now contains {total_techniques} records. "
                    "Embeddings were cleared for refreshed records."
                ),
            )

        except Exception as error:
            connection.rollback()

            complete_ingestion_run(
                connection=connection,
                run_id=run_id,
                records_processed=0,
                status="failed",
                notes=str(error),
            )
            raise

    print()
    ok("Technique loading completed successfully")
    print(f"  Input dataset:      {input_path}")
    print(f"  Input SHA-256:      {input_sha256}")
    print(f"  Records processed:  {len(rows)}")
    print("  Database table:     techniques")
    print("  Embeddings:         not generated in this stage")


if __name__ == "__main__":
    main()