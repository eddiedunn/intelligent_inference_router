"""Tests for secret scrubber."""

from iir.middleware.secret_scrubber import find_secrets, scrub_data, scrub_text, shannon_entropy


def test_shannon_entropy():
    assert shannon_entropy("") == 0.0
    assert shannon_entropy("aaaa") == 0.0
    assert shannon_entropy("abcd") > 1.0


def test_find_env_secrets():
    secrets = {"sk-abc123456789012345"}
    text = "My key is sk-abc123456789012345 and more"
    found = find_secrets(text, secrets)
    assert "sk-abc123456789012345" in found


def test_scrub_text():
    secrets = {"SUPERSECRET12345678"}
    text = "token=SUPERSECRET12345678"
    result = scrub_text(text, secrets)
    assert "SUPERSECRET12345678" not in result
    assert "REDACTED" in result


def test_scrub_data_recursive():
    secrets = {"MYSECRETVALUE12345"}
    data = {"key": "MYSECRETVALUE12345", "nested": {"val": "safe"}}
    result = scrub_data(data, secrets)
    assert "REDACTED" in result["key"]
    assert result["nested"]["val"] == "safe"


def test_find_jwt():
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    found = find_secrets(f"Bearer {jwt}", set())
    assert any("eyJ" in f for f in found)
