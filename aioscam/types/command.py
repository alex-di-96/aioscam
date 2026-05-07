"""
Command type
"""

from typing import Optional
from aioscam.types.base import MaxObject


class Command(MaxObject):
    """
    Bot command
    
    Attributes:
        command: Command name (without /)
        description: Command description
        prefix: Command prefix (default: /)
    """
    
    command: str
    description: Optional[str] = None
    prefix: str = "/"
    
    def __init__(self, command: str, description: Optional[str] = None, prefix: str = "/"):
        super().__init__(command=command, description=description, prefix=prefix)
    
    def __str__(self) -> str:
        return f"{self.prefix}{self.command}"
    
    def __repr__(self) -> str:
        return f"Command({self.command})"
