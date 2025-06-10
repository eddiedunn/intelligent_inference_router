"""Router entry point handling provider forwarding and caching."""

from __future__ import annotations

import os
import time
import uuid

import json
import hashlib
import logging
from logging.handlers import TimedRotatingFileHandler
from typing import List, Dict

import tomllib
from pathlib import Path


import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse, JSONResponse

from starlette.middleware.base import BaseHTTPMiddleware

from prometheus_client import (
    Counter,
    Histogram,
    CONTENT_TYPE_LATEST,
    generate_latest,
)


from .utils import stream_resp
from .providers import (
    openai,
    anthropic,
    google,
    openrouter,
    grok,
    venice,
)
import router.providers as providers
from .providers.base import WeightProvider

from .schemas import ChatCompletionRequest, Message as SchemaMessage
from pydantic import BaseModel

from .config import Settings


from .registry import (
    ModelEntry,
    create_tables,
    get_session,
    upsert_agent,
    upsert_model,
    update_heartbeat,
)

Message = SchemaMessage

settings = Settings()

logger = logging.getLogger("router")

REQUEST_COUNTER = Counter(
    "router_requests_total",
    "Total requests processed",
    labelnames=["backend"],
)
CACHE_HIT_COUNTER = Counter(
    "router_cache_hits_total",
    "Number of cache hits",
    labelnames=["model"],
)
REQUEST_LATENCY = Histogram(
    "router_request_latency_seconds",
    "Request latency in seconds",
    labelnames=["backend"],
)


# Cache configuration
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))
CACHE_ENDPOINT = os.getenv("CACHE_ENDPOINT")


# Simple in-memory cache: {key: (expires_at, json_value)}
CACHE_STORE: Dict[str, tuple[float, str]] = {}


async def cache_get(key: str) -> str | None:
    """Return cached value if present and not expired."""
    if CACHE_ENDPOINT:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{CACHE_ENDPOINT}/{key}", timeout=2)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code != 404:
                logger.warning("remote cache get failed: %s", resp.status_code)
        except Exception:
            logger.warning("remote cache unavailable; falling back to local")

    entry = CACHE_STORE.get(key)
    if entry is None:
        return None
    expires, value = entry
    if time.time() > expires:
        CACHE_STORE.pop(key, None)
        return None
    return value


async def cache_set(key: str, value: str, ttl: int = CACHE_TTL) -> None:
    """Store a value in the cache for ``ttl`` seconds."""
    if CACHE_ENDPOINT:
        try:
            async with httpx.AsyncClient() as client:
                await client.put(
                    f"{CACHE_ENDPOINT}/{key}",
                    params={"ttl": ttl},
                    content=value,
                    timeout=2,
                )
                return
        except Exception:
            logger.warning("remote cache set failed; storing locally")

    CACHE_STORE[key] = (time.time() + ttl, value)


RATE_LIMIT_REQUESTS = settings.rate_limit_requests
RATE_LIMIT_WINDOW = settings.rate_limit_window
RATE_LIMIT_STATE: Dict[str, List[float]] = {}

# Routing configuration weights
try:
    with open(Path(__file__).resolve().parents[1] / "pyproject.toml", "rb") as f:
        _config = tomllib.load(f).get("tool", {}).get("router", {})
except Exception:
    _config = {}

ROUTER_COST_WEIGHT = float(_config.get("cost_weight", settings.router_cost_weight))
ROUTER_LATENCY_WEIGHT = float(
    _config.get("latency_weight", settings.router_latency_weight)
)
ROUTER_COST_THRESHOLD = int(
    _config.get("cost_threshold", settings.router_cost_threshold)
)

BACKEND_METRICS: Dict[str, Dict[str, float]] = {}

# Cache for instantiated weight providers
WEIGHT_PROVIDERS: Dict[str, WeightProvider] = {}


def get_weight_provider(name: str) -> WeightProvider:
    """Return or create a weight provider instance."""

    provider = WEIGHT_PROVIDERS.get(name)
    if provider is None:
        module = providers.PROVIDER_REGISTRY.get(name)
        if module is None:
            raise HTTPException(
                status_code=500,
                detail=f"Unsupported provider '{name}'",
            )
        class_name = "".join(part.capitalize() for part in name.split("_")) + "Provider"
        provider_cls = getattr(module, class_name, None)
        if provider_cls is None:
            raise HTTPException(
                status_code=500,
                detail=f"Provider class for '{name}' not found",
            )
        provider = provider_cls()
        WEIGHT_PROVIDERS[name] = provider
    return provider


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter."""

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = RATE_LIMIT_WINDOW
        max_req = RATE_LIMIT_REQUESTS

        timestamps = RATE_LIMIT_STATE.get(client_ip, [])
        timestamps = [t for t in timestamps if now - t < window]
        if len(timestamps) >= max_req:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)

        timestamps.append(now)
        RATE_LIMIT_STATE[client_ip] = timestamps
        response = await call_next(request)
        return response


app = FastAPI(title="Intelligent Inference Router")
app.add_middleware(RateLimitMiddleware)

MODEL_REGISTRY: dict[str, ModelEntry] = {}


def load_registry() -> None:
    """Load models from the SQLite registry into memory."""

    create_tables()
    with get_session() as session:
        MODEL_REGISTRY.clear()
        for entry in session.query(ModelEntry).all():
            MODEL_REGISTRY[entry.name] = entry


@app.on_event("startup")
async def _startup() -> None:
    global settings
    settings = Settings()
    global CACHE_TTL, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW
    global ROUTER_COST_WEIGHT, ROUTER_LATENCY_WEIGHT, ROUTER_COST_THRESHOLD
    CACHE_TTL = settings.cache_ttl
    RATE_LIMIT_REQUESTS = settings.rate_limit_requests
    RATE_LIMIT_WINDOW = settings.rate_limit_window
    ROUTER_COST_WEIGHT = settings.router_cost_weight
    ROUTER_LATENCY_WEIGHT = settings.router_latency_weight
    ROUTER_COST_THRESHOLD = settings.router_cost_threshold
    load_registry()
    CACHE_STORE.clear()
    log_dir = os.path.dirname(settings.log_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = TimedRotatingFileHandler(settings.log_path, when="D", interval=1)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.setLevel(settings.log_level.upper())
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


class AgentRegistration(BaseModel):
    name: str
    endpoint: str
    models: List[str]


class AgentHeartbeat(BaseModel):
    name: str


def select_backend(payload: ChatCompletionRequest) -> str:
    """Return backend key for the given request."""

    entry = MODEL_REGISTRY.get(payload.model)
    if entry is not None:
        return entry.type

    def _request_cost(req: ChatCompletionRequest) -> int:
        return sum(len(m.content) for m in req.messages)

    if payload.model.startswith("local"):
        return "local"

    if payload.model.startswith("gpt-"):
        cost = _request_cost(payload)
        if cost >= ROUTER_COST_THRESHOLD:
            return "local"
        local_lat = BACKEND_METRICS.get("local", {}).get("latency")
        openai_lat = BACKEND_METRICS.get("openai", {}).get("latency")
        if local_lat is None or openai_lat is None:
            return "local"
        return "openai" if openai_lat < local_lat else "local"

    if payload.model.startswith("llmd-"):
        return "llm-d"

    if payload.model.startswith("claude"):
        return "anthropic"

    if payload.model.startswith("google"):
        return "google"

    if payload.model.startswith("openrouter"):
        return "openrouter"

    if payload.model.startswith("grok"):
        return "grok"

    if payload.model.startswith("venice"):
        return "venice"

    return "dummy"


def make_cache_key(payload: ChatCompletionRequest) -> str:
    """Return a cache key for the given request."""

    serialized = json.dumps(payload.dict(), sort_keys=True)

    digest = hashlib.sha256(serialized.encode()).hexdigest()

    return f"chat:{digest}"


async def forward_to_local_agent(payload: ChatCompletionRequest) -> dict:
    async with httpx.AsyncClient(base_url=settings.local_agent_url) as client:
        resp = await client.post("/infer", json=payload.dict())
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # coverage: ignore  -- best-effort
            raise HTTPException(status_code=502, detail="Local agent error") from exc
        return resp.json()


async def forward_to_openai(payload: ChatCompletionRequest):
    """Forward request to the OpenAI API."""

    return await openai.forward(
        payload, settings.openai_base_url, settings.external_openai_key
    )


async def forward_to_llmd(payload: ChatCompletionRequest):
    """Forward request to the llm-d cluster."""

    if settings.llmd_endpoint is None:
        raise HTTPException(status_code=500, detail="LLMD_ENDPOINT not configured")

    async with httpx.AsyncClient(base_url=settings.llmd_endpoint) as client:
        if payload.stream:
            resp = await client.post(  # type: ignore[call-arg]
                "/v1/chat/completions",
                json=payload.dict(),
                stream=True,
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPError as exc:  # coverage: ignore  -- best-effort
                raise HTTPException(status_code=502, detail="llm-d error") from exc
            return StreamingResponse(stream_resp(resp), media_type="text/event-stream")

        resp = await client.post("/v1/chat/completions", json=payload.dict())
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # coverage: ignore  -- best-effort
            raise HTTPException(status_code=502, detail="llm-d error") from exc
        return resp.json()


async def forward_to_anthropic(payload: ChatCompletionRequest):
    """Forward request to Anthropic."""

    return await anthropic.forward(
        payload, settings.anthropic_base_url, settings.external_anthropic_key
    )


async def forward_to_google(payload: ChatCompletionRequest):
    """Forward request to Google."""

    return await google.forward(
        payload, settings.google_base_url, settings.external_google_key
    )


async def forward_to_openrouter(payload: ChatCompletionRequest):
    """Forward request to OpenRouter."""

    return await openrouter.forward(
        payload, settings.openrouter_base_url, settings.external_openrouter_key
    )


async def forward_to_grok(payload: ChatCompletionRequest):
    """Forward request to Grok."""

    return await grok.forward(
        payload, settings.grok_base_url, settings.external_grok_key
    )


async def forward_to_venice(payload: ChatCompletionRequest):
    """Forward request to Venice."""

    return await venice.forward(
        payload, settings.venice_base_url, settings.external_venice_key
    )


@app.post("/register")
async def register_agent(payload: AgentRegistration) -> dict:
    """Register a local agent and update the model registry."""

    with get_session() as session:
        upsert_agent(session, payload.name, payload.endpoint, payload.models)
        for model in payload.models:
            upsert_model(session, model, "local", payload.endpoint, "weight")
    load_registry()
    return {"status": "ok"}


@app.post("/heartbeat")
async def heartbeat(payload: AgentHeartbeat) -> dict:
    """Update agent heartbeat timestamp."""

    with get_session() as session:
        update_heartbeat(session, payload.name)
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(payload: ChatCompletionRequest):

    start = time.perf_counter()
    backend = "dummy"
    cache_hit = False
    cache_key = make_cache_key(payload)
    cached = await cache_get(cache_key)
    if cached is not None:
        cache_hit = True
        return json.loads(cached)

    async def call_and_cache(func):
        result = await func(payload)
        if not payload.stream:
            await cache_set(cache_key, json.dumps(result))
        return result

    try:
        entry = MODEL_REGISTRY.get(payload.model)

        if entry is not None:
            backend = entry.type
            if entry.kind == "weight":
                if entry.type == "local":
                    return await call_and_cache(forward_to_local_agent)
                if entry.type == "llm-d":
                    return await forward_to_llmd(payload)
                provider = get_weight_provider(entry.type)
                return await call_and_cache(
                    lambda p=payload: provider.forward(p, entry.endpoint)
                )

            if entry.type == "local":
                return await call_and_cache(forward_to_local_agent)
            if entry.type == "openai":
                return await call_and_cache(forward_to_openai)
            if entry.type == "anthropic":
                return await call_and_cache(forward_to_anthropic)
            if entry.type == "google":
                return await call_and_cache(forward_to_google)
            if entry.type == "openrouter":
                return await call_and_cache(forward_to_openrouter)
            if entry.type == "grok":
                return await call_and_cache(forward_to_grok)
            if entry.type == "venice":
                return await call_and_cache(forward_to_venice)
            if entry.type == "llm-d":
                return await forward_to_llmd(payload)

        if payload.model.startswith("local"):
            backend = "local"
            return await call_and_cache(forward_to_local_agent)

        if payload.model.startswith("gpt-"):
            backend = "openai"
            return await call_and_cache(forward_to_openai)

        dummy_text = "Hello world"
        response = {
            "id": f"cmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": payload.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": dummy_text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }
        await cache_set(cache_key, json.dumps(response))
        return response
    finally:
        latency = time.perf_counter() - start
        REQUEST_COUNTER.labels(backend=backend).inc()
        REQUEST_LATENCY.labels(backend=backend).observe(latency)
        stat = BACKEND_METRICS.setdefault(backend, {"latency": 0.0, "count": 0})
        stat["count"] += 1
        stat["latency"] += (latency - stat["latency"]) / stat["count"]
        if cache_hit:
            CACHE_HIT_COUNTER.labels(model=payload.model).inc()
        logger.info(
            "model=%s backend=%s latency=%.3f cache_hit=%s",
            payload.model,
            backend,
            latency,
            cache_hit,
        )


@app.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics."""

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
