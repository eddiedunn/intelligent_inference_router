# Prometheus metrics for IIR MVP
# Prometheus metrics for IIR MVP
from prometheus_client import Counter, Histogram, REGISTRY
from fastapi import FastAPI

_metrics_cache = {}

def get_metrics(registry=None):
    """
    Returns a dict of Prometheus metrics, registering them only once per registry.
    """
    if registry is None:
        registry = REGISTRY
    key = id(registry)
    if key in _metrics_cache:
        return _metrics_cache[key]
    metrics = {
        "router_requests_total": Counter("router_requests_total", "Total requests received", registry=registry),
        "router_requests_errors_total": Counter("router_requests_errors_total", "Total error responses", registry=registry),
        "router_request_latency_seconds": Histogram("router_request_latency_seconds", "Request latency (seconds)", registry=registry),
        "router_cache_hits_total": Counter("router_cache_hits_total", "Cache hits", registry=registry),
        "router_cache_misses_total": Counter("router_cache_misses_total", "Cache misses", registry=registry),
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
