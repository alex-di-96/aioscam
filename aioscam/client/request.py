"""
HTTP Request builder
"""

from typing import Any, Dict, Optional
from aioscam.enums import HttpMethod


def _serialize(value: Any) -> Any:
    """Recursively convert Pydantic models and enums to JSON-safe types."""
    if hasattr(value, "model_dump"):
        return _serialize(value.model_dump())
    if hasattr(value, "dict"):
        return _serialize(value.dict())
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items() if v is not None}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


class RequestBuilder:
    """
    Builder for HTTP requests to Max API
    
    Usage:
        request = RequestBuilder("/sendMessage", HttpMethod.POST)
        request.set_token("your_token")
        request.set_body({"chat_id": 123, "text": "Hello"})
    """
    
    def __init__(
        self,
        path: str,
        method: HttpMethod = HttpMethod.POST,
    ):
        self.path = path
        self.method = method
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.body: Optional[Dict[str, Any]] = None
        self.params: Optional[Dict[str, Any]] = None
        self.timeout: int = 30
    
    def set_token(self, token: str) -> "RequestBuilder":
        """Set authentication token"""
        self.token = token
        self.headers["Authorization"] = token
        return self
    
    def set_body(self, body: Dict[str, Any]) -> "RequestBuilder":
        """Set request body"""
        self.body = body
        return self
    
    def set_params(self, params: Dict[str, Any]) -> "RequestBuilder":
        """Set query parameters (for GET requests)"""
        self.params = params
        return self
    
    def set_headers(self, headers: Dict[str, str]) -> "RequestBuilder":
        """Set additional headers"""
        self.headers.update(headers)
        return self
    
    def set_timeout(self, timeout: int) -> "RequestBuilder":
        """Set request timeout in seconds"""
        self.timeout = timeout
        return self
    
    def add_field(self, key: str, value: Any) -> "RequestBuilder":
        """Add a field to request body"""
        if self.body is None:
            self.body = {}
        self.body[key] = value
        return self
    
    def build(self) -> Dict[str, Any]:
        """
        Build request dictionary for aiohttp
        
        Returns:
            Dict with method, url, headers, json, params, timeout
        """
        request = {
            "method": self.method.value,
            "headers": self.headers,
            "timeout": self.timeout,
        }
        
        if self.body:
            request["json"] = _serialize(self.body)
        
        if self.params:
            request["params"] = self.params
        
        return request
