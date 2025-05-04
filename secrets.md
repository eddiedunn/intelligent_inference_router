# Secrets Inventory for intelligent_inference_router

| Secret Name      | Service | Config Location            | Current Source     | Target Source (Best Practice) | Notes |
|------------------|---------|---------------------------|--------------------|-------------------------------|-------|
| REDIS_URL        | Redis   | config.defaults.yaml      | Hardcoded in YAML  | Vault, fallback config/.env   | Contains Redis host/port, can include password if needed |

## Vault-First, Config/.env-Fallback Pattern

- For secrets (like REDIS_URL) that may contain sensitive info (passwords), fetch from Vault if available, otherwise fall back to config file or environment variable.
- Example (Python):
```python
import os
import requests

def get_secret_from_vault(path, field):
    VAULT_ADDR = os.environ.get('VAULT_ADDR', 'http://localhost:8200')
    VAULT_TOKEN = os.environ.get('VAULT_TOKEN') or os.environ.get('VAULT_DEV_ROOT_TOKEN_ID')
    if not VAULT_TOKEN:
        return None
    url = f"{VAULT_ADDR}/v1/secret/data/{path}"
    headers = {"X-Vault-Token": VAULT_TOKEN}
    try:
        resp = requests.get(url, headers=headers)
        return resp.json()['data']['data'].get(field)
    except Exception:
        return None

# Usage
REDIS_URL = get_secret_from_vault('services/iir/redis', 'url') or os.getenv('REDIS_URL')
```

## What Can Be Rotated
- **Only secrets we generate and manage** (e.g., Redis password) can be rotated by automation.
- **Third-party API keys** are not rotated automatically (future goal).

## Rotation Workflow (Current State)
- Use the central `rotate_secrets.py` (from core-services) to rotate Redis password if present.
- Update Vault and config/.env with new credentials.
- Restart the app to pick up new secrets.

_Last updated: 2025-05-04_
