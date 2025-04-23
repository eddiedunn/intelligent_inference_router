# FastAPI entry point for IIR MVP Phase 1a
from fastapi import FastAPI, Request, Response, status, Depends, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter.depends import RateLimiter
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

@app.get("/health")
def health():
    return {"status": "ok"}

settings = get_settings()

# OpenAI-compatible /v1/models endpoint
@app.get("/v1/models", dependencies=[Depends(api_key_auth), Depends(RateLimiter(times=settings.rate_limit_rpm, seconds=60))])
def list_models():
    # Only local model is enabled; others are placeholders
    data = [
        {"id": settings.local_model_id, "object": "model", "owned_by": "local", "permission": []},
        {"id": "claude-3.7-sonnet", "object": "model", "owned_by": "anthropic", "permission": []},
        {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai", "permission": []}
    ]
    return {"object": "list", "data": data}

# OpenAI-compatible /v1/chat/completions endpoint
@app.post("/v1/chat/completions", dependencies=[Depends(api_key_auth), Depends(RateLimiter(times=settings.rate_limit_rpm, seconds=60))])
async def chat_completions(request: Request, body: dict = Body(...)):
    model = body.get("model")
    messages = body.get("messages", [])
    logger = logging.getLogger("router")
    if not model or not messages:
        logger.warning("Missing required fields: model or messages", extra={"event": "bad_request"})
        router_requests_errors_total.inc()
        return JSONResponse(status_code=400, content={"detail": "Missing required fields: model or messages"})
    if model != settings.local_model_id:
        logger.info(f"Remote model requested: {model}", extra={"event": "remote_model"})
        router_requests_errors_total.inc()
        return JSONResponse(status_code=501, content={"detail": "Remote/external models not implemented in Phase 1a"})
    prompt = " ".join([m.get("content", "") for m in messages if m.get("role") == "user"])
    # Token limit enforcement (simple char-based estimate)
    if len(prompt) > settings.max_request_tokens * 4:
        logger.warning("Request exceeds max token limit", extra={"event": "token_limit"})
        router_requests_errors_total.inc()
        return JSONResponse(status_code=413, content={"detail": "Request exceeds max token limit"})
    # Caching
    cache = await get_cache()
    cache_key = make_cache_key(prompt, "", model)
    cached = await cache.get(cache_key)
    if cached:
        logger.info("Cache hit", extra={"event": "cache_hit", "cache_key": cache_key})
        router_cache_hits_total.inc()
        return JSONResponse(status_code=200, content=eval(cached))
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
    if classification != "local":
        logger.info("Remote path returned (not implemented)", extra={"event": "remote_path"})
        router_requests_errors_total.inc()
        return JSONResponse(status_code=501, content={"detail": "Remote path not implemented in Phase 1a"})
    # Local vLLM call
    try:
        response = await generate_local(body)
        logger.info("Local vLLM call succeeded", extra={"event": "vllm_success"})
    except Exception as e:
        logger.error("Local vLLM backend error", extra={"event": "vllm_error", "error": str(e)})
        router_requests_errors_total.inc()
        return JSONResponse(status_code=502, content={"detail": "Local vLLM backend error: " + str(e)})
    # Cache response
    await cache.set(cache_key, str(response), ex=settings.cache_ttl_seconds)
    return JSONResponse(status_code=200, content=response)

@app.on_event("startup")
async def startup_event():
    redis_url = os.getenv("REDIS_URL", "redis://iir-redis:6379/0")
    redis_client = await redis.from_url(redis_url, encoding="utf8", decode_responses=True)
    await FastAPILimiter.init(redis_client)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
