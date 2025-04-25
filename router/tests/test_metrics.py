import pytest
from router.metrics import router_requests_total, router_requests_errors_total

def test_metrics_increment():
    start_total = router_requests_total._value.get()
    start_errors = router_requests_errors_total._value.get()
    router_requests_total.inc()
    router_requests_errors_total.inc()
    assert router_requests_total._value.get() == start_total + 1
    assert router_requests_errors_total._value.get() == start_errors + 1
