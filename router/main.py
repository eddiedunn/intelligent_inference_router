from __future__ import annotations

import os
import time
import uuid
from typing import AsyncIterator, List, Optional

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from fastapi import FastAPI
from pydantic import BaseModel

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/models.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
LOCAL_AGENT_URL = os.getenv("LOCAL_AGENT_URL", "http://localhost:5000")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
EXTERNAL_OPENAI_KEY = os.getenv("EXTERNAL_OPENAI_KEY")

app = FastAPI(title="Intelligent Inference Router")


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: Optional[bool] = False


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
            resp = await client.post(
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


@app.post("/v1/chat/completions")
async def chat_completions(payload: ChatCompletionRequest):
    if payload.model.startswith("local"):
        return await forward_to_local_agent(payload)

    if payload.model.startswith("gpt-"):
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
