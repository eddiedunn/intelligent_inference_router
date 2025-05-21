import sys
print('[DEBUG] IMPORT: openai_routes.py loaded'); sys.stdout.flush()
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from .validation_utils import (
    validate_required_fields,
    validate_model_format,
    validate_messages,
    validate_token_limit,
    validate_model_registry,
    InvalidPayloadError,
    InvalidModelFormatError,
    UnknownProviderError,
    InvalidMessagesError,
    TokenLimitExceededError,
    RegistryUnavailableError,
)
# (Retain validate_model_and_messages import for now if needed elsewhere)

from .openai_models import (
    ChatCompletionRequest, ChatCompletionResponse, OpenAIErrorResponse,
    CompletionRequest, CompletionResponse
)
from typing import AsyncGenerator
import time
import json  # Ensure json is imported
import sys

router = APIRouter()
import sys
from .main import rate_limiter_dep
print(f'[DEBUG ROUTES] id(rate_limiter_dep) in openai_routes top = {id(rate_limiter_dep)}'); sys.stdout.flush()

# --- Chat Completions Endpoint ---
import httpx
import logging
logger = logging.getLogger("iir.openai_routes")
import os
import yaml
from .provider_router import ProviderRouter

# Load config once (in production, reload on SIGHUP or use a config service)
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.example.yaml")
with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)
# Dependency to retrieve provider_router from app.state
from fastapi import Request

def get_provider_router(request: Request):
    return request.app.state.provider_router

from router.main import rate_limiter_dep

@router.post("/v1/chat/completions", response_model=None, responses={400: {"model": OpenAIErrorResponse}})
async def chat_completions(
    request: Request,
    rate_limiter=Depends(rate_limiter_dep),
    test_force_error: str = Depends(lambda: None),  # test-only slot for forced error short-circuiting
    provider_router=Depends(get_provider_router),
):
    print(f'[DEBUG ROUTES] id(rate_limiter_dep) in chat_completions = {id(rate_limiter_dep)}'); import sys; sys.stdout.flush()
    print('[DEBUG] TOP OF chat_completions endpoint'); import sys; sys.stdout.flush()
    print("[DEBUG] ENTERED /v1/chat/completions endpoint"); sys.stdout.flush()
    # Parse JSON body
    try:
        raw = await request.body()
        payload = json.loads(raw)
    except Exception as e:
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": "Invalid JSON payload"}}, status_code=400)

    user_id = request.headers.get("x-user-id") or payload.get("user")
    from .model_registry import list_models  # import inside the handler so monkeypatch works
    # --- Modular Validation Chain ---
    try:
        validate_required_fields(payload)
        provider, model_name = validate_model_format(payload["model"])
        messages = validate_messages(payload["messages"])
        validate_model_registry(payload["model"], list_models)
        validate_token_limit(messages, token_limit=1000)
    except InvalidPayloadError as e:
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": str(e)}}, status_code=400)
    except InvalidModelFormatError as e:
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_model_format", "message": str(e)}}, status_code=400)
    except InvalidMessagesError as e:
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": str(e)}}, status_code=400)
    except TokenLimitExceededError as e:
        return JSONResponse({"error": {"type": "validation_error", "code": "token_limit_exceeded", "message": str(e)}}, status_code=413)
    except UnknownProviderError as e:
        return JSONResponse({"error": {"type": "validation_error", "code": "unknown_provider", "message": str(e)}}, status_code=400)
    except RegistryUnavailableError as e:
        return JSONResponse({"error": {"type": "service_unavailable", "code": "model_registry_unavailable", "message": str(e)}}, status_code=503)

    # Step 2: Pydantic validation for business logic and docs
    try:
        req_obj = ChatCompletionRequest(**payload)
        print("[DEBUG] After pydantic validation"); sys.stdout.flush()
    except Exception as e:
        print("[DEBUG] RETURNING 400 after pydantic validation"); sys.stdout.flush()
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": str(e)}}, status_code=400)

    # Step 2: Pydantic validation for business logic and docs
    try:
        req_obj = ChatCompletionRequest(**payload)
        print("[DEBUG] After pydantic validation"); sys.stdout.flush()
    except Exception as e:
        print("[DEBUG] RETURNING 400 after pydantic validation"); sys.stdout.flush()
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": str(e)}}, status_code=400)
    # --- AUTHENTICATION CHECK (must pass before classify_prompt/provider selection) ---
    from router.security import api_key_auth
    try:
        await api_key_auth(request)
    except HTTPException as auth_exc:
        print(f"[DEBUG] AUTH ERROR: {auth_exc.detail}"); sys.stdout.flush()
        return JSONResponse({"error": {"type": "authentication_error", "code": "unauthorized", "message": auth_exc.detail}}, status_code=auth_exc.status_code)
    # Remote/unsupported model stub logic
    try:
        print("[DEBUG] Before classify_prompt"); sys.stdout.flush()
        classify_result = await provider_router.classify_prompt(payload.get("messages"))
        print("[DEBUG] After classify_prompt"); sys.stdout.flush()
        if classify_result == "remote":
            print("[DEBUG] RETURNING 501 for remote model"); sys.stdout.flush()
            return JSONResponse({"error": {"type": "not_implemented", "code": "not_implemented", "message": "Remote model routing not implemented in test stub."}}, status_code=501)
    except HTTPException as e:
        raise  # Always propagate HTTPException
    except Exception as e:
        print("[DEBUG] classify_prompt error, returning 400"); sys.stdout.flush()
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_prompt_classification", "message": f"Prompt classification failed: {str(e)}"}}, status_code=400)

    # Provider selection (unknown provider/model handling)
    try:
        provider_url, headers, provider_name = provider_router.select_provider(payload, user_id)
    except Exception as e:
        print("[DEBUG] Unknown provider/model error"); sys.stdout.flush()
        return JSONResponse({"error": {"type": "validation_error", "code": "unknown_provider", "message": str(e)}}, status_code=400)
    print("[DEBUG] After provider selection"); sys.stdout.flush()

    logger.info(f"Proxying /v1/chat/completions to {provider_url} with model {payload['model']} user={user_id}")
    # Patch: For openrouter, strip provider prefix from model name before calling client
    model_arg = payload["model"]
    if provider_name == "openrouter" and "/" in model_arg:
        model_arg = model_arg.split("/", 1)[1]
    print("[DEBUG] Before DummyClient/httpx call"); sys.stdout.flush()
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            if payload.get("stream"):
                r = await client.post(provider_url, json=payload, headers=headers, stream=True)
                return StreamingResponse(r.aiter_raw(), media_type="text/event-stream")
            else:
                r = await client.post(provider_url, json=payload, headers=headers)
                # Define cache_key for caching (stub for test)
                cache_key = f"chat:{payload.get('model','')}:{user_id or 'dummy'}"
                await provider_router.cache_set(cache_key, await r.json(), ttl=CONFIG.get("caching", {}).get("ttl", 60))
                provider_router.record_usage(provider_name, user_id, tokens=0)
                return JSONResponse(content=await r.json(), status_code=r.status_code)
        except HTTPException as e:
            raise  # Always propagate HTTPException
        except Exception as e:
            import traceback
            print(f"[DEBUG] Exception in endpoint: {type(e)} {e}")
            traceback.print_exc()
            if isinstance(e, HTTPException):
                raise
            logger.error(f"Unhandled error in proxy: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "type": "service_unavailable",
                        "code": "proxy_error",
                        "message": str(e)
                    }
                },
            )

# --- Completions Endpoint ---
@router.post("/v1/completions", response_model=None, responses={400: {"model": OpenAIErrorResponse}})
async def completions(request: Request):
    print("[DEBUG] ENTERED /v1/completions endpoint")
    import logging
    from pydantic import ValidationError
    logger = logging.getLogger("iir.proxy")
    # Step 1: Parse raw JSON and validate error contract
    try:
        raw = await request.body()
        payload = json.loads(raw)
        payload.pop("mcp", None)
    except Exception as e:
        print(f"[DEBUG] Exception during payload parse: {type(e)} {e}")
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": "Invalid JSON payload"}}, status_code=400)
    user_id = request.headers.get("x-user-id") or payload.get("user")
    from router.model_registry import list_models
    # NOTE: Rate limiter (429) errors take precedence and will be raised before this point if triggered.
    validation_result = validate_model_and_messages(payload, list_models_func=list_models, require_messages=True)
    logger.debug(f"Validation result: {validation_result}")
    if validation_result is not None:
        logger.debug(f"Returning error response with status {getattr(validation_result, 'status_code', None)}")
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
    # Patch: For openrouter, strip provider prefix from model name before calling client
    model_arg = payload["model"]
    if provider_name == "openrouter" and "/" in model_arg:
        model_arg = model_arg.split("/", 1)[1]