"""
Base type for all Max API objects
"""

from typing import Any, Dict
from pydantic import BaseModel, ConfigDict


class MaxObject(BaseModel):
    """
    Base class for all Max API objects
    
    Provides:
    - Pydantic validation
    - Dictionary conversion
    - JSON serialization
    """
    
    model_config = ConfigDict(
        frozen=False,
        extra="allow",
        populate_by_name=True,
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(exclude_none=True)
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json(exclude_none=True)
