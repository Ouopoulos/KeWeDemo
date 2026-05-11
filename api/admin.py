"""Admin blueprint — rate-limited + RBAC-protected endpoints."""

from kewe import Blueprint, Request, json
from kewe.security.rbac_manager import RBACManager
from kewe.errors.exceptions import Unauthorized
from models.schemas import users_db

admin_bp = Blueprint("admin", url_prefix="/api/admin")

# RBAC manager for route protection
rbac = RBACManager()
rbac.add_role("admin", {"users:read", "users:write", "users:delete", "admin:dashboard"})
rbac.add_role("moderator", {"users:read", "users:write"})
rbac.add_role("user", {"users:read"})

# Assign users to roles (from in-memory DB + demo)
for uid, user in users_db.items():
    rbac.assign_role(str(uid), user.role)


async def check_permission(request: Request, permission: str):
    """Check RBAC permission from JWT token. Raises Unauthorized if denied."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    if not token:
        raise Unauthorized("Missing authentication token")

    from services.auth_service import verify_token
    payload = verify_token(token)
    if payload is None:
        raise Unauthorized("Invalid or expired token")

    user_id = str(payload.get("user_id") or payload.get("sub", ""))
    if not rbac.has_permission(user_id, permission):
        raise Unauthorized(f"Permission '{permission}' denied")
    return payload


@admin_bp.get("/dashboard")
async def admin_dashboard(request: Request):
    """Admin-only dashboard — requires 'admin:dashboard' permission."""
    payload = await check_permission(request, "admin:dashboard")
    return json({
        "dashboard": "admin",
        "welcome": f"Hello {payload.get('username', 'admin')}",
        "stats": {
            "total_users": len(users_db),
            "active_users": sum(1 for u in users_db.values() if u.active),
            "roles_distribution": {
                role: sum(1 for u in users_db.values() if u.role == role)
                for role in set(u.role for u in users_db.values())
            }
        }
    })


@admin_bp.get("/users")
async def admin_list_users(request: Request):
    """View full user details — requires 'users:read' permission."""
    await check_permission(request, "users:read")
    return json([{
        "id": u.id, "username": u.username,
        "email": u.email, "role": u.role, "active": u.active,
    } for u in users_db.values()])
