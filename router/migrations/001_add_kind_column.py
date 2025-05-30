"""Add 'kind' column to models table."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine


def upgrade(engine: Engine) -> None:
    """Add 'kind' column if missing."""
    with engine.begin() as conn:
        result = conn.execute(text("PRAGMA table_info(models)")).fetchall()
        columns = {row[1] for row in result}
        if "kind" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE models ADD COLUMN kind VARCHAR NOT NULL DEFAULT 'api'"
                )
            )
