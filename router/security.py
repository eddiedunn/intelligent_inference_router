# API Key auth for IIR MVP
from fastapi import Depends, HTTPException, status, Request
import os
from typing import List

API_KEY = os.getenv("ROUTER_API_KEY")
ALLOWED_KEYS = os.getenv("ROUTER_ALLOWED_API_KEYS", "").split(",") if os.getenv("ROUTER_ALLOWED_API_KEYS") else []

async def api_key_auth(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    key = auth.split(" ", 1)[1]
    if (API_KEY and key == API_KEY) or (key in ALLOWED_KEYS):
        return True
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
