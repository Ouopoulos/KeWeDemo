"""Custom middleware for the demo app."""

import time
from kewe import Middleware


class TimingMiddleware:
    """Adds X-Response-Time header to every response."""

    async def __call__(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time"] = f"{elapsed:.2f}ms"
        return response


class RequestLoggerMiddleware:
    """Logs incoming requests."""

    async def __call__(self, request, call_next):
        print(f"[REQ] {request.method} {request.url.path}")
        response = await call_next(request)
        status = getattr(response, 'status_code', getattr(response, 'status', 0))
        print(f"[RES] {request.method} {request.url.path} → {status}")
        return response
