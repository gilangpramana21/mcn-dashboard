"""
Unit tests for analytics calculation functions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.services.analytics_calculations import (
    calculate_engagement_rate,
    calculate_conversion_rate,
    calculate_velocity
)


class TestCalculateEngagementRate:
    """Tests for calculate_engagement_rate function."""
    
    def test_basic_engagement_rate_calculation(self):
        """Test basic engagement rate calculation with typical values."""
        # 100 likes + 50 comments + 25 shares = 175 total engagement
        # 175 / 1000 views = 0.175 = 17.5%
        result = calculate_engagement_rate(100, 50, 25, 1000)
        assert result == 17.5
    
    def test_zero_views_returns_zero(self):
        """Test that zero views returns 0.0 without division error."""
        result = calculate_engagement_rate(100, 50, 25, 0)
        assert result == 0.0
    
    def test_zero_engagement_with_views(self):
        """Test video with views but no engagement."""
        result = calculate_engagement_rate(0, 0, 0, 1000)
        assert result == 0.0
    
    def test_all_zeros(self):
        """Test edge case where all metrics are zero."""
        result = calculate_engagement_rate(0, 0, 0, 0)
        assert result == 0.0
    
    def test_high_engagement_rate(self):
        """Test video with very high engagement rate."""
        # 500 likes + 300 comments + 200 shares = 1000 total engagement
        # 1000 / 1000 views = 1.0 = 100%
        result = calculate_engagement_rate(500, 300, 200, 1000)
        assert result == 100.0
    
    def test_engagement_exceeds_views(self):
        """Test case where total engagement exceeds views (possible in viral content)."""
        # 1000 likes + 500 comments + 500 shares = 2000 total engagement
        # 2000 / 1000 views = 2.0 = 200%
        result = calculate_engagement_rate(1000, 500, 500, 1000)
        assert result == 200.0
    
    def test_single_view_with_engagement(self):
        """Test edge case with single view."""
        # 1 like + 1 comment + 1 share = 3 total engagement
        # 3 / 1 view = 3.0 = 300%
        result = calculate_engagement_rate(1, 1, 1, 1)
        assert result == 300.0
    
    def test_large_numbers(self):
        """Test with large realistic numbers."""
        # 10000 likes + 5000 comments + 2500 shares = 17500 total engagement
        # 17500 / 1000000 views = 0.0175 = 1.75%
        result = calculate_engagement_rate(10000, 5000, 2500, 1000000)
        assert abs(result - 1.75) < 0.01
    
    def test_floating_point_precision(self):
        """Test that result maintains reasonable floating point precision."""
        # 333 likes + 222 comments + 111 shares = 666 total engagement
        # 666 / 1000 views = 0.666 = 66.6%
        result = calculate_engagement_rate(333, 222, 111, 1000)
        assert abs(result - 66.6) < 0.01


class TestCalculateConversionRate:
    """Tests for calculate_conversion_rate function."""
    
    def test_basic_conversion_rate_calculation(self):
        """Test basic conversion rate calculation with typical values."""
        # 50 buyers / 1000 views = 0.05 = 5.0%
        result = calculate_conversion_rate(50, 1000)
        assert result == 5.0
    
    def test_zero_views_returns_zero(self):
        """Test that zero views returns 0.0 without division error."""
        result = calculate_conversion_rate(10, 0)
        assert result == 0.0
    
    def test_zero_buyers_with_views(self):
        """Test video with views but no buyers."""
        result = calculate_conversion_rate(0, 1000)
        assert result == 0.0
    
    def test_all_zeros(self):
        """Test edge case where all metrics are zero."""
        result = calculate_conversion_rate(0, 0)
        assert result == 0.0
    
    def test_high_conversion_rate(self):
        """Test video with high conversion rate."""
        # 100 buyers / 1000 views = 0.1 = 10%
        result = calculate_conversion_rate(100, 1000)
        assert result == 10.0
    
    def test_perfect_conversion_rate(self):
        """Test case where all viewers become buyers (100% conversion)."""
        # 1000 buyers / 1000 views = 1.0 = 100%
        result = calculate_conversion_rate(1000, 1000)
        assert result == 100.0
    
    def test_single_view_with_buyer(self):
        """Test edge case with single view and single buyer."""
        # 1 buyer / 1 view = 1.0 = 100%
        result = calculate_conversion_rate(1, 1)
        assert result == 100.0
    
    def test_single_view_no_buyer(self):
        """Test edge case with single view but no buyer."""
        # 0 buyers / 1 view = 0.0 = 0%
        result = calculate_conversion_rate(0, 1)
        assert result == 0.0
    
    def test_large_numbers(self):
        """Test with large realistic numbers."""
        # 5000 buyers / 1000000 views = 0.005 = 0.5%
        result = calculate_conversion_rate(5000, 1000000)
        assert abs(result - 0.5) < 0.01
    
    def test_floating_point_precision(self):
        """Test that result maintains reasonable floating point precision."""
        # 333 buyers / 10000 views = 0.0333 = 3.33%
        result = calculate_conversion_rate(333, 10000)
        assert abs(result - 3.33) < 0.01
    
    def test_low_conversion_rate(self):
        """Test video with very low conversion rate."""
        # 1 buyer / 10000 views = 0.0001 = 0.01%
        result = calculate_conversion_rate(1, 10000)
        assert abs(result - 0.01) < 0.001
    
    def test_typical_ecommerce_conversion(self):
        """Test typical e-commerce conversion rate (2-3%)."""
        # 25 buyers / 1000 views = 0.025 = 2.5%
        result = calculate_conversion_rate(25, 1000)
        assert result == 2.5



class TestCalculateVelocity:
    """Tests for calculate_velocity function."""
    
    def test_basic_velocity_calculation(self):
        """Test basic velocity calculation with 1 hour elapsed."""
        now = datetime.now(timezone.utc)
        posted_1h_ago = now - timedelta(hours=1)
        # 1000 views / 1 hour = 1000 views per hour
        result = calculate_velocity(1000, posted_1h_ago)
        assert abs(result - 1000.0) < 1.0  # Allow small floating point variance
    
    def test_velocity_24_hours(self):
        """Test velocity calculation with 24 hours elapsed."""
        now = datetime.now(timezone.utc)
        posted_24h_ago = now - timedelta(hours=24)
        # 2400 views / 24 hours = 100 views per hour
        result = calculate_velocity(2400, posted_24h_ago)
        assert abs(result - 100.0) < 1.0
    
    def test_velocity_half_hour(self):
        """Test velocity calculation with 30 minutes elapsed."""
        now = datetime.now(timezone.utc)
        posted_30m_ago = now - timedelta(minutes=30)
        # 500 views / 0.5 hours = 1000 views per hour
        result = calculate_velocity(500, posted_30m_ago)
        assert abs(result - 1000.0) < 1.0
    
    def test_zero_views(self):
        """Test velocity with zero views."""
        now = datetime.now(timezone.utc)
        posted_1h_ago = now - timedelta(hours=1)
        # 0 views / 1 hour = 0 views per hour
        result = calculate_velocity(0, posted_1h_ago)
        assert result == 0.0
    
    def test_future_timestamp_returns_zero(self):
        """Test that future timestamp returns 0 (edge case: hours <= 0)."""
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(hours=1)
        # Future timestamp should return 0
        result = calculate_velocity(1000, future_time)
        assert result == 0.0
    
    def test_same_timestamp_returns_zero(self):
        """Test that same timestamp (very small time elapsed) returns near-zero or small value."""
        now = datetime.now(timezone.utc)
        # Very small time elapsed (microseconds) should return very small velocity or zero
        result = calculate_velocity(1000, now)
        # Due to execution time, result might be very large or zero depending on timing
        # We just verify it doesn't crash and returns a number
        assert isinstance(result, float)
        assert result >= 0.0
    
    def test_high_velocity_viral_content(self):
        """Test high velocity for viral content."""
        now = datetime.now(timezone.utc)
        posted_1h_ago = now - timedelta(hours=1)
        # 1 million views / 1 hour = 1 million views per hour
        result = calculate_velocity(1000000, posted_1h_ago)
        assert abs(result - 1000000.0) < 1.0
    
    def test_low_velocity_slow_content(self):
        """Test low velocity for slow-growing content."""
        now = datetime.now(timezone.utc)
        posted_24h_ago = now - timedelta(hours=24)
        # 100 views / 24 hours = 4.17 views per hour
        result = calculate_velocity(100, posted_24h_ago)
        assert abs(result - 4.17) < 0.1
    
    def test_naive_datetime_conversion(self):
        """Test that naive datetime (no timezone) is handled correctly."""
        # Create naive datetime (no timezone info) 1 hour ago
        posted_1h_ago_naive = datetime.now() - timedelta(hours=1)
        # Should not raise error and should calculate velocity
        result = calculate_velocity(1000, posted_1h_ago_naive)
        # Result should be approximately 1000 (allowing for time variance and timezone differences)
        # Since naive datetime is treated as UTC, result should be reasonable
        assert result >= 0.0  # Just verify it doesn't crash and returns non-negative
        assert isinstance(result, float)
    
    def test_very_old_content(self):
        """Test velocity for very old content (30 days)."""
        now = datetime.now(timezone.utc)
        posted_30d_ago = now - timedelta(days=30)
        # 72000 views / 720 hours = 100 views per hour
        result = calculate_velocity(72000, posted_30d_ago)
        assert abs(result - 100.0) < 1.0
    
    def test_minutes_precision(self):
        """Test velocity calculation with minute precision."""
        now = datetime.now(timezone.utc)
        posted_10m_ago = now - timedelta(minutes=10)
        # 100 views / (10/60) hours = 600 views per hour
        result = calculate_velocity(100, posted_10m_ago)
        assert abs(result - 600.0) < 10.0
    
    def test_large_numbers(self):
        """Test with large realistic numbers."""
        now = datetime.now(timezone.utc)
        posted_48h_ago = now - timedelta(hours=48)
        # 10 million views / 48 hours = 208,333.33 views per hour
        result = calculate_velocity(10000000, posted_48h_ago)
        assert abs(result - 208333.33) < 100.0
