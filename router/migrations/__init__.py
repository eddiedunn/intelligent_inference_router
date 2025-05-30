"""Database migration helpers."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from sqlalchemy.engine import Engine


def run_all(engine: Engine) -> None:
    """Run all migration scripts in order."""
    path = Path(__file__).resolve().parent
    for file in sorted(path.glob("[0-9]*_*.py")):
        module = import_module(f"router.migrations.{file.stem}")
        module.upgrade(engine)
