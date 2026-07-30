from __future__ import annotations

import os
from typing import Any

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

EMBEDDING_DIMENSIONS = 384


def get_database_url() -> str:
    load_dotenv()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise EnvironmentError(
            "DATABASE_URL is not set.\n"
            "Create a .env file in the repository root with DATABASE_URL=..."
        )

    return database_url


def get_connection(register_pgvector: bool = False) -> psycopg.Connection[Any]:
    connection = psycopg.connect(get_database_url())

    if register_pgvector:
        register_vector(connection)

    return connection