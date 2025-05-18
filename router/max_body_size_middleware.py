from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        body = await request.body()
        print(f"[DEBUG][MaxBodySizeMiddleware] Received body size: {len(body)} bytes (limit: {self.max_body_size})")
        if len(body) > self.max_body_size:
            print(f"[DEBUG][MaxBodySizeMiddleware] Rejecting request: body too large")
            return Response("Request body too large", status_code=413)
        return await call_next(request)
