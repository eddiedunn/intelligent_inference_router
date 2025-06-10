import importlib
import os
import sys

from fastapi.testclient import TestClient

import router.registry as registry
from sqlalchemy import create_engine


def reload_router(secret: str | None):
    os.environ.pop("ROUTER_SHARED_SECRET", None)
    if secret is not None:
        os.environ["ROUTER_SHARED_SECRET"] = secret
    if "router.main" in sys.modules:
        rm = sys.modules["router.main"]
        from prometheus_client import REGISTRY

        for metric in ("REQUEST_COUNTER", "CACHE_HIT_COUNTER", "REQUEST_LATENCY"):
            collector = getattr(rm, metric, None)
            if collector is not None:
                try:
                    REGISTRY.unregister(collector)
                except KeyError:
                    pass
    if "router.settings" in sys.modules:
        importlib.reload(sys.modules["router.settings"])
    if "router.auth" in sys.modules:
        importlib.reload(sys.modules["router.auth"])
    if "router.main" in sys.modules:
        importlib.reload(sys.modules["router.main"])
    return importlib.import_module("router.main")


def setup_db(monkeypatch, tmp_path, router_main):
    db_path = tmp_path / "models.db"
    monkeypatch.setattr(router_main, "SQLITE_DB_PATH", str(db_path))
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    router_main.load_registry()


def test_unauthorized(monkeypatch, tmp_path):
    router_main = reload_router("s3cret")
    try:
        setup_db(monkeypatch, tmp_path, router_main)
        with TestClient(router_main.app) as client:
            payload = {"model": "dummy", "messages": [{"role": "user", "content": "x"}]}
            resp = client.post("/v1/chat/completions", json=payload)
            assert resp.status_code == 401
    finally:
        reload_router(None)


def test_authorized(monkeypatch, tmp_path):
    router_main = reload_router("s3cret")
    try:
        setup_db(monkeypatch, tmp_path, router_main)
        with TestClient(router_main.app) as client:
            payload = {"model": "dummy", "messages": [{"role": "user", "content": "x"}]}
            headers = {"Authorization": "Bearer s3cret"}
            resp = client.post("/v1/chat/completions", json=payload, headers=headers)
            assert resp.status_code == 200
    finally:
        reload_router(None)
