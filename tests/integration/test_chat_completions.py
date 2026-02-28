"""Integration tests for POST /v1/chat/completions.

Full request flow: auth → classify → route → proxy to Bifrost → response
with routing metadata headers.
"""

from __future__ import annotations

import json

import httpx
import pytest

# ---------------------------------------------------------------------------
# Fixtures: standard Bifrost response
# ---------------------------------------------------------------------------

BIFROST_CHAT_RESPONSE = {
    "id": "chatcmpl-test123",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "test-model",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Hello! How can I help you?"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
}

BIFROST_URL = "http://localhost:8080/v1/chat/completions"


def _msg(content: str) -> dict:
    return {"messages": [{"role": "user", "content": content}]}


# ---------------------------------------------------------------------------
# Classification → Model Routing
# ---------------------------------------------------------------------------


class TestRoutingClassification:
    """Prompts are classified by the rules engine and routed to the expected model."""

    def test_simple_greeting_routes_to_local(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post("/v1/chat/completions", json=_msg("Hello!"), headers=auth_headers)

        assert resp.status_code == 200
        assert resp.headers["X-Route-Model"] == "ollama/llama3.2"
        assert resp.headers["X-Route-Provider"] == "ollama"
        assert resp.headers["X-Classification"] == "simple_chat"

    def test_coding_prompt_routes_to_claude(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Write a Python function to sort a list"),
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.headers["X-Route-Model"] == "anthropic/claude-sonnet-4-20250514"
        assert resp.headers["X-Classification"] == "coding"

    def test_math_prompt_routes_to_gpt4o(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Calculate the integral of x^2 from 0 to 5"),
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.headers["X-Route-Model"] == "openai/gpt-4o"
        assert resp.headers["X-Classification"] == "math"

    def test_translation_routes_to_gpt4o_mini(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Translate hello world to Spanish"),
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.headers["X-Route-Model"] == "openai/gpt-4o-mini"
        assert resp.headers["X-Classification"] == "translation"

    def test_summarization_routes_to_local(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Summarize this article for me please"),
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.headers["X-Route-Model"] == "ollama/llama3.2"
        assert resp.headers["X-Classification"] == "summarization"

    def test_creative_writing_routes_to_claude(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Write a story about a dragon who learns to code"),
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.headers["X-Route-Model"] == "anthropic/claude-sonnet-4-20250514"
        assert resp.headers["X-Classification"] == "creative_writing"

    def test_tools_trigger_function_calling(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "What's the weather in Paris?"}],
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
                        },
                    }
                ],
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.headers["X-Route-Model"] == "openai/gpt-4o"
        assert resp.headers["X-Classification"] == "function_calling"

    def test_unclassified_defaults_to_general_chat(self, client, auth_headers, bifrost_mock):
        """A prompt matching no rule falls back to general_chat → local model."""
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Tell me about the history of Rome"),
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.headers["X-Route-Model"] == "ollama/llama3.2"
        assert resp.headers["X-Classification"] == "general_chat"


# ---------------------------------------------------------------------------
# Routing Strategies & Pass-through
# ---------------------------------------------------------------------------


class TestRoutingStrategies:
    """X-Routing-Strategy and explicit model affect routing decisions."""

    def test_quality_first_picks_excellent_tier(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Write a Python function to sort a list"),
            headers={**auth_headers, "X-Routing-Strategy": "quality-first"},
        )

        assert resp.status_code == 200
        # quality-first for coding → excellent-tier model
        assert resp.headers["X-Route-Model"] in ("openai/gpt-4o", "anthropic/claude-sonnet-4-20250514")

    def test_local_only_picks_free_model(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Hello!"),
            headers={**auth_headers, "X-Routing-Strategy": "local-only"},
        )

        assert resp.status_code == 200
        assert resp.headers["X-Route-Model"] == "ollama/llama3.2"

    def test_pass_through_with_explicit_model(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json={
                "model": "openai/gpt-4o",
                "messages": [{"role": "user", "content": "Hello!"}],
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        assert resp.headers["X-Route-Model"] == "openai/gpt-4o"
        assert resp.headers["X-Classification"] == "explicit"
        assert resp.headers["X-Route-Reason"] == "User-specified model"


# ---------------------------------------------------------------------------
# Response Metadata & Payload Forwarding
# ---------------------------------------------------------------------------


class TestResponseMetadata:
    """Routing metadata headers and payload forwarding to Bifrost."""

    def test_routing_headers_present(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post("/v1/chat/completions", json=_msg("Hello!"), headers=auth_headers)

        for header in ("X-Route-Model", "X-Route-Provider", "X-Route-Reason", "X-Classification"):
            assert header in resp.headers, f"Missing header: {header}"

    def test_request_id_generated(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post("/v1/chat/completions", json=_msg("Hello!"), headers=auth_headers)

        assert "X-Request-ID" in resp.headers
        assert resp.headers["X-Request-ID"].startswith("req_")

    def test_request_id_echoed(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Hello!"),
            headers={**auth_headers, "X-Request-ID": "custom-req-42"},
        )

        assert resp.headers["X-Request-ID"] == "custom-req-42"

    def test_cost_header_for_paid_model(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Write a Python function to sort a list"),
            headers=auth_headers,
        )

        assert "X-Estimated-Cost-Per-1M" in resp.headers
        assert float(resp.headers["X-Estimated-Cost-Per-1M"]) == pytest.approx(3.0)

    def test_no_cost_header_for_free_model(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post("/v1/chat/completions", json=_msg("Hello!"), headers=auth_headers)

        assert "X-Estimated-Cost-Per-1M" not in resp.headers

    def test_bifrost_receives_routed_model_and_params(self, client, auth_headers, bifrost_mock):
        """The payload sent to Bifrost has the routed model and original params."""
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Hello!"}], "temperature": 0.7},
            headers=auth_headers,
        )

        assert len(bifrost_mock.calls) == 1
        sent = json.loads(bifrost_mock.calls.last.request.content)
        assert sent["model"] == "ollama/llama3.2"
        assert sent["temperature"] == 0.7
        assert sent["messages"][0]["content"] == "Hello!"

    def test_response_body_passthrough(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).respond(200, json=BIFROST_CHAT_RESPONSE)

        resp = client.post("/v1/chat/completions", json=_msg("Hello!"), headers=auth_headers)

        data = resp.json()
        assert data["id"] == "chatcmpl-test123"
        assert data["choices"][0]["message"]["content"] == "Hello! How can I help you?"
        assert data["usage"]["total_tokens"] == 18


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_no_auth_returns_401(self, client, bifrost_mock):
        resp = client.post("/v1/chat/completions", json=_msg("Hello!"))
        assert resp.status_code == 401

    def test_invalid_key_returns_403(self, client, bifrost_mock):
        resp = client.post(
            "/v1/chat/completions",
            json=_msg("Hello!"),
            headers={"Authorization": "Bearer invalid-key-999"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Bifrost Error Handling
# ---------------------------------------------------------------------------


class TestBifrostErrors:
    def test_bifrost_4xx_passthrough(self, client, auth_headers, bifrost_mock):
        error_body = {"error": {"message": "Model not found", "type": "invalid_request_error"}}
        bifrost_mock.post(BIFROST_URL).respond(404, json=error_body)

        resp = client.post("/v1/chat/completions", json=_msg("Hello!"), headers=auth_headers)

        assert resp.status_code == 404
        assert resp.json()["error"]["message"] == "Model not found"

    def test_bifrost_5xx_passthrough(self, client, auth_headers, bifrost_mock):
        error_body = {"error": {"message": "Internal server error", "type": "server_error"}}
        bifrost_mock.post(BIFROST_URL).respond(500, json=error_body)

        resp = client.post("/v1/chat/completions", json=_msg("Hello!"), headers=auth_headers)

        assert resp.status_code == 500

    def test_bifrost_connection_error_returns_502(self, client, auth_headers, bifrost_mock):
        bifrost_mock.post(BIFROST_URL).mock(side_effect=httpx.ConnectError("Connection refused"))

        resp = client.post("/v1/chat/completions", json=_msg("Hello!"), headers=auth_headers)

        assert resp.status_code == 502
        assert "Gateway error" in resp.json()["error"]["message"]
