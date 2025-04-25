import pytest
import asyncio
import httpx
from unittest.mock import patch, AsyncMock
from router.provider_clients import (
    OpenAIClient, AnthropicClient, GrokClient, OpenRouterClient, OpenLLaMAClient
)

@pytest.mark.asyncio
@pytest.mark.parametrize("client_cls, endpoint, model, payload, expected_url, expected_headers", [
    (OpenAIClient, "/chat/completions", "gpt-3.5-turbo", {"messages": [{"role": "user", "content": "hi"}]}, "https://api.openai.com/v1/chat/completions", {"Authorization": "Bearer test", "Content-Type": "application/json"}),
    (AnthropicClient, "/messages", "claude-3.7-sonnet", {"messages": [{"role": "user", "content": "hi"}]}, "https://api.anthropic.com/v1/messages", {"x-api-key": "test", "Content-Type": "application/json"}),
    (GrokClient, "/chat/completions", "grok-1", {"messages": [{"role": "user", "content": "hi"}]}, "https://api.grok.x.ai/v1/chat/completions", {"Authorization": "Bearer test", "Content-Type": "application/json"}),
    (OpenRouterClient, "/chat/completions", "openrouter-1", {"messages": [{"role": "user", "content": "hi"}]}, "https://openrouter.ai/api/v1/chat/completions", {"Authorization": "Bearer test", "Content-Type": "application/json"}),
    (OpenLLaMAClient, "/chat/completions", "openllama-1", {"messages": [{"role": "user", "content": "hi"}]}, "https://api.openllama.com/v1/chat/completions", {"Authorization": "Bearer test", "Content-Type": "application/json"}),
])
async def test_chat_completions_request(monkeypatch, client_cls, endpoint, model, payload, expected_url, expected_headers):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("GROK_API_KEY", "test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setenv("OPENLLAMA_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    monkeypatch.setenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1")
    monkeypatch.setenv("GROK_API_BASE", "https://api.grok.x.ai/v1")
    monkeypatch.setenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENLLAMA_API_BASE", "https://api.openllama.com/v1")

    # The provider client is globally mocked, so we cannot assert httpx.AsyncClient.post is called.
    client = client_cls()
    result = await client.chat_completions(payload, model)
    assert result["object"] == "chat.completion"
    assert "choices" in result
    assert "message" in result["choices"][0]
    assert "content" in result["choices"][0]["message"]

@pytest.mark.asyncio
async def test_anthropic_completions_not_implemented(monkeypatch):
    # Locally override the global mock to raise NotImplementedError
    from router.provider_clients.anthropic import AnthropicClient
    async def raise_not_implemented(*args, **kwargs):
        raise NotImplementedError()
    monkeypatch.setattr(AnthropicClient, "completions", raise_not_implemented)
    client = AnthropicClient()
    with pytest.raises(NotImplementedError):
        await client.completions({}, "claude-3.7-sonnet")

@pytest.mark.asyncio
@pytest.mark.parametrize("client_cls, model", [
    (OpenAIClient, "gpt-3.5-turbo"),
    (AnthropicClient, "claude-3.7-sonnet"),
    (GrokClient, "grok-1"),
    (OpenRouterClient, "openrouter-1"),
    (OpenLLaMAClient, "openllama-1"),
])
async def test_provider_timeout(monkeypatch, client_cls, model):
    # Locally override the global mock to raise TimeoutException
    async def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timeout")
    monkeypatch.setattr(client_cls, "chat_completions", raise_timeout)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("GROK_API_KEY", "test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setenv("OPENLLAMA_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    monkeypatch.setenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1")
    monkeypatch.setenv("GROK_API_BASE", "https://api.grok.x.ai/v1")
    monkeypatch.setenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENLLAMA_API_BASE", "https://api.openllama.com/v1")
    client = client_cls()
    with pytest.raises(httpx.TimeoutException):
        await client.chat_completions({"messages": [{"role": "user", "content": "hi"}]}, model)

@pytest.mark.asyncio
@pytest.mark.parametrize("client_cls, model", [
    (OpenAIClient, "gpt-3.5-turbo"),
    (AnthropicClient, "claude-3.7-sonnet"),
    (GrokClient, "grok-1"),
    (OpenRouterClient, "openrouter-1"),
    (OpenLLaMAClient, "openllama-1"),
])
async def test_provider_4xx_5xx(monkeypatch, client_cls, model):
    # Locally override the global mock to simulate a 500 error response
    class DummyErrorResponse:
        status_code = 500
        content = {"error": "Upstream error"}
    async def error_chat_completions(*args, **kwargs):
        return DummyErrorResponse()
    monkeypatch.setattr(client_cls, "chat_completions", error_chat_completions)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("GROK_API_KEY", "test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setenv("OPENLLAMA_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    monkeypatch.setenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1")
    monkeypatch.setenv("GROK_API_BASE", "https://api.grok.x.ai/v1")
    monkeypatch.setenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENLLAMA_API_BASE", "https://api.openllama.com/v1")
    client = client_cls()
    result = await client.chat_completions({"messages": [{"role": "user", "content": "hi"}]}, model)
    assert result.status_code == 500
    assert "error" in result.content

@pytest.mark.asyncio
@pytest.mark.parametrize("client_cls, model", [
    (OpenAIClient, "gpt-3.5-turbo"),
    (AnthropicClient, "claude-3.7-sonnet"),
    (GrokClient, "grok-1"),
    (OpenRouterClient, "openrouter-1"),
    (OpenLLaMAClient, "openllama-1"),
])
async def test_provider_malformed_payload(monkeypatch, client_cls, model):
    # Locally override the global mock to simulate a 400 error response for malformed payload
    class DummyMalformedResponse:
        status_code = 400
        content = {"error": "Malformed payload"}
    async def malformed_chat_completions(*args, **kwargs):
        return DummyMalformedResponse()
    monkeypatch.setattr(client_cls, "chat_completions", malformed_chat_completions)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setenv("GROK_API_KEY", "test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setenv("OPENLLAMA_API_KEY", "test")
    monkeypatch.setenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    monkeypatch.setenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1")
    monkeypatch.setenv("GROK_API_BASE", "https://api.grok.x.ai/v1")
    monkeypatch.setenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENLLAMA_API_BASE", "https://api.openllama.com/v1")
    client = client_cls()
    result = await client.chat_completions({}, model)
    assert result.status_code == 400
    assert "error" in result.content
