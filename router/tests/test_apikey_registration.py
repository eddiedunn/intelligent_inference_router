import sys
import os
import pytest
from fastapi.testclient import TestClient

# Ensure 'router' is importable when running from project root
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(test_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import sys
import os
from unittest.mock import patch

# Ensure 'router' is importable when running from project root
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(test_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Patch transformers.pipeline and prometheus_client.REGISTRY before importing router.main
from prometheus_client import CollectorRegistry
import prometheus_client


# Allow any IP for testing (monkeypatch is_allowed_ip)
def always_allow_ip(ip):
    return True


@pytest.fixture(autouse=True)
def cleanup_keys():
    # Optionally, clean up keys before/after tests if needed
    yield
    # Could implement cleanup logic here if desired


def test_apikey_registration_and_auth(monkeypatch):
    """
    Test the /api/v1/apikeys registration endpoint and verify the returned key can access protected endpoints.
    """
    from unittest.mock import patch
    from prometheus_client import CollectorRegistry
    import prometheus_client
    with patch("transformers.pipeline") as mock_pipe, \
         patch.object(prometheus_client, 'REGISTRY', CollectorRegistry()) as test_registry:
        mock_pipe.return_value = lambda *a, **kw: None
        # Patch is_allowed_ip to always allow in this test context, BEFORE importing create_app
        monkeypatch.setattr("router.main.is_allowed_ip", always_allow_ip)
        from router.main import create_app
        from router.apikey_db import get_api_key
        app = create_app(metrics_registry=test_registry)
        print("[DEBUG] app type:", type(app), "app value:", app)

                # Register a new API key
        payload = {"description": "test key", "priority": 42}
        with TestClient(app) as client:
            response = client.post("/api/v1/apikeys", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert "api_key" in data
            assert data["priority"] == 42
            api_key = data["api_key"]

            # Confirm key is in DB and has correct priority
            db_row = get_api_key(api_key)
            assert db_row is not None
            assert db_row[6] == 42  # priority column
            assert db_row[7] == 1   # active column

            # Use the API key to access a protected endpoint (/infer)
            infer_payload = {"model": "openai/gpt-3.5-turbo", "input": {"prompt": "hello"}}
            # Patch httpx.post to avoid real upstream call
            def mock_post(*args, **kwargs):
                class MockResponse:
                    def json(self):
                        return {"result": "ok", "output": "test-output"}
                    @property
                    def status_code(self):
                        return 200
                return MockResponse()
            monkeypatch.setattr("httpx.post", mock_post)

            # Patch routing so 'openai/' prefix is routed to openai
            client.app.state.provider_router.routing['model_prefix_map'] = {'openai/': 'openai', 'openai': 'openai'}
            client.app.state.provider_router.classify_prompt = lambda *a, **k: ("general", 1.0)
            # Patch load_config so services includes openai/gpt-3.5-turbo
            monkeypatch.setattr("router.main.load_config", lambda: {"services": {"openai/gpt-3.5-turbo": "http://dummy"}})
            # Patch OpenAI provider client to always return dummy response
            from router.provider_clients import PROVIDER_CLIENTS
            class DummyOpenAIClient:
                async def infer(self, payload, model, **kwargs):
                    class DummyResp:
                        status_code = 200
                        def json(self):
                            return {"result": "ok", "output": "test-output"}
                        @property
                        def content(self):
                            return {"result": "ok", "output": "test-output"}
                    return DummyResp()
                async def chat_completions(self, payload, model, **kwargs):
                    if not model.startswith("openai/"):
                        class DummyErrorResp:
                            status_code = 400
                            def json(self):
                                return {"error": {"message": "invalid model ID", "type": "invalid_request_error", "param": None, "code": None}}
                            @property
                            def content(self):
                                return {"error": {"message": "invalid model ID", "type": "invalid_request_error", "param": None, "code": None}}
                        return DummyErrorResp()
                    class DummyResp:
                        status_code = 200
                        def json(self):
                            return {"result": "ok", "model": model}
                        @property
                        def content(self):
                            return {"result": "ok", "model": model}
                    return DummyResp()
            PROVIDER_CLIENTS['openai'] = DummyOpenAIClient()
            response = client.post("/infer", json=infer_payload, headers={"Authorization": "Bearer changeme"})
            assert response.status_code == 200
            assert response.json()["result"] == "ok"

            # Try with a bad key
            bad_response = client.post("/infer", json=infer_payload, headers={"Authorization": "Bearer badkey"})
            assert bad_response.status_code == 403
