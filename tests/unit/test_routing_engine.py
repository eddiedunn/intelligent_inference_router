"""Tests for the routing engine."""

import pytest

from iir.cache.memory_cache import MemoryCache
from iir.classifier.base import HybridClassifier
from iir.classifier.categories import TaskCategory
from iir.classifier.rules import RulesClassifier
from iir.observability.metrics import Metrics
from iir.routing.engine import RoutingEngine
from iir.routing.model_registry import ModelRegistry
from prometheus_client import CollectorRegistry


@pytest.fixture
def registry():
    r = ModelRegistry()
    r.load_from_yaml("config/models.yaml")
    return r


@pytest.fixture
def engine(registry):
    reg = CollectorRegistry()
    metrics = Metrics(registry=reg)
    classifier = HybridClassifier(RulesClassifier(), strategy="rules_only")
    cache = MemoryCache()
    return RoutingEngine(
        registry=registry,
        classifier=classifier,
        cache=cache,
        metrics=metrics,
        default_strategy="cost-optimized",
    )


@pytest.mark.asyncio
async def test_explicit_model(engine):
    decision = await engine.route(
        messages=[{"role": "user", "content": "hello"}],
        explicit_model="openai/gpt-4o",
    )
    assert decision.model == "openai/gpt-4o"
    assert decision.reason == "User-specified model"


@pytest.mark.asyncio
async def test_coding_routes_to_claude(engine):
    decision = await engine.route(
        messages=[{"role": "user", "content": "Write a Python function to merge sort a list"}],
    )
    assert decision.category == "coding"
    assert "anthropic" in decision.model


@pytest.mark.asyncio
async def test_greeting_routes_to_local(engine):
    decision = await engine.route(
        messages=[{"role": "user", "content": "Hello!"}],
    )
    assert decision.category == "simple_chat"
    assert "ollama" in decision.model


@pytest.mark.asyncio
async def test_math_routes_to_gpt4o(engine):
    decision = await engine.route(
        messages=[{"role": "user", "content": "Calculate the derivative of x^3"}],
    )
    assert decision.category == "math"
    assert "openai/gpt-4o" == decision.model


@pytest.mark.asyncio
async def test_quality_first_strategy(engine):
    decision = await engine.route(
        messages=[{"role": "user", "content": "Hello!"}],
        strategy="quality-first",
    )
    # Quality-first should pick highest tier, not local
    assert decision.category == "simple_chat"


@pytest.mark.asyncio
async def test_local_only_strategy(engine):
    decision = await engine.route(
        messages=[{"role": "user", "content": "Write a Python function"}],
        strategy="local-only",
    )
    assert "ollama" in decision.model or decision.estimated_cost_per_1m == 0.0
