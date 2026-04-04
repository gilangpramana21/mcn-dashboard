"""
Unit tests for products analytics endpoint.

Tests the products endpoint implementation including cache integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.api.analytics import get_product_analytics, ProductItem


@pytest.mark.asyncio
class TestProductsEndpoint:
    """Tests for GET /api/v1/analytics/products endpoint."""
    
    async def test_products_endpoint_uses_cache(self):
        """Test that products endpoint checks cache first."""
        # Mock cache service
        with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache:
            # Setup mock to return cached data
            mock_get_cache.return_value = {
                "data": [
                    {
                        "id": "test-product-1",
                        "name": "Test Product",
                        "price": 100000.0,
                        "category": "Beauty",
                        "shop_name": "Test Shop",
                        "total_gmv": 1500000.0,
                        "total_buyers": 15,
                        "total_creators": 1,
                        "conversion_rate": 0.05,
                        "revenue": 1500000.0,
                    }
                ],
                "meta": {
                    "page": 1,
                    "page_size": 50,
                    "total_items": 1,
                    "total_pages": 1,
                }
            }
            
            # Mock dependencies
            mock_db = AsyncMock()
            mock_user = {"id": "test-user"}
            
            # Call endpoint
            result = await get_product_analytics(
                sort_by="gmv",
                category=None,
                page=1,
                page_size=50,
                db=mock_db,
                _=mock_user
            )
            
            # Verify cache was checked
            mock_get_cache.assert_called_once_with(
                "products",
                {"sort_by": "gmv", "category": None, "page": 1, "page_size": 50}
            )
            
            # Verify result is from cache
            assert hasattr(result, 'data')
            assert hasattr(result, 'meta')
            assert len(result.data) == 1
            assert isinstance(result.data[0], ProductItem)
            assert result.data[0].name == "Test Product"
            assert result.data[0].total_gmv == 1500000.0
            assert result.meta.page == 1
            assert result.meta.total_items == 1
            
            # Verify database was NOT queried (cache hit)
            mock_db.execute.assert_not_called()
    
    async def test_products_endpoint_sets_cache_on_miss(self):
        """Test that products endpoint sets cache on cache miss."""
        # Mock cache service
        with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache, \
             patch('app.services.cache_service.set_cached_analytics') as mock_set_cache:
            
            # Setup mock to return None (cache miss)
            mock_get_cache.return_value = None
            
            # Mock database response
            mock_db = AsyncMock()
            
            # Mock count result
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 1
            
            # Mock data result
            mock_data_result = MagicMock()
            mock_row = {
                "id": "test-product-1",
                "name": "Test Product",
                "price": 100000.0,
                "category": "Beauty",
                "shop_name": "Test Shop",
                "total_gmv": 1500000.0,
                "total_buyers": 15,
                "total_creators": 1,
                "conversion_rate": 0.05,
            }
            mock_data_result.mappings.return_value.all.return_value = [mock_row]
            
            mock_db.execute.side_effect = [mock_count_result, mock_data_result]
            mock_user = {"id": "test-user"}
            
            # Call endpoint
            result = await get_product_analytics(
                sort_by="gmv",
                category="Beauty",
                page=1,
                page_size=50,
                db=mock_db,
                _=mock_user
            )
            
            # Verify cache was checked
            mock_get_cache.assert_called_once()
            
            # Verify database was queried (twice: count + data)
            assert mock_db.execute.call_count == 2
            
            # Verify cache was set with results
            mock_set_cache.assert_called_once()
            call_args = mock_set_cache.call_args
            assert call_args[0][0] == "products"
            assert call_args[0][1] == {"sort_by": "gmv", "category": "Beauty", "page": 1, "page_size": 50}
            assert call_args[1]["ttl"] == 300  # 5 minutes
            
            # Verify result structure
            assert hasattr(result, 'data')
            assert hasattr(result, 'meta')
            assert len(result.data) == 1
            assert isinstance(result.data[0], ProductItem)
            assert result.data[0].name == "Test Product"
            assert result.meta.page == 1
            assert result.meta.total_items == 1
    
    async def test_products_endpoint_query_structure(self):
        """Test that products endpoint generates correct SQL query."""
        with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache, \
             patch('app.services.cache_service.set_cached_analytics'):
            
            # Setup cache miss
            mock_get_cache.return_value = None
            
            # Mock database
            mock_db = AsyncMock()
            
            # Mock count result
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0
            
            # Mock data result
            mock_data_result = MagicMock()
            mock_data_result.mappings.return_value.all.return_value = []
            
            mock_db.execute.side_effect = [mock_count_result, mock_data_result]
            mock_user = {"id": "test-user"}
            
            # Call endpoint with category filter
            await get_product_analytics(
                sort_by="buyers",
                category="Electronics",
                page=1,
                page_size=100,
                db=mock_db,
                _=mock_user
            )
            
            # Verify database query was called (twice: count + data)
            assert mock_db.execute.call_count == 2
            
            # Get the SQL query that was executed (second call is the data query)
            call_args = mock_db.execute.call_args_list[1]
            sql_query = str(call_args[0][0])
            params = call_args[0][1]
            
            # Verify query structure
            assert "FROM products p" in sql_query
            assert "LEFT JOIN content_videos cv ON cv.product_id = p.id" in sql_query
            assert "WHERE p.is_active = TRUE AND p.category = :category" in sql_query
            assert "GROUP BY p.id, p.name, p.price, p.category, p.shop_name" in sql_query
            assert "ORDER BY total_buyers DESC" in sql_query
            assert "LIMIT :limit OFFSET :offset" in sql_query
            
            # Verify parameters
            assert params["category"] == "Electronics"
            assert params["limit"] == 100
            assert params["offset"] == 0
    
    async def test_products_endpoint_sorting_options(self):
        """Test that products endpoint supports all sorting options."""
        sort_options = ["gmv", "buyers", "creators", "conversion"]
        expected_order = {
            "gmv": "total_gmv DESC",
            "buyers": "total_buyers DESC",
            "creators": "total_creators DESC",
            "conversion": "conversion_rate DESC",
        }
        
        for sort_by in sort_options:
            with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache, \
                 patch('app.services.cache_service.set_cached_analytics'):
                
                mock_get_cache.return_value = None
                
                mock_db = AsyncMock()
                
                # Mock count result
                mock_count_result = MagicMock()
                mock_count_result.scalar.return_value = 0
                
                # Mock data result
                mock_data_result = MagicMock()
                mock_data_result.mappings.return_value.all.return_value = []
                
                mock_db.execute.side_effect = [mock_count_result, mock_data_result]
                mock_user = {"id": "test-user"}
                
                # Call endpoint
                await get_product_analytics(
                    sort_by=sort_by,
                    category=None,
                    page=1,
                    page_size=50,
                    db=mock_db,
                    _=mock_user
                )
                
                # Verify correct ORDER BY clause (second call is the data query)
                call_args = mock_db.execute.call_args_list[1]
                sql_query = str(call_args[0][0])
                assert f"ORDER BY {expected_order[sort_by]}" in sql_query
    
    async def test_products_endpoint_calculates_metrics_correctly(self):
        """Test that products endpoint calculates aggregated metrics correctly."""
        with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache, \
             patch('app.services.cache_service.set_cached_analytics'):
            
            mock_get_cache.return_value = None
            
            # Mock database response with specific values
            mock_db = AsyncMock()
            
            # Mock count result
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 1
            
            # Mock data result
            mock_data_result = MagicMock()
            mock_row = {
                "id": "prod-1",
                "name": "Product A",
                "price": 50000.0,
                "category": "Fashion",
                "shop_name": "Shop A",
                "total_gmv": 2500000.0,
                "total_buyers": 50,
                "total_creators": 5,
                "conversion_rate": 2.5,
            }
            mock_data_result.mappings.return_value.all.return_value = [mock_row]
            
            mock_db.execute.side_effect = [mock_count_result, mock_data_result]
            mock_user = {"id": "test-user"}
            
            # Call endpoint
            result = await get_product_analytics(
                sort_by="gmv",
                category=None,
                page=1,
                page_size=50,
                db=mock_db,
                _=mock_user
            )
            
            # Verify calculations
            assert len(result.data) == 1
            product = result.data[0]
            
            assert product.total_gmv == 2500000.0
            assert product.total_buyers == 50
            assert product.total_creators == 5
            assert product.conversion_rate == 2.5
            
            # Verify revenue calculation: total_buyers * price
            expected_revenue = 50 * 50000.0
            assert product.revenue == expected_revenue
    
    async def test_products_endpoint_filters_inactive_products(self):
        """Test that products endpoint only returns active products."""
        with patch('app.services.cache_service.get_cached_analytics') as mock_get_cache, \
             patch('app.services.cache_service.set_cached_analytics'):
            
            mock_get_cache.return_value = None
            
            mock_db = AsyncMock()
            
            # Mock count result
            mock_count_result = MagicMock()
            mock_count_result.scalar.return_value = 0
            
            # Mock data result
            mock_data_result = MagicMock()
            mock_data_result.mappings.return_value.all.return_value = []
            
            mock_db.execute.side_effect = [mock_count_result, mock_data_result]
            mock_user = {"id": "test-user"}
            
            # Call endpoint
            await get_product_analytics(
                sort_by="gmv",
                category=None,
                page=1,
                page_size=50,
                db=mock_db,
                _=mock_user
            )
            
            # Verify query includes is_active filter (check both count and data queries)
            for call_args in mock_db.execute.call_args_list:
                sql_query = str(call_args[0][0])
                assert "p.is_active = TRUE" in sql_query
