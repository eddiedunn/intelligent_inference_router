import httpx
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
import pytest

import router.main as router_main
import router.registry as registry
from sqlalchemy import create_engine
from router.providers import openrouter
from router.schemas import ChatCompletionRequest, Message

openrouter_app = FastAPI()


@openrouter_app.post("/api/v1/chat/completions")
async def _completions(payload: router_main.ChatCompletionRequest):

    user_msg = payload.messages[-1].content if payload.messages else ""
    content = f"OpenRouter: {user_msg}"
    return {
        "id": "or-1",
        "object": "chat.completion",
        "created": 0,
        "model": payload.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def test_forward_to_openrouter(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OPENROUTER_BASE_URL", "http://testserver")
    monkeypatch.setenv("EXTERNAL_OPENROUTER_KEY", "dummy")
    router_main.settings = router_main.Settings()

    db_path = tmp_path / "models.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    router_main.settings = router_main.Settings()
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    with registry.get_session() as session:

        registry.upsert_model(session, "orc-1", "openrouter", "unused", "api")

        registry.upsert_model(session, "mixtral-8x7b", "openrouter", "unused", "api")

    real_async_client = httpx.AsyncClient
    transport = httpx.ASGITransport(app=openrouter_app)

    def client_factory(*args, **kwargs):
        return real_async_client(transport=transport, base_url="http://testserver")

    monkeypatch.setattr(router_main.httpx, "AsyncClient", client_factory)

    with TestClient(router_main.app) as client:
        payload = {
            "model": "orc-1",
            "messages": [{"role": "user", "content": "hi"}],
        }
        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 200
        assert response.json()["choices"][0]["message"]["content"] == "OpenRouter: hi"


def test_openrouter_requires_key():
    payload = ChatCompletionRequest(
        model="m", messages=[Message(role="user", content="x")]
    )
    with pytest.raises(HTTPException):
        asyncio.run(openrouter.forward(payload, "http://test", None))


def test_openrouter_streaming(monkeypatch):
    chunks = ["a", "b", "c"]

    class DummyResp:
        def __init__(self) -> None:
            self._chunks = chunks

        def raise_for_status(self) -> None:
            pass

        async def aiter_text(self):
            for chunk in self._chunks:
                yield chunk

    class DummyContext:
        def __init__(self, resp: DummyResp) -> None:
            self.resp = resp

        async def __aenter__(self) -> DummyResp:
            return self.resp

        async def __aexit__(self, exc_type, exc, tb) -> None:
            pass

    class DummyClient:
        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            pass

        def stream(
            self, method: str, path: str, json: dict, headers: dict
        ) -> DummyContext:
            return DummyContext(DummyResp())

    monkeypatch.setattr(openrouter.httpx, "AsyncClient", lambda *a, **kw: DummyClient())

    payload = ChatCompletionRequest(
        model="m",
        messages=[Message(role="user", content="hi")],
        stream=True,
    )
    resp = asyncio.run(openrouter.forward(payload, "http://x", "key"))
    assert isinstance(resp, StreamingResponse)

    async def collect() -> list[str]:
        result: list[str] = []
        async for chunk in resp.body_iterator:
            if hasattr(chunk, "decode"):
                result.append(chunk.decode())
            else:
                result.append(str(chunk))
        return result

    assert asyncio.run(collect()) == chunks
