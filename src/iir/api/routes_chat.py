"""POST /v1/chat/completions — the main endpoint."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from iir.api.errors import upstream_error, validation_error
from iir.api.schemas import ChatCompletionRequest
from iir.bifrost_client.client import BifrostClient
from iir.dependencies import get_api_key, get_bifrost, get_routing_engine
from iir.routing.engine import RoutingEngine

logger = logging.getLogger("iir.api.chat")

router = APIRouter(prefix="/v1")


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    _api_key: str = Depends(get_api_key),
    engine: RoutingEngine = Depends(get_routing_engine),
    bifrost: BifrostClient = Depends(get_bifrost),
) -> Any:
    # Read routing hints from headers
    strategy = request.headers.get("X-Routing-Strategy")
    max_cost_header = request.headers.get("X-Max-Cost")
    max_cost = float(max_cost_header) if max_cost_header else None

    # Route the request
    messages = [m.model_dump() for m in body.messages]
    decision = await engine.route(
        messages=messages,
        strategy=strategy,
        explicit_model=body.model,
        max_cost=max_cost,
        tools=body.tools,
    )

    # Build the payload for Bifrost
    payload = body.model_dump(exclude_none=True)
    payload["model"] = decision.model

    # Proxy to Bifrost
    try:
        resp = await bifrost.chat_completion(payload)
    except Exception as exc:
        logger.error("Bifrost request failed: %s", exc)
        return upstream_error(f"Gateway error: {exc}")

    if resp.status_code >= 400:
        return JSONResponse(status_code=resp.status_code, content=resp.json())

    # Build response with routing metadata headers
    response_data = resp.json()
    response = JSONResponse(content=response_data)
    response.headers["X-Route-Model"] = decision.model
    response.headers["X-Route-Provider"] = decision.provider
    response.headers["X-Route-Reason"] = decision.reason
    response.headers["X-Classification"] = decision.category
    if decision.estimated_cost_per_1m > 0:
        response.headers["X-Estimated-Cost-Per-1M"] = f"{decision.estimated_cost_per_1m:.4f}"

    return response
