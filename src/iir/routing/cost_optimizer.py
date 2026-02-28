"""Cost-based model selection logic."""

from __future__ import annotations

from iir.routing.model_registry import ModelInfo

_QUALITY_ORDER = {"excellent": 3, "great": 2, "good": 1}


def select_cheapest(candidates: list[ModelInfo]) -> ModelInfo | None:
    if not candidates:
        return None
    return min(candidates, key=lambda m: m.cost_per_1m_input)


def select_best_quality(candidates: list[ModelInfo]) -> ModelInfo | None:
    if not candidates:
        return None
    return max(candidates, key=lambda m: _QUALITY_ORDER.get(m.quality_tier, 0))


def select_cost_optimized(candidates: list[ModelInfo], max_cost: float | None = None) -> ModelInfo | None:
    if not candidates:
        return None

    if max_cost is not None:
        affordable = [m for m in candidates if m.cost_per_1m_input <= max_cost * 1000]
        if affordable:
            candidates = affordable

    # Prefer free (local) models first
    free = [m for m in candidates if m.cost_per_1m_input == 0.0]
    if free:
        return max(free, key=lambda m: _QUALITY_ORDER.get(m.quality_tier, 0))

    # Among paid, pick cheapest with at least "great" quality
    great_or_better = [m for m in candidates if _QUALITY_ORDER.get(m.quality_tier, 0) >= 2]
    if great_or_better:
        return min(great_or_better, key=lambda m: m.cost_per_1m_input)

    return min(candidates, key=lambda m: m.cost_per_1m_input)
