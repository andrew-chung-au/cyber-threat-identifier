#!/usr/bin/env python3
from __future__ import annotations

import argparse
from typing import Any

import psycopg

from src.db import EMBEDDING_DIMENSIONS, get_connection


def info(message: str) -> None:
    print(f"[INFO] {message}")


def ok(message: str) -> None:
    print(f"[OK]   {message}")


def create_schema(connection: psycopg.Connection[Any]) -> None:
    info("Ensuring pgvector extension and database schema exist")

    with connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")

        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS techniques (
                attack_id TEXT PRIMARY KEY,
                stix_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                is_subtechnique BOOLEAN NOT NULL DEFAULT FALSE,
                parent_attack_id TEXT,
                tactics JSONB NOT NULL DEFAULT '[]'::jsonb,
                platforms JSONB NOT NULL DEFAULT '[]'::jsonb,
                description_raw TEXT NOT NULL,
                description_clean TEXT NOT NULL,
                embedding_text TEXT NOT NULL,
                embedding vector({EMBEDDING_DIMENSIONS}),
                embedding_model TEXT,
                embedding_updated_at TIMESTAMPTZ,
                source_url TEXT NOT NULL,
                source_created_at TIMESTAMPTZ,
                source_modified_at TIMESTAMPTZ,
                loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ingestion_runs (
                id BIGSERIAL PRIMARY KEY,
                stage TEXT NOT NULL,
                started_at TIMESTAMPTZ NOT NULL,
                completed_at TIMESTAMPTZ,
                input_path TEXT,
                input_sha256 TEXT,
                embedding_model TEXT,
                records_processed INTEGER,
                status TEXT NOT NULL,
                notes TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS techniques_attack_id_idx
            ON techniques (attack_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS techniques_name_idx
            ON techniques (name)
            """
        )

    connection.commit()
    ok("Database schema is ready")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialise PostgreSQL tables for Cyber Threat Identifier."
    )
    parser.parse_args()

    with get_connection() as connection:
        create_schema(connection)

    print()
    ok("Database initialisation completed successfully")
    print("  Database table: techniques")
    print("  Audit table:    ingestion_runs")


if __name__ == "__main__":
    main()