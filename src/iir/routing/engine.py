"""Main routing engine: classify prompt, select model, return decision."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from iir.cache.keys import classification_cache_key
from iir.classifier.base import HybridClassifier
from iir.classifier.categories import TaskCategory
from iir.observability.metrics import Metrics
from iir.routing.model_registry import ModelRegistry
from iir.routing.strategies import route_cost_optimized, route_local_only, route_quality_first

logger = logging.getLogger("iir.routing")


@dataclass
class RoutingDecision:
    model: str
    provider: str
    category: str
    reason: str
    estimated_cost_per_1m: float = 0.0


class RoutingEngine:
    def __init__(
        self,
        registry: ModelRegistry,
        classifier: HybridClassifier,
        cache: Any,
        metrics: Metrics,
        cache_ttl: int = 3600,
        default_strategy: str = "cost-optimized",
        max_cost: float | None = None,
    ) -> None:
        self.registry = registry
        self.classifier = classifier
        self.cache = cache
        self.metrics = metrics
        self.cache_ttl = cache_ttl
        self.default_strategy = default_strategy
        self.max_cost = max_cost

    async def route(
        self,
        messages: list[dict[str, Any]],
        strategy: str | None = None,
        explicit_model: str | None = None,
        max_cost: float | None = None,
        **kwargs: Any,
    ) -> RoutingDecision:
        # Pass-through: user specified a model
        if explicit_model and self.registry.model_exists(explicit_model):
            model = self.registry.get_model(explicit_model)
            assert model is not None
            return RoutingDecision(
                model=model.id,
                provider=model.provider,
                category="explicit",
                reason="User-specified model",
                estimated_cost_per_1m=model.cost_per_1m_input,
            )

        # Classify the prompt
        category = await self._classify(messages, **kwargs)
        self.metrics.classification_category.labels(category=category.value).inc()

        # Select model based on strategy
        active_strategy = strategy or self.default_strategy
        active_max_cost = max_cost or self.max_cost
        model_info = self._select_model(category, active_strategy, active_max_cost)

        if model_info is None:
            # Fallback to any default
            default_id = self.registry.get_default_model_for_task(TaskCategory.GENERAL_CHAT)
            model_info = self.registry.get_model(default_id) if default_id else None

        if model_info is None:
            models = self.registry.list_models()
            if models:
                model_info = models[0]
            else:
                return RoutingDecision(
                    model="unknown",
                    provider="unknown",
                    category=category.value,
                    reason="No models available",
                )

        self.metrics.model_routed.labels(model=model_info.id).inc()

        return RoutingDecision(
            model=model_info.id,
            provider=model_info.provider,
            category=category.value,
            reason=f"Strategy={active_strategy}, task={category.value}",
            estimated_cost_per_1m=model_info.cost_per_1m_input,
        )

    async def _classify(self, messages: list[dict[str, Any]], **kwargs: Any) -> TaskCategory:
        cache_key = classification_cache_key(messages)

        # Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            self.metrics.cache_hits.labels(cache_type="classification").inc()
            try:
                return TaskCategory(cached)
            except ValueError:
                pass
        else:
            self.metrics.cache_misses.labels(cache_type="classification").inc()

        start = time.monotonic()
        category = await self.classifier.classify(messages, **kwargs)
        elapsed = time.monotonic() - start
        self.metrics.classification_latency.observe(elapsed)

        # Cache result
        await self.cache.set(cache_key, category.value, ttl=self.cache_ttl)

        return category

    def _select_model(self, category: TaskCategory, strategy: str, max_cost: float | None) -> Any:
        if strategy == "quality-first":
            return route_quality_first(category, self.registry)
        if strategy == "local-only":
            return route_local_only(category, self.registry)
        return route_cost_optimized(category, self.registry, max_cost)
