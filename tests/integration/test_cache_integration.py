"""
Integration tests for Redis cache service.

Tests real Redis connection and cache operations with actual Redis instance.
These tests require a running Redis server.
"""

import asyncio

import pytest

from app.services.cache_service import (
    clear_analytics_cache,
    close_redis_connection,
    get_cached_analytics,
    get_redis_client,
    set_cached_analytics,
)


@pytest.mark.asyncio
class TestRedisCacheIntegration:
    """Integration tests with real Redis instance."""
    
    async def test_cache_workflow_end_to_end(self):
        """Test complete cache workflow: set → get → clear."""
        # Test data
        endpoint = "overview"
        params = {"test": "integration"}
        test_data = {
            "total_gmv": 5000000,
            "total_views": 100000,
            "total_creators": 50
        }
        
        try:
            # Clear any existing cache
            await clear_analytics_cache(endpoint)
            
            # Verify cache miss
            result = await get_cached_analytics(endpoint, params)
            assert result is None, "Cache should be empty initially"
            
            # Set cache
            success = await set_cached_analytics(endpoint, params, test_data, ttl=60)
            if not success:
                pytest.skip("Redis not available for integration test")
            
            # Verify cache hit
            result = await get_cached_analytics(endpoint, params)
            assert result == test_data, "Cached data should match original"
            
            # Clear cache
            deleted = await clear_analytics_cache(endpoint)
            assert deleted >= 1, "Should delete at least one key"
            
            # Verify cache cleared
            result = await get_cached_analytics(endpoint, params)
            assert result is None, "Cache should be empty after clear"
            
        finally:
            # Cleanup
            await clear_analytics_cache(endpoint)
    
    async def test_cache_ttl_behavior(self):
        """Test that cache respects TTL."""
        endpoint = "test_ttl"
        params = {}
        test_data = {"value": "test"}
        
        try:
            # Set cache with 1 second TTL
            success = await set_cached_analytics(endpoint, params, test_data, ttl=1)
            if not success:
                pytest.skip("Redis not available for integration test")
            
            # Immediate retrieval should work
            result = await get_cached_analytics(endpoint, params)
            assert result == test_data
            
            # Wait for TTL to expire
            await asyncio.sleep(1.5)
            
            # Cache should be expired
            result = await get_cached_analytics(endpoint, params)
            assert result is None, "Cache should expire after TTL"
            
        finally:
            await clear_analytics_cache(endpoint)
    
    async def test_multiple_endpoints_cache_isolation(self):
        """Test that different endpoints have isolated cache."""
        params = {}
        data1 = {"endpoint": "overview"}
        data2 = {"endpoint": "creators"}
        
        try:
            # Set cache for two different endpoints
            await set_cached_analytics("overview", params, data1)
            await set_cached_analytics("creators", params, data2)
            
            # Verify each endpoint has its own data
            result1 = await get_cached_analytics("overview", params)
            result2 = await get_cached_analytics("creators", params)
            
            assert result1 == data1
            assert result2 == data2
            
            # Clear one endpoint
            await clear_analytics_cache("overview")
            
            # Verify only one was cleared
            result1 = await get_cached_analytics("overview", params)
            result2 = await get_cached_analytics("creators", params)
            
            assert result1 is None
            assert result2 == data2
            
        finally:
            await clear_analytics_cache()
    
    async def test_cache_with_complex_params(self):
        """Test cache with complex parameter combinations."""
        endpoint = "creators"
        params = {
            "sort_by": "score",
            "role": "influencer",
            "min_followers": 1000,
            "limit": 50,
            "offset": 0
        }
        test_data = [{"id": "1", "name": "Creator 1"}]
        
        try:
            # Set cache
            await set_cached_analytics(endpoint, params, test_data)
            
            # Retrieve with same params
            result = await get_cached_analytics(endpoint, params)
            assert result == test_data
            
            # Different params should miss cache
            different_params = {**params, "limit": 100}
            result = await get_cached_analytics(endpoint, different_params)
            assert result is None
            
        finally:
            await clear_analytics_cache(endpoint)
    
    async def test_redis_connection_lifecycle(self):
        """Test Redis connection establishment and closure."""
        # Get client
        client = await get_redis_client()
        
        if client is None:
            pytest.skip("Redis not available for integration test")
        
        # Verify connection works by using cache operations
        test_data = {"test": "lifecycle"}
        await set_cached_analytics("test", {}, test_data)
        result = await get_cached_analytics("test", {})
        assert result == test_data
        
        # Close connection
        await close_redis_connection()
        
        # Verify connection is closed
        import app.services.cache_service as cache_module
        assert cache_module._redis_client is None
        
        # Cleanup
        await clear_analytics_cache("test")
