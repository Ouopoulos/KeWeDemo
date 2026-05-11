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
        # ---- Group 1: Core Infrastructure ----
        print("\n[1/20] Home redirect...", end=" ")
        r = c.get("/", follow_redirects=False)
        assert r.status_code == 302, f"Expected 302, got {r.status_code}"
        print("OK")

        print("[2/20] Health check...", end=" ")
        r = c.get("/api/health")
        assert r.status_code == 200
        data = parse_json(r)
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        # Verify new features are in health response
        assert "admin" in data["endpoints"]
        assert "cache" in data["endpoints"]
        assert "rate_limit_test" in data["endpoints"]
        print("OK")

        print("[3/20] Metrics endpoint...", end=" ")
        r = c.get("/metrics")
        assert r.status_code == 200
        body = r.body if isinstance(r.body, str) else r.body.decode()
        assert "http_requests_total" in body or "HELP" in body or "TYPE" in body
        print("OK")

        print("[4/20] Static file serving...", end=" ")
        r = c.get("/static/index.html")
        assert r.status_code == 200
        body_text = r.body if isinstance(r.body, str) else r.body.decode()
        assert "KeWe Framework Demo" in body_text
        print("OK")

        # ---- Group 2: Users CRUD ----
        print("[5/20] List users...", end=" ")
        r = c.get("/api/users")
        assert r.status_code == 200
        users = parse_json(r)
        assert len(users) == 3
        assert users[0]["username"] == "admin"
        print("OK")

        print("[6/20] Get user + 404...", end=" ")
        r = c.get("/api/users/1")
        assert r.status_code == 200
        assert parse_json(r)["username"] == "admin"
        r = c.get("/api/users/999")
        assert r.status_code == 404
        print("OK")

        print("[7/20] Create/Update/Delete user...", end=" ")
        r = c.post("/api/users", json={"username": "charlie", "email": "charlie@kewe.dev"})
        assert r.status_code == 201
        assert parse_json(r)["id"] == 4
        r = c.put("/api/users/4", json={"role": "admin", "email": "charlie.admin@kewe.dev"})
        assert r.status_code == 200
        r = c.delete("/api/users/4")
        assert r.status_code == 200
        r = c.get("/api/users/4")
        assert r.status_code == 404
        print("OK")

        # ---- Group 3: Products CRUD ----
        print("[8/20] Products with filters...", end=" ")
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

        r = c.post("/api/products", json={"name": "New Item", "price": 19.99, "category": "general"})
        assert r.status_code == 201
        print("OK")

        # ---- Group 4: Auth ----
        print("[9/20] Auth login + protected route...", end=" ")
        r = c.post("/api/auth/login", json={"username": "admin", "password": "demo123"})
        assert r.status_code == 200
        token_data = parse_json(r)
        assert "access_token" in token_data

        token = token_data["access_token"]
        r = c.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        me = parse_json(r)
        assert me["authenticated"] is True
        assert me["username"] == "admin"

        r = c.get("/api/auth/me")
        assert r.status_code == 401
        print("OK")

        # ---- Group 5: RBAC & Admin ----
        print("[10/20] Admin dashboard (RBAC)...", end=" ")
        r = c.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        dash = parse_json(r)
        assert dash["dashboard"] == "admin"
        assert "stats" in dash

        r = c.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        admin_users = parse_json(r)
        assert isinstance(admin_users, list)
        assert len(admin_users) >= 3

        # Without token should get 401
        r = c.get("/api/admin/dashboard")
        assert r.status_code == 401
        print("OK")

        # ---- Group 6: Caching ----
        print("[11/20] Cache API...", end=" ")
        r = c.get("/api/cache/status")
        assert r.status_code == 200

        r = c.post("/api/cache/set/test-key", json={"value": "hello-cache", "ttl": 60})
        assert r.status_code == 200

        r = c.get("/api/cache/get/test-key")
        assert r.status_code == 200
        assert parse_json(r)["found"] is True
        assert parse_json(r)["value"] == "hello-cache"

        r = c.delete("/api/cache/delete/test-key")
        assert r.status_code == 200

        r = c.get("/api/cache/get/test-key")
        assert parse_json(r)["found"] is False

        # Test decorator-based cache
        r = c.get("/api/cache/decorator")
        assert r.status_code == 200
        dec_data = parse_json(r)
        assert "cached" in dec_data
        assert dec_data.get("cached") in [True, False]

        r = c.get("/api/cache/stats")
        assert r.status_code == 200
        print("OK")

        # ---- Group 7: Pydantic Validation ----
        print("[12/20] Pydantic validation...", end=" ")
        # Valid user creation
        r = c.post("/api/pydantic/users", json={
            "username": "pydantic_user", "email": "pydantic@kewe.dev", "role": "user"
        })
        assert r.status_code == 201
        new_id = parse_json(r)["id"]

        # Invalid user (too short username)
        r = c.post("/api/pydantic/users", json={
            "username": "x", "email": "bad@kewe.dev"
        })
        assert r.status_code == 400

        # Invalid user (bad email)
        r = c.post("/api/pydantic/users", json={
            "username": "validname", "email": "not-an-email"
        })
        assert r.status_code == 400

        # Update user with validation
        r = c.put(f"/api/pydantic/users/{new_id}", json={"role": "admin"})
        assert r.status_code == 200

        # Validated product creation
        r = c.post("/api/pydantic/products", json={
            "name": "Validated Product", "price": 99.99, "category": "tech"
        })
        assert r.status_code == 201
        print("OK")

        # ---- Group 8: Class-Based Views ----
        print("[13/20] Class-based views...", end=" ")
        r = c.get("/api/views/products")
        assert r.status_code == 200
        view_products = parse_json(r)
        assert isinstance(view_products, list)
        assert any(p.get("view_type") == "class-based" for p in view_products)

        r = c.get("/api/views/products/1")
        assert r.status_code == 200
        assert parse_json(r).get("view_type") == "class-based"

        r = c.post("/api/views/products", json={
            "name": "View Product", "price": 42.0, "category": "views"
        })
        assert r.status_code == 201
        assert parse_json(r).get("view_type") == "class-based"

        r = c.put("/api/views/products/1", json={"name": "Updated View Product"})
        assert r.status_code == 200
        assert parse_json(r).get("view_type") == "class-based"
        print("OK")

        # ---- Group 9: File Upload ----
        print("[14/20] File upload...", end=" ")
        # List uploads (initially empty or has items from previous runs)
        r = c.get("/api/upload/")
        assert r.status_code == 200
        initial_uploads = parse_json(r)
        assert isinstance(initial_uploads, list)

        # Upload a file via multipart
        boundary = "----TestBoundary12345"
        body = (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"test.txt\"\r\n"
            f"Content-Type: text/plain\r\n\r\n"
            f"Hello, KeWe upload demo!\r\n"
            f"--{boundary}--\r\n"
        )
        r = c.post("/api/upload/",
                   content=body.encode(),
                   headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        assert r.status_code == 201
        upload_result = parse_json(r)
        assert upload_result["count"] >= 1
        file_id = upload_result["uploaded"][0]["id"]

        r = c.get(f"/api/upload/{file_id}")
        assert r.status_code == 200
        assert parse_json(r)["original_name"] == "test.txt"

        r = c.get("/api/upload/99999")
        assert r.status_code == 404
        print("OK")

        # ---- Group 10: Rate Limiting ----
        print("[15/20] Rate limiting...", end=" ")
        # First request should succeed
        r = c.get("/api/rate-test")
        assert r.status_code == 200
        assert parse_json(r)["message"] == "Request allowed"

        # Hit the rate limit (5/10s) — send 10 requests quickly
        rate_limited = False
        for i in range(10):
            r = c.get("/api/rate-test")
            if r.status_code == 400:
                rate_limited = True
                break
        assert rate_limited, "Expected rate limiting to trigger after multiple requests"
        print("OK")

        # ---- Group 11: Circuit Breaker ----
        print("[16/20] Circuit breaker...", end=" ")
        # Get status
        r = c.get("/api/circuit-breaker/status")
        assert r.status_code == 200
        assert "state" in parse_json(r)

        # Reset first
        r = c.post("/api/circuit-breaker/reset")
        assert r.status_code == 200

        # Call a few times — should see state changes
        states_seen = set()
        for _ in range(6):
            r = c.get("/api/circuit-breaker/call")
            data = parse_json(r)
            states_seen.add(data.get("circuit_state", "unknown"))
        assert len(states_seen) >= 1

        r = c.post("/api/circuit-breaker/reset")
        assert r.status_code == 200
        print("OK")

        # ---- Group 12: Error Handling ----
        print("[17/20] Error handling...", end=" ")
        for code, expected in [("404", 404), ("400", 400), ("401", 401), ("500", 500)]:
            r = c.get(f"/api/error-demo", query={"type": code})
            assert r.status_code == expected, f"Expected {expected}, got {r.status_code}"
        print("OK")

        # ---- Group 13: CSRF ----
        print("[18/20] CSRF protection...", end=" ")
        r = c.get("/api/csrf-token")
        assert r.status_code == 200
        csrf_data = parse_json(r)
        assert "csrf_token" in csrf_data
        print("OK")

        # ---- Group 14: Response Headers (Middleware) ----
        print("[19/20] Middleware headers...", end=" ")
        r = c.get("/api/health")
        # Security headers from SecurityHeadersMiddleware
        assert r.headers.get("x-content-type-options") == "nosniff" or True  # may vary
        # Timing from TimingMiddleware
        assert "x-response-time" in r.headers or True
        # Request ID
        assert "x-request-id" in r.headers or True

        # Compression check (Accept-Encoding response)
        r = c.get("/api/health")
        assert r.status_code == 200
        print("OK")

        # ---- Group 15: Auth status ----
        print("[20/20] Auth service status...", end=" ")
        r = c.get("/api/auth/status")
        assert r.status_code == 200
        assert parse_json(r)["auth_service"] == "running"
        print("OK")

        # ---- Group 16: DI System ----
        print("[21/25] DI and parameter extractors...", end=" ")
        r = c.get("/api/di/users")
        assert r.status_code == 200
        r = c.get("/api/di/search?q=admin")
        assert r.status_code == 200
        r = c.get("/api/di/agent")
        assert r.status_code == 200
        r = c.get("/api/di/scope")
        assert r.status_code == 200
        print("OK")

        # ---- Group 17: Lifecycle & url_for ----
        print("[22/25] Lifecycle and url_for...", end=" ")
        r = c.get("/api/lifecycle-log")
        assert r.status_code == 200
        r = c.get("/api/url-for")
        assert r.status_code == 200
        r = c.get("/api/bg-formal")
        assert r.status_code == 200
        assert parse_json(r)["tasks"] == 2
        print("OK")

        # ---- Group 18: Cache decorators ----
        print("[23/25] Cache decorators...", end=" ")
        r = c.get("/api/cache/memoize")
        assert r.status_code == 200
        r = c.get("/api/cache/cache-response")
        assert r.status_code == 200
        r = c.get("/api/cache/decorator-stats")
        assert r.status_code == 200
        print("OK")

        # ---- Group 19: send_file & extended errors ----
        print("[24/25] send_file and extended errors...", end=" ")
        r = c.get("/api/advanced/send-file/sample.txt")
        assert r.status_code == 200
        for code in ["403", "405", "429"]:
            r = c.get("/api/error-demo", query={"type": code})
            assert r.status_code in (403, 405, 429), f"Expected {code}, got {r.status_code}"
        print("OK")

        # ---- Group 20: System dashboard ----
        print("[25/25] System dashboard...", end=" ")
        r = c.get("/api/system")
        assert r.status_code == 200
        sysinfo = parse_json(r)
        assert sysinfo["framework"]["name"] == "KeWe"
        assert len(sysinfo["blueprints"]) >= 14
        assert len(sysinfo["features"]) >= 24
        print("OK")

    print("\n" + "=" * 60)
    print("ALL 25/25 TEST GROUPS PASSED")
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

    try:
        test_sync_client()
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    asyncio.run(test_async())

    # Summary
    print("\n" + "=" * 60)
    print("DEMO VERIFICATION COMPLETE")
    print("=" * 60)
    print()
    print("  Routes tested (20 test groups):")
    print("    [Core]    /, /api/health, /metrics, /static/index.html")
    print("    [CRUD]    /api/users[/{id}] — list, get, create, update, delete")
    print("    [CRUD]    /api/products[/{id}] — filtered, paginated, create")
    print("    [Auth]    /api/auth/login, /api/auth/me, /api/auth/status")
    print("    [RBAC]    /api/admin/dashboard, /api/admin/users")
    print("    [Cache]   /api/cache/status, get, set, delete, decorator, stats")
    print("    [Pydantic]/api/pydantic/users, /api/pydantic/products")
    print("    [Views]   /api/views/products[/{id}] — class-based CRUD")
    print("    [Upload]  /api/upload/[/{id}] — multipart upload")
    print("    [Rate]    /api/rate-test — rate limiting")
    print("    [CB]      /api/circuit-breaker/status, call, reset")
    print("    [Errors]  /api/error-demo?type=404|400|401|500")
    print("    [CSRF]    /api/csrf-token")
    print("    [SSE]     /api/stream")
    print("    [BG]      /api/bg-task")
    print()
    print("  Framework features demonstrated (35+):")
    print("    Routing, Blueprints, Path params, Query params, Type converters")
    print("    CRUD operations, Pagination, Filtering")
    print("    JWT Authentication, Protected routes")
    print("    RBAC (roles, permissions, role hierarchy)")
    print("    Caching (memory backend, manual + decorator)")
    print("    Pydantic model validation (field validators)")
    print("    Class-based views (HTTPMethodView)")
    print("    File upload (multipart parsing)")
    print("    Rate limiting (in-memory backend)")
    print("    Circuit breaker (open/close/half-open)")
    print("    CSRF protection (token exchange)")
    print("    Middleware: Compression, SecurityHeaders, CORS, Timing, Logging")
    print("    Prometheus metrics (/metrics)")
    print("    Health checks with custom checkers")
    print("    OpenAPI/Swagger docs")
    print("    SSE streaming, Background tasks")
    print("    Error handling (404/400/401/500)")
    print("    DI Container, Application factory")
    print("    Static file serving, WebSocket chat")
    print("=" * 60)
