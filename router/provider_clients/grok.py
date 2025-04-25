import os
import httpx
from .base import ProviderClient, ProviderResponse

class GrokClient(ProviderClient):
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        self.base_url = os.getenv("GROK_API_BASE", "https://api.grok.x.ai/v1")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat_completions(self, payload, model, **kwargs):
        url = f"{self.base_url}/chat/completions"
        payload = dict(payload)
        payload["model"] = model
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self.headers, json=payload)
        return ProviderResponse(content=resp.json(), raw_response=resp, status_code=resp.status_code)

    async def completions(self, payload, model, **kwargs):
        url = f"{self.base_url}/completions"
        payload = dict(payload)
        payload["model"] = model
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self.headers, json=payload)
        return ProviderResponse(content=resp.json(), raw_response=resp, status_code=resp.status_code)
