"""Integration tests for GET /v1/models."""

from __future__ import annotations


EXPECTED_MODELS = {
    "ollama/llama3.2",
    "groq/llama-3.3-70b-versatile",
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "anthropic/claude-sonnet-4-20250514",
}


class TestListModels:
    def test_returns_all_models(self, client, auth_headers):
        resp = client.get("/v1/models", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["object"] == "list"
        assert len(data["data"]) == len(EXPECTED_MODELS)

    def test_contains_expected_model_ids(self, client, auth_headers):
        resp = client.get("/v1/models", headers=auth_headers)

        model_ids = {m["id"] for m in resp.json()["data"]}
        assert model_ids == EXPECTED_MODELS

    def test_model_entry_structure(self, client, auth_headers):
        resp = client.get("/v1/models", headers=auth_headers)

        model = resp.json()["data"][0]
        assert model["object"] == "model"
        for field in ("id", "provider", "capabilities", "quality_tier", "supports_vision", "supports_tools"):
            assert field in model, f"Missing field: {field}"

    def test_no_auth_returns_401(self, client):
        resp = client.get("/v1/models")
        assert resp.status_code == 401
