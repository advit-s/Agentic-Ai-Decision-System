"""SQLite database connection manager for the workspace layer.
Uses Python's built-in ``sqlite3`` module. No external ORM is added.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any


# Row factory for dict-like access
_DICT_ROW = sqlite3.Row


def _dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict[str, Any]:  # type: ignore[type-arg]
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


class DatabaseConnection:
    """Thin wrapper around a SQLite database file connection.
    Connections are opened per-instance and closed via context manager or
    explicit ``close()``. Table creation is idempotent and never drops data.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        """Open (or return cached) connection with WAL and busy timeout."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path,
                timeout=30,
                check_same_thread=False,
            )
            self._conn.row_factory = _dict_factory
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.connect().execute(sql, params)

    def executemany(self, sql: str, seq_of_params: list[tuple]) -> sqlite3.Cursor:
        return self.connect().executemany(sql, seq_of_params)

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __enter__(self) -> DatabaseConnection:
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def create_tables(conn: sqlite3.Connection) -> None:
    """Backward-compatible alias that delegates to ``run_migrations``."""
    from decision_system.storage.migrations import run_migrations

    run_migrations(conn)
