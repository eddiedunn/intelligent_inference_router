import pytest
import asyncio
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

    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"id": "test", "object": "chat.completion", "choices": [{"message": {"content": "Hello!"}}]})
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)) as mock_post:
        client = client_cls()
        result = await client.chat_completions(payload, model)
        assert result.status_code == 200
        assert result.content["object"] == "chat.completion"
        mock_post.assert_awaited_once()
        call_args = mock_post.call_args
        args, kwargs = call_args
        assert args[0].endswith(endpoint)
        assert kwargs["headers"] == expected_headers
        assert kwargs["json"]["model"] == model

@pytest.mark.asyncio
async def test_anthropic_completions_not_implemented():
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
    # Simulate timeout
    async def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timeout")
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
    with patch("httpx.AsyncClient.post", new=raise_timeout):
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
    # Simulate upstream 500 error
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"error": "Upstream error"})
    mock_response.status_code = 500
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
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
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
    # Simulate malformed payload (e.g. missing messages)
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"error": "Malformed payload"})
    mock_response.status_code = 400
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
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        client = client_cls()
        result = await client.chat_completions({}, model)
        assert result.status_code == 400
        assert "error" in result.content
