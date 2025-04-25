import os
import httpx
from .base import ProviderClient, ProviderResponse

class AnthropicClient(ProviderClient):
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.base_url = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1")
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def chat_completions(self, payload, model, **kwargs):
        url = f"{self.base_url}/messages"
        payload = dict(payload)
        payload["model"] = model
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            data = await resp.json()
            return ProviderResponse(status_code=resp.status_code, content=data)

    async def completions(self, payload, model, **kwargs):
        # Anthropic may not support /completions; treat as not implemented
        raise NotImplementedError("Anthropic does not support /completions endpoint.")
