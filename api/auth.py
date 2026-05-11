"""Auth blueprint — login, JWT, protected routes."""

from kewe import Blueprint, Request, json
from kewe.security.auth import login_required
from kewe.errors.exceptions import Unauthorized, BadRequest
from services.auth_service import authenticate, create_tokens, verify_token

auth_bp = Blueprint("auth", url_prefix="/api/auth")


@auth_bp.post("/login")
async def login(request: Request):
    body = await request.json
    username = body.get("username")
    password = body.get("password")
    if not username or not password:
        raise BadRequest("username and password are required")

    user_data = authenticate(username, password)
    if user_data is None:
        raise Unauthorized("Invalid credentials")

    tokens = create_tokens(user_data)
    return json({"user": user_data, **tokens})


@auth_bp.get("/me")
@login_required
async def me(request: Request):
    """Protected route — requires valid JWT Bearer token."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    payload = verify_token(token)
    if payload is None:
        raise Unauthorized("Invalid or expired token")
    return json({"authenticated": True, "user_id": payload.get("user_id") or payload.get("sub"), "username": payload.get("username")})


@auth_bp.get("/status")
async def status():
    return json({"auth_service": "running", "method": "JWT Bearer"})
