"""
Command and BotCommand types
"""

from typing import Optional
from aioscam.types.base import MaxObject


class Command(MaxObject):
    """
    Bot command (for filters and routing)

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


class BotCommand(MaxObject):
    """
    Bot command for registration (set_my_commands)

    Matches official MAX SDK BotCommand type.
    Sent as {"name": "...", "description": "..."} in API request.

    Attributes:
        name: Command name (without /)
        description: Optional command description
    """

    name: str
    description: Optional[str] = None

    def __init__(self, name: str, description: Optional[str] = None):
        super().__init__(name=name, description=description)
