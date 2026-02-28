"""FastAPI dependency injection wiring."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from iir.auth.security import api_key_auth as _api_key_auth
from iir.bifrost_client.client import BifrostClient
from iir.routing.engine import RoutingEngine


async def get_api_key(request: Request) -> str:
    return await _api_key_auth(request)


def get_bifrost(request: Request) -> BifrostClient:
    return request.app.state.bifrost


def get_routing_engine(request: Request) -> RoutingEngine:
    return request.app.state.routing_engine


def get_cache(request: Request) -> Any:
    return request.app.state.cache
