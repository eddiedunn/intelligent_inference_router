import pytest
from router.cache import SimpleCache

def test_cache_set_and_get():
    cache = SimpleCache()
    cache.set('foo', 'bar')
    assert cache.get('foo') == 'bar'

def test_cache_expiry():
    cache = SimpleCache()
    cache.set('baz', 'qux', ex=1)
    import time
    time.sleep(1.1)
    assert cache.get('baz') is None
