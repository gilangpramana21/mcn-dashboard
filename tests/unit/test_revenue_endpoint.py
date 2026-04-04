"""
Unit tests for revenue insights endpoint.

Tests the revenue endpoint implementation including cache integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.analytics import get_revenue_insights


@pytest.mark.asyncio
class TestRevenueEndpoint:
    """Tests for GET /api/v1/analytics/revenue endpoint."""
    
    async def test_revenue_endpoint_uses_cache(self):
        """Test that revenue endpoint checks cache first."""
        # Mock cache service
        with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache:
            # Setup cache hit
            mock_get_cache.return_value = {
                "data": [
                    {
                        "creator_id": "creator-1",
                        "creator_name": "Test Creator",
                        "product_id": "product-1",
                        "product_name": "Test Product",
                        "revenue": 1000000.0,
                        "gmv": 1000000.0,
                        "buyers": 10,
                        "conversion_rate": 0.5,
                        "video_count": 5,
                    }
                ],
                "meta": {
                    "page": 1,
                    "page_size": 100,
                    "total_items": 1,
                    "total_pages": 1,
                }
            }
            
            # Mock database session (should not be called)
            mock_db = AsyncMock(spec=AsyncSession)
            mock_user = {"id": "user-1", "role": "admin"}
            
            # Call endpoint
            result = await get_revenue_insights(
                sort_by="revenue",
                page=1,
                page_size=100,
                db=mock_db,
                _=mock_user
            )
            
            # Verify cache was checked
            mock_get_cache.assert_called_once_with("revenue", {
                "sort_by": "revenue",
                "page": 1,
                "page_size": 100,
            })
            
            # Verify result structure
            assert hasattr(result, 'data')
            assert hasattr(result, 'meta')
            assert len(result.data) == 1
            assert result.data[0].creator_id == "creator-1"
            assert result.data[0].revenue == 1000000.0
            assert result.meta.page == 1
            assert result.meta.total_items == 1
            
            # Verify database was not queried (cache hit)
            mock_db.execute.assert_not_called()
    
    async def test_revenue_endpoint_sets_cache_on_miss(self):
        """Test that revenue endpoint sets cache on cache miss."""
        # Mock cache service
        with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache, \
             patch('app.services.cache_service.set_cached_analytics') as mock_set_cache:
            
            # Setup cache miss
            mock_get_cache.return_value = None
            
            # Mock database session for count query
            mock_db = AsyncMock(spec=AsyncSession)
            
            # Mock count result
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 1
            
            # Mock data result
            mock_data_result = MagicMock()
            mock_data_result.mappings.return_value.all.return_value = [
                {
                    "creator_id": "creator-1",
                    "creator_name": "Test Creator",
                    "product_id": "product-1",
                    "product_name": "Test Product",
                    "revenue": 1000000.0,
                    "gmv": 1000000.0,
                    "total_buyers": 10,
                    "video_count": 5,
                    "conversion_rate": 0.5,
                }
            ]
            
            # Setup execute to return different results for count and data queries
            mock_db.execute.side_effect = [mock_count_result, mock_data_result]
            mock_user = {"id": "user-1", "role": "admin"}
            
            # Call endpoint
            result = await get_revenue_insights(
                sort_by="revenue",
                page=1,
                page_size=100,
                db=mock_db,
                _=mock_user
            )
            
            # Verify cache was checked
            mock_get_cache.assert_called_once()
            
            # Verify database was queried (twice: count + data)
            assert mock_db.execute.call_count == 2
            
            # Verify cache was set with 5-minute TTL
            mock_set_cache.assert_called_once()
            call_args = mock_set_cache.call_args
            assert call_args[0][0] == "revenue"  # endpoint
            assert call_args[0][1] == {"sort_by": "revenue", "page": 1, "page_size": 100}  # params
            assert call_args[1]["ttl"] == 300  # 5 minutes
            
            # Verify result structure
            assert hasattr(result, 'data')
            assert hasattr(result, 'meta')
            assert len(result.data) == 1
            assert result.data[0].creator_id == "creator-1"
            assert result.data[0].revenue == 1000000.0
            assert result.meta.page == 1
            assert result.meta.page_size == 100
            assert result.meta.total_items == 1
            assert result.meta.total_pages == 1
    
    async def test_revenue_endpoint_supports_sorting(self):
        """Test that revenue endpoint supports different sort options."""
        with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache:
            mock_get_cache.return_value = None
            
            mock_db = AsyncMock(spec=AsyncSession)
            
            # Mock count result
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0
            
            # Mock data result
            mock_data_result = MagicMock()
            mock_data_result.mappings.return_value.all.return_value = []
            
            mock_user = {"id": "user-1", "role": "admin"}
            
            # Test different sort options
            for sort_by in ["revenue", "conversion", "buyers"]:
                # Reset mock
                mock_db.execute.side_effect = [mock_count_result, mock_data_result]
                
                await get_revenue_insights(
                    sort_by=sort_by,
                    page=1,
                    page_size=100,
                    db=mock_db,
                    _=mock_user
                )
                
                # Verify SQL query contains correct ORDER BY clause (second call is the data query)
                call_args = mock_db.execute.call_args_list[1]  # Get second call (data query)
                sql_query = str(call_args[0][0])
                
                if sort_by == "revenue":
                    assert "ORDER BY revenue DESC" in sql_query
                elif sort_by == "conversion":
                    assert "ORDER BY conversion_rate DESC" in sql_query
                elif sort_by == "buyers":
                    assert "ORDER BY total_buyers DESC" in sql_query
                
                # Reset for next iteration
                mock_db.execute.reset_mock()
                mock_db.execute.call_args_list = []
    
    async def test_revenue_endpoint_respects_limit(self):
        """Test that revenue endpoint respects page_size parameter."""
        with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache:
            mock_get_cache.return_value = None
            
            mock_db = AsyncMock(spec=AsyncSession)
            
            # Mock count result
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0
            
            # Mock data result
            mock_data_result = MagicMock()
            mock_data_result.mappings.return_value.all.return_value = []
            
            mock_db.execute.side_effect = [mock_count_result, mock_data_result]
            mock_user = {"id": "user-1", "role": "admin"}
            
            # Test with custom page_size
            await get_revenue_insights(
                sort_by="revenue",
                page=1,
                page_size=50,
                db=mock_db,
                _=mock_user
            )
            
            # Verify SQL query contains LIMIT clause (second call is the data query)
            call_args = mock_db.execute.call_args_list[1]
            sql_params = call_args[0][1]
            assert sql_params["limit"] == 50
            assert sql_params["offset"] == 0
    
    async def test_revenue_endpoint_handles_null_product(self):
        """Test that revenue endpoint handles videos without products."""
        with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache:
            mock_get_cache.return_value = None
            
            mock_db = AsyncMock(spec=AsyncSession)
            
            # Mock count result
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 1
            
            # Mock data result
            mock_data_result = MagicMock()
            mock_data_result.mappings.return_value.all.return_value = [
                {
                    "creator_id": "creator-1",
                    "creator_name": "Test Creator",
                    "product_id": None,  # No product
                    "product_name": None,
                    "revenue": 500000.0,
                    "gmv": 500000.0,
                    "total_buyers": 5,
                    "video_count": 3,
                    "conversion_rate": 0.3,
                }
            ]
            
            mock_db.execute.side_effect = [mock_count_result, mock_data_result]
            mock_user = {"id": "user-1", "role": "admin"}
            
            # Call endpoint
            result = await get_revenue_insights(
                sort_by="revenue",
                page=1,
                page_size=100,
                db=mock_db,
                _=mock_user
            )
            
            # Verify result handles null product correctly
            assert len(result.data) == 1
            assert result.data[0].product_id is None
            assert result.data[0].product_name is None
            assert result.data[0].revenue == 500000.0
