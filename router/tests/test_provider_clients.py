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
    mock_response.json.return_value = {"id": "test", "object": "chat.completion", "choices": [{"message": {"content": "Hello!"}}]}
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)) as mock_post:
        client = client_cls()
        result = await client.chat_completions(payload, model)
        assert result.status_code == 200
        assert result.content["object"] == "chat.completion"
        mock_post.assert_awaited_once()
        call_args = mock_post.call_args[1]
        assert call_args["url"].endswith(endpoint)
        assert call_args["headers"] == expected_headers
        assert call_args["json"]["model"] == model

@pytest.mark.asyncio
async def test_anthropic_completions_not_implemented():
    client = AnthropicClient()
    with pytest.raises(NotImplementedError):
        await client.completions({}, "claude-3.7-sonnet")
