"""Routing strategy implementations."""

from __future__ import annotations

from iir.classifier.categories import TaskCategory
from iir.routing.cost_optimizer import select_best_quality, select_cheapest, select_cost_optimized
from iir.routing.model_registry import ModelInfo, ModelRegistry


def route_cost_optimized(
    category: TaskCategory,
    registry: ModelRegistry,
    max_cost: float | None = None,
) -> ModelInfo | None:
    # Try task default first
    default_id = registry.get_default_model_for_task(category)
    if default_id:
        model = registry.get_model(default_id)
        if model:
            return model

    candidates = registry.get_models_for_task(category)
    return select_cost_optimized(candidates, max_cost)


def route_quality_first(category: TaskCategory, registry: ModelRegistry) -> ModelInfo | None:
    candidates = registry.get_models_for_task(category)
    return select_best_quality(candidates)


def route_local_only(category: TaskCategory, registry: ModelRegistry) -> ModelInfo | None:
    candidates = registry.get_models_for_task(category)
    local = [m for m in candidates if m.cost_per_1m_input == 0.0]
    return select_best_quality(local) if local else select_cheapest(candidates)
