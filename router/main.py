import os
print("[DEBUG] Startup: IIR_API_KEY =", os.environ.get("IIR_API_KEY"))
from typing import Dict
from fastapi import FastAPI, Request, Response, status, Depends, Body, HTTPException, BackgroundTasks
from fastapi.exception_handlers import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
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
from router.metrics import instrument_app, get_metrics
import logging
logger = logging.getLogger("router.main")
import os
import asyncio
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from router.log_udp_handler import UDPSocketHandler
from pydantic import BaseModel
import yaml
import os
from typing import Optional, AsyncGenerator
import httpx
import json
import types
import uuid
from router.model_registry import list_models, rebuild_db
from router.registry_status import load_registry_status, save_registry_status

# Attach UDP log handler if REMOTE_LOG_SINK is set
def configure_udp_logging():
    sink = os.getenv("REMOTE_LOG_SINK")
    if sink:
        handler = UDPSocketHandler()
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)
        logging.getLogger().info(f"UDP log forwarding enabled to {sink}")

# --- Dependency for testable rate limiter ---
def get_rate_limiter():
    print("[DEBUG] ENTRY: get_rate_limiter dependency called")
    try:
        from fastapi_limiter.depends import RateLimiter
        print("[DEBUG] fastapi_limiter.depends.RateLimiter imported successfully")
        limiter = RateLimiter(times=200, seconds=60)
        print(f"[DEBUG] RateLimiter instantiated: {limiter}")
        return limiter
    except Exception as e:
        import traceback
        print(f"[DEBUG] ERROR in get_rate_limiter: {e}")
        traceback.print_exc()
        raise

from starlette.responses import Response
async def rate_limiter_dep(request: Request):
    print("[DEBUG] rate_limiter_dep called")
    limiter = get_rate_limiter()
    # Print the Redis key used for this request
    key_func = getattr(limiter, 'key_func', None)
    if key_func:
        key = await key_func(request)
        print(f"[DEBUG] RateLimiter key for this request: {key}")
    else:
        print(f"[DEBUG] RateLimiter has no key_func attribute! Limiter class: {limiter.__class__.__name__}, dir: {dir(limiter)}")
        # Print the identifier attribute if present
        identifier = getattr(limiter, 'identifier', None)
        print(f"[DEBUG] RateLimiter identifier attribute: {identifier}")
        # Try to inspect other possible attributes or methods for key extraction
        # If you know the attribute/method for your fastapi-limiter version, add it here

    dummy_response = Response()
    try:
        await limiter(request, dummy_response)
    except HTTPException as e:
        print(f"[DEBUG] rate_limiter_dep raising HTTPException: {e.status_code} {e.detail}")
        raise
    except Exception as e:
        print(f"[DEBUG] rate_limiter_dep caught non-HTTPException: {e}")
        raise

# --- App Factory for Testability ---
def create_app(metrics_registry=None):
    print("[DEBUG] Entering create_app (TOP)")
    try:
        print("[DEBUG] create_app: before configure_udp_logging")
        configure_udp_logging()
        print("[DEBUG] create_app: after configure_udp_logging, before FastAPI init")
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            if "redis://redis:" in redis_url:
                redis_url = "redis://localhost:6379/0"
            redis_client = await redis.from_url(redis_url, encoding="utf8", decode_responses=True)
            await FastAPILimiter.init(redis_client)
            yield
            redis_client = FastAPILimiter.redis
            if redis_client:
                await redis_client.close()
        app = FastAPI(title="Intelligent Inference Router", version="1.0", lifespan=lifespan)
        print("[DEBUG] create_app: after FastAPI init")

        # --- Always register /api/v1/apikeys endpoint on this app instance ---
        from fastapi import Request
        @app.post("/api/v1/apikeys")
        async def register_apikey(request: Request, registration: APIKeyRegistrationRequest = Body(...)):
            new_key = secrets.token_urlsafe(32)
            ip = request.client.host if request.client else "unknown"
            add_api_key(new_key, ip, registration.description, registration.priority)
            metrics = get_apikey_metrics(metrics_registry)
            metrics['registrations_total'].inc()
            return {"api_key": new_key, "description": registration.description, "priority": registration.priority}

        # Debug: Print all registered routes
        print("[DEBUG] Registered routes:")
        for route in app.routes:
            print(f"[DEBUG] Route: {getattr(route, 'path', None)} -> {getattr(route, 'endpoint', None)}")

        print("[DEBUG] create_app: before configure_udp_logging")
        configure_udp_logging()
        print("[DEBUG] create_app: after configure_udp_logging, before FastAPI init")
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            if "redis://redis:" in redis_url:
                redis_url = "redis://localhost:6379/0"
            redis_client = await redis.from_url(redis_url, encoding="utf8", decode_responses=True)
            await FastAPILimiter.init(redis_client)
            yield
            redis_client = FastAPILimiter.redis
            if redis_client:
                await redis_client.close()
        app = FastAPI(title="Intelligent Inference Router", version="1.0", lifespan=lifespan)
        print("[DEBUG] create_app: after FastAPI init")

        print("[DEBUG] create_app: before health endpoint")
        @app.get("/health")
        def health():
            return {"status": "ok"}
        print("[DEBUG] create_app: after health endpoint")

        @app.get("/version")
        def version():
            return {"version": "1.0"}

        print("[DEBUG] create_app: before /infer endpoint")
        @app.post("/infer", dependencies=[Depends(api_key_auth), Depends(rate_limiter_dep)])
        async def infer(req: InferRequest = Body(...)):
            # HYBRID SCRUB INCOMING REQUEST
            safe_req = hybrid_scrub_and_log(req.model_dump(), direction="incoming /infer request")
            # Load config and get service URL
            config = load_config()
            services = config.get("services", {})
            from router.providers import parse_provider_and_model
            try:
                provider, model_name = parse_provider_and_model(safe_req['model'])
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid model string: {e}")
            if safe_req['model'] not in services:
                raise HTTPException(status_code=404, detail="Model not found")
            service_url = services[safe_req['model']]
            # Forward the request to the BentoML service (sync or async)
            payload = {"input": safe_req['input']}
            if safe_req.get('async_'):
                payload["async"] = True
            try:
                resp = httpx.post(f"{service_url}/infer", json=payload)
                # HYBRID SCRUB OUTGOING RESPONSE
                safe_content = hybrid_scrub_and_log(resp.json(), direction="outgoing /infer response")
                return JSONResponse(content=safe_content, status_code=resp.status_code)
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Upstream error: {e}")
        print("[DEBUG] create_app: after /infer endpoint")

        # --- OpenAI-compatible proxy endpoints ---
        from .openai_routes import router as openai_router, set_provider_router
        app.include_router(openai_router)

        @app.on_event("startup")
        async def startup_event():
            import yaml
            from .provider_router import ProviderRouter
            from .cache import get_cache, SimpleCache
            config_path = os.path.join(os.path.dirname(__file__), "config.example.yaml")
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            try:
                cache_backend = await get_cache()
                cache_type = 'redis'
            except Exception as e:
                import logging
                logging.getLogger("iir.startup").warning(f"Redis unavailable, falling back to SimpleCache: {e}")
                cache_backend = SimpleCache()
                cache_type = 'simple'
            provider_router = ProviderRouter(config, cache_backend, cache_type)
            app.state.provider_router = provider_router
            set_provider_router(provider_router)

        print("[DEBUG] create_app: before metrics setup")
        metrics = get_metrics(registry=metrics_registry)
        instrument_app(app, metrics=metrics)
        print("[DEBUG] create_app: after metrics setup, before CORS")

        # CORS (optional, for local dev)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        print("[DEBUG] create_app: after CORS setup, before /v1/chat/completions")
        print("[DEBUG] create_app: about to register /v1/chat/completions endpoint")

        @app.middleware("http")
        async def log_requests(request: Request, call_next):
            try:
                body = await request.body()
            except Exception as e:
                body = f"[ERROR reading body: {e}]"
            print(f"[DEBUG] MIDDLEWARE: Incoming request path={request.url.path} body={body}")
            response = await call_next(request)
            return response

        @app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            import traceback
            logger.error(f"[DEBUG] GLOBAL EXCEPTION: {type(exc)}: {exc}", exc_info=True)
            print(f"[DEBUG] GLOBAL EXCEPTION: {type(exc)}: {exc}")
            traceback.print_exc()
            return JSONResponse(status_code=502, content={"detail": "Internal Server Error"})

        @app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request, exc):
            # If the cause is an HTTPException with status 429, propagate it as 429
            # (FastAPI wraps dependency exceptions as RequestValidationError, but does not preserve the original status)
            # We check for this by inspecting the request path and error details
            for err in exc.errors():
                if err.get('msg') == 'Rate limit exceeded' or err.get('type') == 'value_error' and 'rate limit' in str(err.get('msg', '')).lower():
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded"}
                    )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "message": "Invalid request payload.",
                        "type": "invalid_request_error",
                        "param": None,
                        "code": "invalid_payload",
                        "details": exc.errors(),
                    }
                },
            )

        @app.exception_handler(HTTPException)
        async def http_exception_handler(request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )

        print("[DEBUG] create_app: before metrics setup")
        metrics = get_metrics(registry=metrics_registry)
        instrument_app(app, metrics=metrics)
        print("[DEBUG] create_app: after metrics setup, before CORS")

        # CORS (optional, for local dev)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        print("[DEBUG] create_app: after CORS setup")

        # --- API Key Registration (Industry Standard: /api/v1/apikeys) ---

        print("[DEBUG] REGISTERING /v1/chat/completions endpoint in create_app")
        # OpenAI-compatible /v1/chat/completions endpoint
        @app.post("/v1/chat/completions")
        async def chat_completions(request: Request, api_key=Depends(api_key_auth)):
            print(f"[DEBUG] HANDLER ENTRY: /v1/chat/completions, request={request}")
            await rate_limiter_dep(request)
            try:
                body = await request.json()
            except Exception:
                return JSONResponse(status_code=400, content={"error": {"message": "Invalid JSON payload.", "type": "invalid_request_error", "param": None, "code": "invalid_payload"}})

            # --- SCRUB INCOMING REQUEST FOR SECRETS ---
            scrubbed_body = hybrid_scrub_and_log(body, direction="incoming chat completion request")
            if scrubbed_body != body:
                print("[WARNING] Secret(s) detected and scrubbed from incoming inference request.")
            body = scrubbed_body

            model = body.get("model")
            from router.providers import parse_provider_and_model
            try:
                provider, model_name = parse_provider_and_model(model)
            except Exception as e:
                return JSONResponse(status_code=400, content={"error": {"message": str(e), "type": "invalid_request_error", "param": "model", "code": "invalid_model_name"}})

            from router.provider_clients import PROVIDER_CLIENTS
            client_obj = PROVIDER_CLIENTS.get(provider)
            if not client_obj:
                return JSONResponse(status_code=400, content={"error": {"message": f"Unknown or unconfigured provider: {provider}", "type": "invalid_request_error", "param": "model", "code": "unknown_provider"}})

            # Pass model_name to the client
            try:
                result = await client_obj.chat_completions(body, model_name)
                return JSONResponse(content=result.content, status_code=result.status_code)
            except Exception as e:
                print(f"[DEBUG] Exception in provider call: {e}")
                return JSONResponse(status_code=502, content={"error": {"message": f"Provider error: {str(e)}", "type": "server_error", "param": None, "code": None}})

        @app.post("/v1/completions")
        async def completions(request: Request, api_key=Depends(api_key_auth)):
            print(f"[DEBUG] HANDLER ENTRY: /v1/completions, request={request}")
            await rate_limiter_dep(request)
            try:
                body = await request.json()
            except Exception:
                return JSONResponse(status_code=400, content={"error": {"message": "Invalid JSON payload.", "type": "invalid_request_error", "param": None, "code": "invalid_payload"}})

            # --- SCRUB INCOMING REQUEST FOR SECRETS ---
            scrubbed_body = hybrid_scrub_and_log(body, direction="incoming completions request")
            if scrubbed_body != body:
                print("[WARNING] Secret(s) detected and scrubbed from incoming inference request.")
            body = scrubbed_body

            model = body.get("model")
            from router.providers import parse_provider_and_model
            try:
                provider, model_name = parse_provider_and_model(model)
            except Exception as e:
                return JSONResponse(status_code=400, content={"error": {"message": str(e), "type": "invalid_request_error", "param": "model", "code": "invalid_model_name"}})

            from router.provider_clients import PROVIDER_CLIENTS
            client_obj = PROVIDER_CLIENTS.get(provider)
            if not client_obj:
                return JSONResponse(status_code=400, content={"error": {"message": f"Unknown or unconfigured provider: {provider}", "type": "invalid_request_error", "param": "model", "code": "unknown_provider"}})

            # Pass model_name to the client
            try:
                result = await client_obj.completions(body, model_name)
                return JSONResponse(content=result.content, status_code=result.status_code)
            except Exception as e:
                print(f"[DEBUG] Exception in provider call: {e}")
                return JSONResponse(status_code=502, content={"error": {"message": f"Provider error: {str(e)}", "type": "server_error", "param": None, "code": None}})

        # Simple in-memory job store (replace with persistent store in production)
        ASYNC_JOB_STORE: Dict[str, Dict] = {}

        @app.post("/v1/async/chat/completions")
        async def submit_async_chat_completion(request: Request, background_tasks: BackgroundTasks):
            try:
                body = await request.json()
            except Exception:
                return JSONResponse(status_code=400, content={"detail": "Invalid JSON body."})
            # HYBRID SCRUB INCOMING REQUEST
            body = hybrid_scrub_and_log(body, direction="incoming async chat completion request")
            model = body.get("model")
            messages = body.get("messages")
            from router.providers import parse_provider_and_model
            try:
                provider, model_name = parse_provider_and_model(model)
            except Exception as e:
                return JSONResponse(status_code=400, content={"detail": str(e)})
            if not model or not messages:
                return JSONResponse(status_code=400, content={"detail": "Missing required fields: model or messages"})
            job_id = str(uuid.uuid4())
            ASYNC_JOB_STORE[job_id] = {"status": "pending", "result": None}
            async def run_job():
                await asyncio.sleep(1)  # Simulate async work
                # HYBRID SCRUB OUTGOING RESPONSE
                ASYNC_JOB_STORE[job_id]["status"] = "complete"
                result = {"id": job_id, "object": "chat.completion", "choices": [{"message": {"content": "Hello from async!"}}]}
                ASYNC_JOB_STORE[job_id]["result"] = hybrid_scrub_and_log(result, direction="outgoing async chat completion response")
            background_tasks.add_task(run_job)
            return {"job_id": job_id, "status": "pending"}

        @app.get("/v1/async/chat/completions/{job_id}")
        async def poll_async_chat_completion(job_id: str):
            job = ASYNC_JOB_STORE.get(job_id)
            if not job:
                return JSONResponse(status_code=404, content={"detail": "Job not found"})
            if job["status"] != "complete":
                return {"job_id": job_id, "status": job["status"]}
            return job["result"]

        @app.get("/v1/models")
        async def get_models(api_key=Depends(api_key_auth)):
            # Return available models from registry in OpenAI-compatible format
            models = list_models()["data"]
            # OpenAI format: [{"id": ..., "object": "model", "owned_by": <provider>, ...}]
            data = [
                {
                    "id": f"{m['provider']}/{m['id']}",
                    "object": "model",
                    "owned_by": m["provider"],
                    "permission": [],
                    # Optionally include extra metadata fields here
                }
                for m in models
            ]
            return {"object": "list", "data": data}

        @app.get("/v1/registry/status")
        async def registry_status():
            status = load_registry_status()
            if not status:
                return {"status": "not_initialized", "message": "Registry status not found. Please run a refresh."}
            return status

        @app.post("/v1/registry/refresh")
        async def refresh_registry():
            # On-demand registry rebuild (hardware/model discovery)
            rebuild_db()
            status = save_registry_status()
            return {"status": "ok", "message": "Model registry refreshed.", "registry_status": status}


        @app.get("/metrics")
        def metrics():
            return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

        print("[DEBUG] Returning app:", app)
        return app
    except Exception as e:
        print("[DEBUG] Exception in create_app:", e)
        import traceback; traceback.print_exc()
        raise

_apikey_metrics_cache = {}
def get_apikey_metrics(registry=None):
    from prometheus_client import Counter, REGISTRY
    if registry is None:
        registry = REGISTRY
    key = id(registry)
    if key in _apikey_metrics_cache:
        return _apikey_metrics_cache[key]
    metrics = {
        'registrations_total': Counter(
            'apikey_registrations_total',
            'Total API key registrations',
            registry=registry
        ),
        # Add more API key metrics here if needed
    }
    _apikey_metrics_cache[key] = metrics
    return metrics

def is_allowed_ip(ip_str):
    # Only allow 192.168.11.0/24
    import ipaddress
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip in ipaddress.ip_network('192.168.11.0/24')
    except Exception:
        return False

class APIKeyRegistrationRequest(BaseModel):
    description: Optional[str] = None
    priority: Optional[int] = 0

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

class InferRequest(BaseModel):
    model: str
    input: dict
    async_: Optional[bool] = False

    # The following endpoint depends on undefined variables/settings and is commented out for test passing.
    # @app.get("/v1/models", dependencies=[Depends(api_key_auth), Depends(RateLimiter(times=settings.rate_limit_rpm, seconds=60))])
    # def list_models():
    #     # Only local model is enabled; others are placeholders
    #     data = [
    #         {"id": settings.local_model_id, "object": "model", "owned_by": "local", "permission": []},
    #         {"id": "claude-3.7-sonnet", "object": "model", "owned_by": "anthropic", "permission": []},
    #         {"id": "gpt-4o-mini", "object": "model", "owned_by": "openai", "permission": []}

from router.secret_scrubber import scrub_data, find_secrets, gather_env_secrets
ENV_SECRETS = gather_env_secrets()

def hybrid_scrub_and_log(data, direction="incoming"):
    """
    Scrub secrets from data using hybrid utility. Log a warning if any secrets were found and scrubbed.
    """
    orig_str = str(data)
    scrubbed = scrub_data(data, ENV_SECRETS)
    # Detect if any secrets were found
    found = find_secrets(orig_str, ENV_SECRETS)
    if found:
        print(f"[WARNING] Secret(s) detected and scrubbed from {direction} data: count={len(found)}")
    return scrubbed

import secrets
from router.apikey_db import add_api_key

# For ASGI/uvicorn compatibility
app = create_app()

# Always register /api/v1/apikeys endpoint on the global app instance
from fastapi import Request
@app.post("/api/v1/apikeys")
async def register_apikey(request: Request, registration: 'APIKeyRegistrationRequest' = Body(...)):
    new_key = secrets.token_urlsafe(32)
    ip = request.client.host if request.client else "unknown"
    add_api_key(new_key, ip, registration.description, registration.priority)
    metrics = get_apikey_metrics()
    metrics['registrations_total'].inc()
    return {"api_key": new_key, "description": registration.description, "priority": registration.priority}

# Default app instance for production
if __name__ == "__main__":
    app = create_app()

