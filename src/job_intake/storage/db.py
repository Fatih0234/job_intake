"""Database connection helpers for canonical Postgres access."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import urlsplit

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from job_intake.settings import Settings, get_settings


def require_database_dsn(settings: Settings | None = None) -> str:
    active_settings = settings or get_settings()
    database_dsn = active_settings.database_dsn_required.strip()
    direct_host = f"db.{active_settings.supabase.project_ref}.supabase.co"

    if not database_dsn:
        raise RuntimeError(
            "SUPABASE_DB_URL is required for database operations. "
            "Fill it in locally before using storage helpers.",
        )

    if urlsplit(database_dsn).hostname == direct_host:
        raise RuntimeError(
            "SUPABASE_DB_URL must use a Supabase pooler DSN on this machine. "
            f"The direct host {direct_host} is not supported here. "
            "Set a full pooler URL in .env.local instead.",
        )

    return database_dsn


def connect_db(settings: Settings | None = None) -> Connection[Any]:
    return psycopg.connect(
        require_database_dsn(settings),
        row_factory=dict_row,
    )


@contextmanager
def db_connection(settings: Settings | None = None) -> Iterator[Connection[Any]]:
    connection = connect_db(settings)
    try:
        yield connection
    finally:
        connection.close()
