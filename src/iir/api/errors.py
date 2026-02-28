"""Standardized error response models and helpers."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    loc: list[Any]
    msg: str
    type: str
    ctx: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    type: str
    code: str
    message: str
    details: list[ErrorDetail] | None = None
    param: str | None = None
    trace_id: str | None = None

    model_config = {"json_schema_extra": {"example": {
        "type": "validation_error",
        "code": "invalid_payload",
        "message": "Request payload validation failed.",
        "trace_id": "req_abc123",
    }}}


def error_json(
    status_code: int,
    error_type: str,
    code: str,
    message: str,
    param: str | None = None,
) -> JSONResponse:
    trace_id = f"req_{uuid.uuid4().hex[:12]}"
    body = ErrorResponse(type=error_type, code=code, message=message, param=param, trace_id=trace_id)
    return JSONResponse(
        status_code=status_code,
        content={"error": body.model_dump(exclude_none=True)},
    )


def validation_error(message: str, code: str = "invalid_payload", param: str | None = None, status_code: int = 400) -> JSONResponse:
    return error_json(status_code, "validation_error", code, message, param)


def rate_limit_error() -> JSONResponse:
    return error_json(429, "rate_limit_error", "rate_limit_exceeded", "Rate limit exceeded")


def upstream_error(message: str) -> JSONResponse:
    return error_json(502, "upstream_error", "remote_provider_error", message)


def not_found_error(path: str) -> JSONResponse:
    return error_json(404, "not_found", "not_found", f"Not found: {path}")
