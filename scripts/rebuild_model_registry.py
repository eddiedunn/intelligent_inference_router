#!/usr/bin/env python3
"""
Rebuilds the IIR model registry database (~/.agent_coder/models.db) from scratch by fetching real models from all supported providers.
- Drops and recreates the 'models' table
- Fetches models from OpenAI, Anthropic, VeniceAI, HuggingFace, Google Gemini, and OpenRouter
- Inserts all fetched models into the SQLite DB

Requires provider API keys to be set in the environment (.env or shell).
"""
import os
import sqlite3
import sys
from pathlib import Path

# Always add the project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from router.refresh_models import fetch_openai_models, fetch_anthropic_models, fetch_veniceai_models, fetch_gemini_models, fetch_huggingface_models, fetch_openrouter_models

REGISTRY_PATH = os.path.expanduser("~/.agent_coder/models.db")
SCHEMA = """
CREATE TABLE IF NOT EXISTS models (
    id TEXT,
    provider TEXT,
    location TEXT,
    category_json TEXT,
    function_calling INTEGER,
    model_family TEXT,
    traits_json TEXT,
    endpoint_url TEXT,
    file_path TEXT,
    metadata_json TEXT,
    PRIMARY KEY (id, provider, location)
);
"""

def main():
    Path(os.path.dirname(REGISTRY_PATH)).mkdir(parents=True, exist_ok=True)
    print("[IIR] Rebuilding model registry at:", REGISTRY_PATH)
    conn = sqlite3.connect(REGISTRY_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS models;")
    c.execute(SCHEMA)
    all_models = []
    # Fetch from all providers
    print("[IIR] Fetching OpenAI models...")
    all_models += fetch_openai_models()
    print("[IIR] Fetching Anthropic models...")
    all_models += fetch_anthropic_models()
    print("[IIR] Fetching VeniceAI models...")
    all_models += fetch_veniceai_models()
    print("[IIR] Fetching HuggingFace models...")
    all_models += fetch_huggingface_models()
    print("[IIR] Fetching Gemini models...")
    all_models += fetch_gemini_models()
    print("[IIR] Fetching OpenRouter models...")
    all_models += fetch_openrouter_models()
    # Remove duplicates (by id, provider, location)
    seen = set()
    deduped = []
    for m in all_models:
        key = (m.get("id"), m.get("provider"), m.get("location"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(m)
    print(f"[IIR] Inserting {len(deduped)} models into registry...")
    for m in deduped:
        c.execute(
            """
            INSERT OR REPLACE INTO models (
                id, provider, location, category_json, function_calling, model_family, traits_json, endpoint_url, file_path, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                m.get("id"),
                m.get("provider"),
                m.get("location"),
                str(m.get("category", [])),
                int(m.get("function_calling", False)),
                m.get("model_family", ""),
                str(m.get("traits", [])),
                m.get("endpoint_url"),
                m.get("file_path"),
                str(m.get("metadata", {})),
            )
        )
    conn.commit()
    conn.close()
    print("[IIR] Model registry rebuild complete.")

if __name__ == "__main__":
    main()
