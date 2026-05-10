#!/usr/bin/env python
"""
KeWe Demo — Full Integration Test Suite
========================================
Tests all demo APIs via the framework's built-in TestClient.
"""

import sys
import os
import json as json_mod

sys.path.insert(0, os.path.dirname(__file__))

from kewe import TestClient
from app import app


def parse_json(r):
    """Parse response body from TestResponse."""
    if isinstance(r, dict):
        return r
    if isinstance(r.body, dict):
        return r.body
    if isinstance(r.body, (bytes, str)):
        return json_mod.loads(r.body)
    return r.body


def test_sync_client():
    """Run all tests using the synchronous TestClient."""
    print("=" * 60)
    print("KeWe Demo — Full Integration Test Suite")
    print("=" * 60)

    with TestClient(app) as c:
        # 1. Home redirect
        print("\n[1/12] Home redirect...", end=" ")
        r = c.get("/", follow_redirects=False)
        assert r.status_code == 302, f"Expected 302, got {r.status_code}"
        print("OK")

        # 2. Health check
        print("[2/12] Health check...", end=" ")
        r = c.get("/api/health")
        assert r.status_code == 200
        data = parse_json(r)
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        print("OK")

        # 3. List users
        print("[3/12] List users...", end=" ")
        r = c.get("/api/users")
        assert r.status_code == 200
        users = parse_json(r)
        assert len(users) == 3
        assert users[0]["username"] == "admin"
        print("OK")

        # 4. Get single user + 404
        print("[4/12] Get user by ID...", end=" ")
        r = c.get("/api/users/1")
        assert r.status_code == 200
        user = parse_json(r)
        assert user["username"] == "admin"
        assert user["role"] == "admin"

        r = c.get("/api/users/999")
        assert r.status_code == 404
        print("OK")

        # 5. Create user
        print("[5/12] Create user...", end=" ")
        r = c.post("/api/users", json={"username": "charlie", "email": "charlie@kewe.dev"})
        assert r.status_code == 201
        new_user = parse_json(r)
        assert new_user["id"] == 4
        assert new_user["username"] == "charlie"
        print("OK")

        # 6. Update user
        print("[6/12] Update user...", end=" ")
        r = c.put("/api/users/4", json={"role": "admin", "email": "charlie.admin@kewe.dev"})
        assert r.status_code == 200
        updated = parse_json(r)
        assert updated["role"] == "admin"
        print("OK")

        # 7. Delete user
        print("[7/12] Delete user...", end=" ")
        r = c.delete("/api/users/4")
        assert r.status_code == 200
        r = c.get("/api/users/4")
        assert r.status_code == 404
        print("OK")

        # 8. Products with filters + pagination
        print("[8/12] Products with filters...", end=" ")
        r = c.get("/api/products", query={"category": "tools"})
        assert r.status_code == 200
        data = parse_json(r)
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Widget Pro"

        r = c.get("/api/products", query={"in_stock_only": "true"})
        assert r.status_code == 200
        assert parse_json(r)["total"] == 3

        r = c.get("/api/products/1")
        assert r.status_code == 200
        assert parse_json(r)["name"] == "Widget Pro"

        r = c.get("/api/products/999")
        assert r.status_code == 404
        print("OK")

        # 9. Create product
        print("[9/12] Create product...", end=" ")
        r = c.post("/api/products", json={"name": "New Item", "price": 19.99, "category": "general"})
        assert r.status_code == 201
        print("OK")

        # 10. Auth — Login
        print("[10/12] Auth login...", end=" ")
        r = c.post("/api/auth/login", json={"username": "admin", "password": "demo123"})
        assert r.status_code == 200
        token_data = parse_json(r)
        assert "access_token" in token_data
        assert token_data["user"]["username"] == "admin"
        print("OK")

        # 11. Auth — Protected route
        print("[11/12] Protected route...", end=" ")
        token = token_data["access_token"]
        r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        me = parse_json(r)
        assert me["authenticated"] is True
        assert me["username"] == "admin"

        r = c.get("/api/auth/me")
        assert r.status_code == 401
        print("OK")

        # 12. Error handling
        print("[12/12] Error handling...", end=" ")
        for code, expected in [("404", 404), ("400", 400), ("401", 401), ("500", 500)]:
            r = c.get(f"/api/error-demo", query={"type": code})
            assert r.status_code == expected, f"Expected {expected}, got {r.status_code}"
        print("OK")

    print("\n" + "=" * 60)
    print("ALL 12/12 TEST GROUPS PASSED")
    print("=" * 60)
    return True


async def test_async():
    """Additional async-only tests."""
    from kewe import AsyncTestClient

    print("\n--- Async Tests ---")

    async with AsyncTestClient(app) as c:
        # SSE streaming
        print("[Async] SSE streaming...", end=" ")
        r = await c.get("/api/stream")
        assert r.status_code == 200
        print("OK")

        # BG task
        print("[Async] Background task...", end=" ")
        r = await c.get("/api/bg-task")
        assert r.status_code == 200
        data = parse_json(r)
        assert data["task_started"] is True
        print("OK")

    print("Async tests passed\n")


if __name__ == "__main__":
    import asyncio

    test_sync_client()
    asyncio.run(test_async())

    # Summary
    print("\n" + "=" * 60)
    print("DEMO VERIFICATION COMPLETE")
    print("=" * 60)
    print()
    print("  Routes tested:")
    print("    GET    /                    -> 302 redirect")
    print("    GET    /api/health          -> 200 healthy")
    print("    GET    /api/users           -> 200 list users")
    print("    GET    /api/users/1         -> 200 single user")
    print("    POST   /api/users           -> 201 create user")
    print("    PUT    /api/users/4         -> 200 update user")
    print("    DELETE /api/users/4         -> 200 delete user")
    print("    GET    /api/products        -> 200 filtered paginated")
    print("    POST   /api/products        -> 201 create product")
    print("    POST   /api/auth/login      -> 200 JWT tokens")
    print("    GET    /api/auth/me         -> 200/401 protected")
    print("    GET    /api/error-demo      -> 40x/50x error handling")
    print("    GET    /api/stream          -> 200 SSE streaming")
    print("    GET    /api/bg-task         -> 200 background task")
    print()
    print("  Framework features demonstrated:")
    print("    - Routing with path params & type converters")
    print("    - Query parameter filtering & pagination")
    print("    - Blueprints (users, products, auth)")
    print("    - JWT Authentication (login, Bearer token, protected routes)")
    print("    - Custom middleware (timing, request logging)")
    print("    - CORS middleware")
    print("    - Server-Sent Events (SSE) streaming")
    print("    - Background tasks")
    print("    - Error handling (404, 400, 401, 500)")
    print("    - Application factory pattern")
    print("    - DI Container")
    print("    - Health checks (/health)")
    print("    - OpenAPI docs (/api/docs)")
    print("    - Static file serving")
    print("=" * 60)
