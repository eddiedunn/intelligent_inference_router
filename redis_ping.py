import redis.asyncio as redis
import asyncio
import os
from vault_client import get_secret_from_vault

async def main():
    # Vault-first, env-fallback for REDIS_URL
    REDIS_URL = get_secret_from_vault('services/iir/redis', 'url') or os.getenv('REDIS_URL')
    r = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    try:
        pong = await r.ping()
        print(f"Redis ping response: {pong}")
    except Exception as e:
        print(f"Redis ping failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
