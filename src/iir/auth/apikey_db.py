"""SQLite-backed API key storage."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    created_ip TEXT,
    description TEXT,
    priority INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT 1,
    revoked_at TIMESTAMP,
    is_superadmin BOOLEAN DEFAULT 0
);
"""

_db_lock = threading.Lock()


def init_db(db_path: str | Path) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _db_lock, sqlite3.connect(str(db_path)) as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()


@contextmanager
def get_db(db_path: str | Path) -> Generator[sqlite3.Connection, None, None]:
    with _db_lock:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def add_api_key(
    db_path: str | Path,
    key: str,
    created_ip: str,
    description: str | None = None,
    priority: int = 0,
    is_superadmin: bool = False,
) -> None:
    with get_db(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO api_keys (key, created_ip, description, priority, is_superadmin) "
            "VALUES (?, ?, ?, ?, ?)",
            (key, created_ip, description, priority, int(is_superadmin)),
        )
        conn.commit()


def get_api_key(db_path: str | Path, key: str) -> dict[str, Any] | None:
    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key = ? AND active = 1", (key,)
        ).fetchone()
        return dict(row) if row else None


def revoke_api_key(db_path: str | Path, key: str) -> None:
    with get_db(db_path) as conn:
        conn.execute(
            "UPDATE api_keys SET active = 0, revoked_at = CURRENT_TIMESTAMP WHERE key = ?",
            (key,),
        )
        conn.commit()


def list_api_keys(db_path: str | Path) -> list[dict[str, Any]]:
    with get_db(db_path) as conn:
        rows = conn.execute("SELECT id, key, created_at, description, priority, active, is_superadmin FROM api_keys").fetchall()
        return [dict(row) for row in rows]
