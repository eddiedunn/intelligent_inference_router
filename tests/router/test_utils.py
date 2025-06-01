import asyncio
import types

import pytest

import router.main as router_main
from router.schemas import ChatCompletionRequest, Message
from router.utils import stream_resp


class DummyResp:
    def __init__(self, chunks):
        self._chunks = chunks

    async def aiter_text(self):
        for chunk in self._chunks:
            yield chunk


def test_stream_resp_yields_chunks():
    resp = DummyResp(["a", "b", "c"])

    async def collect():
        return [chunk async for chunk in stream_resp(resp)]

    chunks = asyncio.run(collect())
    assert chunks == ["a", "b", "c"]


def test_make_cache_key_deterministic():
    req1 = ChatCompletionRequest(
        model="m1", messages=[Message(role="user", content="x")]
    )
    req2 = ChatCompletionRequest(
        model="m1", messages=[Message(role="user", content="x")]
    )
    req3 = ChatCompletionRequest(
        model="m1", messages=[Message(role="user", content="y")]
    )

    key1 = router_main.make_cache_key(req1)
    key2 = router_main.make_cache_key(req2)
    key3 = router_main.make_cache_key(req3)

    assert key1 == key2
    assert key1 != key3


def test_get_weight_provider(monkeypatch):
    class Dummy(router_main.WeightProvider):
        async def forward(self, payload, base_url):
            return {}

    dummy_module = types.SimpleNamespace(DummyProvider=Dummy)
    monkeypatch.setattr(router_main.providers, "dummy", dummy_module, raising=False)

    router_main.WEIGHT_PROVIDERS.clear()
    provider1 = router_main.get_weight_provider("dummy")
    provider2 = router_main.get_weight_provider("dummy")
    assert isinstance(provider1, Dummy)
    assert provider1 is provider2

    with pytest.raises(router_main.HTTPException):
        router_main.get_weight_provider("missing")
