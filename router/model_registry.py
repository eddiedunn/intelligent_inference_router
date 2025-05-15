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
    raise RuntimeError("model_recommendations.json is deprecated and must not be read. All model registry operations must use the SQLite database.")

def rebuild_db():
    raise RuntimeError("rebuild_db cannot function: model_recommendations.json is deprecated and no longer supported. All model registry operations must use the SQLite database and real provider fetch.")

def list_models():
    conn = sqlite3.connect(REGISTRY_PATH)
    c = conn.cursor()
    c.execute("SELECT id, provider, location, category_json, function_calling, model_family, traits_json, endpoint_url, file_path, metadata_json FROM models")
    rows = c.fetchall()
    conn.close()
    data = []
    for row in rows:
        id, provider, location, category_json, function_calling, model_family, traits_json, endpoint_url, file_path, metadata_json = row
        def safe_json_load(val, default):
            if val is None:
                return default
            if isinstance(val, (dict, list)):
                return val
            if isinstance(val, str):
                val = val.strip()
                if not val:
                    return default
                try:
                    return json.loads(val)
                except Exception:
                    return default
            return default
        model = {
            "id": id,
            "provider": provider,
            "location": location,
            "category": safe_json_load(category_json, []),
            "function_calling": bool(function_calling),
            "model_family": model_family,
            "traits": safe_json_load(traits_json, []),
            "endpoint_url": endpoint_url,
            "file_path": file_path,
            "metadata": safe_json_load(metadata_json, {})
        }
        data.append(model)
    return {
        "object": "list",
        "data": data
    }
