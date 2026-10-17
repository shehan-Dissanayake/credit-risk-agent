"""Minimal SQL migration runner.

Applies migrations/*.sql in filename order, each exactly once, and records them in
the schema_migrations table. Run from the repo root: `cra migrate`.
"""

from __future__ import annotations

from pathlib import Path

from credit_risk_agent.db import connect


def discover_migrations(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.sql"))


def apply_migrations(directory: Path = Path("migrations")) -> list[str]:
    applied_now: list[str] = []
    with connect() as conn:
        conn.execute(
            "create table if not exists schema_migrations ("
            "name text primary key, applied_at timestamptz not null default now())"
        )
        conn.commit()
        done = {row[0] for row in conn.execute("select name from schema_migrations")}
        for path in discover_migrations(directory):
            if path.name in done:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("insert into schema_migrations (name) values (%s)", (path.name,))
            conn.commit()
            applied_now.append(path.name)
    return applied_now
