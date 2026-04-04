# Redis Cache Service

## Overview

The cache service provides Redis-based caching for analytics endpoints to improve performance and reduce database load. It handles Redis connection failures gracefully to ensure the API continues working even if Redis is unavailable.

## Features

- **Automatic cache key generation** from endpoint name and parameters
- **Graceful failure handling** - continues without cache if Redis is unavailable
- **Configurable TTL** - default 5 minutes (300 seconds)
- **Cache clearing** - clear specific endpoints or all analytics cache
- **Connection pooling** - reuses Redis connection across requests

## Usage Example

```python
from app.services.cache_service import (
    get_cached_analytics,
    set_cached_analytics,
    clear_analytics_cache
)

async def get_overview_analytics(params: dict):
    """Get overview analytics with caching."""
    
    # Try to get from cache
    cached_data = await get_cached_analytics("overview", params)
    if cached_data:
        return cached_data
    
    # Cache miss - fetch from database
    data = await fetch_from_database(params)
    
    # Store in cache with 5-minute TTL
    await set_cached_analytics("overview", params, data, ttl=300)
    
    return data
```

## API Reference

### `get_cached_analytics(endpoint, params)`

Retrieve cached analytics data.

**Parameters:**
- `endpoint` (str): Analytics endpoint name (e.g., "overview", "creators")
- `params` (dict): Query parameters used for cache key generation

**Returns:**
- `dict | None`: Cached data or None if cache miss or error

### `set_cached_analytics(endpoint, params, data, ttl=300)`

Store analytics data in cache.

**Parameters:**
- `endpoint` (str): Analytics endpoint name
- `params` (dict): Query parameters
- `data` (Any): Data to cache (will be JSON serialized)
- `ttl` (int): Time-to-live in seconds (default: 300)

**Returns:**
- `bool`: True if successful, False otherwise

### `clear_analytics_cache(endpoint=None)`

Clear analytics cache entries.

**Parameters:**
- `endpoint` (str | None): Specific endpoint to clear, or None for all

**Returns:**
- `int`: Number of keys deleted

## Cache Key Format

Cache keys follow the pattern: `analytics:{endpoint}:{hash(params)}`

Example:
- `analytics:overview:99914b932bd37a50b983c5e7c90ae93b`
- `analytics:creators:a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

## Configuration

Redis connection is configured via environment variable:

```env
REDIS_URL=redis://localhost:6379/0
```

## Error Handling

The cache service handles all Redis errors gracefully:
- Connection failures: logs warning, continues without cache
- Cache get errors: returns None, continues with database query
- Cache set errors: logs warning, returns data anyway

This ensures the API remains functional even if Redis is down.
