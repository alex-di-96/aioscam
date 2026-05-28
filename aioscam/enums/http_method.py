"""
HTTP method enum
"""

from enum import Enum


class HttpMethod(str, Enum):
    """HTTP methods for API requests"""
    
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
