import os
import re
import math
from typing import Any, Dict, List, Set, Pattern

# Patterns for env var names likely to hold secrets
SECRET_ENV_PATTERNS = [
    "KEY", "SECRET", "TOKEN", "PASS", "PWD", "CREDENTIAL", "PRIVATE", "API", "AUTH", "SESSION"
]

# Regex patterns for common secret types (expand as needed)
COMMON_SECRET_REGEXES = [
    # AWS Access Key ID
    r"AKIA[0-9A-Z]{16}",
    # AWS Secret Access Key
    r"(?<![A-Z0-9])[A-Za-z0-9/+=]{40}(?![A-Z0-9])",
    # JWT
    r"eyJ[0-9a-zA-Z_-]{10,}\.[0-9a-zA-Z_-]{10,}\.[0-9a-zA-Z_-]{10,}",
    # Generic API Key
    r"(?i)api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9\-_=]{16,}['\"]",
    # Bearer tokens
    r"Bearer [A-Za-z0-9\-\._~\+\/=]{20,}",
    # OAuth tokens
    r"ya29\.[0-9A-Za-z\-_]+",
    # Private keys (PEM)
    r"-----BEGIN (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----[\s\S]*?-----END (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----",
]

# Shannon entropy calculation
def shannon_entropy(data: str) -> float:
    if not data:
        return 0.0
    freq = {}
    for c in data:
        freq[c] = freq.get(c, 0) + 1
    entropy = 0.0
    for c in freq:
        p = freq[c] / len(data)
        entropy -= p * math.log2(p)
    return entropy

# Build set of likely secrets from env vars
def gather_env_secrets(min_length: int = 10, debug: bool = False) -> Set[str]:
    secrets = set()
    # Build a regex to match full word or trailing/leading secret patterns
    for k, v in os.environ.items():
        components = re.split(r'[_-]', k)
        if any(comp.upper() in SECRET_ENV_PATTERNS for comp in components) and v and len(v) >= min_length:
            if debug:
                print(f"[DEBUG] Adding env secret: {k}={v}")
            secrets.add(v)
    return secrets

# Compile regex patterns
COMPILED_SECRET_REGEXES: List[Pattern] = [re.compile(p, re.DOTALL) for p in COMMON_SECRET_REGEXES]

# Main hybrid secret detection function
def find_secrets(text: str, env_secrets: Set[str], entropy_threshold: float = 4.0, min_entropy_len: int = 16) -> List[str]:
    found = set()
    # 1. Direct env secret match
    for secret in env_secrets:
        if secret and secret in text:
            found.add(secret)
    # 2. Regex patterns
    for regex in COMPILED_SECRET_REGEXES:
        for match in regex.findall(text):
            if match:
                found.add(match)
    # 3. Entropy-based detection
    words = re.findall(r"\S{16,}", text)  # long words only
    for word in words:
        if shannon_entropy(word) >= entropy_threshold and len(word) >= min_entropy_len:
            found.add(word)
    return list(found)

# Scrub secrets from text
def scrub_secrets(text: str, env_secrets: Set[str], entropy_threshold: float = 4.0, min_entropy_len: int = 16) -> str:
    secrets = find_secrets(text, env_secrets, entropy_threshold, min_entropy_len)
    for secret in sorted(secrets, key=lambda s: -len(s)):
        text = text.replace(secret, "REDACTED")
    return text

# Recursively scrub secrets from dicts/lists/strings
def scrub_data(data: Any, env_secrets: Set[str], entropy_threshold: float = 4.0, min_entropy_len: int = 16) -> Any:
    if isinstance(data, str):
        return scrub_secrets(data, env_secrets, entropy_threshold, min_entropy_len)
    elif isinstance(data, dict):
        return {k: scrub_data(v, env_secrets, entropy_threshold, min_entropy_len) for k, v in data.items()}
    elif isinstance(data, list):
        return [scrub_data(x, env_secrets, entropy_threshold, min_entropy_len) for x in data]
    else:
        return data

# Example usage at startup:
# ENV_SECRETS = gather_env_secrets()
# ...
# safe_request = scrub_data(request_body, ENV_SECRETS)
# safe_response = scrub_data(response_body, ENV_SECRETS)
