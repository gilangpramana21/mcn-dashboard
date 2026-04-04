"""Unit tests for analytics validation functions."""

import pytest
from fastapi import HTTPException

from app.services.analytics_validation import validate_product


class TestValidateProduct:
    """Test suite for validate_product function."""

    def test_valid_product_with_all_fields(self):
        """Valid product with all fields should pass validation."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": 100000.50,
            "category": "Electronics"
        }
        # Should not raise any exception
        validate_product(product_data)

    def test_valid_product_with_zero_price(self):
        """Valid product with price = 0 should pass validation."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Free Product",
            "price": 0,
            "category": "Samples"
        }
        # Should not raise any exception
        validate_product(product_data)

    def test_valid_product_without_category(self):
        """Valid product without category should pass validation."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": 50000
        }
        # Should not raise any exception
        validate_product(product_data)

    def test_missing_tiktok_product_id(self):
        """Missing tiktok_product_id should raise HTTPException."""
        product_data = {
            "name": "Test Product",
            "price": 100000
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "MISSING_PRODUCT_ID"

    def test_empty_tiktok_product_id(self):
        """Empty tiktok_product_id should raise HTTPException."""
        product_data = {
            "tiktok_product_id": "",
            "name": "Test Product",
            "price": 100000
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "MISSING_PRODUCT_ID"

    def test_whitespace_only_tiktok_product_id(self):
        """Whitespace-only tiktok_product_id should raise HTTPException."""
        product_data = {
            "tiktok_product_id": "   ",
            "name": "Test Product",
            "price": 100000
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "MISSING_PRODUCT_ID"

    def test_missing_price(self):
        """Missing price should raise HTTPException."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product"
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "MISSING_PRICE"

    def test_negative_price(self):
        """Negative price should raise HTTPException."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": -100
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_PRICE"
        assert exc_info.value.detail["error"]["details"]["value"] == -100

    def test_invalid_price_type_string(self):
        """Invalid price type (non-numeric string) should raise HTTPException."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": "not a number"
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_PRICE_TYPE"

    def test_invalid_price_type_none(self):
        """Price as None should raise HTTPException."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": None
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "MISSING_PRICE"

    def test_empty_category_string(self):
        """Empty category string should raise HTTPException."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": 100000,
            "category": ""
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_CATEGORY"

    def test_whitespace_only_category(self):
        """Whitespace-only category should raise HTTPException."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": 100000,
            "category": "   "
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_CATEGORY"

    def test_invalid_category_type_list(self):
        """Category as list should raise HTTPException."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": 100000,
            "category": ["Electronics", "Gadgets"]
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_CATEGORY_TYPE"

    def test_invalid_category_type_number(self):
        """Category as number should raise HTTPException."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": 100000,
            "category": 123
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_product(product_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_CATEGORY_TYPE"

    def test_price_as_string_number(self):
        """Price as numeric string should be converted and validated."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": "100000.50"
        }
        # Should not raise any exception (string is converted to float)
        validate_product(product_data)

    def test_price_as_integer(self):
        """Price as integer should pass validation."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Test Product",
            "price": 100000
        }
        # Should not raise any exception
        validate_product(product_data)

    def test_large_price_value(self):
        """Large price value should pass validation."""
        product_data = {
            "tiktok_product_id": "TT12345",
            "name": "Expensive Product",
            "price": 999999999.99
        }
        # Should not raise any exception
        validate_product(product_data)


from datetime import datetime, timedelta, timezone

from app.services.analytics_validation import validate_content_video, validate_gmv_limit


class TestValidateContentVideo:
    """Test suite for validate_content_video function."""

    def test_valid_content_video_with_all_fields(self):
        """Valid content video with all fields should pass validation."""
        video_data = {
            "tiktok_video_id": "VID12345",
            "creator_id": "creator_123",
            "product_id": "prod_456",
            "title": "Test Video",
            "views": 10000,
            "likes": 500,
            "comments": 50,
            "shares": 25,
            "gmv_generated": 5000000.50,
            "buyers": 100,
            "posted_at": datetime.utcnow() - timedelta(hours=1)
        }
        # Should not raise any exception
        validate_content_video(video_data)

    def test_valid_content_video_with_zero_metrics(self):
        """Valid content video with zero metrics should pass validation."""
        video_data = {
            "creator_id": "creator_123",
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "gmv_generated": 0,
            "buyers": 0,
            "posted_at": datetime.utcnow()
        }
        # Should not raise any exception
        validate_content_video(video_data)

    def test_valid_content_video_without_product_id(self):
        """Valid content video without product_id should pass validation."""
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "likes": 50,
            "posted_at": datetime.utcnow() - timedelta(days=1)
        }
        # Should not raise any exception
        validate_content_video(video_data)

    def test_valid_content_video_with_string_timestamp(self):
        """Valid content video with ISO string timestamp should pass validation."""
        past_time = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "posted_at": past_time
        }
        # Should not raise any exception
        validate_content_video(video_data)

    def test_missing_creator_id(self):
        """Missing creator_id should raise HTTPException."""
        video_data = {
            "views": 1000,
            "likes": 50
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "MISSING_CREATOR_ID"

    def test_empty_creator_id(self):
        """Empty creator_id should raise HTTPException."""
        video_data = {
            "creator_id": "",
            "views": 1000
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "MISSING_CREATOR_ID"

    def test_whitespace_only_creator_id(self):
        """Whitespace-only creator_id should raise HTTPException."""
        video_data = {
            "creator_id": "   ",
            "views": 1000
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "MISSING_CREATOR_ID"

    def test_empty_product_id(self):
        """Empty product_id string should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "product_id": "",
            "views": 1000
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_PRODUCT_ID"

    def test_whitespace_only_product_id(self):
        """Whitespace-only product_id should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "product_id": "   ",
            "views": 1000
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_PRODUCT_ID"

    def test_negative_views(self):
        """Negative views should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "views": -100
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_METRIC_VALUE"
        assert "Views" in exc_info.value.detail["error"]["message"]

    def test_negative_likes(self):
        """Negative likes should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "likes": -50
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_METRIC_VALUE"
        assert "Likes" in exc_info.value.detail["error"]["message"]

    def test_negative_comments(self):
        """Negative comments should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "comments": -10
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_METRIC_VALUE"
        assert "Comments" in exc_info.value.detail["error"]["message"]

    def test_negative_shares(self):
        """Negative shares should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "shares": -5
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_METRIC_VALUE"
        assert "Shares" in exc_info.value.detail["error"]["message"]

    def test_negative_gmv_generated(self):
        """Negative gmv_generated should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "gmv_generated": -1000.50
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_METRIC_VALUE"
        assert "GMV generated" in exc_info.value.detail["error"]["message"]

    def test_negative_buyers(self):
        """Negative buyers should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "buyers": -10
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_METRIC_VALUE"
        assert "Buyers" in exc_info.value.detail["error"]["message"]

    def test_invalid_views_type(self):
        """Invalid views type should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "views": "not a number"
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_METRIC_TYPE"

    def test_invalid_gmv_type(self):
        """Invalid gmv_generated type should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "gmv_generated": "not a number"
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_METRIC_TYPE"

    def test_future_posted_at_datetime(self):
        """Future posted_at datetime should raise HTTPException."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "posted_at": future_time
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "FUTURE_TIMESTAMP"

    def test_future_posted_at_string(self):
        """Future posted_at as ISO string should raise HTTPException."""
        future_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "posted_at": future_time
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "FUTURE_TIMESTAMP"

    def test_future_posted_at_timezone_aware(self):
        """Future posted_at with timezone should raise HTTPException."""
        future_time = datetime.now(timezone.utc) + timedelta(hours=2)
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "posted_at": future_time
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "FUTURE_TIMESTAMP"

    def test_invalid_posted_at_format(self):
        """Invalid posted_at format should raise HTTPException."""
        video_data = {
            "creator_id": "creator_123",
            "views": 1000,
            "posted_at": "not a valid timestamp"
        }
        with pytest.raises(HTTPException) as exc_info:
            validate_content_video(video_data)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_TIMESTAMP_FORMAT"

    def test_metrics_as_string_numbers(self):
        """Metrics as numeric strings should be converted and validated."""
        video_data = {
            "creator_id": "creator_123",
            "views": "1000",
            "likes": "50",
            "gmv_generated": "5000.50"
        }
        # Should not raise any exception (strings are converted)
        validate_content_video(video_data)

    def test_large_metric_values(self):
        """Large metric values should pass validation."""
        video_data = {
            "creator_id": "creator_123",
            "views": 10000000,
            "likes": 500000,
            "comments": 50000,
            "shares": 25000,
            "gmv_generated": 9999999999.99,
            "buyers": 100000
        }
        # Should not raise any exception
        validate_content_video(video_data)


class TestValidateGmvLimit:
    """Test suite for validate_gmv_limit function."""

    def test_valid_gmv_below_limit(self):
        """GMV below 10 billion should pass validation."""
        # Should not raise any exception
        validate_gmv_limit(5000000000)  # 5 billion

    def test_valid_gmv_at_limit(self):
        """GMV exactly at 10 billion should pass validation."""
        # Should not raise any exception
        validate_gmv_limit(10000000000)  # 10 billion

    def test_valid_gmv_zero(self):
        """GMV of zero should pass validation."""
        # Should not raise any exception
        validate_gmv_limit(0)

    def test_valid_gmv_small_value(self):
        """Small GMV value should pass validation."""
        # Should not raise any exception
        validate_gmv_limit(100.50)

    def test_gmv_exceeds_limit(self):
        """GMV exceeding 10 billion should raise HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            validate_gmv_limit(10000000001)  # 10 billion + 1
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "GMV_EXCEEDS_LIMIT"
        assert exc_info.value.detail["error"]["details"]["max_allowed"] == 10000000000

    def test_gmv_far_exceeds_limit(self):
        """GMV far exceeding 10 billion should raise HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            validate_gmv_limit(50000000000)  # 50 billion
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "GMV_EXCEEDS_LIMIT"

    def test_gmv_as_string_number(self):
        """GMV as numeric string should be converted and validated."""
        # Should not raise any exception
        validate_gmv_limit("5000000000.50")

    def test_gmv_as_string_exceeds_limit(self):
        """GMV as string exceeding limit should raise HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            validate_gmv_limit("15000000000")
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "GMV_EXCEEDS_LIMIT"

    def test_invalid_gmv_type_string(self):
        """Invalid GMV type (non-numeric string) should raise HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            validate_gmv_limit("not a number")
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_GMV_TYPE"

    def test_invalid_gmv_type_none(self):
        """GMV as None should raise HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            validate_gmv_limit(None)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_GMV_TYPE"

    def test_invalid_gmv_type_list(self):
        """GMV as list should raise HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            validate_gmv_limit([1000000])
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error"]["code"] == "INVALID_GMV_TYPE"

    def test_gmv_as_float(self):
        """GMV as float should pass validation."""
        # Should not raise any exception
        validate_gmv_limit(5000000000.99)

    def test_gmv_as_integer(self):
        """GMV as integer should pass validation."""
        # Should not raise any exception
        validate_gmv_limit(5000000000)
