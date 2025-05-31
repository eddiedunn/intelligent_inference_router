import asyncio
import sys
import types
import pytest

# Provide stub modules for optional dependencies
hub_stub = types.ModuleType("huggingface_hub")
hub_stub.snapshot_download = lambda *args, **kwargs: None  # type: ignore[attr-defined]
trans_stub = types.ModuleType("transformers")
trans_stub.pipeline = lambda *args, **kwargs: None  # type: ignore[attr-defined]
sys.modules.setdefault("huggingface_hub", hub_stub)
sys.modules.setdefault("transformers", trans_stub)

from router.providers.base import ApiProvider, WeightProvider  # noqa: E402
from router.schemas import ChatCompletionRequest, Message  # noqa: E402


def test_api_provider_not_implemented():
    provider = ApiProvider()
    payload = ChatCompletionRequest(
        model="m", messages=[Message(role="user", content="hi")]
    )
    with pytest.raises(NotImplementedError):
        asyncio.run(provider.forward(payload, base_url="x", api_key="k"))


def test_weight_provider_not_implemented():
    provider = WeightProvider()
    payload = ChatCompletionRequest(
        model="m", messages=[Message(role="user", content="hi")]
    )
    with pytest.raises(NotImplementedError):
        asyncio.run(provider.forward(payload, base_url="x"))
