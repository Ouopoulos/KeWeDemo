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
"""

import asyncio
import os

from kewe import (
    Kewe, Response, json, text, html, redirect,
    ServerSentEventResponse,
    Request, Depends,
)

from kewe.middleware import CORSMiddleware
from kewe.errors.exceptions import NotFound, BadRequest, Unauthorized
from kewe.errors.handlers import setup_error_handlers
from kewe.plugins.openapi import OpenAPIPlugin
from kewe.monitoring.health import setup_health_checks
from kewe.application.di import Container, Lifetime

from config import config
from middleware.custom import TimingMiddleware, RequestLoggerMiddleware
from api.users import users_bp
from api.products import products_bp
from api.auth import auth_bp


# ---- Application Factory ----
def create_app() -> Kewe:
    app = Kewe("KeWeDemo", config=config, enable_gateway=False)

    # ---- DI Container ----
    container: Container = app.container
    container.register("app_name", lambda: "KeWeDemo", Lifetime.SINGLETON)
    container.register("version", lambda: "1.0.0", Lifetime.SINGLETON)

    # ---- Middleware ----
    app.add_middleware(CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestLoggerMiddleware)

    # ---- Error Handlers ----
    setup_error_handlers(app)

    # ---- Blueprints ----
    app.register_blueprint(users_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(auth_bp)

    # ---- OpenAPI / Swagger ----
    openapi_plugin = OpenAPIPlugin()
    openapi_plugin.setup(app, title="KeWe Demo API", version="1.0.0",
                         description="A complete KeWe framework demo",
                         openapi_url="/api/openapi.json",
                         swagger_ui_url="/api/docs")

    # ---- Health Checks ----
    health_endpoint = setup_health_checks(app, path="/health")
    health_endpoint.checker.add_check("database", lambda: (True, "In-memory DB alive"))
    health_endpoint.checker.add_check("auth", lambda: (True, "JWT auth operational"))

    # ---- WebSocket Chat ----
    from ws.chat import chat_handler
    app.websocket("/ws/chat")(chat_handler)

    return app


app = create_app()


# ---- Routes ----
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
            "docs": "/api/docs",
            "websocket": "/ws/chat",
            "stream": "/api/stream",
            "bg_task": "/api/bg-task",
            "error_demo": "/api/error-demo?type=404",
        }
    })


@app.get("/api/stream")
async def sse_demo(request: Request):
    """Server-Sent Events streaming demo."""
    async def event_generator():
        for i in range(5):
            yield f"data: Tick {i+1}/5\n\n"
            await asyncio.sleep(1)
        yield "data: Done!\n\n"
    return ServerSentEventResponse(event_generator())


@app.get("/api/bg-task")
async def bg_task_demo(request: Request):
    """Background task demo — schedules async work via asyncio."""
    async def slow_notification():
        await asyncio.sleep(3)
        print("[BG-TASK] Notification sent after 3 seconds")

    asyncio.create_task(slow_notification())
    return json({"message": "Response sent immediately, background task running...", "task_started": True})


@app.get("/api/error-demo")
async def error_demo(request: Request):
    """Deliberately trigger errors for testing."""
    error_type = request.query_params.get("type", "404")

    if error_type == "404":
        raise NotFound("This resource does not exist")
    elif error_type == "400":
        raise BadRequest("Bad request demo")
    elif error_type == "401":
        raise Unauthorized("Unauthorized access demo")
    elif error_type == "500":
        raise RuntimeError("Simulated internal server error")

    return json({"error_type": error_type, "status": "ok"})


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
