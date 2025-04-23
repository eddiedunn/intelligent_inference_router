# Redis cache for IIR MVP
import redis.asyncio as redis
import hashlib
import os
from router.settings import get_settings

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

async def get_cache():
    return await redis.from_url(REDIS_URL, decode_responses=True)

def make_cache_key(prompt: str, context: str, model_id: str) -> str:
    key = f"{prompt}|{context}|{model_id}"
    return hashlib.sha256(key.encode()).hexdigest()
