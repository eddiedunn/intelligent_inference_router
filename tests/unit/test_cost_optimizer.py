"""Tests for cost optimizer model selection."""

from iir.routing.cost_optimizer import select_cheapest, select_best_quality, select_cost_optimized
from iir.routing.model_registry import ModelInfo


def _model(name: str, cost: float, quality: str = "good") -> ModelInfo:
    return ModelInfo(id=name, provider=name.split("/")[0], cost_per_1m_input=cost, quality_tier=quality)


def test_select_cheapest():
    models = [_model("a/1", 5.0), _model("b/2", 1.0), _model("c/3", 10.0)]
    assert select_cheapest(models).id == "b/2"


def test_select_cheapest_empty():
    assert select_cheapest([]) is None


def test_select_best_quality():
    models = [_model("a/1", 1.0, "good"), _model("b/2", 5.0, "excellent"), _model("c/3", 3.0, "great")]
    assert select_best_quality(models).id == "b/2"


def test_cost_optimized_prefers_free():
    models = [_model("a/1", 0.0, "good"), _model("b/2", 1.0, "excellent")]
    assert select_cost_optimized(models).id == "a/1"


def test_cost_optimized_cheapest_great_when_no_free():
    models = [_model("a/1", 5.0, "great"), _model("b/2", 1.0, "great"), _model("c/3", 0.5, "good")]
    assert select_cost_optimized(models).id == "b/2"


def test_cost_optimized_with_max_cost():
    models = [_model("a/1", 10.0, "excellent"), _model("b/2", 0.5, "great")]
    result = select_cost_optimized(models, max_cost=0.001)
    assert result.id == "b/2"
