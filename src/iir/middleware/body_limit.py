"""Middleware to enforce max request body size."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class BodyLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, max_bytes: int = 1_048_576) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"error": {
                            "type": "validation_error",
                            "code": "request_too_large",
                            "message": f"Request body too large (max {self.max_bytes} bytes).",
                        }},
                    )
            except ValueError:
                pass
        return await call_next(request)
