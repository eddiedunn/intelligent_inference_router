from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Application configuration loaded from environment variables."""

    shared_secret: str | None = os.getenv("ROUTER_SHARED_SECRET")


settings = Settings()
