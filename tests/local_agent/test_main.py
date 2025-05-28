import pytest
from fastapi.testclient import TestClient

from local_agent.main import app


def test_infer_echo():
    client = TestClient(app)
    payload = {
        "model": "local_test",
        "messages": [{"role": "user", "content": "hello"}],
    }
    resp = client.post("/infer", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Echo: hello"
