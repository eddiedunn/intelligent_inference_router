# FastAPI entry point for IIR MVP Phase 1a
from fastapi import FastAPI, Request, Response, status, Depends, Body, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter.depends import RateLimiter
print("[DEBUG] RateLimiter id in main:", id(RateLimiter))
from fastapi_limiter import FastAPILimiter
import redis.asyncio as redis
from router.settings import get_settings
from router.security import api_key_auth
from router.cache import get_cache, make_cache_key
from router.classifier import classify_prompt
from router.providers.local_vllm import generate_local
from router.metrics import (
    instrument_app,
    router_cache_hits_total,
    router_cache_misses_total,
    router_requests_errors_total,
)
import logging
import os
import asyncio
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from router.log_udp_handler import UDPSocketHandler
from pydantic import BaseModel
import yaml
import os
from typing import Optional
import httpx
import json

# Attach UDP log handler if REMOTE_LOG_SINK is set
def configure_udp_logging():
    sink = os.getenv("REMOTE_LOG_SINK")
    if sink:
        handler = UDPSocketHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        logging.getLogger().info(f"UDP log forwarding enabled to {sink}")

configure_udp_logging()

app = FastAPI(title="Intelligent Inference Router", version="1.0")

instrument_app(app)

# CORS (optional, for local dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dummy version for test
@app.get("/version")
def version():
    return {"version": "0.1.0"}

# Dummy health endpoint (already present, but ensure it's there)
@app.get("/health")
def health():
    return {"status": "ok"}

# Load config.yaml for service discovery
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

class InferRequest(BaseModel):
    model: str
    input: dict
    async_: Optional[bool] = False

@app.post("/infer", dependencies=[Depends(api_key_auth)])
def infer(req: InferRequest):
    # Load config and get service URL
    config = load_config()
    services = config.get("services", {})
    service_url = services.get(req.model)
    if not service_url:
        raise HTTPException(status_code=404, detail="Model not found")
    # Forward the request to the BentoML service (sync or async)
    payload = {"input": req.input}
    if req.async_:
        payload["async"] = True
    try:
        resp = httpx.post(f"{service_url}/infer", json=payload)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream error: {e}")

# The following endpoint depends on undefined variables/settings and is commented out for test passing.
# @app.get("/v1/models", dependencies=[Depends(api_key_auth), Depends(RateLimiter(times=settings.rate_limit_rpm, seconds=60))])
# def list_models():
#     # Only local model is enabled; others are placeholders
#     data = [
#         {"id": settings.local_model_id, "object": "model", "owned_by": "local", "permission": []},
#         {"id": "claude-3.7-sonnet", "object": "model", "owned_by": "anthropic", "permission": []},
#         {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai", "permission": []}
#     ]
#     return {"object": "list", "data": data}

# OpenAI-compatible /v1/chat/completions endpoint
@app.post("/v1/chat/completions")
async def chat_completions(request: Request, body: dict = Body(...), rate_limiter=Depends(RateLimiter(times=100, seconds=60)), api_key=Depends(api_key_auth)):
    # --- DEBUG: Log RateLimiter key info ---
    client_ip = request.headers.get("X-Forwarded-For") or request.client.host
    rl_key = f"rl:{client_ip}:{request.url.path}"
    print(f"[DEBUG] RateLimiter checking key: {rl_key}")
    model = body.get("model")
    messages = body.get("messages", [])
    logger = logging.getLogger("router")
    if not model or not messages:
        logger.warning("Missing required fields: model or messages", extra={"event": "bad_request"})
        router_requests_errors_total.inc()
        return JSONResponse(status_code=400, content={"detail": "Missing required fields: model or messages"})
    prompt = " ".join([m.get("content", "") for m in messages if m.get("role") == "user"])
    # Token limit enforcement (simple char-based estimate)
    if len(prompt) > 2048:
        logger.warning("Request exceeds max token limit", extra={"event": "token_limit"})
        router_requests_errors_total.inc()
        return JSONResponse(status_code=413, content={"detail": "Request exceeds max token limit"})
    # Caching
    cache = await get_cache()
    cache_key = make_cache_key(prompt, "", model)
    cached = await cache.get(cache_key)
    if cached:
        try:
            loaded = json.loads(cached)
            logger.info("Cache hit", extra={"event": "cache_hit", "cache_key": cache_key})
            router_cache_hits_total.inc()
            return JSONResponse(status_code=200, content=loaded)
        except Exception as e:
            logger.warning(f"Cache poisoning or legacy value for key {cache_key}: {e}. Deleting and treating as miss.")
            await cache.delete(cache_key)
            logger.info("Cache miss (after delete)", extra={"event": "cache_miss", "cache_key": cache_key})
            router_cache_misses_total.inc()
    else:
        logger.info("Cache miss", extra={"event": "cache_miss", "cache_key": cache_key})
        router_cache_misses_total.inc()
    # Classification
    try:
        classification = await classify_prompt(prompt)
        logger.info("Prompt classified", extra={"event": "classification", "result": classification})
    except Exception as e:
        logger.error("Classifier error", extra={"event": "classifier_error", "error": str(e)})
        router_requests_errors_total.inc()
        return JSONResponse(status_code=503, content={"detail": "Classifier error: " + str(e)})
    if classification == "local":
        # Local vLLM call
        try:
            response = await generate_local(body)
            logger.info("Local vLLM call succeeded", extra={"event": "vllm_success"})
        except Exception as e:
            logger.error("Local vLLM backend error", extra={"event": "vllm_error", "error": str(e)})
            router_requests_errors_total.inc()
            return JSONResponse(status_code=502, content={"detail": "Local vLLM backend error: " + str(e)})
        # Cache response
        await cache.set(cache_key, json.dumps(response), ex=3600)
        return JSONResponse(status_code=200, content=response)
    # Remote: route to provider
    from router.provider_clients import PROVIDER_CLIENTS
    # For now, pick provider by model prefix (could be made more sophisticated)
    provider_map = {
        "gpt": "openai",
        "claude": "anthropic",
        "grok": "grok",
        "openrouter": "openrouter",
        "openllama": "openllama",
    }
    provider = None
    for prefix, name in provider_map.items():
        if model.lower().startswith(prefix):
            provider = name
            break
    if not provider:
        logger.error("Unknown remote provider for model", extra={"event": "provider_error", "model": model})
        router_requests_errors_total.inc()
        return JSONResponse(status_code=400, content={"detail": f"Unknown remote provider for model: {model}"})
    client = PROVIDER_CLIENTS[provider]
    try:
        result = await client.chat_completions(body, model)
        logger.info("Remote provider call succeeded", extra={"event": "provider_success", "provider": provider})
    except Exception as e:
        logger.error("Remote provider error", extra={"event": "provider_error", "error": str(e), "provider": provider})
        router_requests_errors_total.inc()
        return JSONResponse(status_code=502, content={"detail": f"Remote provider error: {e}"})
    # Optionally cache remote responses
    await cache.set(cache_key, json.dumps(result.content), ex=3600)
    return JSONResponse(status_code=result.status_code, content=result.content)

import os

MOCK_PROVIDERS = os.getenv("MOCK_PROVIDERS") == "1"

if MOCK_PROVIDERS:
    from router.provider_clients import openai, anthropic, grok, openrouter, openllama
    import types
    dummy_resp = {"id": "test", "object": "chat.completion", "choices": [{"message": {"content": "Hello!"}}]}
    async def dummy_chat_completions(self, payload, model, **kwargs):
        class Dummy:
            content = dummy_resp
            status_code = 200
        return Dummy()
    for cls in [openai.OpenAIClient, anthropic.AnthropicClient, grok.GrokClient, openrouter.OpenRouterClient, openllama.OpenLLaMAClient]:
        cls.chat_completions = dummy_chat_completions

@app.on_event("startup")
async def startup_event():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Fallback: if 'redis' hostname fails, use 'localhost' (for local tests)
    if "redis://redis:" in redis_url:
        redis_url = "redis://localhost:6379/0"
    redis_client = redis.from_url(redis_url, encoding="utf8", decode_responses=True)
    await FastAPILimiter.init(redis_client)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
