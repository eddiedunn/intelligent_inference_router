"""Tests for API key auth."""

import pytest

from iir.auth.apikey_db import add_api_key, get_api_key, init_db, list_api_keys, revoke_api_key


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "keys.sqlite3")
    init_db(path)
    return path


def test_add_and_get(db):
    add_api_key(db, "abc123", "127.0.0.1", "test key")
    row = get_api_key(db, "abc123")
    assert row is not None
    assert row["key"] == "abc123"


def test_get_missing(db):
    assert get_api_key(db, "nonexistent") is None


def test_revoke(db):
    add_api_key(db, "abc123", "127.0.0.1")
    revoke_api_key(db, "abc123")
    assert get_api_key(db, "abc123") is None


def test_list(db):
    add_api_key(db, "key1", "127.0.0.1", "first")
    add_api_key(db, "key2", "127.0.0.1", "second")
    keys = list_api_keys(db)
    assert len(keys) == 2


def test_duplicate_insert_ignored(db):
    add_api_key(db, "abc123", "127.0.0.1")
    add_api_key(db, "abc123", "192.168.1.1")  # should not raise
    keys = list_api_keys(db)
    assert len(keys) == 1
