from __future__ import annotations

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from ..schemas import ChatCompletionRequest
from ..utils import stream_resp


async def forward(payload: ChatCompletionRequest, base_url: str, api_key: str | None):
    """Forward request to OpenRouter."""
    if api_key is None:
        raise HTTPException(status_code=500, detail="OpenRouter key not configured")

    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(base_url=base_url) as client:
        path = "/api/v1/chat/completions"
        if payload.stream:
            resp = await client.post(  # type: ignore[call-arg]
                path, json=payload.dict(), headers=headers, stream=True
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPError as exc:  # coverage: ignore
                raise HTTPException(
                    status_code=502, detail="External provider error"
                ) from exc
            return StreamingResponse(stream_resp(resp), media_type="text/event-stream")
        resp = await client.post(path, json=payload.dict(), headers=headers)
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # coverage: ignore
            raise HTTPException(
                status_code=502, detail="External provider error"
            ) from exc
        return resp.json()
