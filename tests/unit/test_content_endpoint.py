"""
Unit tests for content analytics endpoint.

Tests the content endpoint implementation without full integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.api.analytics import get_content_analytics, ContentItem


@pytest.mark.asyncio
async def test_content_endpoint_with_cache_hit():
    """Test that content endpoint returns cached data when available."""
    # Mock cache service
    mock_cached_data = {
        "data": [
            {
                "id": "test-id-1",
                "tiktok_video_id": "vid-1",
                "creator_name": "Test Creator",
                "creator_id": "creator-1",
                "product_name": "Test Product",
                "views": 10000,
                "likes": 500,
                "comments": 100,
                "shares": 50,
                "engagement_rate": 6.5,
                "velocity": 100.0,
                "gmv_generated": 500000.0,
                "buyers": 5,
                "conversion_rate": 0.05,
                "posted_at": "2024-01-01T00:00:00",
            }
        ],
        "meta": {
            "page": 1,
            "page_size": 50,
            "total_items": 1,
            "total_pages": 1,
        }
    }
    
    with patch("app.services.cache_service.get_cached_analytics", new_callable=AsyncMock) as mock_get_cache:
        mock_get_cache.return_value = mock_cached_data
        
        # Mock dependencies
        mock_db = AsyncMock()
        mock_user = {"id": "user-1"}
        
        # Call endpoint
        result = await get_content_analytics(
            sort_by="views",
            creator_id=None,
            product_id=None,
            page=1,
            page_size=50,
            db=mock_db,
            _=mock_user,
        )
        
        # Verify cache was checked
        mock_get_cache.assert_called_once()
        
        # Verify result structure
        assert hasattr(result, 'data')
        assert hasattr(result, 'meta')
        assert len(result.data) == 1
        assert isinstance(result.data[0], ContentItem)
        assert result.data[0].tiktok_video_id == "vid-1"
        assert result.data[0].creator_name == "Test Creator"
        assert result.data[0].views == 10000
        assert result.data[0].engagement_rate == 6.5
        assert result.meta.page == 1
        assert result.meta.total_items == 1


@pytest.mark.asyncio
async def test_content_endpoint_with_cache_miss():
    """Test that content endpoint queries database on cache miss."""
    # Mock database result
    mock_row = {
        "id": "test-id-1",
        "tiktok_video_id": "vid-1",
        "creator_id": "creator-1",
        "creator_name": "Test Creator",
        "product_name": "Test Product",
        "views": 10000,
        "likes": 500,
        "comments": 100,
        "shares": 50,
        "gmv_generated": 500000.0,
        "buyers": 5,
        "posted_at": MagicMock(isoformat=lambda: "2024-01-01T00:00:00"),
        "engagement_rate": 6.5,
        "velocity": 100.0,
        "conversion_rate": 0.05,
    }
    
    mock_db = AsyncMock()
    
    # Mock count result
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 1
    
    # Mock data result
    mock_data_result = MagicMock()
    mock_data_result.mappings.return_value.all.return_value = [mock_row]
    
    mock_db.execute.side_effect = [mock_count_result, mock_data_result]
    
    with patch("app.services.cache_service.get_cached_analytics", new_callable=AsyncMock) as mock_get_cache, \
         patch("app.services.cache_service.set_cached_analytics", new_callable=AsyncMock) as mock_set_cache:
        
        mock_get_cache.return_value = None  # Cache miss
        
        # Mock dependencies
        mock_user = {"id": "user-1"}
        
        # Call endpoint
        result = await get_content_analytics(
            sort_by="views",
            creator_id=None,
            product_id=None,
            page=1,
            page_size=50,
            db=mock_db,
            _=mock_user,
        )
        
        # Verify cache was checked
        mock_get_cache.assert_called_once()
        
        # Verify database was queried (twice: count + data)
        assert mock_db.execute.call_count == 2
        
        # Verify cache was set
        mock_set_cache.assert_called_once()
        
        # Verify result structure
        assert hasattr(result, 'data')
        assert hasattr(result, 'meta')
        assert len(result.data) == 1
        assert isinstance(result.data[0], ContentItem)
        assert result.data[0].tiktok_video_id == "vid-1"
        assert result.data[0].creator_name == "Test Creator"
        assert result.data[0].views == 10000
        assert result.meta.page == 1
        assert result.meta.total_items == 1


@pytest.mark.asyncio
async def test_content_endpoint_with_filters():
    """Test that content endpoint applies filters correctly."""
    mock_db = AsyncMock()
    
    # Mock count result
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 0
    
    # Mock data result
    mock_data_result = MagicMock()
    mock_data_result.mappings.return_value.all.return_value = []
    
    mock_db.execute.side_effect = [mock_count_result, mock_data_result]
    
    with patch("app.services.cache_service.get_cached_analytics", new_callable=AsyncMock) as mock_get_cache, \
         patch("app.services.cache_service.set_cached_analytics", new_callable=AsyncMock):
        
        mock_get_cache.return_value = None  # Cache miss
        
        # Mock dependencies
        mock_user = {"id": "user-1"}
        
        # Call endpoint with filters
        await get_content_analytics(
            sort_by="gmv",
            creator_id="creator-123",
            product_id="product-456",
            page=1,
            page_size=100,
            db=mock_db,
            _=mock_user,
        )
        
        # Verify database was called (twice: count + data)
        assert mock_db.execute.call_count == 2
        
        # Get the SQL query that was executed (second call is the data query)
        call_args = mock_db.execute.call_args_list[1]
        sql_query = str(call_args[0][0])
        
        # Verify filters are in the query
        assert "cv.creator_id = :creator_id" in sql_query
        assert "cv.product_id = :product_id" in sql_query
        
        # Verify sorting
        assert "cv.gmv_generated DESC" in sql_query


def test_content_item_model():
    """Test ContentItem model validation."""
    item = ContentItem(
        id="test-id",
        tiktok_video_id="vid-123",
        creator_name="Test Creator",
        creator_id="creator-123",
        product_name="Test Product",
        views=10000,
        likes=500,
        comments=100,
        shares=50,
        engagement_rate=6.5,
        velocity=100.0,
        gmv_generated=500000.0,
        buyers=5,
        conversion_rate=0.05,
        posted_at="2024-01-01T00:00:00",
    )
    
    assert item.id == "test-id"
    assert item.views == 10000
    assert item.engagement_rate == 6.5
    assert item.velocity == 100.0
    assert item.conversion_rate == 0.05
