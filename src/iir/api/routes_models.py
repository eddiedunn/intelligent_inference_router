"""GET /v1/models endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from iir.dependencies import get_api_key, get_routing_engine
from iir.routing.engine import RoutingEngine

router = APIRouter(prefix="/v1")


@router.get("/models")
async def list_models(
    _api_key: str = Depends(get_api_key),
    engine: RoutingEngine = Depends(get_routing_engine),
) -> dict:
    models = engine.registry.list_models()
    return {
        "object": "list",
        "data": [
            {
                "id": m.id,
                "object": "model",
                "provider": m.provider,
                "capabilities": m.capabilities,
                "quality_tier": m.quality_tier,
                "supports_vision": m.supports_vision,
                "supports_tools": m.supports_tools,
                "cost_per_1m_input_tokens": m.cost_per_1m_input,
                "cost_per_1m_output_tokens": m.cost_per_1m_output,
            }
            for m in models
        ],
    }
