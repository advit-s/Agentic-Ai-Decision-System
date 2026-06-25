"""Idempotent SQLite schema migrations for the workspace layer.
Tables are created with ``IF NOT EXISTS`` and are never dropped automatically.
Calling ``run_migrations`` on an existing database is a no-op for already-created tables.
"""

from __future__ import annotations

MIGRATIONS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS workspaces (
        workspace_id TEXT PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        active INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
        artifact_id TEXT PRIMARY KEY,
        workspace_id TEXT NOT NULL,
        artifact_type TEXT NOT NULL,
        source_path TEXT NOT NULL DEFAULT '',
        title TEXT NOT NULL DEFAULT '',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        content_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    # Indexes for common queries (idempotent on SQLite < 3.37; skip error)
    """
    CREATE INDEX IF NOT EXISTS idx_artifacts_workspace ON artifacts(workspace_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_workspaces_active ON workspaces(active)
    """,
]


def run_migrations(conn: sqlite3.Connection) -> None:
    """Execute all migration SQL statements in order.
    Each statement uses ``IF NOT EXISTS`` so repeated calls are safe.
    Foreign keys are enabled before running migrations.
    """
    conn.execute("PRAGMA foreign_keys=ON")
    for sql in MIGRATIONS:
        conn.executescript(sql)
    conn.commit()
