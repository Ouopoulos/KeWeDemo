"""Advanced features demo: pagination, password hashing, file response, i18n."""

import os
import hashlib
from kewe import Blueprint, Request, json
from kewe.errors.exceptions import NotFound, BadRequest
from kewe.response.response import FileResponse, send_file as _send_file
from kewe.utils.pagination import paginate, PaginationParams, paginate_cursor, CursorPaginationParams
from models.schemas import users_db, products_db, User, Product

advanced_bp = Blueprint("advanced", url_prefix="/api/advanced")


# ---- Pagination Demo ----
@advanced_bp.get("/users")
async def paginated_users(request: Request):
    """List users with built-in pagination utility."""
    page = request.query_params.get("page", "1")
    per_page = request.query_params.get("per_page", "5")
    try:
        page = int(page)
        per_page = int(per_page)
    except ValueError:
        raise BadRequest("Invalid pagination parameters")

    params = PaginationParams(page=page, per_page=per_page)
    all_users = list(users_db.values())
    result = paginate(all_users, params=params)
    return json(result)


@advanced_bp.get("/products")
async def paginated_products(request: Request):
    """List products with built-in pagination utility."""
    page = request.query_params.get("page", "1")
    per_page = request.query_params.get("per_page", "5")
    try:
        page = int(page)
        per_page = int(per_page)
    except ValueError:
        raise BadRequest("Invalid pagination parameters")

    params = PaginationParams(page=page, per_page=per_page)
    all_products = list(products_db.values())
    result = paginate(all_products, params=params)
    return json(result)


# ---- Cursor Pagination Demo ----
@advanced_bp.get("/products-cursor")
async def cursor_paginated_products(request: Request):
    """List products with cursor-based pagination (ideal for infinite scroll)."""
    limit = request.query_params.get("limit", "3")
    cursor = request.query_params.get("cursor", None)
    try:
        limit = int(limit)
    except ValueError:
        raise BadRequest("Invalid limit parameter")

    params = CursorPaginationParams(limit=limit, cursor=cursor)
    all_products = sorted(products_db.values(), key=lambda p: p.id)
    result = paginate_cursor(all_products, cursor_field="id", params=params)
    return json(result)


# ---- Password Hashing Demo ----
_password_hashes: dict[str, str] = {}


@advanced_bp.post("/hash-password")
async def hash_password_demo(request: Request):
    """Hash a password using bcrypt (requires cryptography)."""
    body = await request.json
    password = body.get("password", "")
    if not password:
        raise BadRequest("password is required")

    try:
        from kewe.security.password import hash_password as _hash_pw
        hashed = _hash_pw(password)
        key = hashlib.sha256(password.encode()).hexdigest()[:8]
        _password_hashes[key] = hashed
        return json({
            "password_key": key,
            "hash": hashed,
            "algorithm": "bcrypt",
            "note": "Store the hash, never the plain text password",
        })
    except ImportError:
        hashed = hashlib.sha256(password.encode()).hexdigest()
        key = hashed[:8]
        _password_hashes[key] = hashed
        return json({
            "password_key": key,
            "hash": hashed[:32] + "...",
            "algorithm": "sha256 (fallback — install bcrypt for production)",
        })


@advanced_bp.post("/verify-password")
async def verify_password_demo(request: Request):
    """Verify a password against stored hash."""
    body = await request.json
    password = body.get("password", "")
    password_key = body.get("password_key", "")

    if not password or not password_key:
        raise BadRequest("password and password_key are required")

    stored_hash = _password_hashes.get(password_key)
    if stored_hash is None:
        raise NotFound("Password hash not found for this key")

    try:
        from kewe.security.password import check_password_hash
        is_valid = check_password_hash(password, stored_hash)
    except ImportError:
        import hashlib
        is_valid = hashlib.sha256(password.encode()).hexdigest() == stored_hash

    return json({"valid": is_valid, "message": "Password matches!" if is_valid else "Invalid password"})


# ---- File Download Demo ----
TEMP_FILES_DIR = os.path.join(os.path.dirname(__file__), "..", "temp_downloads")
os.makedirs(TEMP_FILES_DIR, exist_ok=True)

# Create a sample download file
_sample_txt = os.path.join(TEMP_FILES_DIR, "sample.txt")
if not os.path.exists(_sample_txt):
    with open(_sample_txt, "w", encoding="utf-8") as f:
        f.write("Hello from KeWe Framework!\n")
        f.write("This is a sample file download demo.\n")
        f.write("=" * 50 + "\n")
        for i in range(10):
            f.write(f"Line {i+1}: The quick brown fox jumps over the lazy dog.\n")

_sample_json = os.path.join(TEMP_FILES_DIR, "data.json")
if not os.path.exists(_sample_json):
    import json as json_mod
    with open(_sample_json, "w", encoding="utf-8") as f:
        json_mod.dump({
            "framework": "KeWe",
            "version": "1.0.4",
            "features": ["async", "routing", "middleware", "websocket", "caching"],
            "demo_generated": True,
        }, f, indent=2)


@advanced_bp.get("/files")
async def list_downloadable_files():
    """List available downloadable files."""
    files = []
    for fname in os.listdir(TEMP_FILES_DIR):
        fpath = os.path.join(TEMP_FILES_DIR, fname)
        if os.path.isfile(fpath):
            files.append({
                "name": fname,
                "size": os.path.getsize(fpath),
                "url": f"/api/advanced/download/{fname}",
            })
    return json({"files": files})


@advanced_bp.get("/download/{filename:str}")
async def download_file(request: Request, filename: str):
    """Download a file with proper headers (ETag, range support)."""
    filepath = os.path.join(TEMP_FILES_DIR, filename)
    filepath = os.path.normpath(filepath)
    if not filepath.startswith(os.path.normpath(TEMP_FILES_DIR)):
        raise BadRequest("Path traversal denied")
    if not os.path.isfile(filepath):
        raise NotFound(f"File not found: {filename}")

    return FileResponse(
        path=filepath,
        filename=filename,
        request_headers=dict(request.headers),
    )


@advanced_bp.get("/send-file/{filename:str}")
async def send_file_demo(request: Request, filename: str):
    """Download using the convenience send_file() function."""
    filepath = os.path.join(TEMP_FILES_DIR, filename)
    filepath = os.path.normpath(filepath)
    if not filepath.startswith(os.path.normpath(TEMP_FILES_DIR)):
        raise BadRequest("Path traversal denied")
    if not os.path.isfile(filepath):
        raise NotFound(f"File not found: {filename}")
    return _send_file(filepath, filename=filename, attachment=True)


# ---- I18n Demo ----
_translations = {
    "en": {
        "welcome": "Welcome to KeWe Framework",
        "hello_user": "Hello, {username}!",
        "items_count": "You have {count} items",
        "goodbye": "Goodbye!",
    },
    "zh": {
        "welcome": "欢迎使用 KeWe 框架",
        "hello_user": "你好，{username}！",
        "items_count": "你有 {count} 个项目",
        "goodbye": "再见！",
    },
    "ja": {
        "welcome": "KeWeフレームワークへようこそ",
        "hello_user": "こんにちは、{username}！",
        "items_count": "{count}個のアイテムがあります",
        "goodbye": "さようなら！",
    },
}


@advanced_bp.get("/i18n")
async def i18n_demo(request: Request):
    """Internationalization demo — translate based on Accept-Language header."""
    lang = request.query_params.get("lang", "")
    if not lang:
        accept_lang = request.headers.get("accept-language", "en")
        lang = accept_lang.split(",")[0].split("-")[0].strip().lower() if accept_lang else "en"

    if lang not in _translations:
        lang = "en"

    t = _translations[lang]
    username = request.query_params.get("username", "Developer")
    items = request.query_params.get("items", "42")

    return json({
        "language": lang,
        "available_languages": list(_translations.keys()),
        "translations": {
            "welcome": t["welcome"],
            "hello_user": t["hello_user"].format(username=username),
            "items_count": t["items_count"].format(count=items),
            "goodbye": t["goodbye"],
        },
    })


# ---- Utility Endpoints ----
@advanced_bp.get("/server-info")
async def server_info(request: Request):
    """Show server info including KeWe version."""
    from kewe import __version__ as kewe_version
    import sys
    return json({
        "framework": "KeWe",
        "version": kewe_version,
        "python": sys.version,
        "platform": sys.platform,
        "temp_files_dir": TEMP_FILES_DIR,
        "available_endpoints": [
            "GET /api/advanced/users?page=1&per_page=5",
            "GET /api/advanced/products?page=1&per_page=5",
            "POST /api/advanced/hash-password",
            "POST /api/advanced/verify-password",
            "GET /api/advanced/files",
            "GET /api/advanced/download/{filename}",
            "GET /api/advanced/i18n?lang=zh&username=Developer",
            "GET /api/advanced/server-info",
        ],
    })
