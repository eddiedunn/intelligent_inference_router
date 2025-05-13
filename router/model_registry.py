# Imported from agent_coder/local_model_registry.py
# Core logic for model registry, listing, and Google model invocation

import os
import sqlite3
import json
from pathlib import Path

REGISTRY_PATH = os.path.expanduser("~/.agent_coder/models.db")
RECOMMENDATIONS_PATH = os.path.expanduser("~/.agent_coder/model_recommendations.json")

Path(os.path.dirname(REGISTRY_PATH)).mkdir(parents=True, exist_ok=True)

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

GOOGLE_API_URLS = {
    "gemini-pro": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
    "palm-2": "https://generativelanguage.googleapis.com/v1beta/models/palm-2:generateText"
}

def call_google_model(model_id, prompt, api_key, **kwargs):
    import requests
    url = GOOGLE_API_URLS.get(model_id)
    if not url:
        raise ValueError(f"Unknown Google model id: {model_id}")
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    data.update(kwargs)
    resp = requests.post(url, params=params, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json()

def load_recommended_models():
    if not os.path.exists(RECOMMENDATIONS_PATH):
        print(f"No model recommendations found at {RECOMMENDATIONS_PATH}.")
        return []
    with open(RECOMMENDATIONS_PATH, "r") as f:
        recs = json.load(f)
    models = []
    for entry in recs:
        category = entry.get("category")
        provider = entry.get("provider")
        location = entry.get("location")
        for m in entry.get("models", []):
            models.append({
                "id": m.get("id"),
                "provider": provider,
                "location": location,
                "category": [category],
                "function_calling": m.get("function_calling", False),
                "model_family": m.get("model_family", "unknown"),
                "traits": m.get("traits", []),
                "endpoint_url": m.get("endpoint_url"),
                "file_path": m.get("file_path"),
                "metadata": {"description": m.get("description", "")}
            })
    return models

def rebuild_db():
    conn = sqlite3.connect(REGISTRY_PATH)
    c = conn.cursor()
    # Always drop and recreate the models table
    c.execute("DROP TABLE IF EXISTS models;")
    c.execute(SCHEMA)
    # Only use the current recommendations file; if empty, registry will be empty
    models = load_recommended_models()
    for m in models:
        c.execute(
            """
            INSERT OR REPLACE INTO models (
                id, provider, location, category_json, function_calling, model_family, traits_json, endpoint_url, file_path, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                m["id"],
                m["provider"],
                m["location"],
                json.dumps(m.get("category", [])),
                int(m.get("function_calling", False)),
                m.get("model_family", ""),
                json.dumps(m.get("traits", [])),
                m.get("endpoint_url"),
                m.get("file_path"),
                json.dumps(m.get("metadata", {})),
            )
        )
    conn.commit()
    conn.close()

def list_models():
    conn = sqlite3.connect(REGISTRY_PATH)
    c = conn.cursor()
    c.execute("SELECT id, provider, location, category_json, function_calling, model_family, traits_json, endpoint_url, file_path, metadata_json FROM models")
    rows = c.fetchall()
    conn.close()
    data = []
    for row in rows:
        id, provider, location, category_json, function_calling, model_family, traits_json, endpoint_url, file_path, metadata_json = row
        model = {
            "id": id,
            "provider": provider,
            "location": location,
            "category": json.loads(category_json),
            "function_calling": bool(function_calling),
            "model_family": model_family,
            "traits": json.loads(traits_json),
            "endpoint_url": endpoint_url,
            "file_path": file_path,
            "metadata": json.loads(metadata_json)
        }
        data.append(model)
    return {
        "object": "list",
        "data": data
    }
