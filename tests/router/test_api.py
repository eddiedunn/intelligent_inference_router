from fastapi.testclient import TestClient

from router.main import app


def test_chat_completions_dummy_response() -> None:
    client = TestClient(app)
    payload = {
        "model": "dummy",
        "messages": [{"role": "user", "content": "hi"}],
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["choices"][0]["message"]["content"] == "Hello world"
