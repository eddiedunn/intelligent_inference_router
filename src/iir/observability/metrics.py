"""Prometheus metrics registration and middleware."""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram, REGISTRY


def _safe_counter(name: str, desc: str, registry: CollectorRegistry, labelnames: tuple[str, ...] = ()) -> Counter:
    try:
        return Counter(name, desc, labelnames=labelnames, registry=registry)
    except ValueError:
        return registry._names_to_collectors.get(name + "_total") or registry._names_to_collectors[name]


def _safe_histogram(name: str, desc: str, registry: CollectorRegistry, labelnames: tuple[str, ...] = ()) -> Histogram:
    try:
        return Histogram(name, desc, labelnames=labelnames, registry=registry)
    except ValueError:
        return registry._names_to_collectors[name]


class Metrics:
    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        reg = registry or REGISTRY
        self.requests_total = _safe_counter("iir_requests_total", "Total requests", reg)
        self.request_errors_total = _safe_counter("iir_request_errors_total", "Total error responses", reg)
        self.request_latency = _safe_histogram("iir_request_latency_seconds", "Request latency", reg)
        self.classification_latency = _safe_histogram("iir_classification_latency_seconds", "Classification latency", reg)
        self.model_routed = _safe_counter("iir_model_routed_total", "Requests routed per model", reg, labelnames=("model",))
        self.classification_category = _safe_counter("iir_classification_category_total", "Classifications per category", reg, labelnames=("category",))
        self.cache_hits = _safe_counter("iir_cache_hits_total", "Cache hits", reg, labelnames=("cache_type",))
        self.cache_misses = _safe_counter("iir_cache_misses_total", "Cache misses", reg, labelnames=("cache_type",))


_metrics: Metrics | None = None


def get_metrics(registry: CollectorRegistry | None = None) -> Metrics:
    global _metrics
    if _metrics is None:
        _metrics = Metrics(registry)
    return _metrics
