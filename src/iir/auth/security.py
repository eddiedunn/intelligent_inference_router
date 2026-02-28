"""API key authentication via Bearer token + SQLite lookup."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status

from iir.auth.apikey_db import get_api_key
from iir.config import get_settings

logger = logging.getLogger("iir.auth")


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return auth.split(" ", 1)[1]


async def api_key_auth(request: Request) -> str:
    """FastAPI dependency that validates the API key and returns it."""
    settings = get_settings()
    key = _extract_bearer_token(request)

    row = get_api_key(settings.auth_db_path, key)
    if row is not None:
        return key

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key",
    )
