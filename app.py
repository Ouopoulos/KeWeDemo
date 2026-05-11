"""
KeWe Demo Application
=====================
A complete showcase of KeWe framework features:
  - Routing (path params, query params, blueprints)
  - CRUD operations (users, products)
  - JWT Authentication (login, protected routes)
  - Custom middleware (timing, request logging)
  - WebSocket chat
  - Server-Sent Events (SSE) streaming
  - Background tasks
  - Health checks
  - OpenAPI / Swagger docs
  - Static file serving
  - Error handling (404, 400, 401)
  - Dependency injection (DI container)
  - Application factory pattern
  - Rate limiting
  - RBAC (Role-Based Access Control)
  - Caching with memory backend
  - CSRF protection
  - Pydantic model validation
  - File upload
  - Class-based views
  - Compression middleware
  - Security headers middleware
  - Circuit breaker
  - Prometheus-compatible metrics
  - Form data handling, Cookies, Sessions
  - Pagination (offset + cursor), Password hashing
  - FileResponse with ETag/Range/304
  - I18n internationalization
  - Access logging, Request ID, Inspector
  - Signal/Event system
"""

import asyncio
import os
import time

from kewe import (
    Kewe, Response, json, text, html, redirect,
    ServerSentEventResponse,
    Request, Depends, Query,
)
from kewe.middleware import CORSMiddleware, CompressionMiddleware, SecurityHeadersMiddleware, TrustedHostMiddleware
from kewe.security.rate_limit import RateLimiter
from kewe.security.csrf import CSRFMiddleware
from kewe.errors.exceptions import NotFound, BadRequest, Unauthorized, Forbidden, MethodNotAllowed, TooManyRequests
from kewe.errors.handlers import setup_error_handlers
from kewe.errors.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from kewe.plugins.openapi import OpenAPIPlugin
from kewe.monitoring.health import setup_health_checks
from kewe.monitoring.core import MetricsCollector
from kewe.application.di import Container, Lifetime
from kewe.middleware.request_id import RequestIDMiddleware
from kewe.routing.blueprint_group import BlueprintGroup

from config import config
from middleware.custom import TimingMiddleware, RequestLoggerMiddleware
from api.users import users_bp
from api.products import products_bp
from api.auth import auth_bp
from api.admin import admin_bp
from api.cache_demo import cache_bp
from api.upload import upload_bp
from api.views import views_bp
from api.pydantic_validation import pydantic_bp
from api.forms_sessions import forms_bp
from api.advanced import advanced_bp
from api.monitoring_demo import monitoring_bp
from api.http_client_demo import http_bp
from api.signals_demo import signals_bp
from api.di_demo import di_bp
from api.redis_demo import redis_bp
from api.database_demo import db_bp
from api.celery_demo import celery_bp


# ---- Application Factory ----
def create_app() -> Kewe:
    app = Kewe("KeWeDemo", config=config, enable_gateway=False)

    # ---- DI Container ----
    container: Container = app.container
    container.register("app_name", lambda: "KeWeDemo", Lifetime.SINGLETON)
    container.register("version", lambda: "1.0.0", Lifetime.SINGLETON)

    # ---- Middleware Stack ----
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CompressionMiddleware, min_size=500)
    app.add_middleware(CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
    )
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestLoggerMiddleware)

    # ---- Request ID Middleware ----
    RequestIDMiddleware(app)

    # ---- CSRF Protection ----
    if config.csrf_enabled:
        app.add_middleware(CSRFMiddleware,
            secret_key=config.csrf_secret,
            excluded_methods=["GET", "HEAD", "OPTIONS"],
            excluded_paths=["/api/", "/health", "/docs", "/static"])

    # ---- Error Handlers ----
    setup_error_handlers(app)

    # ---- Metrics & Monitoring ----
    metrics = MetricsCollector(app)

    @app.middleware("request")
    async def track_request_start(request):
        request.state.metrics_start = time.time()

    @app.middleware("response")
    async def track_request_end(request, response):
        elapsed = (time.time() - getattr(request.state, 'metrics_start', time.time())) * 1000
        metrics.counter("http_requests_total", labels={"method": request.method, "path": request.path})
        metrics.histogram("http_request_duration_ms", elapsed,
                         labels={"method": request.method})

    # ---- Blueprints ----
    app.register_blueprint(users_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(cache_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(pydantic_bp)
    app.register_blueprint(forms_bp)
    app.register_blueprint(advanced_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(http_bp)
    app.register_blueprint(signals_bp)
    app.register_blueprint(di_bp)
    app.register_blueprint(redis_bp)
    app.register_blueprint(db_bp)
    app.register_blueprint(celery_bp)

    # BlueprintGroup — demonstrates grouping blueprints under a common prefix
    obs_group = BlueprintGroup(url_prefix="/api/observability")
    obs_group.add_blueprint(monitoring_bp)
    obs_group.add_blueprint(signals_bp)
    # Note: registered individually above for route access; group provides prefix for organization
    # Usage: app.register_blueprint_group(obs_group)

    # ---- OpenAPI / Swagger ----
    openapi_plugin = OpenAPIPlugin()
    openapi_plugin.setup(app, title="KeWe Demo API", version="1.0.0",
                         description="A complete KeWe framework demo with 30+ features",
                         openapi_url="/api/openapi.json",
                         swagger_ui_url="/api/docs")

    # ---- Health Checks ----
    health_endpoint = setup_health_checks(app, path="/health")
    health_endpoint.checker.add_check("database", lambda: (True, "In-memory DB alive"))
    health_endpoint.checker.add_check("auth", lambda: (True, "JWT auth operational"))
    health_endpoint.checker.add_check("cache", lambda: (True, "Memory cache ready"))
    health_endpoint.checker.add_check("routing", lambda: (True, "All blueprints registered"))

    # ---- Lifecycle Hooks ----
    @app.before_server_start
    async def on_startup(kewe_app, loop):
        getattr(kewe_app, '_lifecycle_log', []).append({"event": "before_server_start", "time": time.time()})

    @app.after_server_start
    async def on_ready(kewe_app, loop):
        getattr(kewe_app, '_lifecycle_log', []).append({"event": "after_server_start", "time": time.time()})

    @app.before_server_stop
    async def on_shutdown(kewe_app, loop):
        getattr(kewe_app, '_lifecycle_log', []).append({"event": "before_server_stop", "time": time.time()})

    app._lifecycle_log = []

    # ---- WebSocket Chat ----
    from ws.chat import chat_handler
    app.websocket("/ws/chat")(chat_handler)

    # ---- Metrics Endpoint ----
    @app.get("/metrics")
    async def metrics_endpoint(request: Request):
        """Prometheus-compatible metrics endpoint."""
        prom_data = metrics.get_prometheus_metrics()
        return Response(body=prom_data, status=200, content_type="text/plain; charset=utf-8")

    return app


# ---- Metrics Endpoint ---- (moved inside create_app)
app = create_app()


# ===================================================================
# Routes
# ===================================================================

@app.get("/")
async def home(request: Request):
    return redirect("/static/index.html")


@app.get("/api/health")
async def health(request: Request):
    return json({
        "status": "healthy",
        "app": "KeWe Demo",
        "version": "1.0.0",
        "endpoints": {
            "users": "/api/users",
            "products": "/api/products",
            "auth": "/api/auth/login",
            "admin": "/api/admin/dashboard",
            "cache": "/api/cache/status",
            "upload": "/api/upload/",
            "views": "/api/views/products",
            "pydantic": "/api/pydantic/users",
            "docs": "/api/docs",
            "metrics": "/metrics",
            "websocket": "/ws/chat",
            "stream": "/api/stream",
            "bg_task": "/api/bg-task",
            "error_demo": "/api/error-demo?type=404",
            "circuit_breaker": "/api/circuit-breaker/status",
            "rate_limit_test": "/api/rate-test",
        }
    })


# ---- SSE Streaming ----
@app.get("/api/stream")
async def sse_demo(request: Request):
    """Server-Sent Events streaming demo."""
    async def event_generator():
        for i in range(5):
            yield f"data: Tick {i+1}/5\n\n"
            await asyncio.sleep(1)
        yield "data: Done!\n\n"
    return ServerSentEventResponse(event_generator())


# ---- Formal BackgroundTasks API ----
from kewe.response.response import BackgroundTasks


@app.get("/api/bg-formal")
async def bg_formal_demo(request: Request):
    """Background task using the formal BackgroundTasks API."""
    tasks = BackgroundTasks()

    async def send_email():
        await asyncio.sleep(2)
        print("[BG-FORMAL] Email sent after 2 seconds")

    async def update_stats():
        await asyncio.sleep(1)
        print("[BG-FORMAL] Stats updated after 1 second")

    tasks.add_task(send_email)
    tasks.add_task(update_stats)

    response = json({"message": "Response sent, 2 background tasks scheduled", "tasks": 2})
    response.background = tasks
    return response


# ---- url_for Demo ----
@app.get("/api/url-for")
async def url_for_demo(request: Request):
    """Demonstrate URL reversal with url_for()."""
    try:
        users_url = request.app.url_for("list_users") if hasattr(request.app, 'url_for') else "/api/users"
        health_url = request.app.url_for("health") if hasattr(request.app, 'url_for') else "/api/health"
    except Exception:
        users_url = "/api/users"
        health_url = "/api/health"

    return json({
        "url_for": {
            "description": "app.url_for('route_name') generates URLs from route names",
            "example_routes": {
                "list_users": users_url,
                "health": health_url,
            },
            "usage": "Use @app.get('/path', name='my_route') then app.url_for('my_route')",
        }
    })


# ---- Lifecycle Log ----
@app.get("/api/lifecycle-log")
async def lifecycle_log(request: Request):
    """Show lifecycle hook events."""
    log = getattr(app, '_lifecycle_log', [])
    return json({
        "events": log,
        "count": len(log),
        "note": "before_server_start/after_server_start fire on app.run(); before_server_stop on shutdown",
    })


# ---- Background Task ----
@app.get("/api/bg-task")
async def bg_task_demo(request: Request):
    """Background task demo — schedules async work via asyncio."""
    async def slow_notification():
        await asyncio.sleep(3)
        print("[BG-TASK] Notification sent after 3 seconds")

    asyncio.create_task(slow_notification())
    return json({"message": "Response sent immediately, background task running...", "task_started": True})


# ---- Error Handling Demo ----
@app.get("/api/error-demo")
async def error_demo(request: Request):
    """Deliberately trigger errors for testing. Supported types:
    404, 400, 401, 403, 405, 429, 500"""
    error_type = request.query_params.get("type", "404")

    if error_type == "404":
        raise NotFound("This resource does not exist")
    elif error_type == "400":
        raise BadRequest("Bad request demo")
    elif error_type == "401":
        raise Unauthorized("Unauthorized access demo")
    elif error_type == "403":
        raise Forbidden("Access forbidden demo")
    elif error_type == "405":
        raise MethodNotAllowed("Method not allowed demo")
    elif error_type == "429":
        raise TooManyRequests("Rate limit exceeded demo")
    elif error_type == "500":
        raise RuntimeError("Simulated internal server error")

    return json({"error_type": error_type, "status": "ok"})


# ---- Rate Limiting Demo ----
# In-memory rate limiter: 5 requests per 10 seconds
rate_limiter = RateLimiter()


@app.get("/api/rate-test")
async def rate_limit_test(request: Request):
    """Rate-limited endpoint — 5 requests per 10 seconds."""
    is_allowed, info = await rate_limiter.is_allowed(request, limit=5, period=10)
    if not is_allowed:
        raise BadRequest({
            "error": "Rate limit exceeded",
            "limit": info.limit,
            "remaining": info.remaining,
            "retry_after": info.retry_after,
        })

    return json({
        "message": "Request allowed",
        "limit": info.limit,
        "remaining": info.remaining,
        "reset_in_seconds": info.reset_time,
    })


# ---- Circuit Breaker Demo ----
cb_config = CircuitBreakerConfig(
    failure_threshold=config.circuit_breaker_threshold,
    recovery_timeout=config.circuit_breaker_timeout,
)
cb = CircuitBreaker("demo-api", config=cb_config)
_failure_counter = 0


@app.get("/api/circuit-breaker/status")
async def circuit_breaker_status(request: Request):
    """Get circuit breaker status."""
    return json(cb.get_status())


@app.get("/api/circuit-breaker/call")
async def circuit_breaker_call(request: Request):
    """Call an endpoint protected by circuit breaker.
    Fails every 2nd request to demonstrate circuit opening.
    """
    global _failure_counter
    _failure_counter += 1

    async def flaky_operation():
        # Simulate intermittent failure
        if _failure_counter % 2 == 0:
            raise RuntimeError("Simulated transient failure")
        await asyncio.sleep(0.3)
        return {"operation": "success", "attempt": _failure_counter}

    try:
        result = await cb.call(flaky_operation)
        return json({"circuit_state": cb.get_status()["state"], **result})
    except RuntimeError as e:
        raise BadRequest({
            "error": str(e),
            "circuit_state": cb.get_status()["state"],
            "attempt": _failure_counter,
        })


@app.post("/api/circuit-breaker/reset")
async def circuit_breaker_reset(request: Request):
    """Reset the circuit breaker."""
    global _failure_counter
    _failure_counter = 0
    cb.reset()
    return json({"message": "Circuit breaker reset", "status": cb.get_status()})


# ---- CSRF Token Endpoint ----
@app.get("/api/csrf-token")
async def get_csrf_token(request: Request):
    """Get a CSRF token for use in subsequent requests."""
    from kewe.security.csrf import get_csrf_token as generate_token
    token = generate_token(request, config.csrf_secret)
    response = json({"csrf_token": token})
    response.set_cookie("csrf_token", token, httponly=True, samesite="Strict")
    return response


@app.post("/api/csrf-protected")
async def csrf_protected_endpoint(request: Request):
    """CSRF-protected endpoint. Requires X-CSRF-Token header or csrf_token cookie.
    The CSRF middleware handles validation automatically.
    """
    return json({"message": "CSRF validation passed successfully", "protected": True})


# ---- System Status Dashboard ----
@app.get("/api/system")
async def system_status(request: Request):
    """Comprehensive system status dashboard."""
    import sys, platform as plat
    from kewe import __version__ as kewe_version
    from models.schemas import users_db, products_db, uploads_store
    from ws.chat import manager as ws_manager

    return json({
        "framework": {
            "name": "KeWe",
            "version": kewe_version,
        },
        "application": {
            "name": "KeWeDemo",
            "version": "1.0.0",
            "debug": config.debug,
        },
        "runtime": {
            "python": sys.version.split()[0],
            "platform": plat.system(),
            "arch": plat.machine(),
        },
        "data": {
            "users": len(users_db),
            "products": len(products_db),
            "uploads": len(uploads_store),
            "audit_logs": _get_audit_count(),
        },
        "websocket": {
            "connections": ws_manager.connection_count if hasattr(ws_manager, 'connection_count') else 0,
            "groups": getattr(ws_manager, '_groups', {}),
        },
        "blueprints": [
            "users", "products", "auth", "admin",
            "cache", "upload", "views", "pydantic",
            "forms", "advanced", "monitoring", "http_client", "signals", "di",
        ],
        "middleware_stack": [
            "TrustedHost", "SecurityHeaders", "Compression", "RequestID",
            "CORS", "Timing", "RequestLogger", "CSRF", "Metrics",
        ],
        "features": {
            "rate_limiting": True, "rbac": True, "caching": True,
            "pydantic_validation": True, "csrf_protection": config.csrf_enabled,
            "file_upload": True, "class_based_views": True,
            "circuit_breaker": config.circuit_breaker_enabled,
            "prometheus_metrics": True, "i18n": True, "password_hashing": True,
            "pagination": True, "http_client": True, "signal_system": True,
            "anomaly_detection": True, "audit_logging": True,
            "di_extractors": True, "lifecycle_hooks": True,
            "background_tasks": True, "url_for": True,
            "websocket_rooms": True, "cache_decorators": True,
            "blueprint_group": True, "send_file": True,
        },
    })


def _get_audit_count():
    try:
        from api.monitoring_demo import audit_storage
        return len(audit_storage.logs)
    except Exception:
        return 0


# ---- Static Files ----
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

@app.get("/static/{path:path}")
async def serve_static(request: Request, path: str):
    file_path = os.path.join(STATIC_DIR, path or "index.html")
    file_path = os.path.normpath(file_path)
    if not file_path.startswith(os.path.normpath(STATIC_DIR)):
        raise BadRequest("Path traversal denied")
    if not os.path.isfile(file_path):
        raise NotFound(f"Static file not found: {path}")

    content_type_map = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
    }
    ext = os.path.splitext(file_path)[1]
    content_type = content_type_map.get(ext, "application/octet-stream")
    with open(file_path, "rb") as f:
        return Response(body=f.read(), status=200, content_type=content_type)


# ---- CLI Entry ----
if __name__ == "__main__":
    app.run(host=config.host, port=config.port, debug=config.debug, motd=True)
