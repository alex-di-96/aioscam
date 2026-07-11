"""
All exceptions for AioScam framework.

Every exception here can carry a ``.hint`` — a short, actionable suggestion
for the most likely fix. Hints are appended automatically when the
exception is converted to a string (logged, printed, etc.), so
``str(exc)`` alone is usually enough to act on without reading a traceback.

Subclasses that know the likely cause set a sensible default hint;
pass ``hint=`` explicitly to override it at the raise site.
"""

from typing import Optional


class AioScamError(Exception):
    """
    Base exception for all AioScam errors.

    Attributes:
        message: Human-readable error description.
        hint: Optional actionable suggestion, appended to the message
              when the exception is converted to a string.
    """

    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message} — {self.hint}"
        return self.message


class ApiError(AioScamError):
    """
    Error raised when Max API returns an error response.

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
        hint: str = "",
    ):
        super().__init__(
            message,
            hint=hint or "see .response for the full API payload and .code for the Max error code",
        )
        self.code = code
        self.response = response or {}


class BotTokenError(AioScamError):
    """Error raised when the bot token is missing or malformed."""

    def __init__(self, message: str, hint: str = ""):
        super().__init__(
            message,
            hint=hint or "pass token=... to Bot(), or set the MAX_BOT_TOKEN environment variable",
        )


class NetworkError(AioScamError):
    """Error raised when a network request fails (DNS, connection reset, etc)."""

    def __init__(self, message: str, status: Optional[int] = None, hint: str = ""):
        super().__init__(
            message,
            hint=hint or "check internet connectivity and that platform-api2.max.ru is reachable from this host",
        )
        self.status = status


class TimeoutError(NetworkError):
    """Error raised when a request exceeds its configured timeout."""

    def __init__(self, message: str, status: Optional[int] = None, hint: str = ""):
        super().__init__(
            message,
            status=status,
            hint=hint or "increase timeout= on Bot()/AioScamClient, or check for a slow/unstable connection",
        )


class RetryAfter(ApiError):
    """
    Error raised when the API rate-limits the request (HTTP 429).

    Attributes:
        retry_after: Seconds to wait before retrying.
    """

    def __init__(
        self,
        message: str,
        retry_after: int,
        code: Optional[int] = None,
        response: Optional[dict] = None,
    ):
        super().__init__(
            message,
            code=code,
            response=response,
            hint=f"wait {retry_after}s before retrying; lower rate_limit= on Bot() to avoid hitting this",
        )
        self.retry_after = retry_after


class UnauthorizedError(ApiError):
    """Error raised when the bot token is invalid, revoked, or expired (HTTP 401)."""

    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        response: Optional[dict] = None,
        hint: str = "",
    ):
        super().__init__(
            message,
            code=code,
            response=response,
            hint=hint or "verify MAX_BOT_TOKEN is correct and the bot was not deleted/revoked at business.max.ru/self",
        )


class ForbiddenError(ApiError):
    """Error raised when the bot lacks permission for this action (HTTP 403)."""

    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        response: Optional[dict] = None,
        hint: str = "",
    ):
        super().__init__(
            message,
            code=code,
            response=response,
            hint=hint or "the bot may have been removed from the chat, or lacks the rights this action requires",
        )


class NotFoundError(ApiError):
    """Error raised when the target resource does not exist (HTTP 404)."""

    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        response: Optional[dict] = None,
        hint: str = "",
    ):
        super().__init__(
            message,
            code=code,
            response=response,
            hint=hint or "check that the chat_id/user_id/message_id is correct and still exists",
        )


class ValidationError(AioScamError):
    """Error raised when data fails validation before being sent to the API."""
    pass


class FSMError(AioScamError):
    """Error raised when FSM (finite state machine) operations fail."""
    pass


class DispatcherError(AioScamError):
    """Error raised when dispatcher operations fail (e.g. double-start)."""
    pass
