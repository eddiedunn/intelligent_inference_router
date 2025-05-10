# API Key auth for IIR MVP
import os
from fastapi import Request, HTTPException, status

def get_key_from_request(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    return auth.split(" ", 1)[1]

from router.apikey_db import get_api_key

async def api_key_auth(request: Request):
    API_KEY = os.environ.get("IIR_API_KEY")
    ALLOWED_KEYS = set(os.environ.get("IIR_ALLOWED_KEYS", "").split(","))
    key = get_key_from_request(request)
    print("[DEBUG] IIR_API_KEY:", API_KEY)
    print("[DEBUG] IIR_ALLOWED_KEYS:", ALLOWED_KEYS)
    print("[DEBUG] Incoming header Authorization:", request.headers.get("Authorization"))
    print("[DEBUG] Extracted key:", key)
    # Prefer DB lookup for valid keys
    db_row = get_api_key(key)
    if db_row is not None:
        return True
    # Fallback: Accept if matches env API_KEY or is in ALLOWED_KEYS
    if (API_KEY and key == API_KEY) or (key and key in ALLOWED_KEYS):
        return True
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
