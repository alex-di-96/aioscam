"""
HTTP Request builder
"""

from typing import Any, Dict, Optional
from aioscam.enums import HttpMethod


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
            request["json"] = self.body
        
        if self.params:
            request["params"] = self.params
        
        return request
