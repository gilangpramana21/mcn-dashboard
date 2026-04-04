"""Analytics Validation — validation functions for analytics platform data."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import HTTPException


def validate_product(product_data: Dict[str, Any]) -> None:
    """Validate product data before insertion or update.
    
    Validates:
    - price >= 0 (non-negative)
    - tiktok_product_id is not empty
    - category is valid (if provided)
    
    Raises HTTPException with descriptive error for invalid data.
    
    Args:
        product_data: Dictionary containing product fields
        
    Raises:
        HTTPException: 400 status with error details if validation fails
    """
    # Validate tiktok_product_id is not empty
    tiktok_product_id = product_data.get("tiktok_product_id", "").strip()
    if not tiktok_product_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "MISSING_PRODUCT_ID",
                    "message": "TikTok Product ID is required and cannot be empty",
                    "details": {"field": "tiktok_product_id"}
                }
            }
        )
    
    # Validate price is non-negative
    price = product_data.get("price")
    if price is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "MISSING_PRICE",
                    "message": "Product price is required",
                    "details": {"field": "price"}
                }
            }
        )
    
    try:
        price_value = float(price)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_PRICE_TYPE",
                    "message": "Product price must be a valid number",
                    "details": {"field": "price", "value": price}
                }
            }
        )
    
    if price_value < 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_PRICE",
                    "message": "Product price must be non-negative (>= 0)",
                    "details": {"field": "price", "value": price_value}
                }
            }
        )
    
    # Validate category is valid (if provided)
    category = product_data.get("category")
    if category is not None:
        if isinstance(category, str):
            category_str = category.strip()
            if not category_str:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": {
                            "code": "INVALID_CATEGORY",
                            "message": "Product category cannot be empty string",
                            "details": {"field": "category"}
                        }
                    }
                )
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_CATEGORY_TYPE",
                        "message": "Product category must be a string",
                        "details": {"field": "category", "value": category}
                    }
                }
            )


def validate_content_video(video_data: Dict[str, Any]) -> None:
    """Validate content video data before insertion or update.
    
    Validates:
    - All metrics (views, likes, comments, shares, gmv_generated, buyers) >= 0
    - posted_at is not in the future
    - creator_id is not empty
    - product_id is not empty (if provided)
    
    Note: This function validates data format and business rules.
    Foreign key existence (creator_id, product_id) is validated by database constraints.
    
    Args:
        video_data: Dictionary containing content video fields
        
    Raises:
        HTTPException: 400 status with error details if validation fails
    """
    # Validate creator_id is not empty
    creator_id = video_data.get("creator_id", "").strip() if isinstance(video_data.get("creator_id"), str) else ""
    if not creator_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "MISSING_CREATOR_ID",
                    "message": "Creator ID is required and cannot be empty",
                    "details": {"field": "creator_id"}
                }
            }
        )
    
    # Validate product_id is not empty (if provided)
    product_id = video_data.get("product_id")
    if product_id is not None:
        if isinstance(product_id, str):
            product_id_str = product_id.strip()
            if not product_id_str:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": {
                            "code": "INVALID_PRODUCT_ID",
                            "message": "Product ID cannot be empty string",
                            "details": {"field": "product_id"}
                        }
                    }
                )
    
    # Validate all numeric metrics are non-negative
    numeric_fields = {
        "views": "Views",
        "likes": "Likes",
        "comments": "Comments",
        "shares": "Shares",
        "gmv_generated": "GMV generated",
        "buyers": "Buyers"
    }
    
    for field_name, display_name in numeric_fields.items():
        value = video_data.get(field_name)
        if value is None:
            # Allow None for optional fields with defaults
            continue
        
        try:
            numeric_value = float(value) if field_name == "gmv_generated" else int(value)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_METRIC_TYPE",
                        "message": f"{display_name} must be a valid number",
                        "details": {"field": field_name, "value": value}
                    }
                }
            )
        
        if numeric_value < 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_METRIC_VALUE",
                        "message": f"{display_name} must be non-negative (>= 0)",
                        "details": {"field": field_name, "value": numeric_value}
                    }
                }
            )
    
    # Validate posted_at is not in the future
    posted_at = video_data.get("posted_at")
    if posted_at is not None:
        # Handle both datetime objects and string timestamps
        if isinstance(posted_at, str):
            try:
                posted_at = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": {
                            "code": "INVALID_TIMESTAMP_FORMAT",
                            "message": "posted_at must be a valid ISO 8601 timestamp",
                            "details": {"field": "posted_at", "value": posted_at}
                        }
                    }
                )
        
        if isinstance(posted_at, datetime):
            now = datetime.utcnow()
            if posted_at.tzinfo is not None:
                # Make now timezone-aware for comparison
                from datetime import timezone
                now = datetime.now(timezone.utc)
            
            if posted_at > now:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": {
                            "code": "FUTURE_TIMESTAMP",
                            "message": "posted_at cannot be in the future",
                            "details": {"field": "posted_at", "value": posted_at.isoformat()}
                        }
                    }
                )


def validate_gmv_limit(gmv_value: float) -> None:
    """Validate that GMV does not exceed reasonable maximum limit.
    
    Validates:
    - GMV <= 10 billion Rupiah (10,000,000,000)
    
    Args:
        gmv_value: GMV value to validate
        
    Raises:
        HTTPException: 400 status with error details if validation fails
    """
    MAX_GMV = 10_000_000_000  # 10 billion Rupiah
    
    try:
        gmv_float = float(gmv_value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_GMV_TYPE",
                    "message": "GMV must be a valid number",
                    "details": {"value": gmv_value}
                }
            }
        )
    
    if gmv_float > MAX_GMV:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "GMV_EXCEEDS_LIMIT",
                    "message": f"GMV cannot exceed {MAX_GMV:,.0f} Rupiah (10 billion)",
                    "details": {"value": gmv_float, "max_allowed": MAX_GMV}
                }
            }
        )
