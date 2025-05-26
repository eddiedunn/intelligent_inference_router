import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

import router.main as router_main

external_app = FastAPI()


@external_app.post("/v1/chat/completions")
async def _completion(payload: router_main.ChatCompletionRequest):
    user_msg = payload.messages[-1].content if payload.messages else ""
    content = f"OpenAI: {user_msg}"
    return {
        "id": "ext-1",
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


def test_forward_to_openai(monkeypatch) -> None:
    monkeypatch.setattr(router_main, "OPENAI_BASE_URL", "http://testserver")
    monkeypatch.setattr(router_main, "EXTERNAL_OPENAI_KEY", "dummy")

    def client_factory(*args, **kwargs):
        return httpx.AsyncClient(app=external_app, base_url="http://testserver")

    monkeypatch.setattr(router_main.httpx, "AsyncClient", client_factory)

    client = TestClient(router_main.app)
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "hi"}],
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "OpenAI: hi"
