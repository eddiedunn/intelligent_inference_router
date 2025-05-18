import pytest
import asyncio
from fastapi import Request
from router.main import create_app, rate_limiter_dep
from prometheus_client import CollectorRegistry
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

# Remove per-file key generation, use test_api_key fixture from conftest.py

# The patch_provider_clients fixture is removed. All provider mocking is now handled at the app module scope via MOCK_PROVIDERS.

import router.provider_clients
import router.provider_router
import router.model_registry
import router.main
import router.validation_utils
# Monkeypatch validate_model_and_messages to print debug info
orig_validate = router.validation_utils.validate_model_and_messages
def debug_validate_model_and_messages(payload, list_models_func=None, require_messages=True, token_limit=1000):
    print("[DEBUG][TEST] Payload to validate:", payload)
    if list_models_func:
        models = list_models_func()['data']
        print("[DEBUG][TEST] Models from list_models_func:", [m['id'] for m in models])
    else:
        print("[DEBUG][TEST] No list_models_func provided")
    return orig_validate(payload, list_models_func, require_messages, token_limit)
router.validation_utils.validate_model_and_messages = debug_validate_model_and_messages


# Patch services config to include all test models
router.main.load_config = lambda: {
    "services": {
        "openai/gpt-3.5-turbo": "http://dummy",
        "openai/gpt-4.1": "http://dummy",
        "anthropic/claude-3.7-sonnet": "http://dummy",
        "grok/grok-1": "http://dummy",
        "openrouter/openrouter-1": "http://dummy",
        "openllama/openllama-1": "http://dummy",
    },
    "model_prefix_map": {
        "openai/": "openai",
        "anthropic/": "anthropic",
        "grok/": "grok",
        "openrouter/": "openrouter",
        "openllama/": "openllama",
    }
}

# Monkeypatch ProviderRouter.select_provider to print the provider_name being checked
original_select_provider = router.provider_router.ProviderRouter.select_provider
async def debug_select_provider(self, payload, user_id=None, context=None):
    model = payload.get("model", "")
    # Prefix-based routing
    for prefix, provider_name in self.routing.get("model_prefix_map", {}).items():
        if model.startswith(prefix):
            break
    else:
        provider_name = self.routing.get("default", "openai")
    print(f"[DEBUG][TEST] Provider name being checked: '{provider_name}' (model: '{model}')")
    if provider_name not in router.provider_clients.PROVIDER_CLIENTS:
        print(f"[DEBUG][TEST] '{provider_name}' NOT FOUND in PROVIDER_CLIENTS: {list(router.provider_clients.PROVIDER_CLIENTS.keys())}")
        raise Exception(f"No provider client found for: {provider_name}")
    provider_client = router.provider_clients.PROVIDER_CLIENTS[provider_name]
    return provider_name, provider_client, model
router.provider_router.ProviderRouter.select_provider = debug_select_provider

from fastapi.responses import JSONResponse

class DummyProvider:
    async def classify_prompt(self, *args, **kwargs):
        return {"classification": "safe"}
    async def chat(self, model, *args, **kwargs):
        # Simulate 501 for local or unknown models
        valid_models = [
            "openai/gpt-3.5-turbo",
            "anthropic/claude-3.7-sonnet",
            "grok/grok-1",
            "openrouter/openrouter-1",
            "openllama/openllama-1",
        ]
        if model not in valid_models:
            return JSONResponse(
                {"error": {"message": "Model name must be in <provider>/<model> format."}},
                status_code=501
            )
        return {
            "id": "dummy-id",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model,
            "choices": [
                {"message": {"content": "Hello!"}, "finish_reason": "stop", "index": 0}
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        }

router.provider_clients.PROVIDER_CLIENTS = {
    'openai': DummyProvider(),
    'openai/': DummyProvider(),
    'anthropic': DummyProvider(),
    'anthropic/': DummyProvider(),
    'grok': DummyProvider(),
    'grok/': DummyProvider(),
    'openrouter': DummyProvider(),
    'openrouter/': DummyProvider(),
    'openllama': DummyProvider(),
    'openllama/': DummyProvider(),
}

# Monkeypatch model_registry.list_models to always return all test models
router.model_registry.list_models = lambda: {
    "data": [
        {"id": "openai/gpt-3.5-turbo", "endpoint_url": None},
        {"id": "openai/gpt-4.1", "endpoint_url": None},
        {"id": "anthropic/claude-3.7-sonnet", "endpoint_url": None},
        {"id": "grok/grok-1", "endpoint_url": None},
        {"id": "openrouter/openrouter-1", "endpoint_url": None},
        {"id": "openllama/openllama-1", "endpoint_url": None},
    ]
}

@pytest.fixture
def app():
    a = create_app(metrics_registry=CollectorRegistry())
    # Patch routing map for all required providers
    if hasattr(a.state, 'provider_router'):
        a.state.provider_router.routing['model_prefix_map'] = {
            'openai/': 'openai',
            'anthropic/': 'anthropic',
            'grok/': 'grok',
            'openrouter/': 'openrouter',
            'openllama/': 'openllama',
        }
        # Define a minimal DummyProvider class
        class DummyProvider:
            async def classify_prompt(self, *args, **kwargs):
                return {"classification": "safe"}
            async def chat(self, *args, **kwargs):
                return {"choices": [{"message": {"content": "dummy response"}}]}
        a.state.provider_router.providers = {
            'openai': DummyProvider(),
            'anthropic': DummyProvider(),
            'grok': DummyProvider(),
            'openrouter': DummyProvider(),
            'openllama': DummyProvider(),
        }
        # Patch services config if present
        if hasattr(a.state.provider_router, 'config'):
            a.state.provider_router.config['services'] = {
                'openai/gpt-3.5-turbo': 'http://dummy',
                'anthropic/claude-3.7-sonnet': 'http://dummy',
                'grok/grok-1': 'http://dummy',
                'openrouter/openrouter-1': 'http://dummy',
                'openllama/openllama-1': 'http://dummy',
            }
    return a

@pytest.mark.parametrize("model,expected_provider", [
    ("openai/gpt-3.5-turbo", "openai"),
    ("anthropic/claude-3.7-sonnet", "anthropic"),
    ("grok/grok-1", "grok"),
    ("openrouter/openrouter-1", "openrouter"),
    ("openllama/openllama-1", "openllama"),
])
@pytest.mark.asyncio
async def test_routing_remote_models(async_client, model, expected_provider, test_api_key):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hello"}]
    }
    headers = {"Authorization": f"Bearer {test_api_key}"}
    resp = await async_client.post("/v1/chat/completions", json=payload, headers=headers)
    print("[DEBUG][TEST] Payload sent:", payload)
    print("[DEBUG][TEST] Status code:", resp.status_code)
    body = await resp.json()
    print("[DEBUG][TEST] Response body:", body)
    assert resp.status_code == 200
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == "Hello!"

# Test local path (gpt-4.1)
@pytest.mark.asyncio
async def test_routing_local_model(test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    async def no_op_rate_limiter(request: Request):
        pass
    app.dependency_overrides[rate_limiter_dep] = no_op_rate_limiter
    payload = {
        "model": "gpt-4.1",
        "messages": [{"role": "user", "content": "hi"}]
    }
    headers = {"Authorization": f"Bearer {test_api_key}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers=headers)
    assert resp.status_code == 501
    body = await resp.json()
    assert body["error"]["message"] == "Model name must be in <provider>/<model> format."

# Test error on unknown model prefix
@pytest.mark.asyncio
async def test_routing_unknown_model(async_client, test_api_key):
    payload = {
        "model": "foo-unknown",
        "messages": [{"role": "user", "content": "hi"}]
    }
    headers = {"Authorization": f"Bearer {test_api_key}"}
    resp = await async_client.post("/v1/chat/completions", json=payload, headers=headers)
    assert resp.status_code == 501
    body = await resp.json()
    assert body["error"]["message"] == "Model name must be in <provider>/<model> format."
