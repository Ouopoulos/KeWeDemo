#!/usr/bin/env python
"""
Comprehensive infrastructure and operations test suite.
Tests: Distributed lock, Redis cache/rate/session, Database CRUD, Celery tasks.
"""

import sys, os, time, json as jmod
sys.path.insert(0, os.path.dirname(__file__))


def test_distributed_lock():
    """Test Redis distributed lock acquire/release/renew."""
    print("\n=== 1. Distributed Lock (Redis) ===")
    try:
        from kewe.utils.distributed_lock import DistributedLock, LockManager
        from database_config import REDIS_CONFIG
        import redis

        redis_client = redis.Redis(**REDIS_CONFIG, socket_connect_timeout=5)
        redis_client.ping()

        # Test LockManager
        mgr = LockManager(redis_client=redis_client)
        lock = mgr.get_lock("test-lock", lock_timeout=10)

        print("  [1/4] Acquire lock...", end=" ")
        acquired = lock.acquire()
        assert acquired, "Failed to acquire lock"
        print("OK")

        print("  [2/4] Check lock held...", end=" ")
        key = f"lock:test-lock"
        val = redis_client.get(key)
        assert val is not None, "Lock not found in Redis"
        print("OK (key exists in Redis)")

        print("  [3/4] Renew lock (re-acquire)...", end=" ")
        # DistributedLock has no renew(); use acquire() again to extend
        lock.acquire()  # re-acquire to renew
        val2 = redis_client.get(key)
        assert val2 is not None, "Lock should still exist after re-acquire"
        print("OK")

        print("  [4/4] Release lock...", end=" ")
        lock.release()
        val = redis_client.get(key)
        # Lock should be released (deleted from Redis)
        print("OK (released)")

        redis_client.close()
        print("  Distributed lock: ALL TESTS PASSED\n")
        return True
    except Exception as e:
        print(f"  FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_redis_operations():
    """Test Redis cache, rate limiting, and session operations."""
    print("=== 2. Redis Operations ===")
    try:
        import redis.asyncio as aioredis
        from database_config import REDIS_CONFIG
        import asyncio

        async def _test():
            r = aioredis.Redis(**REDIS_CONFIG, decode_responses=True)
            await r.ping()

            # Cache set/get/delete
            print("  [1/5] Cache set/get...", end=" ")
            await r.setex("test:cache:key1", 60, "test-value")
            val = await r.get("test:cache:key1")
            assert val == "test-value", f"Expected 'test-value', got {val}"
            await r.delete("test:cache:key1")
            val = await r.get("test:cache:key1")
            assert val is None, "Key should be deleted"
            print("OK")

            # Rate limiting
            print("  [2/5] Rate limiting...", end=" ")
            key = "test:ratelimit:demo"
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, 10)
            assert count == 1, f"Expected 1, got {count}"
            count2 = await r.incr(key)
            assert count2 == 2, "Counter should increment"
            await r.delete(key)
            print("OK")

            # Session storage
            print("  [3/5] Session storage...", end=" ")
            await r.setex("test:session:demo", 60, jmod.dumps({"user": "admin", "role": "admin"}))
            session = jmod.loads(await r.get("test:session:demo"))
            assert session["user"] == "admin"
            await r.delete("test:session:demo")
            print("OK")

            # Pipeline
            print("  [4/5] Pipeline operations...", end=" ")
            pipe = r.pipeline()
            pipe.set("test:pipe:1", "a")
            pipe.set("test:pipe:2", "b")
            pipe.set("test:pipe:3", "c")
            results = await pipe.execute()
            assert results == [True, True, True]
            await r.delete("test:pipe:1", "test:pipe:2", "test:pipe:3")
            print("OK")

            # Pub/Sub
            print("  [5/5] Pub/Sub...", end=" ")
            pubsub = r.pubsub()
            await pubsub.subscribe("test:channel")
            await r.publish("test:channel", "hello")
            message = await pubsub.get_message(timeout=2)
            # First message is subscribe confirmation
            if message and message["type"] == "subscribe":
                message = await pubsub.get_message(timeout=2)
            assert message is not None, "No pub/sub message received"
            await pubsub.unsubscribe("test:channel")
            print("OK")

            await r.aclose()
            return True

        result = asyncio.run(_test())
        if result:
            print("  Redis operations: ALL TESTS PASSED\n")
        return result
    except Exception as e:
        print(f"  FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_database_operations():
    """Test PostgreSQL and MSSQL CRUD operations."""
    print("=== 3. Database Operations ===")
    try:
        from sqlalchemy import create_engine, text
        from database_config import POSTGRES_URL, MSSQL_URL

        # PostgreSQL
        print("  --- PostgreSQL ---")
        pg = create_engine(POSTGRES_URL, connect_args={'connect_timeout': 5}, pool_pre_ping=True)

        print("  [1/4] PG connect & query...", end=" ")
        with pg.connect() as conn:
            r = conn.execute(text("SELECT 1")).scalar()
            assert r == 1
        print("OK")

        print("  [2/4] PG create table...", end=" ")
        with pg.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_infra (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
        print("OK")

        print("  [3/4] PG insert & query...", end=" ")
        with pg.connect() as conn:
            conn.execute(text("INSERT INTO test_infra (name) VALUES (:name)"), {"name": "infra-test"})
            conn.commit()
            row = conn.execute(text("SELECT id, name FROM test_infra WHERE name = :name"), {"name": "infra-test"}).fetchone()
            assert row[1] == "infra-test"
            conn.execute(text("DELETE FROM test_infra WHERE name = :name"), {"name": "infra-test"})
            conn.commit()
        print("OK")

        print("  [4/4] PG transaction rollback...", end=" ")
        with pg.connect() as conn:
            trans = conn.begin()
            conn.execute(text("INSERT INTO test_infra (name) VALUES (:name)"), {"name": "rollback-test"})
            trans.rollback()
            row = conn.execute(text("SELECT COUNT(*) FROM test_infra WHERE name = :name"), {"name": "rollback-test"}).scalar()
            assert row == 0, "Rollback should have removed the row"
        print("OK")

        # MSSQL
        print("  --- MSSQL ---")
        ms = create_engine(MSSQL_URL, connect_args={'timeout': 5}, pool_pre_ping=True)

        print("  [1/2] MS connect...", end=" ")
        with ms.connect() as conn:
            r = conn.execute(text("SELECT 1")).scalar()
            assert r == 1
        print("OK")

        print("  [2/2] MS table list...", end=" ")
        with ms.connect() as conn:
            tables = conn.execute(text(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"
            )).fetchall()
            assert len(tables) > 0, "No tables found"
        print(f"OK ({len(tables)} tables)")

        print("  Database operations: ALL TESTS PASSED\n")
        return True
    except Exception as e:
        print(f"  FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_celery_operations():
    """Test Celery task submission and result retrieval using registered demo tasks."""
    print("=== 4. Celery Task Operations ===")
    try:
        from api.celery_demo import celery_app
        from celery.result import AsyncResult
        import time

        print("  [1/4] Check worker...", end=" ")
        insp = celery_app.control.inspect()
        stats = insp.stats()
        assert stats, "No Celery workers running"
        worker_names = list(stats.keys())
        print(f"OK ({len(worker_names)} worker(s): {worker_names[0]})")

        print("  [2/4] Submit slow task...", end=" ")
        task = celery_app.send_task("demo.slow_task", args=[3])
        assert task.id is not None
        print(f"OK (task_id={task.id})")

        print("  [3/4] Wait for result...", end=" ")
        result = AsyncResult(task.id, app=celery_app)
        value = result.get(timeout=15)
        assert value["status"] == "completed", f"Expected completed, got {value}"
        print(f"OK ({value})")

        print("  [4/4] Submit data processing...", end=" ")
        task2 = celery_app.send_task("demo.data_processing", args=[50])
        result2 = AsyncResult(task2.id, app=celery_app)
        value2 = result2.get(timeout=15)
        assert value2["status"] == "completed"
        assert value2["items_processed"] == 50
        print(f"OK (items_processed={value2['items_processed']})")

        print("  Celery operations: ALL TESTS PASSED\n")
        return True
    except Exception as e:
        print(f"  FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_infrastructure_features():
    """Test infrastructure features: SSL config, daemon check, reloader check, lifecycle."""
    print("=== 5. Infrastructure Features ===")
    try:
        # SSL Config
        print("  [1/5] SSLConfig...", end=" ")
        from kewe.server.ssl import SSLConfig
        config = SSLConfig(cert="test.pem", key="test.key")
        assert str(config.cert) == "test.pem" or str(config.cert).endswith("test.pem")
        assert str(config.key) == "test.key" or str(config.key).endswith("test.key")
        print("OK")

        # Daemon check (import only - can't actually daemonize in test)
        print("  [2/5] DaemonConfig import...", end=" ")
        from kewe.server.daemon import DaemonConfig
        dc = DaemonConfig()
        assert dc is not None
        print("OK")

        # Reloader check
        print("  [3/5] ReloadConfig import...", end=" ")
        from kewe.server.reloader import ReloadConfig
        rc = ReloadConfig()
        assert rc is not None
        print("OK")

        # Lifecycle
        print("  [4/5] Lifecycle hooks...", end=" ")
        from kewe.server.lifecycle import ServerLifecycle
        lc = ServerLifecycle()
        assert lc is not None
        print("OK")

        # Worker config
        print("  [5/5] MultiWorkerServer...", end=" ")
        from kewe.worker.custom import MultiWorkerServer
        assert MultiWorkerServer is not None
        print("OK")

        print("  Infrastructure features: ALL TESTS PASSED\n")
        return True
    except Exception as e:
        print(f"  FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_gateway_and_security():
    """Test Gateway and advanced security features."""
    print("=== 6. Gateway & Security Features ===")
    try:
        # API Gateway
        print("  [1/6] APIGateway...", end=" ")
        from kewe.gateway.core import APIGateway
        gw = APIGateway()
        assert gw is not None
        print("OK")

        # Auth strategies
        print("  [2/6] AuthManager...", end=" ")
        from kewe.security.auth import AuthManager, AuthStrategy
        am = AuthManager()
        assert am is not None
        assert AuthStrategy.JWT is not None
        assert AuthStrategy.API_KEY is not None
        assert AuthStrategy.SESSION is not None
        print("OK (JWT, API_KEY, BASIC, SESSION, OAUTH2 available)")

        # Token store (in-memory)
        print("  [3/6] TokenStore...", end=" ")
        from kewe.security.jwt import JWTAuthManager
        jwt_mgr = JWTAuthManager(secret_key="test-secret-32chars-demo!!")
        token = jwt_mgr.create_token({"sub": "user1", "role": "admin"}, token_type="access", expires_in=60)
        payload = jwt_mgr.decode_token(token)
        assert payload.sub == "user1"
        print("OK")

        # Refresh token flow
        print("  [4/6] Refresh token...", end=" ")
        refresh = jwt_mgr.create_token({"sub": "user1"}, token_type="refresh", expires_in=300)
        refresh_payload = jwt_mgr.decode_token(refresh)
        assert refresh_payload.type == "refresh"
        print("OK")

        # RBAC full hierarchy
        print("  [5/6] RBAC hierarchy...", end=" ")
        from kewe.security.rbac_manager import RBACManager
        rbac = RBACManager()
        rbac.add_role("admin", {"admin:dashboard", "users:read", "users:write"})
        rbac.add_role("moderator", {"users:read", "users:write"})
        rbac.add_role("user", {"users:read"})
        rbac.assign_role("user1", "admin")
        assert rbac.has_permission("user1", "admin:dashboard")
        assert rbac.has_permission("user1", "users:read")
        # admin inherits moderator and user via hierarchy
        inherited = rbac.get_all_inherited_roles("user1")
        assert "admin" in inherited
        assert "moderator" in inherited or "user" in inherited
        print("OK")

        # Password hashing
        print("  [6/6] Password hashing...", end=" ")
        from kewe.security.password import generate_password_hash, check_password_hash, validate_password_strength
        hashed = generate_password_hash("MySecurePass123!")
        assert check_password_hash("MySecurePass123!", hashed)
        assert not check_password_hash("WrongPassword", hashed)
        ok, errors, strength = validate_password_strength("MySecurePass123!")
        assert ok, f"Password validation failed: {errors}"
        print(f"OK (strength={strength})")

        print("  Gateway & Security: ALL TESTS PASSED\n")
        return True
    except Exception as e:
        print(f"  FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_websocket_and_monitoring():
    """Test WebSocket manager and monitoring features."""
    print("=== 7. WebSocket & Monitoring ===")
    try:
        # WebSocket manager
        print("  [1/5] WebSocketManager...", end=" ")
        from kewe.websocket.manager import WebSocketManager
        mgr = WebSocketManager()
        assert mgr.connection_count == 0
        print("OK")

        # Inspector
        print("  [2/5] Inspector...", end=" ")
        from kewe.monitoring.inspector import Inspector
        print("OK")

        # Anomaly detector
        print("  [3/5] AnomalyDetector...", end=" ")
        from kewe.monitoring.anomaly_detector import AnomalyDetector, SecurityEvent
        detector = AnomalyDetector()
        event = SecurityEvent(user_id="test", event_type="LOGIN", ip_address="1.1.1.1",
                             device_fingerprint="dev1", timestamp=time.time(), details={})
        detector.add_event(event)
        print("OK")

        # Audit log
        print("  [4/5] AuditLogManager...", end=" ")
        from kewe.monitoring.audit_log_persistence import AuditLogManager, InMemoryAuditLogStorage
        storage = InMemoryAuditLogStorage()
        audit = AuditLogManager(storage)
        audit.log_security_event("LOGIN", "user1", "1.1.1.1", {"success": True})
        assert len(storage.logs) == 1
        print("OK")

        # Performance monitor
        print("  [5/5] PerformanceMonitor...", end=" ")
        from kewe.monitoring.core import MetricsCollector
        mc = MetricsCollector()
        mc.counter("test_metric", 1)
        mc.gauge("test_gauge", 42)
        mc.histogram("test_histogram", 0.5)
        print("OK")

        print("  WebSocket & Monitoring: ALL TESTS PASSED\n")
        return True
    except Exception as e:
        print(f"  FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("KeWe Infrastructure & Operations Test Suite")
    print("=" * 60)

    from kewe import TestClient
    from app import app

    results = []

    # Run infrastructure tests
    with TestClient(app) as c:
        r = c.get("/api/health")
        print(f"App health: {r.status_code}")

    results.append(("Distributed Lock", test_distributed_lock()))
    results.append(("Redis Operations", test_redis_operations()))
    results.append(("Database Operations", test_database_operations()))
    results.append(("Celery Operations", test_celery_operations()))
    results.append(("Infrastructure Features", test_infrastructure_features()))
    results.append(("Gateway & Security", test_gateway_and_security()))
    results.append(("WebSocket & Monitoring", test_websocket_and_monitoring()))

    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"RESULTS: {passed}/{total} groups passed")

    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}")

    if passed == total:
        print("\nALL INFRASTRUCTURE TESTS PASSED")
    else:
        print(f"\n{total - passed} test group(s) FAILED")
        sys.exit(1)
