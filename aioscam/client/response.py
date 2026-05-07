"""
HTTP Response wrapper
"""

from typing import Any, Optional
from pydantic import BaseModel


class Response(BaseModel):
    """
    Wrapper for HTTP response
    
    Attributes:
        ok: Whether the request was successful
        result: Response data
        error: Error message if request failed
        status_code: HTTP status code
        headers: Response headers
    """
    
    ok: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    headers: Optional[dict] = None
    
    @property
    def description(self) -> Optional[str]:
        """Get error description if present"""
        if self.error and isinstance(self.result, dict):
            return self.result.get("description")
        return None
    
    @property
    def code(self) -> Optional[int]:
        """Get error code if present"""
        if self.error and isinstance(self.result, dict):
            return self.result.get("code")
        return None
