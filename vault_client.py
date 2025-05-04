# vault_client.py
"""
Minimal Vault client for fetching secrets in Python apps (dev mode, token auth).
Usage: Vault-first secret fetch, fallback to env/config.
"""
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
        resp.raise_for_status()
        return resp.json()['data']['data'].get(field)
    except Exception:
        return None

# Example usage in your app:
# from vault_client import get_secret_from_vault
# REDIS_URL = get_secret_from_vault('services/iir/redis', 'url') or os.getenv('REDIS_URL')
