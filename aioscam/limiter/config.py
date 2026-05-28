"""
Rate Limit Configuration
"""

from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
    """
    Rate limiter configuration

    Attributes:
        rate: Requests per second (default: 10 — safe for most APIs)
        burst: Maximum burst size (tokens in bucket, default: 20)
        max_retries: Max retries on 429 response (default: 3)
        backoff_base: Base backoff delay in seconds (default: 1.0)
        backoff_max: Maximum backoff delay in seconds (default: 60.0)
        retry_429: Automatically retry on 429 (default: True)
    """

    rate: float = 10.0
    burst: int = 20
    max_retries: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 60.0
    retry_429: bool = True

    @classmethod
    def strict(cls) -> "RateLimitConfig":
        """Conservative settings for production"""
        return cls(rate=5.0, burst=10, max_retries=5)

    @classmethod
    def relaxed(cls) -> "RateLimitConfig":
        """Relaxed settings for development/testing"""
        return cls(rate=30.0, burst=50, max_retries=1)
