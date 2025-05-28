from __future__ import annotations

import os
import time
import uuid
from typing import AsyncIterator, List, Optional
import json
import hashlib

import redis.asyncio as redis

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from fastapi import FastAPI
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
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))

redis_client = redis.from_url(REDIS_URL)

app = FastAPI(title="Intelligent Inference Router")

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

def make_cache_key(payload: ChatCompletionRequest) -> str:
    """Return a Redis cache key for the given request."""

    serialized = json.dumps(payload.dict(), sort_keys=True)
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    return f"chat:{payload.model}:{digest}"



async def forward_to_local_agent(payload: ChatCompletionRequest) -> dict:
    async with httpx.AsyncClient(base_url=LOCAL_AGENT_URL) as client:
        resp = await client.post("/infer", json=payload.dict())
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:  # coverage: ignore  -- best-effort
            raise HTTPException(status_code=502, detail="Local agent error") from exc
        return resp.json()


async def _stream_resp(resp: httpx.Response) -> AsyncIterator[str]:
    async for chunk in resp.aiter_text():
        yield chunk


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
            return StreamingResponse(_stream_resp(resp), media_type="text/event-stream")

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
    cache_key = make_cache_key(payload)
    if not payload.stream:
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    entry = MODEL_REGISTRY.get(payload.model)

    if entry is not None:
        if entry.type == "local":
            data = await forward_to_local_agent(payload)
            if not payload.stream:
                await redis_client.setex(cache_key, CACHE_TTL, json.dumps(data))
            return data
        if entry.type == "openai":
            data = await forward_to_openai(payload)
            if not payload.stream:
                await redis_client.setex(cache_key, CACHE_TTL, json.dumps(data))
            return data

    if payload.model.startswith("local"):
        data = await forward_to_local_agent(payload)
        if not payload.stream:
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(data))
        return data

    if payload.model.startswith("gpt-"):
        data = await forward_to_openai(payload)
        if not payload.stream:
            await redis_client.setex(cache_key, CACHE_TTL, json.dumps(data))
        return data

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
    if not payload.stream:
        await redis_client.setex(cache_key, CACHE_TTL, json.dumps(response))
    return response
