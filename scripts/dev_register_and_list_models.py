#!/usr/bin/env python3
"""
Automates API key registration and lists available models for Intelligent Inference Router (IIR).
- Registers a new API key (prints it)
- Lists all available models using the new key
- Prints example usage
"""
import os
import requests

BASE_URL = os.environ.get("IIR_API_URL", "http://localhost:8000")
ADMIN_KEY = os.environ.get("IIR_ADMIN_KEY", "changeme-admin-key")  # Should be set in .env for real use

# 1. Register new API key
print("[IIR] Registering new API key...")
resp = requests.post(f"{BASE_URL}/v1/apikey/register", headers={"Authorization": f"Bearer {ADMIN_KEY}"})
if resp.status_code != 200:
    print(f"[ERROR] Failed to register API key: {resp.status_code} {resp.text}")
    exit(1)
api_key = resp.json().get("api_key")
print(f"[IIR] Registered API key: {api_key}")

# 2. List models
print("[IIR] Listing available models...")
resp = requests.get(f"{BASE_URL}/v1/models", headers={"Authorization": f"Bearer {api_key}"})
if resp.status_code != 200:
    print(f"[ERROR] Failed to list models: {resp.status_code} {resp.text}")
    exit(1)
models = resp.json().get("data", [])
print("[IIR] Available models:")
for m in models:
    print(f" - {m.get('id')} (provider: {m.get('provider', 'unknown')})")

# 3. Print example chat completion call
print("\n[IIR] Example: call /v1/chat/completions with your new API key:")
print(f"curl -X POST {BASE_URL}/v1/chat/completions \\")
print("  -H 'Authorization: Bearer {}' \\").format(api_key)
print("  -H 'Content-Type: application/json' \\")
print("  -d '{\"model\": \"<model-id>\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}'")
