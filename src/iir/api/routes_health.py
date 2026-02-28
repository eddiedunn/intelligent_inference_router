"""Health, version, and metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from iir import __version__

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    bifrost_ok = await request.app.state.bifrost.health()
    return {
        "status": "ok" if bifrost_ok else "degraded",
        "bifrost": "connected" if bifrost_ok else "unreachable",
    }


@router.get("/version")
async def version() -> dict:
    return {"version": __version__}


@router.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
