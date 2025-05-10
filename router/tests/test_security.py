import pytest
from router.security import api_key_auth
from fastapi import Request
import starlette.datastructures
import asyncio

class DummyRequest:
    def __init__(self, key):
        self.headers = starlette.datastructures.Headers({"authorization": key})

import pytest
from router.security import api_key_auth
from router.apikey_db import add_api_key, revoke_api_key
import starlette.datastructures
import asyncio
import uuid

class DummyRequest:
    def __init__(self, key):
        self.headers = starlette.datastructures.Headers({"authorization": key})

@pytest.mark.asyncio
def test_api_key_auth_db_valid(tmp_path, monkeypatch):
    test_key = str(uuid.uuid4())
    add_api_key(test_key, created_ip="127.0.0.1", description="test", priority=1)
    req = DummyRequest(f"Bearer {test_key}")
    result = asyncio.run(api_key_auth(req)) if asyncio.iscoroutinefunction(api_key_auth) else api_key_auth(req)
    assert result is True or result is None

@pytest.mark.asyncio
def test_api_key_auth_db_invalid(tmp_path, monkeypatch):
    req = DummyRequest("Bearer invalid-key")
    with pytest.raises(Exception):
        if asyncio.iscoroutinefunction(api_key_auth):
            asyncio.run(api_key_auth(req))
        else:
            api_key_auth(req)

@pytest.mark.asyncio
def test_api_key_auth_db_revoked(tmp_path, monkeypatch):
    test_key = str(uuid.uuid4())
    add_api_key(test_key, created_ip="127.0.0.1", description="test", priority=1)
    revoke_api_key(test_key)
    req = DummyRequest(f"Bearer {test_key}")
    with pytest.raises(Exception):
        if asyncio.iscoroutinefunction(api_key_auth):
            asyncio.run(api_key_auth(req))
        else:
            api_key_auth(req)
