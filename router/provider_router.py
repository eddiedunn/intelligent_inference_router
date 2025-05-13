import os
import json
import time
from typing import Dict, Any, Optional, Tuple
import hashlib
import logging
from .cache import get_cache, SimpleCache
import asyncio
from router.provider_clients import PROVIDER_CLIENTS

class ProviderRouter:
    def __init__(self, config: dict, cache_backend, cache_type: str):
        self.config = config
        self.providers = config.get("providers", {})
        self.routing = config.get("routing", {})
        self.caching = config.get("caching", {})
        self.logger = logging.getLogger("iir.provider_router")
        self.cache_backend = cache_backend
        self.cache_type = cache_type

    def select_provider(
        self,
        payload: Dict[str, Any],
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Any, str]:
        """
        Decide which provider to use based on payload, user, and context.
        Returns (provider_name, provider_client, model)
        """
        model = payload.get("model", "")
        # Prefix-based routing
        for prefix, provider_name in self.routing.get("model_prefix_map", {}).items():
            if model.startswith(prefix):
                break
        else:
            provider_name = self.routing.get("default", "openai")
        if provider_name not in PROVIDER_CLIENTS:
            raise Exception(f"No provider client found for: {provider_name}")
        provider_client = PROVIDER_CLIENTS[provider_name]
        return provider_name, provider_client, model

    def cache_key(self, payload: Dict[str, Any]) -> str:
        # Hash the payload for cache key
        key = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(key.encode()).hexdigest()

    async def cache_get(self, cache_key: str) -> Optional[Any]:
        """
        Robust async cache getter. Always safe to await.
        Works with both Redis (async) and SimpleCache (sync, via asyncio.to_thread).
        Returns None if not found or expired.
        """
        import asyncio
        if self.cache_type == 'redis':
            value = await self.cache_backend.get(cache_key)
            if value is not None:
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return None
        else:
            return await asyncio.to_thread(self.cache_backend.get, cache_key)

    async def cache_set(self, cache_key: str, response: Any, ttl: int = 60):
        """
        Robust async cache setter. Always safe to await.
        Uses asyncio.to_thread for SimpleCache backend.
        """
        import asyncio
        if self.cache_type == 'redis':
            await self.cache_backend.set(cache_key, json.dumps(response), ex=ttl)
        else:
            await asyncio.to_thread(self.cache_backend.set, cache_key, response, ttl)
        self.logger.debug(f"Cache set for key {cache_key}")

    def record_usage(self, provider: str, user_id: Optional[str], tokens: int):
        # Stub: log usage for quotas/analytics
        self.logger.info(f"Usage: provider={provider} user={user_id} tokens={tokens}")

    @classmethod
    def from_file(cls, path: str):
        with open(path, "r") as f:
            config = json.load(f) if path.endswith(".json") else yaml.safe_load(f)
        return cls(config)
