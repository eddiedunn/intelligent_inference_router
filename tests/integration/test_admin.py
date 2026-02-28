"""Integration tests for /admin/api-keys CRUD."""

from __future__ import annotations


class TestAdminApiKeys:
    def test_create_key(self, client, auth_headers):
        resp = client.post(
            "/admin/api-keys",
            json={"description": "integration test key"},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "api_key" in data
        assert data["description"] == "integration test key"
        assert len(data["api_key"]) > 20  # secrets.token_urlsafe(32) → 43 chars

    def test_list_keys_includes_seeded_key(self, client, auth_headers):
        resp = client.get("/admin/api-keys", headers=auth_headers)

        assert resp.status_code == 200
        keys = resp.json()["data"]
        assert any(k["key"] == "test-key-123" for k in keys)

    def test_create_then_list(self, client, auth_headers):
        client.post("/admin/api-keys", json={"description": "new"}, headers=auth_headers)

        resp = client.get("/admin/api-keys", headers=auth_headers)
        keys = resp.json()["data"]
        assert len(keys) >= 2  # seeded key + new key

    def test_delete_key(self, client, auth_headers):
        # Create a key to delete
        create_resp = client.post(
            "/admin/api-keys",
            json={"description": "to-delete"},
            headers=auth_headers,
        )
        new_key = create_resp.json()["api_key"]

        # Delete by prefix
        resp = client.delete(f"/admin/api-keys/{new_key[:8]}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "revoked"

        # Verify it's revoked (soft-delete: active=0)
        list_resp = client.get("/admin/api-keys", headers=auth_headers)
        revoked = next(k for k in list_resp.json()["data"] if k["key"] == new_key)
        assert revoked["active"] == 0

    def test_delete_nonexistent_returns_404(self, client, auth_headers):
        resp = client.delete("/admin/api-keys/nonexistent-prefix", headers=auth_headers)
        assert resp.status_code == 404

    def test_no_auth_returns_401(self, client):
        resp = client.get("/admin/api-keys")
        assert resp.status_code == 401

        resp = client.post("/admin/api-keys", json={"description": "nope"})
        assert resp.status_code == 401
