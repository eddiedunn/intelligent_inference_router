from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .settings import settings


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing a shared-secret Authorization header."""

    async def dispatch(self, request: Request, call_next):
        secret = settings.shared_secret
        if secret:
            header = request.headers.get("Authorization")
            if header != f"Bearer {secret}":
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)
