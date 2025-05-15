from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from .validation_utils import validate_model_and_messages
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

from router.main import rate_limiter_dep

@router.post("/v1/chat/completions", response_model=None, responses={400: {"model": OpenAIErrorResponse}})
async def chat_completions(
    request: Request,
    rate_limiter=Depends(rate_limiter_dep),
    test_force_error: str = Depends(lambda: None)  # test-only slot for forced error short-circuiting
):
    import logging
    from pydantic import ValidationError
    logger = logging.getLogger("iir.proxy")
    logger.debug("[ENTRY] /v1/chat/completions called. Rate limiter dependency executed.")
    if test_force_error:
        logger.debug(f"[TEST] Forced error dependency triggered: {test_force_error}")
        return JSONResponse({"error": {"type": "forced_error", "code": test_force_error, "message": f"Forced error: {test_force_error}"}}, status_code=499)
    # Step 1: Parse raw JSON and validate error contract
    try:
        raw = await request.body()
        payload = json.loads(raw)
        payload.pop("mcp", None)
    except Exception:
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": "Invalid JSON payload"}}, status_code=400)
    user_id = request.headers.get("x-user-id") or payload.get("user")
    from .model_registry import list_models  # import inside the handler so monkeypatch works
    validation_result = validate_model_and_messages(payload, list_models_func=list_models, require_messages=True)
    if validation_result == "unknown_provider":
        return JSONResponse({"error": {"type": "validation_error", "code": "unknown_provider", "message": "Unknown remote provider for model"}}, status_code=501)
    if validation_result is not None:
        return validation_result
    # Step 2: Pydantic validation for business logic and docs
    try:
        req_obj = ChatCompletionRequest(**payload)
    except ValidationError as e:
        logger.debug("[ERROR] Pydantic validation error")
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": str(e)}} , status_code=400)
        if cached:
            logger.info(f"Cache hit for /v1/chat/completions user={user_id}")
            return JSONResponse(content=cached, status_code=200)
    # Remote/unsupported model stub logic
    try:
        classify_result = await provider_router.classify_prompt(payload.get("messages"))
        if classify_result == "remote":
            return JSONResponse({"error": {"type": "not_implemented", "code": "not_implemented", "message": "Remote model routing not implemented in test stub."}}, status_code=501)
    except Exception as e:
        return JSONResponse({"error": {"type": "service_unavailable", "code": "classifier_error", "message": str(e)}}, status_code=503)
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
async def completions(request: Request):
    import logging
    from pydantic import ValidationError
    logger = logging.getLogger("iir.proxy")
    # Step 1: Parse raw JSON and validate error contract
    try:
        raw = await request.body()
        payload = json.loads(raw)
        payload.pop("mcp", None)
    except Exception:
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": "Invalid JSON payload"}}, status_code=400)
    user_id = request.headers.get("x-user-id") or payload.get("user")
    from router.model_registry import list_models
    validation_result = validate_model_and_messages(payload, list_models_func=list_models, require_messages=True)
    logger.debug(f"Validation result: {validation_result}")
    if validation_result == "unknown_provider":
        logger.debug("Returning 501 for unknown provider")
        return JSONResponse({"error": {"type": "validation_error", "code": "unknown_provider", "message": "Unknown remote provider for model"}}, status_code=501)
    if validation_result is not None:
        status = getattr(validation_result, 'status_code', None)
        logger.debug(f"Returning error response with status {status}")
        return validation_result
    # Step 2: Pydantic validation for business logic and docs
    try:
        req_obj = CompletionRequest(**payload)
    except ValidationError as e:
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": str(e)}} , status_code=400)
    # Hybrid validation approach: 
    # 1. Validate error contract with validate_model_and_messages
    # 2. Validate business logic and docs with Pydantic CompletionRequest
    # If both validations pass, proceed as before
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

