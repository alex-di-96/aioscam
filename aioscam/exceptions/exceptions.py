"""
All exceptions for AioScam framework
"""

from typing import Optional


class AioScamError(Exception):
    """Base exception for AioScam"""
    pass


class ApiError(AioScamError):
    """
    Error raised when Max API returns an error response
    
    Attributes:
        code: Error code from API
        message: Error description
        response: Raw API response
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        response: Optional[dict] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.response = response or {}


class BotTokenError(AioScamError):
    """Error raised when bot token is invalid"""
    pass


class NetworkError(AioScamError):
    """Error raised when network request fails"""
    
    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


class TimeoutError(NetworkError):
    """Error raised when request times out"""
    pass


class RetryAfter(ApiError):
    """
    Error raised when API requires retry after delay
    
    Attributes:
        retry_after: Seconds to wait before retry
    """
    
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


class UnauthorizedError(ApiError):
    """Error raised when bot token is invalid or expired"""
    pass


class ForbiddenError(ApiError):
    """Error raised when bot doesn't have permission"""
    pass


class NotFoundError(ApiError):
    """Error raised when resource not found"""
    pass


class ValidationError(AioScamError):
    """Error raised when data validation fails"""
    pass


class FSMError(AioScamError):
    """Error raised when FSM operations fail"""
    pass


class DispatcherError(AioScamError):
    """Error raised when dispatcher operations fail"""
    pass
