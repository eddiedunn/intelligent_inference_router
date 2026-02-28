"""Unified configuration via Pydantic Settings + YAML defaults."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_yaml_defaults() -> dict[str, Any]:
    path = _PROJECT_ROOT / "config" / "defaults.yaml"
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IIR_", env_file=".env", extra="ignore")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # Bifrost gateway
    bifrost_url: str = "http://localhost:8080"
    bifrost_timeout: int = 120

    # Ollama (local models)
    ollama_url: str = "http://localhost:11434"
    classifier_model: str = "llama3.2:1b"
    ollama_pull_on_startup: bool = True

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    classification_cache_ttl: int = 3600
    redis_fallback_to_memory: bool = True

    # Auth
    api_key: str | None = None
    auth_db_path: str = str(_PROJECT_ROOT / "persistent-data" / "api_keys.sqlite3")
    require_auth: bool = True

    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_rpm: int = 200

    # Classifier
    classifier_strategy: str = "hybrid"  # rules_only | llm_only | hybrid

    # Routing
    routing_default_strategy: str = "cost-optimized"
    routing_config_path: str = str(_PROJECT_ROOT / "config" / "models.yaml")
    max_cost_per_request: float = 0.10
    prefer_local_under_tokens: int = 2000

    # Body limit
    max_body_size: int = 1_048_576

    # Secret scrubbing
    secret_scrubbing_enabled: bool = True
    secret_entropy_threshold: float = 4.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
