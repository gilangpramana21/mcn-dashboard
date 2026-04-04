"""Unit tests for exception handling and error response helpers."""

import pytest
from app.exceptions import create_error_response


class TestErrorResponseHelper:
    """Test the create_error_response helper function."""
    
    def test_create_error_response_with_details(self):
        """Test creating error response with all fields."""
        result = create_error_response(
            code="INVALID_PRICE",
            message="Product price must be non-negative",
            details={"field": "price", "value": -100}
        )
        
        assert result == {
            "error": {
                "code": "INVALID_PRICE",
                "message": "Product price must be non-negative",
                "details": {"field": "price", "value": -100}
            }
        }
    
    def test_create_error_response_without_details(self):
        """Test creating error response without details."""
        result = create_error_response(
            code="MISSING_FIELD",
            message="Required field is missing"
        )
        
        assert result == {
            "error": {
                "code": "MISSING_FIELD",
                "message": "Required field is missing",
                "details": {}
            }
        }
    
    def test_create_error_response_with_none_details(self):
        """Test creating error response with explicit None details."""
        result = create_error_response(
            code="GENERIC_ERROR",
            message="An error occurred",
            details=None
        )
        
        assert result == {
            "error": {
                "code": "GENERIC_ERROR",
                "message": "An error occurred",
                "details": {}
            }
        }
    
    def test_error_response_structure(self):
        """Test that error response has correct structure."""
        result = create_error_response(
            code="TEST_CODE",
            message="Test message",
            details={"key": "value"}
        )
        
        # Verify top-level structure
        assert "error" in result
        assert len(result) == 1
        
        # Verify error object structure
        error = result["error"]
        assert "code" in error
        assert "message" in error
        assert "details" in error
        assert len(error) == 3
    
    def test_error_response_types(self):
        """Test that error response fields have correct types."""
        result = create_error_response(
            code="TYPE_TEST",
            message="Testing types",
            details={"field": "test", "value": 123}
        )
        
        error = result["error"]
        assert isinstance(error["code"], str)
        assert isinstance(error["message"], str)
        assert isinstance(error["details"], dict)
    
    def test_error_response_with_complex_details(self):
        """Test error response with nested details."""
        result = create_error_response(
            code="VALIDATION_ERROR",
            message="Multiple validation errors",
            details={
                "fields": ["price", "category"],
                "errors": {
                    "price": "Must be positive",
                    "category": "Must not be empty"
                },
                "count": 2
            }
        )
        
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert result["error"]["details"]["count"] == 2
        assert "price" in result["error"]["details"]["fields"]
        assert "category" in result["error"]["details"]["fields"]
