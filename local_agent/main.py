from __future__ import annotations

import asyncio
import os
import uuid
from typing import List, Optional

import httpx

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Local Agent")

ROUTER_URL = os.getenv("ROUTER_URL", "http://localhost:8000")
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
AGENT_NAME = os.getenv("AGENT_NAME", "local-agent")
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT", "http://localhost:5000")
MODEL_LIST = os.getenv("MODEL_LIST", "local_mistral-7b-instruct-q4").split(",")


class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: Optional[bool] = False


async def _post_with_retry(path: str, payload: dict) -> None:
    """POST data to the router with retry on failure."""

    url = f"{ROUTER_URL.rstrip('/')}{path}"
    while True:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
            break
        except httpx.HTTPError:
            await asyncio.sleep(1)


async def register_with_router() -> None:
    """Register this agent with the router service."""

    payload = {
        "name": AGENT_NAME,
        "endpoint": AGENT_ENDPOINT,
        "models": MODEL_LIST,
    }
    await _post_with_retry("/register", payload)


async def heartbeat_loop() -> None:
    """Send regular heartbeat messages to the router."""

    while True:
        await _post_with_retry("/heartbeat", {"name": AGENT_NAME})
        await asyncio.sleep(HEARTBEAT_INTERVAL)


@app.on_event("startup")
async def _startup() -> None:
    """Start background registration and heartbeat tasks."""

    asyncio.create_task(register_with_router())
    asyncio.create_task(heartbeat_loop())


@app.post("/infer")
async def infer(payload: ChatCompletionRequest):
    """Return a trivial echo response for the given request."""

    user_msg = payload.messages[-1].content if payload.messages else ""
    content = f"Echo: {user_msg}"
    response = {
        "id": f"local-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": 0,
        "model": payload.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("local_agent.main:app", port=5000)
