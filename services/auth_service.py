"""Auth service with JWT token handling."""

from kewe.security.jwt import JWTAuthManager

jwt = JWTAuthManager(secret_key="demo-jwt-secret-key-32-chars!")


def authenticate(username: str, password: str) -> dict | None:
    """Simple demo auth — in production, hash passwords and use a real DB."""
    from models.schemas import users_db

    for user in users_db.values():
        if user.username == username and password == "demo123":
            return {
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
            }
    return None


def create_tokens(user_data: dict) -> dict:
    access_token = jwt.create_token(user_data, token_type="access", expires_in=3600)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode_token(token)
        return dict(payload) if payload else None
    except Exception:
        return None
