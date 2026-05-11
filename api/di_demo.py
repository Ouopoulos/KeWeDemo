"""Dependency Injection and Parameter Extractor demo."""

from kewe import Blueprint, Request, json, Depends, Query, Header, CookieParam, Body
from kewe.application.di import Container, Lifetime, Scope
from kewe.errors.exceptions import BadRequest
from models.schemas import users_db

di_bp = Blueprint("di", url_prefix="/api/di")


# ---- DI Container registrations ----
def get_container() -> Container:
    from app import app
    return app.container


# Define a reusable dependency
async def get_db():
    """Simulated database dependency — returns in-memory users DB."""
    return users_db


async def get_current_user_id(request: Request):
    """Extract user ID from JWT token."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    from services.auth_service import verify_token
    payload = verify_token(auth.replace("Bearer ", ""))
    return payload.get("sub") if payload else None


# ---- Parameter Extractor Demos ----
@di_bp.get("/")
async def di_index():
    return json({
        "endpoints": {
            "depends_basic": "GET /api/di/users — Depends(get_db) injection",
            "depends_auth": "GET /api/di/me — Depends(get_current_user_id)",
            "query_extractor": "GET /api/di/search?q=hello&limit=10",
            "header_extractor": "GET /api/di/agent — Header() extractor",
            "cookie_extractor": "GET /api/di/cookie-read — CookieParam() extractor",
            "di_scope": "GET /api/di/scope — DI scope demo",
        }
    })


# ---- Depends() DI ----
@di_bp.get("/users")
async def list_users_via_di(request: Request):
    """Uses Depends() to resolve the database dependency."""
    db = await get_db()
    return json([{
        "id": u.id, "username": u.username,
        "email": u.email, "role": u.role,
    } for u in db.values()])


@di_bp.get("/me")
async def current_user_info(request: Request):
    """Uses Depends() to resolve the current user from JWT."""
    user_id = await get_current_user_id(request)
    if user_id is None:
        return json({"authenticated": False, "message": "No valid token"})
    user = users_db.get(int(user_id))
    if user is None:
        return json({"authenticated": False, "message": "User not found"})
    return json({"authenticated": True, "username": user.username, "role": user.role})


# ---- Query Parameter Extractor ----
@di_bp.get("/search")
async def search_demo(
    q: str = Query(default="", alias="q"),
    limit: int = Query(default=10),
    page: int = Query(default=1),
):
    """Multiple Query() extractors with aliases and defaults."""
    results = []
    if q:
        for user in users_db.values():
            if q.lower() in user.username.lower() or q.lower() in user.email.lower():
                results.append({"id": user.id, "username": user.username, "email": user.email})

    start = (page - 1) * limit
    paged = results[start:start + limit]
    return json({
        "query": q,
        "total_results": len(results),
        "page": page,
        "limit": limit,
        "results": paged,
    })


# ---- Header Extractor ----
@di_bp.get("/agent")
async def user_agent_demo(
    user_agent: str = Header(default="unknown", alias="User-Agent"),
    accept_lang: str = Header(default="en", alias="Accept-Language"),
    host: str = Header(default="localhost", alias="Host"),
):
    """Header() extractor demonstrates automatic header-to-parameter injection."""
    return json({
        "user_agent": user_agent,
        "accept_language": accept_lang,
        "host": host,
        "note": "These values are extracted from request headers automatically via Header()",
    })


# ---- Cookie Parameter Extractor ----
@di_bp.get("/cookie-read")
async def cookie_extractor_demo(
    visit_count: str = CookieParam(default="0", alias="visit_count"),
):
    """CookieParam() extractor demonstrates automatic cookie-to-parameter injection."""
    return json({
        "visit_count": visit_count,
        "note": "This value was extracted from the 'visit_count' cookie via CookieParam() — visit /api/forms/cookie-counter first to set it",
    })


# ---- DI Scope Demo ----
@di_bp.get("/scope")
async def scope_demo(request: Request):
    """Demonstrate DI container scopes and registrations."""
    container = get_container()
    registrations = []
    for name in ("app_name", "version"):
        try:
            val = container.resolve(name)
            registrations.append({"name": name, "value": str(val)})
        except Exception:
            registrations.append({"name": name, "value": "unresolved"})

    return json({
        "registrations": registrations,
        "scope_info": {
            "lifetimes": ["SINGLETON (one per app)", "TRANSIENT (new each time)", "SCOPED (new per scope)"],
            "note": "Use container.scope() for request-scoped instances",
            "example": "async with container.scope() as scope: ...",
        }
    })
