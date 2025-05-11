# Prometheus metrics for IIR MVP
# Prometheus metrics for IIR MVP
from prometheus_client import Counter, Histogram, REGISTRY
from fastapi import FastAPI

_metrics_cache = {}

def get_metrics(registry=None):
    """
    Returns a dict of Prometheus metrics, registering them only once per registry.
    Prevents ValueError from duplicated timeseries by reusing existing metrics if already registered.
    """
    if registry is None:
        registry = REGISTRY
    key = id(registry)
    if key in _metrics_cache:
        return _metrics_cache[key]

    def safe_counter(name, desc):
        from prometheus_client.metrics import Counter
        try:
            return Counter(name, desc, registry=registry)
        except ValueError:
            # Already registered, fetch existing
            return registry._names_to_collectors[name]

    def safe_histogram(name, desc):
        from prometheus_client.metrics import Histogram
        try:
            return Histogram(name, desc, registry=registry)
        except ValueError:
            return registry._names_to_collectors[name]

    metrics = {
        "router_requests_total": safe_counter("router_requests_total", "Total requests received"),
        "router_requests_errors_total": safe_counter("router_requests_errors_total", "Total error responses"),
        "router_request_latency_seconds": safe_histogram("router_request_latency_seconds", "Request latency (seconds)"),
        "router_cache_hits_total": safe_counter("router_cache_hits_total", "Cache hits"),
        "router_cache_misses_total": safe_counter("router_cache_misses_total", "Cache misses"),
    }
    _metrics_cache[key] = metrics
    return metrics

# ... other metrics as needed

def instrument_app(app: FastAPI, metrics=None):
    if metrics is None:
        metrics = get_metrics()
    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        metrics["router_requests_total"].inc()
        with metrics["router_request_latency_seconds"].time():
            response = await call_next(request)
        if response.status_code >= 400:
            metrics["router_requests_errors_total"].inc()
        return response
