"""
Analytics calculation helper functions.

This module provides calculation utilities for analytics metrics including
engagement rates, conversion rates, and velocity calculations.
"""

from datetime import datetime, timezone


def calculate_engagement_rate(likes: int, comments: int, shares: int, views: int) -> float:
    """
    Calculate engagement rate for a content video.
    
    Formula: ((likes + comments + shares) / views) × 100
    
    Args:
        likes: Number of likes on the video
        comments: Number of comments on the video
        shares: Number of shares of the video
        views: Number of views on the video
        
    Returns:
        Engagement rate as a percentage (0.0 if views = 0)
        
    Examples:
        >>> calculate_engagement_rate(100, 50, 25, 1000)
        17.5
        >>> calculate_engagement_rate(0, 0, 0, 0)
        0.0
    """
    if views == 0:
        return 0.0
    
    total_engagement = likes + comments + shares
    return (total_engagement / views) * 100


def calculate_conversion_rate(buyers: int, views: int) -> float:
    """
    Calculate conversion rate for a content video.
    
    Formula: (buyers / views) × 100
    
    Args:
        buyers: Number of unique buyers from the video
        views: Number of views on the video
        
    Returns:
        Conversion rate as a percentage (0.0 if views = 0)
        
    Examples:
        >>> calculate_conversion_rate(50, 1000)
        5.0
        >>> calculate_conversion_rate(0, 0)
        0.0
        >>> calculate_conversion_rate(100, 2000)
        5.0
    """
    if views == 0:
        return 0.0
    
    return (buyers / views) * 100


def calculate_velocity(views: int, posted_at: datetime) -> float:
    """
    Calculate velocity (views per hour) for a content video.
    
    Velocity measures how quickly a video is gaining views by calculating
    the rate of views per hour since posting.
    
    Formula: views / hours_since_posted
    
    Args:
        views: Number of views on the video
        posted_at: Timestamp when the video was posted
        
    Returns:
        Velocity as views per hour (0.0 if hours <= 0)
        
    Examples:
        >>> from datetime import datetime, timezone, timedelta
        >>> now = datetime.now(timezone.utc)
        >>> posted_1h_ago = now - timedelta(hours=1)
        >>> calculate_velocity(1000, posted_1h_ago)
        1000.0
        >>> posted_24h_ago = now - timedelta(hours=24)
        >>> calculate_velocity(2400, posted_24h_ago)
        100.0
    """
    # Get current time in UTC
    now = datetime.now(timezone.utc)
    
    # Ensure posted_at is timezone-aware
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)
    
    # Calculate time difference in hours
    time_diff = now - posted_at
    hours = time_diff.total_seconds() / 3600
    
    # Handle edge case: return 0 if hours <= 0
    if hours <= 0:
        return 0.0
    
    # Calculate and return velocity
    return views / hours
