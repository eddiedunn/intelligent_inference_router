"""Admin endpoints for API key management."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from iir.auth.apikey_db import add_api_key, list_api_keys, revoke_api_key
from iir.config import get_settings
from iir.dependencies import get_api_key

router = APIRouter(prefix="/admin")


class CreateKeyRequest(BaseModel):
    description: str | None = None
    priority: int = 0
    is_superadmin: bool = False


class CreateKeyResponse(BaseModel):
    api_key: str
    description: str | None
    priority: int


@router.post("/api-keys")
async def create_api_key(
    request: Request,
    body: CreateKeyRequest,
    _api_key: str = Depends(get_api_key),
) -> CreateKeyResponse:
    settings = get_settings()
    new_key = secrets.token_urlsafe(32)
    ip = request.client.host if request.client else "unknown"
    add_api_key(settings.auth_db_path, new_key, ip, body.description, body.priority, body.is_superadmin)
    return CreateKeyResponse(api_key=new_key, description=body.description, priority=body.priority)


@router.get("/api-keys")
async def get_api_keys(_api_key: str = Depends(get_api_key)) -> dict:
    settings = get_settings()
    keys = list_api_keys(settings.auth_db_path)
    return {"data": keys}


@router.delete("/api-keys/{key_prefix}")
async def delete_api_key(key_prefix: str, _api_key: str = Depends(get_api_key)) -> dict:
    settings = get_settings()
    keys = list_api_keys(settings.auth_db_path)
    target = next((k for k in keys if k["key"].startswith(key_prefix)), None)
    if not target:
        raise HTTPException(status_code=404, detail="API key not found")
    revoke_api_key(settings.auth_db_path, target["key"])
    return {"status": "revoked"}
