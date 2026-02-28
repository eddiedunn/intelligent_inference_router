"""Cache key generation utilities."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def make_cache_key(prefix: str, data: dict[str, Any]) -> str:
    raw = json.dumps(data, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"{prefix}:{digest}"


def classification_cache_key(messages: list[dict[str, Any]]) -> str:
    last_user = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            last_user = content if isinstance(content, str) else json.dumps(content)
            break
    return make_cache_key("classify", {"message": last_user})
