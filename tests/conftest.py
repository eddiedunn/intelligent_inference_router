"""Test fixtures — clean, no monkey-patching."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from iir.app import create_app
from iir.auth.apikey_db import add_api_key, init_db


@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test_keys.sqlite3")
    init_db(db_path)
    add_api_key(db_path, "test-key-123", "127.0.0.1", "test key")
    return db_path


@pytest.fixture
def settings(tmp_db):
    return {
        "auth_db_path": tmp_db,
        "redis_url": "redis://localhost:6379/0",
        "redis_fallback_to_memory": True,
        "bifrost_url": "http://localhost:8080",
        "classifier_strategy": "rules_only",
        "routing_config_path": "config/models.yaml",
        "log_level": "WARNING",
    }


@pytest.fixture
def app(settings):
    return create_app(settings_override=settings)


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-key-123"}
