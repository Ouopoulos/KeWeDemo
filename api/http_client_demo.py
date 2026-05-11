"""HTTP Client proxy demo — demonstrates AsyncHTTPClient with retry and pooling."""

import asyncio
from kewe import Blueprint, Request, json
from kewe.errors.exceptions import BadRequest
from kewe.http.client import AsyncHTTPClient, RetryConfig

http_bp = Blueprint("http_client", url_prefix="/api/http-client")

# Configure HTTP client with retry
retry_config = RetryConfig(max_retries=3, backoff_factor=1.0, backoff_max=10.0)

# Note: In production, use setup_http_client(app) for lifecycle integration
http_client = AsyncHTTPClient(timeout=10.0, retry=retry_config)

# Simulated "external service" state
_external_data = {
    "users": [{"id": 1, "name": "Proxy User 1"}, {"id": 2, "name": "Proxy User 2"}],
    "status": "healthy",
}


@http_bp.get("/")
async def http_client_index():
    """List HTTP client demo endpoints."""
    return json({
        "client_type": "AsyncHTTPClient",
        "features": ["retry", "connection pooling", "interceptors"],
        "retry_config": {
            "max_retries": retry_config.max_retries,
            "backoff_factor": retry_config.backoff_factor,
            "backoff_max": retry_config.backoff_max,
        },
        "endpoints": {
            "simulate_external": "GET /api/http-client/external/users",
            "fetch_self": "GET /api/http-client/fetch?url=/api/health",
            "interceptor_demo": "GET /api/http-client/interceptor",
            "retry_demo": "GET /api/http-client/retry-demo",
        }
    })


@http_bp.get("/external/users")
async def simulate_external_api():
    """Simulate an external API response (normally fetched via HTTP client)."""
    # Simulate network delay
    await asyncio.sleep(0.1)
    return json({
        "source": "simulated-external-api",
        "data": _external_data["users"],
    })


@http_bp.get("/fetch")
async def fetch_internal(request: Request):
    """Fetch another endpoint within this app (self-referencing proxy demo)."""
    target = request.query_params.get("url", "/api/health")

    try:
        response = await http_client.get(f"http://127.0.0.1:8000{target}")
        data = response.json() if hasattr(response, 'json') else str(response.content)
        return json({
            "proxy": True,
            "target": target,
            "status": response.status_code,
            "data": data,
        })
    except Exception as e:
        return json({
            "proxy": True,
            "target": target,
            "error": str(e),
            "note": "HTTP client fetch works when server is running. Use 'uv run python app.py' first.",
        })


@http_bp.get("/interceptor")
async def interceptor_demo():
    """Demonstrate HTTP client with request/response interceptors."""
    return json({
        "interceptors": {
            "request": "Can add auth headers, log requests, modify URLs",
            "response": "Can log responses, transform data, handle errors",
        },
        "example_usage": """
# Add auth interceptor
client.add_request_interceptor(lambda req: req.headers.update({"Authorization": "Bearer ..."}))

# Add logging interceptor
client.add_response_interceptor(lambda resp: print(f"Got {resp.status_code}"))
""",
    })


@http_bp.get("/retry-demo")
async def retry_demo(request: Request):
    """Demonstrate HTTP client retry capabilities."""
    attempt = request.query_params.get("attempt", "1")
    try:
        attempt_num = int(attempt)
    except ValueError:
        attempt_num = 1

    # Simulate retry behavior
    if attempt_num <= 2:
        return json({
            "attempt": attempt_num,
            "status": "retry",
            "message": f"Attempt {attempt_num} failed — would retry with backoff",
            "next_retry_in_seconds": retry_config.backoff_factor * (2 ** (attempt_num - 1)),
        })

    return json({
        "attempt": attempt_num,
        "status": "success",
        "message": f"Succeeded on attempt {attempt_num}",
        "retries_used": attempt_num - 1,
    })


@http_bp.get("/stats")
async def client_stats():
    """Show HTTP client statistics."""
    return json({
        "client_initialized": http_client is not None,
        "base_url": getattr(http_client, 'base_url', 'not set'),
        "timeout": getattr(http_client, 'timeout', 'default'),
        "retry_enabled": True,
    })
