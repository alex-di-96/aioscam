"""
Exceptions for AioScam
"""

from aioscam.exceptions.exceptions import (
    AioScamError,
    ApiError,
    BotTokenError,
    NetworkError,
    TimeoutError,
    RetryAfter,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    FSMError,
    DispatcherError,
)

__all__ = [
    "AioScamError",
    "ApiError",
    "BotTokenError",
    "NetworkError",
    "TimeoutError",
    "RetryAfter",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationError",
    "FSMError",
    "DispatcherError",
]
