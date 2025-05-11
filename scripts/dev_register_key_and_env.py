#!/usr/bin/env python3
"""
Registers an API key with IIR and updates or creates the .env file with the new key.
- Uses the /api/v1/apikeys endpoint
- Parses the api_key from the response
- Sets/updates IIR_API_KEY in .env
"""
import os
import requests
import json
from pathlib import Path

BASE_URL = os.environ.get("IIR_API_URL", "http://localhost:8000")
ENV_PATH = Path(os.environ.get("IIR_ENV_FILE", ".env"))

# 1. Register new API key
print(f"[IIR] Registering new API key at {BASE_URL}/api/v1/apikeys ...")
resp = requests.post(f"{BASE_URL}/api/v1/apikeys", headers={"Content-Type": "application/json"}, json={"description": "dev-auto", "priority": 1})
if resp.status_code != 200:
    print(f"[ERROR] Failed to register API key: {resp.status_code} {resp.text}")
    exit(1)
api_key = resp.json().get("api_key")
if not api_key:
    print(f"[ERROR] No api_key in response: {resp.text}")
    exit(1)
print(f"[IIR] Registered API key: {api_key}")

# 2. Update or create .env
if ENV_PATH.exists():
    with ENV_PATH.open("r") as f:
        lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith("IIR_API_KEY="):
            lines[i] = f"IIR_API_KEY={api_key}\n"
            found = True
    if not found:
        lines.append(f"IIR_API_KEY={api_key}\n")
    with ENV_PATH.open("w") as f:
        f.writelines(lines)
    print(f"[IIR] Updated {ENV_PATH} with new IIR_API_KEY.")
else:
    with ENV_PATH.open("w") as f:
        f.write(f"IIR_API_KEY={api_key}\n")
    print(f"[IIR] Created {ENV_PATH} with new IIR_API_KEY.")
