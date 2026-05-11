"""Cache demo blueprint — demonstrates basic + advanced KeWe caching features."""

import time
import asyncio
from kewe import Blueprint, Request, json
from kewe.cache import CacheManager
from kewe.cache.decorators import cache, memoize, cache_response
from kewe.cache.advanced import LFUCache, BloomFilter, AdvancedCacheManager

cache_bp = Blueprint("cache", url_prefix="/api/cache")

# Global cache manager with memory backend
cache_mgr = CacheManager(backend="memory")

# Advanced cache manager (LFU + BloomFilter)
advanced_cache = AdvancedCacheManager(cache_type="lfu", max_size=100)

# Bloom filter for cache key existence check
bloom = BloomFilter(size=10000, error_rate=0.01)


# ---- Basic Cache API ----
@cache_bp.get("/status")
async def cache_status():
    """Show cache statistics."""
    backend = cache_mgr.get_backend()
    stats = getattr(backend, "stats", lambda: {} )() if hasattr(backend, "stats") else {}
    return json({"backend": "memory", "stats": stats})


@cache_bp.get("/get/{key:str}")
async def cache_get(key: str):
    """Get a value from cache by key."""
    value = cache_mgr.get(key)
    if value is None:
        return json({"key": key, "found": False, "value": None})
    return json({"key": key, "found": True, "value": str(value)})


@cache_bp.post("/set/{key:str}")
async def cache_set(key: str, request):
    """Set a value in cache with optional TTL."""
    body = await request.json
    value = body.get("value", "")
    ttl = body.get("ttl")  # None = no expiry
    cache_mgr.set(key, value, ttl=ttl)
    bloom.add(key)
    return json({"key": key, "set": True, "ttl": ttl})


@cache_bp.delete("/delete/{key:str}")
async def cache_delete(key: str):
    """Delete a key from cache."""
    cache_mgr.delete(key)
    return json({"key": key, "deleted": True})


# ---- Decorator-based Caching Demo ----
_expensive_call_count = 0


@cache_bp.get("/decorator")
async def cached_endpoint():
    """Endpoint that uses manual caching — results cached for 30 seconds."""
    global _expensive_call_count
    cache_key = "demo:cached_endpoint"

    # Check Bloom filter first (probabilistic fast-path)
    if bloom.contains(cache_key):
        cached = cache_mgr.get(cache_key)
        if cached is not None:
            return json({"data": cached, "cached": True, "bloom_filter_hit": True})

    _expensive_call_count += 1
    await asyncio.sleep(0.5)  # simulate heavy work
    result = {
        "message": "Freshly computed result",
        "computed_at": time.time(),
        "call_number": _expensive_call_count,
    }
    cache_mgr.set(cache_key, result, ttl=30)
    bloom.add(cache_key)
    return json({"data": result, "cached": False, "bloom_filter_hit": False})


# ---- @memoize Decorator Demo ----
_memoize_calls = 0


@cache_bp.get("/memoize")
@memoize(maxsize=64, ttl=30)
async def memoized_endpoint(request):
    """This endpoint is memoized — same params return cached result."""
    global _memoize_calls
    _memoize_calls += 1
    await asyncio.sleep(0.2)  # simulate work
    return json({"result": f"Computed result #{_memoize_calls}", "cached": False, "note": "Next call with same params returns cached"})


# ---- @cache_response Decorator Demo ----
_cache_response_calls = 0


@cache_bp.get("/cache-response")
@cache_response(ttl=20, key_prefix="kewe:demo")
async def cache_response_endpoint(request):
    """This entire response is cached for 20 seconds."""
    global _cache_response_calls
    _cache_response_calls += 1
    await asyncio.sleep(0.15)
    return json({
        "computed_at": time.time(),
        "call_number": _cache_response_calls,
        "note": "Response is cached for 20s via @cache_response",
        "cached": False,
    })


@cache_bp.get("/decorator-stats")
async def decorator_stats():
    """Show decorator usage statistics."""
    return json({
        "memoize_calls": _memoize_calls,
        "cache_response_calls": _cache_response_calls,
        "expensive_calls": _expensive_call_count,
        "decorators_used": ["@memoize", "@cache_response", "manual cache with BloomFilter"],
    })


# ---- Advanced Cache (LFU) Demo ----
@cache_bp.get("/advanced/status")
async def advanced_cache_status():
    """Show advanced cache status."""
    stats = {
        "cache_type": "LFU (Least Frequently Used)",
        "max_size": advanced_cache.cache.max_size,
        "cache_entries": len(getattr(advanced_cache.cache, '_cache', {})),
        "bloom_filter_size": advanced_cache.bloom_filter.size,
        "bloom_filter_hash_count": advanced_cache.bloom_filter.hash_count,
        "estimated_error_rate": 2 ** (-advanced_cache.bloom_filter.hash_count),
    }
    return json(stats)


@cache_bp.get("/advanced/get/{key:str}")
async def advanced_cache_get(key: str, request: Request):
    """Get a value from advanced cache (LFU) with loader + BloomFilter."""
    # Define a loader that would fetch from DB in production
    async def expensive_loader():
        await asyncio.sleep(0.2)
        return {
            "key": key,
            "value": f"Loaded value for '{key}'",
            "loaded_at": time.time(),
            "source": "expensive_loader",
        }

    result = await advanced_cache.get(key, loader=expensive_loader, use_bloom=True)
    is_cached = not isinstance(result, dict) or result.get("source") != "expensive_loader"
    return json({"key": key, "data": result, "from_cache": is_cached})


@cache_bp.post("/advanced/set/{key:str}")
async def advanced_cache_set(key: str, request):
    """Set a value in advanced cache (LFU)."""
    body = await request.json
    value = body.get("value", "")
    await advanced_cache.cache.set(key, value)
    advanced_cache.bloom_filter.add(key)
    return json({"key": key, "set": True, "cache_type": "LFU"})


@cache_bp.get("/advanced/bloom-filter")
async def bloom_filter_demo():
    """BloomFilter demonstration."""
    test_keys = ["alpha", "beta", "gamma", "delta", "epsilon"]
    present = []
    for k in test_keys:
        bloom.add(k)
        present.append({"key": k, "probably_present": bloom.contains(k)})

    absent = []
    for k in ["unknown-x", "unknown-y", "unknown-z"]:
        absent.append({"key": k, "probably_present": bloom.contains(k)})

    return json({
        "bloom_filter_stats": {
            "size": bloom.size,
            "hash_count": bloom.hash_count,
            "memory_bytes": len(bloom.bit_array),
            "estimated_error_rate": f"{2 ** (-bloom.hash_count):.6f}",
        },
        "keys_added": present,
        "keys_not_added": absent,
        "note": "Bloom filter guarantees: no false negatives, possible false positives",
    })


@cache_bp.get("/stats")
async def cache_stats():
    """Show detailed cache and call statistics."""
    return json({
        "expensive_calls": _expensive_call_count,
        "backend_type": "memory",
        "advanced_cache_type": "LFU",
        "bloom_filter_enabled": True,
    })
