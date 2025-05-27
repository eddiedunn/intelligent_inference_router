from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import typer

from .registry import create_tables, get_session, upsert_model, clear_models

app = typer.Typer(help="Model registry administration")


@app.command()
def migrate() -> None:
    """Create database tables."""

    create_tables()


@app.command()
def seed(config: Path) -> None:
    """Seed the registry using a JSON file."""

    with config.open() as fh:
        models = json.load(fh)

    with get_session() as session:
        for item in models:
            upsert_model(session, item["name"], item["type"], item["endpoint"])


@app.command("add-model")
def add_model(name: str, type: str, endpoint: str) -> None:
    """Add or update a single model entry."""

    with get_session() as session:
        upsert_model(session, name, type, endpoint)


@app.command("refresh-openai")
def refresh_openai() -> None:
    """Fetch available OpenAI models and refresh the registry."""

    api_key = os.getenv("EXTERNAL_OPENAI_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
    if api_key is None:
        typer.echo("EXTERNAL_OPENAI_KEY not set", err=True)
        raise typer.Exit(1)

    url = f"{base_url.rstrip('/')}/v1/models"
    resp = httpx.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
    resp.raise_for_status()
    data = resp.json().get("data", [])

    with get_session() as session:
        clear_models(session)
        for item in data:
            model_id = item.get("id")
            if model_id:
                upsert_model(session, model_id, "openai", base_url)

    typer.echo(f"Inserted {len(data)} models")


if __name__ == "__main__":
    app()
