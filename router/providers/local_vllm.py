# Local vLLM provider for IIR MVP
import httpx
from router.settings import get_settings

settings = get_settings()

from router.provider_clients.base import ProviderResponse

async def generate_local(payload: dict) -> ProviderResponse:
    url = f"{settings.vllm_base_url}/v1/chat/completions"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = await resp.json()
        return ProviderResponse(status_code=resp.status_code, content=data)

