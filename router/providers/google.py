from __future__ import annotations

import httpx
from fastapi import HTTPException

from ..schemas import ChatCompletionRequest


async def forward(payload: ChatCompletionRequest, base_url: str, api_key: str | None):
    """Forward request to Google."""
    if api_key is None:
        raise HTTPException(status_code=500, detail="Google key not configured")

    headers = {"Authorization": f"Bearer {api_key}"}
    model = payload.model
    path = f"/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(base_url=base_url) as client:
        resp = await client.post(path, json=payload.dict(), headers=headers)
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # coverage: ignore
            raise HTTPException(
                status_code=502, detail="External provider error"
            ) from exc
        return resp.json()
