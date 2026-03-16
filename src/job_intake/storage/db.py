"""Database connection helpers for canonical Postgres access."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from job_intake.settings import Settings, get_settings


def connect_db(settings: Settings | None = None) -> Connection[Any]:
    active_settings = settings or get_settings()
    return psycopg.connect(
        active_settings.database_dsn_required,
        row_factory=dict_row,
    )


@contextmanager
def db_connection(settings: Settings | None = None) -> Iterator[Connection[Any]]:
    connection = connect_db(settings)
    try:
        yield connection
    finally:
        connection.close()

