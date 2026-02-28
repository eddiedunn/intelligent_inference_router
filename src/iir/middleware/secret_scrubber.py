"""Secret detection and scrubbing utilities."""

from __future__ import annotations

import math
import os
import re
from typing import Any

SECRET_ENV_PATTERNS = [
    "KEY", "SECRET", "TOKEN", "PASS", "PWD", "CREDENTIAL", "PRIVATE", "API", "AUTH", "SESSION",
]

COMMON_SECRET_REGEXES = [
    r"AKIA[0-9A-Z]{16}",
    r"eyJ[0-9a-zA-Z_-]{10,}\.[0-9a-zA-Z_-]{10,}\.[0-9a-zA-Z_-]{10,}",
    r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9\-_=]{16,}['\"]",
    r"Bearer [A-Za-z0-9\-\._~\+\/=]{20,}",
    r"ya29\.[0-9A-Za-z\-_]+",
    r"-----BEGIN (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----[\s\S]*?-----END (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----",
]

_COMPILED_REGEXES = [re.compile(p, re.DOTALL) for p in COMMON_SECRET_REGEXES]


def shannon_entropy(data: str) -> float:
    if not data:
        return 0.0
    freq: dict[str, int] = {}
    for c in data:
        freq[c] = freq.get(c, 0) + 1
    length = len(data)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


def gather_env_secrets(min_length: int = 10) -> set[str]:
    secrets: set[str] = set()
    for k, v in os.environ.items():
        components = re.split(r"[_-]", k)
        if any(comp.upper() in SECRET_ENV_PATTERNS for comp in components) and v and len(v) >= min_length:
            secrets.add(v)
    return secrets


def find_secrets(text: str, env_secrets: set[str], entropy_threshold: float = 4.0) -> list[str]:
    found: set[str] = set()
    for secret in env_secrets:
        if secret and secret in text:
            found.add(secret)
    for regex in _COMPILED_REGEXES:
        for match in regex.findall(text):
            if match:
                found.add(match if isinstance(match, str) else match[0])
    for word in re.findall(r"\S{16,}", text):
        if shannon_entropy(word) >= entropy_threshold:
            found.add(word)
    return list(found)


def scrub_text(text: str, env_secrets: set[str], entropy_threshold: float = 4.0) -> str:
    secrets = find_secrets(text, env_secrets, entropy_threshold)
    for secret in sorted(secrets, key=lambda s: -len(s)):
        text = text.replace(secret, "REDACTED")
    return text


def scrub_data(data: Any, env_secrets: set[str], entropy_threshold: float = 4.0) -> Any:
    if isinstance(data, str):
        return scrub_text(data, env_secrets, entropy_threshold)
    if isinstance(data, dict):
        return {k: scrub_data(v, env_secrets, entropy_threshold) for k, v in data.items()}
    if isinstance(data, list):
        return [scrub_data(x, env_secrets, entropy_threshold) for x in data]
    return data
