"""Users blueprint — full CRUD with validation."""

from kewe import Blueprint, Request, json, Depends
from kewe.errors.exceptions import NotFound, BadRequest
from services.user_service import get_all_users, get_user, create_user, update_user, delete_user

users_bp = Blueprint("users", url_prefix="/api/users")


@users_bp.get("/")
async def list_users():
    return json([{
        "id": u.id, "username": u.username,
        "email": u.email, "role": u.role, "active": u.active,
    } for u in get_all_users()])


@users_bp.get("/{user_id:int}")
async def retrieve_user(user_id: int):
    user = get_user(user_id)
    if user is None:
        raise NotFound(f"User {user_id} not found")
    return json({"id": user.id, "username": user.username, "email": user.email, "role": user.role})


@users_bp.post("/")
async def create_new_user(request: Request):
    body = await request.json
    username = body.get("username")
    email = body.get("email")
    if not username or not email:
        raise BadRequest("username and email are required")
    role = body.get("role", "user")
    user = create_user(username=username, email=email, role=role)
    return json({"id": user.id, "username": user.username, "email": user.email, "role": user.role}, status=201)


@users_bp.put("/{user_id:int}")
async def update_existing_user(user_id: int, request: Request):
    body = await request.json
    user = update_user(user_id, **body)
    if user is None:
        raise NotFound(f"User {user_id} not found")
    return json({"id": user.id, "username": user.username, "email": user.email, "role": user.role})


@users_bp.delete("/{user_id:int}")
async def delete_existing_user(user_id: int):
    if not delete_user(user_id):
        raise NotFound(f"User {user_id} not found")
    return json({"message": f"User {user_id} deleted"}, status=200)
