"""
Redis cache service for analytics endpoints.
Falls back to in-memory cache if Redis is unavailable.
"""

import hashlib
import json
import logging
import time
from typing import Any, Optional

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None
_redis_failed = False  # Flag agar tidak retry terus-menerus
_redis_retry_at: float = 0  # Waktu retry berikutnya

# In-memory cache fallback
_memory_cache: dict = {}


async def get_redis_client() -> Optional[redis.Redis]:
    global _redis_client, _redis_failed, _redis_retry_at

    # Jika Redis sudah gagal, coba lagi setiap 60 detik
    if _redis_failed:
        if time.time() < _redis_retry_at:
            return None
        _redis_failed = False  # Reset untuk retry

    if _redis_client is not None:
        return _redis_client

    try:
        settings = get_settings()
        client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        await client.ping()
        _redis_client = client
        logger.info("Redis connection established")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis tidak tersedia: {e}. Pakai in-memory cache.")
        _redis_failed = True
        _redis_retry_at = time.time() + 60  # Retry setelah 60 detik
        _redis_client = None
        return None


def _generate_cache_key(endpoint: str, params: dict) -> str:
    """
    Generate cache key from endpoint and parameters.
    
    Formula: f"analytics:{endpoint}:{hash(params)}"
    
    Args:
        endpoint: Analytics endpoint name (e.g., "overview", "creators")
        params: Query parameters dictionary
        
    Returns:
        Cache key string
        
    Examples:
        >>> _generate_cache_key("overview", {})
        'analytics:overview:99914b932bd37a50b983c5e7c90ae93b'
        >>> _generate_cache_key("creators", {"sort_by": "score", "limit": 50})
        'analytics:creators:...'
    """
    # Sort params to ensure consistent hashing
    params_str = json.dumps(params, sort_keys=True)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()
    return f"analytics:{endpoint}:{params_hash}"


async def get_cached_analytics(endpoint: str, params: dict) -> Optional[dict]:
    """Retrieve cached analytics data. Tries Redis first, falls back to memory."""
    cache_key = _generate_cache_key(endpoint, params)
    
    try:
        client = await get_redis_client()
        if client is not None:
            cached_data = await client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            return None
    except Exception as e:
        logger.warning(f"Redis get error: {e}")

    # Fallback: in-memory cache
    entry = _memory_cache.get(cache_key)
    if entry and entry["expires_at"] > time.time():
        return entry["data"]
    return None


async def set_cached_analytics(
    endpoint: str,
    params: dict,
    data: Any,
    ttl: int = 300
) -> bool:
    """Store analytics data in cache. Tries Redis first, falls back to memory."""
    cache_key = _generate_cache_key(endpoint, params)
    
    try:
        client = await get_redis_client()
        if client is not None:
            serialized_data = json.dumps(data)
            await client.setex(cache_key, ttl, serialized_data)
            return True
    except Exception as e:
        logger.warning(f"Redis set error: {e}")

    # Fallback: in-memory cache
    _memory_cache[cache_key] = {
        "data": data,
        "expires_at": time.time() + ttl,
    }
    # Bersihkan cache yang expired agar tidak membengkak
    expired = [k for k, v in _memory_cache.items() if v["expires_at"] <= time.time()]
    for k in expired:
        del _memory_cache[k]
    return True


async def clear_analytics_cache(endpoint: Optional[str] = None) -> int:
    """
    Clear analytics cache entries.
    
    Args:
        endpoint: Specific endpoint to clear, or None to clear all analytics cache
        
    Returns:
        Number of keys deleted
        
    Examples:
        >>> await clear_analytics_cache("overview")
        5  # Deleted 5 cache entries for overview endpoint
        >>> await clear_analytics_cache()
        42  # Deleted all 42 analytics cache entries
    """
    try:
        client = await get_redis_client()
        if client is None:
            return 0
        
        if endpoint:
            pattern = f"analytics:{endpoint}:*"
        else:
            pattern = "analytics:*"
        
        keys = []
        async for key in client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            deleted = await client.delete(*keys)
            logger.info(f"Cleared {deleted} cache entries matching {pattern}")
            return deleted
        
        return 0
        
    except Exception as e:
        logger.warning(f"Error clearing cache: {e}")
        return 0


async def close_redis_connection():
    """
    Close Redis connection gracefully.
    
    Should be called on application shutdown.
    """
    global _redis_client
    
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")
        finally:
            _redis_client = None
