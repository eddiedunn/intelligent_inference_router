from __future__ import annotations

import os
import time
import uuid


import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse, JSONResponse
from prometheus_client import (
    Counter,
    Histogram,
    CONTENT_TYPE_LATEST,
    generate_latest,
)
import logging
from logging.handlers import TimedRotatingFileHandler

from typing import List, Optional, Dict

import json
import hashlib

import redis.asyncio as redis


from starlette.middleware.base import BaseHTTPMiddleware

from .utils import stream_resp

from pydantic import BaseModel


from .registry import (
    ModelEntry,
    create_tables,
    get_session,
    upsert_agent,
    upsert_model,
    update_heartbeat,
)

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/models.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LOCAL_AGENT_URL = os.getenv("LOCAL_AGENT_URL", "http://localhost:5000")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
EXTERNAL_OPENAI_KEY = os.getenv("EXTERNAL_OPENAI_KEY")
# Base URL for the llm-d inference gateway (GPU worker cluster)
LLMD_ENDPOINT = os.getenv("LLMD_ENDPOINT")


ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
EXTERNAL_ANTHROPIC_KEY = os.getenv("EXTERNAL_ANTHROPIC_KEY")

GOOGLE_BASE_URL = os.getenv(
    "GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com"
)
EXTERNAL_GOOGLE_KEY = os.getenv("EXTERNAL_GOOGLE_KEY")

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai")
EXTERNAL_OPENROUTER_KEY = os.getenv("EXTERNAL_OPENROUTER_KEY")

GROK_BASE_URL = os.getenv("GROK_BASE_URL", "https://api.groq.com")
EXTERNAL_GROK_KEY = os.getenv("EXTERNAL_GROK_KEY")

VENICE_BASE_URL = os.getenv("VENICE_BASE_URL", "https://api.venice.ai")
EXTERNAL_VENICE_KEY = os.getenv("EXTERNAL_VENICE_KEY")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_PATH = os.getenv("LOG_PATH", "logs/router.log")

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

CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))

redis_client = redis.from_url(REDIS_URL)

RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_STATE: Dict[str, List[float]] = {}


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
    load_registry()
    log_dir = os.path.dirname(LOG_PATH)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = TimedRotatingFileHandler(LOG_PATH, when="D", interval=1)
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.setLevel(LOG_LEVEL.upper())
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: Optional[bool] = False


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

    if payload.model.startswith("local"):
        return "local"

    if payload.model.startswith("gpt-"):
        return "openai"

    return "dummy"


def make_cache_key(payload: ChatCompletionRequest) -> str:
    """Return a Redis cache key for the given request."""

    serialized = json.dumps(payload.dict(), sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


async def forward_to_local_agent(payload: ChatCompletionRequest) -> dict:
    async with httpx.AsyncClient(base_url=LOCAL_AGENT_URL) as client:
        resp = await client.post("/infer", json=payload.dict())
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # coverage: ignore  -- best-effort
            raise HTTPException(status_code=502, detail="Local agent error") from exc
        return resp.json()


async def forward_to_openai(payload: ChatCompletionRequest):
    """Forward request to the OpenAI API."""

    if EXTERNAL_OPENAI_KEY is None:
        raise HTTPException(status_code=500, detail="OpenAI key not configured")

    headers = {"Authorization": f"Bearer {EXTERNAL_OPENAI_KEY}"}
    async with httpx.AsyncClient(base_url=OPENAI_BASE_URL) as client:
        if payload.stream:
            resp = await client.post(  # type: ignore[call-arg]
                "/v1/chat/completions",
                json=payload.dict(),
                headers=headers,
                stream=True,
            )
            try:
                resp.raise_for_status()
            except httpx.HTTPError as exc:  # coverage: ignore  -- best-effort
                raise HTTPException(
                    status_code=502, detail="External provider error"
                ) from exc
            return StreamingResponse(stream_resp(resp), media_type="text/event-stream")

        resp = await client.post(
            "/v1/chat/completions",
            json=payload.dict(),
            headers=headers,
        )
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # coverage: ignore  -- best-effort
            raise HTTPException(
                status_code=502, detail="External provider error"
            ) from exc
        return resp.json()


async def forward_to_llmd(payload: ChatCompletionRequest):
    """Forward request to the llm-d cluster."""

    if LLMD_ENDPOINT is None:
        raise HTTPException(status_code=500, detail="LLMD_ENDPOINT not configured")

    async with httpx.AsyncClient(base_url=LLMD_ENDPOINT) as client:
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


@app.post("/register")
async def register_agent(payload: AgentRegistration) -> dict:
    """Register a local agent and update the model registry."""

    with get_session() as session:
        upsert_agent(session, payload.name, payload.endpoint, payload.models)
        for model in payload.models:
            upsert_model(session, model, "local", payload.endpoint)
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
    try:
        entry = MODEL_REGISTRY.get(payload.model)

        if entry is not None:
            if entry.type == "local":
                backend = "local"
                return await forward_to_local_agent(payload)
            if entry.type == "openai":
                backend = "openai"
                return await forward_to_openai(payload)

        if payload.model.startswith("local"):
            backend = "local"
            return await forward_to_local_agent(payload)

        if payload.model.startswith("gpt-"):
            backend = "openai"
            return await forward_to_openai(payload)

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
        return response
    finally:
        latency = time.perf_counter() - start
        REQUEST_COUNTER.labels(backend=backend).inc()
        REQUEST_LATENCY.labels(backend=backend).observe(latency)
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
