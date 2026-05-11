"""Form handling, Cookies, and Sessions demo blueprint."""

from kewe import Blueprint, Request, json, Form, Header
from kewe.errors.exceptions import BadRequest
from kewe.cookies.cookie import CookieJar
from kewe.cookies.signed import SignedCookieManager
from kewe.cookies.session import Session, SessionConfig, SessionInterface

forms_bp = Blueprint("forms", url_prefix="/api/forms")

# Signed cookie manager
signed_cookies = SignedCookieManager(secret_key="demo-cookie-secret-32chars!")


# ---- Form Data Handling ----
@forms_bp.get("/")
async def forms_index():
    return json({
        "endpoints": {
            "form_submit": "POST /api/forms/submit",
            "form_login": "POST /api/forms/login",
            "cookie_counter": "GET /api/forms/cookie-counter",
            "signed_cookie": "GET /api/forms/signed-cookie",
            "session_demo": "GET /api/forms/session",
            "header_info": "GET /api/forms/headers",
        }
    })


@forms_bp.post("/submit")
async def form_submit(request: Request):
    """Handle form submission with Form() parameter extraction."""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.json
        name = body.get("name", "unknown")
        email = body.get("email", "unknown")
        return json({"method": "json", "name": name, "email": email})

    # Parse form-encoded data
    body = await request.body
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")

    fields = {}
    for pair in body.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            fields[k.strip()] = v.strip()

    name = fields.get("name", "unknown")
    email = fields.get("email", "unknown")
    return json({"method": "form", "name": name, "email": email})


@forms_bp.post("/login")
async def form_login(request: Request):
    """Simulated login form."""
    body = await request.body
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    fields = {}
    for pair in body.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            fields[k.strip()] = v.strip()

    username = fields.get("username")
    password = fields.get("password")
    if not username or not password:
        raise BadRequest("username and password required")

    if password == "demo123":
        return json({"login": "success", "username": username, "method": "form_post"})
    raise BadRequest("Invalid credentials")


# ---- Cookie Handling ----
@forms_bp.get("/cookie-counter")
async def cookie_counter(request: Request):
    """Track visits using a plain cookie."""
    jar = CookieJar()
    cookie_value = request.cookies.get("visit_count", "0")
    try:
        count = int(cookie_value) + 1
    except (ValueError, TypeError):
        count = 1

    response = json({"visits": count, "message": f"You've visited {count} times"})
    response.set_cookie(
        "visit_count", str(count),
        path="/", httponly=False, max_age=3600,
    )
    return response


@forms_bp.get("/signed-cookie")
async def signed_cookie_demo(request: Request):
    """Demonstrate signed cookies for tamper-proof values."""
    # Try to read and verify a signed cookie
    existing = request.cookies.get("signed_data", None)

    if existing:
        try:
            verified = signed_cookies.unsign(existing)
            return json({"signed_cookie_verified": True, "value": verified, "note": "Cookie is tamper-proof"})
        except Exception:
            pass

    # Create a new signed cookie
    data = f"premium_user_{request.cookies.get('visit_count', '1')}"
    signed = signed_cookies.sign(data)
    response = json({"signed_cookie_created": True, "raw_value": data, "signed_value": signed[:30] + "..."})
    response.set_cookie("signed_data", signed, path="/", httponly=True, max_age=3600)
    return response


# ---- Session Demo ----
_session_store: dict[str, Session] = {}


@forms_bp.get("/session")
async def session_demo(request: Request):
    """Session-like demo using cookies."""
    session_id = request.cookies.get("demo_session")
    is_new = False

    if session_id and session_id in _session_store:
        session = _session_store[session_id]
    else:
        import uuid
        session_id = uuid.uuid4().hex[:16]
        _session_store[session_id] = {"created": True, "counter": 0}
        is_new = True

    session = _session_store[session_id]
    session["counter"] = session.get("counter", 0) + 1

    response = json({
        "session_id": session_id[:8] + "...",
        "is_new": is_new,
        "counter": session["counter"],
        "stored_sessions": len(_session_store),
    })
    if is_new:
        response.set_cookie("demo_session", session_id, path="/", httponly=True, max_age=600)
    return response


# ---- Header Information ----
@forms_bp.get("/headers")
async def header_info(request: Request):
    """Display request headers for debugging."""
    safe_headers = {}
    for key, value in request.headers.items():
        if key.lower() in ("host", "user-agent", "accept", "accept-language",
                           "accept-encoding", "content-type", "x-forwarded-for"):
            safe_headers[key] = value

    return json({
        "headers": safe_headers,
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "client_cookies": dict(request.cookies) if hasattr(request, 'cookies') else {},
    })
