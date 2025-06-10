"""Base classes for provider implementations."""

from __future__ import annotations

from ..schemas import ChatCompletionRequest


class ApiProvider:
    """Base class for providers that forward requests to external APIs."""

    async def forward(
        self,
        payload: ChatCompletionRequest,
        base_url: str,
        api_key: str | None,
    ):
        """Forward a chat completion request."""
        raise NotImplementedError


class WeightProvider:
    """Base class for providers that load local model weights."""

    async def forward(
        self,
        payload: ChatCompletionRequest,
        base_url: str,
    ):
        """Perform inference using local weights."""
        raise NotImplementedError
