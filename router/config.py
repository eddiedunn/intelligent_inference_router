from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseSettings as _BaseSettings
else:  # pragma: no cover - runtime import
    try:  # pydantic v2
        from pydantic_settings import BaseSettings as _BaseSettings
    except ImportError:  # fallback for pydantic v1
        from pydantic.v1 import BaseSettings as _BaseSettings

try:
    with open(Path(__file__).resolve().parents[1] / "pyproject.toml", "rb") as f:
        _TOOL_CONFIG = tomllib.load(f).get("tool", {}).get("router", {})
except Exception:
    _TOOL_CONFIG = {}


class Settings(_BaseSettings):  # type: ignore[misc, valid-type]
    """Configuration for the router service."""

    sqlite_db_path: str = "data/models.db"
    local_agent_url: str = "http://localhost:5000"
    openai_base_url: str = "https://api.openai.com"
    external_openai_key: str | None = None
    llmd_endpoint: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    external_anthropic_key: str | None = None
    google_base_url: str = "https://generativelanguage.googleapis.com"
    external_google_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai"
    external_openrouter_key: str | None = None
    grok_base_url: str = "https://api.groq.com"
    external_grok_key: str | None = None
    venice_base_url: str = "https://api.venice.ai"
    external_venice_key: str | None = None
    log_level: str = "INFO"
    log_path: str = "logs/router.log"
    cache_ttl: int = 300
    rate_limit_requests: int = 60
    rate_limit_window: int = 60
    router_cost_weight: float = _TOOL_CONFIG.get("cost_weight", 1.0)
    router_latency_weight: float = _TOOL_CONFIG.get("latency_weight", 1.0)
    router_cost_threshold: int = _TOOL_CONFIG.get("cost_threshold", 1000)
    hf_cache_dir: str = "data/hf_models"
    hf_device: str = "cpu"
    hugging_face_hub_token: str | None = None

    class Config:
        case_sensitive = False
