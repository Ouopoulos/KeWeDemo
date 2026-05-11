"""Redis integration demo — caching, rate limiting, session storage."""

import redis.asyncio as aioredis
from kewe import Blueprint, Request, json
from kewe.errors.exceptions import BadRequest, NotFound
from database_config import REDIS_CONFIG

redis_bp = Blueprint("redis", url_prefix="/api/redis")

# Async Redis client
redis_client: aioredis.Redis = None


async def get_redis():
    global redis_client
    if redis_client is None:
        redis_client = aioredis.Redis(**REDIS_CONFIG, decode_responses=True)
    return redis_client


@redis_bp.get("/")
async def redis_index():
    return json({
        "status": "connected" if redis_client else "lazy",
        "endpoints": {
            "ping": "GET /api/redis/ping",
            "cache_set": "POST /api/redis/cache/{key}",
            "cache_get": "GET /api/redis/cache/{key}",
            "cache_delete": "DELETE /api/redis/cache/{key}",
            "rate_limit_test": "GET /api/redis/rate-test",
            "session_set": "POST /api/redis/session/{key}",
            "session_get": "GET /api/redis/session/{key}",
            "list_keys": "GET /api/redis/keys?pattern=*",
        }
    })


@redis_bp.get("/ping")
async def redis_ping():
    """Test Redis connectivity."""
    r = await get_redis()
    await r.ping()
    info = await r.info("server")
    return json({
        "ping": "pong",
        "redis_version": info.get("redis_version", "unknown"),
        "connected_clients": info.get("connected_clients", 0),
        "used_memory_human": info.get("used_memory_human", "unknown"),
    })


# ---- Redis Cache ----
@redis_bp.post("/cache/{key:str}")
async def redis_cache_set(key: str, request: Request):
    """Set a value in Redis cache with optional TTL."""
    body = await request.json
    value = body.get("value", "")
    ttl = body.get("ttl")

    r = await get_redis()
    if ttl:
        await r.setex(f"demo:cache:{key}", ttl, str(value))
    else:
        await r.set(f"demo:cache:{key}", str(value))
    return json({"key": key, "set": True, "ttl": ttl})


@redis_bp.get("/cache/{key:str}")
async def redis_cache_get(key: str):
    """Get a value from Redis cache."""
    r = await get_redis()
    value = await r.get(f"demo:cache:{key}")
    ttl = await r.ttl(f"demo:cache:{key}") if value else None
    return json({
        "key": key,
        "found": value is not None,
        "value": value,
        "ttl": ttl,
    })


@redis_bp.delete("/cache/{key:str}")
async def redis_cache_delete(key: str):
    """Delete a key from Redis cache."""
    r = await get_redis()
    await r.delete(f"demo:cache:{key}")
    return json({"key": key, "deleted": True})


# ---- Redis Rate Limiting ----
@redis_bp.get("/rate-test")
async def redis_rate_test(request: Request):
    """Rate-limited endpoint using Redis (5 requests per 10 seconds)."""
    r = await get_redis()
    client_ip = request.headers.get("X-Forwarded-For", "127.0.0.1").split(",")[0].strip()
    key = f"demo:ratelimit:{client_ip}"

    count = await r.incr(key)
    if count == 1:
        await r.expire(key, 10)

    ttl = await r.ttl(key)
    if count > 5:
        raise BadRequest({
            "error": "Redis rate limit exceeded",
            "limit": 5,
            "remaining": 0,
            "retry_after_seconds": ttl,
        })

    return json({
        "message": "Request allowed",
        "limit": 5,
        "remaining": 5 - count,
        "reset_in_seconds": ttl,
    })


# ---- Redis Session ----
@redis_bp.post("/session/{key:str}")
async def redis_session_set(key: str, request: Request):
    """Store session data in Redis."""
    body = await request.json
    r = await get_redis()
    import json as jmod
    await r.setex(f"demo:session:{key}", 600, jmod.dumps(body))
    return json({"session_key": key, "stored": True, "ttl": 600})


@redis_bp.get("/session/{key:str}")
async def redis_session_get(key: str):
    """Retrieve session data from Redis."""
    r = await get_redis()
    import json as jmod
    data = await r.get(f"demo:session:{key}")
    if data is None:
        raise NotFound(f"Session '{key}' not found or expired")
    return json({
        "session_key": key,
        "data": jmod.loads(data) if isinstance(data, str) else data,
        "ttl": await r.ttl(f"demo:session:{key}"),
    })


@redis_bp.get("/keys")
async def redis_keys(request: Request):
    """List Redis keys matching a pattern."""
    pattern = request.query_params.get("pattern", "demo:*")
    r = await get_redis()
    keys = await r.keys(pattern)
    result = []
    for k in keys[:50]:  # limit to 50
        key_type = await r.type(k)
        ttl = await r.ttl(k)
        result.append({"key": k, "type": key_type, "ttl": ttl})
    return json({"pattern": pattern, "count": len(result), "keys": result})
