"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI

from iir.api.routes_admin import router as admin_router
from iir.api.routes_chat import router as chat_router
from iir.api.routes_health import router as health_router
from iir.api.routes_models import router as models_router
from iir.auth.apikey_db import add_api_key, init_db
from iir.bifrost_client.client import BifrostClient
from iir.cache.memory_cache import MemoryCache
from iir.cache.redis_cache import RedisCache
from iir.classifier.base import HybridClassifier
from iir.classifier.llm_classifier import LLMClassifier
from iir.classifier.rules import RulesClassifier
from iir.config import Settings, get_settings
from iir.middleware.body_limit import BodyLimitMiddleware
from iir.middleware.request_id import RequestIDMiddleware
from iir.observability.logging import setup_logging
from iir.observability.metrics import Metrics, get_metrics
from iir.routing.engine import RoutingEngine
from iir.routing.model_registry import ModelRegistry

logger = logging.getLogger("iir.app")


def create_app(settings_override: dict[str, Any] | None = None) -> FastAPI:
    settings = Settings(**(settings_override or {}))
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # --- Startup ---
        # Auth DB
        init_db(settings.auth_db_path)
        if settings.api_key:
            add_api_key(settings.auth_db_path, settings.api_key, "startup", "env auto-import")

        # Cache
        cache: RedisCache | MemoryCache
        try:
            cache = RedisCache(settings.redis_url)
            await cache.connect()
            logger.info("Redis cache connected")
        except Exception as exc:
            if settings.redis_fallback_to_memory:
                logger.warning("Redis unavailable (%s), using in-memory cache", exc)
                cache = MemoryCache()
            else:
                raise
        app.state.cache = cache

        # Bifrost client
        bifrost = BifrostClient(settings.bifrost_url, settings.bifrost_timeout)
        await bifrost.start()
        app.state.bifrost = bifrost

        # Model registry
        registry = ModelRegistry()
        registry.load_from_yaml(settings.routing_config_path)

        # Classifier
        rules = RulesClassifier()
        llm: LLMClassifier | None = None
        if settings.classifier_strategy in ("hybrid", "llm_only"):
            llm = LLMClassifier(settings.ollama_url, settings.classifier_model)
        classifier = HybridClassifier(rules, llm, settings.classifier_strategy)

        # Metrics
        metrics = get_metrics()

        # Routing engine
        app.state.routing_engine = RoutingEngine(
            registry=registry,
            classifier=classifier,
            cache=cache,
            metrics=metrics,
            cache_ttl=settings.classification_cache_ttl,
            default_strategy=settings.routing_default_strategy,
            max_cost=settings.max_cost_per_request,
        )

        logger.info("IIR v2 started — strategy=%s, bifrost=%s", settings.routing_default_strategy, settings.bifrost_url)
        yield

        # --- Shutdown ---
        await bifrost.close()
        await cache.close()

    app = FastAPI(title="Intelligent Inference Router", version="2.0.0", lifespan=lifespan)

    # Middleware (order matters: outermost first)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_body_size)

    # Routes
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(models_router)
    app.include_router(admin_router)

    return app
