"""Unit tests for analytics platform domain models."""

from datetime import datetime
from uuid import uuid4

import pytest

from app.models.domain import ContentVideo, Product


class TestProductModel:
    """Tests for Product dataclass."""

    def test_product_creation_with_all_fields(self):
        """Test creating a Product with all fields specified."""
        product_id = str(uuid4())
        now = datetime.utcnow()
        
        product = Product(
            id=product_id,
            tiktok_product_id="TT123456",
            name="Test Product",
            price=99.99,
            category="Electronics",
            image_url="https://example.com/image.jpg",
            shop_name="Test Shop",
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        assert product.id == product_id
        assert product.tiktok_product_id == "TT123456"
        assert product.name == "Test Product"
        assert product.price == 99.99
        assert product.category == "Electronics"
        assert product.image_url == "https://example.com/image.jpg"
        assert product.shop_name == "Test Shop"
        assert product.is_active is True
        assert product.created_at == now
        assert product.updated_at == now

    def test_product_creation_with_minimal_fields(self):
        """Test creating a Product with only required fields."""
        product = Product(
            id=str(uuid4()),
            tiktok_product_id="TT789012",
            name="Minimal Product",
            price=50.00
        )
        
        assert product.tiktok_product_id == "TT789012"
        assert product.name == "Minimal Product"
        assert product.price == 50.00
        assert product.category is None
        assert product.image_url is None
        assert product.shop_name is None
        assert product.is_active is True
        assert isinstance(product.created_at, datetime)
        assert isinstance(product.updated_at, datetime)

    def test_product_non_negative_price(self):
        """Test that Product can be created with non-negative price."""
        product = Product(
            id=str(uuid4()),
            tiktok_product_id="TT000001",
            name="Free Product",
            price=0.0
        )
        
        assert product.price == 0.0


class TestContentVideoModel:
    """Tests for ContentVideo dataclass."""

    def test_content_video_creation_with_all_fields(self):
        """Test creating a ContentVideo with all fields specified."""
        video_id = str(uuid4())
        product_id = str(uuid4())
        creator_id = "creator123"
        now = datetime.utcnow()
        
        video = ContentVideo(
            id=video_id,
            tiktok_video_id="VID123456",
            creator_id=creator_id,
            product_id=product_id,
            title="Test Video",
            views=10000,
            likes=500,
            comments=50,
            shares=25,
            gmv_generated=1500000.50,
            buyers=100,
            posted_at=now,
            created_at=now
        )
        
        assert video.id == video_id
        assert video.tiktok_video_id == "VID123456"
        assert video.creator_id == creator_id
        assert video.product_id == product_id
        assert video.title == "Test Video"
        assert video.views == 10000
        assert video.likes == 500
        assert video.comments == 50
        assert video.shares == 25
        assert video.gmv_generated == 1500000.50
        assert video.buyers == 100
        assert video.posted_at == now
        assert video.created_at == now

    def test_content_video_creation_with_minimal_fields(self):
        """Test creating a ContentVideo with only required fields."""
        video = ContentVideo(
            id=str(uuid4()),
            tiktok_video_id="VID789012",
            creator_id="creator456"
        )
        
        assert video.tiktok_video_id == "VID789012"
        assert video.creator_id == "creator456"
        assert video.product_id is None
        assert video.title is None
        assert video.views == 0
        assert video.likes == 0
        assert video.comments == 0
        assert video.shares == 0
        assert video.gmv_generated == 0.0
        assert video.buyers == 0
        assert isinstance(video.posted_at, datetime)
        assert isinstance(video.created_at, datetime)

    def test_content_video_without_product(self):
        """Test creating a ContentVideo without a product (non-product content)."""
        video = ContentVideo(
            id=str(uuid4()),
            tiktok_video_id="VID999999",
            creator_id="creator789",
            product_id=None,
            views=5000,
            likes=250
        )
        
        assert video.product_id is None
        assert video.views == 5000
        assert video.likes == 250

    def test_content_video_default_metrics_are_non_negative(self):
        """Test that default metric values are non-negative."""
        video = ContentVideo(
            id=str(uuid4()),
            tiktok_video_id="VID000000",
            creator_id="creator000"
        )
        
        assert video.views >= 0
        assert video.likes >= 0
        assert video.comments >= 0
        assert video.shares >= 0
        assert video.gmv_generated >= 0.0
        assert video.buyers >= 0
