"""Forwarder for Anthropic provider API."""

from __future__ import annotations

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from ..schemas import ChatCompletionRequest
from typing import AsyncIterator

from .base import ApiProvider


class AnthropicProvider(ApiProvider):
    """Provider wrapper for the Anthropic API."""

    async def forward(
        self, payload: ChatCompletionRequest, base_url: str, api_key: str | None
    ):
        """Forward request to Anthropic."""
        if api_key is None:
            raise HTTPException(status_code=500, detail="Anthropic key not configured")

        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        path = "/v1/messages"
        if payload.stream:

            async def gen() -> AsyncIterator[str]:
                async with httpx.AsyncClient(base_url=base_url) as client:
                    async with client.stream(
                        "POST", path, json=payload.dict(), headers=headers
                    ) as resp:
                        try:
                            resp.raise_for_status()
                        except httpx.HTTPError as exc:  # coverage: ignore
                            raise HTTPException(
                                status_code=502, detail="External provider error"
                            ) from exc
                        async for chunk in resp.aiter_text():
                            yield chunk

            return StreamingResponse(gen(), media_type="text/event-stream")

        async with httpx.AsyncClient(base_url=base_url) as client:
            resp = await client.post(path, json=payload.dict(), headers=headers)
            try:
                resp.raise_for_status()
            except httpx.HTTPError as exc:  # coverage: ignore
                raise HTTPException(
                    status_code=502, detail="External provider error"
                ) from exc
            return resp.json()


async def forward(payload: ChatCompletionRequest, base_url: str, api_key: str | None):
    """Backward compatible wrapper for ``AnthropicProvider``."""
    provider = AnthropicProvider()
    return await provider.forward(payload, base_url, api_key)
