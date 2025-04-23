import pytest
import asyncio
from router.cache import make_cache_key

@pytest.mark.asyncio
async def test_make_cache_key():
    key = make_cache_key("prompt", "ctx", "model")
    assert isinstance(key, str)
    assert len(key) == 64  # sha256
