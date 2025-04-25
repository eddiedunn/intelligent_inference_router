import pytest
from router.security import api_key_auth
from fastapi import Request
import starlette.datastructures
import asyncio

class DummyRequest:
    def __init__(self, key):
        self.headers = starlette.datastructures.Headers({"authorization": key})

@pytest.mark.asyncio
def test_api_key_auth_valid(monkeypatch):
    req = DummyRequest("Bearer test-key")
    monkeypatch.setenv("IIR_API_KEY", "test-key")
    result = asyncio.run(api_key_auth(req)) if asyncio.iscoroutinefunction(api_key_auth) else api_key_auth(req)
    assert result is True or result is None

@pytest.mark.asyncio
def test_api_key_auth_invalid(monkeypatch):
    req = DummyRequest("Bearer wrong-key")
    monkeypatch.setenv("IIR_API_KEY", "test-key")
    with pytest.raises(Exception):
        if asyncio.iscoroutinefunction(api_key_auth):
            asyncio.run(api_key_auth(req))
        else:
            api_key_auth(req)
