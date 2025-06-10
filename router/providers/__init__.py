"""Collection of provider implementations for external APIs."""

# ruff: noqa: E402

from __future__ import annotations

from types import ModuleType

from .base import ApiProvider, WeightProvider

PROVIDER_REGISTRY: dict[str, ModuleType] = {}


def register_provider(name: str, module: ModuleType) -> None:
    """Register ``module`` under ``name``."""

    PROVIDER_REGISTRY[name] = module


from . import (
    anthropic,
    google,
    openrouter,
    grok,
    venice,
    openai,
    huggingface,
)  # noqa: E402

__all__ = [
    "ApiProvider",
    "WeightProvider",
    "PROVIDER_REGISTRY",
    "register_provider",
    "anthropic",
    "google",
    "openrouter",
    "grok",
    "venice",
    "openai",
    "huggingface",
]
