print("[DEBUG] IMPORT: provider_clients/openai.py imported")

import os
import httpx
from .base import ProviderClient, ProviderResponse

class OpenAIClient(ProviderClient):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        print("[DEBUG] OpenAIClient api_key =", self.api_key)
        self.base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat_completions(self, payload, model, **kwargs):
        import traceback
        url = f"{self.base_url}/chat/completions"
        payload = dict(payload)
        payload["model"] = model
        print("[DEBUG] OpenAI payload:", payload)  # Debug: show payload sent to OpenAI
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, headers=self.headers, json=payload)
                print("[DEBUG] resp type:", type(resp))
                print("[DEBUG] resp.json type:", type(getattr(resp, "json", None)))
                # Always await resp.json() (httpx.AsyncClient returns coroutine)
                data = await resp.json()
                print("[DEBUG] OpenAI response:", data)  # Debug: show response from OpenAI
                return ProviderResponse(status_code=resp.status_code, content=data)
        except Exception as e:
            print("[ERROR] Exception in OpenAIClient.chat_completions:", e)
            traceback.print_exc()
            raise

    async def completions(self, payload, model, **kwargs):
        url = f"{self.base_url}/completions"
        payload = dict(payload)
        payload["model"] = model
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=self.headers, json=payload)
            data = await resp.json()
            return ProviderResponse(status_code=resp.status_code, content=data)
