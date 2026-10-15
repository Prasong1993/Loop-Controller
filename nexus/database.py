"""SQLite/PostgreSQL connection compatibility for NEXUS.

Set DATABASE_URL to use PostgreSQL in hosted environments. Local development and
unit tests continue to use SQLite when DATABASE_URL is absent.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


class _HybridRow(dict):
    """Mapping-compatible database row that also supports SQLite-style row[0]."""
    def __init__(self, values: dict[str, Any]):
        super().__init__(values)
        self._ordered_values = tuple(values.values())

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._ordered_values[key]
        return super().__getitem__(key)


def _hybrid_row_factory(cursor, values):
    return _HybridRow({column.name: value for column, value in zip(cursor.description, values)})


class _PostgresConnection:
    def __init__(self, connection):
        self._connection = connection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self._connection.close()
        return False

    def execute(self, sql, params=()):
        normalized = sql.strip().casefold()
        if normalized.startswith("pragma foreign_keys") or normalized.startswith("pragma busy_timeout"):
            return _EmptyCursor()
        if normalized.startswith("pragma table_info("):
            table = sql.strip()[len("PRAGMA table_info("):-1].strip().strip('"').strip("'")
            return self._connection.execute(
                "SELECT column_name AS name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
                (table,),
            )
        return self._connection.execute(sql.replace("?", "%s"), params)

    def executescript(self, script):
        for statement in script.split(";"):
            statement = statement.strip()
            if statement:
                self.execute(statement)


class _EmptyCursor:
    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def __iter__(self):
        return iter(())


def connect_database(database: str):
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith(("postgres://", "postgresql://")):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("DATABASE_URL requires psycopg; install requirements.txt") from exc
        return _PostgresConnection(psycopg.connect(url, row_factory=_hybrid_row_factory))

    Path(database).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=10000")
    return connection
