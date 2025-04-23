# Local vLLM provider for IIR MVP
import httpx
from router.settings import get_settings

settings = get_settings()

async def generate_local(payload: dict) -> dict:
    url = f"{settings.vllm_base_url}/v1/chat/completions"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
