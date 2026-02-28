"""Async HTTP client for proxying requests to Bifrost."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("iir.bifrost")


class BifrostClient:
    def __init__(self, base_url: str, timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=10.0),
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("BifrostClient not started. Call start() first.")
        return self._client

    async def chat_completion(self, payload: dict[str, Any]) -> httpx.Response:
        return await self.client.post("/v1/chat/completions", json=payload)

    async def list_models(self) -> httpx.Response:
        return await self.client.get("/v1/models")

    async def health(self) -> bool:
        try:
            resp = await self.client.get("/health")
            return resp.status_code == 200
        except Exception:
            return False
