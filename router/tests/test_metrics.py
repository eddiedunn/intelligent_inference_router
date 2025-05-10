import pytest
from prometheus_client import CollectorRegistry
from router.metrics import get_metrics

def test_metrics_increment():
    registry = CollectorRegistry()
    metrics = get_metrics(registry=registry)
    total = metrics["router_requests_total"]
    errors = metrics["router_requests_errors_total"]
    start_total = total._value.get()
    start_errors = errors._value.get()
    total.inc()
    errors.inc()
    assert total._value.get() == start_total + 1
    assert errors._value.get() == start_errors + 1
