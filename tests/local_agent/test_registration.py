from __future__ import annotations

import asyncio

import httpx

import local_agent.main as agent


class DummyClient:
    def __init__(self) -> None:
        self.calls = 0

    async def __aenter__(self) -> "DummyClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        pass

    async def post(self, url: str, json: dict) -> httpx.Response:
        self.calls += 1
        if self.calls == 1:
            raise httpx.RequestError("unavailable", request=httpx.Request("POST", url))

        return httpx.Response(200, request=httpx.Request("POST", url))


def test_register_retry(monkeypatch) -> None:
    client = DummyClient()
    monkeypatch.setattr(agent.httpx, "AsyncClient", lambda *a, **kw: client)
    original_sleep = asyncio.sleep
    monkeypatch.setattr(agent.asyncio, "sleep", lambda s: original_sleep(0))

    asyncio.run(agent.register_with_router())

    assert client.calls == 2
