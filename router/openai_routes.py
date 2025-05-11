from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from .openai_models import (
    ChatCompletionRequest, ChatCompletionResponse, OpenAIErrorResponse,
    CompletionRequest, CompletionResponse
)
from typing import AsyncGenerator
import time

router = APIRouter()

# --- Chat Completions Endpoint ---
import httpx
import os
import yaml
from .provider_router import ProviderRouter

# Load config once (in production, reload on SIGHUP or use a config service)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.example.yaml")
with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)
PROVIDER_ROUTER = None

def set_provider_router(router_instance):
    global PROVIDER_ROUTER
    PROVIDER_ROUTER = router_instance

@router.post("/v1/chat/completions", response_model=None, responses={400: {"model": OpenAIErrorResponse}})
async def chat_completions(
    req: ChatCompletionRequest,
    request: Request,
):
    import logging
    logger = logging.getLogger("iir.proxy")
    payload = req.model_dump(exclude_unset=True)
    payload.pop("mcp", None)
    user_id = request.headers.get("x-user-id") or payload.get("user")
    provider_router = request.app.state.provider_router
    cache_key = provider_router.cache_key(payload)
    # Caching (only for non-stream)
    # Async cache usage
    if not payload.get("stream") and CONFIG.get("caching", {}).get("enabled"):
        cached = await provider_router.cache_get(cache_key)
        if cached:
            logger.info(f"Cache hit for /v1/chat/completions user={user_id}")
            return JSONResponse(content=cached, status_code=200)
    provider_url, headers, provider_name = provider_router.select_provider(payload, user_id)
    logger.info(f"Proxying /v1/chat/completions to {provider_url} with model {payload['model']} user={user_id}")
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            if payload.get("stream"):
                r = await client.post(provider_url, json=payload, headers=headers, stream=True)
                return StreamingResponse(r.aiter_raw(), media_type="text/event-stream")
            else:
                r = await client.post(provider_url, json=payload, headers=headers)
                await provider_router.cache_set(cache_key, r.json(), ttl=CONFIG.get("caching", {}).get("ttl", 60))
                # Usage reporting (stub: count tokens if possible)
                provider_router.record_usage(provider_name, user_id, tokens=0)
                return JSONResponse(content=r.json(), status_code=r.status_code)
        except httpx.HTTPError as e:
            logger.error(f"Proxy error: {e}")
            return JSONResponse(
                status_code=502,
                content={
                    "error": {
                        "message": str(e),
                        "type": "proxy_error",
                        "param": None,
                        "code": "proxy_error"
                    }
                },
            )

# --- Completions Endpoint ---
@router.post("/v1/completions", response_model=None, responses={400: {"model": OpenAIErrorResponse}})
async def completions(
    req: CompletionRequest,
    request: Request,
):
    import logging
    logger = logging.getLogger("iir.proxy")
    payload = req.model_dump(exclude_unset=True)
    payload.pop("mcp", None)
    user_id = request.headers.get("x-user-id") or payload.get("user")
    provider_router = request.app.state.provider_router
    cache_key = provider_router.cache_key(payload)
    # Caching (only for non-stream)
    # Async cache usage
    if not payload.get("stream") and CONFIG.get("caching", {}).get("enabled"):
        cached = await provider_router.cache_get(cache_key)
        if cached:
            logger.info(f"Cache hit for /v1/completions user={user_id}")
            return JSONResponse(content=cached, status_code=200)
    provider_url, headers, provider_name = provider_router.select_provider(payload, user_id, context=None)
    logger.info(f"Proxying /v1/completions to {provider_url} with model {payload['model']} user={user_id}")
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            if payload.get("stream"):
                r = await client.post(provider_url, json=payload, headers=headers, stream=True)
                return StreamingResponse(r.aiter_raw(), media_type="text/event-stream")
            else:
                r = await client.post(provider_url, json=payload, headers=headers)
                await provider_router.cache_set(cache_key, r.json(), ttl=CONFIG.get("caching", {}).get("ttl", 60))
                provider_router.record_usage(provider_name, user_id, tokens=0)
                return JSONResponse(content=r.json(), status_code=r.status_code)
        except httpx.HTTPError as e:
            logger.error(f"Proxy error: {e}")
            return JSONResponse(
                status_code=502,
                content={
                    "error": {
                        "message": str(e),
                        "type": "proxy_error",
                        "param": None,
                        "code": "proxy_error"
                    }
                },
            )

