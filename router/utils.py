from __future__ import annotations

from typing import AsyncIterator

import httpx


async def stream_resp(resp: httpx.Response) -> AsyncIterator[str]:
    """Yield chunks from a streaming HTTP response."""
    async for chunk in resp.aiter_text():
        yield chunk
