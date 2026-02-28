"""Integration test fixtures — respx for Bifrost, patched settings."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import respx
from fastapi.testclient import TestClient

from iir.config import Settings


@pytest.fixture(autouse=True)
def _patch_settings(settings):
    """Patch get_settings() in modules that import it directly.

    The app factory uses settings_override, but api_key_auth and admin routes
    call get_settings() which returns the lru_cache'd singleton with production
    defaults.  Patch both import sites so they use the test Settings.
    """
    test_settings = Settings(**settings)
    with (
        patch("iir.auth.security.get_settings", return_value=test_settings),
        patch("iir.api.routes_admin.get_settings", return_value=test_settings),
    ):
        yield


@pytest.fixture
def bifrost_mock():
    """Mock all httpx requests to the Bifrost URL via respx."""
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def client(app, bifrost_mock):
    """TestClient with Bifrost mocked.

    Ordering matters: bifrost_mock activates respx *before* TestClient enters
    the ASGI lifespan (which creates the httpx.AsyncClient inside BifrostClient).
    """
    with TestClient(app) as c:
        yield c
