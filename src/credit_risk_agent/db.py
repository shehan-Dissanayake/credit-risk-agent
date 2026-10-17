"""Postgres / Supabase connection helper."""

from __future__ import annotations

import psycopg
from psycopg.rows import TupleRow

from credit_risk_agent.config import get_settings


def connect() -> psycopg.Connection[TupleRow]:
    settings = get_settings()
    if settings.database_url is None:
        raise RuntimeError("CRA_DATABASE_URL is not set (see .env.example)")
    return psycopg.connect(
        settings.database_url.get_secret_value(),
        prepare_threshold=None,  # required for the Supabase transaction pooler
        connect_timeout=10,
    )


def check_database() -> dict[str, str]:
    """Return server version and pgvector status. Used by `cra db-check`."""
    with connect() as conn:
        version = conn.execute("select version()").fetchone()
        vector = conn.execute(
            "select extversion from pg_extension where extname = 'vector'"
        ).fetchone()
    return {
        "postgres": str(version[0]) if version else "unknown",
        "pgvector": str(vector[0]) if vector else "not installed",
    }
