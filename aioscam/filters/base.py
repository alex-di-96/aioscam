"""
Base filter class
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class FilterResult:
    """
    Result of filter execution
    
    Attributes:
        passed: Whether filter passed
        data: Data to pass to handler
    """
    
    passed: bool
    data: Optional[dict] = None


class BaseFilter(ABC):
    """
    Base class for all filters
    
    Filters are used to determine if an event should be handled
    """
    
    @abstractmethod
    async def __call__(self, event: Any) -> FilterResult:
        """
        Check if event matches filter
        
        Args:
            event: Event object
        
        Returns:
            FilterResult with pass/fail and optional data
        """
        ...
    
    def __and__(self, other: "BaseFilter") -> "AndFilter":
        return AndFilter(self, other)
    
    def __or__(self, other: "BaseFilter") -> "OrFilter":
        return OrFilter(self, other)
    
    def __invert__(self) -> "NotFilter":
        return NotFilter(self)


class AndFilter(BaseFilter):
    """Logical AND filter"""
    
    def __init__(self, *filters: BaseFilter):
        self.filters = filters
    
    async def __call__(self, event: Any) -> FilterResult:
        for f in self.filters:
            result = await f(event)
            if not result.passed:
                return FilterResult(passed=False)
        return FilterResult(passed=True)


class OrFilter(BaseFilter):
    """Logical OR filter"""
    
    def __init__(self, *filters: BaseFilter):
        self.filters = filters
    
    async def __call__(self, event: Any) -> FilterResult:
        for f in self.filters:
            result = await f(event)
            if result.passed:
                return result
        return FilterResult(passed=False)


class NotFilter(BaseFilter):
    """Logical NOT filter"""
    
    def __init__(self, filter: BaseFilter):
        self.filter = filter
    
    async def __call__(self, event: Any) -> FilterResult:
        result = await self.filter(event)
        return FilterResult(passed=not result.passed)
