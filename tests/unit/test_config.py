"""Tests for config loading."""

from iir.config import Settings


def test_defaults():
    s = Settings()
    assert s.bifrost_url == "http://localhost:8080"
    assert s.classifier_strategy == "hybrid"
    assert s.routing_default_strategy == "cost-optimized"
    assert s.max_body_size == 1_048_576


def test_override():
    s = Settings(bifrost_url="http://custom:9090", log_level="DEBUG")
    assert s.bifrost_url == "http://custom:9090"
    assert s.log_level == "DEBUG"
