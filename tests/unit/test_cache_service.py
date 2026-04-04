"""
Unit tests for Redis cache service.

Tests cache hit/miss scenarios, Redis connection failure handling,
TTL expiration, and cache key generation.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.cache_service import (
    _generate_cache_key,
    clear_analytics_cache,
    close_redis_connection,
    get_cached_analytics,
    get_redis_client,
    set_cached_analytics,
)


class TestCacheKeyGeneration:
    """Test cache key generation logic."""
    
    def test_generate_cache_key_basic(self):
        """Test basic cache key generation."""
        key = _generate_cache_key("overview", {})
        assert key.startswith("analytics:overview:")
        assert len(key.split(":")) == 3
    
    def test_generate_cache_key_with_params(self):
        """Test cache key generation with parameters."""
        params = {"sort_by": "score", "limit": 50}
        key = _generate_cache_key("creators", params)
        assert key.startswith("analytics:creators:")
    
    def test_generate_cache_key_consistency(self):
        """Test that same params generate same key."""
        params = {"sort_by": "score", "limit": 50}
        key1 = _generate_cache_key("creators", params)
        key2 = _generate_cache_key("creators", params)
        assert key1 == key2
    
    def test_generate_cache_key_param_order_independence(self):
        """Test that param order doesn't affect key."""
        params1 = {"sort_by": "score", "limit": 50}
        params2 = {"limit": 50, "sort_by": "score"}
        key1 = _generate_cache_key("creators", params1)
        key2 = _generate_cache_key("creators", params2)
        assert key1 == key2
    
    def test_generate_cache_key_different_params(self):
        """Test that different params generate different keys."""
        key1 = _generate_cache_key("creators", {"limit": 50})
        key2 = _generate_cache_key("creators", {"limit": 100})
        assert key1 != key2


@pytest.mark.asyncio
class TestRedisConnection:
    """Test Redis connection handling."""
    
    async def test_get_redis_client_success(self):
        """Test successful Redis connection."""
        with patch("app.services.cache_service.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock()
            mock_from_url.return_value = mock_client
            
            # Reset global client
            import app.services.cache_service as cache_module
            cache_module._redis_client = None
            
            client = await get_redis_client()
            assert client is not None
            mock_client.ping.assert_called_once()
    
    async def test_get_redis_client_connection_failure(self):
        """Test Redis connection failure handling."""
        with patch("app.services.cache_service.redis.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Connection refused")
            
            # Reset global client
            import app.services.cache_service as cache_module
            cache_module._redis_client = None
            
            client = await get_redis_client()
            assert client is None
    
    async def test_get_redis_client_ping_failure(self):
        """Test Redis ping failure handling."""
        with patch("app.services.cache_service.redis.from_url") as mock_from_url:
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(side_effect=Exception("Ping failed"))
            mock_from_url.return_value = mock_client
            
            # Reset global client
            import app.services.cache_service as cache_module
            cache_module._redis_client = None
            
            client = await get_redis_client()
            assert client is None


@pytest.mark.asyncio
class TestCacheOperations:
    """Test cache get/set operations."""
    
    async def test_cache_hit_scenario(self):
        """Test successful cache retrieval."""
        mock_client = AsyncMock()
        test_data = {"total_gmv": 1000000, "total_views": 50000}
        mock_client.get = AsyncMock(return_value=json.dumps(test_data))
        
        with patch("app.services.cache_service.get_redis_client", return_value=mock_client):
            result = await get_cached_analytics("overview", {})
            assert result == test_data
            mock_client.get.assert_called_once()
    
    async def test_cache_miss_scenario(self):
        """Test cache miss (no data in cache)."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        
        with patch("app.services.cache_service.get_redis_client", return_value=mock_client):
            result = await get_cached_analytics("overview", {})
            assert result is None
            mock_client.get.assert_called_once()
    
    async def test_cache_set_success(self):
        """Test successful cache storage."""
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()
        
        test_data = {"total_gmv": 1000000}
        
        with patch("app.services.cache_service.get_redis_client", return_value=mock_client):
            result = await set_cached_analytics("overview", {}, test_data, ttl=300)
            assert result is True
            mock_client.setex.assert_called_once()
            
            # Verify TTL was set correctly
            call_args = mock_client.setex.call_args
            assert call_args[0][1] == 300  # TTL argument
    
    async def test_cache_set_custom_ttl(self):
        """Test cache storage with custom TTL."""
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock()
        
        with patch("app.services.cache_service.get_redis_client", return_value=mock_client):
            await set_cached_analytics("overview", {}, {}, ttl=600)
            
            call_args = mock_client.setex.call_args
            assert call_args[0][1] == 600
    
    async def test_cache_get_redis_unavailable(self):
        """Test cache get when Redis is unavailable."""
        with patch("app.services.cache_service.get_redis_client", return_value=None):
            result = await get_cached_analytics("overview", {})
            assert result is None
    
    async def test_cache_set_redis_unavailable(self):
        """Test cache set when Redis is unavailable — falls back to in-memory cache."""
        with patch("app.services.cache_service.get_redis_client", return_value=None):
            result = await set_cached_analytics("overview", {}, {"test": "data"})
            # Falls back to in-memory cache, returns True
            assert result is True
    
    async def test_cache_get_exception_handling(self):
        """Test exception handling during cache retrieval — falls back to memory cache."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Redis error"))
        
        with patch("app.services.cache_service.get_redis_client", return_value=mock_client):
            # When Redis raises exception, falls back to memory cache (empty = None)
            import app.services.cache_service as cache_module
            cache_module._memory_cache.clear()
            result = await get_cached_analytics("overview_exc_test", {"unique": "key_exc"})
            assert result is None
    
    async def test_cache_set_exception_handling(self):
        """Test exception handling during cache storage — falls back to memory cache."""
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock(side_effect=Exception("Redis error"))
        
        with patch("app.services.cache_service.get_redis_client", return_value=mock_client):
            # When Redis raises exception, falls back to memory cache (returns True)
            result = await set_cached_analytics("overview", {}, {})
            assert result is True


@pytest.mark.asyncio
class TestCacheClear:
    """Test cache clearing functionality."""
    
    async def test_clear_specific_endpoint(self):
        """Test clearing cache for specific endpoint."""
        mock_client = AsyncMock()
        
        # Mock scan_iter to return some keys
        async def mock_scan_iter(match):
            for key in ["analytics:overview:abc123", "analytics:overview:def456"]:
                yield key
        
        mock_client.scan_iter = mock_scan_iter
        mock_client.delete = AsyncMock(return_value=2)
        
        with patch("app.services.cache_service.get_redis_client", return_value=mock_client):
            deleted = await clear_analytics_cache("overview")
            assert deleted == 2
            mock_client.delete.assert_called_once()
    
    async def test_clear_all_analytics_cache(self):
        """Test clearing all analytics cache entries."""
        mock_client = AsyncMock()
        
        async def mock_scan_iter(match):
            for key in ["analytics:overview:abc", "analytics:creators:def", "analytics:content:ghi"]:
                yield key
        
        mock_client.scan_iter = mock_scan_iter
        mock_client.delete = AsyncMock(return_value=3)
        
        with patch("app.services.cache_service.get_redis_client", return_value=mock_client):
            deleted = await clear_analytics_cache()
            assert deleted == 3
    
    async def test_clear_cache_no_keys(self):
        """Test clearing cache when no keys match."""
        mock_client = AsyncMock()
        
        async def mock_scan_iter(match):
            return
            yield  # Make it a generator
        
        mock_client.scan_iter = mock_scan_iter
        
        with patch("app.services.cache_service.get_redis_client", return_value=mock_client):
            deleted = await clear_analytics_cache("overview")
            assert deleted == 0
    
    async def test_clear_cache_redis_unavailable(self):
        """Test clearing cache when Redis is unavailable."""
        with patch("app.services.cache_service.get_redis_client", return_value=None):
            deleted = await clear_analytics_cache()
            assert deleted == 0
    
    async def test_clear_cache_exception_handling(self):
        """Test exception handling during cache clear."""
        mock_client = AsyncMock()
        mock_client.scan_iter = AsyncMock(side_effect=Exception("Redis error"))
        
        with patch("app.services.cache_service.get_redis_client", return_value=mock_client):
            deleted = await clear_analytics_cache()
            assert deleted == 0


@pytest.mark.asyncio
class TestConnectionLifecycle:
    """Test Redis connection lifecycle management."""
    
    async def test_close_redis_connection(self):
        """Test closing Redis connection."""
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()
        
        import app.services.cache_service as cache_module
        cache_module._redis_client = mock_client
        
        await close_redis_connection()
        mock_client.aclose.assert_called_once()
        assert cache_module._redis_client is None
    
    async def test_close_redis_connection_when_none(self):
        """Test closing when no connection exists."""
        import app.services.cache_service as cache_module
        cache_module._redis_client = None
        
        # Should not raise exception
        await close_redis_connection()
        assert cache_module._redis_client is None
    
    async def test_close_redis_connection_exception_handling(self):
        """Test exception handling during connection close."""
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock(side_effect=Exception("Close error"))
        
        import app.services.cache_service as cache_module
        cache_module._redis_client = mock_client
        
        # Should not raise exception
        await close_redis_connection()
        assert cache_module._redis_client is None
