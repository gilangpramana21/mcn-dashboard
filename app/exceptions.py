"""Exception hierarchy for the TikTok Influencer Marketing Agent."""


class TikTokAgentError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str = "", *args):
        super().__init__(message, *args)
        self.message = message


# ---------------------------------------------------------------------------
# Integration errors
# ---------------------------------------------------------------------------


class IntegrationError(TikTokAgentError):
    """Raised when an external integration call fails."""


class AffiliateCenterError(IntegrationError):
    """Raised when the Affiliate Center API returns an error."""


class TikTokAPIError(IntegrationError):
    """Raised when the TikTok API returns an error."""


class WhatsAppAPIError(IntegrationError):
    """Raised when the WhatsApp API returns an error."""


# ---------------------------------------------------------------------------
# Authentication / authorization errors
# ---------------------------------------------------------------------------


class AuthenticationError(TikTokAgentError):
    """Raised when authentication fails."""


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT or OAuth token has expired."""


class RateLimitError(IntegrationError):
    """Raised when an API rate limit is exceeded."""


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class ValidationError(TikTokAgentError):
    """Raised when input data fails validation."""


class BlacklistViolationError(ValidationError):
    """Raised when an operation is attempted on a blacklisted influencer."""


class ClassificationError(TikTokAgentError):
    """Raised when feedback classification fails."""


# ---------------------------------------------------------------------------
# WhatsApp collection errors
# ---------------------------------------------------------------------------


class WhatsAppCollectionError(TikTokAgentError):
    """Raised when WhatsApp number collection fails."""


class InvalidPhoneNumberError(WhatsAppCollectionError):
    """Raised when a phone number does not pass E.164 / Indonesian validation."""


class ChatTimeoutError(WhatsAppCollectionError):
    """Raised when the affiliate does not reply within the allowed timeout."""


# ---------------------------------------------------------------------------
# Learning engine errors
# ---------------------------------------------------------------------------


class LearningEngineError(TikTokAgentError):
    """Raised when the learning engine encounters an error."""


class ModelTrainingError(LearningEngineError):
    """Raised when model training fails."""


# ---------------------------------------------------------------------------
# Template errors
# ---------------------------------------------------------------------------


class TemplateInUseError(TikTokAgentError):
    """Raised when a template deletion is attempted while it is used by an active campaign."""


# ---------------------------------------------------------------------------
# Error response helpers
# ---------------------------------------------------------------------------


def create_error_response(
    code: str,
    message: str,
    details: dict | None = None
) -> dict:
    """Create a standardized error response format.
    
    This helper ensures all API errors follow the consistent format:
    { "error": { "code": str, "message": str, "details": {...} } }
    
    Args:
        code: Error code identifier (e.g., "INVALID_PRICE", "MISSING_FIELD")
        message: Human-readable error message
        details: Optional dictionary with additional error context
        
    Returns:
        Dictionary with standardized error structure
        
    Example:
        >>> create_error_response(
        ...     code="INVALID_PRICE",
        ...     message="Product price must be non-negative",
        ...     details={"field": "price", "value": -100}
        ... )
        {
            "error": {
                "code": "INVALID_PRICE",
                "message": "Product price must be non-negative",
                "details": {"field": "price", "value": -100}
            }
        }
    """
    error_response = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {}
        }
    }
    return error_response
