# Prometheus metrics for IIR MVP
from prometheus_client import Counter, Histogram
from fastapi import FastAPI

router_requests_total = Counter("router_requests_total", "Total requests received")
router_requests_errors_total = Counter("router_requests_errors_total", "Total error responses")
router_request_latency_seconds = Histogram("router_request_latency_seconds", "Request latency (seconds)")
router_cache_hits_total = Counter("router_cache_hits_total", "Cache hits")
router_cache_misses_total = Counter("router_cache_misses_total", "Cache misses")

# ... other metrics as needed

def instrument_app(app: FastAPI):
    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        router_requests_total.inc()
        with router_request_latency_seconds.time():
            response = await call_next(request)
        if response.status_code >= 400:
            router_requests_errors_total.inc()
        return response
